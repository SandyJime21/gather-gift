from email import policy, message_from_bytes
from urllib.parse import urlsplit
from backend.tests.test_advertising import staff_login
from backend.tests.test_reservation_privacy import mutate, register
from backend.app.extensions import db
from backend.app.models import EmailSuppression, User
from backend.app.email_preferences import preference_link
from backend.app import invitation_mail as mail


def test_master_can_send_selected_template_to_test_recipient(app,tmp_path):
    app.config['MAIL_OUTBOX_DIR']=str(tmp_path)
    admin=app.test_client();staff_login(admin)
    result=mutate(admin,'POST','/api/support/email-templates/send',{'template_ids':['game-invite'],'email':'qa@example.com'})
    assert result.status_code==200 and result.json['previewed']==1
    message=message_from_bytes(next(tmp_path.glob('*.eml')).read_bytes(),policy=policy.default)
    assert str(message['To'])=='qa@example.com'
    assert 'sample' in message.get_body(preferencelist=('plain',)).get_content().lower() or '[Template preview]' in message['Subject']
    assert mutate(admin,'POST','/api/support/email-suppressions',{'email':'qa@example.com','unsubscribed':True}).status_code==200
    assert mutate(admin,'POST','/api/support/email-templates/send',{'template_ids':['game-invite'],'email':'qa@example.com'}).status_code==409


def test_block_design_preserves_live_content_and_csv(app, tmp_path):
    app.config['MAIL_OUTBOX_DIR'] = str(tmp_path)
    admin=app.test_client();staff_login(admin)
    blocks=[dict(type='html',html='<h2>Hello family</h2><img src=x onerror=alert(1)>',font='Georgia',size=20,color='#123456',background='#ffffff'),
            dict(type='message',html='',font='Arial',size=16,color='#302b43',background='#ffffff')]
    endpoint='/api/support/email-templates/password-code'
    assert mutate(admin,'POST',endpoint+'/design',{'blocks':blocks[:1]}).status_code==400
    assert mutate(admin,'POST',endpoint+'/design',{'blocks':blocks}).status_code==200
    preview=mutate(admin,'POST',endpoint+'/preview',{'blocks':blocks})
    assert preview.status_code==200
    assert 'Hello family' in preview.json['html'] and 'onerror' not in preview.json['html']
    with app.test_request_context():
        assert mail.send_account_code('real@example.com','987654','password')
    message=message_from_bytes(next(tmp_path.glob('*.eml')).read_bytes(),policy=policy.default)
    html=message.get_body(preferencelist=('html',)).get_content()
    assert 'is: 987654' in html and 'is: 123456' not in html
    assert 'Hello family' in html and '/email-preferences/' in html
    assert mutate(admin,'POST','/api/support/email-templates/deletion-backup/design',{'blocks':blocks}).status_code==200
    with app.test_request_context():
        from backend.app.deletion_backup import send_backup
        assert send_backup('real@example.com',b'Gift,Price\nPuzzle,20')=='preview'
    messages=[message_from_bytes(p.read_bytes(),policy=policy.default) for p in tmp_path.glob('*.eml')]
    backup=next(m for m in messages if list(m.iter_attachments()))
    assert list(backup.iter_attachments())[0].get_payload(decode=True)==b'Gift,Price\nPuzzle,20'
    assert 'Hello family' in backup.get_body(preferencelist=('html',)).get_content()
    assert mutate(admin,'DELETE',endpoint+'/design').status_code==200


def test_master_can_preview_all_real_templates_without_sending(app, monkeypatch):
    app.config.update(SMTP_HOST='', MAIL_FROM='', MAIL_OUTBOX_DIR=None)
    monkeypatch.setattr(mail.smtplib, 'SMTP', lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError('Preview must not send')))
    admin, user = app.test_client(), app.test_client()
    staff_login(admin)
    register(user, 'Person', 'templates-user@example.com')
    assert user.get('/api/support/email-templates').status_code == 403
    result = admin.get('/api/support/email-templates')
    assert result.status_code == 200, result.json
    assert len(result.json['templates']) == 15
    assert result.json['sample_email'] == 'ad-admin@example.com'
    assert result.json['mail_configured'] is False
    for row in result.json['templates']:
        assert '/email-preferences/' in row['text']
        assert '/email-preferences/' in row['html']
    backup = next(row for row in result.json['templates'] if row['id'] == 'deletion-backup')
    assert backup['attachments'] == ['gather-and-gift-wishlists.csv']
    with app.app_context():
        db.session.get(User, 1).is_superuser = False;db.session.commit()
    assert admin.get('/api/support/email-templates').status_code == 403


def test_samples_default_to_master_address_and_respect_unsubscribe(app, tmp_path, monkeypatch):
    app.config['MAIL_OUTBOX_DIR'] = str(tmp_path)
    monkeypatch.setattr(mail.smtplib, 'SMTP', lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError('Must use test outbox')))
    admin = app.test_client();staff_login(admin)
    assert mutate(admin,'POST','/api/support/email-templates/send',{'template_ids':['game-invite'],'email':'not-an-email'}).status_code == 400
    result = mutate(admin,'POST','/api/support/email-templates/send',{'template_ids':['game-invite']})
    assert result.status_code == 200 and result.json['previewed'] == 1 and result.json['sent'] == 0
    files = list(tmp_path.glob('*.eml'));assert len(files) == 1
    message = message_from_bytes(files[0].read_bytes(),policy=policy.default)
    assert str(message['To']) == 'ad-admin@example.com'
    assert str(message['Subject']).startswith('[Template preview]')
    assert '/email-preferences/' in str(message['List-Unsubscribe'])
    assert mutate(admin,'POST','/api/support/email-suppressions',{'email':'ad-admin@example.com','unsubscribed':True}).status_code == 200
    assert mutate(admin,'POST','/api/support/email-templates/send',{'template_ids':['game-invite']}).status_code == 409
    assert len(list(tmp_path.glob('*.eml'))) == 1
    assert mutate(admin,'POST','/api/support/email-suppressions',{'email':'ad-admin@example.com','unsubscribed':False}).status_code == 200
    assert admin.get('/api/support/email-suppressions').json['addresses'] == []
    ids=[row['id'] for row in admin.get('/api/support/email-templates').json['templates']]
    all_samples=mutate(admin,'POST','/api/support/email-templates/send',{'template_ids':ids})
    assert all_samples.status_code == 200 and all_samples.json['previewed'] == 15
    assert len(list(tmp_path.glob('*.eml'))) == 16
    for file in tmp_path.glob('*.eml'):
        sample=message_from_bytes(file.read_bytes(),policy=policy.default)
        assert str(sample['To']) == 'ad-admin@example.com'
        assert '/email-preferences/' in str(sample['List-Unsubscribe'])


def test_signed_unsubscribe_requires_confirmation_and_blocks_all_delivery(app,tmp_path):
    app.config['MAIL_OUTBOX_DIR'] = str(tmp_path)
    email='no-account@example.com'
    path='/api'+urlsplit(preference_link(email)).path
    guest=app.test_client()
    assert guest.get(path).json['unsubscribed'] is False
    assert EmailSuppression.query.count() == 0
    assert guest.get(path+'tampered').status_code == 400
    assert mutate(guest,'POST',path,{'unsubscribed':True}).json['unsubscribed'] is True
    assert mutate(guest,'POST',path,{'unsubscribed':True}).status_code == 200
    assert EmailSuppression.query.count() == 1
    assert mail.send_game_invitation(email,'Sample','Host','https://example.com', ['You']) is False
    assert mail.send_account_code(email,'123456','parent_pin') is False
    mail.send_password_reset(email,'https://example.com/reset')
    assert list(tmp_path.glob('*.eml')) == []
    assert mutate(guest,'POST',path,{'unsubscribed':False}).json['unsubscribed'] is False
    assert mail.send_game_invitation(email,'Sample','Host','https://example.com', ['You']) is True
    message=message_from_bytes(next(tmp_path.glob('*.eml')).read_bytes(),policy=policy.default)
    assert 'Unsubscribe from all emails' in message.get_body(preferencelist=('html',)).get_content()


def test_deletion_review_explains_when_email_opt_out_blocks_the_required_backup(app,tmp_path):
    app.config['MAIL_OUTBOX_DIR']=str(tmp_path)
    owner=app.test_client();register(owner,'Owner','paused-backup@example.com')
    path='/api'+urlsplit(preference_link('paused-backup@example.com')).path
    assert mutate(owner,'POST',path,{'unsubscribed':True}).status_code == 200
    preview=owner.get('/api/auth/account-deletion').json
    assert preview['backup_available'] is False and preview['backup_email_paused'] is True
    assert '/email-preferences/' in preview['backup_preferences_url']
    assert owner.get('/api/auth/me').status_code == 200
