import json
from io import BytesIO
from urllib.parse import urlsplit, parse_qs
from backend.tests.test_reservation_privacy import register
from backend.app.product_search import search_products


def test_child_search_excludes_amazon_even_when_google_hides_store_url(app, monkeypatch):
    app.config['SERPAPI_API_KEY']='test-key'
    rows=[
        {'title':'Amazon toy','source':'Amazon.com','product_link':'https://www.google.com/shopping/product/1'},
        {'title':'Direct toy','source':'Marketplace','link':'https://www.amazon.com/dp/123'},
        {'title':'Short link','link':'https://amzn.to/example'},
        {'title':'Other toy','source':'Other store','link':'https://store.example/toy'},
    ]
    monkeypatch.setattr('backend.app.product_search.urlopen',lambda *args,**kwargs:BytesIO(json.dumps({'shopping_results':rows}).encode()))
    with app.app_context():
        assert len(search_products('toys'))==4
        assert [p['name'] for p in search_products('toys',child_safe=True)]==['Other toy']


def test_discovery_requires_login_and_has_honest_unconfigured_fallback(app):
    client = app.test_client()
    assert client.get('/api/gift-discovery?q=flowers').status_code == 401
    register(client, 'Shopper', 'discovery@example.com')
    app.config['SERPAPI_API_KEY'] = ''
    assert client.get('/api/gift-discovery?q=flowers').json == {
        'enabled': False, 'products': [], 'message': 'Live product results are not available yet. Browse Google or a store below, or save your idea with an automatic shopping link.'}
    assert client.get('/api/gift-discovery?q=').status_code == 400
    assert client.get('/api/gift-discovery?q=' + 'x' * 201).status_code == 400


def test_product_results_are_normalized_and_key_stays_server_side(app, monkeypatch):
    client = app.test_client()
    register(client, 'Shopper', 'live-discovery@example.com')
    app.config['SERPAPI_API_KEY'] = 'test-secret-key'
    calls = []
    def fake_open(url, timeout):
        calls.append(url)
        return BytesIO(json.dumps({'shopping_results': [
            {'title': 'Flowers', 'source': 'Store', 'extracted_price': 24.99, 'product_link': 'https://www.google.com/shopping/product/123'},
            {'title': 'Bad link', 'link': 'javascript:alert(1)'},
            {'title': 'Price missing', 'link': 'https://store.example.com/item'},
            {'title': 'Bad price', 'extracted_price': 'NaN', 'link': 'https://store.example.com/other'},
        ]}).encode())
    monkeypatch.setattr('backend.app.product_search.urlopen', fake_open)
    response = client.get('/api/gift-discovery?q=flowers')
    assert response.status_code == 200
    products = response.json['products']
    assert len(products) == 3
    assert products[0]['estimated_price'] == '24.99'
    assert products[1]['estimated_price'] == '' and products[2]['estimated_price'] == ''
    assert 'test-secret-key' not in response.get_data(as_text=True)
    parameters = parse_qs(urlsplit(calls[0]).query)
    assert parameters['q'] == ['flowers']
    assert parameters['engine'] == ['google_shopping']
    def failed_open(*args, **kwargs):
        raise OSError('Provider unavailable')
    monkeypatch.setattr('backend.app.product_search.urlopen', failed_open)
    app.extensions.get('commerce_search_cache',{}).clear()
    assert client.get('/api/gift-discovery?q=flowers').status_code == 502
