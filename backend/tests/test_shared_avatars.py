from io import BytesIO
from backend.tests.test_advertising import staff_login
from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import mutate, csrf
from backend.app.extensions import db
from backend.app.models import PersonProfile, User


def test_shared_cartoon_publish_select_and_permissions(app,tmp_path):
    parent,child,stranger,home,profiles,*_=child_setup(app)
    app.config['UPLOAD_FOLDER']=str(tmp_path)
    admin=app.test_client();staff_login(admin)
    def upload(client,path):
        return client.post(path,data={'name':'Happy fox','image':(BytesIO(b'\x89PNG\r\n\x1a\nart'),'fox.png')},headers={'X-CSRF-Token':csrf(client)})
    assert upload(stranger,'/api/support/avatars').status_code==403
    created=upload(admin,'/api/support/avatars')
    assert created.status_code==201,created.json
    avatar=created.json['avatar']
    assert parent.get('/api/avatars').json['avatars']==[avatar]
    assert child.get('/api/avatars').status_code==403
    assert child.get(avatar['image']).status_code==200
    assert app.test_client().get(avatar['image']).status_code==401
    pid=profiles[0]['id']
    profile=db.session.get(PersonProfile,pid);profile.photo_path='/api/uploads/old-photo.png';db.session.commit()
    chosen=mutate(parent,'PATCH',f'/api/profiles/{pid}',{'avatar_key':avatar['key'],'use_avatar':True})
    assert chosen.status_code==200,chosen.json
    assert chosen.json['profile']['avatar_key']==avatar['key']
    assert chosen.json['profile']['photo_path'] is None
    assert mutate(stranger,'PATCH',f'/api/profiles/{pid}',{'avatar_key':'cat'}).status_code==404
    assert mutate(child,'PATCH',f'/api/profiles/{pid}',{'avatar_key':'dog'}).status_code==403
    assert mutate(parent,'PATCH',f'/api/profiles/{pid}',{'avatar_key':'a999999'}).status_code==400
    switch=parent.get('/api/household-session').json['profiles']
    assert next(p for p in switch if p['id']==pid)['avatar_key']==avatar['key']


def test_child_switcher_photos_are_scoped_to_parent_siblings(app,tmp_path):
    parent,child,stranger,home,profiles,*_=child_setup(app)
    app.config['UPLOAD_FOLDER']=str(tmp_path)
    pid=profiles[0]['id']
    response=parent.post(f'/api/profiles/{pid}/photo',data={'image':(BytesIO(b'\x89PNG\r\n\x1a\nphoto'),'photo.png')},headers={'X-CSRF-Token':csrf(parent)})
    assert response.status_code==200,response.json
    owner=User.query.filter_by(email='childparent@example.com').one()
    child_user=db.session.get(User,db.session.get(PersonProfile,pid).account_user_id)
    with child.session_transaction() as state:
        state['household_return_user_id']=owner.id;state['household_return_version']=owner.session_version
    rows=child.get('/api/child/profiles').json['profiles']
    photo=next(r for r in rows if r['id']==child_user.id)['photo_path']
    assert photo and child.get(photo).status_code==200
    assert stranger.get(photo).status_code==404
    assert child.get('/api/child/profiles/999999/photo').status_code==404
