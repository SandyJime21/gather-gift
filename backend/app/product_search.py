"""Search public product listings without sending family/profile information."""
import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen
from flask import current_app


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


def search_products(query, child_safe=False):
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
        try:
            price = Decimal(str(row.get('extracted_price')))
            price = str(price.quantize(Decimal('0.01'))) if price.is_finite() and 0 <= price <= Decimal('99999999.99') else ''
        except (InvalidOperation, ValueError):
            price = ''
        products.append({'name': title[:200], 'product_url': link,
            'store_name': str(row.get('source') or 'Google Shopping')[:120],
            'estimated_price': price, 'currency': 'USD',
            'thumbnail': safe_product_url(row.get('thumbnail'))})
    return products
