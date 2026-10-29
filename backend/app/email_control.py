"""Master-only previews and self-addressed samples of the real email templates."""
import smtplib
from html import escape
from flask import request, jsonify, g, current_app
from .api import api, superuser_required, error, normalized_email, record_audit
from .extensions import db, limiter
from .models import EmailSuppression, EmailTemplateDesign
from .email_builder import DEFAULT_BLOCKS, validate_blocks, render_blocks
from .email_preferences import suppressed, set_suppression
from . import invitation_mail as mail

TEMPLATES = [
    ('family-invite','Family follow invitation'),
    ('adult-invite','Adult family invitation'),
    ('company-invite','Company wishlist invitation'),
    ('family-setup','Family setup invitation'),
    ('password-reset','Password reset link'),
    ('advertising-code','Advertising email verification code'),
    ('password-code','Password recovery code'),
    ('parent-pin-code','Parent PIN recovery code'),
    ('email-change-code','Main email change code'),
    ('password-approval','Password change approval'),
    ('photo-approval','Photo change approval'),
    ('game-invite','Gift game invitation'),
    ('co-buy-invite','Co-buy invitation'),
    ('advertising-request','Advertising request alert'),
    ('deletion-backup','Account deletion CSV backup'),
]


def sample_messages(to):
    from .sample_emails import send_all_samples
    previous = getattr(g, 'email_preview_collector', None)
    g.email_preview_collector = []
    try:
        send_all_samples(to)
        messages = list(g.email_preview_collector)
    finally:
        g.email_preview_collector = previous
    if len(messages) != len(TEMPLATES):
        raise RuntimeError('Email sample catalog must include each current template.')
    return dict(zip((key for key,_ in TEMPLATES), messages))


@api.get('/support/email-templates')
@superuser_required
def email_template_catalog():
    messages = sample_messages(request.current_user.email)
    rows = []
    for key,label in TEMPLATES:
        message = messages[key]
        plain = message.get_body(preferencelist=('plain',))
        html = message.get_body(preferencelist=('html',))
        text = plain.get_content() if plain else ''
        design = db.session.get(EmailTemplateDesign,key)
        rows.append(dict(id=key, label=label, subject=str(message['Subject']), text=text,
                         blocks=design.blocks if design else DEFAULT_BLOCKS,
                         html=html.get_content() if html else '<pre style="white-space:pre-wrap">'+escape(text)+'</pre>',
                         attachments=[part.get_filename() for part in message.iter_attachments()]))
    return jsonify(templates=rows, sample_email=request.current_user.email,
                   mail_configured=mail.mail_configured(), unsubscribed=suppressed(request.current_user.email))


@api.route('/support/email-templates/<key>/design', methods=['POST','DELETE'])
@superuser_required
def edit_email_design(key):
    if key not in dict(TEMPLATES):
        return error('Unknown email template.',404)
    row = db.session.get(EmailTemplateDesign,key)
    if request.method == 'DELETE':
        if row:
            db.session.delete(row)
    else:
        try:
            blocks = validate_blocks((request.get_json(silent=True) or {}).get('blocks'))
        except ValueError as exc:
            return error(str(exc),400)
        if row is None:
            row = EmailTemplateDesign(template_id=key)
            db.session.add(row)
        row.blocks = blocks
    record_audit(request.current_user.id,'email_templates.design_updated','email_template',details={'template_id':key,'reset':request.method=='DELETE'})
    db.session.commit()
    return jsonify(saved=True)


@api.post('/support/email-templates/<key>/preview')
@superuser_required
def preview_email_design(key):
    if key not in dict(TEMPLATES):
        return error('Unknown email template.',404)
    try:
        blocks = validate_blocks((request.get_json(silent=True) or {}).get('blocks'))
    except ValueError as exc:
        return error(str(exc),400)
    # Render the original content, not a previously wrapped design.
    previous = getattr(g,'email_design_disabled',False)
    g.email_design_disabled = True
    try:
        message = sample_messages(request.current_user.email)[key]
    finally:
        g.email_design_disabled = previous
    html = message.get_body(preferencelist=('html',))
    plain = message.get_body(preferencelist=('plain',))
    content = html.get_content() if html else '<pre>'+escape(plain.get_content())+'</pre>'
    return jsonify(html=render_blocks(blocks,content))


@api.post('/support/email-templates/send')
@superuser_required
@limiter.limit('20 per hour')
def send_email_samples():
    payload = request.get_json(silent=True) or {}
    ids = payload.get('template_ids')
    valid = {key for key,_ in TEMPLATES}
    if set(payload) != {'template_ids'} or not isinstance(ids,list) or not ids or any(not isinstance(key,str) or key not in valid for key in ids):
        return error('Choose valid email templates. Samples are sent only to your own staff email.', 400)
    if not mail.mail_configured():
        return error('Configure SMTP before sending samples. You can still preview every template here.', 503)
    email = request.current_user.email
    if suppressed(email):
        return error('Your email address is unsubscribed. Restore email delivery before sending samples.', 409)
    messages = sample_messages(email)
    sent = failed = 0
    for key in dict.fromkeys(ids):
        message = messages[key]
        message.replace_header('Subject', '[Template preview] '+str(message['Subject']))
        try:
            mail.deliver(message)
            sent += 1
        except (OSError,smtplib.SMTPException):
            failed += 1
    preview = bool(current_app.config.get('MAIL_OUTBOX_DIR'))
    record_audit(request.current_user.id, 'email_templates.sample_sent', 'email_template',
                 details={'template_ids':list(dict.fromkeys(ids)), 'sent':sent, 'failed':failed, 'preview':preview})
    db.session.commit()
    return jsonify(sent=0 if preview else sent, previewed=sent if preview else 0, failed=failed,
                   error='Sample emails could not be delivered.' if not sent else None), 200 if sent else 503


@api.route('/support/email-suppressions', methods=['GET','POST'])
@superuser_required
def manage_email_suppressions():
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        email = normalized_email(payload.get('email'))
        if not email or type(payload.get('unsubscribed')) is not bool:
            return error('Enter an email address and choose stop or restore delivery.', 400)
        set_suppression(email, payload['unsubscribed'], source='developer')
        record_audit(request.current_user.id, 'email_preferences.updated', 'email_suppression',
                     details={'email':email, 'unsubscribed':payload['unsubscribed']})
        db.session.commit()
    query = request.args.get('q','').strip()[:255]
    rows = EmailSuppression.query
    if query:
        rows = rows.filter(EmailSuppression.email.contains(query, autoescape=True))
    rows = rows.order_by(EmailSuppression.created_at.desc()).limit(100).all()
    return jsonify(addresses=[dict(email=row.email,source=row.source,created_at=row.created_at.isoformat()) for row in rows])
