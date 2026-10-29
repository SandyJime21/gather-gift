"""Email-only game invitations, with explicit game and follow decisions."""
import copy
import hashlib
import secrets
import time
from flask import request, jsonify, current_app
from .gift_games import game_api, organizer, game_dict
from .api import authenticated, error, normalized_email
from .extensions import db, limiter
from .models import (GiftExchangeGame, User, PersonProfile, FamilyFollow,
                     HouseholdProfileAccess, HouseholdMembership, HouseholdMemberProfileAccess)


def invitation(game, token):
    digest = hashlib.sha256(token.encode()).hexdigest()
    return next((row for row in (game.state.get('email_invites', []) if game else [])
                 if row['token_hash'] == digest and row['status'] == 'pending'
                 and row['expires_at'] > time.time()), None)


@game_api.post('/games/<int:game_id>/email-invitations')
@authenticated
@limiter.limit('20 per hour')
def email_game_invitation(game_id):
    game = GiftExchangeGame.query.filter_by(id=game_id).with_for_update().first()
    if not game or not organizer(game, request.current_user):
        return error('Only the organizer can invite players.', 403)
    if game.status != 'waiting':
        return error('Invite players before starting the game.', 409)
    payload = request.get_json()
    recipient_id = payload.get('recipient_user_id')
    target = db.session.get(User, recipient_id) if type(recipient_id) is int else None
    if recipient_id is not None and (not target or target.is_child or target.is_support):
        return error('Choose an adult account.', 400)
    email = target.email.lower() if target else normalized_email(payload.get('email', ''))
    if not email or email == request.current_user.email.lower():
        return error('Enter another adult’s email address.', 400)
    target = User.query.filter_by(email=email).first()
    if target and (target.is_child or target.is_support):
        return error('Invite an adult family account.', 400)
    if target and PersonProfile.query.filter(PersonProfile.id.in_(game.state['participants']), PersonProfile.account_user_id == target.id).first():
        return error('This person is already invited or participating in this game.', 409)
    state = copy.deepcopy(game.state)
    rows = state.setdefault('email_invites', [])
    if len(rows) + len(state['participants']) >= 50 and not any(row['email'] == email for row in rows):
        return error('A game supports up to 50 players and invitations.', 400)
    rows[:] = [row for row in rows if row['email'] != email]
    token = secrets.token_urlsafe(32)
    rows.append(dict(email=email, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                     status='pending', expires_at=time.time()+7*24*3600))
    game.state = state
    game.version += 1
    db.session.commit()
    from .invitation_mail import send_game_invitation
    link = current_app.config['FRONTEND_ORIGIN'].rstrip('/')+f'/game-invitations/{game.id}/{token}'
    delivered = send_game_invitation(email, game.title, request.current_user.name, link, ['you'])
    if not delivered:
        state = copy.deepcopy(game.state)
        for saved in state['email_invites']:
            if saved['token_hash'] == hashlib.sha256(token.encode()).hexdigest():
                saved['status'] = 'failed'
        game.state = state
        game.version += 1
        db.session.commit()
    return jsonify(delivered=delivered, game=game_dict(game, request.current_user),
                   error=None if delivered else 'Email could not be sent. Check email setup and try again.',
                   message='Invitation emailed.' if delivered else 'Email could not be sent. Check email setup and try again.'), 201 if delivered else 503


@game_api.post('/games/<int:game_id>/email-invitations/revoke')
@authenticated
def revoke_email_game_invitation(game_id):
    game = GiftExchangeGame.query.filter_by(id=game_id).with_for_update().first()
    if not game or not organizer(game, request.current_user):
        return error('Only the organizer can withdraw invitations.', 403)
    if game.status != 'waiting':
        return error('This game has already started.', 409)
    email = request.get_json().get('email')
    state = copy.deepcopy(game.state)
    for saved in state.get('email_invites', []):
        if saved['email'] == email and saved['status'] == 'pending':
            saved['status'] = 'revoked'
    game.state = state
    game.version += 1
    db.session.commit()
    return jsonify(game=game_dict(game, request.current_user))


@game_api.get('/game-invitations/<int:game_id>/<token>')
@limiter.limit('60 per hour')
def preview_email_game_invitation(game_id, token):
    game = db.session.get(GiftExchangeGame, game_id)
    if not invitation(game, token) or game.status != 'waiting':
        return error('This invitation has expired, was answered, or the game is no longer accepting players.', 410)
    host = db.session.get(User, game.created_by_id)
    return jsonify(title=game.title, host=host.name if host else 'The organizer',
                   kind=game.kind, budget=str(game.budget) if game.budget is not None else None)


@game_api.post('/game-invitations/<int:game_id>/<token>')
@authenticated
@limiter.limit('30 per hour')
def answer_email_game_invitation(game_id, token):
    game = GiftExchangeGame.query.filter_by(id=game_id).with_for_update().first()
    row = invitation(game, token)
    user = request.current_user
    if not row or game.status != 'waiting':
        return error('This invitation is no longer available.', 410)
    if user.is_child or user.is_support or user.email.lower() != row['email']:
        return error('Sign in with the adult email address that received this invitation.', 403)
    payload = request.get_json()
    if any(type(payload.get(key)) is not bool for key in ('join_game', 'allow_follow')):
        return error('Choose yes or no for the game and follow request.', 400)
    state = copy.deepcopy(game.state)
    for saved in state['email_invites']:
        if saved['token_hash'] == row['token_hash']:
            saved['status'] = 'accepted' if payload['join_game'] else 'declined'
    profile = PersonProfile.query.filter_by(account_user_id=user.id, is_adult=True).order_by(PersonProfile.id).first()
    if profile is None and (payload['join_game'] or payload['allow_follow']):
        profile = PersonProfile(account_user_id=user.id, display_name=user.name, is_adult=True, profile_type='person')
        db.session.add(profile)
        db.session.flush()
    if payload['join_game'] and profile.id not in state['participants']:
        if len(state['participants']) >= 50:
            return error('This game is full.', 409)
        state['participants'].append(profile.id)
    if payload['join_game']:
        state['pending'] = [pid for pid in state.get('pending', []) if pid != profile.id]
    if payload['allow_follow'] and game.created_by_id and game.created_by_id != user.id:
        host_id = game.created_by_id
        if not FamilyFollow.query.filter_by(follower_id=host_id, followed_id=user.id).first():
            db.session.add(FamilyFollow(follower_id=host_id, followed_id=user.id))
        # Share this adult's own profile only; never grant access to children or pets.
        for access in HouseholdProfileAccess.query.filter_by(profile_id=profile.id).all():
            member = HouseholdMembership.query.filter_by(household_id=access.household_id, user_id=host_id).first()
            if member is None:
                member = HouseholdMembership(household_id=access.household_id, user_id=host_id, role='shopper', share_all_profiles=False)
                db.session.add(member); db.session.flush()
            if not HouseholdMemberProfileAccess.query.filter_by(membership_id=member.id, profile_id=profile.id).first():
                db.session.add(HouseholdMemberProfileAccess(membership_id=member.id, profile_id=profile.id, can_edit=False))
    game.state = state
    game.version += 1
    db.session.commit()
    return jsonify(joined=payload['join_game'], message='Your choices have been saved.', game_id=game.id)
