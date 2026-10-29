import pytest


@pytest.fixture(autouse=True)
def deployed_frontend_origin(monkeypatch):
    monkeypatch.setenv('FRONTEND_ORIGIN','https://gather-gift.onrender.com')


def test_browser_requests_from_configured_frontend_allow_credentials(app):
    client=app.test_client()
    origin=app.config['FRONTEND_ORIGIN']
    assert origin=='https://gather-gift.onrender.com'
    response=client.options('/api/auth/login',headers={
        'Origin':origin,
        'Access-Control-Request-Method':'POST',
        'Access-Control-Request-Headers':'Content-Type,X-CSRF-Token',
    })
    assert response.headers['Access-Control-Allow-Origin']==origin
    assert response.headers['Access-Control-Allow-Credentials']=='true'
    assert 'X-CSRF-Token' in response.headers['Access-Control-Allow-Headers']


def test_unrelated_website_cannot_read_authenticated_api(app):
    response=app.test_client().get('/api/auth/csrf',headers={'Origin':'https://unrelated.example'})
    assert 'Access-Control-Allow-Origin' not in response.headers
