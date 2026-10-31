from backend.tests.test_wishlist_price_requests import setup_request
from backend.tests.test_diagnostic_view import staff_client
from backend.tests.test_reservation_privacy import mutate
from backend.app.extensions import db
from backend.app.models import HouseholdProfileAccess,HouseholdMembership,SupportTicket


def test_assigned_staff_see_requester_household_ids_without_receiving_access(app):
    owner,_,outsider,profile,_=setup_request(app)
    owner_id=owner.get('/api/auth/me').json['user']['id']
    other=mutate(outsider,'POST','/api/households',{'name':'Followed only'}).json['household']
    with app.app_context():
        own_home=HouseholdProfileAccess.query.filter_by(profile_id=profile['id']).first().household_id
        db.session.add(HouseholdMembership(household_id=other['id'],user_id=owner_id,role='shopper'));db.session.commit()
    ticket=mutate(owner,'POST','/api/support/tickets',{'subject':'Wishlist problem','description':'Please help with my list','category':'bug'}).json['ticket']
    assert 'households' not in ticket
    staff=staff_client(app,master=False)
    staff_id=staff.get('/api/auth/me').json['user']['id']
    assert staff.get('/api/support/tickets').json['tickets']==[]
    with app.app_context():db.session.get(SupportTicket,ticket['id']).assigned_to_id=staff_id;db.session.commit()
    visible=staff.get('/api/support/tickets').json['tickets'][0]
    assert visible['households']==[{'id':own_home,'name':'Family'}]
    assert staff.get('/api/support/grants').json['grants']==[]
    assert staff.get(f"/api/profiles/{profile['id']}").status_code==403
