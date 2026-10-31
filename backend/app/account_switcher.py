"""Credential-verified account switching within one server-side browser session."""
from flask import request,session,jsonify,current_app
from sqlalchemy.exc import IntegrityError
from .api import api,authenticated,error,normalized_email,record_audit,session_payload
from .extensions import db,limiter
from .models import User


def identity(user):
    return {'user_id':user.id,'version':user.session_version,'mode':'support' if user.is_support else 'family'}


def remembered(user):
    values={row['user_id']:row for row in session.get('account_switches',[]) if isinstance(row,dict) and type(row.get('user_id'))is int}
    values[user.id]=identity(user)
    return list(values.values())


def valid_account(entry):
    user=db.session.get(User,entry['user_id'])
    return user if user and not user.is_child and user.session_version==entry.get('version') and entry.get('mode')==('support' if user.is_support else 'family') else None


def response_accounts(user):
    values=[]
    for entry in remembered(user):
        other=valid_account(entry)
        if other:values.append({'id':other.id,'name':other.name,'email':other.email,'current':other.id==user.id,'is_support':other.is_support,'is_superuser':other.is_superuser})
    response=jsonify(accounts=values)
    response.headers['Cache-Control']='private, no-store'
    return response


@api.get('/auth/accounts')
@authenticated
def saved_accounts():
    if request.current_user.is_child:return error('Account switching is for adults.',403)
    return response_accounts(request.current_user)


@api.post('/auth/accounts/add')
@authenticated
@limiter.limit('10 per minute')
def add_saved_account():
    actor=request.current_user
    if actor.is_child:return error('Account switching is for adults.',403)
    payload=request.get_json(silent=True) or {}
    if set(payload)-{'email','password','name','create'}:return error('Use account credentials to add an account.',400)
    email=normalized_email(payload.get('email'))
    password=payload.get('password');create=payload.get('create',False)
    if not email or not isinstance(password,str) or type(create)is not bool:return error('Enter a valid email and password.',400)
    target=User.query.filter(db.func.lower(User.email)==email).first()
    if create:
        name=payload.get('name','')
        if target:return error('That email already has an account. Choose Sign in to an existing account.',409)
        if not isinstance(name,str) or not 1<=len(name.strip())<=120 or len(password)<10:return error('Enter a name and a password of at least 10 characters.',400)
        target=User(name=name.strip(),email=email,is_child=False,is_support=False,is_superuser=False)
        target.set_password(password);db.session.add(target)
        try:db.session.flush()
        except IntegrityError:db.session.rollback();return error('That email already has an account.',409)
    elif not target or target.is_child or not target.check_password(password):
        return error('Email or password is incorrect. Use an adult account.',401)
    entries=remembered(actor)
    entries=[entry for entry in entries if entry['user_id']!=target.id]
    if len(entries)>=5:return error('Up to five accounts can be saved in this browser session. Sign out to clear them.',400)
    entries.append(identity(target))
    record_audit(actor.id,'account_switcher.account_verified','user',target.id,details={'created':create,'account_type':'support' if target.is_support else 'family'})
    db.session.commit()
    session['account_switches']=entries
    return response_accounts(actor)


@api.post('/auth/accounts/switch')
@authenticated
def switch_saved_account():
    actor=request.current_user
    if actor.is_child:return error('Account switching is for adults.',403)
    target_id=(request.get_json(silent=True) or {}).get('user_id')
    if type(target_id)is not int:return error('Choose a saved account.',400)
    entries=remembered(actor)
    entry=next((value for value in entries if value['user_id']==target_id),None)
    if entry is None:return error('Verify this account with its email and password first.',403)
    target=valid_account(entry)
    if target is None:return error('This account needs sign-in again. Add it again to verify its credentials.',409)
    record_audit(actor.id,'account_switcher.switched','user',target.id)
    db.session.commit()
    session.clear();session.update(user_id=target.id,auth_version=target.session_version,auth_mode=entry['mode'],account_switches=entries)
    current_app.session_interface.regenerate(session)
    return jsonify(session_payload(target))
