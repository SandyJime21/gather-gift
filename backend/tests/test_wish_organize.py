from backend.app.extensions import db
from backend.app.models import Household, HouseholdMembership, HouseholdProfileAccess, PersonProfile, Wishlist, WishlistItem, WishlistItemWishlist, GiftReservation
from backend.tests.test_reservation_privacy import register, mutate


def test_move_copy_received_and_permissions(app):
    client, outsider = app.test_client(), app.test_client()
    owner = register(client, 'Parent', 'organize@example.com')
    register(outsider, 'Other', 'other-organize@example.com')
    home = Household(name='Family', owner_id=owner['id'])
    db.session.add(home); db.session.flush()
    db.session.add(HouseholdMembership(household_id=home.id, user_id=owner['id'], role='owner'))
    profiles = [PersonProfile(display_name=name, is_adult=False) for name in ('Son', 'Daughter')]
    db.session.add_all(profiles); db.session.flush()
    lists = []
    for profile in profiles:
        db.session.add(HouseholdProfileAccess(household_id=home.id, profile_id=profile.id))
        wishlist = Wishlist(profile_id=profile.id, title='Birthday')
        db.session.add(wishlist); lists.append(wishlist)
    db.session.flush()
    item = WishlistItem(profile_id=profiles[0].id, name='Book', estimated_price=12, image_path='https://example.com/book.jpg')
    db.session.add(item); db.session.flush()
    db.session.add(WishlistItemWishlist(item_id=item.id, wishlist_id=lists[0].id)); db.session.commit()
    targets = client.get('/api/wish-edit-targets').json['profiles']
    assert {p['name'] for p in targets} >= {'Son', 'Daughter'}
    url = f'/api/items/{item.id}/organize'
    assert mutate(outsider, 'POST', url, {'action':'received'}).status_code == 403
    copied = mutate(client, 'POST', url, {'action':'copy', 'wishlist_id':lists[1].id})
    assert copied.status_code == 200, copied.json
    assert copied.json['item']['id'] != item.id
    assert copied.json['item']['profile_id'] == profiles[1].id
    assert copied.json['item']['family_only'] is True
    moved = mutate(client, 'POST', url, {'action':'move', 'wishlist_id':lists[1].id})
    assert moved.status_code == 200, moved.json
    assert moved.json['item']['profile_id'] == profiles[1].id
    assert WishlistItemWishlist.query.filter_by(item_id=item.id).one().wishlist_id == lists[1].id
    db.session.add(GiftReservation(item_id=item.id, shopper_id=owner['id'], status='reserved'))
    db.session.commit()
    assert mutate(client, 'POST', url, {'action':'move', 'wishlist_id':lists[0].id}).status_code == 409
    assert mutate(client, 'POST', url, {'action':'received'}).status_code == 200
    assert mutate(client, 'POST', url, {'action':'received'}).status_code == 200
    assert GiftReservation.query.filter_by(item_id=item.id, status='reserved').count() == 0
    assert GiftReservation.query.filter_by(item_id=item.id, status='purchased').count() == 1
