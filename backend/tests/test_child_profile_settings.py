from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import mutate
from backend.app.extensions import db
from backend.app.models import User


def test_parent_sets_child_mode_without_child_password_and_selects_only_own_lists(app):
    parent,child,stranger,home,profiles,lists,_,_=child_setup(app)
    path=f"/api/profiles/{profiles[1]['id']}/child-controls"
    initial=parent.get(path).json
    assert initial['has_parent_pin'] is False and initial['enabled'] is False
    assert initial['wishlists']==[{'id':lists[1]['id'],'title':lists[1]['title']}]
    payload={'enabled':True,'wishlist_ids':[lists[1]['id']]}
    assert mutate(parent,'PATCH',path,payload).status_code==400
    assert mutate(parent,'POST','/api/household-session/pin',{'pin':'123456','password':'a-long-test-password'}).status_code==200
    assert mutate(parent,'PATCH',path,{**payload,'wishlist_ids':[lists[0]['id']]}).status_code==400
    assert mutate(stranger,'PATCH',path,payload).status_code==403
    assert mutate(child,'PATCH',path,payload).status_code==403
    response=mutate(parent,'PATCH',path,payload)
    assert response.status_code==200 and response.json['enabled'] is True
    assert mutate(parent,'POST','/api/household-session/switch',{'profile_id':profiles[1]['id']}).status_code==200
    assert [row['id'] for row in parent.get('/api/child/me').json['wishlists']]==[lists[1]['id']]
    with app.app_context():assert User.query.filter_by(is_child=True).count()==2


def test_revoked_letter_lists_cannot_be_viewed_or_written_and_disable_ends_access(app):
    parent,child,_,home,profiles,lists,_,account=child_setup(app)
    mutate(parent,'POST','/api/household-session/pin',{'pin':'123456','password':'a-long-test-password'})
    letter=mutate(parent,'POST',f"/api/households/{home['id']}/wishlist-letters",{'title':'Santa wishes','sender_name':'Santa','send_on':'2020-01-01','profile_ids':[profiles[0]['id']]}).json['letters'][0]
    assert letter['wishlist_id'] in [row['id'] for row in child.get('/api/child/me').json['wishlists']]
    path=f"/api/profiles/{profiles[0]['id']}/child-controls"
    response=mutate(parent,'PATCH',path,{'enabled':True,'wishlist_ids':[lists[0]['id']]})
    assert response.status_code==200
    assert child.get('/api/child/me').status_code==401

    mutate(child,'POST','/api/child/login',{'username':account['username'],'password':'child-test-password'})
    data=child.get('/api/child/me').json
    assert data['letters']==[]
    assert [row['id'] for row in data['wishlists']]==[lists[0]['id']]
    assert mutate(child,'POST',f"/api/child/wishlists/{letter['wishlist_id']}/items",{'name':'Hidden wish'}).status_code==404
    assert mutate(parent,'PATCH',path,{'enabled':False,'wishlist_ids':[]}).status_code==200
    assert child.get('/api/child/me').status_code==401



def test_company_profiles_do_not_gain_child_mode(app):
    parent,*_=child_setup(app)
    home=mutate(parent,'POST','/api/households',{'name':'Company','registry_type':'company','profiles':[{'display_name':'Employee'}]}).json['household']
    profile=parent.get(f"/api/households/{home['id']}").json['profiles'][0]
    path=f"/api/profiles/{profile['id']}/child-controls"
    assert parent.get(path).status_code==403
    assert mutate(parent,'PATCH',path,{'enabled':False}).status_code==403

