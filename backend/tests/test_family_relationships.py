from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import HouseholdProfileAccess


def test_relationships_are_stored_per_household_and_require_admin(app):
    owner, outsider = app.test_client(), app.test_client()
    register(owner, 'Parent', 'relationparent@example.com')
    register(outsider, 'Visitor', 'relationvisitor@example.com')
    home = mutate(owner, 'POST', '/api/households', {
        'name': 'Family', 'profiles': [{'display_name': 'Sam', 'relationship': 'son'}, {'display_name': 'Alex'}]
    }).json['household']
    path = f"/api/households/{home['id']}"
    profiles = owner.get(path).json['profiles']
    sam = next(row for row in profiles if row['display_name'] == 'Sam')
    alex = next(row for row in profiles if row['display_name'] == 'Alex')
    assert sam['relationship'] == 'son'
    assert alex['relationship'] == 'family_member'
    target = path + f"/profiles/{sam['id']}/relationship"
    assert mutate(outsider, 'PATCH', target, {'relationship': 'dad'}).status_code == 403
    assert mutate(owner, 'PATCH', target, {'relationship': []}).status_code == 400
    assert mutate(owner, 'PATCH', target, {'relationship': 'grandpa'}).status_code == 200
    assert mutate(owner, 'POST', path + '/profiles', {'display_name': 'Grandma', 'relationship': 'grandma'}).status_code == 201
    assert mutate(owner, 'POST', path + '/profiles', {'display_name': 'Invalid', 'relationship': 'bad'}).status_code == 400
    second = mutate(owner, 'POST', '/api/households', {'name': 'Other home'}).json['household']
    with app.app_context():
        db.session.add(HouseholdProfileAccess(household_id=second['id'], profile_id=sam['id'], relationship='cousin'))
        db.session.commit()
    assert owner.get(f"/api/households/{second['id']}").json['profiles'][0]['relationship'] == 'cousin'
    assert next(row for row in owner.get(path).json['profiles'] if row['id'] == sam['id'])['relationship'] == 'grandpa'
