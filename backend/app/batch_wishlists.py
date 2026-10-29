"""Create matching, independently owned lists in one transaction."""
import secrets
from flask import request, jsonify
from .api import api, authenticated, error, profile_access
from .extensions import db
from .models import Wishlist, User, Household, HouseholdProfileAccess, ChildWishlistAccess


@api.post('/wishlists/batch')
@authenticated
def create_family_lists():
    parent = request.current_user
    if parent.is_child or parent.is_support:
        return error('Only family accounts can create these lists.', 403)
    payload = request.get_json(silent=True) or {}
    title, ids = payload.get('title'), payload.get('profile_ids')
    source_id = payload.get('source_wishlist_id')
    if source_id is not None:
        source = db.session.get(Wishlist, source_id) if type(source_id) is int else None
        if not source or profile_access(parent, source.profile_id, write=True) is None:
            return error('Choose a source list you manage.', 403)
        title = source.title
    allow = payload.get('allow_child_items', False)
    if (not isinstance(title, str) or not 1 <= len(title.strip()) <= 160
            or not isinstance(ids, list) or not 1 <= len(ids) <= 50
            or any(type(value) is not int for value in ids) or type(allow) is not bool):
        return error('Enter a list name and choose family members.', 400)
    profiles = [profile_access(parent, pid, write=True) for pid in dict.fromkeys(ids)]
    if any(profile is None for profile in profiles):
        return error('You can only create lists for profiles you manage.', 403)
    # Validate every child before writing any lists or permissions.
    children = {}
    for profile in profiles:
        if not allow or profile.profile_type != 'person' or profile.is_adult:
            continue
        home = Household.query.join(HouseholdProfileAccess).filter(
            HouseholdProfileAccess.profile_id == profile.id,
            Household.registry_type == 'family', Household.owner_id == parent.id).first()
        child = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
        if not home or (child and (not child.is_child or child.parent_user_id != parent.id)):
            return error('Only the supervising family creator can approve child access.', 403)
        children[profile.id] = child
    created = []
    for profile in profiles:
        if source_id is not None:
            existing = next((row for row in Wishlist.query.filter_by(profile_id=profile.id).with_for_update().all()
                             if row.title.strip().casefold() == title.strip().casefold()), None)
            if existing:
                created.append(dict(id=existing.id, profile_id=profile.id, title=existing.title,
                                    name=profile.display_name, already_exists=True))
                continue
        wishlist = Wishlist(profile_id=profile.id, title=title.strip(), share_publicly=False)
        db.session.add(wishlist)
        db.session.flush()
        if profile.id in children:
            child = children[profile.id]
            if child is None:
                username = 'wish-' + secrets.token_hex(5)
                child = User(name=profile.display_name, email=username+'@child.accounts.invalid',
                             is_child=True, child_username=username, parent_user_id=parent.id,
                             child_enabled=False)
                child.set_password(secrets.token_urlsafe(48))
                db.session.add(child)
                db.session.flush()
                profile.account_user_id = child.id
            db.session.add(ChildWishlistAccess(user_id=child.id, wishlist_id=wishlist.id))
            preferences = dict(parent.notification_preferences or {})
            access = dict(preferences.get('child_access', {}))
            access[str(child.id)] = {**access.get(str(child.id), {}), 'lists_configured': True}
            parent.notification_preferences = {**preferences, 'child_access': access}
        created.append(dict(id=wishlist.id, profile_id=profile.id, title=wishlist.title,
                            name=profile.display_name))
    db.session.commit()
    return jsonify(wishlists=created), 201
