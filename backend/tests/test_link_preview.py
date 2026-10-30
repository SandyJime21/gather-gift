from backend.tests.wishlist_setup import create_test_wishlist
import socket
import pytest
from backend.app.link_preview import preview_link, public_target, MetadataParser, product_price
from backend.tests.test_reservation_privacy import register, mutate


def fake_dns(host, *args, **kwargs):
    address = host if host in {'127.0.0.1', '10.0.0.1', '169.254.169.254', '224.0.0.1'} else '93.184.216.34'
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 443))]


@pytest.mark.parametrize('html,expected',[
    ('<meta property="product:price:amount" content="24.95"><meta property="product:price:currency" content="usd">',{'estimated_price':'24.95','currency':'USD'}),
    ('<script type="application/ld+json">{"@graph":[{"@type":"Product","offers":{"price":"0","priceCurrency":"GBP"}}]}</script>',{'estimated_price':'0.00','currency':'GBP'}),
    ('<script type="application/ld+json">{"@type":"Product","offers":{"lowPrice":"4","highPrice":"99","priceCurrency":"USD"}}</script>',{}),
    ('<meta property="product:price:amount" content="NaN"><meta property="product:price:currency" content="USD">',{}),
    ('<script type="application/ld+json">{"@type":"Organization","price":"55","priceCurrency":"USD"}</script>',{}),
    ('<script type="application/ld+json">broken</script><p>$99</p>',{}),
])
def test_only_explicit_product_prices_are_used(html,expected):
    parser=MetadataParser();parser.feed(html)
    assert product_price(parser)==expected


def test_link_preview_reads_image_and_title_without_leaking_network_access(app, monkeypatch):
    app.config['PERMITTED_METADATA_DOMAINS']='shop.example'
    monkeypatch.setattr('backend.app.link_preview.socket.getaddrinfo', fake_dns)
    connections = []
    class Response:
        status = 200
        def getheader(self, key):
            return 'text/html' if key == 'Content-Type' else None
        def read(self, size):
            return b'<title>Fallback</title><meta property="og:title" content="A gift &amp; more"><meta property="og:image" content="/gift.jpg"><meta property="og:site_name" content="Example Store">'
    class Connection:
        def __init__(self, host, address):
            connections.append((host, address))
        def request(self, *args, **kwargs):
            pass
        def getresponse(self):
            return Response()
        def close(self):
            pass
    monkeypatch.setattr('backend.app.link_preview.PinnedHTTPSConnection', Connection)
    client = app.test_client()
    register(client, 'Parent', 'linkpreview@example.com')
    result = mutate(client, 'POST', '/api/link-preview', {'url': 'https://shop.example/gift'})
    assert result.status_code == 200
    assert result.json['preview'] == {'title': 'A gift & more', 'image_url': 'https://shop.example/gift.jpg', 'store_name': 'Example Store'}
    assert connections == [('shop.example', '93.184.216.34')]
    for url in ['https://127.0.0.1/', 'https://10.0.0.1/', 'https://169.254.169.254/', 'https://224.0.0.1/', 'http://shop.example/', 'https://user:pass@shop.example/', 'https://shop.example:8443/']:
        assert mutate(client, 'POST', '/api/link-preview', {'url': url}).status_code == 400
    assert len(connections) == 1


def test_link_preview_revalidates_redirects(monkeypatch):
    monkeypatch.setattr('backend.app.link_preview.socket.getaddrinfo', fake_dns)
    class Response:
        status = 302
        def getheader(self, key):
            return 'https://127.0.0.1/admin' if key == 'Location' else None
    class Connection:
        def __init__(self, *args):
            pass
        def request(self, *args, **kwargs):
            pass
        def getresponse(self):
            return Response()
        def close(self):
            pass
    monkeypatch.setattr('backend.app.link_preview.PinnedHTTPSConnection', Connection)
    with pytest.raises(ValueError):
        preview_link('https://shop.example/gift')


def test_shopper_preview_excludes_private_plans_notes_and_purchases(app):
    owner, other = app.test_client(), app.test_client()
    register(owner, 'Parent', 'previewowner@example.com')
    register(other, 'Other', 'previewother@example.com')
    home = mutate(owner, 'POST', '/api/households', {'name': 'Family', 'profiles': [{'display_name': 'Mia', 'birthday': '05-01'}]}).json['household']
    path = f"/api/households/{home['id']}"
    profile = owner.get(path).json['profiles'][0]
    mutate(owner, 'PATCH', f"/api/profiles/{profile['id']}", {'parent_notes': 'Private parent note'})
    wishlist = create_test_wishlist(owner, f"/api/profiles/{profile['id']}/wishlists")
    mutate(owner, 'POST', f"/api/wishlists/{wishlist['id']}/items", {'name': 'Visible wish'})
    mutate(owner, 'POST', '/api/private-gifts', {'name': 'Secret surprise', 'recipient': 'Mia'})
    response = owner.get(path + '/shopper-preview')
    assert response.status_code == 200
    assert 'Visible wish' in response.get_data(as_text=True)
    for private in ['Secret surprise', 'Private parent note', 'availability', 'is_hearted', '05-01']:
        assert private not in response.get_data(as_text=True)
    assert other.get(path + '/shopper-preview').status_code == 403


def test_blocked_store_preview_can_still_save_a_basic_public_link(monkeypatch):
    monkeypatch.setattr('backend.app.link_preview.socket.getaddrinfo', fake_dns)
    class Response:
        status = 403
        def getheader(self, key):
            return 'text/html'
    class Connection:
        def __init__(self, *args):
            pass
        def request(self, *args, **kwargs):
            pass
        def getresponse(self):
            return Response()
        def close(self):
            pass
    monkeypatch.setattr('backend.app.link_preview.PinnedHTTPSConnection', Connection)
    result = preview_link('https://shop.example/cozy-blanket')
    assert result['title'] == 'cozy blanket'
    assert result['metadata_unavailable']
    assert result['image_url'] is None
    with pytest.raises(ValueError):
        preview_link('https://127.0.0.1/secret')
