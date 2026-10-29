"""Private family invitation messages and optional SMTP delivery."""
from datetime import datetime
from email.message import EmailMessage
from html import escape
from pathlib import Path
import re
import smtplib
import ssl
import certifi
from flask import current_app, g

GETTING_STARTED = (
    ("Make your wish list", "Add things you would love to receive, with links, prices and sizes, under My wishes."),
    ("Add your people", "Invite family and friends from Settings, then Family, and add birthdays and special days so nobody forgets."),
    ("Follow and discover", "Follow friends' lists in Following and browse gift ideas in Discover."),
    ("Shop in secret", "Reserve or buy a gift and it is marked for everyone else. The person you are shopping for never sees it. Find your gifts in Gifting."),
    ("Play together", "Start a gift exchange or Secret Santa draw in Games."),
    ("Need help?", "Tap the Help button in the corner of any page and ask a question, or send our team the chat."),
)

BUTTON_STYLE = 'display:inline-block;background:#5341a0;color:white;padding:14px 22px;border-radius:8px;text-decoration:none'
BODY_STYLE = 'font-family:Arial,sans-serif;color:#302b43;max-width:560px;margin:32px auto'


def intro_text():
    lines = ["How Gather & Gift works:"]
    lines += [f"{number}. {title}: {detail}" for number, (title, detail) in enumerate(GETTING_STARTED, 1)]
    return "\n".join(lines)


def intro_html():
    items = ''.join(f'<li><strong>{escape(title)}.</strong> {escape(detail)}</li>' for title, detail in GETTING_STARTED)
    return f'<h2 style="font-size:18px">How Gather &amp; Gift works</h2><ol style="padding-left:20px;line-height:1.5">{items}</ol>'


def mail_configured():
    config = current_app.config
    return bool(getattr(g, 'email_preview_collector', None) is not None or config.get('MAIL_OUTBOX_DIR') or (config.get('SMTP_HOST') and config.get('MAIL_FROM')))


def new_message(subject, to, template_id=None):
    message = EmailMessage()
    message._template_id = template_id
    message['Subject'] = subject
    message['From'] = current_app.config.get('MAIL_FROM') or 'Gather & Gift <noreply@example.com>'
    message['To'] = to
    return message


def deliver(message):
    """Send through SMTP, or write an .eml file when MAIL_OUTBOX_DIR is set (preview/testing)."""
    from .email_preferences import finalize_message, check_delivery
    from .email_builder import apply_design
    apply_design(message)
    finalize_message(message)
    collector = getattr(g, 'email_preview_collector', None)
    if collector is not None:
        collector.append(message)
        return
    check_delivery(message)
    outbox = current_app.config.get('MAIL_OUTBOX_DIR')
    if outbox:
        folder = Path(outbox)
        folder.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r'[^a-z0-9]+', '-', str(message['Subject']).lower()).strip('-')[:60]
        (folder / f"{datetime.now().strftime('%H%M%S%f')}-{slug}.eml").write_bytes(bytes(message))
        return
    with smtplib.SMTP(current_app.config['SMTP_HOST'], current_app.config['SMTP_PORT'], timeout=10) as smtp:
        if current_app.config['SMTP_STARTTLS']:
            smtp.starttls(context=ssl.create_default_context(cafile=certifi.where()))
        if current_app.config.get('SMTP_USERNAME'):
            smtp.login(current_app.config['SMTP_USERNAME'], current_app.config['SMTP_PASSWORD'])
        smtp.send_message(message)


def button(link, label):
    return f'<p><a href="{escape(link, quote=True)}" style="{BUTTON_STYLE}">{escape(label)}</a></p>'


def prepare_invitation(email, token, family_name, registry_type="family"):
    origin = current_app.config['FRONTEND_ORIGIN'].rstrip('/')
    link = f'{origin}/accept-invitation/{token}'
    subject = "You're invited to a private employee gift list" if registry_type == "company" else "You're invited to a private family gift list"
    joining = registry_type == "family_member"
    if joining: subject = "Join your family with your own login"
    connection_note = ('Accepting also connects both family accounts so you follow each other. Your own lists and photos stay private until you choose to share them back. ' if registry_type == 'family' else '')
    if joining: connection_note = "Join this family with your own credentials. You control your own wishes and share the family connections. Other adults can suggest gifts for your approval. "
    body = (
        (f"You have been invited to join {family_name} with your own login.\n\n" if joining else f"You've been invited to shop for {family_name} on Gather & Gift.\n\n") +
        "Already have an account? Sign in using this email address.\n"
        "Don't have an account? Create a free account using this email address.\n\n"
        f"Open your invitation: {link}\n\n"
        "After you sign in or create your account, the shared gift lists will be added automatically. "
        + connection_note +
        "Private and family-only wishes remain protected.\n\n"
        + intro_text() + "\n\n"
        "This invitation is private, is tied to your email address, and expires in 7 days. "
        "Please don't forward it. Registry photos are visible only to authorized members and invited shoppers."
    )
    delivery = 'not_configured'
    if mail_configured():
        message = new_message(subject, email, {'company':'company-invite','family_member':'adult-invite'}.get(registry_type,'family-invite'))
        message.set_content(body)
        message.add_alternative(
            f'<html><body style="{BODY_STYLE}">'
            '<h1>A thoughtful invitation</h1>'
            f'<p>You have been invited to {"join" if joining else "shop for"} <strong>{escape(family_name)}</strong>.</p>'
            '<p>Already have an account? <strong>Sign in.</strong><br>'
            'New here? <strong>Create a free account.</strong> Use the email address this invitation was sent to.</p>'
            + button(link, 'Open private invitation') +
            f'<p>Your shared gift lists will be added automatically after sign-in. {escape(connection_note)}</p>'
            + intro_html() +
            '<p>This invitation expires in 7 days and is tied to your email. Please do not forward it.</p>'
            '<p>Registry photos are private to authorized members and invited shoppers.</p></body></html>', subtype='html')
        try:
            deliver(message)
            delivery = 'sent'
        except (OSError, smtplib.SMTPException):
            current_app.logger.warning('Invitation email delivery failed; private copyable link remains available.')
            delivery = 'failed'
    return {'subject': subject, 'body': body, 'link': link, 'delivery': delivery}


def prepare_family_setup_invitation(email, token, family_name):
    origin = current_app.config['FRONTEND_ORIGIN'].rstrip('/')
    link = f'{origin}/accept-invitation/{token}'
    subject = "Your family space is ready to claim"
    body = (
        f"A Gather & Gift family space named {family_name} has been prepared for you.\n\n"
        "Already have an account? Sign in using this email address.\n"
        "Don't have an account? Create a free account using this email address.\n\n"
        f"Claim your family space: {link}\n\n"
        "After you sign in or create your account, accept this invitation to become "
        "the family owner. The family profile prepared for you will be linked to "
        "your account, and you can manage the family from there.\n\n"
        + intro_text() + "\n\n"
        "This private invitation is tied to your email address and expires in 7 days. "
        "Please don't forward it."
    )
    delivery = 'not_configured'
    if mail_configured():
        message = new_message(subject, email, 'family-setup')
        message.set_content(body)
        message.add_alternative(
            f'<html><body style="{BODY_STYLE}">'
            '<h1>Your family space is ready</h1>'
            f'<p>A Gather &amp; Gift family space named <strong>{escape(family_name)}</strong> '
            'has been prepared for you.</p>'
            '<p>Already have an account? Sign in with this email address.<br>'
            'New here? Create a free account using this email address.</p>'
            + button(link, 'Claim your family space') +
            '<p>After you sign in or create your account, accept this invitation to become '
            'the family owner. The prepared profile will be linked to your account.</p>'
            + intro_html() +
            '<p>This private invitation is tied to your email and expires in 7 days. '
            'Please do not forward it.</p></body></html>', subtype='html')
        try:
            deliver(message)
            delivery = 'sent'
        except (OSError, smtplib.SMTPException):
            current_app.logger.warning('Family setup invitation email delivery failed; private copyable link remains available.')
            delivery = 'failed'
    return {'subject': subject, 'body': body, 'link': link, 'delivery': delivery}


def send_password_reset(email, link):
    message = new_message('Reset your Gather & Gift password', email, 'password-reset')
    message.set_content(
        'We received a request to reset your password.\n\n'
        f'Choose a new password: {link}\n\n'
        'This private link expires in 30 minutes and can only be used once. '
        'If you did not request this, you can ignore this email. Your password has not changed.'
    )
    message.add_alternative(
        f'<html><body style="{BODY_STYLE}">'
        '<h1>Reset your password</h1><p>Choose a new password for your Gather &amp; Gift account.</p>'
        + button(link, 'Choose a new password') +
        '<p>This private link expires in 30 minutes and can only be used once.</p>'
        '<p>If you did not request this, ignore this email. Your password has not changed.</p></body></html>', subtype='html')
    try:
        deliver(message)
    except (OSError, smtplib.SMTPException):
        current_app.logger.warning('Password reset email could not be delivered.')


def send_account_code(email, code, purpose):
    message = new_message('Your Gather & Gift one-time verification code', email, {'ads_alert_email':'advertising-code','password':'password-code','parent_pin':'parent-pin-code'}.get(purpose,'email-change-code'))
    action = 'confirm your advertising notification email' if purpose == 'ads_alert_email' else 'reset the household password' if purpose == 'password' else 'reset the parent PIN (this code becomes your new PIN after confirmation)' if purpose == 'parent_pin' else 'change the household main email'
    message.set_content(f'Your one-time code to {action} is: {code}\n\nThis code expires in 10 minutes and can only be used once. Do not share this code. If you did not request it, ignore this message.')
    try:
        deliver(message)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.warning('Account verification email could not be delivered.')
        return False


def send_change_approval(email, link, purpose):
    action = 'password change' if purpose == 'password_change' else 'family photo change'
    message = new_message('Approve or cancel your Gather & Gift ' + action, email, 'password-approval' if purpose=='password_change' else 'photo-approval')
    message.set_content(f'A {action} was requested for your household. Nothing has changed yet.\n\nReview and choose Yes, approve or No, cancel: {link}\n\nThis private approval expires in 30 minutes and works once. If you did not request this, choose cancel or ignore the email. Do not share this link.')
    try:
        deliver(message)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.warning('Change approval email could not be delivered.')
        return False


def send_game_invitation(email, title, inviter, link, names, co_buy=False):
    if not mail_configured():
        return False
    message = new_message(('Co-buy invitation: ' if co_buy else 'Gift game invitation: ') + title, email, 'co-buy-invite' if co_buy else 'game-invite')
    action = 'accept or decline the requested contribution' if co_buy else 'review the game and follow request separately. New here? Create a free account using this email, then choose yes or no for each invitation'
    message.set_content(f'{inviter} invited {", ".join(names)} to {title}. Sign in to {action}.\n\n{link}')
    message.add_alternative(
        f'<html><body style="{BODY_STYLE}"><h1>You are invited!</h1>'
        f'<p>{escape(inviter)} invited {escape(", ".join(names))} to <strong>{escape(title)}</strong>.</p>'
        + button(link, 'Review invitation') + f'<p>Sign in to {action}.</p></body></html>', subtype='html')
    try:
        deliver(message)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.warning('Game invitation email could not be delivered.')
        return False


def send_co_buy_invitation(email, item_name, inviter, share):
    link = current_app.config['FRONTEND_ORIGIN'].rstrip('/') + '/gifting'
    return send_game_invitation(email, 'Co-buy ' + item_name + ' (' + share + '%)', inviter, link, ['you'], co_buy=True)


def send_advertising_notification(email, name, entry, portal_url):
    if not mail_configured():
        return False
    message = new_message('New advertising request - Gather & Gift', email, 'advertising-request')
    message.set_content(
        f"Hello {name or 'there'},\n\nA new advertising request is ready in your developer portal.\n\n"
        f"From: {entry.name}\nContact email: {entry.email}\nBusiness: {entry.business_name or 'Not provided'}\n\n"
        f"{entry.message}\n\nReview it securely: {portal_url}\n\nSign in to your developer account to review the request."
    )
    try:
        deliver(message)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.warning('Advertising notification email could not be delivered; the request remains in the portal.')
        return False
