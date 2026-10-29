from datetime import date
from types import SimpleNamespace
from backend.app.profile_preferences import completion, gift_guide
from backend.tests.test_reservation_privacy import register, mutate


def profile(**values):
    fields = dict(photo_path=None, birthday=None, allergies=None, favorite_snacks=[], interests=[], favorite_characters=[], hobbies=[], profile_type="person", is_adult=True, clothing_sizes={}, shoe_sizes={}, favorite_colors=[], favorite_brands=[], favorite_stores=[], gift_preferences=None)
    return SimpleNamespace(**(fields | values))


def test_completion_counts_only_provided_details_and_supports_none_known():
    empty = profile()
    assert completion(empty)["percent"] == 0
    assert "Allergies or none known" in completion(empty)["missing"]
    full = profile(photo_path="photo.jpg", birthday=date(2000, 6, 1), allergies="None known", interests=["Painting"], clothing_sizes={"shirt":"M"}, shoe_sizes={"US":"7"}, favorite_colors=["Pink"], favorite_brands=["Brand"], favorite_stores=["Shop"], gift_preferences="Art supplies")
    assert completion(full)["percent"] == 100
    assert completion(full)["missing"] == []
    assert completion(profile(interests=["  "]))["percent"] == 0


def test_children_and_pets_have_shorter_checklists_and_guides_exclude_private_notes():
    adult = profile()
    child = profile(is_adult=False)
    pet = profile(profile_type="pet", is_adult=False)
    assert completion(pet)["total"] < completion(child)["total"] < completion(adult)["total"]
    assert "Clothing size" not in completion(pet)["missing"]
    assert "Favorite brands" not in completion(child)["missing"]
    guide = gift_guide(profile(allergies="Peanuts", parent_notes="Private", items_to_avoid="Private"))
    assert guide["allergies"] == "Peanuts"
    assert "parent_notes" not in guide and "items_to_avoid" not in guide


def test_parent_updates_child_gift_guide_and_strangers_cannot_view_it(app):
    owner, stranger = app.test_client(), app.test_client()
    register(owner, "Parent", "guide-parent@example.com")
    register(stranger, "Stranger", "guide-stranger@example.com")
    home = mutate(owner,"POST","/api/households",{"name":"Family","profiles":[{"display_name":"Child"}]}).json["household"]
    profiles = owner.get(f"/api/households/{home['id']}").json["profiles"]
    child = next(p for p in profiles if p["display_name"] == "Child")
    path = f"/api/profiles/{child['id']}"
    saved = mutate(owner,"PATCH",path,{"allergies":"Peanuts","favorite_characters":["Minnie Mouse"],"favorite_colors":["Pink"],"clothing_sizes":{"shirt":"5T"},"shoe_sizes":{"US":"11"}})
    assert saved.status_code == 200
    assert saved.json["profile"]["allergies"] == "Peanuts"
    assert saved.json["profile"]["favorite_characters"] == ["Minnie Mouse"]
    assert saved.json["profile"]["completion"]["percent"] > 0
    wishlist = owner.get(path+"/wishlists").json["wishlists"][0]
    item = mutate(owner,"POST",f"/api/wishlists/{wishlist['id']}/items",{"name":"Cozy pajamas"}).json["item"]
    assert item["recipient_preferences"]["allergies"] == "Peanuts"
    assert item["recipient_preferences"]["clothing_sizes"] == {"shirt":"5T"}
    assert "parent_notes" not in item["recipient_preferences"]
    assert stranger.get(path).status_code == 404
    assert mutate(stranger,"PATCH",path,{"allergies":"None known"}).status_code == 404
    assert mutate(owner,"PATCH",path,{"allergies":["invalid"]}).status_code == 400
    reminders = owner.get("/api/notifications").json["profile_reminders"]
    assert any(n["profile_id"] == child["id"] for n in reminders)
    assert stranger.get("/api/notifications").json["profile_reminders"] == []


def test_profile_reminders_are_owned_ordered_and_clear_per_user(app):
    from backend.app.extensions import db
    from backend.app.models import PersonProfile
    owner, adult = app.test_client(), app.test_client()
    me = register(owner, 'Owner', 'reminder-owner@example.com')
    other = register(adult, 'Adult', 'reminder-adult@example.com')
    home = mutate(owner, 'POST', '/api/households', {'name':'Family', 'profiles':[{'display_name':'Z Me'},{'display_name':'A Child'},{'display_name':'Invited Adult'}]}).json['household']
    profiles = owner.get(f"/api/households/{home['id']}").json['profiles']
    ids = {row['display_name']:row['id'] for row in profiles}
    with app.app_context():
        own = db.session.get(PersonProfile, ids['Z Me'])
        own.account_user_id, own.is_adult = me['id'], True
        invited = db.session.get(PersonProfile, ids['Invited Adult'])
        invited.account_user_id, invited.is_adult = other['id'], True
        db.session.commit()
    response = owner.get('/api/notifications')
    assert response.status_code == 200
    reminders = response.json['profile_reminders']
    assert reminders[0]['is_you'] is True
    assert any(row['profile_id'] == ids['A Child'] for row in reminders)
    assert not any(row['profile_id'] == ids['Invited Adult'] for row in reminders)
    assert all('%' not in row['message'] for row in reminders)
    assert mutate(owner, 'POST', '/api/notifications/clear').status_code == 200
    assert owner.get('/api/notifications').json['profile_reminders'] == []
    with app.app_context():
        assert db.session.get(PersonProfile, ids['Invited Adult']).account_user_id == other['id']
