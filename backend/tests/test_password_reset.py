from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from backend.app.extensions import db
from backend.app.models import PasswordReset
from backend.tests.test_reservation_privacy import register, mutate


def reset_setup(app, monkeypatch):
    first, second, recovery = [app.test_client() for _ in range(3)]
    register(first, 'Taylor', 'reset@example.com')
    assert mutate(second, 'POST', '/api/auth/login', {'email': 'reset@example.com', 'password': 'a-long-test-password'}).status_code == 200
    app.config.update(SMTP_HOST='smtp.example.com', MAIL_FROM='family@example.com')
    links = []
    monkeypatch.setattr('backend.app.api.send_password_reset', lambda email, link: links.append(link) or True)
    return first, second, recovery, links


def test_password_reset_is_private_single_use_and_revokes_sessions(app, monkeypatch):
    first, second, recovery, links = reset_setup(app, monkeypatch)
    unknown = mutate(recovery, 'POST', '/api/auth/forgot-password', {'email': 'unknown@example.com'})
    known = mutate(recovery, 'POST', '/api/auth/forgot-password', {'email': 'reset@example.com', 'next': '/accept-invitation/private-invite'})
    assert unknown.json == known.json
    parameters = parse_qs(urlsplit(links[0]).query)
    token = parameters['token'][0]
    assert parameters['next'] == ['/accept-invitation/private-invite']
    assert token not in str(known.json)
    with app.app_context():
        row = PasswordReset.query.one()
        assert row.token_hash != token and len(row.token_hash) == 64
    assert mutate(recovery, 'POST', '/api/auth/reset-password', {'token': token, 'password': 'short'}).status_code == 400
    assert first.get('/api/auth/me').status_code == 200
    response = mutate(recovery, 'POST', '/api/auth/reset-password', {'token': token, 'password': 'a-new-long-password'})
    assert response.status_code == 200
    assert response.json['login_path'] == '/login'
    assert first.get('/api/auth/me').status_code == 401
    assert second.get('/api/auth/me').status_code == 401
    assert mutate(recovery, 'POST', '/api/auth/reset-password', {'token': token, 'password': 'another-long-password'}).status_code == 400
    assert mutate(recovery, 'POST', '/api/auth/login', {'email': 'reset@example.com', 'password': 'a-long-test-password'}).status_code == 401
    assert mutate(recovery, 'POST', '/api/auth/login', {'email': 'reset@example.com', 'password': 'a-new-long-password'}).status_code == 200


def test_reset_expiry_new_link_and_password_change_invalidate_tokens(app, monkeypatch):
    first, _, recovery, links = reset_setup(app, monkeypatch)
    def request_token():
        assert mutate(recovery, 'POST', '/api/auth/forgot-password', {'email': 'reset@example.com'}).status_code == 200
        return parse_qs(urlsplit(links[-1]).query)['token'][0]
    old = request_token()
    new = request_token()
    assert mutate(recovery, 'POST', '/api/auth/reset-password', {'token': old, 'password': 'a-new-long-password'}).status_code == 400
    with app.app_context():
        row = PasswordReset.query.filter_by(used_at=None).one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
    assert mutate(recovery, 'POST', '/api/auth/reset-password', {'token': new, 'password': 'a-new-long-password'}).status_code == 400
    token = request_token()
    assert mutate(first, 'POST', '/api/auth/password', {'old_password': 'a-long-test-password', 'new_password': 'changed-from-settings'}).status_code == 200
    assert first.get('/api/auth/me').status_code == 200
    assert mutate(recovery, 'POST', '/api/auth/reset-password', {'token': token, 'password': 'a-new-long-password'}).status_code == 400


def test_unconfigured_email_does_not_expose_reset_links(app):
    client = app.test_client()
    app.config.update(SMTP_HOST='', MAIL_FROM='')
    response = mutate(client, 'POST', '/api/auth/forgot-password', {'email': 'anyone@example.com'})
    assert response.status_code == 503
    assert 'not available' in response.json['error']
    assert PasswordReset.query.count() == 0
