from datetime import datetime, timedelta, timezone
from backend.app.extensions import db
from backend.app.models import AccountEmailCode, AdvertisingRequest, User
from backend.tests.test_advertising import campaign_payload, staff_login
from backend.tests.test_reservation_privacy import register, mutate


def inquiry(client):
    return mutate(client, 'POST', '/api/ads/requests', {'name':'Alex','email':'alex@example.com','business_name':'Gift shop','message':'I would like to advertise a holiday sale.'})


def prepare_admin(app, monkeypatch):
    admin = app.test_client()
    staff_login(admin)
    app.config.update(SMTP_HOST='test', MAIL_FROM='test@example.com')
    codes, alerts = [], []
    monkeypatch.setattr('backend.app.advertising.send_account_code', lambda email, code, purpose: codes.append((email, code, purpose)) or True)
    monkeypatch.setattr('backend.app.advertising.send_advertising_notification', lambda email, name, entry, url: alerts.append((email,name,entry.id,url)) or True)
    return admin, codes, alerts


def test_advertising_requests_always_reach_the_private_portal(app, monkeypatch):
    admin, _, alerts = prepare_admin(app, monkeypatch)
    public = app.test_client()
    result = inquiry(public)
    assert result.status_code == 201
    request_id = result.json['request_id']
    assert alerts == []
    assert public.get('/api/support/advertising-requests').status_code == 403
    register(public, 'Regular user', 'regular-ad-request@example.com')
    assert public.get('/api/support/advertising-alerts').status_code == 403
    rows = admin.get('/api/support/advertising-requests').json
    assert rows['new_count'] == 1
    assert rows['requests'][0]['email'] == 'alex@example.com'
    assert rows['requests'][0]['email_delivery'] == 'no_verified_recipient'
    assert mutate(admin, 'PATCH', f'/api/support/advertising-requests/{request_id}', {'status':'reviewed'}).status_code == 200
    assert admin.get('/api/support/advertising-requests').json['new_count'] == 0
    assert AdvertisingRequest.query.count() == 1


def test_only_confirmed_email_receives_alerts_and_campaigns_also_enter_the_portal(app, monkeypatch):
    admin, codes, alerts = prepare_admin(app, monkeypatch)
    public = app.test_client()
    start = mutate(admin, 'POST', '/api/support/advertising-alerts/verify-email', {'name':'Sandra','email':'alerts@example.com'})
    assert start.status_code == 200
    assert codes[0][0] == 'alerts@example.com'
    assert codes[0][2] == 'ads_alert_email'
    assert 'code' not in start.json
    challenge = AccountEmailCode.query.filter_by(id=start.json['challenge_id']).one()
    assert challenge.code_hash != codes[0][1]
    assert mutate(admin,'PATCH','/api/support/advertising-alerts',{'enabled':True}).status_code == 400
    inquiry(public)
    assert alerts == []
    body = {'challenge_id':challenge.id,'code':codes[0][1],'email':'alerts@example.com'}
    assert mutate(admin,'POST','/api/support/advertising-alerts/confirm-email',{**body,'email':'someone-else@example.com'}).status_code == 400
    assert mutate(admin,'POST','/api/support/advertising-alerts/confirm-email',body).status_code == 200
    assert mutate(admin,'POST','/api/support/advertising-alerts/confirm-email',body).status_code == 400
    result = inquiry(public)
    assert result.status_code == 201
    assert alerts[-1][0:2] == ('alerts@example.com','Sandra')
    assert '/support?advertising_request=' in alerts[-1][3]
    app.config['ADS_DAILY_RATE_CENTS'] = 100
    campaign = mutate(public,'POST','/api/ads/campaigns',campaign_payload())
    assert campaign.status_code == 201
    event = AdvertisingRequest.query.filter_by(campaign_id=campaign.json['campaign']['id']).one()
    assert event.email_delivery == 'sent'
    assert len(alerts) == 2
    assert admin.get('/api/support/advertising-requests').json['new_count'] == 3
    assert mutate(admin,'PATCH',f"/api/support/ads/{campaign.json['campaign']['id']}",{'status':'approved'}).status_code == 200
    assert admin.get('/api/support/advertising-requests').json['new_count'] == 2
    assert mutate(admin,'PATCH','/api/support/advertising-alerts',{'enabled':False}).status_code == 200
    inquiry(public)
    assert len(alerts) == 2
    assert AdvertisingRequest.query.order_by(AdvertisingRequest.id.desc()).first().email_delivery == 'disabled'


def test_changing_recipient_keeps_the_confirmed_address_until_new_confirmation(app, monkeypatch):
    admin, codes, alerts = prepare_admin(app, monkeypatch)
    user = User.query.filter_by(email='ad-admin@example.com').one()
    user.notification_preferences = {'advertising_alerts':{'name':'Old name','email':'old@example.com','verified_at':'2026-10-01','enabled':True}}
    db.session.commit()
    start = mutate(admin,'POST','/api/support/advertising-alerts/verify-email',{'name':'New name','email':'new@example.com'})
    inquiry(app.test_client())
    assert alerts[-1][0] == 'old@example.com'
    challenge = AccountEmailCode.query.filter_by(id=start.json['challenge_id']).one()
    challenge.expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
    db.session.commit()
    assert mutate(admin,'POST','/api/support/advertising-alerts/confirm-email',{'challenge_id':challenge.id,'code':codes[0][1],'email':'new@example.com'}).status_code == 400
    assert admin.get('/api/support/advertising-alerts').json['settings']['email'] == 'old@example.com'


def test_failed_notification_delivery_does_not_lose_the_request(app, monkeypatch):
    admin, _, _ = prepare_admin(app, monkeypatch)
    user = User.query.filter_by(email='ad-admin@example.com').one()
    user.notification_preferences = {'advertising_alerts':{'name':'Admin','email':'alerts@example.com','verified_at':'2026-10-01','enabled':True}}
    db.session.commit()
    def fail(*args):
        raise RuntimeError('Mail unavailable')
    monkeypatch.setattr('backend.app.advertising.send_advertising_notification', fail)
    result = inquiry(app.test_client())
    assert result.status_code == 201
    portal = admin.get('/api/support/advertising-requests').json
    assert portal['new_count'] == 1
    assert portal['requests'][0]['email_delivery'] == 'failed'
    assert portal['requests'][0]['id'] == result.json['request_id']


def test_verification_requires_working_email_and_rejects_invalid_contact_data(app, monkeypatch):
    admin, _, _ = prepare_admin(app, monkeypatch)
    app.config['SMTP_HOST'] = ''
    assert mutate(admin,'POST','/api/support/advertising-alerts/verify-email',{'name':'Sandra','email':'alerts@example.com'}).status_code == 503
    assert not AccountEmailCode.query.filter_by(purpose='ads_alert_email').first()
    assert mutate(app.test_client(),'POST','/api/ads/requests',{'name':'','email':'invalid','message':''}).status_code == 400
