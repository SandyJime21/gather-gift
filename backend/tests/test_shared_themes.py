from io import BytesIO
from backend.tests.test_advertising import staff_login
from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import mutate, csrf


def test_shared_themes_master_only_and_child_choices(app, tmp_path):
    parent, child, stranger, *_ = child_setup(app)
    admin = app.test_client()
    with app.app_context():
        staff_login(admin)
    app.config['UPLOAD_FOLDER'] = str(tmp_path.resolve())
    data = dict(name='Winter bubbles', season='Winter', audience='kids', background='#eeeeff', foreground='#221144', accent='#663399')
    assert stranger.post('/api/support/themes', data=data, headers={'X-CSRF-Token':csrf(stranger)}).status_code == 403
    response = admin.post('/api/support/themes', data={**data, 'image':(BytesIO(b'\x89PNG\r\n\x1a\nart'), 'art.png')}, headers={'X-CSRF-Token':csrf(admin)})
    assert response.status_code == 201, response.json
    theme = response.json['theme']
    assert child.get('/api/themes').status_code == 403
    assert child.get(theme['art']).status_code == 200
    assert mutate(child, 'PATCH', '/api/auth/theme', {'theme_key':theme['key']}).status_code == 403
    assert child.get('/api/auth/me').json['user']['shared_theme'] is None
    adult = admin.post('/api/support/themes', data={**data, 'name':'Adult theme','audience':'adults'}, headers={'X-CSRF-Token':csrf(admin)}).json['theme']
    assert mutate(child, 'PATCH', '/api/auth/theme', {'theme_key':adult['key']}).status_code == 403
    assert child.get('/api/themes').status_code == 403
    assert parent.post('/api/auth/theme/photo', headers={'X-CSRF-Token':csrf(parent)}).status_code == 410
