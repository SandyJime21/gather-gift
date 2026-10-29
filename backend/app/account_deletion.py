"""Explicit account deletion with previewed, transactional family succession."""
import hashlib
import json
import secrets
import time
from pathlib import Path
from flask import current_app, jsonify, request, session
from sqlalchemy import delete
from .extensions import db, limiter
from .models import (User, Household, HouseholdMembership, HouseholdProfileAccess,
                     HouseholdMemberProfileAccess, PersonProfile, PersonalWish, WishlistItem,
                     WishlistLetter, GiftExchangeGame, AuditLog, PrivateGift, SharedAvatar, SharedTheme)
from .api import api, authenticated, error, record_audit


def remaining_owner(profile_id, departing_id, transfers, removed_homes):
    homes = Household.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.profile_id == profile_id).order_by(Household.id).all()
    for home in homes:
        if home.id in removed_homes:
            continue
        owner_id = transfers.get(home.id, home.owner_id)
        owner = db.session.get(User, owner_id)
        if owner and owner.id != departing_id and not owner.is_child and not owner.is_support:
            return owner
    return None


def deletion_plan(user):
    homes = Household.query.filter_by(owner_id=user.id).order_by(Household.id).all()
    families, transfers, removed = [], {}, []
    snapshot = []
    for home in homes:
        profiles = PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id == home.id).order_by(PersonProfile.id).all()
        candidates = []
        members = HouseholdMembership.query.filter_by(household_id=home.id).order_by(HouseholdMembership.id).all()
        for member in members:
            account = db.session.get(User, member.user_id)
            claimed = [p for p in profiles if p.account_user_id == member.user_id and p.is_adult and p.profile_type == 'person']
            if account and account.id != user.id and not account.is_child and not account.is_support and claimed and (member.is_family_member or member.role in ('owner','admin')):
                profile = next((p for p in claimed if p.is_guardian), claimed[0])
                candidates.append((member.role != 'admin', not profile.is_guardian, member.created_at, member.id, account, profile))
        candidates.sort(key=lambda row: row[:4])
        successor = candidates[0][4] if candidates else None
        successor_profile = candidates[0][5] if candidates else None
        if successor:
            transfers[home.id] = successor.id
        else:
            removed.append(home.id)
        families.append(dict(id=home.id,name=home.name,registry_type=home.registry_type,
            action='transfer' if successor else 'delete',
            successor=dict(id=successor.id,name=successor.name,profile_name=successor_profile.display_name) if successor else None,
            children=sum(p.profile_type=='person' and not p.is_adult for p in profiles),pets=sum(p.profile_type=='pet' for p in profiles)))
        snapshot.append(dict(home=home.id,owner=home.owner_id,
            profiles=[(p.id,p.account_user_id,p.is_adult,p.is_guardian) for p in profiles],
            members=[(m.id,m.user_id,m.role,m.is_family_member) for m in members]))
    child_plans=[]
    for child in User.query.filter_by(parent_user_id=user.id,is_child=True).order_by(User.id).all():
        profile=PersonProfile.query.filter_by(account_user_id=child.id).order_by(PersonProfile.id).first()
        successor=remaining_owner(profile.id,user.id,transfers,removed) if profile else None
        child_plans.append(dict(id=child.id,name=child.name,profile_id=profile.id if profile else None,
            successor_id=successor.id if successor else None,successor_name=successor.name if successor else None))
    own_profiles=[p.id for p in PersonProfile.query.filter_by(account_user_id=user.id).order_by(PersonProfile.id).all()]
    public=dict(families=families,children=child_plans)
    signature=hashlib.sha256(json.dumps(dict(preview=public,snapshot=snapshot,own_profiles=own_profiles,session_version=user.session_version),sort_keys=True,default=str).encode()).hexdigest()
    return public,signature,transfers,removed,own_profiles


def cleanup_uploads(paths):
    root=Path(current_app.config['UPLOAD_FOLDER']).resolve()
    for path in set(paths):
        if not path or not path.startswith('/api/uploads/'):
            continue
        filename=path.removeprefix('/api/uploads/')
        target=(root/filename).resolve()
        if target.parent != root:
            continue
        if PersonProfile.query.filter_by(photo_path=path).first() or Household.query.filter_by(photo_path=path).first() or User.query.filter_by(theme_image_path=path).first() or WishlistItem.query.filter_by(image_path=path).first() or PrivateGift.query.filter_by(image_url=path).first() or SharedAvatar.query.filter_by(image_path=path).first() or any((theme.data or {}).get('image_path') == path for theme in SharedTheme.query.all()):
            continue
        try:
            target.unlink(missing_ok=True)
        except OSError:
            current_app.logger.warning('Could not remove an unused account upload.')


@api.get('/auth/account-deletion')
@authenticated
def account_deletion_preview():
    user=request.current_user
    if user.is_child or user.is_support:
        return error('Use an adult family account to manage account deletion.',403)
    preview,signature,_,_,_=deletion_plan(user)
    token=secrets.token_urlsafe(32)
    session['account_deletion_preview']=dict(token=token,signature=signature,expires=time.time()+600)
    from .invitation_mail import mail_configured
    from .email_preferences import suppressed, preference_link
    paused=suppressed(user.email)
    return jsonify(**preview,confirmation_token=token,backup_email=user.email,backup_available=mail_configured() and not paused,
                   backup_email_paused=paused,backup_preferences_url=preference_link(user.email) if paused else None)


@api.delete('/auth/account')
@authenticated
@limiter.limit('5 per hour')
def delete_my_account():
    user=request.current_user
    if user.is_child or user.is_support:
        return error('Use an adult family account to manage account deletion.',403)
    payload=request.get_json(silent=True) or {}
    saved=session.get('account_deletion_preview') or {}
    token=payload.get('confirmation_token')
    if payload.get('confirm') is not True or not isinstance(token,str) or not saved.get('token') or not secrets.compare_digest(token,saved['token']) or saved.get('expires',0)<time.time():
        return error('Review account deletion before confirming.',409)
    # Refresh the locked account before reauthentication, including its session version.
    user=User.query.filter_by(id=user.id).populate_existing().with_for_update().first()
    if not user or session.get('auth_version',0) != user.session_version:
        db.session.rollback()
        session.clear()
        return error('Your session has expired. Please sign in again.',401)
    password=payload.get('password')
    if not isinstance(password,str) or not user.check_password(password):
        return error('Enter your current account password.',403)
    # Lock ownership and its eligible successors before checking the preview again.
    homes=Household.query.filter_by(owner_id=user.id).order_by(Household.id).populate_existing().with_for_update().all()
    home_ids=[h.id for h in homes]
    HouseholdMembership.query.filter(HouseholdMembership.household_id.in_(home_ids)).order_by(HouseholdMembership.id).populate_existing().with_for_update().all()
    HouseholdProfileAccess.query.filter(HouseholdProfileAccess.household_id.in_(home_ids)).order_by(HouseholdProfileAccess.id).populate_existing().with_for_update().all()
    PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id.in_(home_ids)).order_by(PersonProfile.id).populate_existing().with_for_update().all()
    preview,signature,transfers,removed,own_profiles=deletion_plan(user)
    if not secrets.compare_digest(signature,saved['signature']):
        db.session.rollback()
        session.pop('account_deletion_preview',None)
        return error('Family membership changed. Review account deletion again.',409)
    from .deletion_backup import build_csv, send_backup
    backup_email=user.email
    backup_delivery=send_backup(backup_email,build_csv(user))
    if not backup_delivery:
        db.session.rollback()
        return error("We couldn't email your CSV backup. Your account has not been deleted. Please try again.",503)
    uid=user.id
    paths=[user.theme_image_path]
    affected_profiles={r.profile_id for r in HouseholdProfileAccess.query.filter(HouseholdProfileAccess.household_id.in_(removed)).all()}
    for home in homes:
        if home.id not in transfers:
            paths.append(home.photo_path)
            continue
        successor_id=transfers[home.id]
        home.owner_id=successor_id
        member=HouseholdMembership.query.filter_by(household_id=home.id,user_id=successor_id).one()
        member.role='owner';member.is_family_member=True;member.share_all_profiles=True;member.inherited_from_household_id=None
        for profile in PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id==home.id,PersonProfile.account_user_id==successor_id).all():
            profile.is_guardian=True
        for letter in WishlistLetter.query.filter_by(household_id=home.id,created_by_id=uid).all():
            letter.created_by_id=successor_id
        for game in GiftExchangeGame.query.filter_by(household_id=home.id,created_by_id=uid).all():
            game.created_by_id=successor_id
        record_audit(uid,'family.ownership_transferred','household',home.id,home.id,dict(previous_owner_id=uid,new_owner_id=successor_id))
    removed_child_ids=[]
    for row in preview['children']:
        child=db.session.get(User,row['id'])
        if row['successor_id']:
            child.parent_user_id=row['successor_id']
            child.session_version+=1
        else:
            paths.append(child.theme_image_path)
            removed_child_ids.append(child.id)
            if row['profile_id']:
                affected_profiles.add(row['profile_id'])
    db.session.flush()  # Persist transfers before any cascading delete.
    if removed:
        # Retain only a one-way payment receipt hash, never family or buyer data.
        # A retried event for an already delivered design must not trigger a refund.
        from .letter_art import remember_fulfilled
        from .models import LetterArtPurchase
        for purchase in LetterArtPurchase.query.filter(LetterArtPurchase.household_id.in_(removed), LetterArtPurchase.paid.is_(True)).with_for_update().all():
            remember_fulfilled(purchase.stripe_session_id)
        db.session.flush()
        db.session.execute(delete(Household).where(Household.id.in_(removed)),execution_options={'synchronize_session':False})
    delete_profiles=set(own_profiles)
    for pid in affected_profiles:
        profile=db.session.get(PersonProfile,pid)
        if not profile or HouseholdProfileAccess.query.filter_by(profile_id=pid).first():
            continue
        account=db.session.get(User,profile.account_user_id) if profile.account_user_id else None
        if not account or account.id in removed_child_ids:
            delete_profiles.add(pid)
    paths += [p.photo_path for p in PersonProfile.query.filter(PersonProfile.id.in_(delete_profiles)).all()]
    # Remove private personal-wish items, not merely their audience records.
    private_ids=[r.item_id for r in PersonalWish.query.filter_by(owner_id=uid).all()]
    deleted_item_ids = set(private_ids) | {item.id for item in WishlistItem.query.filter(WishlistItem.profile_id.in_(delete_profiles)).all()}
    paths += [item.image_path for item in WishlistItem.query.filter(WishlistItem.id.in_(deleted_item_ids)).all()]
    paths += [gift.image_url for gift in PrivateGift.query.filter(PrivateGift.user_id.in_([uid] + removed_child_ids)).all()]
    if private_ids:
        db.session.execute(delete(WishlistItem).where(WishlistItem.id.in_(private_ids)),execution_options={'synchronize_session':False})
    if delete_profiles:
        db.session.execute(delete(PersonProfile).where(PersonProfile.id.in_(delete_profiles)),execution_options={'synchronize_session':False})
    if removed_child_ids:
        db.session.execute(delete(User).where(User.id.in_(removed_child_ids)),execution_options={'synchronize_session':False})
    record_audit(uid,'account.deleted','user',uid,details=dict(transferred_households=sorted(transfers),deleted_households=removed))
    db.session.flush()
    db.session.execute(delete(User).where(User.id==uid),execution_options={'synchronize_session':False})
    db.session.commit()
    session.clear()
    try:
        cleanup_uploads(paths)
    except Exception:
        db.session.rollback()
        current_app.logger.warning('Account deleted; unused-upload cleanup could not finish.')
    return jsonify(status='deleted',backup_delivery=backup_delivery,backup_email=backup_email,family_transferred=bool(transfers))
