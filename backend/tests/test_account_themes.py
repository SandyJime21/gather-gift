from io import BytesIO
from backend.tests.test_reservation_privacy import register, mutate, csrf


def test_account_palette_is_independent_and_personal_background_uploads_are_disabled(app, tmp_path):
    owner, other = app.test_client(), app.test_client()
    register(owner, 'Owner', 'themeowner@example.com')
    register(other, 'Other', 'themeother@example.com')
    app.config['UPLOAD_FOLDER'] = str(tmp_path.resolve())
    assert owner.get('/api/auth/me').json['user']['theme_key'] == 'classic'
    assert mutate(owner, 'PATCH', '/api/auth/theme', {'theme_key': 'christmas'}).status_code == 200
    assert owner.get('/api/auth/me').json['user']['theme_key'] == 'christmas'
    assert other.get('/api/auth/me').json['user']['theme_key'] == 'classic'
    for key in ('custom', 'invalid'):
        assert mutate(owner, 'PATCH', '/api/auth/theme', {'theme_key': key}).status_code == 400
    uploaded = owner.post('/api/auth/theme/photo', data={'image': (BytesIO(b'\x89PNG\r\n\x1a\nbackground'), 'theme.png')}, headers={'X-CSRF-Token': csrf(owner)})
    assert uploaded.status_code == 410
    assert list(tmp_path.iterdir()) == []
    assert owner.get('/api/auth/me').json['user']['theme_key'] == 'christmas'
    assert owner.get('/api/auth/me').json['user']['theme_image_path'] is None


def test_children_cannot_select_non_child_palettes_or_upload_backgrounds(app):
    from backend.tests.test_child_access import child_setup
    _, child, _, _, _, _, _, _ = child_setup(app)
    assert mutate(child, 'PATCH', '/api/auth/theme', {'theme_key': 'halloween'}).status_code == 403
    assert mutate(child, 'POST', '/api/auth/theme/photo').status_code == 403
    assert mutate(child, 'DELETE', '/api/auth/theme/photo').status_code == 403
    # Children cannot change themes; catalog permissions are covered by test_shared_themes.
