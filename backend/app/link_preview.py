"""Bounded, public-HTTPS metadata previews; never fetch internal network URLs."""
import http.client
import ipaddress
import socket
import ssl
import certifi
import json
import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from flask import has_app_context,current_app
from urllib.parse import urljoin, urlsplit, unquote


def public_target(url):
    if not isinstance(url, str) or len(url) > 2000 or any(ord(char) < 32 for char in url):
        raise ValueError('Use a valid public HTTPS product link.')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Use a public HTTPS product link on the standard port.')
    host = parsed.hostname.encode('idna').decode('ascii')
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any((not ipaddress.ip_address(row[4][0]).is_global or ipaddress.ip_address(row[4][0]).is_multicast) for row in addresses):
        raise ValueError('Only public website links can be previewed.')
    return parsed, host, addresses[0][4][0]


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, port=443, timeout=5, context=ssl.create_default_context(cafile=certifi.where()))
        self.address = address

    def connect(self):
        # Pin the validated address, while retaining hostname certificate verification.
        connection = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(connection, server_hostname=self.host)
        except Exception:
            connection.close()
            raise


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metadata = {}
        self.in_title = False
        self.title = ''
        self.json_blocks = []
        self.in_json = False
        self.json_text = ''

    def handle_starttag(self, tag, attrs):
        values = {key.lower(): value for key, value in attrs}
        if tag.lower() == 'meta':
            key = (values.get('property') or values.get('name') or '').lower()
            if key in {'og:title', 'og:image', 'og:site_name', 'twitter:image', 'twitter:title', 'product:price:amount', 'product:price:currency', 'og:price:amount', 'og:price:currency'} and values.get('content'):
                self.metadata.setdefault(key, values['content'])
        if tag.lower() == 'script' and (values.get('type') or '').lower() == 'application/ld+json':
            self.in_json = True
            self.json_text = ''
        if tag.lower() == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self.in_json:
            self.in_json = False
            try:
                self.json_blocks.append(json.loads(self.json_text))
            except (ValueError, RecursionError):
                pass
        if tag.lower() == 'title':
            self.in_title = False

    def handle_data(self, value):
        if self.in_json:
            self.json_text += value
        if self.in_title:
            self.title += value[:500]


def product_price(parser):
    """Use only explicit product prices, never unrelated page text or ranges."""
    def normalize(amount, currency):
        if not isinstance(currency,str) or not re.fullmatch('[A-Za-z]{3}',currency):
            return None
        if not isinstance(amount,(str,int,float)) or isinstance(amount,bool):
            return None
        try:
            price=Decimal(str(amount))
            if price.is_finite() and 0<=price<=Decimal('99999999.99'):
                return {'estimated_price':str(price.quantize(Decimal('.01'))),'currency':currency.upper()}
        except InvalidOperation:
            pass
        return None
    meta=parser.metadata
    result=normalize(meta.get('product:price:amount') or meta.get('og:price:amount'),meta.get('product:price:currency') or meta.get('og:price:currency'))
    if result:
        return result
    def products(node,depth=0):
        if depth>12:
            return
        if isinstance(node,list):
            for value in node[:100]:
                yield from products(value,depth+1)
        elif isinstance(node,dict):
            types=node.get('@type',[])
            if types=='Product' or isinstance(types,list) and 'Product' in types:
                yield node
            for key in ('@graph','mainEntity'):
                yield from products(node.get(key),depth+1)
    for node in parser.json_blocks:
        for product in products(node):
            offers=product.get('offers',[])
            for offer in (offers if isinstance(offers,list) else [offers])[:50]:
                if isinstance(offer,dict):
                    result=normalize(offer.get('price'),offer.get('priceCurrency'))
                    if result:
                        return result
    return {}


def basic_link_preview(url, host):
    segments = [part for part in urlsplit(url).path.split('/') if part and not part.isdigit()]
    slug = unquote(segments[-1]).replace('-', ' ').replace('_', ' ') if segments else ''
    return {'title': (slug if len(slug) > 3 else 'Gift link from ' + host)[:200],
        'image_url': None, 'store_name': host.removeprefix('www.'), 'metadata_unavailable': True}


def preview_link(url,allowed_hosts=None):
    if allowed_hosts is None and has_app_context():
        from .commerce_urls import validated_product_url
        _,host=validated_product_url(url)
        allowed_hosts={value.strip().lower() for value in current_app.config.get('PERMITTED_METADATA_DOMAINS','').split(',') if value.strip()}
        if host not in allowed_hosts:
            return basic_link_preview(url,host)
    for attempt in range(4):
        parsed, host, address = public_target(url)
        if allowed_hosts is not None and host.lower() not in allowed_hosts:
            raise ValueError('This store is not enabled for permitted metadata previews.')
        connection = PinnedHTTPSConnection(host, address)
        try:
            path = parsed.path or '/'
            if parsed.query:
                path += '?' + parsed.query
            connection.request('GET', path, headers={'User-Agent': 'GatherGift-LinkPreview/1.0', 'Accept': 'text/html', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location or attempt == 3:
                    raise ValueError('This link redirects too many times. Try the full product link or search for the gift.')
                url = urljoin(url, location)
                continue
            if response.status != 200 or 'text/html' not in (response.getheader('Content-Type') or '').lower():
                return basic_link_preview(url, host)
            body = response.read(1_000_001)
            if len(body) > 1_000_000:
                body = body[:1_000_000]
            parser = MetadataParser()
            parser.feed(body.decode('utf-8', errors='replace'))
            metadata = parser.metadata
            image = metadata.get('og:image') or metadata.get('twitter:image')
            if image:
                image = urljoin(url, image)
                try:
                    public_target(image)
                except (OSError, ValueError):
                    image = None
            title = (metadata.get('og:title') or metadata.get('twitter:title') or parser.title).strip()
            if not title or any(word in title.lower() for word in ('robot or human', 'access denied', 'verify you are human', 'just a moment')):
                return basic_link_preview(url, host)
            # Amazon pricing will come from its approved API. Until then adults
            # can enter an estimated price themselves when saving a link.
            price = {} if 'amazon' in host.lower().split('.') or host.lower()=='amzn.to' else product_price(parser)
            return {'title': (metadata.get('og:title') or metadata.get('twitter:title') or parser.title).strip()[:200],
                **price,
                'image_url': image, 'store_name': (metadata.get('og:site_name') or host.removeprefix('www.'))[:120]}
        except (http.client.HTTPException, OSError):
            return basic_link_preview(url, host)
        finally:
            connection.close()
    raise ValueError('Could not preview this link.')
