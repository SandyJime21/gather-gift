"""Permission-filtered family collections. Existing per-person lists remain independent."""
from flask import request,jsonify,g
from sqlalchemy import inspect
from .extensions import db
from .models import FamilyListCollection,Household,HouseholdProfileAccess,Wishlist,WishlistItem,WishlistItemWishlist,PersonProfile,SharedTheme
from .api import api,authenticated,error,membership_for,profile_access,can_manage_wishes,list_family_access,list_is_shared,item_audience_allowed,item_dict
from .commerce_urls import validated_product_url


def ready():
    if not hasattr(g,'family_collections_ready'):
        g.family_collections_ready=inspect(db.session.connection()).has_table('family_list_collection')
    return g.family_collections_ready


def family_manager(user,home_id):
    member=membership_for(user,home_id)
    return bool(member and (member.is_family_member or member.role in ('owner','admin','profile_manager')) and not user.is_child and not user.is_support)


def visible_lists(collection,user):
    ids=collection.wishlist_ids or []
    if not ids:return []
    rows=Wishlist.query.join(HouseholdProfileAccess,HouseholdProfileAccess.profile_id==Wishlist.profile_id).filter(HouseholdProfileAccess.household_id==collection.household_id,Wishlist.id.in_(ids)).all()
    return [row for row in rows if profile_access(user,row.profile_id) is not None and (list_family_access(row,user) or list_is_shared(row))]


def list_items(row,user):
    rows=WishlistItem.query.join(WishlistItemWishlist).filter(WishlistItemWishlist.wishlist_id==row.id,WishlistItem.profile_id==row.profile_id).all()
    return [item for item in rows if item_audience_allowed(item,user)]


def summary(collection,user):
    home=db.session.get(Household,collection.household_id)
    rows=visible_lists(collection,user)
    populated=[row for row in rows if list_items(row,user)]
    manager=family_manager(user,home.id)
    if not populated and not manager:return None
    theme=None
    if (collection.cover_url or '').startswith('theme:'):
        try:theme=db.session.get(SharedTheme,int(collection.cover_url.split(':')[1]))
        except ValueError:pass
        if theme and (theme.data.get('purpose')!='list' or not theme.data.get('active',True)):theme=None
    artwork=theme.data.get('art') if theme else None
    return dict(id=collection.id,title=collection.title,cover_url=home.photo_path if collection.use_family_photo else artwork or (collection.cover_url if not (collection.cover_url or '').startswith('theme:') else None),family_photo_url=home.photo_path if collection.use_family_photo else None,background_art=artwork,background_colors={key:theme.data.get(key) for key in ('background','foreground','accent')} if theme else None,household_name=home.name,list_count=len(populated),can_manage=manager,wishlist_ids=[row.id for row in rows])


@api.route('/households/<int:home_id>/list-collections',methods=['GET','POST'])
@authenticated
def collections(home_id):
    user=request.current_user
    if not membership_for(user,home_id):return error('Family not found.',404)
    if not ready():return (jsonify(collections=[],migration_required=True),200) if request.method=='GET' else error('Family collections need the matching release database migration.',503)
    if request.method=='GET':
        return jsonify(collections=[value for row in FamilyListCollection.query.filter_by(household_id=home_id).all() if (value:=summary(row,user))])
    if not family_manager(user,home_id):return error('Only family managers can organize collections.',403)
    body=request.get_json(silent=True) or {}
    title=body.get('title','')
    ids=body.get('wishlist_ids',[])
    shared=body.get('share_publicly')
    use_photo=body.get('use_family_photo',True)
    cover=body.get('cover_url','')
    art_id=body.get('background_theme_id')
    art=None
    if art_id is not None:
        art=db.session.get(SharedTheme,art_id) if type(art_id)is int else None
        if not art or art.data.get('purpose')!='list' or not art.data.get('active',True):return error('Choose an available family list background.',400)
    if not isinstance(title,str) or not title.strip() or len(title.strip())>160:return error('Enter a collection name within 160 characters.',400)
    if not isinstance(ids,list) or not ids or len(ids)>100 or any(type(i)is not int for i in ids):return error('Choose the member lists to include.',400)
    if type(shared)is not bool or type(use_photo)is not bool:return error('Choose valid sharing and artwork settings.',400)
    if not isinstance(cover,str):return error('Choose a valid artwork URL.',400)
    if cover:
        try:validated_product_url(cover)
        except ValueError as exc:return error(str(exc),400)
    rows=Wishlist.query.filter(Wishlist.id.in_(set(ids))).all()
    if len(rows)!=len(set(ids)):return error('A selected list no longer exists.',404)
    for row in rows:
        if not HouseholdProfileAccess.query.filter_by(household_id=home_id,profile_id=row.profile_id).first() or not can_manage_wishes(user,db.session.get(PersonProfile,row.profile_id)):
            return error('Each adult controls their own lists. Only include lists you can manage.',403)
    collection=FamilyListCollection.query.filter_by(household_id=home_id,title=title.strip()).with_for_update().first()
    if collection is None:
        collection=FamilyListCollection(household_id=home_id,title=title.strip())
        db.session.add(collection)
    # Each adult may update only their own managed participation. Other adults'
    # existing lists stay linked and retain their current sharing settings.
    previous=Wishlist.query.filter(Wishlist.id.in_(collection.wishlist_ids or [])).all()
    preserved=[row.id for row in previous if not can_manage_wishes(user,db.session.get(PersonProfile,row.profile_id))]
    collection.wishlist_ids=list(dict.fromkeys(preserved+ids));collection.use_family_photo=use_photo;collection.cover_url='theme:'+str(art.id) if art else cover or None
    for row in rows:row.share_publicly=shared
    db.session.commit()
    return jsonify(collection=summary(collection,user)),201


@api.get('/households/<int:home_id>/list-collections/<int:collection_id>')
@authenticated
def collection_detail(home_id,collection_id):
    user=request.current_user
    if not ready() or not membership_for(user,home_id):return error('Collection not found.',404)
    collection=FamilyListCollection.query.filter_by(id=collection_id,household_id=home_id).first()
    if not collection or not (value:=summary(collection,user)):return error('Collection not found.',404)
    unique={item.id:item for row in visible_lists(collection,user) for item in list_items(row,user)}
    return jsonify(collection=value,items=[item_dict(item,user) for item in unique.values()])


@api.get('/list-backgrounds')
@authenticated
def list_background_catalog():
    return jsonify(backgrounds=[{'id':row.id,**{key:row.data.get(key) for key in ('name','season','background','foreground','accent','art')}} for row in SharedTheme.query.order_by(SharedTheme.id.desc()).all() if row.data.get('purpose')=='list' and row.data.get('active',True)])
