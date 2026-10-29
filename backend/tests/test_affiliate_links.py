from backend.app.affiliate_links import shopping_link


def test_optional_amazon_tag_preserves_other_links(app):
    with app.app_context():
        original = 'https://www.amazon.com/dp/ABC?ref=wish&tag=old-20'
        app.config['AMAZON_ASSOCIATE_TAG'] = ''
        assert shopping_link(original) == original
        app.config['AMAZON_ASSOCIATE_TAG'] = 'gather-20'
        assert shopping_link(original) == 'https://www.amazon.com/dp/ABC?ref=wish&tag=gather-20'
        for url in ['https://amazon.com.evil.test/dp/ABC', 'https://amzn.to/example', 'https://amazon.co.uk/dp/ABC', 'https://google.com/shopping/123', 'http://amazon.com/dp/ABC', None]:
            assert shopping_link(url) == url


def test_store_rules_only_match_exact_domains_and_encode_deep_links(app):
    with app.app_context():
        app.config['STORE_AFFILIATE_RULES'] = {'shop.example': {'query': {'partner': 'our-account'}}, 'other.example': {'deeplink': 'https://affiliate.example/click?merchant=123&url={url}'}}
        assert shopping_link('https://www.shop.example/gift?id=1') == 'https://www.shop.example/gift?id=1&partner=our-account'
        assert shopping_link('https://shop.example.evil.test/gift') == 'https://shop.example.evil.test/gift'
        assert shopping_link('https://other.example/gift?a=1&b=2') == 'https://affiliate.example/click?merchant=123&url=https%3A%2F%2Fother.example%2Fgift%3Fa%3D1%26b%3D2'
        app.config['STORE_AFFILIATE_RULES'] = 'invalid-json'
        assert shopping_link('https://shop.example/gift') == 'https://shop.example/gift'
