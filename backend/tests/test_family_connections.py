from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import FamilyFollow


def test_new_account_mutual_follow_and_selected_share_back(app):
    owner, guest, stranger = [app.test_client() for _ in range(3)]
    register(owner, 'Owner', 'follow-owner@example.com')
    home = mutate(owner, 'POST', '/api/households', {'name': 'Owners', 'profiles': [{'display_name': 'One'}, {'display_name': 'Two'}]}).json['household']
    profiles = owner.get(f"/api/households/{home['id']}").json['profiles']
    response = mutate(owner, 'POST', f"/api/households/{home['id']}/invitations", {'email': 'follow-guest@example.com', 'role': 'shopper', 'profile_ids': [profiles[0]['id']]})
    token = response.json['invitation']['token']
    assert owner.get('/api/family-connections').json['connections'] == []
    register(stranger, 'Stranger', 'follow-stranger@example.com')
    assert mutate(stranger, 'POST', '/api/invitations/accept', {'token': token}).status_code == 403
    register(guest, 'Guest', 'follow-guest@example.com')
    for _ in range(2):
        assert mutate(guest, 'POST', '/api/invitations/accept', {'token': token}).status_code == 200
    with app.app_context():
        assert FamilyFollow.query.count() == 2
    connection = guest.get('/api/family-connections').json['connections'][0]
    assert connection['mutual'] is True
    assert connection['shared_households'] == [{'id': home['id'], 'name': 'Owners'}]
    back = mutate(guest, 'POST', '/api/households', {'name': 'Guests', 'profiles': [{'display_name': 'Shared'}, {'display_name': 'Private'}]}).json['household']
    back_path = f"/api/households/{back['id']}"
    back_profiles = guest.get(back_path).json['profiles']
    payload = {'household_id': back['id'], 'profile_ids': [back_profiles[0]['id']]}
    assert mutate(stranger, 'POST', f"/api/family-connections/{connection['user_id']}/share", payload).status_code == 404
    assert mutate(guest, 'POST', f"/api/family-connections/{connection['user_id']}/share", {**payload, 'profile_ids': [profiles[0]['id']]}).status_code == 400
    assert mutate(guest, 'POST', f"/api/family-connections/{connection['user_id']}/share", payload).status_code == 200
    assert [p['id'] for p in owner.get(back_path).json['profiles']] == [back_profiles[0]['id']]

def test_existing_user_lookup_request_notification_and_acceptance(app):
    owner, guest, stranger = [app.test_client() for _ in range(3)]
    register(owner, 'Owner', 'request-owner@example.com')
    register(guest, 'Guest', 'request-guest@example.com')
    register(stranger, 'Stranger', 'request-stranger@example.com')
    home = mutate(owner, 'POST', '/api/households', {'name':'Request family','profiles':[{'display_name':'One'}]}).json['household']
    profiles = owner.get(f"/api/households/{home['id']}").json['profiles']
    assert mutate(owner,'POST','/api/families/lookup',{'email':'request-guest@example.com'}).json['match']['name'] == 'Guest'
    assert mutate(owner,'POST','/api/families/lookup',{'email':'new@example.com'}).json['match'] is None
    mutate(owner,'POST',f"/api/households/{home['id']}/invitations",{'email':'request-guest@example.com','role':'shopper','profile_ids':[profiles[0]['id']]})
    sent=owner.get('/api/invitations').json['sent'][0]
    assert sent['status']=='pending'
    assert guest.get(f"/api/households/{home['id']}").status_code == 404
    assert guest.get('/api/notifications').json['notifications'][0]['invitation_id']==sent['id']
    assert stranger.get('/api/invitations').json == {'sent':[], 'received':[]}
    assert mutate(stranger,'POST','/api/invitations/accept',{'invitation_id':sent['id']}).status_code==400
    assert mutate(guest,'POST','/api/invitations/accept',{'invitation_id':sent['id']}).status_code==200
    assert owner.get('/api/invitations').json['sent'][0]['status']=='accepted'
    assert guest.get('/api/notifications').json['notifications']==[]
    assert guest.get('/api/family-connections').json['connections'][0]['mutual']

def test_decline_request_preserves_history_and_prevents_acceptance(app):
    owner, guest = app.test_client(), app.test_client()
    register(owner,'Owner','decline-owner@example.com')
    register(guest,'Guest','decline-guest@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Family','profiles':[{'display_name':'Sam'}]}).json['household']
    pid=owner.get(f"/api/households/{home['id']}").json['profiles'][0]['id']
    result=mutate(owner,'POST',f"/api/households/{home['id']}/invitations",{'email':'decline-guest@example.com','role':'shopper','profile_ids':[pid]}).json
    row=guest.get('/api/invitations').json['received'][0]
    assert mutate(owner,'POST',f"/api/invitations/{row['id']}/decline",{}).status_code==404
    assert mutate(guest,'POST',f"/api/invitations/{row['id']}/decline",{}).status_code==200
    assert owner.get('/api/invitations').json['sent'][0]['status']=='declined'
    assert guest.get('/api/notifications').json['notifications']==[]
    assert mutate(guest,'POST','/api/invitations/accept',{'token':result['invitation']['token']}).status_code==400
    assert guest.get('/api/family-connections').json['connections']==[]

def test_auto_sharing_includes_future_profiles_but_excludes_private_gifts(app):
    owner, guest = app.test_client(), app.test_client()
    register(owner,'Owner','auto-owner@example.com')
    register(guest,'Guest','auto-guest@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Automatic family','profiles':[{'display_name':'Alex'},{'display_name':'Blair'}]}).json['household']
    path=f"/api/households/{home['id']}"
    profiles=owner.get(path).json['profiles']
    response=mutate(owner,'POST',path+'/invitations',{'email':'auto-guest@example.com','role':'shopper','share_all_profiles':True})
    assert response.status_code==201,response.json
    assert guest.get(path).status_code==404
    assert mutate(guest,'POST','/api/invitations/accept',{'token':response.json['invitation']['token']}).status_code==200
    assert len(guest.get(path).json['profiles'])==2
    added=mutate(owner,'POST',path+'/profiles',{'display_name':'New member'}).json['profile']
    assert added['id'] in [p['id'] for p in guest.get(path).json['profiles']]
    wishlist=owner.get(f"/api/profiles/{added['id']}/wishlists").json['wishlists'][0]
    shared=mutate(owner,'POST',f"/api/wishlists/{wishlist['id']}/items",{'name':'Shared book'}).json['item']
    hidden=mutate(owner,'POST',f"/api/wishlists/{wishlist['id']}/items",{'name':'Family-only book','family_only':True}).json['item']
    mutate(owner,'POST','/api/personal-wishes',{'name':'Private jewelry','visibility':'private','viewer_ids':[]})
    mutate(owner,'POST','/api/personal-wishes',{'name':'Family-only jewelry','visibility':'family','viewer_ids':[]})
    names=[i['name'] for i in guest.get('/api/shopping').json['items']]
    assert 'Shared book' in names
    assert 'Family-only book' not in names
    assert 'Private jewelry' not in names
    assert 'Family-only jewelry' not in names
    assert mutate(guest,'POST',f"/api/items/{hidden['id']}/reservations",{}).status_code==404
    assert guest.get(f"/api/profiles/{added['id']}").status_code==200
    assert mutate(guest,'PATCH',f"/api/profiles/{added['id']}",{'display_name':'Not allowed'}).status_code==404
    assert added['id'] in [p['id'] for p in guest.get('/api/wishlist').json['family_profiles']]

def test_request_photo_only_visible_to_invited_account(app, tmp_path):
    from backend.app.models import Household
    owner, guest, stranger = [app.test_client() for _ in range(3)]
    for client, name in [(owner,'photoowner'),(guest,'photoguest'),(stranger,'photostranger')]:
        register(client,name,name+'@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Photo family','profiles':[]}).json['household']
    app.config['UPLOAD_FOLDER']=str(tmp_path)
    (tmp_path/'family.png').write_bytes(b'family-photo')
    with app.app_context():
        db.session.get(Household,home['id']).photo_path='/api/uploads/family.png'
        db.session.commit()
    response=mutate(owner,'POST',f"/api/households/{home['id']}/invitations",{'email':'photoguest@example.com','role':'shopper','share_all_profiles':True})
    assert response.status_code == 201
    notification=guest.get('/api/notifications').json['notifications'][0]
    assert notification['household_name']=='Photo family'
    photo=notification['family_photo']
    assert guest.get(photo).data==b'family-photo'
    assert stranger.get(photo).status_code==404
    assert app.test_client().get(photo).status_code==401
    assert mutate(guest,'POST',f"/api/invitations/{notification['invitation_id']}/decline",{}).status_code==200
    assert guest.get(photo).status_code==404

def test_name_search_matches_only_adults_never_children(app):
    from backend.app.models import PersonProfile
    owner, guest = app.test_client(), app.test_client()
    register(owner,'Morgan Parker','nameowner@example.com')
    register(guest,'Searcher','namesearcher@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Parker family','profiles':[{'display_name':'Tiny Secretkid'},{'display_name':'Jordan Adultname'}]}).json['household']
    with app.app_context():
        PersonProfile.query.filter_by(display_name='Jordan Adultname').one().is_adult=True
        db.session.commit()
    for query in ['Morgan','Parker','Morgan Parker','Jordan','Adultname','Jordan Adultname']:
        response=mutate(guest,'POST','/api/families/name-search',{'query':query})
        assert response.status_code==200
        assert response.json['matches'][0]['name']=='Parker family'
        assert 'email' not in response.json['matches'][0]
    for query in ['Tiny','Secretkid','Tiny Secretkid']:
        assert mutate(guest,'POST','/api/families/name-search',{'query':query}).json['matches']==[]
    own=mutate(guest,'POST','/api/households',{'name':'Searcher family','profiles':[]}).json['household']
    target=owner.get('/api/auth/me').json['user']['id']
    assert mutate(guest,'POST',f"/api/households/{own['id']}/invitations",{'recipient_user_id':target,'role':'shopper','share_all_profiles':True}).status_code==201

def test_family_search_preview_shows_only_public_gifts(app):
    owner, visitor = app.test_client(), app.test_client()
    register(owner,'Public adult','public-preview@example.com')
    register(visitor,'Visitor','preview-visitor@example.com')
    for visibility in ['public','followers','private','family']:
        result=mutate(owner,'POST','/api/personal-wishes',{'name':visibility+' gift','visibility':visibility,'viewer_ids':[]})
        assert result.status_code == 201, result.json
    owner_id=owner.get('/api/auth/me').json['user']['id']
    response=visitor.get(f'/api/families/{owner_id}/public-wishes')
    assert response.status_code==200
    assert [w['name'] for w in response.json['wishes']]==['public gift']
    assert set(response.json['wishes'][0])=={'id','name','image','occasion','store_name'}

def test_automatic_acceptance_shares_families_both_ways_and_repairs_missing_membership(app):
    from backend.app.models import HouseholdMembership
    sender, recipient = app.test_client(), app.test_client()
    register(sender,'Sender','reciprocal-sender@example.com')
    register(recipient,'Recipient','reciprocal-recipient@example.com')
    first=mutate(sender,'POST','/api/households',{'name':'First family','profiles':[]}).json['household']
    second=mutate(recipient,'POST','/api/households',{'name':'Second family','profiles':[]}).json['household']
    response=mutate(sender,'POST',f"/api/households/{first['id']}/invitations",{'email':'reciprocal-recipient@example.com','role':'shopper','share_all_profiles':True})
    assert mutate(recipient,'POST','/api/invitations/accept',{'token':response.json['invitation']['token']}).status_code==200
    sender_id=sender.get('/api/auth/me').json['user']['id']
    assert any(h['id']==second['id'] and h['role']=='shopper' for h in sender.get('/api/auth/me').json['households'])
    assert any(h['id']==first['id'] for h in recipient.get('/api/auth/me').json['households'])
    with app.app_context():
        HouseholdMembership.query.filter_by(user_id=sender_id,household_id=second['id']).delete()
        db.session.commit()
    assert any(h['id']==second['id'] for h in sender.get('/api/auth/me').json['households'])

def test_following_search_finds_personal_gift_titles_without_profile_membership(app):
    owner, shopper=app.test_client(),app.test_client()
    register(owner,'Book owner','bookowner@example.com')
    register(shopper,'Book shopper','bookshopper@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Book family','profiles':[]}).json['household']
    owner_id=owner.get('/api/auth/me').json['user']['id']
    shopper_id=shopper.get('/api/auth/me').json['user']['id']
    with app.app_context():
        db.session.add(FamilyFollow(follower_id=shopper_id,followed_id=owner_id))
        db.session.commit()
    assert mutate(owner,'POST','/api/personal-wishes',{'name':'Dinosaur story book','visibility':'followers','viewer_ids':[]}).status_code==201
    assert mutate(owner,'POST','/api/personal-wishes',{'name':'Private story book','visibility':'private','viewer_ids':[]}).status_code==201
    result=shopper.get('/api/shopping?q=book+dinosaur&sort=priority')
    assert result.status_code==200
    assert [i['name'] for i in result.json['items']]==['Dinosaur story book']
    item=result.json['items'][0]
    assert item['followed_by_you'] is True
    assert any(h['id']==home['id'] for h in item['households'])

def test_notification_preferences_persist_and_hide_alerts(app):
    owner, guest=app.test_client(),app.test_client()
    register(owner,'Notify owner','notify-owner@example.com')
    register(guest,'Notify guest','notify-guest@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Notify family','profiles':[]}).json['household']
    mutate(owner,'POST',f"/api/households/{home['id']}/invitations",{'email':'notify-guest@example.com','role':'shopper','share_all_profiles':True})
    assert guest.get('/api/notifications').json['notifications']
    response=mutate(guest,'PATCH','/api/notification-preferences',{'follow_requests':False})
    assert response.status_code==200
    assert guest.get('/api/notification-preferences').json['preferences']['follow_requests'] is False
    assert guest.get('/api/notifications').json['notifications']==[]
    assert guest.get('/api/invitations').json['received']
    assert mutate(guest,'PATCH','/api/notification-preferences',{'games':'false'}).status_code==400
    assert mutate(guest,'PATCH','/api/notification-preferences',{'unknown':True}).status_code==400
    assert mutate(guest,'PATCH','/api/notification-preferences',{'follow_requests':True}).status_code==200
    assert guest.get('/api/notifications').json['notifications']

def test_recommendations_use_saved_gifts_and_respect_shared_visibility(app,monkeypatch):
    shopper,owner=app.test_client(),app.test_client()
    register(shopper,'Shopper','recommend-shopper@example.com')
    register(owner,'Owner','recommend-owner@example.com')
    mutate(owner,'POST','/api/households',{'name':'Gift family','profiles':[]})
    shopper_id=shopper.get('/api/auth/me').json['user']['id']
    owner_id=owner.get('/api/auth/me').json['user']['id']
    with app.app_context():
        db.session.add(FamilyFollow(follower_id=shopper_id,followed_id=owner_id))
        db.session.commit()
    mutate(shopper,'POST','/api/personal-wishes',{'name':'Dinosaur book','visibility':'followers','viewer_ids':[]})
    mutate(owner,'POST','/api/personal-wishes',{'name':'Dinosaur puzzle','visibility':'followers','viewer_ids':[]})
    mutate(owner,'POST','/api/personal-wishes',{'name':'Hidden dinosaur gift','visibility':'private','viewer_ids':[]})
    app.config['SERPAPI_API_KEY']='test-key'
    calls=[]
    def products(query):
        calls.append(query)
        return [{'name':'Dinosaur toy','product_url':'https://example.com/toy','thumbnail':None,'store_name':'Store','estimated_price':'12.00','currency':'USD'}]
    monkeypatch.setattr('backend.app.api.search_products',products)
    response=shopper.get('/api/gift-recommendations')
    assert response.status_code==200
    assert response.json['personalized'] is True
    assert response.json['wishes'][0]['name']=='Dinosaur toy'
    assert [i['name'] for i in response.json['buys']]==['Dinosaur puzzle']
    assert calls==['Dinosaur book']
    assert shopper.get('/api/gift-recommendations').status_code==200
    assert len(calls)==1
