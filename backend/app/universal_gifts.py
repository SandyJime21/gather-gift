"""Permitted metadata is optional; any public HTTPS store link can be saved."""
from flask import request,jsonify,current_app
from .api import api,authenticated,error
from .extensions import limiter
from .commerce_urls import validated_product_url
from .link_preview import preview_link


@api.post('/commerce/preview')
@authenticated
@limiter.limit('20 per minute')
def universal_gift_preview():
    try:
        url,host=validated_product_url((request.get_json(silent=True) or {}).get('url'))
    except ValueError as exc:
        return error(str(exc),400)
    allowed={value.strip().lower() for value in current_app.config.get('PERMITTED_METADATA_DOMAINS','').split(',') if value.strip()}
    preview={'title':'','store_name':host.removeprefix('www.')[:120],'image_url':None,'metadata_unavailable':True}
    # Permission must be configured explicitly; unknown shops are never scraped.
    if host in allowed:
        try:
            preview=preview_link(url,allowed_hosts=allowed)
        except (OSError,ValueError,TimeoutError):
            pass
    return jsonify(preview=preview,original_url=url,
                   message='Review the details, then save.' if not preview.get('metadata_unavailable') else 'Add a gift name and any details you know. This store link can still be saved.')
