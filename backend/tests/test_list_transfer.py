from backend.tests.test_wishlist_price_requests import setup_request
from backend.tests.test_reservation_privacy import mutate
from backend.app.extensions import db
from backend.app.models import WishlistItem,WishlistItemWishlist


def test_copy_move_deduplicate_and_preserve_original_gifts(app):
    owner,follower,_,profile,source=setup_request(app)
    target=mutate(owner,'POST',f"/api/profiles/{profile['id']}/wishlists",{'title':'Christmas'}).json['wishlist']
    def add(wid,name,url=''):
        response=mutate(owner,'POST',f'/api/wishlists/{wid}/items',{'name':name,'product_url':url,'image_url':'https://images.example/gift.jpg','estimated_price':'25','notes':'Keep these notes'})
        assert response.status_code==201,response.json
        return response.json['item']['id']
    unique=add(source['id'],'Unique gift','https://shop.example/unique')
    name_dupe=add(source['id'],'  TOY   train ')
    link_dupe=add(source['id'],'Different label','https://shop.example/item?utm_source=mail#details')
    add(target['id'],'toy train')
    add(target['id'],'Existing product','https://shop.example/item')
    path=f"/api/wishlists/{source['id']}/transfer"
    body=dict(wishlist_id=target['id'],mode='copy')
    assert mutate(follower,'POST',path,body).status_code==404
    copied=mutate(owner,'POST',path,body)
    assert copied.status_code==200,copied.json
    assert copied.json==dict(transferred=1,skipped=2,already_present=0,remaining=3)
    repeated=mutate(owner,'POST',path,body).json
    assert repeated==dict(transferred=0,skipped=2,already_present=1,remaining=3)
    moved=mutate(owner,'POST',path,{**body,'mode':'move'}).json
    assert moved==dict(transferred=0,skipped=2,already_present=1,remaining=2)
    with app.app_context():
        assert db.session.get(WishlistItem,unique).notes=='Keep these notes'
        assert db.session.get(WishlistItem,unique).image_path=='https://images.example/gift.jpg'
        assert WishlistItemWishlist.query.filter_by(item_id=unique,wishlist_id=target['id']).first()
        assert not WishlistItemWishlist.query.filter_by(item_id=unique,wishlist_id=source['id']).first()
        assert WishlistItemWishlist.query.filter_by(item_id=name_dupe,wishlist_id=source['id']).first()
        assert WishlistItemWishlist.query.filter_by(item_id=link_dupe,wishlist_id=source['id']).first()
    assert mutate(owner,'DELETE',f"/api/wishlists/{source['id']}",{}).status_code==200
    with app.app_context():assert db.session.get(WishlistItem,unique) is not None


def test_transfer_rejects_other_people_and_same_list(app):
    owner,_,_,profile,source=setup_request(app)
    home=mutate(owner,'POST','/api/households',{'name':'Another family','profiles':[{'display_name':'Pet','profile_type':'pet'}]}).json['household']
    other=owner.get(f"/api/households/{home['id']}").json['profiles'][0]
    target=mutate(owner,'POST',f"/api/profiles/{other['id']}/wishlists",{'title':'Other wishes'}).json['wishlist']
    path=f"/api/wishlists/{source['id']}/transfer"
    assert mutate(owner,'POST',path,dict(wishlist_id=source['id'],mode='move')).status_code==400
    assert mutate(owner,'POST',path,dict(wishlist_id=target['id'],mode='move')).status_code==400
    assert mutate(owner,'POST',path,dict(wishlist_id=999999,mode='copy')).status_code==404


def test_single_move_keeps_gift_identity_and_uses_named_list_not_everyday(app):
    owner,follower,_,profile,source=setup_request(app)
    target=mutate(owner,'POST',f"/api/profiles/{profile['id']}/wishlists",{'title':'Christmas'}).json['wishlist']
    created=mutate(owner,'POST',f"/api/wishlists/{source['id']}/items",{'name':'Book','notes':'Keep me','image_url':'https://images.example/book.jpg'}).json['item']
    path=f"/api/items/{created['id']}/move-list"
    assert mutate(follower,'POST',path,{'wishlist_id':target['id']}).status_code==403
    assert mutate(owner,'POST',path,{'wishlist_id':target['id']}).status_code==200
    items=owner.get(f"/api/wishlists/{target['id']}/items").json['items']
    assert [i['id'] for i in items]==[created['id']]
    assert items[0]['occasions']==['Christmas']
    assert items[0]['notes']=='Keep me'
    assert owner.get(f"/api/wishlists/{source['id']}/items").json['items']==[]
