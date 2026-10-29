"""Parent-owned, default-deny permissions for optional child activities."""
from flask import jsonify, request
from .api import api, authenticated, error, profile_access
from .extensions import db
from .models import PersonProfile, User

CONTROL_KEYS = ('web_search', 'product_links', 'manage_pets', 'switch_siblings', 'game_invites')


def controls_for(child):
    parent = db.session.get(User, child.parent_user_id) if child and child.is_child else None
    saved = ((parent.notification_preferences or {}).get('child_access', {}).get(str(child.id), {}) if parent else {})
    return {key: saved.get(key) is True for key in CONTROL_KEYS}


@api.route('/profiles/<int:profile_id>/child-controls', methods=['GET', 'PATCH'])
@authenticated
def parent_child_controls(profile_id):
    parent = request.current_user
    profile = db.session.get(PersonProfile, profile_id)
    if (parent.is_child or parent.is_support or not profile or profile.profile_type != 'person'
            or profile.is_adult or not profile_access(parent, profile_id, write=True)):
        return error('Child controls are not available.', 403)
    child = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
    if not child or not child.is_child or child.parent_user_id != parent.id:
        return jsonify(controls={key: False for key in CONTROL_KEYS}, available=False)
    if request.method == 'PATCH':
        payload = request.get_json(silent=True) or {}
        if not payload or set(payload) - set(CONTROL_KEYS) or any(type(value) is not bool for value in payload.values()):
            return error('Choose valid child access switches.', 400)
        preferences = dict(parent.notification_preferences or {})
        access = dict(preferences.get('child_access', {}))
        access[str(child.id)] = {**controls_for(child), **payload}
        preferences['child_access'] = access
        parent.notification_preferences = preferences
        db.session.commit()
    return jsonify(controls=controls_for(child), available=True)
