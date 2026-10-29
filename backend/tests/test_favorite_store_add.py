from backend.tests.test_reservation_privacy import register, mutate


def test_add_store_preserves_favorites_deduplicates_and_updates_completion(app):
    owner, stranger = app.test_client(), app.test_client()
    register(owner, 'Alex', 'store-owner@example.com')
    register(stranger, 'Other', 'store-other@example.com')
    home = mutate(owner, 'POST', '/api/households', {'name': 'Family', 'self_profile_index': 'new', 'profiles': []}).json['household']
    profile = owner.get(f"/api/households/{home['id']}").json['profiles'][0]
    path = f"/api/profiles/{profile['id']}/favorite-stores"
    before = owner.get(f"/api/profiles/{profile['id']}").json['profile']['completion']['percent']
    added = mutate(owner, 'POST', path, {'store': 'Target'})
    assert added.status_code == 200, added.json
    assert added.json['favorite_stores'] == ['Target']
    assert added.json['completion']['percent'] > before
    assert mutate(owner, 'POST', path, {'store': ' target '}).json['favorite_stores'] == ['Target']
    assert mutate(owner, 'POST', path, {'store': 'Local shop'}).json['favorite_stores'] == ['Target', 'Local shop']
    assert mutate(stranger, 'POST', path, {'store': 'No'}).status_code == 403
    assert mutate(owner, 'POST', path, {'store': ''}).status_code == 400
    assert mutate(owner, 'PATCH', f"/api/profiles/{profile['id']}", {'favorite_stores': ['None']}).status_code == 200
    assert mutate(owner, 'POST', path, {'store': 'Target'}).json['favorite_stores'] == ['Target']
