"""Shared sessions and fixed-window limits on the existing application database."""
import hashlib
import math
import time
from flask_session.base import ServerSideSessionInterface
from limits.storage import Storage
from sqlalchemy import delete, select, case
from sqlalchemy.exc import SQLAlchemyError
from .extensions import db
from .models import AppSession, RequestLimit


def digest(key):
    return hashlib.sha256(key.encode()).hexdigest()


def upsert(connection, table, values, updates):
    if connection.dialect.name == 'mysql':
        from sqlalchemy.dialects.mysql import insert
        statement = insert(table).values(**values).on_duplicate_key_update(list(updates.items()))
    elif connection.dialect.name == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
        statement = insert(table).values(**values).on_conflict_do_update(index_elements=['key_hash'], set_=updates)
    else:
        raise RuntimeError('Database session storage supports MySQL and SQLite.')
    connection.execute(statement)


class DatabaseSessionInterface(ServerSideSessionInterface):
    ttl = False

    def __init__(self, app):
        super().__init__(app, key_prefix='session:', permanent=True, cleanup_n_requests=100)

    def _retrieve_session_data(self, store_id):
        table = AppSession.__table__
        with db.engine.begin() as connection:
            row = connection.execute(select(table.c.data).where(table.c.key_hash == digest(store_id), table.c.expires_at > time.time())).first()
        return self.serializer.decode(row.data) if row else None

    def _delete_session(self, store_id):
        with db.engine.begin() as connection:
            connection.execute(delete(AppSession).where(AppSession.key_hash == digest(store_id)))

    def _upsert_session(self, session_lifetime, session, store_id):
        values = dict(key_hash=digest(store_id), data=self.serializer.encode(session),
                      expires_at=math.ceil(time.time() + session_lifetime.total_seconds()))
        with db.engine.begin() as connection:
            upsert(connection, AppSession.__table__, values, {key: values[key] for key in ('data', 'expires_at')})

    def _delete_expired_sessions(self):
        cleanup_state()


def cleanup_state():
    with db.engine.begin() as connection:
        now = time.time()
        connection.execute(delete(AppSession).where(AppSession.expires_at <= now))
        connection.execute(delete(RequestLimit).where(RequestLimit.expires_at <= now))


class DatabaseLimitStorage(Storage):
    STORAGE_SCHEME = ['appsql']

    @property
    def base_exceptions(self):
        return SQLAlchemyError

    def incr(self, key, expiry, amount=1):
        table = RequestLimit.__table__
        now = time.time()
        end = math.ceil(now + expiry)
        expired = table.c.expires_at <= now
        with db.engine.begin() as connection:
            upsert(connection, table, dict(key_hash=digest(key), value=amount, expires_at=end),
                   dict(value=case((expired, amount), else_=table.c.value + amount),
                        expires_at=case((expired, end), else_=table.c.expires_at)))
            return connection.execute(select(table.c.value).where(table.c.key_hash == digest(key))).scalar_one()

    def get(self, key):
        table = RequestLimit.__table__
        with db.engine.connect() as connection:
            return connection.execute(select(table.c.value).where(table.c.key_hash == digest(key), table.c.expires_at > time.time())).scalar() or 0

    def get_expiry(self, key):
        table = RequestLimit.__table__
        with db.engine.connect() as connection:
            return connection.execute(select(table.c.expires_at).where(table.c.key_hash == digest(key))).scalar() or time.time()

    def check(self):
        with db.engine.connect() as connection:
            connection.execute(select(RequestLimit.key_hash).limit(1))
        return True

    def clear(self, key):
        with db.engine.begin() as connection:
            connection.execute(delete(RequestLimit).where(RequestLimit.key_hash == digest(key)))

    def reset(self):
        with db.engine.begin() as connection:
            return connection.execute(delete(RequestLimit)).rowcount
