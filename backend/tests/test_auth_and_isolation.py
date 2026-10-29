from backend.app.extensions import db
from backend.app.models import HouseholdMemberProfileAccess, HouseholdMembership


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


def test_registration_login_and_csrf(client):
    response = mutate(client, "POST", "/api/auth/register", {
        "name": "Jamie",
        "email": "jamie@example.com",
        "password": "a-long-test-password",
    })
    assert response.status_code == 201
    assert response.get_json()["user"]["email"] == "jamie@example.com"
    assert client.get("/api/auth/me").status_code == 200

    logout = mutate(client, "POST", "/api/auth/logout")
    assert logout.status_code == 200
    login = mutate(client, "POST", "/api/auth/login", {
        "email": "jamie@example.com",
        "password": "a-long-test-password",
    })
    assert login.status_code == 200
    assert login.get_json()["user"]["name"] == "Jamie"


def test_mutation_requires_csrf(client):
    response = client.post("/api/households", json={"name": "Private household"})
    assert response.status_code == 400
    assert "CSRF" in response.get_json()["error"]


def test_household_access_is_scoped_to_membership(app):
    first = app.test_client()
    second = app.test_client()
    user = register(first, "Avery", "avery@example.com")
    household_response = mutate(first, "POST", "/api/households", {"name": "Avery household"})
    household_id = household_response.get_json()["household"]["id"]
    profile_response = mutate(first, "POST", f"/api/households/{household_id}/profiles", {
        "display_name": "Riley",
    })
    profile_id = profile_response.get_json()["profile"]["id"]

    register(second, "Morgan", "morgan@example.com")
    assert second.get(f"/api/profiles/{profile_id}").status_code == 404
    assert second.get(f"/api/households/{household_id}").status_code == 404
    assert user["email"] == "avery@example.com"


def test_household_creation_accepts_multiple_people_and_pets_with_birthdays(client):
    register(client, "Avery", "family@example.com")
    response = mutate(client, "POST", "/api/households", {
        "name": "Avery family",
        "profiles": [
            {"display_name": "Avery", "profile_type": "person", "birthday": "1990-05-14"},
            {"display_name": "Mochi", "profile_type": "pet", "birthday": "2020-08-02"},
        ],
    })
    assert response.status_code == 201, response.get_json()
    household_id = response.get_json()["household"]["id"]
    household = client.get(f"/api/households/{household_id}")
    assert household.status_code == 200, household.get_json()
    profiles = household.get_json()["profiles"]
    assert [(row["display_name"], row["profile_type"], row["birthday"]) for row in profiles] == [
        ("Avery", "person", "05-14"),
        ("Mochi", "pet", "08-02"),
    ]
    assert len(profiles) == 2
    assert all(row["can_edit"] for row in profiles)


def test_household_occasion_creation_adds_occasion_wishlist(client):
    register(client, "Avery", "occasions@example.com")
    household = mutate(client, "POST", "/api/households", {"name": "Avery family"}).get_json()["household"]
    profile = mutate(client, "POST", f"/api/households/{household['id']}/profiles", {
        "display_name": "Mochi",
        "profile_type": "pet",
    }).get_json()["profile"]
    response = mutate(client, "POST", f"/api/households/{household['id']}/occasions", {
        "profile_id": profile["id"],
        "name": "Mochi's Gotcha Day",
        "type": "other",
        "date": "2026-11-01",
    })
    assert response.status_code == 201, response.get_json()
    wishlists = client.get(f"/api/profiles/{profile['id']}/wishlists").get_json()["wishlists"]
    assert [row["title"] for row in wishlists] == ["Mochi's Gotcha Day wishes"]


def test_profile_managers_cannot_edit_profiles(client):
    owner = client
    manager = owner.application.test_client()
    owner_user = register(owner, "Avery", "parent@example.com")
    manager_user = register(manager, "Morgan", "manager@example.com")
    household = mutate(owner, "POST", "/api/households", {"name": "Avery family"}).get_json()["household"]
    profile = mutate(owner, "POST", f"/api/households/{household['id']}/profiles", {
        "display_name": "Riley",
    }).get_json()["profile"]
    with owner.application.app_context():
        membership = HouseholdMembership(
            household_id=household["id"],
            user_id=manager_user["id"],
            role="profile_manager",
        )
        db.session.add(membership)
        db.session.flush()
        db.session.add(HouseholdMemberProfileAccess(
            membership_id=membership.id,
            profile_id=profile["id"],
            can_edit=True,
        ))
        db.session.commit()
    assert mutate(manager, "PATCH", f"/api/profiles/{profile['id']}", {
        "display_name": "Changed",
    }).status_code == 404
    assert owner_user["email"] == "parent@example.com"
