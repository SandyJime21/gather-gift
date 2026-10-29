from io import BytesIO
from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import register, mutate, csrf
from backend.app.models import Household
from backend.app.extensions import db


def test_adult_password_change_is_immediate_without_email(app):
    owner, login = app.test_client(), app.test_client()
    register(owner, 'Owner', 'main@example.com')
    response = mutate(owner, 'POST', '/api/auth/password', {'old_password':'a-long-test-password','new_password':'new-long-password'})
    assert response.status_code == 200
    assert response.json['status'] == 'updated'
    assert owner.get('/api/auth/me').status_code == 200
    assert mutate(login,'POST','/api/auth/login',{'email':'main@example.com','password':'a-long-test-password'}).status_code == 401
    assert mutate(login,'POST','/api/auth/login',{'email':'main@example.com','password':'new-long-password'}).status_code == 200


def test_adult_photo_saves_without_email_and_children_cannot_change_settings(app, monkeypatch):
    parent, child, stranger, home, _, _, _, _ = child_setup(app)
    monkeypatch.setattr('backend.app.api.save_profile_image', lambda *_: ('/api/uploads/new-photo.png',None))
    path = f"/api/households/{home['id']}/photo"
    response = parent.post(path,data={'image':(BytesIO(b'photo'),'photo.png')},headers={'X-CSRF-Token':csrf(parent)})
    assert response.status_code == 200
    assert response.json['photo_path'] == '/api/uploads/new-photo.png'
    with app.app_context():
        assert db.session.get(Household,home['id']).photo_path == '/api/uploads/new-photo.png'
    assert mutate(stranger,'POST',path,{}).status_code == 403
    assert mutate(child,'POST',path,{}).status_code == 403
    assert mutate(child,'POST','/api/auth/password',{'old_password':'child-test-password','new_password':'another-long-password'}).status_code == 403
    assert mutate(child,'PATCH','/api/auth/profile',{'name':'Changed'}).status_code == 403


def test_adult_email_changes_without_email_approval(app):
    client=app.test_client()
    register(client,'Adult','before@example.com')
    response=mutate(client,'PATCH','/api/auth/profile',{'email':'after@example.com','current_password':'a-long-test-password'})
    assert response.status_code == 200
    assert response.json['user']['email'] == 'after@example.com'
