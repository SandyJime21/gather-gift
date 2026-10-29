from io import BytesIO
from pathlib import Path
from backend.tests.test_reservation_privacy import register, mutate, csrf


def test_uploaded_household_photo_can_be_loaded(app, tmp_path, monkeypatch):
    app.config['UPLOAD_FOLDER'] = str(tmp_path.resolve())
    owner = app.test_client()
    stranger = app.test_client()
    register(owner, 'Photo owner', 'photoowner@example.com')
    register(stranger, 'Stranger', 'photostranger@example.com')
    household = mutate(owner, 'POST', '/api/households', {'name': 'Photo family'}).json['household']
    image = b'\x89PNG\r\n\x1a\nphoto-test'
    response = owner.post(f"/api/households/{household['id']}/photo",
        data={'image': (BytesIO(image), 'family.png')}, headers={'X-CSRF-Token': csrf(owner)})
    assert response.status_code == 200
    path = owner.get(f"/api/households/{household['id']}").json['household']['photo_path']
    loaded = owner.get(path)
    assert loaded.status_code == 200
    assert loaded.data == image
    assert loaded.mimetype == 'image/png'
    assert stranger.get(path).status_code == 404


def test_relative_upload_directory_is_normalized(tmp_path, monkeypatch):
    from backend.app import create_app
    monkeypatch.chdir(tmp_path)
    app = create_app({'TESTING': True, 'UPLOAD_FOLDER': 'instance/uploads',
        'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'RATELIMIT_ENABLED': False})
    assert Path(app.config['UPLOAD_FOLDER']).is_absolute()
    assert Path(app.config['UPLOAD_FOLDER']) == tmp_path / 'instance' / 'uploads'


def test_jpeg_extensions_are_accepted_and_checked(app, tmp_path):
    from werkzeug.datastructures import FileStorage
    from backend.app.api import save_profile_image
    app.config['UPLOAD_FOLDER']=str(tmp_path)
    with app.app_context():
        for extension in ['jpg','jpeg','JPEG']:
            path, failure=save_profile_image(FileStorage(stream=BytesIO(b'\xff\xd8\xffjpeg-test'),filename='photo.'+extension),1)
            assert failure is None
            assert (tmp_path/Path(path).name).exists()
        path,failure=save_profile_image(FileStorage(stream=BytesIO(b'not-a-jpeg'),filename='photo.jpeg'),1)
        assert path is None and failure
