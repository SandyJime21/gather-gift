from backend.tests.test_wishlist_price_requests import setup_request
from backend.tests.test_reservation_privacy import mutate


def test_empty_lists_are_hidden_from_followers_but_remain_manageable(app):
    owner, follower, _, profile, wishlist = setup_request(app)
    path = f"/api/profiles/{profile['id']}/wishlists"
    assert wishlist['id'] in {row['id'] for row in owner.get(path).json['wishlists']}
    assert follower.get(path).json['wishlists'] == []
    extra = mutate(owner, 'POST', path, {'title': 'Empty Christmas'}).json['wishlist']
    assert mutate(owner, 'PATCH', f"/api/wishlists/{extra['id']}", {'share_publicly': True}).status_code == 200
    item = mutate(owner, 'POST', f"/api/wishlists/{wishlist['id']}/items", {'name': 'Puzzle'}).json['item']
    assert [row['id'] for row in follower.get(path).json['wishlists']] == [wishlist['id']]
    assert {row['id'] for row in owner.get(path).json['wishlists']} >= {wishlist['id'], extra['id']}
    assert mutate(owner, 'DELETE', f"/api/items/{item['id']}", {}).status_code == 200
    assert follower.get(path).json['wishlists'] == []


def test_a_filled_private_list_is_still_hidden_from_followers(app):
    owner, follower, _, profile, wishlist = setup_request(app)
    assert mutate(owner, 'POST', f"/api/wishlists/{wishlist['id']}/items", {'name': 'Private puzzle'}).status_code == 201
    assert mutate(owner, 'PATCH', f"/api/wishlists/{wishlist['id']}", {'share_publicly': False}).status_code == 200
    assert follower.get(f"/api/profiles/{profile['id']}/wishlists").json['wishlists'] == []
