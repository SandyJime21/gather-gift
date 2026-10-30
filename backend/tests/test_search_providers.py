from backend.app.product_search import search_products,source_serializer
from backend.app.extensions import db
from backend.app.models import CommerceIntegration,CommerceProductMetadata
from backend.tests.test_reservation_privacy import register,mutate


def test_multiple_configured_providers_merge_dedupe_filter_and_keep_partial_results(app,monkeypatch):
    app.config.update(EBAY_CLIENT_ID='id',EBAY_CLIENT_SECRET='secret',SERPAPI_API_KEY='key')
    calls=[]
    def ebay(query):
        calls.append('ebay');return [{'name':'Building set','store_name':'eBay','product_url':'https://www.ebay.com/itm/1','estimated_price':'10.00','currency':'USD'}]
    def serp(query,child_safe=False):
        calls.append('serpapi');return [{'name':'Target set','store_name':'Target','product_url':'https://www.target.com/p/set','estimated_price':'20.00','currency':'USD'},{'name':'Other set','store_name':'Other','product_url':'https://shop.example/set','estimated_price':'50.00','currency':'USD'}]
    monkeypatch.setattr('backend.app.ebay_search.search_ebay',ebay)
    monkeypatch.setattr('backend.app.product_search.search_serpapi',serp)
    with app.app_context():
        assert len(search_products('sets'))==3
        assert len(search_products('sets'))==3 and calls==['ebay','serpapi']
        assert [p['store_name'] for p in search_products('sets',filters={'max_price':'25','currency':'USD'})]==['eBay','Target']
        assert [p['store_name'] for p in search_products('sets',filters={'store':'Target'})]==['Target']
        app.extensions['commerce_search_cache'].clear()
        monkeypatch.setattr('backend.app.ebay_search.search_ebay',lambda *args:(_ for _ in ()).throw(OSError()))
        assert len(search_products('sets'))==2


def test_search_can_be_disabled_without_changing_keys_and_child_excludes_ebay(app,monkeypatch):
    app.config.update(EBAY_CLIENT_ID='id',EBAY_CLIENT_SECRET='secret',SERPAPI_API_KEY='key')
    monkeypatch.setattr('backend.app.ebay_search.search_ebay',lambda *args:(_ for _ in ()).throw(AssertionError('Child search must not call eBay')))
    monkeypatch.setattr('backend.app.product_search.search_serpapi',lambda *args,**kwargs:[])
    with app.app_context():
        assert search_products('toys',child_safe=True)==[]
        db.session.add(CommerceIntegration(provider='search_serpapi',enabled=False,approved=False,merchant_rules={}))
        db.session.commit()
        from backend.app.product_search import search_configured
        assert search_configured() and not search_configured(child_safe=True)


def test_filter_validation_and_signed_provenance(app):
    client=app.test_client();register(client,'Parent','signed-product@example.com');app.config['SERPAPI_API_KEY']='key'
    assert client.get('/api/gift-discovery?q=gift&min_price=50&max_price=10').status_code==400
    with app.app_context():token=source_serializer().dumps({'url':'https://shop.example/gift','provider':'ebay','product_id':'real-provider-id','verified_at':'2026-10-30T12:00:00+00:00'})
    saved=mutate(client,'POST','/api/personal-wishes',{'name':'Gift','product_url':'https://shop.example/gift','visibility':'private','viewer_ids':[],'source_token':token})
    assert saved.status_code==201,saved.json
    with app.app_context():
        row=db.session.get(CommerceProductMetadata,saved.json['wish']['item']['id'])
        assert row.source_provider=='ebay' and row.external_product_id=='real-provider-id' and row.last_verified_at is not None
    forged=mutate(client,'POST','/api/personal-wishes',{'name':'Manual','product_url':'https://shop.example/other','visibility':'private','viewer_ids':[],'source_token':token})
    with app.app_context():assert db.session.get(CommerceProductMetadata,forged.json['wish']['item']['id']).source_provider=='manual'
