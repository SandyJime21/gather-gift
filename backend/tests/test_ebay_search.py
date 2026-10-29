import base64
import json
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import parse_qs,urlsplit
import pytest
from backend.app.ebay_search import search_ebay
from backend.app.product_search import search_products,search_configured
from backend.tests.test_reservation_privacy import register


def setup_keys(app):
    app.config.update(EBAY_CLIENT_ID='private-app-id',EBAY_CLIENT_SECRET='private-secret',EBAY_ENVIRONMENT='production',EBAY_MARKETPLACE_ID='EBAY_US',EBAY_AFFILIATE_CAMPAIGN_ID='',SERPAPI_API_KEY='')


def test_ebay_search_uses_app_oauth_and_caches_token_without_exposing_secrets(app,monkeypatch):
    setup_keys(app);calls=[]
    def fetch(req,**kwargs):
        calls.append(req)
        if req.full_url.endswith('/oauth2/token'):
            assert req.get_header('Authorization')=='Basic '+base64.b64encode(b'private-app-id:private-secret').decode()
            assert parse_qs(req.data.decode())=={'grant_type':['client_credentials'],'scope':['https://api.ebay.com/oauth/api_scope']}
            return BytesIO(json.dumps({'access_token':'private-token','expires_in':7200}).encode())
        assert req.get_header('Authorization')=='Bearer private-token'
        assert req.get_header('X-ebay-c-marketplace-id')=='EBAY_US'
        assert parse_qs(urlsplit(req.full_url).query)['q']==['building blocks']
        return BytesIO(json.dumps({'itemSummaries':[
            {'title':'Building set','itemWebUrl':'https://www.ebay.com/itm/123','price':{'value':'19.5','currency':'USD'},'image':{'imageUrl':'https://i.ebayimg.com/example.jpg'}},
            {'title':'Bad','itemWebUrl':'javascript:alert(1)'},
            {'title':'No price','itemWebUrl':'https://www.ebay.com/itm/456','price':{'value':'NaN','currency':'USD'}},
        ]}).encode())
    monkeypatch.setattr('backend.app.ebay_search.urlopen',fetch)
    client=app.test_client();register(client,'Parent','ebay-search@example.com')
    response=client.get('/api/gift-discovery?q=building+blocks')
    assert response.status_code==200
    assert len(response.json['products'])==2
    assert response.json['products'][0]['estimated_price']=='19.50'
    assert response.json['products'][1]['estimated_price']==''
    assert all(secret not in response.get_data(as_text=True) for secret in ('private-app-id','private-secret','private-token'))
    assert client.get('/api/gift-discovery?q=building+blocks').status_code==200
    assert sum(req.full_url.endswith('/oauth2/token') for req in calls)==1


def test_ebay_401_refreshes_once_and_affiliate_link_is_used_only_with_campaign(app,monkeypatch):
    setup_keys(app);app.config['EBAY_AFFILIATE_CAMPAIGN_ID']='1234567890';tokens=[];searches=[]
    def fetch(req,**kwargs):
        if req.full_url.endswith('/oauth2/token'):
            tokens.append(req);return BytesIO(json.dumps({'access_token':'token-'+str(len(tokens)),'expires_in':7200}).encode())
        searches.append(req)
        if len(searches)==1:raise HTTPError(req.full_url,401,'Expired',{},None)
        assert req.get_header('X-ebay-c-enduserctx')=='affiliateCampaignId=1234567890'
        return BytesIO(json.dumps({'itemSummaries':[{'title':'Toy','itemWebUrl':'https://www.ebay.com/itm/1','itemAffiliateWebUrl':'https://www.ebay.com/itm/1?campid=1234567890'}]}).encode())
    monkeypatch.setattr('backend.app.ebay_search.urlopen',fetch)
    with app.app_context():
        assert 'campid=1234567890' in search_ebay('toys')[0]['product_url']
    assert len(tokens)==2 and len(searches)==2


def test_child_mode_never_calls_ebay_and_adult_search_falls_back(app,monkeypatch):
    setup_keys(app);app.config['SERPAPI_API_KEY']='serp-key';ebay_calls=[]
    def failed(*args):ebay_calls.append(True);raise OSError('Unavailable')
    monkeypatch.setattr('backend.app.ebay_search.search_ebay',failed)
    monkeypatch.setattr('backend.app.product_search.urlopen',lambda *args,**kwargs:BytesIO(b'{"shopping_results":[]}'))
    with app.app_context():
        assert search_products('toys',child_safe=True)==[]
        assert not ebay_calls
        assert search_products('toys')==[]
        assert len(ebay_calls)==1
        app.config['SERPAPI_API_KEY']=''
        assert not search_configured(child_safe=True)
        assert search_configured()


def test_sandbox_cannot_feed_live_site(app):
    setup_keys(app);app.config.update(APP_ENV='production',EBAY_ENVIRONMENT='sandbox')
    with app.app_context(),pytest.raises(ValueError,match='Sandbox'):
        search_ebay('toys')
