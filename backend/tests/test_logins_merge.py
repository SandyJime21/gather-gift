from backend.app.extensions import db
from backend.app.models import HouseholdMembership, Household, PersonProfile, User
from backend.tests.test_invitations_and_support import mutate, register


def test_support_can_merge_adult_login_back_into_requesters_login(app):
    owner = app.test_client()
    adult = app.test_client()
    support = app.test_client()
    owner_user = register(owner, "Avery", "avery@example.com")
    adult_user = register(adult, "Sam", "sam@example.com")
    household = mutate(owner, "POST", "/api/households", {"name": "Avery family"}).get_json()["household"]
    profile = mutate(owner, "POST", f"/api/households/{household['id']}/profiles", {"display_name": "Sam"}).get_json()["profile"]

    # Sam has taken ownership with their own login.
    with app.app_context():
        row = db.session.get(PersonProfile, profile["id"])
        row.is_adult = True
        row.account_user_id = adult_user["id"]
        row.member_email = "sam@example.com"
        db.session.get(Household, household["id"]).owner_id = adult_user["id"]
        db.session.add(HouseholdMembership(household_id=household["id"], user_id=adult_user["id"], role="owner"))
        db.session.query(HouseholdMembership).filter_by(household_id=household["id"], user_id=owner_user["id"]).one().role = "admin"
        staff = User(name="Support", email="support@example.com", is_support=True, is_superuser=True)
        staff.set_password("a-separate-strong-support-password")
        db.session.add(staff)
        db.session.commit()

    entry = next(p for p in owner.get("/api/household-session").get_json()["profiles"] if p["id"] == profile["id"])
    assert entry["uses_separate_login"] is True
    assert mutate(owner, "POST", "/api/household-session/switch", {"profile_id": profile["id"]}).status_code == 403

    ticket = mutate(owner, "POST", "/api/support/tickets", {
        "subject": "[Merge logins] Put us back together", "description": "Please merge Sam.", "category": "help",
    }).get_json()["ticket"]
    assert owner.get(f"/api/support/tickets/{ticket['id']}/merge-candidates").status_code == 403

    assert mutate(support, "POST", "/api/auth/support/login", {
        "email": "support@example.com", "password": "a-separate-strong-support-password",
    }).status_code == 200
    candidates = support.get(f"/api/support/tickets/{ticket['id']}/merge-candidates").get_json()["candidates"]
    assert [c["profile_id"] for c in candidates] == [profile["id"]]
    assert candidates[0]["login_email"] == "sam@example.com"

    path = f"/api/support/tickets/{ticket['id']}/merge-login"
    assert mutate(support, "POST", path, {"profile_id": profile["id"]}).status_code == 400
    assert mutate(support, "POST", path, {"profile_id": 999999, "confirmed": True}).status_code == 404
    assert mutate(support, "POST", path, {"profile_id": profile["id"], "confirmed": True}).status_code == 200

    with app.app_context():
        row = db.session.get(PersonProfile, profile["id"])
        assert row.account_user_id == owner_user["id"]
        assert row.member_email == "sam@example.com"
        assert db.session.get(Household, household["id"]).owner_id == owner_user["id"]
        assert HouseholdMembership.query.filter_by(household_id=household["id"], user_id=adult_user["id"]).count() == 0
        assert HouseholdMembership.query.filter_by(household_id=household["id"], user_id=owner_user["id"]).one().role == "owner"
    assert support.get(f"/api/support/tickets/{ticket['id']}/merge-candidates").get_json()["candidates"] == []
