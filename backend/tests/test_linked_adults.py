from urllib.parse import urlsplit
from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import HouseholdInvitation, HouseholdMembership, PersonProfile, WishlistItem, FamilyFollow


def joined_family(app):
    owner, adult, outsider = [app.test_client() for _ in range(3)]
    o=register(owner,'Creator','linked-owner@example.com')
    a=register(adult,'Joined adult','linked-adult@example.com')
    register(outsider,'Outside','linked-outside@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Joined family','profiles':[
        {'display_name':'Partner','relationship':'parent'},{'display_name':'Kid','relationship':'child'}]}).json['household']
    profiles=owner.get(f"/api/households/{home['id']}").json['profiles']
    partner=next(p for p in profiles if p['display_name']=='Partner')
    kid=next(p for p in profiles if p['display_name']=='Kid')
    response=mutate(owner,'POST',f"/api/households/{home['id']}/adult-invitations",{'profile_id':partner['id'],'email':'linked-adult@example.com'})
    assert response.status_code==201,response.json
    token=response.json['email_message']['link'].rsplit('/',1)[-1]
    assert mutate(outsider,'POST','/api/invitations/accept',{'token':token}).status_code==403
    accepted=mutate(adult,'POST','/api/invitations/accept',{'token':token})
    assert accepted.status_code==200,accepted.json
    return owner,adult,outsider,home,partner,kid,o,a


def test_adult_owns_wishes_and_creator_only_edits_child_items(app):
    owner,adult,outsider,home,partner,kid,_,_=joined_family(app)
    assert adult.get('/api/auth/me').json['households'][0]['role']=='family_member'
    own_list=adult.get(f"/api/profiles/{partner['id']}/wishlists").json['wishlists'][0]['id']
    own=mutate(adult,'POST',f'/api/wishlists/{own_list}/items',{'name':'Adult gift'})
    assert own.status_code==201,own.json
    iid=own.json['item']['id']
    assert mutate(owner,'DELETE',f'/api/items/{iid}').status_code==404
    assert mutate(owner,'PATCH',f'/api/items/{iid}',{'name':'Hijack'}).status_code==404
    assert mutate(owner,'POST','/api/household-session/switch',{'profile_id':partner['id']}).status_code==403
    assert mutate(adult,'PATCH',f'/api/items/{iid}',{'name':'My change'}).status_code==200
    assert mutate(adult,'DELETE',f'/api/items/{iid}').status_code==200
    child_list=adult.get(f"/api/profiles/{kid['id']}/wishlists").json['wishlists'][0]['id']
    child_item=mutate(adult,'POST',f'/api/wishlists/{child_list}/items',{'name':'Kid gift'})
    assert child_item.status_code==201,child_item.json
    cid=child_item.json['item']['id']
    assert mutate(adult,'PATCH',f'/api/items/{cid}',{'name':'Not allowed'}).status_code==404
    assert mutate(adult,'DELETE',f'/api/items/{cid}').status_code==404
    assert mutate(owner,'DELETE',f'/api/items/{cid}').status_code==200
    assert mutate(adult,'PATCH',f"/api/profiles/{kid['id']}",{'display_name':'No'}).status_code==404


def test_gift_suggestion_requires_recipient_approval_and_own_list(app):
    owner,adult,outsider,home,partner,kid,_,_=joined_family(app)
    payload={'name':'Suggested book','product_url':'https://example.com/book','estimated_price':'12.00'}
    response=mutate(owner,'POST',f"/api/profiles/{partner['id']}/suggestions",payload)
    assert response.status_code==201,response.json
    sid=response.json['suggestion_id']
    assert mutate(outsider,'POST',f"/api/profiles/{partner['id']}/suggestions",payload).status_code==404
    notices=adult.get('/api/notifications').json['notifications']
    assert any(n.get('suggestion_id')==sid for n in notices)
    assert not any(n.get('suggestion_id') for n in owner.get('/api/notifications').json['notifications'])
    own_list=adult.get(f"/api/profiles/{partner['id']}/wishlists").json['wishlists'][0]['id']
    kid_list=owner.get(f"/api/profiles/{kid['id']}/wishlists").json['wishlists'][0]['id']
    assert mutate(owner,'POST',f'/api/gift-suggestions/{sid}/respond',{'action':'accept','wishlist_id':own_list}).status_code==404
    assert mutate(adult,'POST',f'/api/gift-suggestions/{sid}/respond',{'action':'accept','wishlist_id':kid_list}).status_code==400
    assert adult.get(f'/api/wishlists/{own_list}/items').json['items']==[]
    added=mutate(adult,'POST',f'/api/gift-suggestions/{sid}/respond',{'action':'accept','wishlist_id':own_list})
    assert added.status_code==201,added.json
    assert mutate(adult,'POST',f'/api/gift-suggestions/{sid}/respond',{'action':'accept','wishlist_id':own_list}).status_code==404
    assert not adult.get('/api/gift-suggestions').json['suggestions']


def test_joined_adult_inherits_followed_family_access_without_new_request(app):
    owner,adult,friend,home,partner,kid,oid,aid=joined_family(app)
    fh=mutate(friend,'POST','/api/households',{'name':'Followed family','profiles':[{'display_name':'Friend kid'}]}).json['household']
    invitation=mutate(friend,'POST',f"/api/households/{fh['id']}/invitations",{'email':'linked-owner@example.com','role':'shopper','share_all_profiles':True})
    token=invitation.json['invitation']['token']
    assert mutate(owner,'POST','/api/invitations/accept',{'token':token}).status_code==200
    homes=adult.get('/api/auth/me').json['households']
    assert any(h['id']==fh['id'] and h['role']=='shopper' for h in homes)
    assert adult.get(f"/api/households/{fh['id']}").status_code==200
    with app.app_context():
        assert not FamilyFollow.query.filter_by(follower_id=aid['id']).count()

def test_inherited_access_is_removed_after_leaving_family_and_members_cannot_escalate(app):
    owner,adult,friend,home,partner,kid,oid,aid=joined_family(app)
    fh=mutate(friend,'POST','/api/households',{'name':'External family','profiles':[]}).json['household']
    invitation=mutate(friend,'POST',f"/api/households/{fh['id']}/invitations",{'email':'linked-owner@example.com','role':'shopper','share_all_profiles':True})
    assert mutate(owner,'POST','/api/invitations/accept',{'token':invitation.json['invitation']['token']}).status_code==200
    assert adult.get(f"/api/households/{fh['id']}").status_code==200
    assert mutate(adult,'POST',f"/api/households/{home['id']}/invitations",{'email':'new@example.com','role':'admin'}).status_code==403
    assert mutate(adult,'POST',f"/api/households/{home['id']}/adult-invitations",{'profile_id':kid['id'],'email':'new@example.com'}).status_code==403
    assert mutate(adult,'PATCH',f"/api/households/{home['id']}/profiles/{kid['id']}/relationship",{'relationship':'mom'}).status_code==403
    with app.app_context():
        HouseholdMembership.query.filter_by(user_id=aid['id'],household_id=home['id']).delete()
        db.session.commit()
    assert adult.get(f"/api/households/{fh['id']}").status_code==404
    with app.app_context():
        assert not HouseholdMembership.query.filter_by(user_id=aid['id'],household_id=fh['id']).first()


def test_replaced_adult_invitation_revokes_old_link_and_only_intended_adult_can_join(app):
    owner,adult,_,home,partner,kid,_,_=joined_family(app)
    extra=mutate(owner,'POST',f"/api/households/{home['id']}/profiles",{'display_name':'Another adult','relationship':'parent'}).json['profile']
    first=mutate(owner,'POST',f"/api/households/{home['id']}/adult-invitations",{'profile_id':extra['id'],'email':'other@example.com'})
    old_token=first.json['email_message']['link'].rsplit('/',1)[-1]
    second=mutate(owner,'POST',f"/api/households/{home['id']}/adult-invitations",{'profile_id':extra['id'],'email':'newadult@example.com'})
    assert second.status_code==201
    newcomer=app.test_client();register(newcomer,'New adult','newadult@example.com')
    assert mutate(newcomer,'POST','/api/invitations/accept',{'token':old_token}).status_code==400
    token=second.json['email_message']['link'].rsplit('/',1)[-1]
    assert mutate(adult,'POST','/api/invitations/accept',{'token':token}).status_code==403
    assert mutate(newcomer,'POST','/api/invitations/accept',{'token':token}).status_code==200


def test_owner_can_remove_joined_member_without_taking_over_their_account(app):
    from backend.app.models import HouseholdProfileAccess
    owner,adult,outsider,home,partner,kid,oid,aid=joined_family(app)
    profiles=owner.get(f"/api/households/{home['id']}").json['profiles']
    linked=next(p for p in profiles if p['id']==partner['id'])
    assert linked['can_edit'] is False and linked['can_remove_from_family'] is True
    assert linked['member_email']=='linked-adult@example.com'
    assert mutate(owner,'PATCH',f"/api/profiles/{partner['id']}",{'display_name':'Take over'}).status_code==404
    own_list=adult.get(f"/api/profiles/{partner['id']}/wishlists").json['wishlists'][0]['id']
    item=mutate(adult,'POST',f'/api/wishlists/{own_list}/items',{'name':'Owned adult wish'}).json['item']
    path=f"/api/households/{home['id']}/profiles/{partner['id']}/member"
    assert mutate(adult,'DELETE',path,{}).status_code==403
    assert mutate(outsider,'DELETE',path,{}).status_code==403
    assert mutate(owner,'DELETE',path,{}).status_code==200
    assert not HouseholdMembership.query.filter_by(user_id=aid['id'],household_id=home['id']).first()
    assert not HouseholdProfileAccess.query.filter_by(household_id=home['id'],profile_id=partner['id']).first()
    assert adult.get(f"/api/households/{home['id']}").status_code==404
    assert adult.get(f"/api/profiles/{kid['id']}").status_code==404
    assert partner['id'] not in [p['id'] for p in owner.get(f"/api/households/{home['id']}").json['profiles']]
    assert mutate(adult,'PATCH',f"/api/items/{item['id']}",{'name':'Still mine'}).status_code==200
    assert mutate(owner,'PATCH',f"/api/items/{item['id']}",{'name':'Not yours'}).status_code==404


def test_authorized_owner_manages_unclaimed_adult_wishes_without_switching_profiles(app):
    owner,stranger=app.test_client(),app.test_client()
    register(owner,'Owner','unclaimed-owner@example.com')
    register(stranger,'Stranger','unclaimed-stranger@example.com')
    home=mutate(owner,'POST','/api/households',dict(name='Family',profiles=[dict(display_name='Unclaimed adult',relationship='parent')])).json['household']
    profile=owner.get(f"/api/households/{home['id']}").json['profiles'][0]
    assert owner.get(f"/api/profiles/{profile['id']}").json['profile']['can_remove_wishes'] is True
    wishlist=owner.get(f"/api/profiles/{profile['id']}/wishlists").json['wishlists'][0]
    added=mutate(owner,'POST',f"/api/wishlists/{wishlist['id']}/items",dict(name='A book'))
    assert added.status_code==201,added.json
    item_id=added.json['item']['id']
    assert mutate(stranger,'PATCH',f'/api/items/{item_id}',dict(name='No')).status_code==404
    assert mutate(owner,'PATCH',f'/api/items/{item_id}',dict(name='A cookbook')).status_code==200
    assert mutate(owner,'DELETE',f'/api/items/{item_id}').status_code==200
