from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import mutate


def test_child_permissions_default_deny_and_parent_can_revoke(app):
    @app.get('/api/new-unrestricted-feature')
    def new_feature():
        return {'available': True}

    parent, child, stranger, _, profiles, lists, _, _ = child_setup(app)
    assert child.get('/api/new-unrestricted-feature').status_code == 403
    assert parent.get('/api/new-unrestricted-feature').status_code == 200
    path = f"/api/profiles/{profiles[0]['id']}/child-controls"
    controls = parent.get(path).json['controls']
    assert controls and not any(controls.values())
    assert child.get('/api/child/me').json['pets'] == []
    assert child.get('/api/child/gift-search?q=book').status_code == 403
    assert child.get('/api/child/game-notifications').status_code == 403
    link = f"/api/child/wishlists/{lists[0]['id']}/links"
    assert mutate(child, 'POST', link, {'url': 'https://example.com/toy'}).status_code == 403
    assert mutate(child, 'POST', f"/api/child/wishlists/{lists[0]['id']}/items", {'product_index': 0}).status_code == 403
    assert mutate(child, 'POST', '/api/child/pets/999/items', {'name': 'Toy'}).status_code == 403
    assert mutate(child, 'DELETE', '/api/child/pets/999/items/999', {}).status_code == 403
    for client in (child, stranger):
        assert mutate(client, 'PATCH', path, {'web_search': True}).status_code == 403
    assert mutate(parent, 'PATCH', path, {'web_search': 'yes'}).status_code == 400
    assert mutate(parent, 'PATCH', path, {'web_search': True}).status_code == 200
    assert child.get('/api/child/me').json['controls']['web_search'] is True
    assert child.get('/api/child/gift-search?q=book').status_code == 503
    assert mutate(parent, 'PATCH', path, {'web_search': False}).status_code == 200
    assert child.get('/api/child/gift-search?q=book').status_code == 403
    assert mutate(child, 'POST', f"/api/child/wishlists/{lists[0]['id']}/items", {'name': 'A book'}).status_code == 201


def allow_optional_features(app):
    """Explicit parental approval used only by tests of optional features."""
    from backend.app.extensions import db
    from backend.app.models import User
    from backend.app.child_controls import CONTROL_KEYS
    with app.app_context():
        for child in User.query.filter_by(is_child=True).all():
            parent = db.session.get(User, child.parent_user_id)
            preferences = dict(parent.notification_preferences or {})
            access = dict(preferences.get('child_access', {}))
            access[str(child.id)] = dict.fromkeys(CONTROL_KEYS, True)
            parent.notification_preferences = {**preferences, 'child_access': access}
        db.session.commit()
