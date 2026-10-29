"""CLI helper that renders (or sends) one sample of every email the app can send."""
from email import message_from_bytes, policy
from html import escape
from pathlib import Path
from types import SimpleNamespace

import click
from flask import current_app

from . import invitation_mail as mail


def send_all_samples(to):
    origin = current_app.config['FRONTEND_ORIGIN'].rstrip('/')
    entry = SimpleNamespace(name='Pat Baker', email='pat@bakery.example', business_name='Pat\'s Bakery',
                            message='We would love to advertise our birthday cakes to your families.')
    mail.prepare_invitation(to, 'sample-token', 'The Rivera Family', 'family')
    mail.prepare_invitation(to, 'sample-token', 'The Rivera Family', 'family_member')
    mail.prepare_invitation(to, 'sample-token', 'Acme Co. gift list', 'company')
    mail.prepare_family_setup_invitation(to, 'sample-token', 'The Rivera Family')
    mail.send_password_reset(to, origin + '/reset-password?token=sample-token')
    for purpose in ('ads_alert_email', 'password', 'parent_pin', 'email'):
        mail.send_account_code(to, '123456', purpose)
    mail.send_change_approval(to, origin + '/approve-change?token=sample-token', 'password_change')
    mail.send_change_approval(to, origin + '/approve-change?token=sample-token', 'photo_change')
    mail.send_game_invitation(to, 'Family Secret Santa', 'Alex Rivera', origin + '/games', ['Taylor', 'Sam'])
    mail.send_co_buy_invitation(to, 'Lego Castle', 'Alex Rivera', '50.00')
    mail.send_advertising_notification(to, 'Sandy', entry, origin + '/support')
    from .deletion_backup import send_backup
    send_backup(to, b'Person,Gift,Link,Price\r\nTaylor,Sample puzzle,https://example.com/puzzle,20.00\r\n')


def write_html_previews(folder):
    for path in sorted(Path(folder).glob('*.eml')):
        message = message_from_bytes(path.read_bytes(), policy=policy.default)
        html = message.get_body(preferencelist=('html',))
        text = message.get_body(preferencelist=('plain',))
        if html:
            content = html.get_content()
        else:
            content = '<pre style="font-family:Arial,sans-serif;white-space:pre-wrap;max-width:560px;margin:32px auto">' + escape(text.get_content() if text else '') + '</pre>'
        header = f'<div style="background:#eee;padding:8px 12px;font:13px Arial">Subject: <b>{escape(str(message["Subject"]))}</b> &middot; To: {escape(str(message["To"]))}</div>'
        path.with_suffix('.html').write_text(header + content, encoding='utf-8')


def register(app):
    @app.cli.command('sample-emails')
    @click.option('--to', required=True, help='Address that receives every sample email.')
    @click.option('--send', is_flag=True, help='Deliver through the configured SMTP server instead of writing preview files.')
    @click.option('--folder', default='instance/email-previews', show_default=True)
    def sample_emails(to, send, folder):
        if send:
            if not (app.config.get('SMTP_HOST') and app.config.get('MAIL_FROM')):
                raise click.ClickException('Set SMTP_HOST, MAIL_FROM (and SMTP_USERNAME/SMTP_PASSWORD) first.')
            send_all_samples(to)
            click.echo(f'Sent every sample email to {to}. Check spam too.')
            return
        app.config['MAIL_OUTBOX_DIR'] = folder
        send_all_samples(to)
        write_html_previews(folder)
        click.echo(f'Wrote previews to {folder} (open the .html files in a browser).')
