from io import BytesIO
from base64 import b64decode
from backend.tests.test_wishlist_price_requests import setup_request
from backend.tests.test_diagnostic_view import staff_client
from backend.tests.test_reservation_privacy import mutate,csrf
from backend.app.extensions import db
from backend.app.models import Household,HouseholdProfileAccess


def test_published_background_covers_matching_family_lists_with_photo_above(app,tmp_path):
    app.config['UPLOAD_FOLDER']=str(tmp_path)
    owner,follower,_,profile,wishlist=setup_request(app)
    staff=staff_client(app)
    image=b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6Yx8AAAAASUVORK5CYII=')
    response=staff.post('/api/support/themes',data={'name':'Christmas ribbons','season':'Christmas','purpose':'list','audience':'everyone','background':'#fff4ef','foreground':'#382b42','accent':'#9d5368','price':'0','active':'true','image':(BytesIO(image),'christmas.png')},headers={'X-CSRF-Token':csrf(staff)},content_type='multipart/form-data')
    assert response.status_code==201,response.json
    theme_id=int(response.json['theme']['key'][1:])
    catalog=owner.get('/api/list-backgrounds').json['backgrounds']
    assert catalog[0]['id']==theme_id
    assert owner.get('/api/themes').json['themes']==[]
    with app.app_context():
        home_id=HouseholdProfileAccess.query.filter_by(profile_id=profile['id']).first().household_id
        db.session.get(Household,home_id).photo_path='/api/uploads/family-photo.png';db.session.commit()
    assert mutate(owner,'POST',f"/api/wishlists/{wishlist['id']}/items",{'name':'Christmas book'}).status_code==201
    saved=mutate(owner,'POST',f'/api/households/{home_id}/list-collections',{'title':'Family Christmas','wishlist_ids':[wishlist['id']],'share_publicly':True,'use_family_photo':True,'background_theme_id':theme_id})
    assert saved.status_code==201,saved.json
    visible=follower.get(f'/api/households/{home_id}/list-collections').json['collections'][0]
    assert visible['background_art']==f'/api/themes/{theme_id}/art'
    assert visible['family_photo_url']=='/api/uploads/family-photo.png'
    assert visible['wishlist_ids']==[wishlist['id']]
    assert follower.get(visible['background_art']).status_code==200
    assert mutate(owner,'POST',f'/api/households/{home_id}/list-collections',{'title':'Invalid','wishlist_ids':[wishlist['id']],'share_publicly':True,'background_theme_id':999999}).status_code==400
