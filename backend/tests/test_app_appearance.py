from copy import deepcopy
from backend.tests.test_diagnostic_view import staff_client
from backend.tests.test_reservation_privacy import register,mutate
from backend.app.app_appearance import DEFAULTS


def test_only_master_can_publish_light_and_dark_colors_and_internal_settings_stay_out_of_catalog(app):
    master=staff_client(app)
    agent=staff_client(app,master=False)
    family=app.test_client();register(family,'Parent','palette-parent@example.com')
    public=app.test_client()
    assert public.get('/api/app-appearance').json['appearance']==DEFAULTS
    draft=deepcopy(DEFAULTS);draft['light']['accent']='#774499';draft['season']='christmas'
    for client in (agent,family,public):
        assert mutate(client,'PATCH','/api/support/app-appearance',draft).status_code==403
    saved=mutate(master,'PATCH','/api/support/app-appearance',draft)
    assert saved.status_code==200,saved.json
    assert public.get('/api/app-appearance').json['appearance']==draft
    assert master.get('/api/support/themes').json['themes']==[]
    assert family.get('/api/themes').json['themes']==[]


def test_rejects_invalid_colors_and_unreadable_text_without_changing_published_colors(app):
    master=staff_client(app)
    for color in ('red','url(https://example.com)','#fff8ff'):
        draft=deepcopy(DEFAULTS);draft['light']['foreground']=color
        assert mutate(master,'PATCH','/api/support/app-appearance',draft).status_code==400
    assert master.get('/api/app-appearance').json['appearance']==DEFAULTS
