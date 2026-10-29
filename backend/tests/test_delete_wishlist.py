from sqlalchemy import text
from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import mutate
from backend.app.extensions import db
from backend.app.models import Wishlist, WishlistItem, WishlistItemWishlist, ChildWishlistAccess


def test_delete_list_preserves_other_lists_and_shared_items_and_revokes_child_access(app):
    with app.app_context():
        db.session.execute(text('PRAGMA foreign_keys=ON'));db.session.commit()
    parent, child, stranger, _, profiles, lists, _, account = child_setup(app)
    source = lists[0]
    other = mutate(parent, 'POST', f"/api/profiles/{profiles[0]['id']}/wishlists", {'title': 'Keep Christmas'}).json['wishlist']
    exclusive = mutate(parent, 'POST', f"/api/wishlists/{source['id']}/items", {'name': 'Only here'}).json['item']
    shared = mutate(parent, 'POST', f"/api/wishlists/{source['id']}/items", {'name': 'On two lists'}).json['item']
    with app.app_context():
        db.session.add(WishlistItemWishlist(item_id=shared['id'], wishlist_id=other['id']));db.session.commit()
    endpoint = f"/api/wishlists/{source['id']}"
    assert mutate(stranger, 'DELETE', endpoint).status_code == 404
    assert mutate(child, 'DELETE', endpoint).status_code == 403
    assert mutate(parent, 'DELETE', endpoint).status_code == 200
    with app.app_context():
        assert db.session.get(Wishlist, source['id']) is None
        assert db.session.get(Wishlist, other['id']) is not None
        assert db.session.get(WishlistItem, exclusive['id']) is None
        assert db.session.get(WishlistItem, shared['id']) is not None
        assert WishlistItemWishlist.query.filter_by(item_id=shared['id']).one().wishlist_id == other['id']
        assert ChildWishlistAccess.query.filter_by(wishlist_id=source['id']).count() == 0
    assert child.get('/api/child/me').status_code == 401
    assert mutate(child, 'POST', '/api/child/login', {'username': account['username'], 'password': 'child-test-password'}).status_code == 200
    assert child.get('/api/child/me').json['wishlists'] == []
    assert mutate(parent, 'DELETE', endpoint).status_code == 404


def test_can_delete_an_empty_list_without_recreating_a_default(app):
    parent, _, _, _, profiles, _, _, _ = child_setup(app)
    response = mutate(parent, 'POST', f"/api/profiles/{profiles[0]['id']}/wishlists", {'title': 'Remove empty list'})
    list_id = response.json['wishlist']['id']
    assert mutate(parent, 'DELETE', f'/api/wishlists/{list_id}').status_code == 200
    assert all(row['id'] != list_id for row in parent.get(f"/api/profiles/{profiles[0]['id']}/wishlists").json['wishlists'])
