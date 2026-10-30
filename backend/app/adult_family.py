"""Separate adult logins, household connections, and approved suggestions."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from flask import jsonify, request, session
from sqlalchemy import or_
from .extensions import db, limiter
from .models import (User, Household, HouseholdMembership, HouseholdInvitation,
    HouseholdProfileAccess, HouseholdMemberProfileAccess, PersonProfile, FamilyFollow,
    GiftSuggestion, Wishlist, WishlistItem, WishlistItemWishlist, WishlistItemOccasion)
from .api import api, authenticated, error, normalized_email, profile_access, membership_for
from .invitation_mail import prepare_invitation
from .product_search import safe_product_url


def family_ids(user):
    return {m.household_id for m in HouseholdMembership.query.filter_by(user_id=user.id).all()
        if m.is_family_member or m.role in ('owner', 'admin')}


def family_account_ids(user):
    homes=family_ids(user)
    ids={user.id}
    for m in HouseholdMembership.query.filter(HouseholdMembership.household_id.in_(homes)).all():
        if m.is_family_member or m.role in ('owner','admin'): ids.add(m.user_id)
    return ids


def followed_ids(user):
    return {r.followed_id for r in FamilyFollow.query.filter(FamilyFollow.follower_id.in_(family_account_ids(user))).all()}


def sync_family_connections(user):
    if user.is_child or user.is_support: return
    homes=family_ids(user)
    if not homes:
        for membership in HouseholdMembership.query.filter_by(user_id=user.id).filter(
                HouseholdMembership.inherited_from_household_id.isnot(None)).all():
            HouseholdMemberProfileAccess.query.filter_by(membership_id=membership.id).delete()
            db.session.delete(membership)
        db.session.commit()
        return
    accounts=family_account_ids(user)
    desired={}
    # Copy viewing grants, preserving selective profile permissions.
    for source in HouseholdMembership.query.filter(HouseholdMembership.user_id.in_(accounts),
            HouseholdMembership.role.in_(('shopper','viewer')),HouseholdMembership.inherited_from_household_id.is_(None)).all():
        home=db.session.get(Household,source.household_id)
        if home and (home.owner_id in followed_ids(user) or home.registry_type=='company'): desired.setdefault(home.id,[]).append(source)
    inherited=HouseholdMembership.query.filter_by(user_id=user.id).filter(HouseholdMembership.inherited_from_household_id.isnot(None)).all()
    changed=False
    for m in inherited:
        if m.household_id not in desired:
            HouseholdMemberProfileAccess.query.filter_by(membership_id=m.id).delete()
            db.session.delete(m); changed=True
    for home_id,sources in desired.items():
        m=HouseholdMembership.query.filter_by(user_id=user.id,household_id=home_id).first()
        if m and m.inherited_from_household_id is None: continue
        if m is None:
            m=HouseholdMembership(user_id=user.id,household_id=home_id,role='shopper',inherited_from_household_id=min(homes))
            db.session.add(m);db.session.flush();changed=True
        share_all=any(s.share_all_profiles for s in sources)
        if m.share_all_profiles!=share_all: m.share_all_profiles=share_all;changed=True
        ids={r.profile_id for source in sources for r in HouseholdMemberProfileAccess.query.filter_by(membership_id=source.id).all()}
        current={r.profile_id for r in HouseholdMemberProfileAccess.query.filter_by(membership_id=m.id).all()}
        for pid in ids-current: db.session.add(HouseholdMemberProfileAccess(membership_id=m.id,profile_id=pid,can_edit=False));changed=True
        for pid in current-ids: HouseholdMemberProfileAccess.query.filter_by(membership_id=m.id,profile_id=pid).delete();changed=True
    if changed: db.session.commit()


def can_suggest_profile(user, profile):
    return bool(profile and profile.is_adult and profile.account_user_id not in (None,user.id) and
        HouseholdProfileAccess.query.filter(HouseholdProfileAccess.profile_id==profile.id,
            HouseholdProfileAccess.household_id.in_(family_ids(user))).first())


def can_add_child_gift(user, profile):
    return bool(profile and not profile.is_adult and not user.is_child and
        HouseholdProfileAccess.query.filter(HouseholdProfileAccess.profile_id==profile.id,
            HouseholdProfileAccess.household_id.in_(family_ids(user))).first())


@api.post('/households/<int:household_id>/adult-invitations')
@authenticated
@limiter.limit('10 per hour')
def invite_adult_member(household_id):
    home=db.session.get(Household,household_id)
    if not home or home.owner_id!=request.current_user.id or home.registry_type!='family':
        return error('Only the family creator can invite adults to join.',403)
    payload=request.get_json(silent=True) or {}
    pid=payload.get('profile_id')
    profile=db.session.get(PersonProfile,pid) if type(pid) is int else None
    email=normalized_email(payload.get('email'))
    if not email or email.lower()==request.current_user.email.lower(): return error('Enter the adult member email.',400)
    if not profile or not profile.is_adult or not HouseholdProfileAccess.query.filter_by(household_id=home.id,profile_id=profile.id).first():
        return error('Choose an adult in this family.',400)
    if profile.account_user_id is not None: return error('This adult already has a login.',409)
    # Replacing an outstanding invitation revokes its old link.
    HouseholdInvitation.query.filter_by(household_id=home.id,linked_profile_id=profile.id,accepted_at=None).delete()
    token=secrets.token_urlsafe(32)
    invitation=HouseholdInvitation(household_id=home.id,email=email,token_hash=hashlib.sha256(token.encode()).hexdigest(),
        role='profile_manager',profile_ids=[profile.id],linked_profile_id=profile.id,expires_at=datetime.now(timezone.utc)+timedelta(days=7))
    db.session.add(invitation);profile.member_email=email;db.session.commit()
    mail=prepare_invitation(email,token,home.name,'family_member')
    return jsonify(message='Invitation sent.' if mail['delivery']=='sent' else 'Invitation created, but email could not be delivered.',email_message=mail),201


def accept_adult_invitation(invitation,user):
    profile=PersonProfile.query.filter_by(id=invitation.linked_profile_id).with_for_update().first()
    if not profile or not profile.is_adult: return error('Adult profile is unavailable.',409)
    if profile.account_user_id not in (None,user.id): return error('This adult profile already has another login.',409)
    home=db.session.get(Household,invitation.household_id)
    if home.owner_id==user.id: return error('Use your own separate adult account to join.',409)
    membership=membership_for(user,home.id)
    if membership is None:
        membership=HouseholdMembership(user_id=user.id,household_id=home.id,role='profile_manager')
        db.session.add(membership)
    membership.is_family_member=True;membership.share_all_profiles=True;membership.inherited_from_household_id=None
    profile.account_user_id=user.id;profile.member_email=user.email
    invitation.accepted_at=datetime.now(timezone.utc)
    db.session.commit();sync_family_connections(user)
    session['active_member_profile_id']=profile.id
    return jsonify(status='accepted',household_id=home.id,profile_ids=[profile.id],joined_family=True)


def suggestion_values(payload):
    allowed={'name','description','store_name','product_url','image_url','estimated_price','currency','priority','quantity','category'}
    if set(payload)-allowed: raise ValueError('Unsupported gift details.')
    name=payload.get('name','')
    if not isinstance(name,str) or not name.strip() or len(name)>200: raise ValueError('Choose a gift name up to 200 characters.')
    result={'name':name.strip()}
    for field,limit in [('description',2000),('store_name',120),('category',120)]:
        value=payload.get(field,'') or ''
        if not isinstance(value,str) or len(value)>limit: raise ValueError('Gift details are too long.')
        result[field]=value
    for field in ('product_url','image_url'):
        value=payload.get(field,'') or ''
        if value and not safe_product_url(value): raise ValueError('Use a public HTTPS product or image link.')
        result['image_path' if field=='image_url' else field]=value or None
    price=payload.get('estimated_price')
    if price not in (None,''):
        try: amount=Decimal(str(price))
        except InvalidOperation: raise ValueError('Enter a valid price.')
        if not amount.is_finite() or amount<0 or amount>Decimal('99999999.99'): raise ValueError('Enter a valid price.')
        result['estimated_price']=str(amount.quantize(Decimal('.01')))
    currency=payload.get('currency','USD')
    if not isinstance(currency,str) or len(currency)!=3 or not currency.isalpha(): raise ValueError('Choose a three-letter currency.')
    result['currency']=currency.upper()
    try:
        result['priority']=int(payload.get('priority',2));result['quantity']=int(payload.get('quantity',1))
    except (TypeError,ValueError):
        raise ValueError('Choose a positive quantity and a priority from 1 to 4.')
    if result['priority'] not in (1,2,3,4) or not 1<=result['quantity']<=10000:
        raise ValueError('Choose a quantity from 1 to 10,000 and priority from 1 to 4.')
    return result


@api.post('/profiles/<int:profile_id>/suggestions')
@authenticated
@limiter.limit('30 per hour')
def suggest_gift(profile_id):
    user=request.current_user
    profile=profile_access(user,profile_id)
    if not profile or not profile.is_adult or profile.account_user_id in (None,user.id):
        return error('Choose another joined adult in your family.',404)
    if not HouseholdProfileAccess.query.filter(HouseholdProfileAccess.profile_id==profile.id,HouseholdProfileAccess.household_id.in_(family_ids(user))).first():
        return error('This adult is not in your family.',403)
    try: values=suggestion_values(request.get_json(silent=True) or {})
    except ValueError as exc: return error(str(exc),400)
    suggestion=GiftSuggestion(sender_id=user.id,recipient_id=profile.account_user_id,profile_id=profile.id,data=values)
    db.session.add(suggestion);db.session.commit()
    return jsonify(message='Suggestion sent.',suggestion_id=suggestion.id),201


@api.get('/gift-suggestions')
@authenticated
def list_gift_suggestions():
    user=request.current_user
    rows=GiftSuggestion.query.filter_by(recipient_id=user.id,status='pending').order_by(GiftSuggestion.id.desc()).all()
    return jsonify(suggestions=[{'id':r.id,'profile_id':r.profile_id,'sender':db.session.get(User,r.sender_id).name,'gift':r.data} for r in rows
        if db.session.get(PersonProfile,r.profile_id).account_user_id==user.id])


@api.post('/gift-suggestions/<int:suggestion_id>/respond')
@authenticated
def respond_gift_suggestion(suggestion_id):
    user=request.current_user
    row=GiftSuggestion.query.filter_by(id=suggestion_id,recipient_id=user.id,status='pending').with_for_update().first()
    if not row or db.session.get(PersonProfile,row.profile_id).account_user_id!=user.id: return error('Suggestion not found.',404)
    payload=request.get_json(silent=True) or {}
    if payload.get('action')=='dismiss': row.status='dismissed';db.session.commit();return jsonify(status='dismissed')
    if payload.get('action')!='accept': return error('Choose Add to list or Dismiss.',400)
    wid=payload.get('wishlist_id')
    wishlist=db.session.get(Wishlist,wid) if type(wid) is int else None
    if not wishlist or wishlist.profile_id!=row.profile_id: return error('Choose one of your own lists.',400)
    item=WishlistItem(profile_id=row.profile_id,created_by_id=user.id,**row.data)
    db.session.add(item);db.session.flush()
    db.session.add(WishlistItemWishlist(item_id=item.id,wishlist_id=wishlist.id))
    if wishlist.occasion_id: db.session.add(WishlistItemOccasion(item_id=item.id,occasion_id=wishlist.occasion_id))
    row.status='accepted';db.session.commit()
    return jsonify(status='accepted',item_id=item.id),201


def suggestion_notifications(user):
    rows=GiftSuggestion.query.filter_by(recipient_id=user.id,status='pending').all()
    return [{'id':'suggestion-'+str(r.id),'suggestion_id':r.id,'message':db.session.get(User,r.sender_id).name+' suggested '+r.data['name'],
        'household_name':'','read':False,'created_at':r.created_at.isoformat(),'url':'/settings?tab=notifications'} for r in rows
        if db.session.get(PersonProfile,r.profile_id).account_user_id==user.id]
