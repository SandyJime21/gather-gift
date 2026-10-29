from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import mutate
from backend.app.extensions import db
from backend.app.models import Wishlist, WishlistItem, WishlistLetter


def test_scheduled_letters_parent_control_child_isolation_and_manual_wishes(app):
    parent,child,stranger,home,profiles,lists,_,_=child_setup(app)
    path=f"/api/households/{home['id']}/wishlist-letters"
    payload=dict(title='Dream wishes',sender_name='Santa',send_on='2099-12-01',profile_ids=[p['id'] for p in profiles])
    assert mutate(stranger,'POST',path,payload).status_code==403
    assert mutate(child,'POST',path,payload).status_code==403
    assert mutate(parent,'POST',path,{**payload,'profile_ids':[999999]}).status_code==404
    assert mutate(parent,'POST',path,{**payload,'send_on':'invalid'}).status_code==400
    created=mutate(parent,'POST',path,payload)
    assert created.status_code==201,created.json
    letters=created.json['letters']
    own=next(row for row in letters if row['profile_id']==profiles[0]['id'])
    sibling=next(row for row in letters if row['profile_id']==profiles[1]['id'])
    assert child.get('/api/child/me').json['letters']==[]
    assert mutate(child,'POST',f"/api/child/wishlists/{own['wishlist_id']}/items",dict(name='A dragon')).status_code==404
    assert mutate(parent,'PATCH',path+'/'+str(own['id']),dict(title='Magic wishes',sender_name='Birthday Fairy',send_on='2020-01-01')).status_code==200
    visible=child.get('/api/child/me').json
    assert [row['id'] for row in visible['letters']]==[own['id']]
    assert visible['letters'][0]['sender_name']=='Birthday Fairy'
    assert own['wishlist_id'] in [row['id'] for row in visible['wishlists']]
    assert sibling['wishlist_id'] not in [row['id'] for row in visible['wishlists']]
    assert mutate(child,'PATCH',path+'/'+str(own['id']),payload).status_code==403
    added=mutate(child,'POST',f"/api/child/wishlists/{own['wishlist_id']}/items",dict(name='A day with Grandma',description='Baking cookies together'))
    assert added.status_code==201,added.json
    assert mutate(child,'POST',f"/api/child/wishlists/{sibling['wishlist_id']}/items",dict(name='Wrong child')).status_code==404
    assert mutate(parent,'DELETE',path+'/'+str(own['id'])).status_code==200
    assert child.get('/api/child/me').json['letters']==[]
    with app.app_context():
        assert db.session.get(Wishlist,own['wishlist_id']).share_publicly is False
        assert db.session.get(WishlistItem,added.json['item']['id']) is not None
        assert db.session.get(WishlistLetter,own['id']) is None


def test_letter_is_created_without_child_login_then_appears_in_child_mode(app):
    parent,_,_,home,profiles,_,_,_=child_setup(app)
    profile=profiles[1]
    path=f"/api/households/{home['id']}/wishlist-letters"
    letter=mutate(parent,'POST',path,dict(title='Santa list',sender_name='Santa',send_on='2020-01-01',profile_ids=[profile['id']])).json['letters'][0]
    assert mutate(parent,'POST','/api/household-session/pin',dict(pin='123456',password='a-long-test-password')).status_code==200
    assert mutate(parent,'POST','/api/household-session/switch',dict(profile_id=profile['id'])).status_code==200
    result=parent.get('/api/child/me')
    assert result.status_code==200
    assert result.json['letters'][0]['id']==letter['id']


def test_adults_can_save_manual_wishes_without_product_links_or_prices(app):
    parent,_,_,_,_,_,_,_=child_setup(app)
    result=mutate(parent,'POST','/api/personal-wishes',dict(name='A family picnic',description='At the park',visibility='private',viewer_ids=[]))
    assert result.status_code==201,result.json
    item=result.json['wish']['item']
    assert item['name']=='A family picnic'
    assert item['estimated_price'] is None
    assert not item['product_url']
