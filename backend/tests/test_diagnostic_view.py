from datetime import datetime,timezone
from backend.tests.test_reservation_privacy import register,mutate
from backend.app.extensions import db
from backend.app.models import User,AuditLog


def staff_client(app,master=True):
    with app.app_context():
        staff=User(name='Master' if master else 'Agent',email='master@example.com' if master else 'agent@example.com',is_support=True,is_superuser=master)
        staff.set_password('a-strong-testing-password')
        db.session.add(staff);db.session.commit()
        email=staff.email
    client=app.test_client()
    assert mutate(client,'POST','/api/auth/support/login',dict(email=email,password='a-strong-testing-password')).status_code==200
    return client


def test_superuser_views_real_account_without_consent_and_can_return(app):
    owner=app.test_client();target=register(owner,'Parent','diagnostic-parent@example.com')
    master=staff_client(app)
    start=mutate(master,'POST','/api/support/diagnostic-view',dict(email='diagnostic-parent@example.com',reason='Check profile layout for testing'))
    assert start.status_code==200,start.json
    assert start.json['user']['id']==target['id']
    assert start.json['user']['diagnostic_view']['read_only'] is True
    assert master.get('/api/wishlist').status_code==200
    assert master.get('/api/auth/me').json['user']['id']==target['id']
    assert mutate(master,'POST','/api/households',{'name':'Must not create'}).status_code==403
    assert mutate(master,'PATCH','/api/auth/profile',{'name':'Must not change'}).status_code==403
    assert mutate(master,'POST','/api/auth/login',{}).status_code==403
    end=mutate(master,'POST','/api/support/diagnostic-view/end',{})
    assert end.status_code==200,end.json
    assert end.json['user']['is_superuser'] is True
    assert end.json['user']['diagnostic_view'] is None
    with app.app_context():
        actions={r.action for r in AuditLog.query.all()}
        assert {'support.diagnostic_started','support.diagnostic_read','support.diagnostic_ended'}<=actions
        assert db.session.get(User,target['id']).name=='Parent'


def test_normal_staff_and_family_cannot_start_direct_diagnostics(app):
    owner=app.test_client();register(owner,'Parent','diagnostic-parent@example.com')
    agent=staff_client(app,master=False)
    body=dict(email='diagnostic-parent@example.com',reason='Check the profile layout')
    assert mutate(agent,'POST','/api/support/diagnostic-view',body).status_code==403
    assert mutate(owner,'POST','/api/support/diagnostic-view',body).status_code==403
    assert agent.get('/api/support/grants').json['grants']==[]


def test_expired_view_restores_only_original_superuser(app):
    owner=app.test_client();register(owner,'Parent','diagnostic-parent@example.com')
    master=staff_client(app)
    assert mutate(master,'POST','/api/support/diagnostic-view',dict(email='diagnostic-parent@example.com',reason='Check profile layout')).status_code==200
    with master.session_transaction() as state:
        diagnostic=dict(state['diagnostic_view']);diagnostic['expires_at']=0;state['diagnostic_view']=diagnostic
    assert master.get('/api/wishlist').status_code==401
    assert master.get('/api/auth/me').json['user']['is_superuser'] is True


def test_invalid_targets_and_reason_never_change_staff_identity(app):
    master=staff_client(app)
    for body in [dict(email='missing@example.com',reason='Check profile layout'),dict(email='master@example.com',reason='Check profile layout'),dict(email='x@example.com',reason='short')]:
        assert mutate(master,'POST','/api/support/diagnostic-view',body).status_code in (400,404)
        assert master.get('/api/auth/me').json['user']['is_superuser'] is True


def test_only_superuser_can_search_accounts_by_name_or_literal_email(app):
    owner=app.test_client();target=register(owner,'Find Me','find_me@example.com')
    master=staff_client(app)
    agent=staff_client(app,master=False)
    assert agent.get('/api/support/users?q=Find').status_code==403
    assert owner.get('/api/support/users?q=Find').status_code==403
    for query in ('Find Me','find_me@example.com'):
        result=master.get('/api/support/users',query_string={'q':query})
        assert result.status_code==200,result.json
        assert [row['id'] for row in result.json['users']]==[target['id']]
