"""Search public product listings without sending family/profile information."""
import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen
from flask import current_app
import time
import hashlib
from datetime import datetime,timezone
from itsdangerous import URLSafeTimedSerializer


def safe_product_url(value):
    if not isinstance(value, str) or len(value) > 2000:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
            return value
    except ValueError:
        pass
    return None


def search_configured(child_safe=False):
    from .search_providers import search_providers
    return any(provider.configured() and provider.enabled() and (not child_safe or provider.child_safe) for provider in search_providers())


def search_serpapi(query, child_safe=False):
    parameters = urlencode({'engine': 'google_shopping', 'q': query, 'gl': 'us', 'hl': 'en',
        **({'safe': 'active'} if child_safe else {}), 'api_key': current_app.config['SERPAPI_API_KEY']})
    with urlopen('https://serpapi.com/search.json?' + parameters, timeout=12) as response:
        data = json.loads(response.read(2_000_001))
    if not isinstance(data, dict) or data.get('error'):
        raise ValueError('Shopping provider could not complete the search.')
    products = []
    for row in data.get('shopping_results', [])[:24]:
        if not isinstance(row, dict):
            continue
        link = safe_product_url(row.get('link')) or safe_product_url(row.get('product_link'))
        title = row.get('title')
        if not link or not isinstance(title, str) or not title.strip():
            continue
        # Child search never receives Amazon listings, including listings whose
        # URL points to Google's product page rather than directly to Amazon.
        source = str(row.get('source') or '')
        host = (urlsplit(link).hostname or '').lower()
        if child_safe and ('amazon' in source.casefold() or host == 'amzn.to' or host.endswith('.amzn.to') or any(part == 'amazon' for part in host.split('.'))):
            continue
        try:
            price = Decimal(str(row.get('extracted_price')))
            price = str(price.quantize(Decimal('0.01'))) if price.is_finite() and 0 <= price <= Decimal('99999999.99') else ''
        except (InvalidOperation, ValueError):
            price = ''
        products.append({'name': title[:200], 'product_url': link,
            'source_product_id':str(row.get('product_id',''))[:200],
            'store_name': str(row.get('source') or 'Google Shopping')[:120],
            'estimated_price': price, 'currency': 'USD',
            'thumbnail': safe_product_url(row.get('thumbnail'))})
    return products


def source_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'],salt='commerce-product-source-v1')


def validate_filters(values):
    filters={}
    for field in ('store','brand','category'):
        value=values.get(field,'')
        if not isinstance(value,str) or len(value)>120:raise ValueError('Keep search filters within 120 characters.')
        filters[field]=value.strip()
    currency=values.get('currency','USD')
    if not isinstance(currency,str) or len(currency)!=3 or not currency.isalpha():raise ValueError('Choose a three-letter currency.')
    filters['currency']=currency.upper()
    for field in ('min_price','max_price'):
        value=values.get(field,'')
        if value in (None,''):filters[field]=None;continue
        try:
            amount=Decimal(str(value))
            if not amount.is_finite() or amount<0 or amount>Decimal('99999999.99'):raise ValueError()
        except (ValueError,InvalidOperation):raise ValueError('Choose a valid non-negative price range.')
        filters[field]=amount
    if filters['min_price'] is not None and filters['max_price'] is not None and filters['min_price']>filters['max_price']:raise ValueError('Minimum price must not exceed maximum price.')
    return filters


def search_products(query,child_safe=False,filters=None):
    from .search_providers import search_providers
    filters=validate_filters(filters or {})
    combined=' '.join(part for part in (query,filters['brand'],filters['category']) if part)[:440]
    products=[];success=False;configured=False;attempted=0
    cache=current_app.extensions.setdefault('commerce_search_cache',{})
    for provider in search_providers():
        if not provider.configured() or not provider.enabled() or (child_safe and not provider.child_safe):continue
        configured=True
        if filters['store'] and provider.key=='ebay' and filters['store'].casefold() not in ('ebay','ebay.com'):continue
        attempted+=1
        credential_keys=('EBAY_CLIENT_ID','EBAY_CLIENT_SECRET','EBAY_ENVIRONMENT') if provider.key=='ebay' else ('SERPAPI_API_KEY',)
        fingerprint=hashlib.sha256('|'.join(current_app.config.get(name,'') for name in credential_keys).encode()).hexdigest()
        key=(provider.key,combined,child_safe,fingerprint)
        cached=cache.get(key)
        try:
            if cached and time.monotonic()-cached[0]<300:rows,verified_at=cached[1],cached[2]
            else:
                rows=provider.searchProducts(combined,child_safe=child_safe)
                if len(cache)>=200:cache.clear()
                verified_at=datetime.now(timezone.utc).isoformat()
                cache[key]=(time.monotonic(),rows,verified_at)
            success=True
            for row in rows:
                row={**row,'source_provider':provider.key}
                row['source_token']=source_serializer().dumps({'url':row['product_url'],'provider':provider.key,'product_id':row.get('source_product_id'),'verified_at':verified_at})
                products.append(row)
        except (OSError,ValueError,TypeError):
            current_app.logger.warning('Product provider %s unavailable; other configured sources retained.',provider.key)
    if not configured:raise ValueError('Product search is not configured for this account mode.')
    if attempted and not success:raise ValueError('Configured product providers could not complete this search.')
    output=[];seen=set()
    for row in products:
        if row['product_url'] in seen:continue
        store=filters['store'].casefold()
        if store and store not in (row.get('store_name','')+' '+(urlsplit(row['product_url']).hostname or '')).casefold():continue
        if filters['min_price'] is not None or filters['max_price'] is not None:
            try:amount=Decimal(str(row.get('estimated_price')))
            except (InvalidOperation,ValueError):continue
            if not amount.is_finite() or row.get('currency')!=filters['currency']:continue
            if filters['min_price'] is not None and amount<filters['min_price'] or filters['max_price'] is not None and amount>filters['max_price']:continue
        seen.add(row['product_url']);output.append(row)
    return output[:48]
