from backend.app.extensions import db
from backend.app.models import FamilyFollow, User, Household, HouseholdMembership, HouseholdProfileAccess, PersonProfile, WishlistItem
from backend.tests.test_reservation_privacy import register, mutate


def test_family_search_and_co_buy_acceptance(app, monkeypatch):
    emails=[]
    monkeypatch.setattr("backend.app.invitation_mail.send_co_buy_invitation",lambda *args: emails.append(args) or True)
    owner, parent, buyer, other, recipient = [app.test_client() for _ in range(5)]
    users = [register(client, name, name + '@example.com') for client, name in zip(
        [owner, parent, buyer, other, recipient], ['owner', 'parent', 'buyer', 'other', 'recipient'])]
    with app.app_context():
        home = Household(name='Family', owner_id=users[0]['id'])
        db.session.add(home)
        db.session.flush()
        for user, role in zip(users, ['owner', 'admin', 'admin', 'viewer', 'admin']):
            db.session.add(HouseholdMembership(household_id=home.id, user_id=user['id'], role=role))
        profile = PersonProfile(display_name='Recipient', account_user_id=users[4]['id'])
        db.session.add(profile)
        db.session.flush()
        db.session.add(HouseholdProfileAccess(household_id=home.id, profile_id=profile.id))
        item = WishlistItem(profile_id=profile.id, name='Bicycle', quantity=1)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    assert buyer.get('/api/households/search?q=parent@').json['households'][0]['name'] == 'Family'
    assert buyer.get('/api/households/search?q=owner@').json['households'][0]['name'] == 'Family'
    row = mutate(owner, 'POST', f'/api/items/{item_id}/reservations', {'private_note': 'Secret'}).json['reservation']
    path = f"/api/reservations/{row['id']}"
    assert mutate(owner, 'POST', path + '/co-buyers', {'email': 'recipient@example.com'}).status_code == 400
    assert mutate(owner, 'POST', path + '/co-buyers', {'email': 'other@example.com'}).status_code == 400
    with app.app_context():
        db.session.add(FamilyFollow(follower_id=users[0]['id'], followed_id=users[2]['id']))
        db.session.commit()
    options=owner.get(path+'/co-buyers/options')
    assert options.status_code==200
    assert [p['name'] for p in options.json['people']]==['buyer', 'parent']
    assert other.get(path+'/co-buyers/options').status_code==404
    assert mutate(owner, 'POST', path + '/co-buyers', {'user_id': users[2]['id'], 'share_percent':'40.25'}).status_code == 201
    assert len(emails)==1 and emails[0][-1]=='40.25'
    assert mutate(owner,'POST',path+'/co-buyers',{'user_id':users[1]['id'],'share_percent':'60'}).status_code==400
    assert mutate(parent,'PATCH','/api/notification-preferences',{'co_buy_emails':False}).status_code==200
    assert mutate(owner,'POST',path+'/co-buyers',{'user_id':users[1]['id'],'share_percent':'30'}).status_code==201
    assert len(emails)==1
    parent_invite=parent.get('/api/co-buy-invitations').json['invitations'][0]
    assert parent_invite['share_percent']=='30.00'
    assert mutate(parent,'POST',f"/api/co-buy-invitations/{parent_invite['id']}/decline",{}).status_code==200
    assert parent.get('/api/co-buy-invitations').json['invitations']==[]
    assert mutate(parent,'POST',f"/api/co-buy-invitations/{parent_invite['id']}/accept",{}).status_code==409
    notifications=buyer.get('/api/notifications').json['notifications']
    assert any(n.get('co_buy_invitation_id') and 'Bicycle' in n['message'] for n in notifications)
    assert not other.get('/api/notifications').json['notifications']
    assert mutate(buyer, 'PATCH', path, {'status': 'purchased'}).status_code == 404
    invitation = buyer.get('/api/co-buy-invitations').json['invitations'][0]
    assert mutate(other, 'POST', f"/api/co-buy-invitations/{invitation['id']}/accept").status_code == 404
    assert mutate(buyer, 'POST', f"/api/co-buy-invitations/{invitation['id']}/accept").status_code == 200
    assert not any(n.get('co_buy_invitation_id') for n in buyer.get('/api/notifications').json['notifications'])
    shared = buyer.get('/api/my-shopping').json['reservations']
    assert len(shared) == 1 and shared[0]['private_note'] is None
    assert mutate(buyer, 'PATCH', path, {'status': 'cancelled'}).status_code == 403
    assert mutate(buyer, 'PATCH', path, {'status': 'purchased'}).status_code == 200
    assert owner.get('/api/my-shopping').json['reservations'][0]['status'] == 'purchased'
    assert recipient.get('/api/my-shopping').json['reservations'] == []


def test_buy_reuses_hold_and_blocks_other_shoppers(app):
    from backend.app.models import GiftReservation
    owner, other = app.test_client(), app.test_client()
    users = [register(owner, 'Owner', 'holdowner@example.com'), register(other, 'Other', 'holdother@example.com')]
    with app.app_context():
        home = Household(name='Hold family', owner_id=users[0]['id'])
        db.session.add(home)
        db.session.flush()
        for user in users:
            db.session.add(HouseholdMembership(household_id=home.id, user_id=user['id'], role='admin'))
        person = PersonProfile(display_name='Child')
        db.session.add(person)
        db.session.flush()
        db.session.add(HouseholdProfileAccess(household_id=home.id, profile_id=person.id))
        item = WishlistItem(profile_id=person.id, name='Only one', quantity=1)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    path = f'/api/items/{item_id}/reservations'
    first = mutate(owner, 'POST', path, {'reuse_existing': True})
    assert first.status_code == 201
    again = mutate(owner, 'POST', path, {'reuse_existing': True})
    assert again.status_code == 200
    assert first.json['reservation']['id'] == again.json['reservation']['id']
    assert mutate(other, 'POST', path, {'reuse_existing': True}).status_code == 409
    with app.app_context():
        assert GiftReservation.query.filter_by(item_id=item_id).count() == 1
    reservation_id = first.json['reservation']['id']
    assert mutate(other,'PUT',f'/api/items/{item_id}/availability-alert',{}).status_code==200
    assert mutate(other,'PUT',f'/api/items/{item_id}/availability-alert',{}).status_code==200
    assert not any(n.get('availability_alert_id') for n in other.get('/api/notifications').json['notifications'])
    assert mutate(owner, 'PATCH', f'/api/reservations/{reservation_id}', {'status': 'cancelled'}).status_code == 200
    alerts=[n for n in other.get('/api/notifications').json['notifications'] if n.get('availability_alert_id')]
    assert len(alerts)==1 and 'available again' in alerts[0]['message']
    assert len([n for n in other.get('/api/notifications').json['notifications'] if n.get('availability_alert_id')])==1
    assert mutate(owner,'POST',f"/api/availability-alerts/{alerts[0]['availability_alert_id']}/read",{}).status_code==404
    assert mutate(other,'POST',f"/api/availability-alerts/{alerts[0]['availability_alert_id']}/read",{}).status_code==200
    assert mutate(other, 'POST', path, {'reuse_existing': True}).status_code == 201
