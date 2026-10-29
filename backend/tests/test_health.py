from pathlib import Path
import shutil
from uuid import uuid4

from backend.app import normalize_database_url


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_api_index(client):
    response = client.get("/api/")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Family Gift Registry API"


def test_readiness_returns_503_for_missing_production_migrations(client, app):
    assert client.get('/ready').get_json() == {'status':'ready'}
    app.config['APP_ENV']='production'
    response=client.get('/ready')
    assert response.status_code==503
    assert response.get_json()=={'status':'unavailable'}


def test_api_responses_cannot_be_cached_by_a_shared_proxy(client):
    response=client.get('/api/auth/me')
    assert response.headers['Cache-Control']=='no-store'
    assert 'Cookie' in response.headers['Vary']
    assert response.headers['X-Content-Type-Options']=='nosniff'


def test_mysql_urls_use_the_installed_pymysql_driver():
    assert normalize_database_url("mysql://user:password@db.example:3306/family") == (
        "mysql+pymysql://user:password@db.example:3306/family"
    )
    existing_driver = "mysql+pymysql://user:password@db.example:3306/family"
    assert normalize_database_url(existing_driver) == existing_driver


def test_docker_frontend_serves_spa_routes_and_assets(client, app):
    frontend = Path(app.instance_path) / f"frontend-test-{uuid4().hex}"
    assets = frontend / "assets"
    assets.mkdir(parents=True)
    app.config["FRONTEND_DIST"] = str(frontend)
    try:
        (frontend / "index.html").write_text("<main>Gather &amp; Gift</main>", encoding="utf-8")
        (assets / "app.js").write_text("window.ready = true;", encoding="utf-8")

        with client.get("/settings?tab=family") as page:
            assert page.status_code == 200
            assert b"Gather &amp; Gift" in page.data
        with client.get("/assets/app.js") as asset:
            assert asset.data == b"window.ready = true;"
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/api/not-a-route").get_json() == {"error": "Not found."}
    finally:
        shutil.rmtree(frontend)
