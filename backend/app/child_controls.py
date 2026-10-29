"""Parent-owned, default-deny permissions for optional child activities."""
import secrets
from flask import jsonify, request
from .api import api, authenticated, error, profile_access
from .extensions import db
from .models import PersonProfile, User, Wishlist, ChildWishlistAccess, Household, HouseholdProfileAccess

CONTROL_KEYS = ('web_search', 'product_links', 'manage_pets', 'switch_siblings', 'game_invites')


def controls_for(child):
    parent = db.session.get(User, child.parent_user_id) if child and child.is_child else None
    saved = ((parent.notification_preferences or {}).get('child_access', {}).get(str(child.id), {}) if parent else {})
    return {key: saved.get(key) is True for key in CONTROL_KEYS}


@api.route('/profiles/<int:profile_id>/child-controls', methods=['GET', 'PATCH'])
@authenticated
def parent_child_controls(profile_id):
    parent = request.current_user
    profile = PersonProfile.query.filter_by(id=profile_id).populate_existing().with_for_update().first() if request.method == 'PATCH' else db.session.get(PersonProfile, profile_id)
    if (parent.is_child or parent.is_support or not profile or profile.profile_type != 'person'
            or profile.is_adult or not profile_access(parent, profile_id, write=True)):
        return error('Child controls are not available.', 403)
    if not Household.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.profile_id==profile_id,
            Household.registry_type=='family',Household.owner_id==parent.id).first():
        return error('Child mode is managed by the family creator.',403)
    child = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
    if child and (not child.is_child or child.parent_user_id != parent.id):
        return error('Only the supervising parent can manage child access.',403)
    lists=Wishlist.query.filter_by(profile_id=profile.id).order_by(Wishlist.is_everyday.desc(),Wishlist.id).all()
    from .api import empty_legacy_default_list
    lists=[row for row in lists if not empty_legacy_default_list(row)]
    if request.method == 'PATCH':
        payload = request.get_json(silent=True) or {}
        switches=set(CONTROL_KEYS)|{'enabled'}
        if not payload or set(payload) - (switches|{'wishlist_ids'}) or any(type(value) is not bool for key,value in payload.items() if key in switches):
            return error('Choose valid child access switches.', 400)
        ids=payload.get('wishlist_ids')
        enabled=payload.get('enabled',child.child_enabled if child else False)
        if ids is not None and (not isinstance(ids,list) or any(type(value) is not int for value in ids) or set(ids)-{row.id for row in lists}):
            return error('Choose wishlists belonging to this child only.',400)
        approved=[row.wishlist_id for row in ChildWishlistAccess.query.filter_by(user_id=child.id).all()] if child else [lists[0].id] if lists else []
        if enabled and not (ids if ids is not None else approved):
            return error('Choose at least one wishlist for child mode.',400)
        if enabled and (not child or not child.child_enabled or 'enabled' in payload) and not parent.parent_pin_hash:
            return error('Set your parent PIN before enabling child mode.',400)
        if not child:
            username='wish-'+secrets.token_hex(5)
            child=User(name=profile.display_name,email=username+'@child.accounts.invalid',is_child=True,
                       child_username=username,parent_user_id=parent.id,child_enabled=enabled)
            child.set_password(secrets.token_urlsafe(48))
            db.session.add(child);db.session.flush();profile.account_user_id=child.id
            if ids is None:ids=approved
        child.child_enabled=enabled
        if ids is not None:
            ChildWishlistAccess.query.filter_by(user_id=child.id).delete()
            for wishlist_id in set(ids):db.session.add(ChildWishlistAccess(user_id=child.id,wishlist_id=wishlist_id))
        preferences = dict(parent.notification_preferences or {})
        access = dict(preferences.get('child_access', {}))
        access[str(child.id)] = {**access.get(str(child.id),{}),**controls_for(child),**{key:value for key,value in payload.items() if key in CONTROL_KEYS}}
        if ids is not None:access[str(child.id)]['lists_configured']=True
        preferences['child_access'] = access
        parent.notification_preferences = preferences
        if 'wishlist_ids' in payload or 'enabled' in payload:child.session_version+=1
        db.session.commit()
    approved=[row.wishlist_id for row in ChildWishlistAccess.query.filter_by(user_id=child.id).all()] if child else [lists[0].id] if lists else []
    configured=((parent.notification_preferences or {}).get('child_access',{}).get(str(child.id),{})).get('lists_configured',False) if child else False
    if not configured:
        from .wishlist_letters import active_letters
        approved=list(dict.fromkeys(approved+[row.wishlist_id for row in active_letters(profile.id)]))
    return jsonify(controls=controls_for(child),available=bool(child),enabled=bool(child and child.child_enabled),
        has_parent_pin=bool(parent.parent_pin_hash),wishlist_ids=approved,
        wishlists=[{'id':row.id,'title':row.title} for row in lists])
