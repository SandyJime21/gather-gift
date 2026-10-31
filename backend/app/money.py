"""Read-only money overview for the master support account: Stripe, ad revenue, affiliates, accounts."""
import json
import ssl
from urllib.request import Request, urlopen

import certifi
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_

from .api import superuser_required
from .extensions import db
from .models import AdCampaign, User, LetterArtPurchase

money_api = Blueprint('money', __name__)

RECOMMENDED_STORES = (('amazon.com', 'Amazon'), ('target.com', 'Target'), ('walmart.com', 'Walmart'))
AFFILIATE_DASHBOARDS = {
    'amazon.com': 'https://affiliate-program.amazon.com/',
    'target.com': 'https://partners.target.com/',
    'walmart.com': 'https://affiliates.walmart.com/',
}


def stripe_status():
    key = (current_app.config.get('STRIPE_SECRET_KEY') or '').strip()
    status = {
        'key_configured': bool(key),
        'webhook_configured': bool(current_app.config.get('STRIPE_WEBHOOK_SECRET')),
        'mode': 'live' if key.startswith(('sk_live_', 'rk_live_')) else 'test' if key.startswith(('sk_test_', 'rk_test_')) else 'unknown',
        'reachable': False,
        'available': [],
        'pending': [],
        'error': None,
    }
    if not key:
        status['error'] = 'STRIPE_SECRET_KEY is not set.'
        return status
    request_ = Request('https://api.stripe.com/v1/balance', headers={'Authorization': 'Bearer ' + key})
    try:
        with urlopen(request_, timeout=10, context=ssl.create_default_context(cafile=certifi.where())) as response:
            balance = json.loads(response.read(100000))
        status['reachable'] = True
        for field in ('available', 'pending'):
            status[field] = [
                {'currency': row.get('currency'), 'amount_cents': row.get('amount')}
                for row in balance.get(field, []) if isinstance(row, dict)
            ]
    except OSError as error:
        status['error'] = 'Stripe rejected the key or could not be reached (HTTP %s).' % getattr(error, 'code', 'network')
    except ValueError:
        status['error'] = 'Stripe returned an unexpected response.'
    if not status['webhook_configured']:
        status['error'] = status['error'] or 'STRIPE_WEBHOOK_SECRET is not set, so paid ads cannot be confirmed.'
    return status


def affiliate_status():
    try:
        rules = json.loads(current_app.config.get('STORE_AFFILIATE_RULES') or '{}')
    except ValueError:
        rules = {}
    rules = rules if isinstance(rules, dict) else {}
    configured = {host for host, rule in rules.items() if isinstance(rule, dict) and (rule.get('deeplink') or rule.get('query'))}
    if (current_app.config.get('AMAZON_ASSOCIATE_TAG') or '').strip():
        configured.add('amazon.com')
    stores = [
        {'host': host, 'label': label, 'configured': host in configured, 'dashboard_url': AFFILIATE_DASHBOARDS[host]}
        for host, label in RECOMMENDED_STORES
    ]
    others = sorted(host for host in configured if host not in dict(RECOMMENDED_STORES))
    return {
        'stores': stores,
        'other_configured_hosts': others,
        'note': 'Affiliate earnings are paid and reported by each store program; this app only rewrites outbound links.',
    }


def ad_revenue():
    rows = AdCampaign.query.order_by(AdCampaign.id.desc()).limit(200).all()
    paid = sum(row.amount_cents for row in rows if row.paid)
    awaiting = sum(row.amount_cents for row in rows if row.status == 'approved' and not row.paid)
    return {
        'paid_cents': paid,
        'awaiting_payment_cents': awaiting,
        'pending_review': sum(1 for row in rows if row.status == 'pending_review'),
        'campaigns': [{
            'id': row.id,
            'business_name': row.data.get('business_name'),
            'title': row.data.get('title'),
            'email': row.data.get('email'),
            'status': row.status,
            'amount_cents': row.amount_cents,
            'paid': row.paid,
            'payment_intent': row.payment_intent,
            'created_at': row.created_at.isoformat(),
        } for row in rows],
    }


@money_api.get('/support/money')
@superuser_required
def money_overview():
    purchases=LetterArtPurchase.query.filter(LetterArtPurchase.amount_cents>0).order_by(LetterArtPurchase.id.desc()).limit(200).all()
    paid_total=db.session.query(db.func.coalesce(db.func.sum(LetterArtPurchase.amount_cents),0)).filter(LetterArtPurchase.amount_cents>0,LetterArtPurchase.paid.is_(True),LetterArtPurchase.revoked.is_(False)).scalar()
    paid_count=LetterArtPurchase.query.filter(LetterArtPurchase.amount_cents>0,LetterArtPurchase.paid.is_(True),LetterArtPurchase.revoked.is_(False)).count()
    art=dict(paid_cents=int(paid_total),paid_count=paid_count,
        purchases=[dict(id=row.id,household_id=row.household_id,name=row.art_name,amount_cents=row.amount_cents,paid=row.paid,revoked=row.revoked,payment_intent=row.payment_intent) for row in purchases])
    return jsonify({'stripe': stripe_status(), 'ads': ad_revenue(), 'letter_art':art, 'affiliates': affiliate_status(), 'currency': 'usd'})


@money_api.get('/support/users')
@superuser_required
def list_user_accounts():
    query = User.query
    term = request.args.get('q', '').strip()[:100]
    if term:
        like = '%' + term.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
        query = query.filter(or_(User.name.ilike(like, escape='!'), User.email.ilike(like, escape='!')))
    rows = query.order_by(User.created_at.desc()).limit(200).all()
    return jsonify({
        'total': db.session.query(db.func.count(User.id)).scalar(),
        'users': [{
            'id': row.id,
            'name': row.name,
            'email': None if row.is_child else row.email,
            'kind': 'master' if row.is_superuser else 'staff' if row.is_support else 'child' if row.is_child else 'member',
            'created_at': row.created_at.isoformat(),
        } for row in rows],
    })
