from urllib.parse import urlsplit
from backend.tests.test_gift_games import setup_game, action
from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import FamilyFollow, User, GiftExchangeGame


def invite(app, monkeypatch, email='new-player@example.com'):
    host, outsider, game, ids = setup_game(app)
    sent = []
    monkeypatch.setattr('backend.app.invitation_mail.send_game_invitation', lambda *args: sent.append(args) or True)
    response = mutate(host, 'POST', f"/api/games/{game['id']}/email-invitations", {'email': email})
    assert response.status_code == 201, response.json
    path = '/api' + urlsplit(sent[0][3]).path
    return host, outsider, response.json['game'], ids, path


def test_email_signup_game_yes_follow_no_is_explicit_and_one_use(app, monkeypatch):
    host, outsider, game, ids, path = invite(app, monkeypatch)
    guest = app.test_client()
    assert guest.get(path).json['title'] == 'Holiday exchange'
    assert 'email' not in guest.get(path).json
    assert action(host, game, 'start').status_code == 409
    assert mutate(outsider, 'POST', path, {'join_game': True, 'allow_follow': True}).status_code == 403
    register(guest, 'New Player', 'new-player@example.com')
    assert mutate(guest, 'POST', path, {'join_game': True}).status_code == 400
    response = mutate(guest, 'POST', path, {'join_game': True, 'allow_follow': False})
    assert response.status_code == 200, response.json
    own_game = guest.get(f"/api/games/{game['id']}")
    assert own_game.status_code == 200
    assert len(own_game.json['game']['participants']) == len(ids) + 1
    assert own_game.json['game']['email_invitations'] == []
    with app.app_context():
        assert FamilyFollow.query.count() == 0
    assert mutate(guest, 'POST', path, {'join_game': True, 'allow_follow': True}).status_code == 410
    assert guest.get(path).status_code == 410


def test_game_no_follow_yes_does_not_join_or_share_children(app, monkeypatch):
    host, outsider, game, ids, path = invite(app, monkeypatch, 'games-outside@example.com')
    home = mutate(outsider, 'POST', '/api/households', {'name': 'Guest home', 'profiles': [{'display_name': 'Child'}]}).json['household']
    profiles = outsider.get(f"/api/households/{home['id']}").json['profiles']
    response = mutate(outsider, 'POST', path, {'join_game': False, 'allow_follow': True})
    assert response.status_code == 200
    assert outsider.get(f"/api/games/{game['id']}").status_code == 404
    assert len(host.get(f"/api/games/{game['id']}").json['game']['participants']) == len(ids)
    with app.app_context():
        assert FamilyFollow.query.count() == 1
    for profile in profiles:
        assert host.get(f"/api/profiles/{profile['id']}").status_code == (200 if profile.get('is_adult') else 404)


def test_host_can_revoke_and_failed_delivery_does_not_block_game(app, monkeypatch):
    host, outsider, game, _, path = invite(app, monkeypatch)
    endpoint = f"/api/games/{game['id']}/email-invitations/revoke"
    assert mutate(outsider, 'POST', endpoint, {'email': 'new-player@example.com'}).status_code == 403
    response = mutate(host, 'POST', endpoint, {'email': 'new-player@example.com'})
    assert response.json['game']['pending_email_invitations'] == 0
    assert app.test_client().get(path).status_code == 410
    monkeypatch.setattr('backend.app.invitation_mail.send_game_invitation', lambda *args: False)
    failed = mutate(host, 'POST', f"/api/games/{game['id']}/email-invitations", {'email': 'new-player@example.com'})
    assert failed.status_code == 503
    assert host.get(f"/api/games/{game['id']}").json['game']['pending_email_invitations'] == 0


def test_game_can_be_created_as_one_player_draft(app):
    host, _, game, ids = setup_game(app)
    response = mutate(host, 'POST', '/api/games', dict(household_id=game['household_id'], title='New game', kind='secret_santa', participants=[ids[0]], allow_draft=True))
    assert response.status_code == 201, response.json
    assert action(host, response.json['game'], 'start').status_code == 409


def test_expired_or_changed_tokens_cannot_be_previewed_or_accepted(app, monkeypatch):
    import copy
    host, outsider, game, _, path = invite(app, monkeypatch, 'games-outside@example.com')
    assert outsider.get(path+'changed').status_code == 410
    with app.app_context():
        row = db.session.get(GiftExchangeGame, game['id'])
        state = copy.deepcopy(row.state)
        state['email_invites'][0]['expires_at'] = 0
        row.state = state
        db.session.commit()
    assert outsider.get(path).status_code == 410
    assert mutate(outsider, 'POST', path, {'join_game': True, 'allow_follow': True}).status_code == 410
    assert host.get(f"/api/games/{game['id']}").json['game']['pending_email_invitations'] == 0
