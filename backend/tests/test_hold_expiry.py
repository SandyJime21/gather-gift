from datetime import datetime, timedelta, timezone
from backend.app.extensions import db
from backend.app.models import (User, Household, HouseholdMembership, HouseholdProfileAccess,
    PersonProfile, WishlistItem, GiftReservation, SupportAccessRequest, SupportAccessGrant, AuditLog)
from backend.tests.test_reservation_privacy import register, mutate


def setup_holds(app):
    owner, shopper, stranger, staff = [app.test_client() for _ in range(4)]
    people = [register(client, name, name + '@holds.example.com') for client, name in zip(
        [owner, shopper, stranger], ['owner', 'shopper', 'stranger'])]
    with app.app_context():
        home = Household(name='Home', owner_id=people[0]['id'])
        db.session.add(home)
        db.session.flush()
        for user in people[:2]:
            db.session.add(HouseholdMembership(household_id=home.id, user_id=user['id'], role='admin'))
        profile = PersonProfile(display_name='Child')
        db.session.add(profile)
        db.session.flush()
        db.session.add(HouseholdProfileAccess(household_id=home.id, profile_id=profile.id))
        item = WishlistItem(profile_id=profile.id, name='Gift', quantity=1)
        agent = User(name='Support', email='support@holds.example.com', is_support=True, password_hash='unused')
        db.session.add_all([item, agent])
        db.session.flush()
        access = SupportAccessRequest(household_id=home.id, support_user_id=agent.id, status='approved', reason='Stuck hold')
        db.session.add(access)
        db.session.flush()
        grant = SupportAccessGrant(request_id=access.id, household_id=home.id, support_user_id=agent.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
        db.session.add(grant)
        db.session.commit()
        ids = home.id, item.id, grant.id, agent.id
    with staff.session_transaction() as session:
        session['user_id'] = ids[3]
        session['auth_mode'] = 'support'
    return owner, shopper, stranger, staff, ids


def test_24_hour_expiry_cannot_be_extended_or_revived(app):
    owner, shopper, _, _, (_, item_id, _, _) = setup_holds(app)
    path = f'/api/items/{item_id}/reservations'
    reservation = mutate(shopper, 'POST', path, {}).json['reservation']['id']
    with app.app_context():
        row = db.session.get(GiftReservation, reservation)
        row.created_at = datetime.now(timezone.utc) - timedelta(hours=23)
        db.session.commit()
        original_created_at = row.created_at
    assert shopper.get('/api/my-shopping').json['reservations'][0]['status'] == 'reserved'
    assert mutate(shopper, 'POST', path, {'reuse_existing': True}).json['reservation']['id'] == reservation
    with app.app_context():
        row = db.session.get(GiftReservation, reservation)
        assert row.created_at == original_created_at
        row.created_at = datetime.now(timezone.utc) - timedelta(hours=24)
        db.session.commit()
    assert shopper.get('/api/my-shopping').json['reservations'] == []
    assert mutate(shopper, 'PATCH', f'/api/reservations/{reservation}', {'status': 'reserved'}).status_code == 409
    assert mutate(owner, 'POST', path, {}).status_code == 201
    with app.app_context():
        assert db.session.get(GiftReservation, reservation).status == 'cancelled'


def test_owner_and_approved_support_release_holds(app):
    owner, shopper, stranger, staff, (household_id, item_id, grant_id, _) = setup_holds(app)
    path = f'/api/households/{household_id}/holds'
    support_path = f'/api/support/grants/{grant_id}/holds'
    reservation = mutate(shopper, 'POST', f'/api/items/{item_id}/reservations', {}).json['reservation']['id']
    assert stranger.get(path).status_code == 403
    assert mutate(stranger, 'DELETE', path + f'/{reservation}').status_code == 403
    assert owner.get(path).json['holds'][0]['id'] == reservation
    assert mutate(owner, 'DELETE', path + f'/{reservation}').status_code == 200
    reservation = mutate(shopper, 'POST', f'/api/items/{item_id}/reservations', {}).json['reservation']['id']
    assert staff.get(support_path).json['holds'][0]['id'] == reservation
    assert mutate(staff, 'DELETE', support_path + f'/{reservation}').status_code == 200
    reservation = mutate(shopper, 'POST', f'/api/items/{item_id}/reservations', {}).json['reservation']['id']
    with app.app_context():
        grant = db.session.get(SupportAccessGrant, grant_id)
        grant.revoked_at = datetime.now(timezone.utc)
        db.session.commit()
        assert AuditLog.query.filter_by(action='support.hold_released').count() == 1
    assert mutate(staff, 'DELETE', support_path + f'/{reservation}').status_code == 403
    assert mutate(shopper, 'PATCH', f'/api/reservations/{reservation}', {'status': 'cancelled'}).status_code == 200


def test_purchased_gifts_do_not_expire(app):
    _, shopper, _, _, (_, item_id, _, _) = setup_holds(app)
    reservation = mutate(shopper, 'POST', f'/api/items/{item_id}/reservations', {}).json['reservation']['id']
    assert mutate(shopper, 'PATCH', f'/api/reservations/{reservation}', {'status': 'purchased'}).status_code == 200
    with app.app_context():
        db.session.get(GiftReservation, reservation).created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        db.session.commit()
    assert shopper.get('/api/my-shopping').json['reservations'][0]['status'] == 'purchased'

def test_expired_hold_notifies_its_shopper_once(app):
    owner,shopper,stranger,_,(_,item_id,_,_)=setup_holds(app)
    reservation=mutate(shopper,'POST',f'/api/items/{item_id}/reservations',{}).json['reservation']['id']
    with app.app_context():
        db.session.get(GiftReservation,reservation).created_at=datetime.now(timezone.utc)-timedelta(hours=25)
        db.session.commit()
    notices=shopper.get('/api/notifications').json['notifications']
    expired=[n for n in notices if n.get('hold_expired')]
    assert len(expired)==1
    assert expired[0]['url']=='/gifting'
    assert 'Gift' in expired[0]['message']
    assert not owner.get('/api/notifications').json['notifications']
    assert not stranger.get('/api/notifications').json['notifications']
    assert len([n for n in shopper.get('/api/notifications').json['notifications'] if n.get('hold_expired')])==1
    assert mutate(shopper,'PATCH','/api/notification-preferences',{'holds':False}).status_code==200
    assert not shopper.get('/api/notifications').json['notifications']
