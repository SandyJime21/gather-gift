from backend.tests.wishlist_setup import create_test_wishlist
from backend.app.extensions import db
from backend.app.models import HouseholdMemberProfileAccess, HouseholdMembership, GiftReservation
from backend.tests.test_child_access import child_setup
from backend.tests.test_reservation_privacy import mutate, register


def add_pet(parent, household_id):
    response = mutate(
        parent,
        "POST",
        f"/api/households/{household_id}/profiles",
        {"display_name": "Mochi", "profile_type": "pet"},
    )
    assert response.status_code == 201, response.get_json()
    profile = response.get_json()["profile"]
    wishlist = create_test_wishlist(parent, f"/api/profiles/{profile['id']}/wishlists")
    return profile, wishlist


def test_family_members_can_add_and_remove_pet_wishes(app):
    owner, child, _, household, profiles, _, _, _ = child_setup(app)
    from backend.tests.test_child_controls import allow_optional_features
    allow_optional_features(app)
    pet, wishlist = add_pet(owner, household["id"])
    item = mutate(owner, "POST", f"/api/wishlists/{wishlist['id']}/items", {
        "name": "Treat puzzle",
    }).get_json()["item"]

    pet_view = child.get("/api/child/me").get_json()["pets"][0]
    assert pet_view["name"] == "Mochi"
    assert [row["name"] for row in pet_view["items"]] == ["Treat puzzle"]

    added = mutate(child, "POST", f"/api/child/pets/{pet['id']}/items", {
        "name": "Soft bed",
        "description": "A cozy place to nap",
    })
    assert added.status_code == 201, added.get_json()
    assert [row["name"] for row in child.get("/api/child/me").get_json()["pets"][0]["items"]] == [
        "Soft bed",
        "Treat puzzle",
    ]
    assert mutate(child, "DELETE", f"/api/child/pets/{pet['id']}/items/{item['id']}").status_code == 200
    assert [row["name"] for row in child.get("/api/child/me").get_json()["pets"][0]["items"]] == ["Soft bed"]

def test_family_member_can_manage_pet_items_but_not_remove_child_items(app):
    owner, _, _, household, profiles, lists, _, _ = child_setup(app)
    pet, wishlist = add_pet(owner, household["id"])
    member = app.test_client()
    member_data = register(member, "Family member", "pet-member@example.com")

    with app.app_context():
        membership = HouseholdMembership(
            household_id=household["id"],
            user_id=member_data["id"],
            role="profile_manager",
            is_family_member=True,
        )
        db.session.add(membership)
        db.session.commit()

    pet_profile = member.get(f"/api/profiles/{pet['id']}").get_json()["profile"]
    assert pet_profile["can_add"] is True
    assert pet_profile["can_remove_wishes"] is True
    added = mutate(member, "POST", f"/api/wishlists/{wishlist['id']}/items", {
        "name": "Pet toy",
    })
    assert added.status_code == 201, added.get_json()
    assert mutate(member, "DELETE", f"/api/items/{added.get_json()['item']['id']}").status_code == 200

    person_item = mutate(owner, "POST", f"/api/wishlists/{lists[0]['id']}/items", {
        "name": "Child's puzzle",
    }).get_json()["item"]
    assert mutate(member, "DELETE", f"/api/items/{person_item['id']}").status_code == 404


def test_pet_wishlist_is_hidden_from_invited_shoppers_until_enabled(app):
    owner = app.test_client()
    shopper = app.test_client()
    register(owner, "Pet owner", "pet-owner@example.com")
    shopper_user = register(shopper, "Shopper", "pet-shopper@example.com")
    household = mutate(owner, "POST", "/api/households", {"name": "Pet family"}).get_json()["household"]
    pet, wishlist = add_pet(owner, household["id"])
    item = mutate(owner, "POST", f"/api/wishlists/{wishlist['id']}/items", {
        "name": "Cat tree",
    }).get_json()["item"]

    with app.app_context():
        membership = HouseholdMembership(
            household_id=household["id"],
            user_id=shopper_user["id"],
            role="shopper",
        )
        db.session.add(membership)
        db.session.flush()
        db.session.add(HouseholdMemberProfileAccess(
            membership_id=membership.id,
            profile_id=pet["id"],
            can_edit=False,
        ))
        db.session.commit()

    assert shopper.get(f"/api/wishlists/{wishlist['id']}/items").get_json()["items"] == []
    assert mutate(shopper, "POST", f"/api/items/{item['id']}/reservations", {"quantity": 1}).status_code == 404
    enabled = mutate(owner, "PATCH", f"/api/profiles/{pet['id']}", {"share_wishlist": True})
    assert enabled.status_code == 200, enabled.get_json()
    assert shopper.get(f"/api/wishlists/{wishlist['id']}/items").get_json()["items"][0]["name"] == "Cat tree"
    assert mutate(shopper, "POST", f"/api/items/{item['id']}/reservations", {"quantity": 1}).status_code == 201


def test_list_sharing_applies_to_existing_and_future_pet_wishes(app):
    owner = app.test_client()
    shopper = app.test_client()
    register(owner, "Owner", "list-owner@example.com")
    shopper_user = register(shopper, "Shopper", "list-shopper@example.com")
    home = mutate(owner, "POST", "/api/households", {"name": "Family"}).get_json()["household"]
    pet, wishlist = add_pet(owner, home["id"])
    with app.app_context():
        membership = HouseholdMembership(household_id=home["id"], user_id=shopper_user["id"], role="shopper")
        db.session.add(membership)
        db.session.flush()
        db.session.add(HouseholdMemberProfileAccess(membership_id=membership.id, profile_id=pet["id"], can_edit=False))
        db.session.commit()
    endpoint = f"/api/wishlists/{wishlist['id']}"
    first = mutate(owner, "POST", endpoint + "/items", {"name": "Bed"}).get_json()["item"]
    assert mutate(owner, "PATCH", endpoint, {"share_publicly": True}).status_code == 200
    assert len(shopper.get(endpoint + "/items").get_json()["items"]) == 1
    mutate(owner, "POST", endpoint + "/items", {"name": "Toy"})
    assert len(shopper.get(endpoint + "/items").get_json()["items"]) == 2
    assert mutate(shopper, "PATCH", endpoint, {"share_publicly": False}).status_code == 404
    assert mutate(owner, "PATCH", endpoint, {"share_publicly": "yes"}).status_code == 400
    held = mutate(shopper, "POST", f"/api/items/{first['id']}/reservations", {"quantity":1})
    assert held.status_code == 201
    assert mutate(owner, "PATCH", endpoint, {"share_publicly": False}).status_code == 200
    assert shopper.get(f"/api/profiles/{pet['id']}/wishlists").get_json()["wishlists"] == []
    with app.app_context():
        assert db.session.get(GiftReservation, held.get_json()["reservation"]["id"]).status == 'cancelled'
    assert shopper.get(endpoint + "/items").get_json()["items"] == []
    assert len(owner.get(endpoint + "/items").get_json()["items"]) == 2
    assert mutate(shopper, "POST", f"/api/items/{first['id']}/reservations", {"quantity": 1}).status_code == 404


def test_pets_are_not_login_profiles_and_can_be_removed_from_family(app):
    owner = app.test_client()
    register(owner, "Owner", "remove-pet@example.com")
    home = mutate(owner, "POST", "/api/households", {"name": "Family"}).get_json()["household"]
    pet, _ = add_pet(owner, home["id"])
    assert pet["id"] not in [p["id"] for p in owner.get("/api/household-session").get_json()["profiles"]]
    assert mutate(owner, "POST", "/api/household-session/switch", {"profile_id": pet["id"]}).status_code == 400
    assert mutate(owner, "DELETE", f"/api/households/{home['id']}/profiles/{pet['id']}/member").status_code == 200
    assert pet["id"] not in [p["id"] for p in owner.get(f"/api/households/{home['id']}").get_json()["profiles"]]
