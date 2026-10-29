"""Run only against the explicitly named disposable GitHub Actions database."""
import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy.engine import make_url
from backend.app import create_app
from backend.app.extensions import db
from backend.app.database_state import DatabaseLimitStorage
from backend.tests.test_reservation_privacy import register, mutate


@pytest.fixture
def mysql_app():
    url=os.getenv('MYSQL_STATE_TEST_URL')
    if not url:pytest.skip('Disposable MySQL integration database not configured.')
    parsed=make_url(url)
    if parsed.host not in ('127.0.0.1','localhost') or parsed.database!='gather_gift_ci':
        pytest.fail('Integration tests require the disposable local gather_gift_ci database.')
    app=create_app(dict(TESTING=True,APP_ENV='test',SECRET_KEY='ci-state-test-secret',
        SQLALCHEMY_DATABASE_URI=url,SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping':True},
        SESSION_TYPE='mysql',RATELIMIT_STORAGE_URI='appsql://',RATELIMIT_ENABLED=False))
    with app.app_context():
        yield app
        db.session.remove()
        db.engine.dispose()


def test_mysql_atomic_counters_are_shared_across_connections(mysql_app):
    storage=DatabaseLimitStorage('appsql://');storage.clear('mysql-ci-concurrent')
    def hit(_):
        with mysql_app.app_context():return DatabaseLimitStorage('appsql://').incr('mysql-ci-concurrent',60)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sorted(pool.map(hit,range(40)))==list(range(1,41))
    assert storage.get('mysql-ci-concurrent')==40
    storage.clear('mysql-ci-concurrent')


def test_mysql_sessions_rotate_persist_and_logout(mysql_app):
    client=mysql_app.test_client()
    client.get('/api/auth/csrf');old=client.get_cookie('session').value
    register(client,'CI parent','ci-state@example.com')
    cookie=client.get_cookie('session').value
    assert cookie!=old
    second=mysql_app.test_client();second.set_cookie('session',cookie)
    assert second.get('/api/auth/me').json['user']['email']=='ci-state@example.com'
    assert mutate(client,'POST','/api/auth/logout',{}).status_code==200
    second.set_cookie('session',cookie)
    assert second.get('/api/auth/me').status_code==401
