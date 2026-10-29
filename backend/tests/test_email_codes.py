from backend.tests.test_reservation_privacy import register, mutate
from backend.app.models import AccountEmailCode
from backend.app.extensions import db
from datetime import datetime, timedelta, timezone


def setup_code(app, monkeypatch):
    app.config.update(SMTP_HOST='test', MAIL_FROM='test@example.com')
    sent = []
    monkeypatch.setattr('backend.app.api.send_account_code', lambda email, code, purpose: sent.append((email, code, purpose)) or True)
    user, recovery = app.test_client(), app.test_client()
    register(user, 'Main account', 'main@example.com')
    return user, recovery, sent


def test_recovery_code_is_single_use_and_resets_main_password(app, monkeypatch):
    user, recovery, sent = setup_code(app, monkeypatch)
    unknown = mutate(recovery, 'POST', '/api/auth/recovery-code', {'email': 'missing@example.com'})
    known = mutate(recovery, 'POST', '/api/auth/recovery-code', {'email': 'main@example.com'})
    assert unknown.json['message'] == known.json['message']
    assert sent[0][0] == 'main@example.com'
    body = {'email': 'main@example.com', 'challenge_id': known.json['challenge_id'], 'code': sent[0][1]}
    assert AccountEmailCode.query.one().code_hash != sent[0][1]
    verified = mutate(recovery, 'POST', '/api/auth/recovery-code/verify', body)
    assert verified.status_code == 200
    assert mutate(recovery, 'POST', '/api/auth/recovery-code/verify', body).status_code == 400
    assert mutate(recovery, 'POST', '/api/auth/reset-password', {'token': verified.json['token'], 'password': 'a-new-household-password'}).status_code == 200
    assert user.get('/api/auth/me').status_code == 401


def test_recovery_codes_expire_and_lock_after_five_wrong_attempts(app, monkeypatch):
    user, recovery, sent = setup_code(app, monkeypatch)
    issued = mutate(recovery, 'POST', '/api/auth/recovery-code', {'email': 'main@example.com'}).json
    body = {'email': 'main@example.com', 'challenge_id': issued['challenge_id'], 'code': 'wrong'}
    for _ in range(5):
        assert mutate(recovery, 'POST', '/api/auth/recovery-code/verify', body).status_code == 400
    body['code'] = sent[-1][1]
    assert mutate(recovery, 'POST', '/api/auth/recovery-code/verify', body).status_code == 400
    issued = mutate(recovery, 'POST', '/api/auth/recovery-code', {'email': 'main@example.com'}).json
    row = db.session.get(AccountEmailCode, issued['challenge_id'])
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    body.update(challenge_id=issued['challenge_id'], code=sent[-1][1])
    assert mutate(recovery, 'POST', '/api/auth/recovery-code/verify', body).status_code == 400


def test_email_change_requires_current_password_and_not_email_approval(app, monkeypatch):
    user, recovery, sent = setup_code(app, monkeypatch)
    assert mutate(user,'PATCH','/api/auth/profile',{'email':'new@example.com'}).status_code==400
    assert mutate(user,'PATCH','/api/auth/profile',{'email':'new@example.com','current_password':'wrong'}).status_code==400
    assert mutate(user,'PATCH','/api/auth/profile',{'email':'new@example.com','current_password':'a-long-test-password'}).status_code==200
    assert user.get('/api/auth/me').json['user']['email']=='new@example.com'
    assert sent==[]
