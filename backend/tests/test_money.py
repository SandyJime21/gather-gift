import io
import json

from backend.app import money
from backend.app.extensions import db
from backend.app.models import AdCampaign
from backend.tests.test_invitations_and_support import mutate, register


def master_client(app):
    result = app.test_cli_runner().invoke(
        args=["create-superuser"],
        input="boss@example.com\nBoss\nthe-boss-password-123\nthe-boss-password-123\n",
    )
    assert result.exit_code == 0, result.output
    client = app.test_client()
    assert mutate(client, "POST", "/api/auth/support/login", {
        "email": "boss@example.com", "password": "the-boss-password-123",
    }).status_code == 200
    return client


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_money_and_accounts_are_master_only_and_never_leak_keys(app, monkeypatch):
    app.config.update(
        STRIPE_SECRET_KEY="sk_test_supersecretvalue",
        STRIPE_WEBHOOK_SECRET="whsec_secret",
        AMAZON_ASSOCIATE_TAG="gather-20",
        STORE_AFFILIATE_RULES=json.dumps({"target.com": {"query": {"afid": "abc"}}}),
    )
    monkeypatch.setattr(money, "urlopen", lambda *a, **k: FakeResponse(json.dumps({
        "available": [{"currency": "usd", "amount": 12500}], "pending": [{"currency": "usd", "amount": 300}],
    }).encode()))
    db.session.add_all([
        AdCampaign(token_hash="a", data={"business_name": "Cake Co", "title": "Cakes", "email": "c@example.com"},
                   status="approved", amount_cents=5000, paid=True, payment_intent="pi_1"),
        AdCampaign(token_hash="b", data={"business_name": "Toy Co", "title": "Toys", "email": "t@example.com"},
                   status="approved", amount_cents=2000),
    ])
    db.session.commit()
    customer = app.test_client()
    register(customer, "Casey", "casey@example.com")
    assert customer.get("/api/support/money").status_code == 403
    assert customer.get("/api/support/users").status_code == 403

    master = master_client(app)
    response = master.get("/api/support/money")
    assert response.status_code == 200
    data = response.get_json()
    assert "supersecretvalue" not in response.get_data(as_text=True)
    assert "whsec_secret" not in response.get_data(as_text=True)
    assert data["stripe"]["mode"] == "test"
    assert data["stripe"]["reachable"] is True
    assert data["stripe"]["available"] == [{"currency": "usd", "amount_cents": 12500}]
    assert data["ads"]["paid_cents"] == 5000
    assert data["ads"]["awaiting_payment_cents"] == 2000
    stores = {row["host"]: row["configured"] for row in data["affiliates"]["stores"]}
    assert stores == {"amazon.com": True, "target.com": True, "walmart.com": False}

    users = master.get("/api/support/users?q=casey").get_json()
    assert [row["email"] for row in users["users"]] == ["casey@example.com"]
    assert users["users"][0]["kind"] == "member"
    assert "password_hash" not in json.dumps(users)


def test_money_reports_missing_stripe_configuration(app):
    app.config.update(STRIPE_SECRET_KEY="", STRIPE_WEBHOOK_SECRET="")
    data = master_client(app).get("/api/support/money").get_json()
    assert data["stripe"]["key_configured"] is False
    assert data["stripe"]["reachable"] is False
    assert "not set" in data["stripe"]["error"]
