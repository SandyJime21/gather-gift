from backend.tests.wishlist_setup import create_test_wishlist
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
import shutil
from uuid import uuid4

from backend.app.extensions import db
from backend.app.models import (
    AuditLog,
    Household,
    HouseholdInvitation,
    HouseholdMembership,
    HouseholdProfileAccess,
    PersonProfile,
    SupportAccessGrant,
    User,
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
    assert response.status_code == 201, response.get_json()
    return response.get_json()["user"]


def test_invitation_grants_only_selected_profiles(app):
    owner = app.test_client()
    shopper = app.test_client()
    owner_user = register(owner, "Avery", "avery@example.com")
    shopper_user = register(shopper, "Sam", "sam@example.com")
    household = mutate(owner, "POST", "/api/households", {"name": "Avery family"}).get_json()["household"]
    first = mutate(owner, "POST", f"/api/households/{household['id']}/profiles", {
        "display_name": "Jordan",
    }).get_json()["profile"]
    second = mutate(owner, "POST", f"/api/households/{household['id']}/profiles", {
        "display_name": "Casey",
    }).get_json()["profile"]
    for profile, gift_name in ((first, "Jordan's book"), (second, "Casey's puzzle")):
        wishlist = create_test_wishlist(owner, f"/api/profiles/{profile['id']}/wishlists")
        gift = mutate(owner, "POST", f"/api/wishlists/{wishlist['id']}/items", {
            "name": gift_name,
        })
        assert gift.status_code == 201, gift.get_json()

    invitation_response = mutate(owner, "POST", f"/api/households/{household['id']}/invitations", {
        "email": shopper_user["email"],
        "role": "shopper",
        "profile_ids": [first["id"]],
    })
    assert invitation_response.status_code == 201, invitation_response.get_json()
    invitation = invitation_response.get_json()["invitation"]
    assert invitation["profile_ids"] == [first["id"]]

    assert shopper.get(f"/api/profiles/{first['id']}").status_code == 404
    assert mutate(shopper, "POST", "/api/invitations/accept", {"token": invitation["token"]}).status_code == 200
    shared_profile = shopper.get(f"/api/profiles/{first['id']}")
    assert shared_profile.status_code == 200
    assert shared_profile.get_json()["profile"]["can_edit"] is False
    assert mutate(shopper, "PATCH", f"/api/profiles/{first['id']}", {
        "display_name": "Unauthorized edit",
    }).status_code == 404
    assert shopper.get(f"/api/profiles/{second['id']}").status_code == 404
    assert shopper.get(f"/api/households/{household['id']}").get_json()["profiles"][0]["id"] == first["id"]
    shopping_items = shopper.get("/api/shopping").get_json()["items"]
    assert [item["name"] for item in shopping_items] == ["Jordan's book"]

    with app.app_context():
        assert db.session.get(User, owner_user["id"]) is not None
        access = HouseholdProfileAccess.query.filter_by(
            household_id=household["id"],
            profile_id=first["id"],
        ).one()
        assert access.can_edit is True


def test_support_login_requires_separate_portal_and_owner_consent(app):
    owner = app.test_client()
    support = app.test_client()
    owner_user = register(owner, "Taylor", "taylor@example.com")
    household = mutate(owner, "POST", "/api/households", {"name": "Taylor family"}).get_json()["household"]
    profile = mutate(owner, "POST", f"/api/households/{household['id']}/profiles", {
        "display_name": "Mia",
    }).get_json()["profile"]

    runner = app.test_cli_runner()
    command = runner.invoke(
        args=["create-superuser"],
        input=(
            "support@example.com\n"
            "Support Agent\n"
            "a-separate-strong-support-password\n"
            "a-separate-strong-support-password\n"
        ),
    )
    assert command.exit_code == 0, command.output
    with app.app_context():
        staff = User.query.filter_by(email="support@example.com").one()
        staff_id = staff.id
        assert staff.is_support is True
        assert staff.is_superuser is True
        assert HouseholdMembership.query.filter_by(user_id=staff.id).count() == 0

    family_login = mutate(support, "POST", "/api/auth/login", {
        "email": "support@example.com",
        "password": "a-separate-strong-support-password",
    })
    assert family_login.status_code == 403
    assert mutate(support, "POST", "/api/auth/support/login", {
        "email": "support@example.com",
        "password": "a-separate-strong-support-password",
    }).status_code == 200
    assert support.get("/api/auth/me").get_json()["households"] == []
    assert support.get(f"/api/profiles/{profile['id']}").status_code == 403
    ticket = mutate(owner, "POST", "/api/support/tickets", {
        "subject": "Profile help",
        "description": "Please help with a profile setting.",
        "category": "help",
    }).get_json()["ticket"]
    assert len(support.get("/api/support/tickets").get_json()["tickets"]) == 1
    reply = mutate(support, "POST", f"/api/support/tickets/{ticket['id']}/messages", {
        "message": "We can help with that setting.",
    })
    assert reply.status_code == 200
    assert len(owner.get("/api/support/tickets").get_json()["tickets"][0]["messages"]) == 2

    assert mutate(owner, "POST", "/api/help/chat", {"question": "How do I reset my password?", "answer": "Use Forgot password."}).status_code == 201
    chats = support.get("/api/support/help-chats").get_json()["chats"]
    assert [m["sender"] for m in chats[0]["messages"]] == ["user", "bot"]
    assert owner.get("/api/support/help-chats").status_code == 403
    escalated = mutate(owner, "POST", "/api/help/chat/escalate", {"note": "Still stuck"})
    assert escalated.status_code == 201
    assert "How do I reset my password?" in escalated.get_json()["ticket"]["description"]
    assert "Still stuck" in escalated.get_json()["ticket"]["description"]
    request_response = mutate(support, "POST", "/api/support/access-requests", {
        "household_id": household["id"],
        "reason": "Investigate a customer-reported profile display issue.",
    })
    assert request_response.status_code == 201, request_response.get_json()
    request_id = request_response.get_json()["request"]["id"]
    assert support.get("/api/support/grants").get_json()["grants"] == []
    assert support.get("/api/support/grants/99999/snapshot").status_code == 403

    pending = owner.get(f"/api/support/access-requests?household_id={household['id']}")
    assert pending.status_code == 200
    assert pending.get_json()["requests"][0]["support_name"] == "Support Agent"
    approved = mutate(owner, "PATCH", f"/api/support/access-requests/{request_id}", {
        "decision": "approve",
    })
    assert approved.status_code == 200, approved.get_json()

    grants = support.get("/api/support/grants").get_json()["grants"]
    assert len(grants) == 1
    grant_id = grants[0]["id"]
    snapshot = support.get(f"/api/support/grants/{grant_id}/snapshot")
    assert snapshot.status_code == 200
    assert snapshot.get_json()["profiles"][0]["profile"]["display_name"] == "Mia"
    assert "grant_id" in snapshot.get_json()

    edited = mutate(support, "PATCH", f"/api/support/grants/{grant_id}/profiles/{profile['id']}", {
        "display_name": "Mia Updated",
    })
    assert edited.status_code == 200, edited.get_json()
    assert owner.get(f"/api/profiles/{profile['id']}").get_json()["profile"]["display_name"] == "Mia Updated"
    assert support.get("/api/support/audit-logs").get_json()["logs"]

    with app.app_context():
        grant = db.session.get(SupportAccessGrant, grant_id)
        grant.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
    assert support.get(f"/api/support/grants/{grant_id}/snapshot").status_code == 403
    assert support.get(f"/api/households/{household['id']}").status_code == 403
    assert mutate(owner, "DELETE", f"/api/support/grants/{grant_id}").status_code == 200
    with app.app_context():
        assert AuditLog.query.filter_by(actor_id=staff_id, action="support.profile_edited").count() == 1
        assert AuditLog.query.filter_by(household_id=household["id"], action="support.access_revoked").count() == 1
        assert HouseholdMembership.query.filter_by(user_id=owner_user["id"]).count() == 1
    household_logs = owner.get(f"/api/households/{household['id']}/support-audit-logs")
    assert household_logs.status_code == 200
    assert any(row["action"] == "support.profile_edited" for row in household_logs.get_json()["logs"])


def test_support_can_prepare_family_for_email_and_transfer_ownership_on_claim(app):
    support = app.test_client()
    recipient = app.test_client()
    stranger = app.test_client()
    upload_folder = Path(app.instance_path) / f"family-setup-test-{uuid4().hex}"
    upload_folder.mkdir(parents=True)
    app.config["UPLOAD_FOLDER"] = str(upload_folder)
    runner = app.test_cli_runner()
    command = runner.invoke(
        args=["create-superuser"],
        input=(
            "setup-support@example.com\n"
            "Setup Support\n"
            "a-separate-strong-support-password\n"
            "a-separate-strong-support-password\n"
        ),
    )
    assert command.exit_code == 0, command.output
    with app.app_context():
        support_user = User.query.filter_by(email="setup-support@example.com").one()
        support_user_id = support_user.id
    login = mutate(support, "POST", "/api/auth/support/login", {
        "email": "setup-support@example.com",
        "password": "a-separate-strong-support-password",
    })
    assert login.status_code == 200

    created = support.post(
        "/api/support/family-setup-invitations",
        data={
            "email": "claim-family@example.com",
            "household_name": "The Rivera Family",
            "profile_name": "Alex Rivera",
            "birthday": "1990-07-23",
            "image": (BytesIO(b"\x89PNG\r\n\x1a\nfake-image-data"), "alex.png"),
        },
        headers={"X-CSRF-Token": csrf(support)},
    )
    assert created.status_code == 201, created.get_json()
    result = created.get_json()
    assert result["invitation"]["email"] == "claim-family@example.com"
    assert result["email_message"]["delivery"] == "not_configured"
    assert result["profile"]["display_name"] == "Alex Rivera"
    assert result["profile"]["birthday"] == "07-23"
    assert result["profile"]["photo_path"].startswith("/api/uploads/")
    with app.app_context():
        household = db.session.get(Household, result["household"]["id"])
        profile = db.session.get(PersonProfile, result["profile"]["id"])
        invitation = HouseholdInvitation.query.filter_by(
            transfer_owner_on_accept=True,
        ).one()
        assert household.owner_id == support_user_id
        assert profile.account_user_id is None
        assert profile.member_email == "claim-family@example.com"
        assert invitation.setup_created_by_id == support_user_id
        assert HouseholdMembership.query.filter_by(household_id=household.id).count() == 0
        assert (upload_folder / profile.photo_path.rsplit("/", 1)[-1]).exists()

    register(stranger, "Wrong Person", "wrong-person@example.com")
    unauthorized_setup = stranger.post(
        "/api/support/family-setup-invitations",
        data={
            "email": "other-invitee@example.com",
            "household_name": "Unauthorized Family",
            "profile_name": "Someone",
        },
        headers={"X-CSRF-Token": csrf(stranger)},
    )
    assert unauthorized_setup.status_code == 403
    wrong_email = mutate(stranger, "POST", "/api/invitations/accept", {
        "token": result["invitation"]["token"],
    })
    assert wrong_email.status_code == 403
    user = register(recipient, "Alex Rivera", "claim-family@example.com")
    assert recipient.get(f"/api/households/{result['household']['id']}").status_code == 404
    accepted = mutate(recipient, "POST", "/api/invitations/accept", {
        "token": result["invitation"]["token"],
    })
    assert accepted.status_code == 200, accepted.get_json()
    assert accepted.get_json()["joined_family"] is True
    family = recipient.get(f"/api/households/{result['household']['id']}")
    assert family.status_code == 200
    assert family.get_json()["household"]["owner_id"] == user["id"]
    assert family.get_json()["profiles"][0]["id"] == result["profile"]["id"]
    assert recipient.get(result["profile"]["photo_path"]).status_code == 200
    assert support.get(f"/api/households/{result['household']['id']}").status_code == 403
    assert mutate(recipient, "POST", "/api/invitations/accept", {
        "token": result["invitation"]["token"],
    }).status_code == 200
    with app.app_context():
        household = db.session.get(Household, result["household"]["id"])
        profile = db.session.get(PersonProfile, result["profile"]["id"])
        assert household.owner_id == user["id"]
        assert profile.account_user_id == user["id"]
        assert profile.is_guardian is True
        assert HouseholdMembership.query.filter_by(
            household_id=household.id,
            user_id=user["id"],
            role="owner",
        ).one()
        assert HouseholdMembership.query.filter_by(user_id=support_user_id).count() == 0
        assert AuditLog.query.filter_by(
            actor_id=support_user_id,
            action="support.family_setup_created",
            household_id=household.id,
        ).count() == 1
        assert AuditLog.query.filter_by(
            actor_id=user["id"],
            action="family.support_setup_claimed",
            household_id=household.id,
        ).count() == 1
    shutil.rmtree(upload_folder)


def test_only_master_can_invite_staff_and_invitation_is_single_use(app):
    runner = app.test_cli_runner()
    created = runner.invoke(
        args=["create-superuser"],
        input=(
            "master@example.com\n"
            "Master Agent\n"
            "a-very-strong-master-password\n"
            "a-very-strong-master-password\n"
        ),
    )
    assert created.exit_code == 0, created.output

    master = app.test_client()
    login = mutate(master, "POST", "/api/auth/support/login", {
        "email": "master@example.com",
        "password": "a-very-strong-master-password",
    })
    assert login.status_code == 200
    assert login.get_json()["user"]["is_superuser"] is True

    invitation_response = mutate(master, "POST", "/api/support/staff-invitations", {
        "email": "invited-staff@example.com",
    })
    assert invitation_response.status_code == 201, invitation_response.get_json()
    invitation = invitation_response.get_json()["invitation"]
    assert invitation["email"] == "invited-staff@example.com"
    assert len(master.get("/api/support/staff-invitations").get_json()["invitations"]) == 1

    staff = app.test_client()
    accepted = mutate(staff, "POST", "/api/auth/support/accept-invitation", {
        "token": invitation["token"],
        "name": "Invited Agent",
        "password": "an-invited-staff-password",
    })
    assert accepted.status_code == 201, accepted.get_json()
    assert accepted.get_json()["user"]["is_support"] is True
    assert accepted.get_json()["user"]["is_superuser"] is False
    assert staff.get("/api/support/tickets").status_code == 200

    customer = app.test_client()
    register(customer, "Casey", "casey@example.com")
    ticket = mutate(customer, "POST", "/api/support/tickets", {
        "subject": "Need help", "description": "Stuck on a thing.", "category": "help",
    }).get_json()["ticket"]
    assert staff.get("/api/support/tickets").get_json()["tickets"] == []
    assert mutate(staff, "PATCH", f"/api/support/tickets/{ticket['id']}", {"status": "closed"}).status_code == 404
    assert master.get("/api/support/staff").status_code == 200
    assert staff.get("/api/support/staff").status_code == 403
    staff_id = next(row["id"] for row in master.get("/api/support/staff").get_json()["staff"] if not row["is_superuser"])
    assert mutate(staff, "PATCH", f"/api/support/tickets/{ticket['id']}", {"assigned_to_id": staff_id}).status_code == 404
    assigned = mutate(master, "PATCH", f"/api/support/tickets/{ticket['id']}", {"assigned_to_id": staff_id})
    assert assigned.status_code == 200
    assert assigned.get_json()["ticket"]["assigned_to"]["id"] == staff_id
    mine = staff.get("/api/support/tickets").get_json()["tickets"]
    assert [row["id"] for row in mine] == [ticket["id"]]
    assert mine[0]["user_email"] == "casey@example.com"
    assert mutate(staff, "PATCH", f"/api/support/tickets/{ticket['id']}", {"status": "in_progress"}).status_code == 200
    assert mutate(staff, "POST", "/api/support/staff-invitations", {
        "email": "another-staff@example.com",
    }).status_code == 403
    assert mutate(app.test_client(), "POST", "/api/auth/support/accept-invitation", {
        "token": invitation["token"],
        "name": "Duplicate Agent",
        "password": "another-staff-password",
    }).status_code == 400
    assert master.get("/api/auth/support/register").status_code == 404

    second_master = runner.invoke(
        args=["create-superuser"],
        input="another-master@example.com\nAnother Master\n",
    )
    assert second_master.exit_code != 0
    assert "already exists" in second_master.output


def test_support_tickets_are_private_to_their_owner(app):
    customer = app.test_client()
    stranger = app.test_client()
    register(customer, "Taylor", "customer@example.com")
    register(stranger, "Morgan", "stranger@example.com")
    ticket = mutate(customer, "POST", "/api/support/tickets", {
        "subject": "Photo upload issue",
        "description": "The profile photo button does not save.",
        "category": "bug",
    })
    assert ticket.status_code == 201, ticket.get_json()
    ticket_id = ticket.get_json()["ticket"]["id"]
    assert len(customer.get("/api/support/tickets").get_json()["tickets"]) == 1
    assert stranger.get("/api/support/tickets").get_json()["tickets"] == []
    assert mutate(stranger, "POST", f"/api/support/tickets/{ticket_id}/messages", {
        "message": "I should not see this ticket.",
    }).status_code == 404


def test_unmatched_routes_return_json_error(app):
    def unexpected_failure():
        raise RuntimeError("internal detail")

    app.add_url_rule(
        "/api/test-unexpected-failure",
        view_func=unexpected_failure,
    )
    client = app.test_client()
    response = client.get("/api/not-a-real-route")
    assert response.status_code == 404
    assert response.get_json()["error"]

    failure = client.get("/api/test-unexpected-failure")
    assert failure.status_code == 500
    assert failure.get_json()["error"] == "An unexpected server error occurred. Please try again."
    assert "internal detail" not in failure.get_data(as_text=True)


def test_shopper_invitation_requires_selected_profiles(app):
    owner = app.test_client()
    register(owner, "Avery", "avery2@example.com")
    household = mutate(owner, "POST", "/api/households", {"name": "Another family"}).get_json()["household"]
    response = mutate(owner, "POST", f"/api/households/{household['id']}/invitations", {
        "email": "shopper@example.com",
        "role": "shopper",
        "profile_ids": [],
    })
    assert response.status_code == 400
