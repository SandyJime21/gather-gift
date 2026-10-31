"""Published app palettes, stored separately from selectable theme artwork."""
import re
from copy import deepcopy
from flask import request,jsonify
from .api import api,superuser_required,error,record_audit
from .models import SharedTheme
from .extensions import db
DEFAULTS={'season':'classic','light':{'background':'#e8f4ff','surface':'#f7fbff','foreground':'#203b54','accent':'#286aab','soft':'#d5eaff','border':'#adcde9'},'dark':{'background':'#101e30','surface':'#1b3048','foreground':'#edf6ff','accent':'#91caff','soft':'#29435f','border':'#567b9e'}}

def stored():
    return next((row for row in SharedTheme.query.order_by(SharedTheme.id.desc()).all() if row.data.get('purpose')=='site-palette'),None)

def luminance(color):
    values=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
    return sum(v*w for v,w in zip(values,(.2126,.7152,.0722)))

def contrast(a,b):
    light,dark=sorted([luminance(a),luminance(b)],reverse=True)
    return (light+.05)/(dark+.05)

@api.get('/app-appearance')
def public_app_appearance():
    row=stored()
    response=jsonify(appearance=row.data['appearance'] if row else deepcopy(DEFAULTS))
    response.headers['Cache-Control']='no-store'
    return response

@api.route('/support/app-appearance',methods=['GET','PATCH'])
@superuser_required
def manage_app_appearance():
    row=stored()
    if request.method=='PATCH':
        value=request.get_json(silent=True) or {}
        if value.get('season') not in ('classic','christmas'):return error('Choose classic or Christmas.',400)
        cleaned={'season':value['season']}
        for mode in ('light','dark'):
            palette=value.get(mode)
            if not isinstance(palette,dict) or set(palette)!=set(DEFAULTS[mode]) or any(not isinstance(c,str) or not re.fullmatch('#[0-9a-fA-F]{6}',c) for c in palette.values()):return error('Use six-digit hex colors for each palette.',400)
            if any(contrast(palette['foreground'],palette[key])<4.5 for key in ('background','surface','soft')):return error('Text needs at least 4.5:1 contrast against the page and card colors.',400)
            if any(contrast(palette['accent'],palette[key])<4.5 for key in ('background','surface','soft')):return error('Links need at least 4.5:1 contrast against page, card and soft accent colors.',400)
            cleaned[mode]=dict(palette)
        if row is None:row=SharedTheme(data={});db.session.add(row)
        row.data={'purpose':'site-palette','active':False,'name':'App display colors','audience':'everyone','appearance':cleaned}
        db.session.flush();record_audit(request.current_user.id,'appearance.colors_updated','shared_theme',row.id,details={'season':cleaned['season']});db.session.commit()
    return jsonify(appearance=row.data['appearance'] if row else deepcopy(DEFAULTS))
