from backend.tests.test_reservation_privacy import register, mutate
from backend.app.models import PersonProfile
from backend.app.extensions import db


def test_household_setup_identifies_the_creator_as_an_adult(app):
    owner=app.test_client()
    register(owner,'Alex','alex-owner@example.com')
    result=mutate(owner,'POST','/api/households',{'name':'Family','profiles':[{'display_name':'Alex'},{'display_name':'Child'}],'self_profile_index':0})
    assert result.status_code==201
    own_id=result.json['self_profile_id']
    own=owner.get(f'/api/profiles/{own_id}').json['profile']
    assert own['is_you'] and own['is_adult'] and own['is_guardian']
    assert owner.get('/api/auth/me').json['user']['active_member_profile_id']==own_id
    mutate(owner,'POST','/api/auth/logout')
    assert mutate(owner,'POST','/api/auth/login',{'email':'alex-owner@example.com','password':'a-long-test-password'}).status_code==200
    assert owner.get('/api/auth/me').json['user']['active_member_profile_id']==own_id


def test_existing_household_can_identify_owner_but_not_take_child_account(app):
    from backend.tests.test_child_access import child_setup
    owner,child,stranger,home,profiles,lists,path,account=child_setup(app)
    endpoint=f"/api/households/{home['id']}/identify-me"
    assert mutate(owner,'POST',endpoint,{'profile_id':profiles[0]['id']}).status_code==409
    assert mutate(stranger,'POST',endpoint,{'profile_id':profiles[1]['id']}).status_code==403
    assert mutate(child,'POST',endpoint,{'profile_id':profiles[1]['id']}).status_code==403
    assert mutate(owner,'POST',endpoint,{'profile_id':profiles[1]['id']}).status_code==200
    assert owner.get(f"/api/profiles/{profiles[1]['id']}").json['profile']['is_you']


def test_setup_can_add_creator_without_claiming_a_family_member(app):
    owner=app.test_client()
    register(owner,'Creator','creator@example.com')
    result=mutate(owner,'POST','/api/households',{'name':'Family','profiles':[{'display_name':'Child'}],'self_profile_index':'new'})
    assert result.status_code==201
    own=owner.get(f"/api/profiles/{result.json['self_profile_id']}").json['profile']
    assert own['display_name']=='Creator' and own['is_adult']
