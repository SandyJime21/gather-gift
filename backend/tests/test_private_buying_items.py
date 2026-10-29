from backend.tests.test_reservation_privacy import register, mutate


def test_private_buying_saved_and_purchased_are_separate_and_owned(app):
    owner, stranger = app.test_client(), app.test_client()
    register(owner, 'Alex', 'private-bag@example.com')
    register(stranger, 'Other', 'private-bag-other@example.com')
    created = mutate(owner, 'POST', '/api/private-gifts', dict(name='Puzzle',recipient='Alex',buying_now=True))
    assert created.status_code == 201, created.json
    gift = created.json['gift']
    assert gift['buying_now'] is True
    assert owner.get('/api/wishlist').json['private_gifts'][0]['buying_now'] is True
    assert stranger.get('/api/wishlist').json['private_gifts'] == []
    path = f"/api/private-gifts/{gift['id']}"
    assert mutate(stranger, 'PATCH', path, {'buying_now': False}).status_code == 404
    assert mutate(owner, 'PATCH', path, {'buying_now': 'yes'}).status_code == 400
    saved = mutate(owner, 'PATCH', path, {'buying_now': False}).json['gift']
    assert saved['status'] == 'planned' and saved['buying_now'] is False
    assert mutate(owner, 'PATCH', path, {'buying_now': True}).json['gift']['buying_now'] is True
    purchased = mutate(owner, 'PATCH', path, {'status': 'purchased'}).json['gift']
    assert purchased['status'] == 'purchased' and purchased['buying_now'] is False
