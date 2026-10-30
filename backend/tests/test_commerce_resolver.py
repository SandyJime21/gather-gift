import json
from io import BytesIO
from urllib.parse import parse_qs,urlsplit
from backend.tests.test_reservation_privacy import register,mutate
from backend.tests.test_advertising import staff_login
from backend.app.extensions import db
from backend.app.models import CommerceIntegration,CommerceOutboundEvent


def wish(client,url='https://shop.example/product'):
    return mutate(client,'POST','/api/personal-wishes',{'name':'Gift','product_url':url,'visibility':'private','viewer_ids':[]}).json['wish']['item']


def test_outbound_preserves_original_and_private_permissions(app):
    owner,other,anonymous=app.test_client(),app.test_client(),app.test_client()
    register(owner,'Owner','out-owner@example.com');register(other,'Other','out-other@example.com')
    item=wish(owner)
    path=item['shopping_url']
    assert path==f"/api/commerce/items/{item['id']}/out"
    assert anonymous.get(path).status_code==404 and other.get(path).status_code==404
    response=owner.get(path+'?url=https://attacker.example/overwrite')
    assert response.status_code==302 and response.location=='https://shop.example/product'
    assert response.headers['Cache-Control']=='no-store'
    with app.app_context():
        event=CommerceOutboundEvent.query.one()
        assert event.provider=='direct' and event.merchant=='shop.example'
        assert not hasattr(event,'user_id') and not hasattr(event,'ip_address')


def test_approved_template_only_and_existing_affiliate_not_double_wrapped(app):
    client=app.test_client();register(client,'Owner','approved-out@example.com')
    item=wish(client)
    with app.app_context():
        db.session.add(CommerceIntegration(provider='impact',enabled=True,approved=False,merchant_rules={'approved_merchants':['shop.example'],'links':{'shop.example':'https://partner.example/click?url={url}'}}));db.session.commit()
    assert client.get(item['shopping_url']).location=='https://shop.example/product'
    with app.app_context():
        db.session.get(CommerceIntegration,'impact').approved=True;db.session.commit()
    assert client.get(item['shopping_url']).location=='https://partner.example/click?url=https%3A%2F%2Fshop.example%2Fproduct'
    original='https://www.amazon.com/dp/ABC?tag=existing-20'
    tagged=wish(client,original)
    assert client.get(tagged['shopping_url']).location==original


def test_sovrn_checks_eligibility_and_fails_open_without_leaking_keys(app,monkeypatch):
    client=app.test_client();register(client,'Owner','sovrn-out@example.com');item=wish(client)
    app.config['SOVRN_COMMERCE_API_KEY']='private-sovrn-key'
    with app.app_context():
        db.session.add(CommerceIntegration(provider='sovrn',enabled=True,approved=True,merchant_rules={'approved_merchants':['shop.example']}));db.session.commit()
    def response(url,**kwargs):
        params=parse_qs(urlsplit(url).query)
        assert params['optimize']==['false'] and params['out']==['https://shop.example/product']
        return BytesIO(json.dumps({'affiliatable':True,'optimized':'https://sovrn.co/opaque-issued-link'}).encode())
    monkeypatch.setattr('backend.app.commerce_adapters.urlopen',response)
    assert client.get(item['shopping_url']).location=='https://sovrn.co/opaque-issued-link'
    monkeypatch.setattr('backend.app.commerce_adapters.urlopen',lambda *a,**k:BytesIO(b'{"affiliatable":true,"optimized":"https://sovrn.co/click?key=private-sovrn-key"}'))
    result=client.get(item['shopping_url'])
    assert result.location=='https://shop.example/product' and 'private-sovrn-key' not in result.get_data(as_text=True)
    monkeypatch.setattr('backend.app.commerce_adapters.urlopen',lambda *a,**k:(_ for _ in ()).throw(OSError('Unavailable')))
    assert client.get(item['shopping_url']).location=='https://shop.example/product'


def test_public_wish_outbound_and_privacy_signals(app):
    owner,anonymous=app.test_client(),app.test_client();register(owner,'Owner','public-out@example.com')
    saved=mutate(owner,'POST','/api/personal-wishes',{'name':'Public gift','product_url':'https://shop.example/public','visibility':'public','viewer_ids':[]}).json['wish']
    path=saved['item']['shopping_url']
    for headers in ({'DNT':'1'},{'Sec-GPC':'1'},{'Sec-Purpose':'prefetch'}):
        assert anonymous.get(path,headers=headers).status_code==302
    assert anonymous.head(path).status_code==302
    with app.app_context():assert CommerceOutboundEvent.query.count()==0
    assert anonymous.get(path).status_code==302
    with app.app_context():assert CommerceOutboundEvent.query.count()==1


def test_provider_controls_require_master_and_real_approval(app):
    admin,user=app.test_client(),app.test_client();staff_login(admin);register(user,'User','provider-user@example.com')
    assert user.get('/api/support/commerce').status_code==403
    result=admin.get('/api/support/commerce')
    assert result.status_code==200 and result.json['conversions'] is None and result.json['commissions'] is None
    assert all(not row['approved'] and not row['enabled'] for row in result.json['providers'] if not row['id'].startswith('search_'))
    assert mutate(admin,'PATCH','/api/support/commerce/sovrn',{'enabled':True}).status_code==400
    assert mutate(admin,'PATCH','/api/support/commerce/impact',{'approved':True,'enabled':True,'merchant_rules':{'approved_merchants':['shop.example'],'links':{'shop.example':'https://partner.example/link?api_key=secret&url={url}'}}}).status_code==400
    result=mutate(admin,'PATCH','/api/support/commerce/impact',{'approved':True,'enabled':True,'merchant_rules':{'approved_merchants':['shop.example'],'excluded_merchants':[],'links':{'shop.example':'https://partner.example/link?url={url}'}}})
    assert result.status_code==200 and result.json['provider']['configured']
