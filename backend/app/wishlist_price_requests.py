"""Follower requests for more wishes, separate from notification read state."""
import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from flask import request, jsonify
from .api import api, authenticated, error, profile_access, list_is_shared, list_family_access
from .extensions import db, limiter
from .models import User, Household, HouseholdProfileAccess, Wishlist, WishlistItem, WishlistItemWishlist


def visible_items(profile_id, wishlist_id, viewer):
    lists = Wishlist.query.filter_by(profile_id=profile_id).all()
    ids = [row.id for row in lists if (not wishlist_id or row.id == wishlist_id)
           and (list_is_shared(row) or list_family_access(row, viewer))]
    return WishlistItem.query.join(WishlistItemWishlist).filter(WishlistItemWishlist.wishlist_id.in_(ids)).distinct().all() if ids else []


def matches(item, row):
    return (item.estimated_price is not None and item.currency == row['currency']
            and Decimal(row['minimum']) <= item.estimated_price <= Decimal(row['maximum']))


def price_request_notifications(user):
    rows = []
    for saved in (user.notification_preferences or {}).get('wishlist_price_requests', []):
        profile = profile_access(user, saved['profile_id'], write=True)
        sender = db.session.get(User, saved['sender_id'])
        if not profile or not sender or profile_access(sender, profile.id) is None:
            continue
        if any(item.id not in saved['existing_item_ids'] and matches(item, saved)
               for item in visible_items(profile.id, saved.get('wishlist_id'), sender)):
            continue
        rows.append(dict(id=saved['id'], price_request=True, profile_id=profile.id,
                         wishlist_id=saved.get('wishlist_id'), minimum=saved['minimum'], maximum=saved['maximum'], currency=saved['currency'],
                         message=f"{sender.name} asked for more wishes for {profile.display_name} in {saved['currency']} {saved['minimum']}–{saved['maximum']}.",
                         household_name='Wishlist request', read=False, created_at=saved['created_at'],
                         url=f"/profiles/{profile.id}"+(f"?wishlist={saved['wishlist_id']}" if saved.get('wishlist_id') else '')))
    return rows


@api.post('/profiles/<int:profile_id>/price-requests')
@authenticated
@limiter.limit('10 per hour')
def request_price_range(profile_id):
    sender = request.current_user
    profile = profile_access(sender, profile_id)
    if sender.is_child or sender.is_support or profile is None:
        return error('Choose a shared profile you follow.', 403)
    recipient = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
    if recipient and recipient.is_child:
        recipient = db.session.get(User, recipient.parent_user_id)
    if recipient is None:
        home = Household.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.profile_id == profile.id, Household.registry_type == 'family').order_by(Household.id).first()
        recipient = db.session.get(User, home.owner_id) if home else None
    if not recipient or recipient.id == sender.id or recipient.is_support or profile_access(recipient, profile.id, write=True) is None:
        return error('This profile cannot receive a request.', 403)
    from .adult_family import followed_ids
    if recipient.id not in followed_ids(sender):
        return error('Follow this person or family before requesting more wishes.', 403)
    payload = request.get_json(silent=True) or {}
    try:
        low, high = Decimal(str(payload.get('minimum'))), Decimal(str(payload.get('maximum')))
        if not low.is_finite() or not high.is_finite() or not 0 <= low <= high <= 99999999 or any(value != value.quantize(Decimal('.01')) for value in (low, high)):
            raise ValueError()
    except (ValueError, InvalidOperation, TypeError):
        return error('Choose a valid minimum and maximum price.', 400)
    currency = payload.get('currency', 'USD')
    if currency not in ('USD','CAD','EUR','GBP','AUD','NZD','JPY','INR'):
        return error('Choose a supported currency.', 400)
    list_id = payload.get('wishlist_id')
    if list_id is not None:
        row = db.session.get(Wishlist, list_id) if type(list_id) is int else None
        if not row or row.profile_id != profile.id or not (list_is_shared(row) or list_family_access(row, sender)):
            return error('Choose a shared wishlist for this profile.', 400)
    recipient = User.query.filter_by(id=recipient.id).populate_existing().with_for_update().one()
    preferences = dict(recipient.notification_preferences or {})
    saved = list(preferences.get('wishlist_price_requests', []))
    active_ids = {row['id'] for row in price_request_notifications(recipient)}
    if any(row['id'] in active_ids and row['sender_id']==sender.id and row['profile_id']==profile.id and row.get('wishlist_id')==list_id and row['minimum']==format(low,'.2f') and row['maximum']==format(high,'.2f') and row['currency']==currency and row['id'] not in preferences.get('dismissed_notification_ids', []) for row in saved):
        return error('You already sent this request.', 409)
    saved.append(dict(id='price-request-'+secrets.token_hex(12), sender_id=sender.id, profile_id=profile.id,
                      wishlist_id=list_id, minimum=format(low,'.2f'), maximum=format(high,'.2f'), currency=currency,
                      existing_item_ids=[item.id for item in visible_items(profile.id, list_id, sender)],
                      created_at=datetime.now(timezone.utc).isoformat()))
    preferences['wishlist_price_requests'] = saved[-100:]
    recipient.notification_preferences = preferences
    db.session.commit()
    return jsonify(message='Request sent. They can add wishes in this price range or ignore the request.'), 201


@api.post('/notifications/state')
@authenticated
def notification_state():
    from .api import list_notifications
    payload = request.get_json(silent=True) or {}
    identifier, action = str(payload.get('id', '')), payload.get('action')
    if action not in ('read', 'dismiss'):
        return error('Choose read or dismiss.', 400)
    visible = list_notifications.__wrapped__().get_json()
    if not any(str(row['id']) == identifier for row in visible['notifications']+visible['profile_reminders']):
        return error('Notification not found.', 404)
    preferences = dict(request.current_user.notification_preferences or {})
    key = 'read_notification_ids' if action == 'read' else 'dismissed_notification_ids'
    ids = set(preferences.get(key, [])); ids.add(identifier)
    preferences[key] = sorted(ids)
    request.current_user.notification_preferences = preferences
    db.session.commit()
    return jsonify(status=action)
