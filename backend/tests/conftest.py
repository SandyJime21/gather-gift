import shutil
import os
from pathlib import Path
from uuid import uuid4

import pytest
from cachelib.file import FileSystemCache

from backend.app import create_app
from backend.app.extensions import db


@pytest.fixture()
def app():
    session_directory = (
        Path(__file__).resolve().parents[1]
        / "instance"
        / f"test-sessions-{uuid4().hex}"
    )
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SQLALCHEMY_ENGINE_OPTIONS": {},
            "RATELIMIT_ENABLED": False,
            "SESSION_TYPE": os.getenv('TEST_SESSION_BACKEND', 'cachelib'),
            "RATELIMIT_STORAGE_URI": 'appsql://' if os.getenv('TEST_SESSION_BACKEND') == 'mysql' else 'memory://',
            "SESSION_FILE_DIR": str(session_directory),
            "SESSION_CACHELIB": FileSystemCache(cache_dir=str(session_directory), threshold=500),
        }
    )
    try:
        with application.app_context():
            db.create_all()
            yield application
            db.session.remove()
            db.drop_all()
    finally:
        if session_directory.exists():
            shutil.rmtree(session_directory)


@pytest.fixture()
def client(app):
    return app.test_client()
