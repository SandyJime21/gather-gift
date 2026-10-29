from io import BytesIO
from backend.tests.test_reservation_privacy import register, mutate, csrf
from backend.app.extensions import db
from backend.app.models import HouseholdMembership
from backend.app.invitation_mail import prepare_invitation


def test_invitation_template_privacy_and_reopen(app, tmp_path, monkeypatch):
    owner, guest, stranger = [app.test_client() for _ in range(3)]
    register(owner, 'Owner', 'inviteowner@example.com')
    guest_user = register(guest, 'Guest', 'inviteguest@example.com')
    register(stranger, 'Stranger', 'invitestranger@example.com')
    app.config['UPLOAD_FOLDER'] = str(tmp_path.resolve())
    home = mutate(owner, 'POST', '/api/households', {'name': 'Private family', 'profiles': [
        {'display_name': 'Alex', 'relationship': 'son'}, {'display_name': 'Sam', 'relationship': 'daughter'}]}).json['household']
    path = f"/api/households/{home['id']}"
    profiles = owner.get(path).json['profiles']
    image = b'\x89PNG\r\n\x1a\nprivate-photo'
    response = owner.post(path + '/photo', data={'image': (BytesIO(image), 'family.png')}, headers={'X-CSRF-Token': csrf(owner)})
    assert response.status_code == 200
    photo = owner.get(path).json['household']['photo_path']
    profile_photos = [owner.post(f"/api/profiles/{profile['id']}/photo", data={'image': (BytesIO(image), 'child.png')}, headers={'X-CSRF-Token': csrf(owner)}).json['photo_path'] for profile in profiles]
    response = mutate(owner, 'POST', path + '/invitations', {'email': 'inviteguest@example.com', 'role': 'shopper', 'profile_ids': [profiles[0]['id']]})
    message = response.json['email_message']
    assert 'Sign in' in message['body'] and 'Create a free account' in message['body']
    assert message['delivery'] == 'not_configured'
    token = response.json['invitation']['token']
    assert guest.get(photo).status_code == 404
    assert app.test_client().get(photo).status_code == 401
    assert mutate(stranger, 'POST', '/api/invitations/accept', {'token': token}).status_code == 403
    for _ in range(2):
        assert mutate(guest, 'POST', '/api/invitations/accept', {'token': token}).status_code == 200
    shared = guest.get(path).json['profiles']
    assert len(shared) == 1 and shared[0]['relationship'] is None
    assert guest.get(path + '/members').status_code == 403
    assert guest.get(photo).status_code == 200
    assert guest.get(photo).headers['Cache-Control'] == 'private, no-store'
    assert guest.get(profile_photos[0]).status_code == 200
    assert guest.get(profile_photos[1]).status_code == 404
    with app.app_context():
        membership = HouseholdMembership.query.filter_by(user_id=guest_user['id'], household_id=home['id']).one()
        db.session.delete(membership)
        db.session.commit()
    assert guest.get(photo).status_code == 404
    assert guest.get(profile_photos[0]).status_code == 404


def test_invitation_smtp_template_and_failure_fallback(app, monkeypatch):
    from unittest.mock import MagicMock
    smtp = MagicMock()
    monkeypatch.setattr('backend.app.invitation_mail.smtplib.SMTP', smtp)
    app.config.update(SMTP_HOST='smtp.example.com', SMTP_PORT=587, MAIL_FROM='family@example.com', SMTP_USERNAME='user', SMTP_PASSWORD='password', SMTP_STARTTLS=True)
    with app.app_context():
        result = prepare_invitation('guest@example.com', 'private-token', '<Family>')
        assert result['delivery'] == 'sent'
        message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        assert message['To'] == 'guest@example.com'
        assert '&lt;Family&gt;' in message.get_payload()[1].get_content()
        smtp.side_effect = OSError('Cannot connect')
        assert prepare_invitation('guest@example.com', 'private-token', 'Family')['delivery'] == 'failed'
