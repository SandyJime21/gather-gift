from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import User, HouseholdMembership


def test_hearts_are_private_and_do_not_reserve_gifts(app):
    owner, shopper, other = [app.test_client() for _ in range(3)]
    register(owner, 'Parent', 'wishparent@example.com')
    user = register(shopper, 'Shopper', 'wishshopper@example.com')
    register(other, 'Other', 'wishother@example.com')
    household = mutate(owner, 'POST', '/api/households', {'name': 'Family', 'profiles': [{'display_name': 'Child'}]}).json['household']
    profile = owner.get(f"/api/households/{household['id']}").json['profiles'][0]
    occasion = mutate(owner, 'POST', f"/api/households/{household['id']}/occasions", {'profile_id': profile['id'], 'type': 'birthday', 'name': 'Birthday', 'date': '2027-06-01'})
    assert occasion.status_code == 201
    wishlist = owner.get(f"/api/profiles/{profile['id']}/wishlists").json['wishlists'][-1]
    gift = mutate(owner, 'POST', f"/api/wishlists/{wishlist['id']}/items", {'name': 'Gift', 'image_url': 'https://example.com/gift.jpg'}).json['item']
    with app.app_context():
        db.session.add(HouseholdMembership(household_id=household['id'], user_id=user['id'], role='admin'))
        db.session.commit()
    path = f"/api/items/{gift['id']}/heart"
    assert mutate(other, 'PUT', path).status_code == 404
    assert mutate(shopper, 'PUT', path).status_code == 200
    assert mutate(shopper, 'PUT', path).status_code == 200
    saved = shopper.get('/api/wishlist').json['hearted']
    assert len(saved) == 1 and saved[0]['availability']['available'] == 1
    assert saved[0]['recipient'] == 'Child'
    assert saved[0]['households'][0]['name'] == 'Family'
    assert saved[0]['occasions'] == ['Birthday']
    assert saved[0]['added_by'] == 'Parent'
    assert owner.get('/api/wishlist').json['hearted'] == []
    assert mutate(shopper, 'DELETE', path).status_code == 200
    assert shopper.get('/api/wishlist').json['hearted'] == []
    # Children are profiles, not user accounts.
    with app.app_context():
        assert User.query.count() == 3


def test_personal_gifts_remain_private_to_creator(app):
    me, recipient = app.test_client(), app.test_client()
    register(me, 'Me', 'privateowner@example.com')
    register(recipient, 'Mom', 'privatemom@example.com')
    created = mutate(me, 'POST', '/api/private-gifts', {'name': 'Something Mom asked for', 'recipient': 'Mom', 'household_name': 'Mom family', 'occasion': 'Christmas', 'estimated_price': '30', 'product_url': 'https://example.com/item'})
    assert created.status_code == 201
    gift = created.json['gift']
    assert len(me.get('/api/wishlist').json['private_gifts']) == 1
    assert recipient.get('/api/wishlist').json['private_gifts'] == []
    path = f"/api/private-gifts/{gift['id']}"
    assert mutate(recipient, 'PATCH', path, {'status': 'purchased'}).status_code == 404
    assert mutate(recipient, 'DELETE', path).status_code == 404
    assert mutate(me, 'PATCH', path, {'status': 'purchased'}).json['gift']['status'] == 'purchased'
    assert mutate(me, 'PATCH', path, {'status': 'planned'}).status_code == 200
    assert mutate(me, 'POST', '/api/private-gifts', {'name': 'Gift', 'recipient': 'Mom', 'product_url': 'javascript:alert(1)'}).status_code == 400
    assert mutate(me, 'DELETE', path).status_code == 200
    assert me.get('/api/wishlist').json['private_gifts'] == []
