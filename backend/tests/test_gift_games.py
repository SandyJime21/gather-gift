from backend.tests.test_reservation_privacy import register, mutate
from backend.tests.test_child_access import child_setup


def setup_game(app,kind='secret_santa'):
    owner, outsider=app.test_client(),app.test_client()
    register(owner,'Host','games-host@example.com')
    register(outsider,'Outside','games-outside@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Party family','profiles':[{'display_name':'Alex'},{'display_name':'Blair'},{'display_name':'Casey'}]}).json['household']
    people=owner.get(f"/api/households/{home['id']}").json['profiles']
    ids=[person['id'] for person in people]
    for pid in ids:
        assert mutate(owner,'PATCH',f'/api/profiles/{pid}',{'is_adult':True}).status_code==200
    created=mutate(owner,'POST','/api/games',{'household_id':home['id'],'title':'Holiday exchange','kind':kind,'participants':ids,'max_steals':1,'budget':'25'})
    assert created.status_code==201,created.json
    return owner,outsider,created.json['game'],ids


def action(client,game,path,**body):
    return mutate(client,'POST',f"/api/games/{game['id']}/{path}",{'version':game['version'],**body})


def test_secret_draw_has_no_self_assignments_and_only_reveals_selected_profile(app):
    owner,outsider,game,ids=setup_game(app)
    response=action(owner,game,'start')
    assert response.status_code==200
    game=response.json['game']
    assert game['status']=='drawn'
    assert 'assignments' not in owner.get(f"/api/games/{game['id']}").get_data(as_text=True)
    assert mutate(owner,'POST',f"/api/games/{game['id']}/assignment",{}).status_code==403
    recipients=[]
    for pid in ids:
        assert mutate(owner,'POST','/api/household-session/switch',{'profile_id':pid}).status_code==200
        result=mutate(owner,'POST',f"/api/games/{game['id']}/assignment",{})
        assert result.status_code==200
        recipient=result.json['recipient']['id']
        assert recipient!=pid
        recipients.append(recipient)
        other=next(value for value in ids if value!=pid)
        assert mutate(owner,'POST',f"/api/games/{game['id']}/assignment",{'profile_id':other}).status_code==403
    assert set(recipients)==set(ids)
    assert action(owner,game,'start').status_code==409
    assert outsider.get(f"/api/games/{game['id']}").status_code==404
    assert outsider.get('/api/games').json=={'games':[]}
    assert mutate(outsider,'POST',f"/api/games/{game['id']}/assignment",{}).status_code==404


def test_white_elephant_hides_gifts_and_enforces_turns_steals_and_versions(app,monkeypatch):
    class FixedRandom:
        def shuffle(self,values):
            pass
    monkeypatch.setattr('backend.app.gift_games.secrets.SystemRandom',FixedRandom)
    owner,outsider,game,ids=setup_game(app,'white_elephant')
    assert action(owner,game,'start').status_code==409
    for index,pid in enumerate(ids):
        response=action(owner,game,'gifts',profile_id=pid,name=f'Secret toy {index}',product_url=f'https://example.com/toy/{index}',image_url='https://example.com/toy.jpg')
        assert response.status_code==201,response.json
        game=response.json['game']
        assert all('name' not in gift and 'product_url' not in gift for gift in game['gifts'])
    assert action(owner,game,'gifts',profile_id=ids[0],name='Duplicate',product_url='https://example.com/duplicate').status_code==409
    game=action(owner,game,'start').json['game']
    assert game['current_player_id']==ids[0]
    gift_ids=[gift['id'] for gift in game['gifts']]
    stale=game
    game=action(owner,game,'turn',action='open',gift_id=gift_ids[0]).json['game']
    assert game['current_player_id']==ids[1]
    assert game['gifts'][0]['name']=='Secret toy 0'
    assert action(owner,stale,'turn',action='open',gift_id=gift_ids[1]).status_code==409
    game=action(owner,game,'turn',action='steal',gift_id=gift_ids[0]).json['game']
    assert game['current_player_id']==ids[0]
    assert game['gifts'][0]['holder_id']==ids[1]
    assert action(owner,game,'turn',action='steal',gift_id=gift_ids[0]).status_code==409
    game=action(owner,game,'turn',action='open',gift_id=gift_ids[1]).json['game']
    assert game['current_player_id']==ids[2]
    assert action(owner,game,'turn',action='steal',gift_id=gift_ids[0]).status_code==409
    game=action(owner,game,'turn',action='open',gift_id=gift_ids[2]).json['game']
    assert game['status']=='completed'
    assert {gift['holder_id'] for gift in game['gifts']}==set(ids)
    assert action(owner,game,'turn',action='open',gift_id=gift_ids[0]).status_code==409
    assert action(outsider,game,'cancel').status_code==404


def test_child_accounts_cannot_escape_into_games(app):
    parent,child,_,home,profiles,lists,path,account=child_setup(app)
    assert child.get('/api/games').status_code==403
    assert child.get('/api/games/options').status_code==403
    assert mutate(child,'POST','/api/games',{'household_id':home['id']}).status_code==403


def test_parent_can_reveal_for_child_without_a_child_login(app):
    owner=app.test_client()
    register(owner,'Parent','party-parent@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Family','profiles':[{'display_name':'Parent'},{'display_name':'Child'}]}).json['household']
    profiles=owner.get(f"/api/households/{home['id']}").json['profiles']
    parent_id,child_id=[person['id'] for person in profiles]
    assert mutate(owner,'PATCH',f'/api/profiles/{parent_id}',{'is_adult':True,'is_guardian':True}).status_code==200
    game=mutate(owner,'POST','/api/games',{'household_id':home['id'],'title':'Family Santa','kind':'secret_santa','participants':[parent_id,child_id]}).json['game']
    game=action(owner,game,'start').json['game']
    mutate(owner,'POST','/api/household-session/switch',{'profile_id':parent_id})
    result=mutate(owner,'POST',f"/api/games/{game['id']}/assignment",{'profile_id':child_id})
    assert result.status_code==200
    assert result.json['recipient']['id']==parent_id

def test_cross_family_selected_participants_can_see_and_leave_game(app, monkeypatch):
    emails=[]
    monkeypatch.setattr("backend.app.invitation_mail.send_game_invitation", lambda *args: emails.append(args) or True)
    host, stranger, original, ids = setup_game(app)
    guest = app.test_client()
    register(guest, 'Other parent', 'other-game-parent@example.com')
    home = mutate(guest, 'POST', '/api/households', {'name':'Other family','self_profile_index':0,'profiles':[{'display_name':'Other parent'},{'display_name':'Not shared'}]}).json['household']
    other_people = guest.get(f"/api/households/{home['id']}").json['profiles']
    from backend.app.extensions import db
    from backend.app.models import User, PersonProfile
    adult = db.session.get(PersonProfile, other_people[0]['id'])
    adult.account_user_id = User.query.filter_by(email='other-game-parent@example.com').one().id
    adult.is_adult = True
    db.session.commit()
    invite = mutate(host, 'POST', f"/api/households/{original['household_id']}/invitations", {'email':'other-game-parent@example.com','role':'shopper','profile_ids':[ids[0]]}).json['invitation']
    mutate(guest,'POST','/api/invitations/accept',{'token':invite['token']})
    host_id = guest.get('/api/family-connections').json['connections'][0]['user_id']
    assert mutate(guest,'POST',f'/api/family-connections/{host_id}/share',{'household_id':home['id'],'profile_ids':[other_people[0]['id']]}).status_code == 200
    options = host.get('/api/games/options').json['households']
    other_option = next(h for h in options if h['id'] == home['id'])
    assert [p['id'] for p in other_option['profiles']] == [other_people[0]['id']]
    payload = {'household_id':original['household_id'],'title':'Across families','kind':'secret_santa','participants':[ids[0],ids[1],other_people[0]['id']],'budget':'1.03'}
    assert mutate(host,'POST','/api/games',{**payload,'budget':'1.033333'}).status_code == 400
    assert mutate(host,'POST','/api/games',{**payload,'participants':[ids[0],other_people[1]['id']]}).status_code == 400
    result = mutate(host,'POST','/api/games',payload)
    assert result.status_code == 201, result.json
    game = result.json['game']
    assert len(emails) == 1 and emails[0][0] == 'other-game-parent@example.com'
    assert mutate(guest, 'PATCH', '/api/notification-preferences', {'game_emails': False}).status_code == 200
    assert mutate(host, 'POST', '/api/games', payload).status_code == 201
    assert len(emails) == 1
    assert mutate(guest, 'PATCH', '/api/notification-preferences', {'game_emails': True}).status_code == 200
    assert game['budget'] == '1.03'
    assert game['id'] in [row['id'] for row in guest.get('/api/games').json['games']]
    assert stranger.get(f"/api/games/{game['id']}").status_code == 404
    assert action(host, game, 'start').status_code == 409
    assert game['id'] in [n.get('game_id') for n in guest.get('/api/notifications').json['notifications']]
    assert action(stranger, game, 'join', profile_id=other_people[0]['id']).status_code == 404
    game = action(guest, game, 'join', profile_id=other_people[0]['id']).json['game']
    assert game['id'] not in [n.get('game_id') for n in guest.get('/api/notifications').json['notifications']]
    game = action(host, game, 'start').json['game']
    assert action(guest,game,'leave',profile_id=ids[0]).status_code == 403
    response = action(guest,game,'leave',profile_id=other_people[0]['id'])
    assert response.status_code == 200
    assert response.json['game'] is None
    remaining = host.get(f"/api/games/{game['id']}").json['game']
    assert remaining['status'] == 'waiting'
    assert len(remaining['participants']) == 2
    assert guest.get(f"/api/games/{game['id']}").status_code == 404


def test_child_game_notifications_are_read_only_and_no_email(app, monkeypatch):
    parent, child, stranger, home, profiles, lists, path, account = child_setup(app)
    from backend.tests.test_child_controls import allow_optional_features
    allow_optional_features(app)
    emails=[]
    monkeypatch.setattr('backend.app.invitation_mail.send_game_invitation', lambda *args: emails.append(args) or True)
    response=mutate(parent,'POST','/api/games',{'household_id':home['id'],'title':'Kids exchange','kind':'secret_santa','participants':[p['id'] for p in profiles]})
    assert response.status_code==201, response.json
    game=response.json['game']
    notes=child.get('/api/child/game-notifications').json['notifications']
    assert notes==[{'id':game['id'],'message':'You are invited to Kids exchange. Ask your parent about joining.','read':False}]
    assert emails==[]
    assert mutate(child,'POST',f"/api/child/game-notifications/{game['id']}/read",{}).status_code==200
    assert child.get('/api/child/game-notifications').json['notifications'][0]['read'] is True
    assert mutate(child,'POST',f"/api/games/{game['id']}/join",{'profile_id':profiles[0]['id'],'version':game['version']}).status_code==403
    assert stranger.get('/api/child/game-notifications').status_code==403
    assert mutate(child,'POST','/api/child/game-notifications/999999/read',{}).status_code==404


def test_game_options_dedupe_accounts_across_profiles(app):
    from backend.app.extensions import db
    from backend.app.models import PersonProfile, HouseholdProfileAccess, User
    owner, outsider, game, ids=setup_game(app)
    user=User.query.filter_by(email='games-host@example.com').one()
    profile=db.session.get(PersonProfile,ids[0]); profile.account_user_id=user.id
    duplicate=PersonProfile(display_name='Same adult standalone',is_adult=True,account_user_id=user.id)
    db.session.add(duplicate);db.session.flush()
    db.session.add(HouseholdProfileAccess(household_id=game['household_id'],profile_id=duplicate.id));db.session.commit()
    options=owner.get('/api/games/options').json['households']
    selected=[p['id'] for h in options for p in h['profiles']]
    assert ids[0] in selected and duplicate.id not in selected
