from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import User, HouseholdMembership


def child_setup(app):
    parent, child, stranger = [app.test_client() for _ in range(3)]
    register(parent, 'Parent', 'childparent@example.com')
    register(stranger, 'Stranger', 'childstranger@example.com')
    home = mutate(parent, 'POST', '/api/households', {'name': 'Family', 'profiles': [{'display_name': 'Mia'}, {'display_name': 'Sam'}]}).json['household']
    profiles = parent.get(f"/api/households/{home['id']}").json['profiles']
    lists = [parent.get(f"/api/profiles/{person['id']}/wishlists").json['wishlists'][0] for person in profiles]
    path = f"/api/households/{home['id']}/child-accounts"
    created = mutate(parent, 'POST', path, {'profile_id': profiles[0]['id'], 'wishlist_ids': [lists[0]['id']], 'password': 'child-test-password'})
    assert created.status_code == 201, created.json
    account = created.json['child']
    assert mutate(child, 'POST', '/api/child/login', {'username': account['username'], 'password': 'child-test-password'}).status_code == 200
    return parent, child, stranger, home, profiles, lists, path, account


def test_child_can_only_view_approved_lists_and_add_gifts(app):
    parent, child, _, home, profiles, lists, path, account = child_setup(app)
    result = child.get('/api/child/me')
    assert result.status_code == 200
    assert [row['id'] for row in result.json['wishlists']] == [lists[0]['id']]
    added = mutate(child, 'POST', f"/api/child/wishlists/{lists[0]['id']}/items", {'name': 'A book', 'description': 'About dinosaurs'})
    assert added.status_code == 201
    item_id = added.json['item']['id']
    visible = child.get('/api/child/me').json['wishlists'][0]['items'][0]
    assert set(visible) == {'id', 'name', 'description'}
    assert mutate(child, 'POST', f"/api/child/wishlists/{lists[1]['id']}/items", {'name': 'Other person'}).status_code == 404
    assert mutate(child, 'POST', f"/api/child/wishlists/{lists[0]['id']}/items", {'name': 'Gift', 'product_url': 'https://example.com'}).status_code == 400
    for method, endpoint, payload in [
        ('GET', '/api/shopping', None), ('GET', '/api/gift-discovery?q=toys', None),
        ('GET', '/api/wishlist', None), ('GET', '/api/households/search?q=parent', None),
        ('GET', f"/api/households/{home['id']}", None), ('GET', '/api/notifications', None),
        ('GET', '/api/my-shopping', None), ('GET', '/api/uploads/any.jpg', None),
        ('PATCH', '/api/auth/profile', {'name': 'Changed'}), ('POST', '/api/auth/password', {}),
        ('POST', '/api/auth/register', {'name': 'Adult', 'email': 'adult@example.com', 'password': 'a-new-password'}),
        ('POST', f"/api/households/{home['id']}/invitations", {}),
        ('POST', f'/api/items/{item_id}/reservations', {}),
        ('PUT', f'/api/items/{item_id}/heart', {}),
        ('PATCH', f'/api/items/{item_id}', {'name': 'Changed'}),
        ('DELETE', f'/api/items/{item_id}', None),
        ('PATCH', f"/api/profiles/{profiles[0]['id']}", {'display_name': 'Changed'}),
    ]:
        response = child.get(endpoint) if method == 'GET' else mutate(child, method, endpoint, payload)
        assert response.status_code == 403, (method, endpoint, response.json)
    assert mutate(parent, 'PATCH', f'/api/items/{item_id}', {'name': 'Parent edited'}).status_code == 200
    assert child.get('/api/auth/me').json['households'] == []
    assert child.get('/api/auth/me').json['user']['email'] is None
    with app.app_context():
        assert HouseholdMembership.query.filter_by(user_id=account['id']).count() == 0
    assert mutate(child, 'POST', '/api/auth/logout').status_code == 200


def test_parent_can_change_lists_reset_password_and_disable_access(app):
    parent, child, stranger, _, profiles, lists, path, account = child_setup(app)
    target = path + f"/{account['id']}"
    assert stranger.get(path).status_code == 403
    assert mutate(stranger, 'PATCH', target, {'enabled': False}).status_code == 403
    assert mutate(parent, 'PATCH', target, {'wishlist_ids': [lists[1]['id']]}).status_code == 400
    extra = mutate(parent, 'POST', f"/api/profiles/{profiles[0]['id']}/wishlists", {'title': 'Christmas'}).json['wishlist']
    assert mutate(parent, 'PATCH', target, {'wishlist_ids': [extra['id']], 'password': 'new-child-password'}).status_code == 200
    assert child.get('/api/child/me').status_code == 401
    assert mutate(child, 'POST', '/api/child/login', {'username': account['username'], 'password': 'child-test-password'}).status_code == 401
    assert mutate(child, 'POST', '/api/child/login', {'username': account['username'], 'password': 'new-child-password'}).status_code == 200
    assert child.get('/api/child/me').json['wishlists'][0]['id'] == extra['id']
    assert mutate(parent, 'PATCH', target, {'enabled': False}).status_code == 200
    assert child.get('/api/child/me').status_code == 401
    assert mutate(child, 'POST', '/api/child/login', {'username': account['username'], 'password': 'new-child-password'}).status_code == 401


def test_child_link_import_is_limited_to_parent_approved_lists(app, monkeypatch):
    parent, child, _, home, profiles, lists, path, account = child_setup(app)
    from backend.tests.test_child_controls import allow_optional_features
    allow_optional_features(app)
    calls = []
    def preview(url):
        calls.append(url)
        return {'title': 'Dinosaur puzzle', 'store_name': 'Example', 'image_url': None}
    monkeypatch.setattr('backend.app.api.preview_link', preview)
    endpoint = f"/api/child/wishlists/{lists[0]['id']}/links"
    assert mutate(child, 'POST', f"/api/child/wishlists/{lists[1]['id']}/links", {'url': 'https://example.com/toy'}).status_code == 404
    assert not calls
    assert mutate(child, 'POST', endpoint, {'url': 'javascript:alert(1)'}).status_code == 400
    response = mutate(child, 'POST', endpoint, {'url': 'https://example.com/toy'})
    assert response.status_code == 201
    assert response.json['item']['name'] == 'Dinosaur puzzle'
    assert set(response.json['item']) == {'id', 'name', 'description'}
    assert calls == ['https://example.com/toy']
    assert mutate(child, 'DELETE', '/api/items/' + str(response.json['item']['id'])).status_code == 403


def test_parent_can_hide_child_wishes_from_invited_shoppers(app):
    parent, child, stranger, home, profiles, lists, path, account = child_setup(app)
    from backend.app.models import HouseholdMemberProfileAccess
    with app.app_context():
        shopper = User.query.filter_by(email='childstranger@example.com').one()
        membership = HouseholdMembership(household_id=home['id'], user_id=shopper.id, role='shopper')
        db.session.add(membership)
        db.session.flush()
        db.session.add(HouseholdMemberProfileAccess(membership_id=membership.id, profile_id=profiles[0]['id']))
        db.session.commit()
    added = mutate(child, 'POST', f"/api/child/wishlists/{lists[0]['id']}/items", {'name': 'Book'}).json['item']
    item_id = added['id']
    url = f"/api/wishlists/{lists[0]['id']}/items"
    assert stranger.get(url).json['items']
    assert mutate(parent, 'PATCH', f'/api/items/{item_id}', {'family_only': True}).status_code == 200
    assert not stranger.get(url).json['items']
    assert not stranger.get('/api/shopping').json['items']
    assert mutate(stranger, 'POST', f'/api/items/{item_id}/reservations', {'quantity': 1}).status_code == 404
    assert parent.get(url).json['items']
    assert child.get('/api/child/me').json['wishlists'][0]['items']
    assert mutate(child, 'PATCH', f'/api/items/{item_id}', {'family_only': False}).status_code == 403
    assert mutate(parent, 'PATCH', f'/api/items/{item_id}', {'family_only': False}).status_code == 200
    assert stranger.get(url).json['items']
    assert mutate(parent, 'DELETE', f'/api/items/{item_id}').status_code == 200

def test_child_gets_default_wish_space_without_parent_list_setup(app):
    parent, child, _, _, profiles, _, path, _ = child_setup(app)
    from backend.app.extensions import db
    from backend.app.models import ChildWishlistAccess
    with app.app_context():
        ChildWishlistAccess.query.delete()
        db.session.commit()
    result = child.get('/api/child/me')
    assert result.status_code == 200
    assert len(result.json['wishlists']) == 1
    wishlist_id = result.json['wishlists'][0]['id']
    added = mutate(child, 'POST', f'/api/child/wishlists/{wishlist_id}/items', {'name': 'Toy bear'})
    assert added.status_code == 201
    assert child.get('/api/child/me').json['wishlists'][0]['items'][0]['name'] == 'Toy bear'

def test_shared_household_child_mode_needs_no_list_or_login_setup(app):
    parent, _, _, _, profiles, _, _, _ = child_setup(app)
    from werkzeug.security import generate_password_hash
    with app.app_context():
        owner = User.query.filter_by(email='childparent@example.com').one()
        owner.parent_pin_hash = generate_password_hash('123456')
        db.session.commit()
    switched = mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': profiles[1]['id']})
    assert switched.status_code == 200, switched.json
    result = parent.get('/api/child/me')
    assert result.status_code == 200
    wishlist_id = result.json['wishlists'][0]['id']
    assert mutate(parent, 'POST', f'/api/child/wishlists/{wishlist_id}/items', {'name': 'Building set'}).status_code == 201
    assert mutate(parent, 'DELETE', '/api/items/1', None).status_code == 403

def test_child_search_saves_only_returned_products_to_own_list(app, monkeypatch):
    parent, child, _, _, _, lists, _, _ = child_setup(app)
    from backend.tests.test_child_controls import allow_optional_features
    allow_optional_features(app)
    app.config['SERPAPI_API_KEY'] = 'test-key'
    def search(query, child_safe=False):
        assert query == 'toy bear'
        assert child_safe is True
        return [{'name': 'Toy bear', 'product_url': 'https://example.com/bear', 'thumbnail': 'https://example.com/bear.jpg', 'estimated_price': '12.00', 'store_name': 'Toys'}]
    monkeypatch.setattr('backend.app.api.search_products', search)
    result = child.get('/api/child/gift-search?q=toy+bear')
    assert result.status_code == 200
    assert 'product_url' not in result.json['products'][0]
    path = f"/api/child/wishlists/{lists[0]['id']}/items"
    assert mutate(child, 'POST', path, {'product_index': 99}).status_code == 400
    assert mutate(child, 'POST', f"/api/child/wishlists/{lists[1]['id']}/items", {'product_index': 0}).status_code == 404
    assert mutate(child, 'POST', path, {'product_index': 0}).status_code == 201
    assert child.get('/api/child/me').json['wishlists'][0]['items'][0]['name'] == 'Toy bear'
