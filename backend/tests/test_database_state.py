from concurrent.futures import ThreadPoolExecutor
import time
import pytest
from sqlalchemy import inspect, update, select
from backend.app import create_app
from backend.app.extensions import db
from backend.app.database_state import DatabaseLimitStorage, digest, cleanup_state
from backend.app.models import AppSession, RequestLimit
from backend.tests.test_reservation_privacy import register, mutate


def config(path):
    return dict(TESTING=True, APP_ENV='test', SECRET_KEY='state-test-secret',
                SQLALCHEMY_DATABASE_URI='sqlite:///'+str(path), SQLALCHEMY_ENGINE_OPTIONS={},
                SESSION_TYPE='mysql', RATELIMIT_STORAGE_URI='appsql://',
                RATELIMIT_ENABLED=True, RATELIMIT_STRATEGY='fixed-window')


@pytest.fixture
def state_app(tmp_path):
    app=create_app(config(tmp_path/'state.sqlite'))
    with app.app_context():
        assert inspect(db.engine).get_table_names()==[]  # Migrations own schema creation.
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def test_sessions_survive_another_worker_and_logout_revokes_cookie(state_app):
    client=state_app.test_client()
    register(client,'Parent','parent-state@example.com')
    cookie=client.get_cookie('session').value
    with state_app.app_context():
        stored=db.session.execute(select(AppSession)).scalars().all()
        assert stored and all(row.key_hash!=cookie for row in stored)
    second=create_app(config(state_app.config['SQLALCHEMY_DATABASE_URI'].removeprefix('sqlite:///')))
    other=second.test_client();other.set_cookie('session',cookie)
    assert other.get('/api/auth/me').json['user']['email']=='parent-state@example.com'
    assert mutate(client,'POST','/api/auth/logout',{}).status_code==200
    other.set_cookie('session',cookie)
    assert other.get('/api/auth/me').status_code==401
    with second.app_context():db.engine.dispose()


def test_expired_sessions_are_not_authenticated_and_cleanup_removes_expired_rows(state_app):
    client=state_app.test_client();register(client,'Parent','expiry-state@example.com')
    with db.engine.begin() as connection:
        connection.execute(update(AppSession).values(expires_at=0))
    assert client.get('/api/auth/me').status_code==401
    storage=DatabaseLimitStorage('appsql://');storage.incr('expired',10)
    with db.engine.begin() as connection:connection.execute(update(RequestLimit).values(expires_at=0))
    cleanup_state()
    assert RequestLimit.query.count()==0
    assert not db.session.execute(select(AppSession).where(AppSession.expires_at<=time.time())).first()


def test_counters_are_atomic_shared_and_expire(state_app):
    storage=DatabaseLimitStorage('appsql://')
    def hit(_):
        with state_app.app_context():return DatabaseLimitStorage('appsql://').incr('shared',60)
    with ThreadPoolExecutor(max_workers=6) as workers:
        assert sorted(workers.map(hit,range(24)))==list(range(1,25))
    assert storage.get('shared')==24
    expiry=storage.get_expiry('shared')
    assert storage.incr('shared',60,amount=2)==26
    assert storage.get_expiry('shared')==expiry
    with db.engine.begin() as connection:
        connection.execute(update(RequestLimit).where(RequestLimit.key_hash==digest('shared')).values(expires_at=0))
    assert storage.get('shared')==0
    assert storage.incr('shared',60)==1
    assert storage.check()
    storage.clear('shared');assert storage.get('shared')==0
    storage.incr('one',60);assert storage.reset()==1


def test_http_limits_are_enforced_and_session_ids_rotate_on_login(state_app):
    client=state_app.test_client()
    client.get('/api/auth/csrf')
    guest_cookie=client.get_cookie('session').value
    register(client,'Parent','rotation-state@example.com')
    assert client.get_cookie('session').value!=guest_cookie
    # Login endpoint is limited to ten attempts/minute, shared across clients.
    statuses=[]
    for _ in range(12):
        other=state_app.test_client()
        statuses.append(mutate(other,'POST','/api/auth/login',{'email':'none@example.com','password':'incorrect'}).status_code)
    assert 429 in statuses


def test_locked_child_and_parent_pin_work_with_database_sessions(state_app):
    from backend.tests.test_household_modes import test_child_mode_requires_pin_and_cannot_switch_or_escape_without_it
    test_child_mode_requires_pin_and_cannot_switch_or_escape_without_it(state_app)


def test_production_does_not_require_redis_or_connect_before_migrations():
    from backend.app.database_state import DatabaseSessionInterface
    app=create_app(dict(APP_ENV='production', SECRET_KEY='x'*48,
        SQLALCHEMY_DATABASE_URI='mysql+pymysql://u:p@db.example.com/gifts',
        FRONTEND_ORIGIN='https://gifts.example.com', SESSION_TYPE='redis',
        RATELIMIT_STORAGE_URI='redis://unavailable.example.com', SMTP_HOST='',MAIL_FROM=''))
    assert app.config['SESSION_TYPE']=='mysql'
    assert app.config['RATELIMIT_STORAGE_URI']=='appsql://'
    assert isinstance(app.session_interface,DatabaseSessionInterface)
    with app.app_context():db.engine.dispose()
