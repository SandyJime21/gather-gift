from backend.tests.test_reservation_privacy import register, mutate


def test_account_email_change_requires_password_and_rejects_duplicates(app, monkeypatch):
    client, other = app.test_client(), app.test_client()
    register(client, 'Me', 'accountold@example.com')
    register(other, 'Other', 'accounttaken@example.com')
    path = '/api/auth/profile'
    assert mutate(client, 'PATCH', path, {'name': 'New name'}).json['user']['name'] == 'New name'
    assert mutate(client, 'PATCH', path, {'email': 'accountnew@example.com'}).status_code == 400
    assert mutate(client, 'PATCH', path, {'email': 'accountnew@example.com', 'current_password': 'wrong'}).status_code == 400
    assert mutate(client, 'PATCH', path, {'email': 'accounttaken@example.com', 'current_password': 'a-long-test-password'}).status_code == 409
    sent = []
    app.config.update(SMTP_HOST='test', MAIL_FROM='test@example.com')
    monkeypatch.setattr('backend.app.api.send_account_code', lambda email, code, purpose: sent.append((email, code)) or True)
    challenge = mutate(client, 'POST', '/api/auth/email-change-code', {'email': 'accountnew@example.com', 'current_password': 'a-long-test-password'}).json['challenge_id']
    assert sent[0][0] == 'accountold@example.com'
    response = mutate(client, 'PATCH', path, {'email': 'accountnew@example.com', 'current_password': 'a-long-test-password', 'challenge_id': challenge, 'code': sent[0][1]})
    assert response.status_code == 200
    assert response.json['user']['email'] == 'accountnew@example.com'
    assert client.get('/api/auth/me').json['user']['email'] == 'accountnew@example.com'
    mutate(client, 'POST', '/api/auth/logout')
    assert mutate(client, 'POST', '/api/auth/login', {'email': 'accountold@example.com', 'password': 'a-long-test-password'}).status_code == 401
    assert mutate(client, 'POST', '/api/auth/login', {'email': 'accountnew@example.com', 'password': 'a-long-test-password'}).status_code == 200
