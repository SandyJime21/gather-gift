"""Move/copy existing gifts between the same person's managed lists."""
import unicodedata
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
from flask import request,jsonify
from .api import api,authenticated,error,can_manage_wishes,record_audit
from .extensions import db
from .models import Wishlist,PersonProfile,WishlistItem,WishlistItemWishlist


def name_key(value):
    return ' '.join(unicodedata.normalize('NFKC',value or '').casefold().split())


def link_key(value):
    if not value:return ''
    try:
        parts=urlsplit(value.strip())
        ignored={'gclid','fbclid','msclkid','tag','ascsubtag','linkcode','campid','irclickid','irgwc'}
        query=sorted((k,v) for k,v in parse_qsl(parts.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ignored)
        return urlunsplit((parts.scheme.lower(),parts.netloc.lower().removeprefix('www.'),parts.path.rstrip('/') or '/',urlencode(query),''))
    except ValueError:return value.strip()


def editable(row,user):
    return row and can_manage_wishes(user,db.session.get(PersonProfile,row.profile_id))


@api.get('/wishlists/<int:list_id>/transfer-targets')
@authenticated
def transfer_targets(list_id):
    source=db.session.get(Wishlist,list_id)
    if not editable(source,request.current_user):return error('List not found or edit permission denied.',404)
    return jsonify(wishlists=[{'id':r.id,'title':r.title} for r in Wishlist.query.filter(Wishlist.profile_id==source.profile_id,Wishlist.id!=source.id).order_by(Wishlist.title).all()])


@api.post('/wishlists/<int:list_id>/transfer')
@authenticated
def transfer_list_items(list_id):
    body=request.get_json(silent=True) or {}
    target_id=body.get('wishlist_id');mode=body.get('mode')
    if type(target_id)is not int or target_id==list_id or mode not in ('move','copy'):
        return error('Choose a different list and Move or Copy.',400)
    rows=Wishlist.query.filter(Wishlist.id.in_([list_id,target_id])).order_by(Wishlist.id).with_for_update().all()
    source=next((r for r in rows if r.id==list_id),None);target=next((r for r in rows if r.id==target_id),None)
    if not editable(source,request.current_user) or not editable(target,request.current_user):return error('Both lists must be managed by your account.',404)
    if source.profile_id!=target.profile_id:return error('Choose another list for the same person or pet.',400)
    existing=WishlistItem.query.join(WishlistItemWishlist).filter(WishlistItemWishlist.wishlist_id==target.id).all()
    ids={i.id for i in existing};names={name_key(i.name) for i in existing};links={link_key(i.product_url) for i in existing if i.product_url}
    source_links=WishlistItemWishlist.query.filter_by(wishlist_id=source.id).order_by(WishlistItemWishlist.item_id).all()
    transferred=skipped=already=0
    for association in source_links:
        item=db.session.get(WishlistItem,association.item_id)
        if not item or item.profile_id!=source.profile_id:continue
        if item.id in ids:
            already+=1
            if mode=='move':db.session.delete(association)
            continue
        name=name_key(item.name);url=link_key(item.product_url)
        if name in names or (url and url in links):
            skipped+=1
            continue # Keep unmatched source records intact, including their notes/holds.
        db.session.add(WishlistItemWishlist(item_id=item.id,wishlist_id=target.id))
        ids.add(item.id);names.add(name)
        if url:links.add(url)
        if mode=='move':db.session.delete(association)
        transferred+=1
    db.session.flush()
    remaining=WishlistItemWishlist.query.filter_by(wishlist_id=source.id).count()
    record_audit(request.current_user.id,'wishlist.items_'+mode,'wishlist',source.id,details={'target_id':target.id,'transferred':transferred,'skipped':skipped,'already_present':already})
    db.session.commit()
    return jsonify(transferred=transferred,skipped=skipped,already_present=already,remaining=remaining)


@api.post('/items/<int:item_id>/move-list')
@authenticated
def move_single_gift_list(item_id):
    from .models import PersonalWish,WishlistItemOccasion
    item=db.session.get(WishlistItem,item_id)
    if not item or not can_manage_wishes(request.current_user,item.profile):return error('Gift edit permission denied.',403)
    target_id=(request.get_json(silent=True) or {}).get('wishlist_id')
    if type(target_id)is not int:return error('Choose a destination list.',400)
    target=Wishlist.query.filter_by(id=target_id).with_for_update().first()
    if not editable(target,request.current_user) or target.profile_id!=item.profile_id:return error('Choose a managed list for this same person or pet.',403)
    existing=WishlistItem.query.join(WishlistItemWishlist).filter(WishlistItemWishlist.wishlist_id==target.id,WishlistItem.id!=item.id).all()
    if any(name_key(row.name)==name_key(item.name) or (item.product_url and link_key(row.product_url)==link_key(item.product_url)) for row in existing):
        return error('That list already has a gift with this name or link. The original gift was kept.',409)
    # Reassign only list/occasion links. Keep photos, saved hearts, holds and item identity.
    item.wishlists.clear();item.occasions.clear()
    db.session.flush()
    db.session.add(WishlistItemWishlist(item_id=item.id,wishlist_id=target.id))
    if target.occasion_id:db.session.add(WishlistItemOccasion(item_id=item.id,occasion_id=target.occasion_id))
    personal=PersonalWish.query.filter_by(item_id=item.id).first()
    if personal:personal.occasion=target.title
    record_audit(request.current_user.id,'wishlist.item_moved','wishlist_item',item.id,details={'target_id':target.id})
    db.session.commit()
    return jsonify(status='moved',list_title=target.title)
