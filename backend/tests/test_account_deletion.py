import pytest
from sqlalchemy import text
from backend.app.extensions import db
from backend.app.models import (User,Household,HouseholdMembership,HouseholdProfileAccess,PersonProfile,
                                Wishlist,WishlistItem,WishlistLetter,GiftReservation,PrivateGift)
from backend.tests.test_linked_adults import joined_family
from backend.tests.test_reservation_privacy import register,mutate


@pytest.fixture(autouse=True)
def foreign_keys(app,tmp_path):
    app.config['UPLOAD_FOLDER']=str(tmp_path)
    app.config['MAIL_OUTBOX_DIR']=str(tmp_path/'outbox')
    with app.app_context():
        db.session.remove()
        with db.engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA foreign_keys=ON')
            assert connection.exec_driver_sql('PRAGMA foreign_keys').scalar()==1
    yield


def confirm(client,preview,password='a-long-test-password'):
    return mutate(client,'DELETE','/api/auth/account',dict(confirmation_token=preview['confirmation_token'],password=password,confirm=True))


def test_transfers_family_children_letters_and_permissions_before_deleting_owner(app):
    owner,adult,outsider,home,partner,kid,o,a=joined_family(app)
    made=mutate(owner,'POST',f"/api/households/{home['id']}/child-accounts",dict(profile_id=kid['id'],password='child-test-password'))
    assert made.status_code==201,made.json
    child_id=made.json['child']['id']
    child=app.test_client()
    assert mutate(child,'POST','/api/child/login',dict(username=made.json['child']['username'],password='child-test-password')).status_code==200
    kid_list=owner.get(f"/api/profiles/{kid['id']}/wishlists").json['wishlists'][0]['id']
    item=mutate(owner,'POST',f'/api/wishlists/{kid_list}/items',dict(name='Keep this wish')).json['item']
    letter=mutate(owner,'POST',f"/api/households/{home['id']}/wishlist-letters",dict(title='Santa wishes',sender_name='Santa',send_on='2020-01-01',profile_ids=[kid['id']])).json['letters'][0]
    private=mutate(owner,'POST','/api/personal-wishes',dict(name='Private wish',visibility='private',viewer_ids=[])).json['wish']['item']
    preview=owner.get('/api/auth/account-deletion').json
    assert preview['families'][0]['successor']['id']==a['id']
    assert preview['children'][0]['successor_id']==a['id']
    assert confirm(owner,preview).status_code==200
    assert owner.get('/api/auth/me').status_code==401
    assert child.get('/api/auth/me').status_code==401
    with app.app_context():
        assert db.session.get(User,o['id']) is None
        assert db.session.get(Household,home['id']).owner_id==a['id']
        member=HouseholdMembership.query.filter_by(household_id=home['id'],user_id=a['id']).one()
        assert member.role=='owner' and member.is_family_member and member.share_all_profiles
        assert db.session.get(User,child_id).parent_user_id==a['id']
        assert db.session.get(PersonProfile,kid['id']) is not None
        assert db.session.get(WishlistItem,item['id']) is not None
        assert db.session.get(WishlistItem,private['id']) is None
        assert db.session.get(WishlistLetter,letter['id']).created_by_id==a['id']
    assert mutate(adult,'PATCH',f"/api/profiles/{kid['id']}",dict(favorite_colors=['Pink'])).status_code==200
    assert mutate(outsider,'PATCH',f"/api/profiles/{kid['id']}",dict(favorite_colors=['Blue'])).status_code==404
    assert mutate(adult,'POST','/api/household-session/pin',dict(pin='654321',password='a-long-test-password')).status_code==200
    assert mutate(adult,'POST','/api/household-session/switch',dict(profile_id=kid['id'])).status_code==200
    assert adult.get('/api/child/me').json['letters'][0]['id']==letter['id']


def test_no_eligible_successor_deletes_owned_family_but_not_other_adult_account(app):
    owner,adult,_,home,partner,kid,o,a=joined_family(app)
    assert mutate(owner,'DELETE',f"/api/households/{home['id']}/profiles/{partner['id']}/member").status_code==200
    preview=owner.get('/api/auth/account-deletion').json
    assert preview['families'][0]['action']=='delete'
    assert preview['families'][0]['successor'] is None
    assert confirm(owner,preview).status_code==200
    with app.app_context():
        assert db.session.get(Household,home['id']) is None
        assert db.session.get(PersonProfile,kid['id']) is None
        assert db.session.get(User,a['id']) is not None
        assert db.session.get(PersonProfile,partner['id']).account_user_id==a['id']


def test_preview_and_current_password_and_unchanged_succession_are_required(app):
    owner,adult,_,home,partner,kid,o,a=joined_family(app)
    assert mutate(owner,'DELETE','/api/auth/account',dict(password='a-long-test-password',confirm=True)).status_code==409
    preview=owner.get('/api/auth/account-deletion').json
    assert confirm(owner,preview,password='wrong-password').status_code==403
    assert mutate(owner,'DELETE',f"/api/households/{home['id']}/profiles/{partner['id']}/member").status_code==200
    response=confirm(owner,preview)
    assert response.status_code==409,response.json
    with app.app_context():
        assert db.session.get(User,o['id']) is not None
        assert db.session.get(Household,home['id']).owner_id==o['id']


def test_joined_adult_deletion_does_not_delete_owners_family(app):
    owner,adult,_,home,partner,kid,o,a=joined_family(app)
    preview=adult.get('/api/auth/account-deletion').json
    assert preview['families']==[]
    assert confirm(adult,preview).status_code==200
    with app.app_context():
        assert db.session.get(User,a['id']) is None
        assert db.session.get(Household,home['id']).owner_id==o['id']
        assert db.session.get(PersonProfile,kid['id']) is not None
        assert db.session.get(PersonProfile,partner['id']) is None


def test_pending_invitation_or_shopper_cannot_inherit_family(app):
    from backend.app.models import HouseholdInvitation
    owner=app.test_client();shopper=app.test_client()
    o=register(owner,'Owner','delete-owner@example.com')
    s=register(shopper,'Shopper','delete-shopper@example.com')
    home=mutate(owner,'POST','/api/households',dict(name='Family',profiles=[dict(display_name='Pending',relationship='parent')])).json['household']
    profile=owner.get(f"/api/households/{home['id']}").json['profiles'][0]
    with app.app_context():
        db.session.add(HouseholdMembership(household_id=home['id'],user_id=s['id'],role='shopper',share_all_profiles=True))
        db.session.get(PersonProfile,profile['id']).account_user_id=s['id']
        db.session.commit()
    preview=owner.get('/api/auth/account-deletion').json
    assert preview['families'][0]['successor'] is None


def test_no_successor_deletes_owned_child_access_and_unshared_wishes(app):
    owner,adult,_,home,partner,kid,o,a=joined_family(app)
    child=mutate(owner,'POST',f"/api/households/{home['id']}/child-accounts",dict(profile_id=kid['id'],password='child-test-password')).json['child']
    kid_list=owner.get(f"/api/profiles/{kid['id']}/wishlists").json['wishlists'][0]['id']
    item=mutate(owner,'POST',f'/api/wishlists/{kid_list}/items',dict(name='Family-only wish')).json['item']
    mutate(owner,'DELETE',f"/api/households/{home['id']}/profiles/{partner['id']}/member")
    preview=owner.get('/api/auth/account-deletion').json
    assert preview['children'][0]['successor_id'] is None
    assert confirm(owner,preview).status_code==200
    with app.app_context():
        assert db.session.get(User,child['id']) is None
        assert db.session.get(PersonProfile,kid['id']) is None
        assert db.session.get(WishlistItem,item['id']) is None
        assert db.session.get(User,a['id']) is not None


def test_account_deletion_cleans_up_private_holds_and_cannot_be_replayed(app):
    owner,adult,_,home,partner,kid,o,a=joined_family(app)
    kid_list=owner.get(f"/api/profiles/{kid['id']}/wishlists").json['wishlists'][0]['id']
    item=mutate(owner,'POST',f'/api/wishlists/{kid_list}/items',dict(name='Retained gift')).json['item']
    with app.app_context():
        db.session.add(GiftReservation(item_id=item['id'],shopper_id=o['id'],quantity=1,status='reserved'))
        db.session.add(PrivateGift(user_id=o['id'],name='Private plan',recipient='Friend'))
        db.session.commit()
    preview=owner.get('/api/auth/account-deletion').json
    assert confirm(owner,preview).status_code==200
    with app.app_context():
        assert GiftReservation.query.filter_by(shopper_id=o['id']).count()==0
        assert PrivateGift.query.filter_by(user_id=o['id']).count()==0
        assert db.session.get(WishlistItem,item['id']) is not None
    assert confirm(owner,preview).status_code==401


def test_expired_preview_or_missing_confirmation_cannot_delete_account(app):
    owner,_,_,home,_,_,o,_=joined_family(app)
    preview=owner.get('/api/auth/account-deletion').json
    assert mutate(owner,'DELETE','/api/auth/account',dict(confirmation_token=preview['confirmation_token'],password='a-long-test-password',confirm=False)).status_code==409
    with owner.session_transaction() as state:
        state['account_deletion_preview']={**state['account_deletion_preview'],'expires':0}
    assert confirm(owner,preview).status_code==409
    with app.app_context():
        assert db.session.get(User,o['id']) is not None
        assert db.session.get(Household,home['id']).owner_id==o['id']


def test_full_family_cascade_removes_pets_saved_gifts_related_records_and_uploads(app):
    from pathlib import Path
    from datetime import datetime,timedelta,timezone
    from backend.app.models import (SavedGift,CoBuyInvitation,Notification,Occasion,WishlistItemWishlist,
        WishlistItemOccasion,ChildWishlistAccess,PersonalWish,PersonalWishViewer,FamilyFollow,ShoppingBudget,
        GiftSuggestion,GiftAvailabilityAlert,GiftExchangeGame,PasswordReset,AccountEmailCode,SupportTicket,
        SupportTicketMessage,HelpChatMessage,HouseholdInvitation,HouseholdMemberProfileAccess)
    owner,outsider=app.test_client(),app.test_client()
    o=register(owner,'Owner','cascade-owner@example.com')
    other=register(outsider,'Other account','cascade-other@example.com')
    home=mutate(owner,'POST','/api/households',dict(name='Delete this family',self_profile_index='new',profiles=[dict(display_name='Child'),dict(display_name='Pretzel',profile_type='pet')])).json['household']
    profiles=owner.get(f"/api/households/{home['id']}").json['profiles']
    kid=next(p for p in profiles if p['display_name']=='Child')
    pet=next(p for p in profiles if p['profile_type']=='pet')
    child=mutate(owner,'POST',f"/api/households/{home['id']}/child-accounts",dict(profile_id=kid['id'],password='child-test-password')).json['child']
    pet_list=owner.get(f"/api/profiles/{pet['id']}/wishlists").json['wishlists'][0]['id']
    gift=mutate(owner,'POST',f'/api/wishlists/{pet_list}/items',dict(name='Pet toy')).json['item']
    personal=mutate(owner,'POST','/api/personal-wishes',dict(name='Personal wish',visibility='private',viewer_ids=[])).json['wish']['item']
    letter=mutate(owner,'POST',f"/api/households/{home['id']}/wishlist-letters",dict(title='Magic wishes',sender_name='Santa',send_on='2020-01-01',profile_ids=[kid['id']]))
    assert letter.status_code==201
    now=datetime.now(timezone.utc)
    with app.app_context():
        root=Path(app.config['UPLOAD_FOLDER']);root.mkdir(parents=True,exist_ok=True)
        paths={key:'/api/uploads/'+key+'.png' for key in ['pet-photo','family-photo','gift-image','personal-image','private-image','child-theme']}
        for path in paths.values():(root/Path(path).name).write_bytes(b'test-image')
        db.session.get(PersonProfile,pet['id']).photo_path=paths['pet-photo']
        db.session.get(Household,home['id']).photo_path=paths['family-photo']
        db.session.get(WishlistItem,gift['id']).image_path=paths['gift-image']
        db.session.get(WishlistItem,personal['id']).image_path=paths['personal-image']
        db.session.get(User,child['id']).theme_image_path=paths['child-theme']
        db.session.add_all([SavedGift(user_id=o['id'],item_id=gift['id']),SavedGift(user_id=other['id'],item_id=gift['id']),
            PrivateGift(user_id=o['id'],name='Saved plan',recipient='Friend',image_url=paths['private-image']),
            Notification(user_id=o['id'],household_id=home['id'],item_id=gift['id'],message='An update'),
            FamilyFollow(follower_id=o['id'],followed_id=other['id']),FamilyFollow(follower_id=other['id'],followed_id=o['id']),
            ShoppingBudget(user_id=o['id'],household_id=home['id'],profile_id=pet['id'],amount=25),
            GiftAvailabilityAlert(user_id=o['id'],item_id=gift['id']),
            GiftSuggestion(sender_id=other['id'],recipient_id=o['id'],profile_id=kid['id'],data={'name':'A wish'}),
            GiftExchangeGame(household_id=home['id'],created_by_id=o['id'],kind='secret_santa',title='Family game',state={}),
            PasswordReset(user_id=o['id'],token_hash='a'*64,expires_at=now+timedelta(days=1),password_version=0),
            AccountEmailCode(id='b'*64,user_id=o['id'],purpose='password',code_hash='hash',expires_at=now+timedelta(days=1),session_version=0),
            HelpChatMessage(user_id=o['id'],sender='user',message='Help please')])
        reservation=GiftReservation(item_id=gift['id'],shopper_id=other['id'],quantity=1)
        ticket=SupportTicket(user_id=o['id'],subject='Help',description='Question')
        db.session.add_all([reservation,ticket]);db.session.flush()
        db.session.add(CoBuyInvitation(reservation_id=reservation.id,email='co@example.com',share_percent=50))
        db.session.add(SupportTicketMessage(ticket_id=ticket.id,author_id=other['id'],message='A reply'))
        db.session.commit()
    preview=owner.get('/api/auth/account-deletion').json
    assert preview['families'][0]['pets']==1 and preview['families'][0]['action']=='delete'
    assert confirm(owner,preview).status_code==200
    with app.app_context():
        for model in [Household,PersonProfile,Wishlist,WishlistItem,WishlistItemWishlist,WishlistItemOccasion,
            Occasion,HouseholdProfileAccess,HouseholdMembership,HouseholdMemberProfileAccess,HouseholdInvitation,
            ChildWishlistAccess,PersonalWish,PersonalWishViewer,SavedGift,PrivateGift,GiftReservation,CoBuyInvitation,
            Notification,FamilyFollow,ShoppingBudget,GiftSuggestion,GiftAvailabilityAlert,GiftExchangeGame,
            WishlistLetter,PasswordReset,AccountEmailCode,SupportTicket,SupportTicketMessage,HelpChatMessage]:
            assert model.query.count()==0,model.__name__
        assert db.session.get(User,o['id']) is None
        assert db.session.get(User,child['id']) is None
        assert db.session.get(User,other['id']) is not None
        for path in paths.values():assert not (root/Path(path).name).exists(),path
