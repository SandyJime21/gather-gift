import certifi
from backend.app.database_tls import mysql_engine_options, BUNDLED_CA


def test_railway_uses_its_trusted_public_ca_and_verifies_hostname():
    options=mysql_engine_options('mysql+pymysql://u:p@tokaido.proxy.rlwy.net:1234/railway',production=True)
    assert options['connect_args']['ssl_ca']==str(BUNDLED_CA)
    assert options['connect_args']['ssl_verify_cert'] is True
    assert options['connect_args']['ssl_verify_identity'] is True
    content=BUNDLED_CA.read_text()
    assert 'BEGIN CERTIFICATE' in content
    assert 'PRIVATE KEY' not in content


def test_custom_ca_takes_precedence_without_disabling_verification():
    args=mysql_engine_options('mysql+pymysql://u:p@db.example/gifts',True,'/custom/ca.pem')['connect_args']
    assert args['ssl_ca']=='/custom/ca.pem'
    assert args['ssl_verify_cert'] and args['ssl_verify_identity']


def test_other_production_mysql_uses_public_trust_roots():
    args=mysql_engine_options('mysql+pymysql://u:p@other-db.example/gifts',True)['connect_args']
    assert args['ssl_ca']==certifi.where()
    assert args['ssl_verify_cert'] and args['ssl_verify_identity']


def test_local_mysql_and_sqlite_do_not_require_the_railway_ca():
    assert 'ssl_ca' not in mysql_engine_options('mysql+pymysql://u:p@localhost/gifts')['connect_args']
    assert mysql_engine_options('sqlite://')=={}
