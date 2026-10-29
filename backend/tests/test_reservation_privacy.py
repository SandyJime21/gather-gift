from backend.app.extensions import db
from backend.app.models import (
    Household,
    HouseholdMemberProfileAccess,
    HouseholdMembership,
    HouseholdProfileAccess,
    Notification,
    PersonProfile,
    User,
    Wishlist,
    WishlistItem,
    WishlistItemWishlist,
)


def csrf(client):
    return client.get("/api/auth/csrf").get_json()["csrf_token"]


def mutate(client, method, path, payload=None):
    return client.open(
        path,
        method=method,
        json=payload,
        headers={"X-CSRF-Token": csrf(client)},
    )


def register(client, name, email):
    response = mutate(client, "POST", "/api/auth/register", {
        "name": name,
        "email": email,
        "password": "a-long-test-password",
    })
    assert response.status_code == 201
    return response.get_json()["user"]


def test_hold_status_visible_but_secret_buyer_identity_hidden(app):
    recipient = app.test_client()
    shopper = app.test_client()
    profile_manager = app.test_client()
    household_head = app.test_client()
    recipient_user = register(recipient, "Taylor", "taylor@example.com")
    shopper_user = register(shopper, "Jordan", "jordan@example.com")
    manager_user = register(profile_manager, "Casey", "casey@example.com")
    head_user = register(household_head, "Harper", "head@example.com")

    with app.app_context():
        household = Household(name="Taylor household", owner_id=recipient_user["id"])
        db.session.add(household)
        db.session.flush()
        db.session.add(HouseholdMembership(
            household_id=household.id,
            user_id=recipient_user["id"],
            role="owner",
        ))
        db.session.add(HouseholdMembership(
            household_id=household.id,
            user_id=head_user["id"],
            role="admin",
        ))
        shopper_membership = HouseholdMembership(
            household_id=household.id,
            user_id=shopper_user["id"],
            role="shopper",
        )
        db.session.add(shopper_membership)
        manager_membership = HouseholdMembership(
            household_id=household.id,
            user_id=manager_user["id"],
            role="profile_manager",
        )
        db.session.add(manager_membership)
        profile = PersonProfile(
            account_user_id=recipient_user["id"],
            display_name="Taylor",
            birthday_shared=False,
            parent_notes="Private family note.",
            items_to_avoid="Strong fragrances.",
        )
        db.session.add(profile)
        db.session.flush()
        db.session.add(HouseholdProfileAccess(
            household_id=household.id,
            profile_id=profile.id,
        ))
        db.session.flush()
        db.session.add_all([
            HouseholdMemberProfileAccess(
                membership_id=shopper_membership.id,
                profile_id=profile.id,
            ),
            HouseholdMemberProfileAccess(
                membership_id=manager_membership.id,
                profile_id=profile.id,
                can_edit=True,
            ),
        ])
        wishlist = Wishlist(profile_id=profile.id, title="Everyday", is_everyday=True)
        db.session.add(wishlist)
        db.session.flush()
        item = WishlistItem(
            profile_id=profile.id,
            created_by_id=recipient_user["id"],
            name="A little surprise",
            quantity=1,
        )
        db.session.add(item)
        db.session.flush()
        db.session.add(WishlistItemWishlist(item_id=item.id, wishlist_id=wishlist.id))
        db.session.commit()
        wishlist_id = wishlist.id
        item_id = item.id
        profile_id = profile.id

    reserved = mutate(shopper, "POST", f"/api/items/{item_id}/reservations", {"quantity": 1})
    assert reserved.status_code == 201

    recipient_items = recipient.get(f"/api/wishlists/{wishlist_id}/items").get_json()["items"]
    assert recipient_items[0]["availability"]["reserved"] == 1
    assert "reservations" not in recipient_items[0]
    recipient_profile = recipient.get(f"/api/profiles/{profile_id}").get_json()["profile"]
    assert recipient_profile["parent_notes"] == "Private family note."
    assert recipient_profile["birthday_shared"] is False

    shopper_profile = shopper.get(f"/api/profiles/{profile_id}").get_json()["profile"]
    assert shopper_profile["parent_notes"] is None
    assert shopper_profile["items_to_avoid"] is None
    assert shopper_profile["birthday"] is None
    manager_items = profile_manager.get(f"/api/wishlists/{wishlist_id}/items").get_json()["items"]
    assert manager_items[0]["availability"]["reserved"] == 1

    shopper_items = shopper.get(f"/api/wishlists/{wishlist_id}/items").get_json()["items"]
    assert shopper_items[0]["availability"] == {
        "reserved": 1,
        "purchased": 0,
        "available": 0,
        "held_by_you": True,
    }
    assert shopper.get("/api/my-shopping").get_json()["reservations"][0]["item"]["name"] == "A little surprise"
    reservation_id = reserved.get_json()["reservation"]["id"]
    purchased = mutate(shopper, "PATCH", f"/api/reservations/{reservation_id}", {"status": "purchased"})
    assert purchased.status_code == 200
    summary = recipient.get(f"/api/wishlists/{wishlist_id}/items").json["items"][0]["availability"]
    assert summary["purchased"] == 1 and "purchased_by" not in summary
    revealed = mutate(shopper, "PATCH", f"/api/reservations/{reservation_id}", {"status": "purchased", "purchase_secret": False})
    assert revealed.status_code == 200
    summary = recipient.get(f"/api/wishlists/{wishlist_id}/items").json["items"][0]["availability"]
    assert summary["purchased_by"] == ["Jordan"]
    assert recipient.get("/api/notifications").get_json()["notifications"] == []
    notifications = household_head.get("/api/notifications").get_json()["notifications"]
    assert len(notifications) == 1
    assert notifications[0]["item_name"] == "A little surprise"
    assert notifications[0]["profile_id"] == profile_id
    assert notifications[0]["wishlist_id"] == wishlist_id
    assert shopper.get("/api/notifications").get_json()["notifications"] == []
    assert mutate(household_head, "POST", f"/api/notifications/{notifications[0]['id']}/read", {}).status_code == 200
    with app.app_context():
        assert Notification.query.count() == 1


def test_item_cannot_be_reserved_over_available_quantity(app):
    recipient = app.test_client()
    shopper = app.test_client()
    recipient_user = register(recipient, "Taylor", "owner@example.com")
    shopper_user = register(shopper, "Jordan", "shopper@example.com")
    with app.app_context():
        household = Household(name="A household", owner_id=recipient_user["id"])
        db.session.add(household)
        db.session.flush()
        profile = PersonProfile(display_name="Casey")
        db.session.add(profile)
        db.session.flush()
        owner_membership = HouseholdMembership(household_id=household.id, user_id=recipient_user["id"], role="owner")
        shopper_membership = HouseholdMembership(household_id=household.id, user_id=shopper_user["id"], role="shopper")
        db.session.add_all([
            owner_membership,
            shopper_membership,
            HouseholdProfileAccess(household_id=household.id, profile_id=profile.id),
        ])
        db.session.flush()
        db.session.add(HouseholdMemberProfileAccess(
            membership_id=shopper_membership.id,
            profile_id=profile.id,
        ))
        item = WishlistItem(profile_id=profile.id, name="One item", quantity=1)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    assert mutate(shopper, "POST", f"/api/items/{item_id}/reservations", {"quantity": 1}).status_code == 201
    conflict = mutate(shopper, "POST", f"/api/items/{item_id}/reservations", {"quantity": 1})
    assert conflict.status_code == 409
