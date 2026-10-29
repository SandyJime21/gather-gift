from backend.tests.wishlist_setup import create_test_wishlist
from backend.tests.test_reservation_privacy import register, mutate


def test_private_company_employee_lists_and_selected_invitations(app):
    company, shopper, stranger = [app.test_client() for _ in range(3)]
    register(company, 'Company owner', 'companyowner@example.com')
    register(shopper, 'Gifter', 'companygifter@example.com')
    register(stranger, 'Stranger', 'companystranger@example.com')
    response = mutate(company, 'POST', '/api/households', {'name': 'Example Co', 'registry_type': 'company',
        'profiles': [{'display_name': 'Alex'}, {'display_name': 'Sam', 'relationship': 'manager'}]})
    assert response.status_code == 201, response.json
    home = response.json['household']
    assert home['registry_type'] == 'company'
    path = f"/api/households/{home['id']}"
    profiles = company.get(path).json['profiles']
    assert [row['relationship'] for row in profiles] == ['employee', 'manager']
    assert stranger.get(path).status_code == 404
    profile_id = profiles[0]['id']
    wishlist = create_test_wishlist(company, f'/api/profiles/{profile_id}/wishlists')
    assert mutate(company, 'POST', f"/api/wishlists/{wishlist['id']}/items", {'name': 'Coffee gift set'}).status_code == 201
    invitation = mutate(company, 'POST', path + '/invitations', {'email': 'companygifter@example.com', 'role': 'shopper', 'profile_ids': [profile_id]})
    assert 'employee gift list' in invitation.json['email_message']['subject']
    assert mutate(shopper, 'POST', '/api/invitations/accept', {'token': invitation.json['invitation']['token']}).status_code == 200
    shared = shopper.get(path).json
    assert shared['household']['registry_type'] == 'company'
    assert [row['id'] for row in shared['profiles']] == [profile_id]
    assert shopper.get(f"/api/profiles/{profiles[1]['id']}").status_code == 404
    assert shopper.get('/api/shopping').json['items'][0]['name'] == 'Coffee gift set'
    assert mutate(company, 'POST', path + '/child-accounts', {'profile_id': profile_id, 'wishlist_ids': [wishlist['id']], 'password': 'not-a-child-account'}).status_code == 400
    assert mutate(company, 'POST', path + '/profiles', {'display_name': 'Pet', 'profile_type': 'pet'}).status_code == 400
    assert mutate(company, 'POST', '/api/households', {'name': 'Bad', 'registry_type': 'public'}).status_code == 400
