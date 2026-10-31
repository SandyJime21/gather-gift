"""Time-limited, read-only superuser diagnostic impersonation."""
from datetime import datetime,timedelta,timezone
from flask import session,request,jsonify
from .api import api,superuser_required,error,record_audit,session_payload,_csrf_token
from .extensions import db
from .models import User


def restore(state):
    actor=db.session.get(User,state.get('actor_id'))
    valid=bool(actor and actor.is_support and actor.is_superuser and actor.session_version==state.get('actor_version'))
    session.clear()
    if valid:
        session.update(user_id=actor.id,auth_version=actor.session_version,auth_mode='support')
    return actor if valid else None


@api.before_app_request
def guard_diagnostic_view():
    state=session.get('diagnostic_view')
    if not state or not request.path.startswith('/api/'):return None
    actor=db.session.get(User,state.get('actor_id'))
    target=db.session.get(User,state.get('target_id'))
    valid=bool(actor and actor.is_support and actor.is_superuser and actor.session_version==state.get('actor_version') and target and not target.is_support and session.get('user_id')==target.id and target.session_version==session.get('auth_version') and state.get('expires_at',0)>datetime.now(timezone.utc).timestamp())
    if request.endpoint=='api.end_diagnostic_view':return None
    if not valid:
        restore(state)
        return error('Diagnostic view expired. Return to the support portal.',401)
    if request.method not in ('GET','HEAD','OPTIONS'):
        return error('This diagnostic view is read-only. Return to support to end it.',403)
    if request.endpoint not in ('api.csrf','api.current_user') and request.method=='GET':
        record_audit(actor.id,'support.diagnostic_read','user',target.id,details={'path':request.path,'reason':state['reason']})
        db.session.commit()


@api.post('/support/diagnostic-view')
@superuser_required
def start_diagnostic_view():
    body=request.get_json(silent=True) or {}
    email=body.get('email','')
    reason=body.get('reason','')
    if not isinstance(email,str) or not isinstance(reason,str) or not 10<=len(reason.strip())<=1000:
        return error('Enter an account email and a testing reason of 10 to 1,000 characters.',400)
    target=User.query.filter(db.func.lower(User.email)==email.strip().lower(),User.is_support.is_(False)).first()
    if not target or target.is_child:return error('Choose an existing adult family account.',404)
    actor=request.current_user
    expires=datetime.now(timezone.utc)+timedelta(minutes=30)
    record_audit(actor.id,'support.diagnostic_started','user',target.id,details={'reason':reason.strip(),'expires_at':expires.isoformat(),'consent_basis':'superuser_diagnostics'})
    db.session.commit()
    state=dict(actor_id=actor.id,actor_version=actor.session_version,target_id=target.id,expires_at=expires.timestamp(),reason=reason.strip(),actor_name=actor.name)
    session.clear()
    session.update(user_id=target.id,auth_version=target.session_version,auth_mode='family',diagnostic_view=state)
    return jsonify(session_payload(target))


@api.post('/support/diagnostic-view/end')
def end_diagnostic_view():
    state=session.get('diagnostic_view')
    if not state:return error('No diagnostic view is active.',400)
    actor=restore(state)
    if not actor:return error('Sign in to the support portal again.',401)
    record_audit(actor.id,'support.diagnostic_ended','user',state.get('target_id'),details={'reason':state['reason']})
    db.session.commit()
    return jsonify(session_payload(actor))
