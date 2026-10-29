"""Signed recipient-controlled opt-out for all application email."""
from email.utils import getaddresses
from html import escape
import smtplib
from flask import current_app, request, jsonify
from itsdangerous import URLSafeSerializer, BadSignature
from sqlalchemy.exc import IntegrityError
from .api import api, error, normalized_email
from .extensions import db, limiter
from .models import EmailSuppression


class EmailSuppressed(smtplib.SMTPException):
    pass


def serializer():
    return URLSafeSerializer(current_app.config['SECRET_KEY'], salt='email-preferences-v1')


def preference_link(email):
    token = serializer().dumps({'email': email.strip().lower()})
    return current_app.config['FRONTEND_ORIGIN'].rstrip('/')+'/email-preferences/'+token


def suppressed(email):
    return EmailSuppression.query.filter_by(email=email.strip().lower()).first() is not None


def set_suppression(email, unsubscribed, source='recipient'):
    row = EmailSuppression.query.filter_by(email=email).with_for_update().first()
    if unsubscribed and row is None:
        db.session.add(EmailSuppression(email=email, source=source))
    elif not unsubscribed and row is not None:
        db.session.delete(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if not unsubscribed or not suppressed(email):
            raise


def finalize_message(message):
    if getattr(message, '_email_preferences_added', False):
        return
    recipients = getaddresses(message.get_all('To', []))
    if len(recipients) != 1:
        raise ValueError('Application emails must have one recipient.')
    link = preference_link(recipients[0][1])
    plain = message.get_body(preferencelist=('plain',))
    if plain:
        plain.set_content(plain.get_content().rstrip()+'\n\nEmail preferences: unsubscribe from all Gather & Gift emails to this address:\n'+link+'\n')
    html = message.get_body(preferencelist=('html',))
    if html:
        footer = '<hr><p style="font-size:12px;color:#666"><a href="'+escape(link, quote=True)+'">Unsubscribe from all emails</a> to this address, or manage email preferences.</p>'
        content = html.get_content()
        html.set_content(content.replace('</body>',footer+'</body>') if '</body>' in content else content+footer, subtype='html')
    if 'List-Unsubscribe' not in message:
        message['List-Unsubscribe'] = '<'+link+'>'
    message._email_preferences_added = True


def check_delivery(message):
    addresses = getaddresses(message.get_all('To', [])+message.get_all('Cc', [])+message.get_all('Bcc', []))
    if any(suppressed(email) for _,email in addresses):
        raise EmailSuppressed('Email delivery is turned off for this recipient.')


@api.route('/email-preferences/<token>', methods=['GET','POST'])
@limiter.limit('30 per hour')
def recipient_email_preferences(token):
    try:
        email = serializer().loads(token)['email']
        if not normalized_email(email):
            raise BadSignature('Invalid email')
    except (BadSignature, KeyError, TypeError, ValueError):
        return error('This email preferences link is invalid.', 400)
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        if type(payload.get('unsubscribed')) is not bool:
            return error('Choose whether to stop or resume emails.', 400)
        set_suppression(email, payload['unsubscribed'])
    return jsonify(email=email, unsubscribed=suppressed(email))
