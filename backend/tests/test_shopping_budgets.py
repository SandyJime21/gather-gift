from backend.tests.wishlist_setup import create_test_wishlist
from backend.app.extensions import db
from backend.app.models import HouseholdMembership
from backend.tests.test_reservation_privacy import register, mutate


def test_budget_filters_search_followed_people_and_exclude_unknown_prices_and_other_currencies(app):
    shopper = app.test_client()
    user = register(shopper, "Shopper", "budget-shopper@example.com")
    for index in range(2):
        owner = app.test_client()
        register(owner, "Parent", f"budget-owner-{index}@example.com")
        home = mutate(owner,"POST","/api/households",{"name":f"Budget family {index}","profiles":[{"display_name":f"Child {index}"}]}).json["household"]
        child = next(p for p in owner.get(f"/api/households/{home['id']}").json["profiles"] if p["display_name"] == f"Child {index}")
        wishlist = create_test_wishlist(owner, f"/api/profiles/{child['id']}/wishlists")
        for name, price, currency, private in [("Small puzzle",10,"USD",False),("At limit",50,"USD",False),("Free printable",0,"USD",False),("Expensive",100,"USD",False),("Unknown",None,"USD",False),("Euro",10,"EUR",False),("Private puzzle",10,"USD",True)]:
            response = mutate(owner,"POST",f"/api/wishlists/{wishlist['id']}/items",{"name":f"{name} {index}","estimated_price":price,"currency":currency,"family_only":private})
            assert response.status_code == 201
        with app.app_context():
            db.session.add(HouseholdMembership(household_id=home["id"],user_id=user["id"],role="shopper",share_all_profiles=True))
            db.session.commit()
    endpoint = "/api/shopping?scope=following"
    results = shopper.get(endpoint+"&max_price=50&currency=USD").json["items"]
    assert len(results) == 6
    assert all(row["estimated_price"] is not None and float(row["estimated_price"]) <= 50 and row["currency"] == "USD" for row in results)
    assert {row["recipient"] for row in results} == {"Child 0","Child 1"}
    assert len(shopper.get(endpoint+"&min_price=50&max_price=50").json["items"]) == 2
    assert len(shopper.get(endpoint+"&max_price=0").json["items"]) == 2
    assert len(shopper.get(endpoint+"&q=Small&max_price=25").json["items"]) == 2
    assert len(shopper.get(endpoint+"&q=Child%200&max_price=25").json["items"]) == 2
    all_prices = shopper.get(endpoint).json["items"]
    assert len(all_prices) == 12
    assert any(row["estimated_price"] is None for row in all_prices)
    for parameters in ("max_price=-1","max_price=NaN","max_price=Infinity","min_price=30&max_price=20","max_price=50&currency=invalid"):
        assert shopper.get(endpoint+"&"+parameters).status_code == 400


def test_wishlist_budget_tips_are_optional_persist_and_do_not_change_shopping_filters(app):
    client, other = app.test_client(), app.test_client()
    register(client,"Owner","budget-preference@example.com")
    register(other,"Other","budget-other@example.com")
    endpoint = "/api/wishlist-budget-preferences"
    assert client.get(endpoint).json["enabled"] is True
    assert mutate(client,"PATCH",endpoint,{"enabled":False}).json["enabled"] is False
    assert client.get("/api/auth/me").json["user"]["wishlist_budget_suggestions"] is False
    assert other.get(endpoint).json["enabled"] is True
    mutate(client,"PATCH","/api/notification-preferences",{"purchases":False})
    assert client.get(endpoint).json["enabled"] is False
    assert mutate(client,"PATCH",endpoint,{"enabled":"false"}).status_code == 400
    assert mutate(client,"PATCH",endpoint,{"enabled":True}).json["enabled"] is True
