from backend.tests.test_wishlist_price_requests import setup_request
from backend.tests.test_reservation_privacy import mutate
from backend.app.extensions import db
from backend.app.models import HouseholdProfileAccess, Wishlist


def test_collection_followers_only_see_shared_populated_lists(app):
    owner,follower,stranger,profile,wishlist=setup_request(app)
    with app.app_context():home_id=HouseholdProfileAccess.query.filter_by(profile_id=profile['id']).first().household_id
    path=f'/api/households/{home_id}/list-collections'
    secret=mutate(owner,'POST',f"/api/profiles/{profile['id']}/wishlists",{'title':'Private'}).json['wishlist']
    empty=mutate(owner,'POST',f"/api/profiles/{profile['id']}/wishlists",{'title':'Empty'}).json['wishlist']
    for row,name in [(wishlist,'Shared puzzle'),(secret,'Secret gift')]:
        assert mutate(owner,'POST',f"/api/wishlists/{row['id']}/items",{'name':name,'category':'toys','estimated_price':25}).status_code==201
    body=dict(title='Family Christmas',wishlist_ids=[wishlist['id'],empty['id']],share_publicly=True,use_family_photo=True)
    response=mutate(owner,'POST',path,body)
    assert response.status_code==201,response.json
    cid=response.json['collection']['id']
    assert follower.get(path).json['collections'][0]['list_count']==1
    visible=follower.get(path+f'/{cid}').json['items']
    assert [i['name'] for i in visible]==['Shared puzzle']
    assert visible[0]['can_view_sharing'] is False
    assert owner.get(path+f'/{cid}').json['items'][0]['can_view_sharing'] is True
    assert mutate(follower,'POST',path,body).status_code==403
    assert stranger.get(path).status_code==404
    invalid={**body,'wishlist_ids':[wishlist['id'],999999],'share_publicly':False}
    assert mutate(owner,'POST',path,invalid).status_code==404
    with app.app_context():assert db.session.get(Wishlist,wishlist['id']).share_publicly is True
    assert mutate(owner,'POST',path,{**body,'share_publicly':False}).status_code==201
    assert follower.get(path).json['collections']==[]
    assert follower.get(path+f'/{cid}').status_code==404
    assert [i['name'] for i in owner.get(path+f'/{cid}').json['items']]==['Shared puzzle']


def test_collection_rejects_unsafe_cover_and_cross_family_lists(app):
    owner,_,stranger,profile,wishlist=setup_request(app)
    with app.app_context():home_id=HouseholdProfileAccess.query.filter_by(profile_id=profile['id']).first().household_id
    path=f'/api/households/{home_id}/list-collections'
    body=dict(title='Family Christmas',wishlist_ids=[wishlist['id']],share_publicly=True,use_family_photo=False,cover_url='https://127.0.0.1/art')
    assert mutate(owner,'POST',path,body).status_code==400
    other=mutate(owner,'POST','/api/households',{'name':'Other family','profiles':[{'display_name':'Other'}]}).json['household']
    pid=owner.get(f"/api/households/{other['id']}").json['profiles'][0]['id']
    otherlist=mutate(owner,'POST',f'/api/profiles/{pid}/wishlists',{'title':'Other'}).json['wishlist']
    assert mutate(owner,'POST',path,{**body,'cover_url':'','wishlist_ids':[otherlist['id']]}).status_code==403


def test_collection_does_not_override_claimed_adult_control(app):
    from backend.tests.test_linked_adults import joined_family
    owner,adult,_,home,partner,_,_,_=joined_family(app)
    own=mutate(adult,'POST',f"/api/profiles/{partner['id']}/wishlists",{'title':'Christmas'}).json['wishlist']
    gift=mutate(adult,'POST',f"/api/wishlists/{own['id']}/items",{'name':'Adult gift'}).json['item']
    body=dict(title='Family Christmas',wishlist_ids=[own['id']],share_publicly=True,use_family_photo=True)
    path=f"/api/households/{home['id']}/list-collections"
    assert mutate(owner,'POST',path,body).status_code==403
    assert mutate(adult,'POST',path,body).status_code==201
    with app.app_context():assert db.session.get(Wishlist,own['id']).share_publicly is True
    ownview=adult.get(f"/api/wishlists/{own['id']}/items").json['items'][0]
    assert ownview['can_edit'] and ownview['can_view_sharing']


def test_collection_migration_round_trip_is_additive(app):
    from flask_migrate import stamp,upgrade,downgrade
    from sqlalchemy import inspect
    from backend.app.models import FamilyListCollection
    with app.app_context():
        assert db.engine.url.get_backend_name()=='sqlite'
        db.session.remove()
        FamilyListCollection.__table__.drop(db.engine)
        before=set(inspect(db.engine).get_table_names())
        stamp(directory='backend/migrations',revision='6ab4e1d092f3')
        upgrade(directory='backend/migrations',revision='7c83a92db461')
        assert set(inspect(db.engine).get_table_names())==before|{'alembic_version','family_list_collection'}
        downgrade(directory='backend/migrations',revision='6ab4e1d092f3')
        assert set(inspect(db.engine).get_table_names())==before|{'alembic_version'}


def test_adults_can_join_same_collection_without_changing_each_others_lists(app):
    from backend.tests.test_linked_adults import joined_family
    owner,adult,_,home,partner,kid,_,_=joined_family(app)
    child_list=mutate(owner,'POST',f"/api/profiles/{kid['id']}/wishlists",{'title':'Christmas'}).json['wishlist']
    adult_list=mutate(adult,'POST',f"/api/profiles/{partner['id']}/wishlists",{'title':'Christmas'}).json['wishlist']
    path=f"/api/households/{home['id']}/list-collections"
    body=dict(title='Family Christmas',wishlist_ids=[child_list['id']],share_publicly=True,use_family_photo=True)
    assert mutate(owner,'POST',path,body).status_code==201
    assert mutate(adult,'POST',path,{**body,'wishlist_ids':[adult_list['id']],'share_publicly':False}).status_code==201
    from backend.app.models import FamilyListCollection
    with app.app_context():
        row=FamilyListCollection.query.filter_by(household_id=home['id']).first()
        assert set(row.wishlist_ids)=={child_list['id'],adult_list['id']}
        assert db.session.get(Wishlist,child_list['id']).share_publicly is True
        assert db.session.get(Wishlist,adult_list['id']).share_publicly is False
