"""Fail early on deployment settings that would break core account flows."""
from urllib.parse import urlsplit
from sqlalchemy.engine import make_url


def validate_production(config):
    if config.get('APP_ENV') != 'production':
        return
    secret = config.get('SECRET_KEY') or ''
    if len(secret) < 32 or secret.startswith(('local-only', 'replace-with')):
        raise RuntimeError('Production SECRET_KEY must be a random value of at least 32 characters.')
    url = make_url(config['SQLALCHEMY_DATABASE_URI'])
    if url.drivername != 'mysql+pymysql' or not url.host or not url.database:
        raise RuntimeError('Production DATABASE_URL must point to the managed MySQL database.')
    if url.host in ('localhost', '127.0.0.1', '::1'):
        raise RuntimeError('Production DATABASE_URL cannot point to a local development database.')
    origin = urlsplit(config.get('FRONTEND_ORIGIN') or '')
    if origin.scheme != 'https' or not origin.hostname or origin.path not in ('', '/') or origin.query or origin.fragment or origin.username:
        raise RuntimeError('Production FRONTEND_ORIGIN must be your public HTTPS origin without a path.')
    if config.get('SMTP_HOST') and config.get('MAIL_FROM') and not config.get('SMTP_STARTTLS'):
        raise RuntimeError('Production SMTP requires SMTP_STARTTLS=true when email is configured.')
    if bool(config.get('STRIPE_SECRET_KEY')) != bool(config.get('STRIPE_WEBHOOK_SECRET')):
        raise RuntimeError('Configure both Stripe secrets or leave both empty to keep checkout disabled.')
