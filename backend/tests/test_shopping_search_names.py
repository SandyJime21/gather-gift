from backend.tests.test_wishlist_price_requests import setup_request
from backend.tests.test_reservation_privacy import mutate


def test_search_names_and_family_names_returns_shared_gifts(app):
    owner,follower,stranger,profile,wishlist=setup_request(app)
    assert mutate(owner,'POST',f"/api/wishlists/{wishlist['id']}/items",{'name':'Puzzle','category':'toys'}).status_code==201
    for query in [profile['display_name'],'Family','Mia Puzzle','nothing','50%','_']:
        for client,scope in [(owner,''),(follower,'following')]:
            response=client.get('/api/shopping',query_string={'q':query,'scope':scope,'sort':'priority'})
            assert response.status_code==200,(query,response.json)
    assert [i['name'] for i in follower.get('/api/shopping',query_string={'q':profile['display_name']}).json['items']]==['Puzzle']


def test_search_followed_account_name_even_when_profile_name_differs(app):
    from backend.app.extensions import db
    from backend.app.models import FamilyFollow,PersonalWish
    owner,follower,_,_,_=setup_request(app)
    owner_id=owner.get('/api/auth/me').json['user']['id']
    follower_id=follower.get('/api/auth/me').json['user']['id']
    with app.app_context():
        if not FamilyFollow.query.filter_by(follower_id=follower_id,followed_id=owner_id).first():
            db.session.add(FamilyFollow(follower_id=follower_id,followed_id=owner_id));db.session.commit()
    created=mutate(owner,'POST','/api/personal-wishes',{'name':'Personal puzzle','visibility':'followers','viewer_ids':[]})
    assert created.status_code==201,created.json
    with app.app_context():
        wish=PersonalWish.query.filter_by(owner_id=owner_id).first()
        wish.item.profile.display_name='Different profile nickname';db.session.commit()
    response=follower.get('/api/shopping',query_string={'q':'Parent','scope':'following'})
    assert response.status_code==200,response.json
    assert [i['name'] for i in response.json['items']]==['Personal puzzle']
    assert response.json['items'][0]['recipient']=='Parent'
