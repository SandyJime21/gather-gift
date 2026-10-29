"""Store-specific affiliate rules applied at read time; saved URLs stay original."""
import json
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote
from flask import current_app


def shopping_link(url):
    if not isinstance(url, str):
        return url
    try:
        parts = urlsplit(url)
        if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
            return url
        host = parts.hostname.lower().removeprefix('www.')
        raw = current_app.config.get('STORE_AFFILIATE_RULES', '{}') or '{}'
        try:
            rules = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            rules = {}
        rule = rules.get(host) if isinstance(rules, dict) else None
        if isinstance(rule, dict):
            template = rule.get('deeplink')
            if isinstance(template, str) and template.count('{url}') == 1:
                target = template.replace('{url}', quote(url, safe=''))
                destination = urlsplit(target)
                if destination.scheme == 'https' and destination.hostname and not destination.username and not destination.password and destination.port in (None,443):
                    return target
            parameters = rule.get('query')
            if isinstance(parameters, dict) and parameters and all(isinstance(key,str) and isinstance(value,str) for key,value in parameters.items()):
                existing = [(key,value) for key,value in parse_qsl(parts.query, keep_blank_values=True) if key not in parameters]
                return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(existing + list(parameters.items())), parts.fragment))
        tag = current_app.config.get('AMAZON_ASSOCIATE_TAG', '').strip()
        if host in ('amazon.com','smile.amazon.com') and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', tag):
            query = [(key,value) for key,value in parse_qsl(parts.query,keep_blank_values=True) if key.lower() != 'tag']
            return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query+[('tag',tag)]),parts.fragment))
    except ValueError:
        pass
    return url
