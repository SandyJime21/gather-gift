from backend.app.extensions import db
from backend.app.models import Household, HouseholdMembership, HouseholdProfileAccess, PersonProfile, Wishlist, WishlistItem, WishlistItemWishlist
from backend.tests.test_reservation_privacy import register, mutate


def test_address_is_private_until_shared_and_handover_is_saved(app):
    owner, viewer, stranger=[app.test_client() for _ in range(3)]
    users=[register(c,n,n+'-delivery@example.com') for c,n in zip([owner,viewer,stranger],['Owner','Viewer','Stranger'])]
    home=Household(name='Family',owner_id=users[0]['id']);db.session.add(home);db.session.flush()
    db.session.add_all([HouseholdMembership(household_id=home.id,user_id=users[0]['id'],role='owner'),HouseholdMembership(household_id=home.id,user_id=users[1]['id'],role='viewer',share_all_profiles=True)])
    person=PersonProfile(display_name='Child',is_adult=False);db.session.add(person);db.session.flush()
    db.session.add(HouseholdProfileAccess(household_id=home.id,profile_id=person.id))
    wishlist=Wishlist(profile_id=person.id,title='Birthday');item=WishlistItem(profile_id=person.id,name='Book')
    db.session.add_all([wishlist,item]);db.session.flush()
    db.session.add(WishlistItemWishlist(item_id=item.id,wishlist_id=wishlist.id));db.session.commit()
    path=f'/api/wishlists/{wishlist.id}/delivery'
    address='Recipient\n123 Example St\nCity, State 12345\nUSA'
    assert mutate(owner,'PATCH',path,{'address':address,'shared':False}).status_code==200
    assert viewer.get(path).json['address'] is None
    assert viewer.get(f'/api/items/{item.id}/delivery').json['addresses']==[]
    assert stranger.get(path).status_code==404
    assert mutate(viewer,'PATCH',path,{'address':'Changed','shared':True}).status_code==403
    assert mutate(owner,'PATCH',path,{'address':'','shared':True}).status_code==400
    assert mutate(owner,'PATCH',path,{'address':address,'shared':True}).status_code==200
    assert viewer.get(f'/api/items/{item.id}/delivery').json['addresses']==[{'list':'Birthday','address':address}]
    assert stranger.get(f'/api/items/{item.id}/delivery').status_code==404
    assert 'delivery_address' not in viewer.get(f'/api/wishlists/{wishlist.id}/items').json['items'][0]
    held=mutate(viewer,'POST',f'/api/items/{item.id}/reservations',{}).json['reservation']
    result=mutate(viewer,'PATCH',f"/api/reservations/{held['id']}",{'status':'purchased','delivery_method':'in_person'})
    assert result.status_code==200,result.json
    assert viewer.get('/api/my-shopping').json['reservations'][0]['delivery_method']=='in_person'
    assert mutate(owner,'PATCH',path,{'address':address,'shared':False}).status_code==200
    assert viewer.get(f'/api/items/{item.id}/delivery').json['addresses']==[]


def test_private_list_metadata_and_shared_addresses_do_not_leak_through_public_linked_items(app):
    owner, viewer = app.test_client(), app.test_client()
    owner_user = register(owner, 'Owner', 'private-list-owner@example.com')
    viewer_user = register(viewer, 'Viewer', 'private-list-viewer@example.com')
    home = Household(name='Family', owner_id=owner_user['id'])
    db.session.add(home); db.session.flush()
    db.session.add_all([HouseholdMembership(household_id=home.id,user_id=owner_user['id'],role='owner'),HouseholdMembership(household_id=home.id,user_id=viewer_user['id'],role='viewer',share_all_profiles=True)])
    profile = PersonProfile(display_name='Child',is_adult=False)
    db.session.add(profile);db.session.flush()
    db.session.add(HouseholdProfileAccess(household_id=home.id,profile_id=profile.id))
    private = Wishlist(profile_id=profile.id,title='Private surprises',share_publicly=False,share_delivery_address=True,delivery_address='Private address')
    public = Wishlist(profile_id=profile.id,title='Shared ideas',share_publicly=True,share_delivery_address=True,delivery_address='Shared address')
    item = WishlistItem(profile_id=profile.id,name='Book')
    db.session.add_all([private,public,item]);db.session.flush()
    db.session.add_all([WishlistItemWishlist(item_id=item.id,wishlist_id=private.id),WishlistItemWishlist(item_id=item.id,wishlist_id=public.id)])
    db.session.commit()
    lists = viewer.get(f'/api/profiles/{profile.id}/wishlists').json['wishlists']
    assert [row['title'] for row in lists] == ['Shared ideas']
    assert viewer.get(f'/api/wishlists/{private.id}/delivery').status_code == 404
    assert owner.get(f'/api/wishlists/{private.id}/delivery').json['address'] == 'Private address'
    assert viewer.get(f'/api/items/{item.id}/delivery').json['addresses'] == [{'list':'Shared ideas','address':'Shared address'}]
    preview = owner.get(f'/api/households/{home.id}/shopper-preview').json['profiles']
    assert [row['title'] for row in next(p for p in preview if p['id'] == profile.id)['wishlists']] == ['Shared ideas']
