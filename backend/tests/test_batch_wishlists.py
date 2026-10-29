from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import mutate
from backend.app.extensions import db
from backend.app.models import Wishlist


def test_batch_lists_are_separate_and_child_approval_is_scoped(app):
    parent, child, stranger, _, profiles, _, _, _ = child_setup(app)
    ids = [p['id'] for p in profiles]
    response = mutate(parent, 'POST', '/api/wishlists/batch',
                      dict(title='Christmas', profile_ids=ids, allow_child_items=True))
    assert response.status_code == 201, response.json
    rows = response.json['wishlists']
    assert {row['profile_id'] for row in rows} == set(ids)
    assert len({row['id'] for row in rows}) == len(ids)
    own = next(row for row in rows if row['profile_id'] == ids[0])
    other = next(row for row in rows if row['profile_id'] == ids[1])
    assert mutate(child, 'POST', f"/api/child/wishlists/{own['id']}/items", {'name': 'A train'}).status_code == 201
    assert mutate(child, 'POST', f"/api/child/wishlists/{other['id']}/items", {'name': 'A train'}).status_code == 404
    assert not any(child.get('/api/child/me').json['controls'].values())
    controls = parent.get(f"/api/profiles/{ids[1]}/child-controls").json
    assert other['id'] in controls['wishlist_ids']
    assert controls['enabled'] is False  # A new child still needs parent setup.
    assert mutate(stranger, 'POST', '/api/wishlists/batch', dict(title='No', profile_ids=ids)).status_code == 403
    assert mutate(child, 'POST', '/api/wishlists/batch', dict(title='No', profile_ids=ids)).status_code == 403


def test_batch_without_approval_and_invalid_request_are_atomic(app):
    parent, child, _, _, profiles, _, _, _ = child_setup(app)
    pid = profiles[0]['id']
    response = mutate(parent, 'POST', '/api/wishlists/batch',
                      dict(title='Birthday', profile_ids=[pid, pid], allow_child_items=False))
    assert response.status_code == 201
    assert len(response.json['wishlists']) == 1
    wid = response.json['wishlists'][0]['id']
    assert mutate(child, 'POST', f'/api/child/wishlists/{wid}/items', {'name': 'No'}).status_code == 404
    with app.app_context():
        before = Wishlist.query.count()
    for payload in [dict(title='Christmas', profile_ids=[pid, 999999]),
                    dict(title='Christmas', profile_ids=[True]),
                    dict(title='Christmas', profile_ids=[pid], allow_child_items='yes'),
                    dict(title='', profile_ids=[pid])]:
        assert mutate(parent, 'POST', '/api/wishlists/batch', payload).status_code in (400, 403)
    with app.app_context():
        assert Wishlist.query.count() == before


def test_assign_name_creates_independent_empty_lists_and_skips_duplicates(app):
    parent, _, stranger, _, profiles, _, _, _ = child_setup(app)
    source = mutate(parent, 'POST', f"/api/profiles/{profiles[0]['id']}/wishlists", {'title': 'Christmas'}).json['wishlist']
    assert mutate(parent, 'POST', f"/api/wishlists/{source['id']}/items", {'name': 'Source gift'}).status_code == 201
    payload = dict(source_wishlist_id=source['id'], profile_ids=[row['id'] for row in profiles], allow_child_items=False)
    response = mutate(parent, 'POST', '/api/wishlists/batch', payload)
    assert response.status_code == 201, response.json
    rows = response.json['wishlists']
    original = next(row for row in rows if row['profile_id'] == profiles[0]['id'])
    assigned = next(row for row in rows if row['profile_id'] == profiles[1]['id'])
    assert original['id'] == source['id'] and original['already_exists'] is True
    assert assigned['id'] != source['id'] and assigned['title'] == 'Christmas'
    assert parent.get(f"/api/wishlists/{assigned['id']}/items").json['items'] == []
    assert parent.get(f"/api/wishlists/{source['id']}/items").json['items'][0]['name'] == 'Source gift'
    with app.app_context():
        count = Wishlist.query.count()
    repeated = mutate(parent, 'POST', '/api/wishlists/batch', payload)
    assert repeated.status_code == 201
    assert all(row['already_exists'] for row in repeated.json['wishlists'])
    with app.app_context():
        assert Wishlist.query.count() == count
    assert mutate(stranger, 'POST', '/api/wishlists/batch', payload).status_code == 403
