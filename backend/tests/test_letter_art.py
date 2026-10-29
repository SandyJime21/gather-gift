import hashlib
import hmac
import json
import time
from datetime import datetime,timedelta,timezone
from urllib.parse import parse_qs
from io import BytesIO
from backend.tests.test_account_deletion import foreign_keys,confirm
from backend.tests.test_advertising import staff_login
from backend.tests.test_child_access import child_setup
from backend.tests.test_linked_adults import joined_family
from backend.tests.test_reservation_privacy import mutate,csrf
from backend.app.extensions import db
from backend.app.models import SharedTheme,LetterArtPurchase,Wishlist,User


def admin_client(app):
    admin=app.test_client()
    with app.app_context():staff_login(admin)
    return admin


def art(admin,name='Santa stars',price='3.00',purpose='letter'):
    response=admin.post('/api/support/themes',data=dict(name=name,season='Christmas',purpose=purpose,price=price,audience='everyone',background='#fff5ee',foreground='#332244',accent='#775599'),headers={'X-CSRF-Token':csrf(admin)})
    assert response.status_code==201,response.json
    return response.json['theme']


def event(client,app,kind,obj,signature=True):
    raw=json.dumps({'type':kind,'data':{'object':obj}}).encode()
    timestamp=str(int(time.time()))
    digest=hmac.new(app.config['STRIPE_WEBHOOK_SECRET'].encode(),timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    return client.post('/api/ads/stripe-webhook',data=raw,content_type='application/json',headers={'Stripe-Signature':f't={timestamp},v1={digest}'} if signature else {})


def test_developer_catalog_free_and_paid_selection_stay_separate_from_app_themes(app):
    parent,child,stranger,home,profiles,*_=child_setup(app)
    admin=admin_client(app)
    free=art(admin,name='Free stars',price='0')
    paid=art(admin)
    palette=art(admin,name='App palette',price='0',purpose='app')
    assert paid['price_cents']==300 and paid['purpose']=='letter'
    assert parent.get('/api/support/themes').status_code==403
    assert len(admin.get('/api/support/themes').json['themes'])==3
    catalog=parent.get(f"/api/households/{home['id']}/letter-art").json
    assert {row['id'] for row in catalog['designs']}=={int(free['key'][1:]),int(paid['key'][1:])}
    assert next(row for row in catalog['designs'] if row['key']==paid['key'])['unlocked'] is False
    assert [row['key'] for row in parent.get('/api/themes').json['themes']]==[palette['key']]
    assert mutate(parent,'PATCH','/api/auth/theme',dict(theme_key=paid['key'])).status_code==400
    assert stranger.get(f"/api/households/{home['id']}/letter-art").status_code==403
    assert child.get(f"/api/households/{home['id']}/letter-art").status_code==403
    path=f"/api/households/{home['id']}/wishlist-letters"
    payload=dict(title='Santa wishes',sender_name='Santa',send_on='2020-01-01',profile_ids=[profiles[0]['id']])
    assert mutate(parent,'POST',path,{**payload,'theme_id':int(paid['key'][1:])}).status_code==402
    selected=mutate(parent,'POST',path,{**payload,'theme_id':int(free['key'][1:])})
    assert selected.status_code==201,selected.json
    assert selected.json['letters'][0]['letter_art']['name']=='Free stars'
    assert child.get('/api/child/me').json['letters'][0]['letter_art']['name']=='Free stars'
    assert mutate(admin,'PATCH','/api/support/themes/'+free['key'][1:],dict(price='3.00')).status_code==200
    catalog=parent.get(f"/api/households/{home['id']}/letter-art").json
    assert next(row for row in catalog['designs'] if row['key']==free['key'])['unlocked'] is True


def test_only_confirmed_server_priced_payment_unlocks_design_for_one_family(app,monkeypatch):
    parent,_,_,home,profiles,*_=child_setup(app)
    design=art(admin_client(app));theme_id=int(design['key'][1:])
    app.config.update(STRIPE_SECRET_KEY='sk_test_fake',STRIPE_WEBHOOK_SECRET='test-secret')
    requests=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps(dict(id='cs_letter_test',url='https://checkout.stripe.com/test-session',expires_at=int(time.time())+86400)).encode()
    def checkout(request,**kwargs):requests.append(request);return Response()
    monkeypatch.setattr('backend.app.letter_art.urlopen',checkout)
    path=f"/api/households/{home['id']}/letter-art/{theme_id}/checkout"
    result=mutate(parent,'POST',path,dict(amount_cents=1,paid=True))
    assert result.status_code==200,result.json
    assert parse_qs(requests[0].data.decode())['line_items[0][price_data][unit_amount]']==['300']
    assert mutate(parent,'POST',path).json['url']==result.json['url'] and len(requests)==1
    with app.app_context():purchase=LetterArtPurchase.query.filter_by(theme_id=theme_id).one();pid=purchase.id
    obj=dict(id='cs_letter_test',payment_status='paid',amount_total=300,currency='usd',payment_intent='pi_letter_test',metadata=dict(letter_art_purchase_id=str(pid),household_id=str(home['id']),theme_id=str(theme_id)))
    assert event(parent,app,'checkout.session.completed',obj,signature=False).status_code==400
    assert event(parent,app,'checkout.session.completed',{**obj,'amount_total':1}).status_code==400
    assert event(parent,app,'checkout.session.completed',{**obj,'payment_status':'unpaid'}).status_code==200
    assert parent.get(f"/api/households/{home['id']}/letter-art").json['designs'][0]['unlocked'] is False
    assert event(parent,app,'checkout.session.completed',obj).status_code==200
    assert event(parent,app,'checkout.session.completed',obj).status_code==200
    assert parent.get(f"/api/households/{home['id']}/letter-art").json['designs'][0]['unlocked'] is True
    payload=dict(title='Dream wishes',sender_name='Santa',send_on='2020-01-01',profile_ids=[p['id'] for p in profiles],theme_id=theme_id)
    assert len(mutate(parent,'POST',f"/api/households/{home['id']}/wishlist-letters",payload).json['letters'])==2
    assert mutate(parent,'POST',path).json['unlocked'] is True and len(requests)==1
    other=mutate(parent,'POST','/api/households',dict(name='Other family',profiles=[dict(display_name='Other child')])).json['household']
    assert parent.get(f"/api/households/{other['id']}/letter-art").json['designs'][0]['unlocked'] is False
    assert event(parent,app,'charge.refunded',dict(payment_intent='pi_letter_test')).status_code==200
    assert event(parent,app,'checkout.session.completed',obj).status_code==200
    assert parent.get(f"/api/households/{home['id']}/letter-art").json['designs'][0]['unlocked'] is False
    assert mutate(parent,'POST',f"/api/households/{home['id']}/wishlist-letters",payload).status_code==402


def test_developer_validates_prices_and_can_hide_designs_without_losing_family_unlock(app):
    parent,_,_,home,profiles,*_=child_setup(app)
    admin=admin_client(app);design=art(admin);tid=int(design['key'][1:])
    for price in ['-1','0.01','3.001','NaN','Infinity','1001']:
        assert mutate(admin,'PATCH',f'/api/support/themes/{tid}',dict(price=price)).status_code==400
    assert mutate(admin,'PATCH',f'/api/support/themes/{tid}',dict(purpose='app',price='0')).status_code==400
    app.config.update(STRIPE_SECRET_KEY='',STRIPE_WEBHOOK_SECRET='')
    assert mutate(parent,'POST',f"/api/households/{home['id']}/letter-art/{tid}/checkout").status_code==503
    with app.app_context():
        user=User.query.filter_by(email='childparent@example.com').one()
        db.session.add(LetterArtPurchase(household_id=home['id'],theme_id=tid,buyer_user_id=user.id,art_name='Santa stars',amount_cents=300,paid=True,expires_at=datetime.now(timezone.utc)+timedelta(days=1)))
        db.session.commit()
    assert mutate(admin,'PATCH',f'/api/support/themes/{tid}',dict(active=False)).status_code==200
    assert parent.get(f"/api/households/{home['id']}/letter-art").json['designs'][0]['unlocked'] is True
    payload=dict(title='Santa wishes',sender_name='Santa',send_on='2020-01-01',profile_ids=[profiles[0]['id']],theme_id=tid)
    assert mutate(parent,'POST',f"/api/households/{home['id']}/wishlist-letters",payload).status_code==201


def test_family_unlock_survives_owner_account_deletion(app):
    owner,adult,_,home,_,kid,o,a=joined_family(app)
    design=art(admin_client(app));tid=int(design['key'][1:])
    with app.app_context():
        db.session.add(LetterArtPurchase(household_id=home['id'],theme_id=tid,buyer_user_id=o['id'],art_name='Santa stars',amount_cents=300,paid=True,expires_at=datetime.now(timezone.utc)+timedelta(days=1)))
        db.session.commit()
    preview=owner.get('/api/auth/account-deletion').json
    assert confirm(owner,preview).status_code==200
    assert adult.get(f"/api/households/{home['id']}/letter-art").json['designs'][0]['unlocked'] is True
    with app.app_context():assert LetterArtPurchase.query.one().buyer_user_id is None


def test_deleting_entire_family_cascades_unlocks_and_late_events_cannot_restore_them(app):
    parent,_,_,home,_,*_=child_setup(app)
    design=art(admin_client(app));tid=int(design['key'][1:])
    app.config['STRIPE_WEBHOOK_SECRET']='test-secret'
    with app.app_context():
        buyer=User.query.filter_by(email='childparent@example.com').one()
        purchase=LetterArtPurchase(household_id=home['id'],theme_id=tid,buyer_user_id=buyer.id,art_name='Santa stars',amount_cents=300,paid=True,stripe_session_id='cs_deleted_family',payment_intent='pi_deleted_family',expires_at=datetime.now(timezone.utc)+timedelta(days=1))
        db.session.add(purchase);db.session.commit();pid=purchase.id
    preview=parent.get('/api/auth/account-deletion').json
    assert confirm(parent,preview).status_code==200
    with app.app_context():
        assert LetterArtPurchase.query.count()==0
        assert db.session.get(SharedTheme,tid) is not None
    data=dict(id='cs_deleted_family',payment_status='paid',amount_total=300,currency='usd',metadata=dict(letter_art_purchase_id=str(pid),household_id=str(home['id']),theme_id=str(tid)))
    assert event(parent,app,'checkout.session.completed',data).status_code==200
    with app.app_context():assert LetterArtPurchase.query.count()==0


def test_paid_checkout_after_family_deletion_refunds_with_retry_and_no_duplicate(app,monkeypatch):
    parent,_,_,home,_,*_=child_setup(app)
    design=art(admin_client(app));tid=int(design['key'][1:])
    app.config.update(STRIPE_SECRET_KEY='sk_test_fake', STRIPE_WEBHOOK_SECRET='test-secret')
    with app.app_context():
        buyer=User.query.filter_by(email='childparent@example.com').one()
        purchase=LetterArtPurchase(household_id=home['id'],theme_id=tid,buyer_user_id=buyer.id,art_name='Santa stars',amount_cents=300,paid=False,stripe_session_id='cs_pending_deleted',expires_at=datetime.now(timezone.utc)+timedelta(days=1))
        db.session.add(purchase);db.session.commit();pid=purchase.id
    preview=parent.get('/api/auth/account-deletion').json
    assert confirm(parent,preview).status_code==200
    requests=[];unavailable=True
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps(dict(id='re_test',status='succeeded')).encode()
    def refund(req,**kwargs):
        requests.append(req)
        if unavailable:raise OSError('Temporary connection failure')
        return Response()
    monkeypatch.setattr('backend.app.letter_art.urlopen',refund)
    obj=dict(id='cs_pending_deleted',payment_status='paid',payment_intent='pi_pending_deleted',amount_total=300,currency='usd',metadata=dict(letter_art_purchase_id=str(pid),household_id=str(home['id']),theme_id=str(tid)))
    assert event(parent,app,'checkout.session.completed',obj,signature=False).status_code==400
    assert requests==[]
    assert event(parent,app,'checkout.session.completed',obj).status_code==502
    unavailable=False
    assert event(parent,app,'checkout.session.completed',obj).status_code==200
    assert event(parent,app,'checkout.session.completed',obj).status_code==200
    assert len(requests)==2
    assert requests[0].full_url=='https://api.stripe.com/v1/refunds'
    assert requests[0].get_header('Idempotency-key')==requests[1].get_header('Idempotency-key')
    assert parse_qs(requests[1].data.decode())['payment_intent']==['pi_pending_deleted']
    with app.app_context():assert LetterArtPurchase.query.count()==0
