import csv
import io
import smtplib
from backend.tests.test_account_deletion import foreign_keys,confirm
from backend.tests.test_linked_adults import joined_family
from backend.tests.test_reservation_privacy import mutate
from backend.app.extensions import db
from backend.app.models import User,Household,PersonProfile,SavedGift,PrivateGift
from backend.app.deletion_backup import build_csv,safe_cell
from backend.app import invitation_mail


def test_csv_contains_managed_family_links_prices_and_saved_items_but_not_another_adults_private_wishes(app):
    owner,adult,_,home,partner,kid,o,a=joined_family(app)
    kid_list=owner.get(f"/api/profiles/{kid['id']}/wishlists").json['wishlists'][0]['id']
    child_gift=mutate(owner,'POST',f'/api/wishlists/{kid_list}/items',dict(name='Art kit',estimated_price='24.50',currency='USD',product_url='https://example.com/art')).json['item']
    mine=mutate(owner,'POST','/api/personal-wishes',dict(name='My private wish',visibility='private',viewer_ids=[]))
    assert mine.status_code==201
    other=mutate(adult,'POST','/api/personal-wishes',dict(name='Do not export this adult secret',visibility='private',viewer_ids=[])).json['wish']['item']
    with app.app_context():
        db.session.add(SavedGift(user_id=o['id'],item_id=child_gift['id']))
        db.session.add(SavedGift(user_id=o['id'],item_id=other['id']))
        db.session.add(PrivateGift(user_id=o['id'],name='Saved surprise',recipient='Grandma',product_url='https://example.com/surprise',estimated_price=12,currency='USD'))
        db.session.commit()
        with app.test_request_context():
            data=build_csv(db.session.get(User,o['id'])).decode('utf-8-sig')
    rows=list(csv.DictReader(io.StringIO(data)))
    row=next(row for row in rows if row['Gift']=='Art kit' and row['Type']=='Wishlist')
    assert row['Family']==home['name'] and row['Person']==kid['display_name']
    assert row['Product link']=='https://example.com/art' and row['Price']=='24.50'
    assert any(row['Gift']=='My private wish' for row in rows)
    assert any(row['Gift']=='Saved surprise' and row['Person']=='Grandma' for row in rows)
    assert any(row['Gift']=='Art kit' and row['Type']=='Saved gift' for row in rows)
    assert 'Do not export this adult secret' not in data


def test_backup_is_sent_to_account_email_before_deletion_without_writing_an_export_file(app,monkeypatch):
    owner,_,_,home,_,kid,o,_=joined_family(app)
    captured=[]
    def deliver(message):
        assert db.session.get(User,o['id']) is not None
        assert db.session.get(Household,home['id']).owner_id==o['id']
        captured.append(message)
    monkeypatch.setattr(invitation_mail,'deliver',deliver)
    app.config['MAIL_OUTBOX_DIR']=None
    app.config.update(SMTP_HOST='test-smtp',MAIL_FROM='test@example.com')
    preview=owner.get('/api/auth/account-deletion').json
    assert preview['backup_email']=='linked-owner@example.com'
    assert preview['backup_available'] is True
    result=confirm(owner,preview)
    assert result.status_code==200,result.json
    assert result.json['backup_delivery']=='sent'
    assert result.json['backup_email']=='linked-owner@example.com'
    assert len(captured)==1 and str(captured[0]['To'])=='linked-owner@example.com'
    attachments=list(captured[0].iter_attachments())
    assert len(attachments)==1 and attachments[0].get_filename()=='gather-and-gift-wishlists.csv'
    assert attachments[0].get_content_type()=='text/csv'
    assert 'Person' in attachments[0].get_payload(decode=True).decode('utf-8-sig')
    with app.app_context():assert db.session.get(User,o['id']) is None


def test_failed_backup_delivery_preserves_account_and_family_ownership(app,monkeypatch):
    owner,_,_,home,_,_,o,_=joined_family(app)
    def fail(message):raise smtplib.SMTPException('Simulated mail failure')
    monkeypatch.setattr(invitation_mail,'deliver',fail)
    preview=owner.get('/api/auth/account-deletion').json
    result=confirm(owner,preview)
    assert result.status_code==503
    assert 'has not been deleted' in result.json['error']
    with app.app_context():
        assert db.session.get(User,o['id']) is not None
        assert db.session.get(Household,home['id']).owner_id==o['id']


def test_missing_mail_configuration_stops_deletion_and_csv_cells_cannot_execute_formulas(app):
    owner,_,_,home,_,_,o,_=joined_family(app)
    app.config.update(MAIL_OUTBOX_DIR=None,SMTP_HOST='',MAIL_FROM='')
    preview=owner.get('/api/auth/account-deletion').json
    assert preview['backup_available'] is False
    assert confirm(owner,preview).status_code==503
    with app.app_context():assert db.session.get(User,o['id']) is not None
    for cell in ['=SUM(1,2)','+formula','-formula','@formula','  =formula','\tvalue','\nvalue']:
        assert safe_cell(cell).startswith("'")
    assert safe_cell('https://example.com/item')=='https://example.com/item'
