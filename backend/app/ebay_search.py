"""Read-only eBay Browse search using server-held application credentials."""
import base64
import hashlib
import json
import re
import ssl
import time
from decimal import Decimal, InvalidOperation
from threading import Lock
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import certifi
from flask import current_app

TOKEN_LOCK = Lock()


def configured():
    return bool(current_app.config.get('EBAY_CLIENT_ID','').strip() and current_app.config.get('EBAY_CLIENT_SECRET','').strip())


def api_origin():
    environment=current_app.config.get('EBAY_ENVIRONMENT','production')
    if environment not in ('production','sandbox'):
        raise ValueError('Choose production or sandbox for eBay.')
    if environment=='sandbox' and current_app.config.get('APP_ENV')=='production':
        raise ValueError('Sandbox listings cannot be shown on the production website.')
    return 'https://api.sandbox.ebay.com' if environment=='sandbox' else 'https://api.ebay.com'


def read_json(req):
    with urlopen(req,timeout=10,context=ssl.create_default_context(cafile=certifi.where())) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:
        raise ValueError('eBay response was too large.')
    data=json.loads(raw)
    if not isinstance(data,dict):
        raise ValueError('Invalid eBay response.')
    return data


def app_token(refresh=False):
    client=current_app.config.get('EBAY_CLIENT_ID','').strip()
    secret=current_app.config.get('EBAY_CLIENT_SECRET','').strip()
    if not client or not secret:
        raise ValueError('eBay application keys are not configured.')
    origin=api_origin()
    fingerprint=hashlib.sha256((origin+'\0'+client+'\0'+secret).encode()).hexdigest()
    with TOKEN_LOCK:
        cached=current_app.extensions.get('ebay_application_token')
        if not refresh and cached and cached['key']==fingerprint and cached['expires']>time.monotonic():
            return cached['token']
        auth=base64.b64encode((client+':'+secret).encode()).decode()
        req=Request(origin+'/identity/v1/oauth2/token',data=urlencode({'grant_type':'client_credentials','scope':'https://api.ebay.com/oauth/api_scope'}).encode(),
                    headers={'Authorization':'Basic '+auth,'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json'},method='POST')
        data=read_json(req)
        token=data.get('access_token')
        expires=data.get('expires_in')
        if not isinstance(token,str) or not token or not isinstance(expires,(int,float)) or isinstance(expires,bool) or expires<=0:
            raise ValueError('eBay did not return a valid application token.')
        current_app.extensions['ebay_application_token']={'key':fingerprint,'token':token,'expires':time.monotonic()+max(0,min(expires,7200)-60)}
        return token


def search_ebay(query):
    from .product_search import safe_product_url
    origin=api_origin()
    marketplace=current_app.config.get('EBAY_MARKETPLACE_ID','EBAY_US')
    if not re.fullmatch(r'EBAY_[A-Z]{2,10}',marketplace):
        raise ValueError('Invalid eBay marketplace.')
    headers={'Accept':'application/json','X-EBAY-C-MARKETPLACE-ID':marketplace}
    campaign=current_app.config.get('EBAY_AFFILIATE_CAMPAIGN_ID','').strip()
    if campaign:
        if not re.fullmatch(r'[0-9]{1,30}',campaign):
            raise ValueError('Invalid eBay affiliate campaign ID.')
        headers['X-EBAY-C-ENDUSERCTX']='affiliateCampaignId='+campaign
    # Fixed-price items keep the gift flow out of bidding and checkout APIs.
    url=origin+'/buy/browse/v1/item_summary/search?'+urlencode({'q':query,'limit':24,'filter':'buyingOptions:{FIXED_PRICE}'})
    for attempt in range(2):
        headers['Authorization']='Bearer '+app_token(refresh=attempt==1)
        try:
            data=read_json(Request(url,headers=headers))
            break
        except HTTPError as exc:
            if exc.code!=401 or attempt:
                raise
    if data.get('errors'):
        raise ValueError('eBay could not complete the search.')
    rows=data.get('itemSummaries',[])
    if not isinstance(rows,list):
        raise ValueError('Invalid eBay product results.')
    products=[]
    for row in rows[:24]:
        if not isinstance(row,dict):
            continue
        link=safe_product_url(row.get('itemAffiliateWebUrl')) if campaign else None
        link=link or safe_product_url(row.get('itemWebUrl'))
        title=row.get('title')
        if not link or not isinstance(title,str) or not title.strip():
            continue
        amount=row.get('price') if isinstance(row.get('price'),dict) else {}
        price=''
        try:
            value=Decimal(str(amount.get('value')))
            if value.is_finite() and 0<=value<=Decimal('99999999.99'):
                price=str(value.quantize(Decimal('.01')))
        except (InvalidOperation,ValueError):
            pass
        currency=amount.get('currency','')
        if not isinstance(currency,str) or not re.fullmatch(r'[A-Z]{3}',currency):
            currency='USD';price=''
        image=row.get('image') if isinstance(row.get('image'),dict) else {}
        products.append({'name':title.strip()[:200],'product_url':link,'store_name':'eBay','source_product_id':str(row.get('itemId',''))[:200],
                         'estimated_price':price,'currency':currency,'thumbnail':safe_product_url(image.get('imageUrl'))})
    return products
