"""Developer-managed letter art and one-time family unlocks."""
import json
import hashlib
import re
import ssl
from datetime import datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import certifi
from flask import current_app,jsonify,request
from .api import api,authenticated,superuser_required,error,save_profile_image
from .extensions import db,limiter
from .models import SharedTheme,LetterArtPurchase,Household,AuditLog
from .wishlist_letters import managed_home


def theme_metadata(payload,previous=None):
    previous=previous or {}
    purpose=payload.get('purpose',previous.get('purpose','app'))
    if purpose not in ('app','letter','list'):
        raise ValueError('Choose app theme, family list background or wishlist letter art.')
    try:
        price=Decimal(str(payload.get('price',Decimal(previous.get('price_cents',0))/100)))
        if not price.is_finite() or price<0 or price>1000 or price*100 != (price*100).to_integral_value() or (price>0 and price<Decimal('0.50')):
            raise ValueError()
    except (InvalidOperation,ValueError,TypeError):
        raise ValueError('Choose Free or a USD price from 0.50 to 1000.00, with at most two decimal places.')
    if purpose in ('app','list') and price:
        raise ValueError('Prices are available for letter art. App themes remain free.')
    active=payload.get('active',previous.get('active',True))
    if active in ('true','false'):
        active=active=='true'
    if type(active) is not bool:
        raise ValueError('Choose whether this design is available.')
    if purpose=='letter' and payload.get('audience',previous.get('audience','everyone'))=='adults':
        raise ValueError('Letter art must be suitable for children or everyone.')
    return dict(purpose=purpose,price_cents=int(price*100),currency='usd',active=active)


def public_art(row):
    return dict(id=row.id,key='t'+str(row.id),**{key:row.data.get(key) for key in ['name','season','background','foreground','accent','art']},
                price_cents=row.data.get('price_cents',0),currency='usd',active=row.data.get('active',True))


def unlocked(home_id,theme_id):
    return LetterArtPurchase.query.filter_by(household_id=home_id,theme_id=theme_id,paid=True,revoked=False).first() is not None


def validate_letter_art(home_id,theme_id,existing_id=None):
    if theme_id is None:
        return None
    row=db.session.get(SharedTheme,theme_id) if type(theme_id) is int else None
    if not row or row.data.get('purpose','app')!='letter':
        raise ValueError('Choose a valid letter design.')
    owned=unlocked(home_id,row.id)
    if not row.data.get('active',True) and not owned and row.id!=existing_id:
        raise ValueError('This letter design is no longer available.')
    if row.data.get('price_cents',0)>0 and not owned and row.id!=existing_id:
        raise PermissionError('Unlock this design for your family before using it.')
    return row


def remember_free_art(home_id,row,user_id):
    if row and row.data.get('price_cents',0)==0 and not unlocked(home_id,row.id):
        db.session.add(LetterArtPurchase(household_id=home_id,theme_id=row.id,buyer_user_id=user_id,
            art_name=row.data['name'],amount_cents=0,currency='usd',paid=True,expires_at=datetime.now(timezone.utc)))


@api.get('/support/themes')
@superuser_required
def developer_theme_catalog():
    return jsonify(themes=[dict(key='t'+str(row.id),id=row.id,**row.data) for row in SharedTheme.query.order_by(SharedTheme.id.desc()).all() if row.data.get('purpose')!='site-palette'])


@api.patch('/support/themes/<int:theme_id>')
@superuser_required
def update_developer_theme(theme_id):
    row=db.session.get(SharedTheme,theme_id)
    if not row:
        return error('Design not found.',404)
    payload=request.get_json(silent=True) if request.is_json else request.form
    payload=payload or {}
    previous=row.data
    name=payload.get('name',previous.get('name',''))
    if not isinstance(name,str):
        return error('Enter a valid design name.',400)
    name=name.strip()
    audience=payload.get('audience',previous.get('audience','everyone'))
    colors={key:payload.get(key,previous.get(key,'')) for key in ('background','foreground','accent')}
    if not name or len(name)>80 or audience not in ('adults','kids','everyone') or any(not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value) for value in colors.values()):
        return error('Enter a name, audience and valid colors.',400)
    if 'season' in payload and not isinstance(payload.get('season'),str):
        return error('Enter a valid season or occasion.',400)
    try:
        metadata=theme_metadata(payload,previous)
    except ValueError as exc:
        return error(str(exc),400)
    if previous.get('purpose','app')!=metadata['purpose']:
        return error('A published design cannot change category. Publish a new design instead.',400)
    image=previous.get('image_path')
    if request.files.get('image'):
        image,failure=save_profile_image(request.files['image'],request.current_user.id)
        if failure:
            return error(failure,400)
    row.data={**previous,**metadata,**colors,'name':name,'audience':audience,'season':payload.get('season',previous.get('season',''))[:80],
              'image_path':image,'art':'/api/themes/'+str(row.id)+'/art' if image else None}
    db.session.commit()
    return jsonify(theme=dict(id=row.id,key='t'+str(row.id),**row.data))


@api.get('/households/<int:home_id>/letter-art')
@authenticated
def letter_art_catalog(home_id):
    failure=managed_home(home_id)
    if failure:
        return failure
    rows=SharedTheme.query.order_by(SharedTheme.id.desc()).all()
    designs=[]
    for row in rows:
        if row.data.get('purpose','app')!='letter':
            continue
        owned=unlocked(home_id,row.id)
        if not row.data.get('active',True) and not owned:
            continue
        designs.append(dict(**public_art(row),unlocked=owned or row.data.get('price_cents',0)==0))
    return jsonify(designs=designs,checkout_enabled=bool(current_app.config.get('STRIPE_SECRET_KEY') and current_app.config.get('STRIPE_WEBHOOK_SECRET')))


@api.post('/households/<int:home_id>/letter-art/<int:theme_id>/checkout')
@authenticated
@limiter.limit('10 per hour')
def letter_art_checkout(home_id,theme_id):
    failure=managed_home(home_id)
    if failure:
        return failure
    Household.query.filter_by(id=home_id).with_for_update().first()
    row=db.session.get(SharedTheme,theme_id)
    if not row or row.data.get('purpose','app')!='letter' or not row.data.get('active',True):
        return error('Letter design not found.',404)
    if row.data.get('price_cents',0)==0 or unlocked(home_id,theme_id):
        return jsonify(unlocked=True)
    key=current_app.config.get('STRIPE_SECRET_KEY')
    if not key or not current_app.config.get('STRIPE_WEBHOOK_SECRET'):
        return error('Paid designs are unavailable right now. You can choose free letter art.',503)
    now=datetime.now(timezone.utc)
    purchase=LetterArtPurchase.query.filter(LetterArtPurchase.household_id==home_id,LetterArtPurchase.theme_id==theme_id,
        LetterArtPurchase.paid.is_(False),LetterArtPurchase.revoked.is_(False),LetterArtPurchase.amount_cents==row.data['price_cents'],LetterArtPurchase.expires_at>now).order_by(LetterArtPurchase.id.desc()).first()
    if purchase and purchase.checkout_url:
        return jsonify(url=purchase.checkout_url)
    if not purchase:
        purchase=LetterArtPurchase(household_id=home_id,theme_id=theme_id,buyer_user_id=request.current_user.id,
            art_name=row.data['name'],amount_cents=row.data['price_cents'],currency='usd',expires_at=now+timedelta(hours=24))
        db.session.add(purchase)
    db.session.commit()
    origin=current_app.config['FRONTEND_ORIGIN'].rstrip('/')
    back=origin+'/settings?tab=account&letter_family='+str(home_id)
    fields={'mode':'payment','payment_method_types[0]':'card','success_url':back+'&letter_art_checkout=returned','cancel_url':back+'&letter_art_checkout=cancelled',
        'metadata[letter_art_purchase_id]':purchase.id,'metadata[household_id]':home_id,'metadata[theme_id]':theme_id,
        'line_items[0][quantity]':1,'line_items[0][price_data][currency]':purchase.currency,
        'line_items[0][price_data][unit_amount]':purchase.amount_cents,'line_items[0][price_data][product_data][name]':'Family letter art: '+purchase.art_name}
    req=Request('https://api.stripe.com/v1/checkout/sessions',data=urlencode(fields).encode(),headers={
        'Authorization':'Bearer '+key,'Idempotency-Key':'letter-art-'+str(purchase.id),'Content-Type':'application/x-www-form-urlencoded'})
    try:
        with urlopen(req,timeout=15,context=ssl.create_default_context(cafile=certifi.where())) as response:
            checkout=json.loads(response.read(100000))
        if not checkout.get('id') or not str(checkout.get('url','')).startswith('https://checkout.stripe.com/'):
            raise ValueError()
    except (OSError,ValueError):
        return error('Could not open checkout. Please try again or choose free art.',502)
    purchase.stripe_session_id=checkout['id'];purchase.checkout_url=checkout['url']
    if type(checkout.get('expires_at')) is int:
        purchase.expires_at=datetime.fromtimestamp(checkout['expires_at'],timezone.utc)
    db.session.commit()
    return jsonify(url=checkout['url'])


def payment_marker(checkout_id):
    return hashlib.sha256(str(checkout_id).encode()).hexdigest()


def remember_fulfilled(checkout_id):
    if checkout_id and not AuditLog.query.filter_by(action='letter_art.fulfilled', entity_id=payment_marker(checkout_id)).first():
        db.session.add(AuditLog(action='letter_art.fulfilled', entity_type='payment', entity_id=payment_marker(checkout_id), details={}))


def refund_unavailable_purchase(checkout):
    """A signed checkout paid after deletion must not charge for missing art."""
    if checkout.get('payment_status') != 'paid':
        return jsonify(received=True)
    marker = payment_marker(checkout.get('id'))
    if AuditLog.query.filter(AuditLog.entity_id == marker, AuditLog.action.in_(('letter_art.fulfilled', 'letter_art.refunded'))).first():
        return jsonify(received=True)
    intent = checkout.get('payment_intent')
    key = current_app.config.get('STRIPE_SECRET_KEY')
    if not key or not isinstance(intent, str) or not re.fullmatch(r'pi_[A-Za-z0-9_]+', intent):
        return jsonify(error='Refund is not ready. Retry this event.'), 503
    req = Request('https://api.stripe.com/v1/refunds',
        data=urlencode({'payment_intent': intent, 'reason': 'requested_by_customer',
                        'metadata[reason]': 'letter_art_no_longer_available'}).encode(),
        headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/x-www-form-urlencoded',
                 'Idempotency-Key': 'unavailable-letter-art-'+intent})
    try:
        with urlopen(req, timeout=15, context=ssl.create_default_context(cafile=certifi.where())) as response:
            result = json.loads(response.read(100000))
        if not result.get('id') or result.get('status') not in ('succeeded', 'pending'):
            raise ValueError()
    except HTTPError as exc:
        try:
            already_refunded = json.loads(exc.read(100000)).get('error', {}).get('code') == 'charge_already_refunded'
        except (ValueError, OSError):
            already_refunded = False
        if not already_refunded:
            return jsonify(error='Refund could not be confirmed. Retry this event.'), 502
    except (OSError, ValueError):
        return jsonify(error='Refund could not be confirmed. Retry this event.'), 502
    db.session.add(AuditLog(action='letter_art.refunded', entity_type='payment', entity_id=marker, details={}))
    db.session.commit()
    return jsonify(received=True)


def handle_payment_event(event):
    kind=event.get('type')
    checkout=event.get('data',{}).get('object',{})
    if kind in ('checkout.session.completed','checkout.session.async_payment_succeeded'):
        metadata=checkout.get('metadata') or {}
        marker=metadata.get('letter_art_purchase_id')
        row=LetterArtPurchase.query.filter_by(stripe_session_id=checkout.get('id')).with_for_update().first() if checkout.get('id') else None
        if not row:
            if not marker:
                return None
            pending=db.session.get(LetterArtPurchase,int(marker)) if str(marker).isdigit() else None
            return (jsonify(error='Letter checkout is not recorded yet. Retry this event.'),409) if pending else refund_unavailable_purchase(checkout)
        if str(marker)!=str(row.id) or str(metadata.get('household_id'))!=str(row.household_id) or str(metadata.get('theme_id'))!=str(row.theme_id) or checkout.get('amount_total')!=row.amount_cents or checkout.get('currency')!=row.currency:
            return jsonify(error='Letter payment does not match the purchase.'),400
        if checkout.get('payment_status')=='paid' and not row.revoked:
            row.paid=True;row.payment_intent=checkout.get('payment_intent')
            remember_fulfilled(row.stripe_session_id)
            db.session.commit()
        return jsonify(received=True)
    if kind in ('charge.refunded','charge.dispute.created'):
        intent=checkout.get('payment_intent')
        rows=LetterArtPurchase.query.filter_by(payment_intent=intent).with_for_update().all() if intent else []
        if rows:
            for row in rows:row.paid=False;row.revoked=True
            db.session.commit()
            return jsonify(received=True)
    return None
