from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import Household, HouseholdMembership, HouseholdProfileAccess, PersonProfile, Occasion


def test_occasion_presets_and_shared_family_events(app):
    client = app.test_client()
    user = register(client, 'Parent', 'occasions@example.com')
    with app.app_context():
        household = Household(name='Family', owner_id=user['id'])
        db.session.add(household)
        db.session.flush()
        db.session.add(HouseholdMembership(household_id=household.id, user_id=user['id'], role='owner'))
        person = PersonProfile(display_name='Child', birthday=__import__('datetime').date(2016, 2, 29))
        db.session.add(person)
        db.session.flush()
        db.session.add(HouseholdProfileAccess(household_id=household.id, profile_id=person.id))
        event = Occasion(household_id=household.id, name='Family Christmas', occasion_type='christmas', event_date=__import__('datetime').date(2026, 12, 25))
        db.session.add(event)
        db.session.commit()
        profile_id, event_id = person.id, event.id
    path = f'/api/profiles/{profile_id}'
    assert client.get(path + '/occasions').json['occasions'][0]['id'] == event_id
    assert mutate(client, 'POST', path + '/wishlists', {'title': 'Christmas wishes', 'occasion_type': 'christmas'}).status_code == 201
    assert mutate(client, 'POST', path + '/wishlists', {'title': 'Birthday wishes', 'occasion_type': 'birthday'}).status_code == 201
    assert mutate(client, 'POST', path + '/wishlists', {'title': 'Graduation', 'occasion_type': 'other', 'occasion_date': '2027-06-10'}).status_code == 201
    assert mutate(client, 'POST', path + '/wishlists', {'title': 'Shared', 'occasion_id': event_id}).status_code == 201
    assert mutate(client, 'POST', path + '/wishlists', {'title': 'Invalid', 'occasion_type': 'other', 'occasion_date': 'bad'}).status_code == 400
    assert len(client.get(path + '/occasions').json['occasions']) == 4


def test_wedding_and_baby_registry_presets_require_dates(app):
    from backend.tests.test_reservation_privacy import register, mutate
    client = app.test_client()
    register(client, 'Parent', 'registry-types@example.com')
    home = mutate(client, 'POST', '/api/households', {'name': 'Family', 'profiles': [{'display_name': 'Alex'}]}).json['household']
    profile = client.get(f"/api/households/{home['id']}").json['profiles'][0]
    for kind in ('wedding', 'baby_shower', 'anniversary'):
        path = f"/api/profiles/{profile['id']}/wishlists"
        body = {'title': kind + ' registry', 'occasion_type': kind}
        assert mutate(client, 'POST', path, body).status_code == 400
        assert mutate(client, 'POST', path, {**body, 'occasion_date': '2027-06-15'}).status_code == 201
