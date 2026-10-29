from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import Wishlist, PersonProfile


def test_new_people_and_pets_start_without_default_lists(app):
    owner = app.test_client()
    register(owner, 'Parent', 'no-default@example.com')
    result = mutate(owner, 'POST', '/api/households', {'name': 'Family', 'profiles': [
        {'display_name': 'Mia'}, {'display_name': 'Pretzel', 'profile_type': 'pet'}]})
    home = result.json['household']
    profiles = owner.get(f"/api/households/{home['id']}").json['profiles']
    for profile in profiles:
        assert owner.get(f"/api/profiles/{profile['id']}/wishlists").json['wishlists'] == []
    kid = next(row for row in profiles if row['display_name'] == 'Mia')
    controls = owner.get(f"/api/profiles/{kid['id']}/child-controls").json
    assert controls['wishlists'] == []
    assert mutate(owner, 'POST', '/api/household-session/pin', {'pin': '123456', 'password': 'a-long-test-password'}).status_code == 200
    assert mutate(owner, 'POST', '/api/household-session/switch', {'profile_id': kid['id']}).status_code == 400
    with app.app_context():
        assert Wishlist.query.count() == 0
        assert db.session.get(PersonProfile, kid['id']).account_user_id is None
    created = mutate(owner, 'POST', f"/api/profiles/{kid['id']}/wishlists", {'title': 'Christmas'})
    assert created.status_code == 201
    assert [row['title'] for row in owner.get(f"/api/profiles/{kid['id']}/wishlists").json['wishlists']] == ['Christmas']


def test_empty_legacy_default_is_hidden_but_existing_gifts_are_preserved(app):
    owner = app.test_client()
    register(owner, 'Parent', 'legacy-default@example.com')
    home = mutate(owner, 'POST', '/api/households', {'name': 'Family', 'profiles': [{'display_name': 'Mia'}]}).json['household']
    profile = owner.get(f"/api/households/{home['id']}").json['profiles'][0]
    with app.app_context():
        legacy = Wishlist(profile_id=profile['id'], title='Everyday Wants & Needs', is_everyday=True)
        db.session.add(legacy); db.session.commit(); list_id=legacy.id
    path = f"/api/profiles/{profile['id']}/wishlists"
    assert owner.get(path).json['wishlists'] == []
    assert mutate(owner, 'POST', f'/api/wishlists/{list_id}/items', {'name': 'Keep this gift'}).status_code == 201
    assert [row['id'] for row in owner.get(path).json['wishlists']] == [list_id]
