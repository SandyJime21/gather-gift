from backend.tests.test_diagnostic_view import staff_client
from backend.tests.test_reservation_privacy import register,mutate
from backend.app.extensions import db
from backend.app.models import User


def test_staff_and_family_accounts_switch_only_after_password_verification(app):
    owner=app.test_client();family=register(owner,'Family me','switch-family@example.com')
    staff=staff_client(app,master=False)
    staff_id=staff.get('/api/auth/me').json['user']['id']
    assert mutate(staff,'POST','/api/auth/accounts/switch',{'user_id':family['id']}).status_code==403
    assert mutate(staff,'POST','/api/auth/accounts/add',{'email':'switch-family@example.com','password':'wrong'}).status_code==401
    assert len(staff.get('/api/auth/accounts').json['accounts'])==1
    with app.app_context():
        db.session.get(User,family['id']).set_password('verified-family-password');db.session.commit()
    added=mutate(staff,'POST','/api/auth/accounts/add',{'email':'switch-family@example.com','password':'verified-family-password'})
    assert added.status_code==200,added.json
    assert len(added.json['accounts'])==2
    switched=mutate(staff,'POST','/api/auth/accounts/switch',{'user_id':family['id']})
    assert switched.status_code==200,switched.json
    assert not switched.json['user']['is_support']
    assert staff.get('/api/support/requests').status_code==403
    assert mutate(staff,'POST','/api/households',{'name':'My own family'}).status_code==201
    restored=mutate(staff,'POST','/api/auth/accounts/switch',{'user_id':staff_id})
    assert restored.status_code==200,restored.json
    assert restored.json['user']['is_support'] and not restored.json['user']['is_superuser']
    assert staff.get('/api/auth/me').json['households']==[]
    assert mutate(staff,'POST','/api/auth/logout',{}).status_code==200
    assert staff.get('/api/auth/accounts').status_code==401


def test_superuser_can_create_separate_family_account_without_copying_privileges(app):
    staff=staff_client(app)
    added=mutate(staff,'POST','/api/auth/accounts/add',{'create':True,'name':'My family login','email':'new-family@example.com','password':'a-separate-family-password'})
    assert added.status_code==200,added.json
    family=next(row for row in added.json['accounts'] if not row['current'])
    assert not family['is_support'] and not family['is_superuser']
    assert staff.get('/api/auth/me').json['user']['is_superuser']
    switched=mutate(staff,'POST','/api/auth/accounts/switch',{'user_id':family['id']})
    assert switched.status_code==200
    assert not switched.json['user']['is_superuser']
    assert mutate(staff,'POST','/api/auth/accounts/add',{'email':'evil@example.com','password':'some-password','is_superuser':True}).status_code==400


def test_stale_account_authentication_cannot_restore_staff_access(app):
    staff=staff_client(app)
    staff_id=staff.get('/api/auth/me').json['user']['id']
    created=mutate(staff,'POST','/api/auth/accounts/add',{'create':True,'name':'Family','email':'stale-family@example.com','password':'a-family-password'})
    family=next(row for row in created.json['accounts'] if not row['current'])
    assert mutate(staff,'POST','/api/auth/accounts/switch',{'user_id':family['id']}).status_code==200
    with app.app_context():db.session.get(User,staff_id).session_version+=1;db.session.commit()
    assert mutate(staff,'POST','/api/auth/accounts/switch',{'user_id':staff_id}).status_code==409
    assert staff.get('/api/auth/me').json['user']['id']==family['id']
