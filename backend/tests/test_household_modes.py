from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import mutate


def test_child_mode_requires_pin_and_cannot_switch_or_escape_without_it(app):
    parent, child, stranger, home, profiles, lists, path, account = child_setup(app)
    assert mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': profiles[0]['id']}).status_code == 400
    assert mutate(parent, 'POST', '/api/household-session/pin', {'pin': '123456', 'password': 'wrong'}).status_code == 403
    assert mutate(parent, 'POST', '/api/household-session/pin', {'pin': '123456', 'password': 'a-long-test-password'}).status_code == 200
    assert mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': profiles[0]['id']}).json['status'] == 'child'
    assert parent.get('/api/auth/me').json['user']['child_mode_locked']
    assert mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': None}).status_code == 403
    assert parent.get('/api/household-session').status_code == 403
    assert mutate(parent, 'POST', '/api/household-session/exit-child', {'pin': '999999'}).status_code == 403
    assert parent.get('/api/auth/me').json['user']['is_child']
    assert mutate(parent, 'POST', '/api/household-session/exit-child', {'pin': '123456'}).status_code == 200
    assert not parent.get('/api/auth/me').json['user']['is_child']
    # A standalone child login cannot recover the household session using a PIN.
    assert mutate(child, 'POST', '/api/household-session/exit-child', {'pin': '123456'}).status_code == 403


def test_adult_profile_mode_limits_editing_and_guardians_can_edit_children(app):
    parent, child, stranger, home, profiles, lists, path, account = child_setup(app)
    adult_id = profiles[1]['id']
    assert mutate(parent, 'PATCH', f'/api/profiles/{adult_id}', {'is_adult': True, 'member_email': 'adult@example.com'}).status_code == 200
    assert mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': adult_id}).json['status'] == 'adult'
    assert parent.get(f'/api/profiles/{adult_id}').json['profile']['can_edit']
    assert not parent.get(f"/api/profiles/{profiles[0]['id']}").json['profile']['can_edit']
    assert mutate(parent, 'PATCH', f"/api/profiles/{profiles[0]['id']}", {'display_name': 'Blocked'}).status_code == 404
    assert mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': None}).status_code == 200
    assert mutate(parent, 'PATCH', f'/api/profiles/{adult_id}', {'is_guardian': True}).status_code == 200
    assert mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': adult_id}).status_code == 200
    assert parent.get(f"/api/profiles/{profiles[0]['id']}").json['profile']['can_edit']
    assert mutate(stranger, 'POST', '/api/household-session/switch', {'profile_id': adult_id}).status_code == 404


def test_unclaimed_adult_wishes_can_be_managed_without_switching_profiles(app):
    parent, child, stranger, home, profiles, lists, path, account = child_setup(app)
    adult_id = profiles[1]['id']
    item = mutate(parent, 'POST', f"/api/wishlists/{lists[1]['id']}/items", {'name': 'Adult gift'}).json['item']
    assert mutate(parent, 'PATCH', f'/api/profiles/{adult_id}', {'is_adult': True}).status_code == 200
    assert parent.get(f'/api/profiles/{adult_id}').json['profile']['can_remove_wishes']
    assert mutate(parent, 'PATCH', f"/api/items/{item['id']}", {'name':'Edited adult gift'}).status_code == 200
    assert mutate(stranger, 'DELETE', f"/api/items/{item['id']}").status_code == 404
    assert mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': adult_id}).status_code == 200
    assert parent.get('/api/auth/me').json['user']['browsing_as'] == profiles[1]['display_name']
    assert parent.get(f'/api/profiles/{adult_id}').json['profile']['can_remove_wishes']
    assert mutate(parent, 'DELETE', f"/api/items/{item['id']}").status_code == 200

def test_locked_child_can_switch_only_enabled_siblings_and_stays_locked(app):
    parent, child, stranger, home, profiles, lists, path, account = child_setup(app)
    sibling = mutate(parent, 'POST', path, {'profile_id': profiles[1]['id'], 'wishlist_ids': [lists[1]['id']], 'password': 'child-test-password'}).json['child']
    assert child.get('/api/child/profiles').json['profiles'] == []
    assert mutate(child, 'POST', '/api/child/profiles/switch', {'child_id': sibling['id']}).status_code == 403
    mutate(parent, 'POST', '/api/household-session/pin', {'pin': '123456', 'password': 'a-long-test-password'})
    mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': profiles[0]['id']})
    assert len(parent.get('/api/child/profiles').json['profiles']) == 1
    assert mutate(parent, 'POST', '/api/child/profiles/switch', {'child_id': sibling['id']}).status_code == 403
    from backend.tests.test_child_controls import allow_optional_features
    allow_optional_features(app)
    assert len(parent.get('/api/child/profiles').json['profiles']) == 2
    assert mutate(parent, 'POST', '/api/child/profiles/switch', {'child_id': sibling['id']}).status_code == 200
    assert parent.get('/api/auth/me').json['user']['child_mode_locked']
    assert [w['id'] for w in parent.get('/api/child/me').json['wishlists']] == [lists[1]['id']]
    assert mutate(parent, 'POST', '/api/household-session/switch', {'profile_id': None}).status_code == 403
    assert mutate(parent, 'POST', '/api/household-session/exit-child', {'pin': '123456'}).status_code == 200

def test_forgot_parent_pin_requires_email_confirmation(app, monkeypatch):
    from backend.app.models import User
    from backend.app.extensions import db
    from werkzeug.security import generate_password_hash
    parent, _, stranger, _, profiles, _, _, _ = child_setup(app)
    app.config.update(SMTP_HOST='test',MAIL_FROM='test@example.com')
    sent=[]
    monkeypatch.setattr('backend.app.api.send_account_code',lambda email,code,purpose:sent.append((email,code,purpose)) or True)
    with app.app_context():
        owner=User.query.filter_by(email='childparent@example.com').one()
        owner.parent_pin_hash=generate_password_hash('123456')
        db.session.commit()
    assert mutate(parent,'POST','/api/household-session/switch',{'profile_id':profiles[0]['id']}).status_code==200
    challenge=mutate(parent,'POST','/api/household-session/pin/reset',{}).json['challenge_id']
    email,code,purpose=sent[0]
    assert email=='childparent@example.com' and purpose=='parent_pin' and len(code)==6
    with app.app_context():
        from werkzeug.security import check_password_hash
        assert check_password_hash(User.query.filter_by(email=email).one().parent_pin_hash,'123456')
    assert mutate(stranger,'POST','/api/household-session/pin/reset/confirm',{'challenge_id':challenge,'code':code}).status_code==400
    assert mutate(parent,'POST','/api/household-session/pin/reset/confirm',{'challenge_id':challenge,'code':'not-a-pin'}).status_code==400
    assert mutate(parent,'POST','/api/household-session/pin/reset/confirm',{'challenge_id':challenge,'code':code}).status_code==200
    assert mutate(parent,'POST','/api/household-session/exit-child',{'pin':code}).status_code==200
    assert mutate(parent,'POST','/api/household-session/pin/reset/confirm',{'challenge_id':challenge,'code':code}).status_code==400

def test_parent_and_grandparent_relationships_default_to_adult(app):
    parent=app.test_client()
    from backend.tests.test_reservation_privacy import register
    register(parent,'Owner','adult-relations@example.com')
    home=mutate(parent,'POST','/api/households',{'name':'Family','profiles':[{'display_name':role,'relationship':role} for role in ['mom','dad','grandma','grandpa','grandparent']]}).json['household']
    profiles=parent.get(f"/api/households/{home['id']}").json['profiles']
    assert all(p['is_adult'] for p in profiles if p['display_name'] in ['mom','dad','grandma','grandpa','grandparent'])
    child=mutate(parent,'POST',f"/api/households/{home['id']}/profiles",{'display_name':'Member','relationship':'child'}).json['profile']
    assert not child['is_adult']
    assert mutate(parent,'PATCH',f"/api/households/{home['id']}/profiles/{child['id']}/relationship",{'relationship':'grandma'}).status_code==200
    assert parent.get(f"/api/profiles/{child['id']}").json['profile']['is_adult']
