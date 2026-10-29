"""Household gift exchanges, private draws, and versioned party turns."""
import copy
import secrets
import time
from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, jsonify, request, session, current_app
from .api import authenticated, membership_for, profile_access, error, record_audit
from .extensions import db, limiter
from .models import GiftExchangeGame, HouseholdProfileAccess, HouseholdMembership, PersonProfile, User, Household, FamilyFollow
from .product_search import safe_product_url
from .affiliate_links import shopping_link

game_api = Blueprint('gift_games', __name__)


@game_api.before_request
def protect_games():
    user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
    if user and user.is_child:
        return error('Ask a parent to help with gift-exchange games.', 403)
    if request.method != 'GET':
        token = session.get('csrf_token')
        if not token or not secrets.compare_digest(token, request.headers.get('X-CSRF-Token', '')):
            return error('A valid CSRF token is required.', 400)
        if not isinstance(request.get_json(silent=True), dict):
            return error('JSON object required.', 400)


def organizer(game, user):
    member = membership_for(user, game.household_id)
    return bool(member and (member.role in ('owner','admin') or game.created_by_id==user.id and member.is_family_member))


def player_id(game, user):
    active = session.get('active_member_profile_id')
    if active in game.state['participants'] and profile_access(user, active):
        return active
    for profile_id in game.state['participants']:
        profile = db.session.get(PersonProfile, profile_id)
        if profile and profile.account_user_id == user.id:
            return profile_id
    return None


def managed_participants(game, user):
    return [pid for pid in game.state['participants'] if db.session.get(PersonProfile, pid) and (
        db.session.get(PersonProfile, pid).account_user_id == user.id or db.session.query(HouseholdProfileAccess).join(HouseholdMembership,
        HouseholdMembership.household_id == HouseholdProfileAccess.household_id).filter(HouseholdProfileAccess.profile_id == pid,
        HouseholdProfileAccess.can_edit.is_(True), HouseholdMembership.user_id == user.id,
        HouseholdMembership.role.in_(('owner', 'admin'))).first())]


def accessible(game, user):
    return game is not None and (organizer(game, user) or bool(managed_participants(game, user)))


def eligible_families(user):
    from .adult_family import followed_ids
    follows = followed_ids(user)
    homes = Household.query.join(HouseholdMembership).filter(HouseholdMembership.user_id == user.id, Household.registry_type == 'family').all()
    result = []
    for home in homes:
        member = membership_for(user, home.id)
        can_host = member.role in ('owner', 'admin') or member.is_family_member
        if not can_host and home.owner_id not in follows:
            continue
        profiles = PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id == home.id, PersonProfile.profile_type == 'person').all()
        result.append({'id': home.id, 'name': home.name, 'account_name': db.session.get(User, home.owner_id).name, 'can_host': can_host,
            'profiles': [{'id': p.id, 'name': p.display_name} for p in profiles if profile_access(user, p.id)]})
    included = {p['id'] for family in result for p in family['profiles']}
    individuals = PersonProfile.query.filter(PersonProfile.account_user_id.in_(follows), PersonProfile.profile_type == 'person').all() if follows else []
    for person in individuals:
        if person.id in included or HouseholdProfileAccess.query.filter_by(profile_id=person.id).first():
            continue
        account = db.session.get(User, person.account_user_id)
        if account and not account.is_child and not account.is_support:
            result.append({'id': -account.id, 'name': account.name, 'can_host': False, 'profiles': [{'id': person.id, 'name': person.display_name}]})
    # An adult may have an old standalone profile as well as their joined-family profile.
    preferred = {}
    for group in result:
        for person in group['profiles']:
            profile = db.session.get(PersonProfile, person['id'])
            key = ('account', profile.account_user_id) if profile.account_user_id else ('profile', profile.id)
            linked = HouseholdMembership.query.filter_by(household_id=group['id'], user_id=profile.account_user_id, is_family_member=True).first() if profile.account_user_id and group['id'] > 0 else None
            score = (bool(linked), group['id'] > 0, -profile.id)
            if key not in preferred or score > preferred[key][0]:
                preferred[key] = (score, group['id'], profile.id)
    for group in result:
        group['profiles'] = [person for person in group['profiles'] if any(home_id == group['id'] and pid == person['id'] for _, home_id, pid in preferred.values())]
    return [group for group in result if group['profiles'] or group['can_host']]


def people(game):
    result=[]
    for profile_id in game.state['participants']:
        profile=db.session.get(PersonProfile,profile_id)
        result.append({'id':profile_id,'name':profile.display_name if profile else 'Former family member', 'invitation_status':'invited' if profile_id in game.state.get('pending',[]) else 'joined'})
    return result


def assignment_profiles(game, user):
    choices=[]
    own=player_id(game,user)
    for pid in game.state['participants']:
        profile=db.session.get(PersonProfile,pid)
        child=db.session.get(User,profile.account_user_id) if profile and profile.account_user_id else None
        if pid==own or (profile and not profile.is_adult and pid in managed_participants(game,user) and profile_access(user,pid,write=True)):
            choices.append(pid)
    return choices


def game_dict(game, user):
    state=game.state
    gifts=[]
    active=player_id(game,user)
    for gift in state.get('gifts',[]):
        row={'id':gift['id'],'opened':gift.get('opened',False),'holder_id':gift.get('holder_id'), 'steals':gift.get('steals',0), 'is_yours':gift['contributor_id']==active}
        if row['opened']:
            row.update({key:gift.get(key) for key in ('name','image_url','store_name')})
            row['product_url']=shopping_link(gift.get('product_url'))
        gifts.append(row)
    return {'id':game.id,'household_id':game.household_id,'kind':game.kind,'title':game.title,
        'budget':format(game.budget, '.2f') if game.budget is not None else None,'event_date':game.event_date.isoformat() if game.event_date else None,
        'status':game.status,'version':game.version,'participants':people(game),'can_host':organizer(game,user), 'your_profile_id':active,
        'join_profiles':[pid for pid in managed_participants(game,user) if pid in state.get('pending',[])], 'leave_profiles':managed_participants(game,user), 'assignment_profiles':assignment_profiles(game,user),'gifts':gifts,'contributed_profile_ids':[gift['contributor_id'] for gift in state.get('gifts',[])],'order':state.get('order',[]),'current_player_id':state.get('current_player_id'),
        'max_steals':state.get('max_steals',2),'last_stolen_id':state.get('last_stolen_id'),
        'pending_email_invitations':sum(row['status']=='pending' and row['expires_at']>time.time() for row in state.get('email_invites',[])),
        'email_invitations':[{'email':row['email'],'status':row['status']} for row in state.get('email_invites',[]) if row['status']=='pending' and row['expires_at']>time.time()] if organizer(game,user) else []}


def locked_game(game_id):
    game=GiftExchangeGame.query.filter_by(id=game_id).with_for_update().first()
    if not accessible(game,request.current_user):
        return None,error('Game not found.',404)
    payload=request.get_json()
    if type(payload.get('version')) is not int or payload['version']!=game.version:
        return None,error('The game changed. Refresh before taking your turn.',409)
    return game,None


@game_api.get('/games/options')
@authenticated
def game_options():
    return jsonify(households=eligible_families(request.current_user))


@game_api.get('/games')
@authenticated
def list_games():
    user=request.current_user
    games=GiftExchangeGame.query.order_by(GiftExchangeGame.id.desc()).all()
    return jsonify(games=[game_dict(game,user) for game in games if accessible(game,user)])


@game_api.get('/games/<int:game_id>')
@authenticated
def get_game(game_id):
    game=db.session.get(GiftExchangeGame,game_id)
    if not accessible(game,request.current_user):
        return error('Game not found.',404)
    return jsonify(game=game_dict(game,request.current_user))


@game_api.post('/games')
@authenticated
@limiter.limit('10 per hour')
def create_game():
    payload=request.get_json()
    home_id=payload.get('household_id')
    if type(home_id) is not int:
        return error('Choose a family.',400)
    home=db.session.get(Household,home_id)
    member=membership_for(request.current_user,home_id)
    if not home or home.registry_type!='family' or not member or (member.role not in ('owner','admin') and not member.is_family_member):
        return error('Household owner or administrator required.',403)
    participants=payload.get('participants')
    if not isinstance(participants,list) or not (1 if payload.get('allow_draft') is True else 2)<=len(participants)<=50 or any(type(pid) is not int for pid in participants) or len(set(participants))!=len(participants):
        return error('Choose 2 to 50 different family members.',400)
    allowed={p['id'] for home in eligible_families(request.current_user) for p in home['profiles']}
    if not set(participants)<=allowed:
        return error('Choose people from your family or followed families whose profiles are shared with you.',400)
    title=payload.get('title','')
    kind=payload.get('kind')
    if not isinstance(title,str) or not title.strip() or len(title)>160 or kind not in ('secret_santa','white_elephant'):
        return error('Enter a game name and supported game type.',400)
    try:
        budget=Decimal(str(payload['budget'])) if payload.get('budget') not in ('',None) else None
        if budget is not None and (not budget.is_finite() or not 0<=budget<=99999999 or budget != budget.quantize(Decimal('0.01'))):
            raise ValueError()
        event_date=date.fromisoformat(payload['event_date']) if payload.get('event_date') else None
        max_steals=payload.get('max_steals',2)
        if type(max_steals) is not int or not 1<=max_steals<=5:
            raise ValueError()
    except (ValueError,TypeError,InvalidOperation):
        return error('Choose a valid budget, event date, and steal limit of 1-5.',400)
    game=GiftExchangeGame(household_id=home_id,created_by_id=request.current_user.id,kind=kind,title=title.strip(),budget=budget,event_date=event_date,
        state={'participants':participants,'gifts':[],'max_steals':max_steals})
    own = set(managed_participants(game, request.current_user))
    game.state = {**game.state, 'pending': [pid for pid in participants if pid not in own]}
    db.session.add(game);db.session.commit()
    from .invitation_mail import send_game_invitation
    recipients = {}
    for pid in participants:
        profile = db.session.get(PersonProfile, pid)
        account = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
        if account and not account.is_child and account.id != request.current_user.id and (account.notification_preferences or {}).get('game_emails', True):
            recipients.setdefault(account.id, []).append(profile.display_name)
    failed = 0
    for uid, names in recipients.items():
        account = db.session.get(User, uid)
        link = current_app.config['FRONTEND_ORIGIN'].rstrip('/') + '/following?tab=games&game=' + str(game.id)
        if not send_game_invitation(account.email, game.title, request.current_user.name, link, names):
            failed += 1
    return jsonify(game=game_dict(game,request.current_user), email_warning='Game created. Some invitation emails could not be delivered; in-app invitations are available.' if failed else None),201


@game_api.post('/games/<int:game_id>/gifts')
@authenticated
def add_wrapped_gift(game_id):
    game,failure=locked_game(game_id)
    if failure:return failure
    if game.kind!='white_elephant' or game.status!='waiting':
        return error('Gifts can only be added before White Elephant starts.',409)
    payload=request.get_json()
    contributor=payload.get('profile_id')
    if type(contributor) is not int or contributor not in game.state['participants'] or (not organizer(game,request.current_user) and contributor!=player_id(game,request.current_user)):
        return error('Choose your participating profile.',403)
    if contributor in game.state.get('pending',[]):
        return error('Join the game before adding a gift.',403)
    name=payload.get('name')
    link=safe_product_url(payload.get('product_url'))
    image=safe_product_url(payload.get('image_url'))
    if not isinstance(name,str) or not name.strip() or len(name)>200 or not link:
        return error('Search for a gift or paste a product link first.',400)
    state=copy.deepcopy(game.state)
    if any(gift['contributor_id']==contributor for gift in state['gifts']):
        return error('This person already has a wrapped gift in the game.',409)
    state['gifts'].append({'id':secrets.token_hex(8),'contributor_id':contributor,'name':name.strip(),'product_url':link,'image_url':image,'store_name':str(payload.get('store_name',''))[:120],'opened':False,'holder_id':None,'steals':0})
    game.state=state;game.version+=1;db.session.commit()
    return jsonify(game=game_dict(game,request.current_user)),201


@game_api.post('/games/<int:game_id>/start')
@authenticated
def start_game(game_id):
    game,failure=locked_game(game_id)
    if failure:return failure
    if not organizer(game,request.current_user):return error('Only the organizer can start this game.',403)
    if game.status!='waiting':return error('This game has already started.',409)
    state=copy.deepcopy(game.state)
    if state.get('pending') or any(row['status']=='pending' and row['expires_at']>time.time() for row in state.get('email_invites',[])):
        return error('Wait for invited participants to join or leave before starting.',409)
    if any(db.session.get(PersonProfile,pid) is None for pid in state['participants']):
        return error('A participant is no longer available. Create a new game.',409)
    if len(state['participants']) < 2:
        return error('At least two participants are required.', 409)
    order=list(state['participants']);secrets.SystemRandom().shuffle(order)
    if game.kind=='secret_santa':
        state['assignments']={str(profile_id):order[(index+1)%len(order)] for index,profile_id in enumerate(order)}
        game.status='drawn'
    else:
        if len(state['gifts'])!=len(order):return error('Each participant needs one wrapped gift before starting.',409)
        state.update(order=order,current_player_id=order[0],next_index=1,last_stolen_id=None)
        game.status='active'
    game.state=state;game.version+=1
    record_audit(request.current_user.id,'gift_game.started','gift_exchange_game',game.id,game.household_id)
    db.session.commit()
    return jsonify(game=game_dict(game,request.current_user))


@game_api.post('/games/<int:game_id>/assignment')
@authenticated
@limiter.limit('30 per minute')
def my_assignment(game_id):
    game=db.session.get(GiftExchangeGame,game_id)
    if not accessible(game,request.current_user):return error('Game not found.',404)
    if game.kind!='secret_santa' or game.status!='drawn':return error('The organizer has not drawn names yet.',409)
    profile_id=(request.get_json() or {}).get('profile_id',player_id(game,request.current_user))
    if profile_id not in assignment_profiles(game,request.current_user):return error('Switch Browsing as to your participating adult profile first.',403)
    recipient_id=game.state['assignments'].get(str(profile_id))
    recipient=db.session.get(PersonProfile,recipient_id) if recipient_id else None
    if not recipient:return error('Your recipient is no longer available. Contact the organizer.',409)
    return jsonify(recipient={'id':recipient.id,'name':recipient.display_name,'can_view_wishes':bool(profile_access(request.current_user,recipient.id))},profile_id=profile_id)


@game_api.post('/games/<int:game_id>/turn')
@authenticated
def take_turn(game_id):
    game,failure=locked_game(game_id)
    if failure:return failure
    if game.kind!='white_elephant' or game.status!='active':return error('This game is not accepting turns.',409)
    state=copy.deepcopy(game.state);current=state['current_player_id']
    if not organizer(game,request.current_user) and player_id(game,request.current_user)!=current:
        return error("It is another player's turn.",403)
    payload=request.get_json();gift=next((row for row in state['gifts'] if row['id']==payload.get('gift_id')),None)
    if not gift:return error('Gift not found.',404)
    action=payload.get('action')
    if action=='open' and not gift['opened']:
        gift['opened']=True;gift['holder_id']=current;state['last_stolen_id']=None
        next_index=state['next_index']
        if next_index>=len(state['order']):
            game.status='completed';state['current_player_id']=None
        else:
            state['current_player_id']=state['order'][next_index];state['next_index']=next_index+1
    elif action=='steal' and gift['opened'] and gift['holder_id']!=current and gift['steals']<state['max_steals'] and gift['id']!=state.get('last_stolen_id'):
        previous=gift['holder_id'];gift['holder_id']=current;gift['steals']+=1;state['current_player_id']=previous;state['last_stolen_id']=gift['id']
    else:return error('That move is not allowed. Open a wrapped gift or choose an eligible gift to steal.',409)
    game.state=state;game.version+=1;db.session.commit()
    return jsonify(game=game_dict(game,request.current_user))


@game_api.post('/games/<int:game_id>/cancel')
@authenticated
def cancel_game(game_id):
    game,failure=locked_game(game_id)
    if failure:return failure
    if not organizer(game,request.current_user):return error('Only the organizer can cancel.',403)
    if game.status in ('cancelled','completed'):return error('This game has ended.',409)
    game.status='cancelled';game.version+=1;db.session.commit()
    return jsonify(game=game_dict(game,request.current_user))


@game_api.post('/games/<int:game_id>/leave')
@authenticated
def leave_game(game_id):
    game, failure = locked_game(game_id)
    if failure:
        return failure
    pid = request.get_json().get('profile_id', player_id(game, request.current_user))
    if type(pid) is not int or pid not in managed_participants(game, request.current_user):
        return error('Choose your own family participant to remove.', 403)
    if game.status in ('completed', 'cancelled'):
        return error('This exchange has already ended.', 409)
    state = copy.deepcopy(game.state)
    state['participants'].remove(pid)
    state['pending'] = [value for value in state.get('pending', []) if value != pid]
    state['gifts'] = [gift for gift in state.get('gifts', []) if gift['contributor_id'] != pid]
    for gift in state['gifts']:
        gift.update(opened=False, holder_id=None, steals=0)
    for key in ('assignments', 'order', 'current_player_id', 'next_index', 'last_stolen_id'):
        state.pop(key, None)
    game.state = state
    game.status = 'waiting' if len(state['participants']) >= 2 else 'cancelled'
    game.version += 1
    record_audit(request.current_user.id, 'gift_game.left', 'gift_exchange_game', game.id, game.household_id)
    db.session.commit()
    return jsonify(status='left', game=game_dict(game, request.current_user) if accessible(game, request.current_user) else None)


@game_api.post('/games/<int:game_id>/join')
@authenticated
def join_game(game_id):
    game, failure = locked_game(game_id)
    if failure:
        return failure
    pid = request.get_json().get('profile_id')
    if type(pid) is not int or pid not in managed_participants(game,request.current_user) or pid not in game.state.get('pending',[]):
        return error('Choose your invited participant.',403)
    if game.status != 'waiting':
        return error('This game is no longer accepting participants.',409)
    game.state = {**game.state,'pending':[value for value in game.state['pending'] if value != pid]}
    game.version += 1
    db.session.commit()
    return jsonify(game=game_dict(game,request.current_user))


def pending_game_notifications(user):
    games = GiftExchangeGame.query.filter_by(status='waiting').order_by(GiftExchangeGame.id.desc()).all()
    return [{'id':'game-'+str(game.id),'game_id':game.id,'household_name':game.title,
        'message':'You are invited to '+game.title+'. Join or decline in Games.', 'read':False,
        'created_at':game.created_at.isoformat(),'url':'/following?tab=games&game='+str(game.id)}
        for game in games if set(game.state.get('pending',[])).intersection(managed_participants(game,user))]
