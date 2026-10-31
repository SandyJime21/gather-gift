"""Approved outbound shopping with privacy-preserving, non-sales click events."""
from datetime import datetime,timezone
from uuid import uuid4
from flask import current_app,g,request,jsonify,redirect,session
from sqlalchemy import inspect,func
from sqlalchemy.exc import SQLAlchemyError
from .extensions import db,limiter
from .api import api,authenticated,superuser_required,error,record_audit,shopper_can_see,can_manage_wishes,item_audience_allowed
from .models import CommerceIntegration,CommerceOutboundEvent,CommerceProductMetadata,WishlistItem,PersonalWish,PrivateGift
from .commerce_urls import validated_product_url
from .commerce_adapters import PROVIDERS,adapter,already_affiliated


def schema_ready():
    if not hasattr(g,'commerce_schema_ready'):
        try:
            # Inspect on the session connection so in-memory SQLite (and active
            # gift saves) never get rolled back by a separate inspector handle.
            g.commerce_schema_ready={'commerce_integration','commerce_outbound_event','commerce_product_metadata'}.issubset(set(inspect(db.session.connection()).get_table_names()))
        except SQLAlchemyError:
            g.commerce_schema_ready=False
    return g.commerce_schema_ready


def shopping_url(item):
    try:validated_product_url(item.product_url)
    except ValueError:return None
    return '/api/commerce/items/'+str(item.id)+'/out' if schema_ready() else None


def record_product_metadata(item):
    if not schema_ready() or not item.product_url:return
    try:_,host=validated_product_url(item.product_url)
    except ValueError:return
    row=db.session.get(CommerceProductMetadata,item.id)
    if row is None:
        row=CommerceProductMetadata(item_id=item.id,retailer_domain=host,source_provider='manual')
        db.session.add(row)
    token=(request.get_json(silent=True) or {}).get('source_token') if request.is_json else None
    if token:
        from .product_search import source_serializer
        from itsdangerous import BadData
        try:
            source=source_serializer().loads(token,max_age=3600)
            if source['url']==item.product_url and source['provider'] in ('ebay','serpapi'):
                row.source_provider=source['provider']
                row.external_product_id=str(source.get('product_id') or '')[:200] or None
                row.last_verified_at=datetime.fromisoformat(source['verified_at'])
        except (BadData,ValueError,TypeError,KeyError):
            pass


def resolve(url):
    original,host=validated_product_url(url)
    if already_affiliated(original) or not schema_ready():return original,'existing_link' if already_affiliated(original) else 'direct'
    settings={row.provider:row for row in CommerceIntegration.query.filter_by(enabled=True,approved=True).all()}
    for key in list(PROVIDERS)+[key for key in settings if key.startswith('custom_')]:
        row=settings.get(key)
        if not row:continue
        provider=adapter(key,row)
        if not provider.configured() or not provider.eligible_host(original):continue
        try:
            target=provider.generateAffiliateLink(original)
            if target:
                validated_product_url(target)
                return target,key
        except (OSError,ValueError,TypeError):
            row.last_error='Provider unavailable or returned an unsupported tracking link; original URL used.'
            row.last_error_at=datetime.now(timezone.utc)
            current_app.logger.warning('Commerce provider %s unavailable; using original retailer link.',key)
    return original,'direct'


def outbound(original,item_id=None):
    try:_,host=validated_product_url(original)
    except ValueError:return error('This gift does not have a safe public shopping link.',400)
    if request.method=='HEAD' or 'prefetch' in request.headers.get('Sec-Purpose',request.headers.get('Purpose','')).lower():
        target,provider=original,'direct'
    else:
        target,provider=resolve(original)
        if schema_ready() and request.headers.get('DNT')!='1' and request.headers.get('Sec-GPC')!='1':
            db.session.add(CommerceOutboundEvent(item_id=item_id,provider=provider,merchant=host,attribution_id=uuid4().hex))
        try:db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.warning('Outbound event storage unavailable; retailer navigation retained.')
    response=redirect(target,code=302)
    response.headers['Cache-Control']='no-store'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Robots-Tag']='noindex, nofollow'
    return response


def _authenticated_item_out(item_id):
    item=db.session.get(WishlistItem,item_id)
    if not item or not (shopper_can_see(item,request.current_user) or (can_manage_wishes(request.current_user,item.profile) and item_audience_allowed(item,request.current_user))):return error('Gift not found.',404)
    return outbound(item.product_url,item.id)


@api.get('/commerce/items/<int:item_id>/out')
@limiter.limit('60 per minute')
def commerce_item_out(item_id):
    if session.get('user_id'):
        return authenticated(_authenticated_item_out)(item_id)
    # Only explicit public personal wishes are accessible anonymously.
    wish=PersonalWish.query.filter_by(item_id=item_id,visibility='public').first()
    item=db.session.get(WishlistItem,item_id) if wish else None
    if not item or item.family_only:return error('Gift not found.',404)
    return outbound(item.product_url,item.id)


@api.get('/commerce/private-gifts/<int:gift_id>/out')
@authenticated
@limiter.limit('60 per minute')
def commerce_private_out(gift_id):
    gift=PrivateGift.query.filter_by(id=gift_id,user_id=request.current_user.id).first()
    if not gift:return error('Gift not found.',404)
    return outbound(gift.product_url)


def provider_rows():
    saved={row.provider:row for row in CommerceIntegration.query.all()} if schema_ready() else {}
    rows=[]
    for key,info in PROVIDERS.items():
        row=saved.get(key) or CommerceIntegration(provider=key,enabled=False,approved=False,merchant_rules={})
        instance=adapter(key,row)
        configured=instance.configured()
        rows.append({'id':key,'name':info['name'],'implementation':info['implementation'],'docs':info['docs'],
                     'required_environment':info['env'],
                     'enabled':row.enabled,'approved':row.approved,'configured':configured,
                     'status':'disabled' if not row.enabled else 'awaiting_approval' if not row.approved else ('credentials_required' if key=='sovrn' else 'issued_link_template_required') if not configured else 'ready_for_approved_merchants',
                     'capabilities':instance.capabilities,'documented_capabilities':info['documented'],
                     'api_credentials_present':all(current_app.config.get(env) for env in info['env']),
                     'merchant_rules':row.merchant_rules,'reporting':instance.getAvailableReporting(),
                     'last_error':row.last_error,'last_error_at':row.last_error_at.isoformat() if row.last_error_at else None})
    from .search_providers import search_status
    for key,row in saved.items():
        if not key.startswith('custom_'):continue
        info=row.merchant_rules or {}
        instance=adapter(key,row)
        rows.append({'id':key,'name':info.get('company_name','Custom company'),'implementation':'approved_link_templates','docs':info.get('website',''),'required_environment':[info['key_environment']] if info.get('key_environment') else [],'enabled':row.enabled,'approved':row.approved,'configured':instance.configured(),'status':'ready_for_approved_merchants' if row.enabled and row.approved and instance.configured() else 'disabled','capabilities':instance.capabilities,'merchant_rules':{k:v for k,v in info.items() if k in ('approved_merchants','excluded_merchants','links')},'company':{k:info.get(k,'') for k in ('company_name','website','publisher_id','key_environment')},'last_error':row.last_error})
    return rows+search_status()


def validate_rules(value):
    if not isinstance(value,dict) or set(value)-{'approved_merchants','excluded_merchants','links'}:raise ValueError('Use approved_merchants, excluded_merchants and links only.')
    result={}
    for key in ('approved_merchants','excluded_merchants'):
        domains=value.get(key,[])
        if not isinstance(domains,list) or len(domains)>1000:raise ValueError('Use a list of merchant domains.')
        clean=[]
        for domain in domains:
            if not isinstance(domain,str) or '/' in domain or domain!=domain.strip():raise ValueError('Enter domains without paths or protocols.')
            _,host=validated_product_url('https://'+domain+'/')
            clean.append(host)
        result[key]=list(dict.fromkeys(clean))
    links=value.get('links',{})
    if not isinstance(links,dict) or len(links)>1000:raise ValueError('Use a map of approved domains to issued link templates.')
    for host,template in links.items():
        if host not in result['approved_merchants'] or not isinstance(template,str) or template.count('{url}')!=1:raise ValueError('Each template needs one {url} placeholder and an approved merchant.')
        validated_product_url(template.replace('{url}','https%3A%2F%2Fexample.com'))
        from urllib.parse import urlsplit,parse_qsl,unquote
        if any(key.lower() in {'key','api_key','token','access_token','secret','password'} for key,_ in parse_qsl(urlsplit(template).query)):
            raise ValueError('Keep credentials on the server; use issued public tracking templates only.')
        if any(current_app.config.get(env) and current_app.config[env] in unquote(template) for info in PROVIDERS.values() for env in info['env']):
            raise ValueError('Tracking templates must not contain configured API credentials.')
    result['links']=links
    return result


@api.get('/support/commerce')
@superuser_required
def commerce_dashboard():
    rows=[]
    if schema_ready():
        rows=[{'provider':provider,'merchant':merchant,'outbound_events':count} for provider,merchant,count in db.session.query(CommerceOutboundEvent.provider,CommerceOutboundEvent.merchant,func.count(CommerceOutboundEvent.id)).group_by(CommerceOutboundEvent.provider,CommerceOutboundEvent.merchant).all()]
    return jsonify(schema_ready=schema_ready(),providers=provider_rows(),outbound=rows,conversions=None,commissions=None,
                   reporting_message='Outbound events are not sales. Conversion and commission reporting is not connected.')


@api.patch('/support/commerce/<provider_id>')
@superuser_required
def update_commerce_provider(provider_id):
    search_provider=provider_id in ('search_ebay','search_serpapi')
    if provider_id not in PROVIDERS and not search_provider and not (provider_id.startswith('custom_') and db.session.get(CommerceIntegration,provider_id)):return error('Provider not found.',404)
    if not schema_ready():return error('Apply the commerce database migration before changing providers.',503)
    payload=request.get_json(silent=True) or {}
    if set(payload)-{'enabled','approved','merchant_rules'} or not payload or any(type(payload[key]) is not bool for key in ('enabled','approved') if key in payload):return error('Choose valid provider settings.',400)
    row=db.session.get(CommerceIntegration,provider_id)
    if not row:row=CommerceIntegration(provider=provider_id,enabled=False,approved=False,merchant_rules={});db.session.add(row)
    try:
        if 'merchant_rules' in payload:row.merchant_rules={**(row.merchant_rules or {}),**validate_rules(payload['merchant_rules'])} if provider_id.startswith('custom_') else validate_rules(payload['merchant_rules'])
        if provider_id.startswith('custom_'):
            import os
            from urllib.parse import unquote
            env=(row.merchant_rules or {}).get('key_environment')
            secret=os.environ.get(env,'') if env else ''
            if secret and any(secret in unquote(value) for value in (row.merchant_rules or {}).get('links',{}).values()):raise ValueError('Keep API secrets out of public tracking URLs.')
    except ValueError as exc:
        db.session.rollback()
        return error(str(exc),400)
    for key in ('enabled','approved'):
        if key in payload:setattr(row,key,payload[key])
    if row.enabled and not row.approved and not search_provider:
        db.session.rollback()
        return error('Confirm actual provider approval before enabling affiliate monetization.',400)
    if provider_id.startswith('custom_') and row.enabled and not adapter(provider_id,row).configured():
        db.session.rollback();return error('Add an issued tracking template before enabling this company.',400)
    record_audit(request.current_user.id,'commerce.provider_updated','commerce_provider',provider_id,details={'enabled':row.enabled,'approved':row.approved})
    db.session.commit()
    return jsonify(provider=next(row for row in provider_rows() if row['id']==provider_id))


@api.post('/support/commerce/companies')
@superuser_required
def add_affiliate_company():
    import re,os
    from urllib.parse import unquote
    if not schema_ready():return error('Install the matching commerce migration first.',503)
    body=request.get_json(silent=True) or {}
    if set(body)-{'company_name','website','tracking_template','publisher_id','key_environment','approved','enabled'}:return error('Enter company details and a server key reference only.',400)
    name=body.get('company_name','');website=body.get('website','');template=body.get('tracking_template','');publisher=body.get('publisher_id','');env=body.get('key_environment','')
    if not all(isinstance(v,str) for v in (name,website,template,publisher,env)) or not 1<=len(name.strip())<=120 or len(publisher)>200:return error('Enter a company name and valid details.',400)
    if env and not re.fullmatch('[A-Z][A-Z0-9_]{2,79}',env):return error('Use the environment variable name, not the secret key value.',400)
    approved=body.get('approved',False);enabled=body.get('enabled',False)
    if type(approved)is not bool or type(enabled)is not bool or (enabled and not approved):return error('Confirm actual approval before enabling this company.',400)
    try:
        _,host=validated_product_url(website)
        host=host.removeprefix('www.')
        rules=validate_rules({'approved_merchants':[host],'links':{host:template} if template else {}})
        if env and os.environ.get(env) and os.environ[env] in unquote(template):raise ValueError('Keep API secrets out of public tracking URLs.')
    except ValueError as exc:return error(str(exc),400)
    if enabled and not template:return error('An issued tracking template is required to enable link routing.',400)
    row=CommerceIntegration(provider='custom_'+uuid4().hex[:16],enabled=enabled,approved=approved,merchant_rules={**rules,'company_name':name.strip(),'website':website,'publisher_id':publisher.strip(),'key_environment':env})
    db.session.add(row);db.session.flush();record_audit(request.current_user.id,'commerce.company_added','commerce_provider',row.provider);db.session.commit()
    return jsonify(provider=next(value for value in provider_rows() if value['id']==row.provider)),201
