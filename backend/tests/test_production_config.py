import pytest
from backend.app.production import validate_production


def valid_settings():
    return dict(APP_ENV='production', SECRET_KEY='x'*48,
                SQLALCHEMY_DATABASE_URI='mysql+pymysql://user:password@db.example.com/gifts',
                FRONTEND_ORIGIN='https://gifts.example.com', SMTP_HOST='smtp.example.com',
                MAIL_FROM='app@example.com', SMTP_STARTTLS=True,
                STRIPE_SECRET_KEY='', STRIPE_WEBHOOK_SECRET='')


def test_valid_production_settings_allow_free_launch():
    validate_production(valid_settings())


@pytest.mark.parametrize('host,sender',[('',''),('smtp.example.com',''),('','app@example.com')])
def test_database_migrations_and_startup_do_not_require_email(host,sender):
    config=valid_settings()
    config.update(SMTP_HOST=host,MAIL_FROM=sender)
    validate_production(config)


@pytest.mark.parametrize('field,value',[
    ('SECRET_KEY','local-only-change-me'),
    ('SQLALCHEMY_DATABASE_URI','sqlite:///local.db'),
    ('SQLALCHEMY_DATABASE_URI','mysql+pymysql://u:p@127.0.0.1/gifts'),
    ('FRONTEND_ORIGIN','http://localhost:5173'),
    ('FRONTEND_ORIGIN','https://example.com/some-path'),
    ('SMTP_STARTTLS',False),
    ('STRIPE_SECRET_KEY','sk_test_placeholder'),
])
def test_production_rejects_missing_or_unsafe_settings(field,value):
    config=valid_settings();config[field]=value
    with pytest.raises(RuntimeError):validate_production(config)
