"""Verified MySQL TLS, including this deployment's private CA trust anchor."""
from pathlib import Path
import certifi
from sqlalchemy.engine import make_url


RAILWAY_DATABASE_HOST = 'tokaido.proxy.rlwy.net'
BUNDLED_CA = Path(__file__).resolve().parents[1] / 'certs' / 'railway-mysql-ca.crt'


def mysql_engine_options(database_url, production=False, ca_file=None):
    url = make_url(database_url)
    if url.drivername != 'mysql+pymysql':
        return {}
    options = {'pool_pre_ping': True, 'pool_recycle': 280, 'connect_args': {'connect_timeout': 10}}
    if production or ca_file or url.host == RAILWAY_DATABASE_HOST:
        ca = ca_file or (str(BUNDLED_CA) if url.host == RAILWAY_DATABASE_HOST else certifi.where())
        options['connect_args'].update(ssl_ca=ca, ssl_verify_cert=True, ssl_verify_identity=True)
    return options
