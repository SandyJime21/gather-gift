"""Reviewed, scheduled advertisements with server-priced Stripe Checkout."""
import hashlib
import hmac
import json
import secrets
import time
import ssl
from pathlib import Path
from flask import send_file, abort
import certifi
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from flask import Blueprint, current_app, jsonify, request, session
from .extensions import db, limiter
from .models import AdCampaign, User, SavedGift, PersonalWish, WishlistItem, AdvertisingRequest, AccountEmailCode
from .api import superuser_required, normalized_email, record_audit, consume_email_code, account_mail_available
from .invitation_mail import send_account_code, send_advertising_notification
from werkzeug.security import generate_password_hash
from .product_search import safe_product_url

ad_api = Blueprint('advertising', __name__)


@ad_api.before_request
def protect_ads():
    user = db.session.get(User, session['user_id']) if session.get('user_id') else None
    if user and user.is_child:
        return jsonify(error='Advertising is for adults only.'), 403
    if request.method != 'GET' and request.endpoint != 'advertising.stripe_webhook':
        expected = session.get('csrf_token', '')
        if not expected or not secrets.compare_digest(expected, request.headers.get('X-CSRF-Token', '')):
            return jsonify(error='A valid CSRF token is required.'), 400
        if request.endpoint == 'advertising.submit_campaign' and request.mimetype == 'multipart/form-data':
            return
        if not isinstance(request.get_json(silent=True), dict):
            return jsonify(error='JSON object required.'), 400


def config_rate():
    try:
        return max(0, int(current_app.config.get('ADS_DAILY_RATE_CENTS', 0)))
    except (ValueError, TypeError):
        return 0


def validate_campaign(payload):
    data = {}
    for field, limit in [('business_name', 160), ('title', 160), ('description', 500)]:
        value = payload.get(field, '')
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError('Enter a valid business name, ad title, and short description.')
        data[field] = value.strip()
    data['email'] = normalized_email(payload.get('email'))
    if not data['email']:
        raise ValueError('Enter a business contact email.')
    for field in ('business_url', 'media_url'):
        data[field] = safe_product_url(payload.get(field))
        if not data[field]:
            raise ValueError('Use HTTPS business and creative URLs.')
    data['media_type'] = payload.get('media_type')
    if data['media_type'] not in ('image', 'video'):
        raise ValueError('Choose image or video creative.')
    for key, allowed in [('placements', {'home', 'wishlist', 'following', 'discover'}), ('weekdays', set(range(7)))]:
        values = payload.get(key)
        if not isinstance(values, list) or not values or any(type(value) not in (str if key == 'placements' else int,) or value not in allowed for value in values):
            raise ValueError('Choose valid placements and days of the week.')
        data[key] = sorted(set(values))
    try:
        zone = ZoneInfo(payload.get('timezone', 'America/Los_Angeles'))
        start, end = date.fromisoformat(payload['start_date']), date.fromisoformat(payload['end_date'])
        if start < datetime.now(zone).date() or end < start or (end - start).days > 365:
            raise ValueError()
        start_time, end_time = payload['start_time'], payload['end_time']
        if datetime.strptime(start_time, '%H:%M').strftime('%H:%M') != start_time or datetime.strptime(end_time, '%H:%M').strftime('%H:%M') != end_time:
            raise ValueError()
        if start_time >= end_time:
            raise ValueError()
        duration = payload.get('display_seconds', 15)
        if type(duration) is not int or not 5 <= duration <= 120:
            raise ValueError()
    except (ValueError, TypeError, KeyError, ZoneInfoNotFoundError):
        raise ValueError('Choose valid future dates, a same-day time window, timezone, and display length of 5-120 seconds.')
    data.update(start_date=start.isoformat(), end_date=end.isoformat(), start_time=start_time, end_time=end_time,
        timezone=zone.key, display_seconds=duration)
    keywords = payload.get('keywords', [])
    if not isinstance(keywords, list) or len(keywords) > 20 or any(not isinstance(word, str) or not 1 <= len(word.strip()) <= 40 for word in keywords):
        raise ValueError('Use up to 20 keywords, each at most 40 characters.')
    data['keywords'] = sorted(set(word.strip().lower() for word in keywords))
    days = sum((start + timedelta(days=offset)).weekday() in data['weekdays'] for offset in range((end-start).days + 1))
    if not days:
        raise ValueError('No selected weekdays occur in this date range.')
    data['scheduled_days'] = days
    return data


def placement_rates():
    rates = {}
    for key in ('home', 'wishlist', 'following', 'discover'):
        try:
            rates[key] = max(0, int(current_app.config.get('ADS_' + key.upper() + '_DAILY_RATE_CENTS') or config_rate()))
        except (ValueError, TypeError):
            rates[key] = 0
    return rates


def price_campaign(data):
    rates = placement_rates()
    lines = [{'placement': key, 'daily_rate_cents': rates[key], 'days': data['scheduled_days'], 'amount_cents': rates[key] * data['scheduled_days']} for key in data['placements']]
    return {'pricing': lines, 'amount_cents': sum(line['amount_cents'] for line in lines), 'pricing_configured': all(line['daily_rate_cents'] > 0 for line in lines)}


@ad_api.get('/ads/creative/<int:campaign_id>')
def creative(campaign_id):
    row = db.session.get(AdCampaign, campaign_id)
    user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
    allowed = row and ((row.status == 'approved' and row.paid) or (user and user.is_superuser) or authorized_campaign(campaign_id, request.args.get('token')))
    if not allowed or not row.data.get('creative_file'):
        abort(404)
    response = send_file(Path(current_app.config['UPLOAD_FOLDER']) / 'advertising' / row.data['creative_file'], conditional=True)
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def campaign_dict(row):
    data = {key: value for key, value in row.data.items() if key != 'creative_file'}
    return {'id': row.id, **data, 'status': row.status, 'paid': row.paid, 'amount_cents': row.amount_cents, 'currency': 'usd'}


def authorized_campaign(campaign_id, token):
    if not isinstance(token, str) or len(token) > 100:
        return None
    return AdCampaign.query.filter_by(id=campaign_id, token_hash=hashlib.sha256(token.encode()).hexdigest()).first()


@ad_api.get('/ads/config')
def ad_config():
    return jsonify(placement_rates=placement_rates(), rotation_mode='shared_top_banner', daily_rate_cents=config_rate(), currency='usd', checkout_enabled=bool(current_app.config.get('STRIPE_SECRET_KEY') and current_app.config.get('STRIPE_WEBHOOK_SECRET') and any(placement_rates().values())))


@ad_api.post('/ads/campaigns')
@limiter.limit('5 per hour')
def submit_campaign():
    try:
        payload = request.get_json(silent=True) if request.is_json else json.loads(request.form.get('payload', '{}'))
        upload = request.files.get('creative')
        if upload:
            payload['media_url'] = 'https://placeholder.example/creative'
        data = validate_campaign(payload)
        if upload:
            raw = upload.read(7 * 1024 * 1024 + 1)
            suffix = Path(upload.filename or '').suffix.lower()
            valid = (suffix in ('.jpg', '.jpeg') and raw.startswith(b'\xff\xd8\xff')) or (suffix == '.png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (suffix == '.webp' and raw.startswith(b'RIFF') and raw[8:12] == b'WEBP') or (suffix == '.mp4' and raw[4:8] == b'ftyp') or (suffix == '.webm' and raw.startswith(b'\x1a\x45\xdf\xa3'))
            expected_type = 'video' if suffix in ('.mp4', '.webm') else 'image'
            if not valid or len(raw) > 7 * 1024 * 1024 or data['media_type'] != expected_type:
                raise ValueError('Upload a matching JPEG, PNG, WebP, MP4 or WebM file up to 7 MB.')
        price = price_campaign(data)
        data.update(pricing=price['pricing'], pricing_configured=price['pricing_configured'])
    except (ValueError, TypeError, AttributeError) as exc:
        return jsonify(error=str(exc)), 400
    token = secrets.token_urlsafe(32)
    row = AdCampaign(token_hash=hashlib.sha256(token.encode()).hexdigest(), data=data,
        amount_cents=price['amount_cents'])
    db.session.add(row); db.session.flush()
    if upload:
        folder = Path(current_app.config['UPLOAD_FOLDER']) / 'advertising'
        folder.mkdir(parents=True, exist_ok=True)
        name = secrets.token_hex(24) + suffix
        (folder / name).write_bytes(raw)
        row.data = {**data, 'creative_file': name, 'media_url': '/api/ads/creative/' + str(row.id)}
    record_advertising_request(data['business_name'], data['email'], data['business_name'], data['title']+'\n\n'+data['description'], row.id)
    result = campaign_dict(row)
    if upload:
        result['media_url'] += '?token=' + token
    return jsonify(campaign=result, token=token), 201


@ad_api.post('/ads/campaigns/<int:campaign_id>/status')
@limiter.limit('30 per minute')
def campaign_status(campaign_id):
    row = authorized_campaign(campaign_id, request.get_json().get('token'))
    if not row:
        return jsonify(error='Campaign not found.'), 404
    result = campaign_dict(row)
    if row.data.get('creative_file'):
        result['media_url'] += '?token=' + request.get_json()['token']
    return jsonify(campaign=result)


@ad_api.post('/ads/campaigns/<int:campaign_id>/checkout')
@limiter.limit('10 per hour')
def campaign_checkout(campaign_id):
    row = authorized_campaign(campaign_id, request.get_json().get('token'))
    if not row:
        return jsonify(error='Campaign not found.'), 404
    if row.status != 'approved' or row.paid:
        return jsonify(error='The campaign must be approved and unpaid before checkout.'), 409
    if row.data['start_date'] < datetime.now(ZoneInfo(row.data['timezone'])).date().isoformat():
        return jsonify(error='The start date has passed. Submit a campaign with new dates.'), 409
    key = current_app.config.get('STRIPE_SECRET_KEY')
    if not key or not current_app.config.get('STRIPE_WEBHOOK_SECRET') or row.amount_cents < 50:
        return jsonify(error='Payments are not configured yet. Contact the advertising team.'), 503
    origin = current_app.config['FRONTEND_ORIGIN'].rstrip('/')
    token = request.get_json()['token']
    path = origin + '/advertise?campaign=' + str(row.id) + '&token=' + token
    fields = {'mode': 'payment', 'payment_method_types[0]': 'card', 'customer_email': row.data['email'],
        'success_url': path + '&checkout=returned', 'cancel_url': path,
        'metadata[campaign_id]': row.id, 'line_items[0][quantity]': 1,
        'line_items[0][price_data][currency]': 'usd', 'line_items[0][price_data][unit_amount]': row.amount_cents,
        'line_items[0][price_data][product_data][name]': 'Advertising: ' + row.data['title']}
    req = Request('https://api.stripe.com/v1/checkout/sessions', data=urlencode(fields).encode(),
        headers={'Authorization': 'Bearer ' + key, 'Idempotency-Key': 'ad-campaign-' + str(row.id), 'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urlopen(req, timeout=15, context=ssl.create_default_context(cafile=certifi.where())) as response:
            checkout = json.loads(response.read(100000))
        if not checkout.get('id') or not str(checkout.get('url', '')).startswith('https://checkout.stripe.com/'):
            raise ValueError()
    except (OSError, ValueError):
        return jsonify(error='Could not open payment checkout. Please try again.'), 502
    row.stripe_session_id = checkout['id']; db.session.commit()
    return jsonify(url=checkout['url'])


@ad_api.post('/ads/stripe-webhook')
def stripe_webhook():
    secret = current_app.config.get('STRIPE_WEBHOOK_SECRET', '')
    if not secret:
        return jsonify(error='Webhook unavailable.'), 503
    raw = request.get_data()
    parts = request.headers.get('Stripe-Signature', '').split(',')
    values = [part.split('=', 1) for part in parts if '=' in part]
    try:
        timestamp = next(value for key, value in values if key == 't')
        if abs(time.time() - int(timestamp)) > 300:
            raise ValueError()
        expected = hmac.new(secret.encode(), timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
        if not any(key == 'v1' and hmac.compare_digest(expected, value) for key, value in values):
            raise ValueError()
        event = json.loads(raw)
    except (ValueError, StopIteration):
        return jsonify(error='Invalid webhook signature.'), 400
    from .letter_art import handle_payment_event
    letter_result=handle_payment_event(event)
    if letter_result is not None:
        return letter_result
    if event.get('type') in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
        checkout = event.get('data', {}).get('object', {})
        row = AdCampaign.query.filter_by(stripe_session_id=checkout.get('id')).with_for_update().first() if checkout.get('id') else None
        if not row and checkout.get('metadata', {}).get('campaign_id'):
            return jsonify(error='Checkout is not recorded yet. Retry this event.'), 409
        if row and checkout.get('payment_status') == 'paid' and checkout.get('amount_total') == row.amount_cents and checkout.get('currency') == 'usd' and str(checkout.get('metadata', {}).get('campaign_id')) == str(row.id):
            row.paid = True; row.payment_intent = checkout.get('payment_intent'); db.session.commit()
    elif event.get('type') in ('charge.refunded', 'charge.dispute.created'):
        intent = event.get('data', {}).get('object', {}).get('payment_intent')
        if intent:
            AdCampaign.query.filter_by(payment_intent=intent).update({'paid': False, 'status': 'paused'})
            db.session.commit()
    return jsonify(received=True)


@ad_api.get('/support/ads')
@superuser_required
def review_campaigns():
    return jsonify(campaigns=[campaign_dict(row) for row in AdCampaign.query.order_by(AdCampaign.id.desc()).limit(100)])


@ad_api.patch('/support/ads/<int:campaign_id>')
@superuser_required
def review_campaign(campaign_id):
    row = db.session.get(AdCampaign, campaign_id)
    status = request.get_json().get('status')
    if not row or status not in ('approved', 'rejected', 'paused'):
        return jsonify(error='Choose a valid campaign and review decision.'), 400
    if status == 'approved' and not row.amount_cents:
        row.amount_cents = config_rate() * row.data['scheduled_days'] * len(row.data['placements'])
    if status == 'approved' and (row.amount_cents < 50 or row.data.get('pricing_configured') is False):
        return jsonify(error='Configure advertising pricing before approving.'), 400
    row.status = status
    AdvertisingRequest.query.filter_by(campaign_id=row.id, status='new').update({'status':'reviewed', 'reviewed_at':datetime.now(timezone.utc)})
    record_audit(request.current_user.id, 'advertisement.' + status, 'ad_campaign', row.id)
    db.session.commit()
    return jsonify(campaign=campaign_dict(row))


def is_scheduled(row, now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(row.data['timezone']))
    return row.data['start_date'] <= local.date().isoformat() <= row.data['end_date'] and local.weekday() in row.data['weekdays'] and row.data['start_time'] <= local.strftime('%H:%M') < row.data['end_time']


@ad_api.get('/ads/active')
def active_ads():
    placement = request.args.get('placement')
    if placement not in ('home', 'wishlist', 'following', 'discover'):
        return jsonify(ads=[])
    query = request.args.get('q', '').lower()[:200]
    result = []
    interests = ''
    user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
    if placement == 'discover' and user:
        saved_ids = db.session.query(SavedGift.item_id).filter_by(user_id=user.id)
        own_ids = db.session.query(PersonalWish.item_id).filter_by(owner_id=user.id)
        items = WishlistItem.query.filter(db.or_(WishlistItem.id.in_(saved_ids), WishlistItem.id.in_(own_ids))).order_by(WishlistItem.id.desc()).limit(40).all()
        interests = ' '.join(' '.join(filter(None, [item.name, item.category, item.store_name])) for item in items).lower()
    for row in AdCampaign.query.filter_by(status='approved', paid=True).order_by(AdCampaign.id.desc()).limit(100):
        data = row.data
        if placement in data['placements'] and is_scheduled(row) and (not data['keywords'] or any(word.lower() in (query or interests) for word in data['keywords'])):
            result.append({'id': row.id, '_score': sum(word.lower() in interests for word in data['keywords']), **{key: data[key] for key in ('business_name', 'title', 'description', 'media_type', 'media_url', 'business_url', 'display_seconds')}})
    result.sort(key=lambda ad: ad['_score'], reverse=True)
    for ad in result:
        ad.pop('_score', None)
    return jsonify(ads=result)


def advertising_request_dict(row):
    return dict(id=row.id, name=row.name, email=row.email, business_name=row.business_name,
        message=row.message, campaign_id=row.campaign_id, status=row.status,
        email_delivery=row.email_delivery, created_at=row.created_at.isoformat())


def advertising_alert_settings(user):
    return (user.notification_preferences or {}).get('advertising_alerts') or {}


def notify_advertising_request(row):
    recipients = [advertising_alert_settings(user) for user in User.query.filter_by(is_support=True, is_superuser=True).all()]
    verified = [value for value in recipients if value.get('verified_at') and value.get('email')]
    recipients = [value for value in verified if value.get('enabled')]
    if not recipients:
        row.email_delivery = 'disabled' if verified else 'no_verified_recipient'
    elif not account_mail_available():
        row.email_delivery = 'not_configured'
    else:
        portal_url = current_app.config['FRONTEND_ORIGIN'].rstrip('/') + '/support?advertising_request=' + str(row.id)
        deliveries = []
        for value in recipients:
            try:
                deliveries.append(send_advertising_notification(value['email'], value.get('name', ''), row, portal_url))
            except Exception:
                current_app.logger.warning('Advertising email delivery failed; request %s remains in the portal.', row.id)
                deliveries.append(False)
        row.email_delivery = 'sent' if all(deliveries) else 'partial' if any(deliveries) else 'failed'
    db.session.commit()


def record_advertising_request(name, email, business, message, campaign_id=None):
    row = AdvertisingRequest(name=name, email=email, business_name=business, message=message, campaign_id=campaign_id)
    db.session.add(row)
    db.session.commit()
    notify_advertising_request(row)
    return row


@ad_api.post('/ads/requests')
@limiter.limit('5 per hour')
def submit_advertising_request():
    payload = request.get_json()
    values = {}
    for key, maximum, required in [('name', 120, True), ('business_name', 160, False), ('message', 4000, True)]:
        value = payload.get(key, '')
        if not isinstance(value, str) or len(value.strip()) > maximum or (required and not value.strip()):
            return jsonify(error='Enter your name and message within the displayed limits.'), 400
        values[key] = value.strip()
    email = normalized_email(payload.get('email'))
    if not email:
        return jsonify(error='Enter a valid contact email.'), 400
    row = record_advertising_request(values['name'], email, values['business_name'], values['message'])
    return jsonify(request_id=row.id, message='Your advertising request has been sent to our team. We will reply using your contact email.'), 201


@ad_api.get('/support/advertising-requests')
@superuser_required
def advertising_requests():
    rows = AdvertisingRequest.query.order_by(AdvertisingRequest.created_at.desc()).limit(100).all()
    return jsonify(requests=[advertising_request_dict(row) for row in rows], new_count=AdvertisingRequest.query.filter_by(status='new').count())


@ad_api.patch('/support/advertising-requests/<int:request_id>')
@superuser_required
def update_advertising_request(request_id):
    row = db.session.get(AdvertisingRequest, request_id)
    status = request.get_json().get('status')
    if not row or status not in ('new', 'reviewed', 'closed'):
        return jsonify(error='Choose a request and a valid status.'), 400
    row.status = status
    row.reviewed_at = None if status == 'new' else datetime.now(timezone.utc)
    record_audit(request.current_user.id, 'advertising_request.'+status, 'advertising_request', row.id)
    db.session.commit()
    return jsonify(request=advertising_request_dict(row))


@ad_api.route('/support/advertising-alerts', methods=['GET', 'PATCH'])
@superuser_required
def advertising_alert_preferences():
    user = request.current_user
    settings = advertising_alert_settings(user)
    if request.method == 'PATCH':
        payload = request.get_json()
        if set(payload) != {'enabled'} or type(payload['enabled']) is not bool or not settings.get('verified_at'):
            return jsonify(error='Confirm your notification email before enabling alerts.'), 400
        settings = {**settings, 'enabled':payload['enabled']}
        user.notification_preferences = {**(user.notification_preferences or {}), 'advertising_alerts': settings}
        db.session.commit()
    return jsonify(settings=settings, mail_available=account_mail_available())


@ad_api.post('/support/advertising-alerts/verify-email')
@superuser_required
@limiter.limit('3 per hour')
def request_advertising_alert_verification():
    user = request.current_user
    payload = request.get_json()
    email = normalized_email(payload.get('email'))
    name = payload.get('name', '')
    if not email or not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        return jsonify(error='Enter a name and valid notification email.'), 400
    if not account_mail_available():
        return jsonify(error='Email delivery is not configured. Requests will still appear in the developer portal.'), 503
    now = datetime.now(timezone.utc)
    AccountEmailCode.query.filter_by(user_id=user.id, purpose='ads_alert_email', used_at=None).update({'used_at': now})
    code = str(secrets.randbelow(1000000)).zfill(6)
    challenge = AccountEmailCode(id=secrets.token_urlsafe(24), user_id=user.id, purpose='ads_alert_email',
        target_email=email, pending_data={'name': name.strip()}, code_hash=generate_password_hash(code),
        expires_at=now+timedelta(minutes=10), session_version=user.session_version)
    db.session.add(challenge)
    db.session.commit()
    try:
        delivered = send_account_code(email, code, 'ads_alert_email')
    except Exception:
        current_app.logger.warning('Advertising email confirmation could not be delivered.')
        delivered = False
    if not delivered:
        challenge.used_at = now
        db.session.commit()
        return jsonify(error='The verification code could not be delivered. Try again later.'), 503
    return jsonify(challenge_id=challenge.id, message='A confirmation code was sent to your notification email. It expires in 10 minutes.')


@ad_api.post('/support/advertising-alerts/confirm-email')
@superuser_required
@limiter.limit('10 per minute')
def confirm_advertising_alert_email():
    user = request.current_user
    payload = request.get_json()
    email = normalized_email(payload.get('email'))
    if not email:
        return jsonify(error='Enter the email you are confirming.'), 400
    challenge, failure = consume_email_code(payload.get('challenge_id'), payload.get('code'), 'ads_alert_email', user, email)
    if failure:
        return failure
    settings = {'name':challenge.pending_data['name'], 'email':email, 'enabled':True, 'verified_at':datetime.now(timezone.utc).isoformat()}
    user.notification_preferences = {**(user.notification_preferences or {}), 'advertising_alerts':settings}
    record_audit(user.id, 'advertising_alert.email_confirmed', 'user', user.id)
    db.session.commit()
    return jsonify(settings=settings, message='Notification email confirmed. New advertising requests will appear here and be emailed to you.')
