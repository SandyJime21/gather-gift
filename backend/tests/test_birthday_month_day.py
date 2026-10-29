from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import PersonProfile


def test_birthdays_use_month_and_day_without_birth_year(app):
    client = app.test_client()
    register(client, 'Parent', 'birthday@example.com')
    home = mutate(client, 'POST', '/api/households', {'name': 'Family', 'profiles': [{'display_name': 'Child', 'birthday': '02-29'}]}).json['household']
    profile = client.get(f"/api/households/{home['id']}").json['profiles'][0]
    assert profile['birthday'] == '02-29'
    path = f"/api/profiles/{profile['id']}"
    assert mutate(client, 'PATCH', path, {'birthday': '06-15'}).json['profile']['birthday'] == '06-15'
    assert mutate(client, 'PATCH', path, {'birthday': '02-30'}).status_code == 400
    assert mutate(client, 'PATCH', path, {'birthday': '06-'}).status_code == 400
    with app.app_context():
        assert db.session.get(PersonProfile, profile['id']).birthday.year == 2000
    # Full dates from older clients are accepted without retaining their birth year.
    assert mutate(client, 'PATCH', path, {'birthday': '1995-04-12'}).json['profile']['birthday'] == '04-12'
    with app.app_context():
        assert db.session.get(PersonProfile, profile['id']).birthday.year == 2000
    assert mutate(client, 'PATCH', path, {'birthday': None}).json['profile']['birthday'] is None
