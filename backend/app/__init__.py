import os
from pathlib import Path
from datetime import timedelta

import click
from flask import Flask, jsonify, send_from_directory, request
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
from flask_session import Session
from cachelib.file import FileSystemCache

from .extensions import limiter, migrate, db


def normalize_database_url(database_url):
    if database_url.startswith("mysql://"):
        return "mysql+pymysql://" + database_url[len("mysql://"):]
    return database_url


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        instance_path=str(Path(__file__).resolve().parents[1] / "instance"),
    )
    app.config.from_mapping(
        APP_ENV=os.getenv("APP_ENV", "development"),
        SECRET_KEY=os.getenv("SECRET_KEY", "local-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://gift_registry:gift_registry_dev@127.0.0.1:3306/family_gifts?charset=utf8mb4",
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("APP_ENV") == "production",
        SESSION_TYPE=os.getenv("SESSION_TYPE", "mysql" if os.getenv("APP_ENV") == "production" else "cachelib"),
        SESSION_FILE_DIR=str(Path(__file__).resolve().parents[1] / "instance" / "sessions"),
        SESSION_USE_SIGNER=False,
        SESSION_PERMANENT=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        RATELIMIT_STORAGE_URI=os.getenv("RATELIMIT_STORAGE_URI", "appsql://" if os.getenv("APP_ENV") == "production" else "memory://"),
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH", 8 * 1024 * 1024)),
        STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY", ""),
        STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        ADS_DAILY_RATE_CENTS=os.getenv("ADS_DAILY_RATE_CENTS", "0"),
        ADS_WISHLIST_DAILY_RATE_CENTS=os.getenv("ADS_WISHLIST_DAILY_RATE_CENTS", ""),
        ADS_FOLLOWING_DAILY_RATE_CENTS=os.getenv("ADS_FOLLOWING_DAILY_RATE_CENTS", ""),
        ADS_DISCOVER_DAILY_RATE_CENTS=os.getenv("ADS_DISCOVER_DAILY_RATE_CENTS", ""),
        SERPAPI_API_KEY=os.getenv("SERPAPI_API_KEY", ""),
        PERMITTED_METADATA_DOMAINS=os.getenv('PERMITTED_METADATA_DOMAINS',''),
        EBAY_CLIENT_ID=os.getenv('EBAY_CLIENT_ID',''),
        EBAY_CLIENT_SECRET=os.getenv('EBAY_CLIENT_SECRET',''),
        EBAY_ENVIRONMENT=os.getenv('EBAY_ENVIRONMENT','production'),
        EBAY_MARKETPLACE_ID=os.getenv('EBAY_MARKETPLACE_ID','EBAY_US'),
        EBAY_AFFILIATE_CAMPAIGN_ID=os.getenv('EBAY_AFFILIATE_CAMPAIGN_ID',''),
        STORE_AFFILIATE_RULES=os.getenv("STORE_AFFILIATE_RULES", "{}"),
        AMAZON_ASSOCIATE_TAG=os.getenv("AMAZON_ASSOCIATE_TAG", ""),
        SMTP_HOST=os.getenv("SMTP_HOST", ""),
        SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
        SMTP_USERNAME=os.getenv("SMTP_USERNAME", ""),
        SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
        SMTP_STARTTLS=os.getenv("SMTP_STARTTLS", "true").lower() == "true",
        MAIL_FROM=os.getenv("MAIL_FROM", ""),
        FRONTEND_ORIGIN=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        UPLOAD_FOLDER=os.getenv(
            "UPLOAD_FOLDER",
            str(Path(__file__).resolve().parents[1] / "instance" / "uploads"),
        ),
    )
    from .commerce_adapters import PROVIDERS as commerce_providers
    app.config.update({key:os.getenv(key,'') for provider in commerce_providers.values() for key in provider['env']})
    if test_config:
        app.config.update(test_config)

    app.config.setdefault("FRONTEND_DIST", str(Path(__file__).resolve().parents[2] / "frontend"))
    app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_url(app.config["SQLALCHEMY_DATABASE_URI"])
    if not test_config and not os.getenv("FRONTEND_ORIGIN") and os.getenv("RENDER_EXTERNAL_URL"):
        app.config["FRONTEND_ORIGIN"] = os.environ["RENDER_EXTERNAL_URL"]

    from .production import validate_production
    validate_production(app.config)
    from .database_tls import mysql_engine_options
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        **app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}),
        **mysql_engine_options(app.config['SQLALCHEMY_DATABASE_URI'],
            production=app.config['APP_ENV'] == 'production', ca_file=os.getenv('DATABASE_SSL_CA') or None),
    }

    # Save and serve uploads from the same absolute directory. Flask resolves
    # relative send_from_directory paths against app.root_path, unlike Path.write_bytes.
    app.config["UPLOAD_FOLDER"] = str(Path(app.config["UPLOAD_FOLDER"]).resolve())

    if os.getenv("APP_ENV") == "production" and not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be configured in production.")
    # Existing Render deployments can retain old Redis env vars until Blueprint sync.
    # Production now always shares sessions and limits through the application DB.
    if app.config['APP_ENV'] == 'production':
        app.config['SESSION_TYPE'] = 'mysql'
        app.config['RATELIMIT_STORAGE_URI'] = 'appsql://'
        app.config['RATELIMIT_STRATEGY'] = 'fixed-window'
    if app.config["SESSION_TYPE"] == "cachelib" and not app.config.get("SESSION_CACHELIB"):
        app.config["SESSION_CACHELIB"] = FileSystemCache(
            cache_dir=app.config["SESSION_FILE_DIR"],
            threshold=500,
        )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["SESSION_FILE_DIR"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migration_directory = Path(__file__).resolve().parents[1] / "migrations"
    migrate.init_app(app, db, directory=str(migration_directory))
    from .database_state import DatabaseSessionInterface  # Register shared SQL limiter storage.
    limiter.init_app(app)
    if app.config['SESSION_TYPE'] == 'mysql':
        app.session_interface = DatabaseSessionInterface(app)
    else:
        Session(app)

    CORS(
        app,
        supports_credentials=True,
        origins=[app.config["FRONTEND_ORIGIN"]],
        allow_headers=["Content-Type", "X-CSRF-Token"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    from . import models  # noqa: F401
    from .api import api
    from . import adult_family  # Register linked-adult routes before the blueprint.

    from . import wishlist_letters  # Register parent-managed letter routes.
    from . import account_deletion  # Register previewed account deletion.
    from . import letter_art  # Register design catalog and family unlocks.
    from . import preference_search  # Optional public suggestions for manual favorites.
    from . import child_controls  # Parent-owned optional child permissions.
    from . import batch_wishlists  # Create matching lists for several family members.
    from . import wishlist_price_requests
    from . import email_preferences
    from . import email_control
    from . import universal_gifts
    from . import commerce
    app.register_blueprint(api, url_prefix="/api")
    from .advertising import ad_api
    app.register_blueprint(ad_api, url_prefix="/api")
    from .money import money_api
    app.register_blueprint(money_api, url_prefix="/api")
    from .gift_games import game_api
    from . import game_email_invites
    app.register_blueprint(game_api, url_prefix="/api")
    from .sample_emails import register as register_sample_emails
    register_sample_emails(app)

    @app.cli.command("create-superuser")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    def create_superuser(email, name):
        from email_validator import EmailNotValidError, validate_email

        from .models import User

        if User.query.filter_by(is_superuser=True).first():
            raise click.ClickException(
                "A master support account already exists. Ask its owner to invite staff."
            )
        try:
            normalized = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError as exc:
            raise click.ClickException("Enter a valid email address.") from exc
        if not name.strip() or len(name.strip()) > 120:
            raise click.ClickException("Name is required and must be at most 120 characters.")
        if User.query.filter_by(email=normalized).first():
            raise click.ClickException("An account with that email already exists.")
        password = click.prompt("Master password", hide_input=True, confirmation_prompt=True)
        if len(password) < 16:
            raise click.ClickException("Master passwords must be at least 16 characters.")
        user = User(name=name.strip(), email=normalized, is_support=True, is_superuser=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created master support account for {normalized}.")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path):
        frontend_directory = Path(app.config["FRONTEND_DIST"])
        if not (frontend_directory / "index.html").is_file():
            return jsonify({"error": "Not found."}), 404
        if path in {"api", "health"} or path.startswith("api/"):
            return jsonify({"error": "Not found."}), 404
        target = (frontend_directory / path).resolve()
        try:
            target.relative_to(frontend_directory.resolve())
        except ValueError:
            return jsonify({"error": "Not found."}), 404
        if path and target.is_file():
            return send_from_directory(frontend_directory, path)
        if path.startswith("assets/"):
            return jsonify({"error": "Not found."}), 404
        return send_from_directory(frontend_directory, "index.html")

    @app.after_request
    def response_privacy(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if request.path.startswith('/api/') and response.is_json:
            response.headers['Cache-Control'] = 'no-store'
            response.vary.add('Cookie')
        if app.config['APP_ENV'] == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(exception):
        return jsonify({"error": exception.description}), exception.code

    @app.get('/ready')
    def readiness():
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError
        from alembic.script import ScriptDirectory
        try:
            db.session.execute(text('SELECT 1'))
            if app.config['APP_ENV'] == 'production':
                expected = set(ScriptDirectory(str(migration_directory)).get_heads())
                actual = set(db.session.execute(text('SELECT version_num FROM alembic_version')).scalars())
                if actual != expected:
                    return jsonify(status='unavailable'), 503
                from .models import AppSession, RequestLimit
                db.session.execute(db.select(AppSession.key_hash).limit(1))
                db.session.execute(db.select(RequestLimit.key_hash).limit(1))
        except (SQLAlchemyError, OSError):
            db.session.rollback()
            return jsonify(status='unavailable'), 503
        return jsonify(status='ready')

    @app.errorhandler(Exception)
    def handle_unexpected_error(exception):
        db.session.rollback()
        app.logger.exception("Unhandled application error")
        return jsonify({"error": "An unexpected server error occurred. Please try again."}), 500

    return app
