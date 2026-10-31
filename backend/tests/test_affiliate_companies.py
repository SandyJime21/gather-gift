from backend.tests.test_diagnostic_view import staff_client
from backend.tests.test_reservation_privacy import mutate
from backend.app.commerce import resolve
from backend.app.extensions import db
from backend.app.models import CommerceIntegration


def test_master_adds_approved_company_and_resolves_issued_links_only(app,monkeypatch):
    staff=staff_client(app)
    monkeypatch.setenv('MY_STORE_SECRET','private-test-value')
    body=dict(company_name='My Store',website='https://www.store.example',tracking_template='https://partner.example/track?url={url}',publisher_id='public-publisher-7',key_environment='MY_STORE_SECRET',approved=True,enabled=True)
    response=mutate(staff,'POST','/api/support/commerce/companies',body)
    assert response.status_code==201,response.json
    provider=response.json['provider'];assert provider['name']=='My Store'
    assert 'private-test-value' not in str(response.json)
    with app.app_context():
        target,key=resolve('https://store.example/gift')
        assert target=='https://partner.example/track?url=https%3A%2F%2Fstore.example%2Fgift'
        assert key==provider['id']
        row=db.session.get(CommerceIntegration,key)
        assert 'private-test-value' not in str(row.merchant_rules)
    denied=mutate(staff,'PATCH','/api/support/commerce/'+provider['id'],{'merchant_rules':{'approved_merchants':['store.example'],'links':{'store.example':'https://partner.example/private-test-value?url={url}'}}})
    assert denied.status_code==400
    assert mutate(staff,'POST','/api/support/commerce/companies',{**body,'approved':False}).status_code==400
    assert mutate(staff,'POST','/api/support/commerce/companies',{**body,'api_key':'must-not-store'}).status_code==400


def test_company_creation_is_master_only_and_defaults_unapproved(app):
    staff=staff_client(app);agent=staff_client(app,master=False)
    body=dict(company_name='Pending store',website='https://pending.example')
    assert mutate(agent,'POST','/api/support/commerce/companies',body).status_code==403
    created=mutate(staff,'POST','/api/support/commerce/companies',body)
    assert created.status_code==201,created.json
    assert not created.json['provider']['enabled'] and not created.json['provider']['approved']
    with app.app_context():assert resolve('https://pending.example/gift')==('https://pending.example/gift','direct')
