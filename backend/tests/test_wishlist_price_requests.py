from backend.tests.wishlist_setup import create_test_wishlist
from backend.tests.test_reservation_privacy import register, mutate


def setup_request(app):
    owner, follower, stranger = [app.test_client() for _ in range(3)]
    register(owner, 'Parent', 'range-parent@example.com')
    register(follower, 'Friend', 'range-friend@example.com')
    register(stranger, 'Stranger', 'range-stranger@example.com')
    home = mutate(owner, 'POST', '/api/households', {'name': 'Family', 'profiles': [{'display_name': 'Mia'}]}).json['household']
    profile = owner.get(f"/api/households/{home['id']}").json['profiles'][0]
    wishlist = create_test_wishlist(owner, f"/api/profiles/{profile['id']}/wishlists")
    mutate(owner, 'PATCH', f"/api/wishlists/{wishlist['id']}", {'share_publicly': True})
    invitation = mutate(owner, 'POST', f"/api/households/{home['id']}/invitations", {'email': 'range-friend@example.com', 'role': 'shopper', 'profile_ids': [profile['id']]}).json['invitation']
    assert mutate(follower, 'POST', '/api/invitations/accept', {'token': invitation['token']}).status_code == 200
    return owner, follower, stranger, profile, wishlist


def test_price_request_stays_after_read_and_completes_only_in_requested_range(app):
    owner, follower, stranger, profile, wishlist = setup_request(app)
    path = f"/api/profiles/{profile['id']}/price-requests"
    payload = dict(minimum='0', maximum='50', currency='USD', wishlist_id=wishlist['id'])
    assert mutate(stranger, 'POST', path, payload).status_code == 403
    assert mutate(follower, 'POST', path, payload).status_code == 201
    def reminders():
        return [row for row in owner.get('/api/notifications').json['notifications'] if row.get('price_request')]
    row = reminders()[0]
    assert 'Friend' in row['message'] and '0.00' in row['message'] and not row['read']
    assert mutate(stranger, 'POST', '/api/notifications/state', {'id': row['id'], 'action': 'read'}).status_code == 404
    assert mutate(owner, 'POST', '/api/notifications/state', {'id': row['id'], 'action': 'read'}).status_code == 200
    assert reminders()[0]['read'] is True
    assert mutate(follower, 'POST', path, payload).status_code == 409
    assert mutate(owner, 'POST', f"/api/wishlists/{wishlist['id']}/items", {'name': 'Expensive', 'estimated_price': '100', 'currency': 'USD'}).status_code == 201
    assert len(reminders()) == 1
    assert mutate(owner, 'POST', f"/api/wishlists/{wishlist['id']}/items", {'name': 'Book', 'estimated_price': '25', 'currency': 'USD'}).status_code == 201
    assert reminders() == []


def test_profile_reminder_read_does_not_dismiss_and_ignore_removes_it(app):
    owner, _, stranger, _, _ = setup_request(app)
    row = owner.get('/api/notifications').json['profile_reminders'][0]
    assert mutate(owner, 'POST', '/api/notifications/state', {'id': row['id'], 'action': 'read'}).status_code == 200
    assert next(item for item in owner.get('/api/notifications').json['profile_reminders'] if item['id'] == row['id'])['read'] is True
    assert mutate(owner, 'POST', '/api/notifications/state', {'id': row['id'], 'action': 'dismiss'}).status_code == 200
    assert all(item['id'] != row['id'] for item in owner.get('/api/notifications').json['profile_reminders'])


def test_price_request_ignore_clear_and_validation(app):
    owner, follower, _, profile, wishlist = setup_request(app)
    path = f"/api/profiles/{profile['id']}/price-requests"
    for low, high in [('60','50'),('-1','50'),('NaN','50')]:
        assert mutate(follower, 'POST', path, dict(minimum=low, maximum=high)).status_code == 400
    assert mutate(follower, 'POST', path, dict(minimum='0', maximum='50', wishlist_id=999999)).status_code == 400
    assert mutate(follower, 'POST', path, dict(minimum='0', maximum='50')).status_code == 201
    row = next(row for row in owner.get('/api/notifications').json['notifications'] if row.get('price_request'))
    assert mutate(owner, 'POST', '/api/notifications/state', {'id': row['id'], 'action': 'dismiss'}).status_code == 200
    assert not any(row.get('price_request') for row in owner.get('/api/notifications').json['notifications'])
    assert mutate(follower, 'POST', path, dict(minimum='0', maximum='50')).status_code == 201
    assert mutate(owner, 'POST', '/api/notifications/clear', {}).status_code == 200
    assert not any(row.get('price_request') for row in owner.get('/api/notifications').json['notifications'])
