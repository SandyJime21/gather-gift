"""Explicit list setup for tests that need gifts rather than an empty profile."""
from backend.tests.test_reservation_privacy import mutate


def create_test_wishlist(client, path):
    existing = client.get(path).get_json().get('wishlists', [])
    if existing:
        return existing[0]
    response = mutate(client, 'POST', path, {'title': 'Test wishes'})
    assert response.status_code == 201, response.get_json()
    wishlist = response.get_json()['wishlist']
    # These existing tests exercise profile/item sharing rather than explicit list privacy.
    from backend.app.extensions import db
    from backend.app.models import Wishlist
    with client.application.app_context():
        db.session.get(Wishlist, wishlist['id']).share_publicly = None
        db.session.commit()
    return wishlist
