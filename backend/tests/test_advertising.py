import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from io import BytesIO
from urllib.parse import parse_qs
from backend.app.extensions import db
from backend.app.models import AdCampaign, User
from backend.app.advertising import is_scheduled
from backend.tests.test_reservation_privacy import mutate, register


def campaign_payload():
    start = (datetime.now(timezone.utc) + timedelta(days=2)).date()
    return dict(business_name='Test store', email='ads@example.com', title='Thoughtful gifts', description='Shop our selection', business_url='https://store.example.com', media_url='https://store.example.com/ad.jpg', media_type='image', placements=['home','wishlist'], weekdays=list(range(7)), start_date=start.isoformat(), end_date=(start + timedelta(days=2)).isoformat(), start_time='09:00', end_time='17:00', timezone='UTC', display_seconds=15, keywords=['Christmas'])


def staff_login(client):
    user = User(name='Ad admin', email='ad-admin@example.com', is_support=True, is_superuser=True)
    user.set_password('staff-long-password')
    db.session.add(user); db.session.commit()
    with client.session_transaction() as state:
        state['user_id'] = user.id; state['auth_mode'] = 'support'; state['auth_version'] = user.session_version


def test_submission_validation_pricing_private_status_and_admin_review(app):
    app.config['ADS_DAILY_RATE_CENTS'] = 100
    client, admin = app.test_client(), app.test_client()
    created = mutate(client, 'POST', '/api/ads/campaigns', {**campaign_payload(), 'amount_cents': 1})
    assert created.status_code == 201, created.json
    row = created.json['campaign']; token = created.json['token']
    assert row['amount_cents'] == 600 and row['status'] == 'pending_review' and not row['paid']
    assert mutate(client, 'POST', f"/api/ads/campaigns/{row['id']}/status", {'token':'wrong'}).status_code == 404
    assert mutate(client, 'POST', f"/api/ads/campaigns/{row['id']}/checkout", {'token':token}).status_code == 409
    assert client.get('/api/ads/active?placement=home').json == {'ads':[]}
    assert client.get('/api/support/ads').status_code == 403
    staff_login(admin)
    assert mutate(admin, 'PATCH', f"/api/support/ads/{row['id']}", {'status':'approved'}).status_code == 200
    assert mutate(client, 'POST', f"/api/ads/campaigns/{row['id']}/checkout", {'token':token}).status_code == 503
    for change in [{'business_url':'javascript:alert(1)'}, {'weekdays':[True]}, {'end_time':'08:00'}, {'display_seconds':999}, {'keywords':['x'*50]}]:
        assert mutate(client, 'POST', '/api/ads/campaigns', {**campaign_payload(), **change}).status_code == 400


def test_checkout_uses_server_amount_and_signed_webhook_is_required(app, monkeypatch):
    app.config.update(ADS_DAILY_RATE_CENTS=100, STRIPE_SECRET_KEY='sk_test_private', STRIPE_WEBHOOK_SECRET='whsec_test')
    client = app.test_client()
    created = mutate(client,'POST','/api/ads/campaigns',campaign_payload()).json
    row = db.session.get(AdCampaign, created['campaign']['id']); row.status='approved'; db.session.commit()
    calls=[]
    def fake_open(request, timeout, context):
        calls.append(request)
        return BytesIO(json.dumps({'id':'cs_test_123','url':'https://checkout.stripe.com/c/pay/example'}).encode())
    monkeypatch.setattr('backend.app.advertising.urlopen', fake_open)
    response=mutate(client,'POST',f'/api/ads/campaigns/{row.id}/checkout',{'token':created['token'],'amount_cents':1})
    assert response.status_code == 200
    assert parse_qs(calls[0].data.decode())['line_items[0][price_data][unit_amount]'] == ['600']
    assert not row.paid
    event={'type':'checkout.session.completed','data':{'object':{'id':'cs_test_123','payment_status':'paid','amount_total':600,'currency':'usd','payment_intent':'pi_123','metadata':{'campaign_id':str(row.id)}}}}
    raw=json.dumps(event).encode()
    assert client.post('/api/ads/stripe-webhook',data=raw,content_type='application/json').status_code == 400
    timestamp=str(int(time.time()))
    signature=hmac.new(b'whsec_test',timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    for _ in range(2):
        assert client.post('/api/ads/stripe-webhook',data=raw,headers={'Stripe-Signature':f't={timestamp},v1={signature}'},content_type='application/json').status_code == 200
    db.session.refresh(row)
    assert row.paid and row.payment_intent == 'pi_123'
    assert mutate(client,'POST',f'/api/ads/campaigns/{row.id}/checkout',{'token':created['token']}).status_code == 409


def test_schedule_and_keyword_matching_and_public_output(app):
    client=app.test_client()
    app.config['ADS_DAILY_RATE_CENTS']=100
    created=mutate(client,'POST','/api/ads/campaigns',campaign_payload()).json
    row=db.session.get(AdCampaign,created['campaign']['id'])
    row.status='approved';row.paid=True
    data={**row.data,'start_date':'2020-01-01','end_date':'2099-12-31','start_time':'00:00','end_time':'23:59'}
    row.data=data;db.session.commit()
    assert is_scheduled(row,datetime(2026,12,25,12,tzinfo=timezone.utc))
    assert client.get('/api/ads/active?placement=home&q=christmas').json['ads']
    assert client.get('/api/ads/active?placement=settings&q=christmas').json == {'ads':[]}
    assert client.get('/api/ads/active?placement=home&q=birthday').json == {'ads':[]}
    ad=client.get('/api/ads/active?placement=home&q=christmas').json['ads'][0]
    assert 'email' not in ad and 'token' not in ad and 'amount_cents' not in ad
    row.status='paused';db.session.commit()
    assert not client.get('/api/ads/active?placement=home&q=christmas').json['ads']


def test_per_page_prices_and_private_uploaded_creative(app, tmp_path):
    app.config.update(ADS_WISHLIST_DAILY_RATE_CENTS='125', ADS_FOLLOWING_DAILY_RATE_CENTS='200', UPLOAD_FOLDER=str(tmp_path))
    client = app.test_client()
    payload = {**campaign_payload(), 'placements': ['wishlist', 'following']}
    csrf = client.get('/api/auth/csrf').json['csrf_token']
    response = client.post('/api/ads/campaigns', data={'payload': json.dumps(payload), 'creative': (BytesIO(b'\xff\xd8\xff' + b'image'), 'photo.jpeg')}, headers={'X-CSRF-Token': csrf})
    assert response.status_code == 201, response.json
    campaign = response.json['campaign']
    assert campaign['amount_cents'] == 975
    assert len(campaign['pricing']) == 2
    assert 'creative_file' not in campaign
    url = campaign['media_url']
    assert client.get(url.split('?')[0]).status_code == 404
    assert client.get(url).status_code == 200
    row = db.session.get(AdCampaign, campaign['id'])
    row.status = 'approved'; row.paid = True; db.session.commit()
    assert client.get(url.split('?')[0]).status_code == 200
    row.status = 'paused'; db.session.commit()
    assert client.get(url.split('?')[0]).status_code == 404
    bad = client.post('/api/ads/campaigns', data={'payload': json.dumps(payload), 'creative': (BytesIO(b'<script>bad</script>'), 'photo.jpeg')}, headers={'X-CSRF-Token': csrf})
    assert bad.status_code == 400


def test_discover_ads_match_saved_interests_without_exposing_them(app):
    from backend.app.models import PersonProfile, WishlistItem, SavedGift
    client=app.test_client()
    user=register(client,'Shopper','ads-interest@example.com')
    profile=PersonProfile(display_name='Shopper')
    db.session.add(profile); db.session.flush()
    item=WishlistItem(profile_id=profile.id,name='Christmas building toys')
    db.session.add(item); db.session.flush()
    db.session.add(SavedGift(user_id=user['id'],item_id=item.id))
    data={**campaign_payload(),'placements':['discover'],'start_date':'2020-01-01','end_date':'2099-12-31','start_time':'00:00','end_time':'23:59'}
    ad=AdCampaign(token_hash='interest-ad',data=data,status='approved',paid=True,amount_cents=100)
    db.session.add(ad);db.session.commit()
    result=client.get('/api/ads/active?placement=discover').json['ads']
    assert len(result)==1 and result[0]['title']==data['title']
    assert '_score' not in result[0] and 'keywords' not in result[0]
    assert app.test_client().get('/api/ads/active?placement=discover').json['ads']==[]
    ad.paid=False;db.session.commit()
    assert client.get('/api/ads/active?placement=discover').json['ads']==[]
