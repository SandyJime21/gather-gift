from backend.tests.test_reservation_privacy import register, mutate
from backend.app.extensions import db
from backend.app.models import HouseholdMembership, HouseholdProfileAccess, User


def setup_family(app):
    owner, spouse, relative, outsider = [app.test_client() for _ in range(4)]
    users = [register(client, name, name + '@personal.example.com') for client, name in zip(
        [owner, spouse, relative, outsider], ['owner', 'spouse', 'relative', 'outsider'])]
    home = mutate(owner, 'POST', '/api/households', {'name': 'Our family'}).json['household']
    with app.app_context():
        db.session.add(HouseholdMembership(household_id=home['id'], user_id=users[1]['id'], role='shopper'))
        db.session.add(HouseholdMembership(household_id=home['id'], user_id=users[2]['id'], role='admin'))
        db.session.commit()
    return owner, spouse, relative, outsider, users, home


def test_personal_wishes_are_private_and_only_selected_family_can_shop(app):
    owner, spouse, relative, outsider, users, home = setup_family(app)
    created = mutate(owner, 'POST', '/api/personal-wishes', {'name': 'Jewelry', 'product_url': 'https://example.com/jewelry', 'viewer_ids': []})
    assert created.status_code == 201, created.json
    wish_id = created.json['wish']['id']
    item_id = created.json['wish']['item']['id']
    assert created.json['wish']['item']['availability']['available'] == 1
    assert spouse.get('/api/personal-wishes').json['shared'] == []
    assert relative.get('/api/shopping').json['items'] == []
    assert mutate(relative, 'POST', f'/api/items/{item_id}/reservations', {}).status_code == 404
    assert mutate(owner, 'PATCH', f'/api/personal-wishes/{wish_id}', {'viewer_ids': [users[1]['id']]}).status_code == 200
    shared = spouse.get('/api/personal-wishes').json['shared']
    assert [row['item']['name'] for row in shared] == ['Jewelry']
    assert spouse.get('/api/shopping').json['items'][0]['id'] == item_id
    assert relative.get('/api/personal-wishes').json['shared'] == []
    assert relative.get('/api/shopping').json['items'] == []
    assert outsider.get('/api/personal-wishes').json['shared'] == []
    assert mutate(outsider, 'PATCH', f'/api/personal-wishes/{wish_id}', {'name': 'Changed'}).status_code == 404
    assert mutate(owner, 'PATCH', f'/api/personal-wishes/{wish_id}', {'viewer_ids': [users[3]['id']]}).status_code == 400
    assert mutate(spouse, 'PUT', f'/api/items/{item_id}/heart').status_code == 200
    held = mutate(spouse, 'POST', f'/api/items/{item_id}/reservations', {}).json['reservation']
    assert mutate(spouse, 'PATCH', f"/api/reservations/{held['id']}", {'status': 'purchased'}).status_code == 200
    mine = owner.get('/api/personal-wishes').json['mine'][0]
    assert mine['item']['availability']['purchased'] == 1
    assert 'purchased_by' not in mine['item']['availability']
    assert owner.get('/api/my-shopping').json['reservations'] == []
    assert owner.get('/api/notifications').json['notifications'] == []
    assert mutate(relative, 'DELETE', f'/api/personal-wishes/{wish_id}').status_code == 404
    assert mutate(owner, 'DELETE', f'/api/personal-wishes/{wish_id}').status_code == 200
    assert spouse.get('/api/personal-wishes').json['shared'] == []
    assert spouse.get('/api/wishlist').json['hearted'] == []


def test_new_personal_wish_defaults_to_invited_family_visibility(app):
    owner, spouse, relative, outsider, users, _ = setup_family(app)
    created = mutate(owner, 'POST', '/api/personal-wishes', {
        'name': 'A birthday book',
        'product_url': 'https://example.com/book',
    })
    assert created.status_code == 201, created.json
    wish_id = created.json['wish']['id']
    item_id = created.json['wish']['item']['id']

    assert set(created.json['wish']['viewer_ids']) == {users[1]['id'], users[2]['id']}
    assert [row['item']['id'] for row in spouse.get('/api/personal-wishes').json['shared']] == [item_id]
    assert [row['item']['id'] for row in relative.get('/api/personal-wishes').json['shared']] == [item_id]
    assert outsider.get('/api/personal-wishes').json['shared'] == []
    assert mutate(owner, 'PATCH', f'/api/personal-wishes/{wish_id}', {'viewer_ids': []}).status_code == 200
    assert spouse.get('/api/personal-wishes').json['shared'] == []


def test_unsharing_or_removing_family_members_stops_access(app):
    owner, spouse, relative, _, users, home = setup_family(app)
    wish = mutate(owner, 'POST', '/api/personal-wishes', {'name': 'A necklace', 'viewer_ids': [users[1]['id']]}).json['wish']
    item_id = wish['item']['id']
    assert mutate(spouse, 'POST', f'/api/items/{item_id}/reservations', {}).status_code == 201
    assert mutate(owner, 'PATCH', f"/api/personal-wishes/{wish['id']}", {'viewer_ids': [users[2]['id']]}).status_code == 200
    assert spouse.get('/api/personal-wishes').json['shared'] == []
    assert spouse.get('/api/my-shopping').json['reservations'] == []
    assert mutate(relative, 'POST', f'/api/items/{item_id}/reservations', {}).status_code == 201
    assert mutate(owner, 'DELETE', f"/api/households/{home['id']}/members/{users[2]['id']}").status_code == 200
    assert relative.get('/api/personal-wishes').json['shared'] == []
    assert mutate(relative, 'PUT', f'/api/items/{item_id}/heart').status_code == 404


def test_family_shopper_can_share_back_with_household_owner(app):
    owner, spouse, _, _, users, _ = setup_family(app)
    audience = spouse.get('/api/personal-wishes').json['audience']
    assert users[0]['id'] in {person['id'] for person in audience}
    wish = mutate(spouse, 'POST', '/api/personal-wishes', {'name': 'Favorite book', 'viewer_ids': [users[0]['id']]}).json['wish']
    assert owner.get('/api/personal-wishes').json['shared'][0]['item']['id'] == wish['item']['id']

def test_personal_wish_occasion_remains_private_and_can_change(app):
    owner, spouse, _, _, _, _ = setup_family(app)
    response = mutate(owner, 'POST', '/api/personal-wishes', {'name':'Jewelry','occasion':'Anniversary','viewer_ids':[]})
    assert response.status_code == 201
    wish = response.json['wish']
    assert wish['occasion'] == 'Anniversary'
    assert spouse.get('/api/personal-wishes').json['shared'] == []
    assert mutate(owner,'PATCH',f"/api/personal-wishes/{wish['id']}",{'occasion':'Birthday'}).status_code == 200
    assert owner.get('/api/personal-wishes').json['mine'][0]['occasion'] == 'Birthday'

def test_explicit_audiences_and_public_preview_never_publish_private_wishes(app):
    from backend.app.models import FamilyFollow, GiftReservation
    owner, spouse, relative, outsider, users, _ = setup_family(app)
    public = mutate(owner,'POST','/api/personal-wishes',{'name':'Public book','visibility':'public','viewer_ids':[],'product_url':'https://example.com/book'}).json['wish']
    private = mutate(owner,'POST','/api/personal-wishes',{'name':'Private jewelry','visibility':'private','viewer_ids':[users[1]['id']]}).json['wish']
    assert [w['name'] for w in app.test_client().get('/api/public/wishes').json['wishes']] == ['Public book']
    assert 'email' not in app.test_client().get('/api/public/wishes').get_data(as_text=True)
    assert [w['id'] for w in outsider.get('/api/personal-wishes').json['shared']] == [public['id']]
    assert private['id'] not in [w['id'] for w in spouse.get('/api/personal-wishes').json['shared']]
    hold=mutate(outsider,'POST',f"/api/items/{public['item']['id']}/reservations",{}).json['reservation']
    assert mutate(owner,'PATCH',f"/api/personal-wishes/{public['id']}",{'visibility':'private'}).status_code==200
    assert app.test_client().get('/api/public/wishes').json['wishes']==[]
    with app.app_context():
        assert db.session.get(GiftReservation,hold['id']).status=='cancelled'
        db.session.add(FamilyFollow(follower_id=users[3]['id'],followed_id=users[0]['id']));db.session.commit()
    follow=mutate(owner,'POST','/api/personal-wishes',{'name':'Followers book','visibility':'followers','viewer_ids':[]}).json['wish']
    family=mutate(owner,'POST','/api/personal-wishes',{'name':'Family book','visibility':'family','viewer_ids':[]}).json['wish']
    assert [w['id'] for w in outsider.get('/api/personal-wishes').json['shared']]==[follow['id']]
    assert spouse.get('/api/personal-wishes').json['shared']==[]
    assert [w['id'] for w in relative.get('/api/personal-wishes').json['shared']]==[family['id']]

def test_list_rename_requires_edit_permission_and_keeps_child_add_only(app):
    from backend.tests.test_child_access import child_setup
    parent, child, stranger, _, _, lists, _, _ = child_setup(app)
    path=f"/api/wishlists/{lists[0]['id']}"
    assert mutate(stranger,'PATCH',path,{'title':'Changed'}).status_code==404
    assert mutate(child,'PATCH',path,{'title':'Changed'}).status_code==403
    assert mutate(parent,'PATCH',path,{'title':''}).status_code==400
    result=mutate(parent,'PATCH',path,{'title':'Holiday wishes'})
    assert result.status_code==200
    assert result.json['wishlist']['title']=='Holiday wishes'


def test_private_personal_wish_stays_private_when_its_profile_is_also_in_a_family(app):
    owner, spouse, relative, outsider, users, home = setup_family(app)
    created = mutate(owner, 'POST', '/api/personal-wishes', {'name':'Private surprise', 'visibility':'private', 'viewer_ids':[]}).json['wish']
    profile_id = created['item']['profile_id']
    with app.app_context():
        if not HouseholdProfileAccess.query.filter_by(household_id=home['id'],profile_id=profile_id).first():
            db.session.add(HouseholdProfileAccess(household_id=home['id'],profile_id=profile_id))
            db.session.commit()
    lists = owner.get(f'/api/profiles/{profile_id}/wishlists').json['wishlists']
    for wishlist in lists:
        response = relative.get(f"/api/wishlists/{wishlist['id']}/items")
        assert response.status_code == 200
        assert all(row['id'] != created['item']['id'] for row in response.json['items'])
    assert all(row['id'] != created['item']['id'] for row in relative.get('/api/shopping').json['items'])
    assert mutate(relative,'POST',f"/api/items/{created['item']['id']}/reservations",{}).status_code == 404
    assert owner.get('/api/personal-wishes').json['mine'][0]['item']['id'] == created['item']['id']
