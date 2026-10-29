"""Private, parent-managed invitations to write a wishlist."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from flask import request, jsonify
from .api import api, authenticated, error, require_household_admin, profile_access
from .extensions import db
from .models import Household, HouseholdProfileAccess, PersonProfile, Wishlist, WishlistLetter, SharedTheme, User, ChildWishlistAccess


def letter_dict(row):
    profile = db.session.get(PersonProfile, row.profile_id)
    wishlist = db.session.get(Wishlist, row.wishlist_id)
    from .letter_art import public_art
    art=db.session.get(SharedTheme,row.theme_id) if row.theme_id else None
    return dict(theme_id=row.theme_id,letter_art=public_art(art) if art else None,id=row.id, profile_id=row.profile_id, child_name=profile.display_name,
                wishlist_id=row.wishlist_id, title=wishlist.title, sender_name=row.sender_name, send_on=row.send_on.isoformat())


def active_letters(profile_id):
    today = datetime.now(ZoneInfo('America/Los_Angeles')).date()
    return WishlistLetter.query.filter(WishlistLetter.profile_id == profile_id, WishlistLetter.send_on <= today).all()


def managed_home(home_id):
    _, failure = require_household_admin(home_id)
    if failure:
        return failure
    home = db.session.get(Household, home_id)
    if home.registry_type != 'family' or home.owner_id != request.current_user.id:
        return error('Only the family creator can manage child wishlist letters.', 403)


def values(payload):
    title, sender = payload.get('title'), payload.get('sender_name')
    if not isinstance(title,str) or not 1 <= len(title.strip()) <= 160 or not isinstance(sender,str) or not 1 <= len(sender.strip()) <= 120:
        raise ValueError('Enter a list name and who the letter is from.')
    try:
        send_on = date.fromisoformat(payload.get('send_on',''))
    except (ValueError,TypeError):
        raise ValueError('Choose a valid invitation date.')
    return title.strip(), sender.strip(), send_on


@api.route('/households/<int:home_id>/wishlist-letters', methods=['GET','POST'])
@authenticated
def manage_wishlist_letters(home_id):
    failure = managed_home(home_id)
    if failure:
        return failure
    if request.method == 'GET':
        return jsonify(letters=[letter_dict(row) for row in WishlistLetter.query.filter_by(household_id=home_id).order_by(WishlistLetter.id.desc()).all()])
    payload = request.get_json(silent=True) or {}
    try:
        title, sender, send_on = values(payload)
    except ValueError as exc:
        return error(str(exc),400)
    ids = payload.get('profile_ids')
    if not isinstance(ids,list) or not ids or len(ids)>50 or any(type(pid) is not int for pid in ids):
        return error('Choose at least one child in your family.',400)
    profiles = PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id==home_id, PersonProfile.id.in_(ids), PersonProfile.is_adult.is_(False), PersonProfile.profile_type=='person').all()
    if {p.id for p in profiles} != set(ids) or any(profile_access(request.current_user,p.id,write=True) is None for p in profiles):
        return error('Choose child profiles you manage in this family.',404)
    from .letter_art import validate_letter_art, remember_free_art
    try:
        art=validate_letter_art(home_id,payload.get('theme_id'))
    except PermissionError as exc:
        return error(str(exc),402)
    except ValueError as exc:
        return error(str(exc),400)
    remember_free_art(home_id,art,request.current_user.id)
    letters=[]
    for profile in profiles:
        wishlist=Wishlist(profile_id=profile.id,title=title,share_publicly=False)
        db.session.add(wishlist)
        db.session.flush()
        letter=WishlistLetter(theme_id=art.id if art else None,household_id=home_id,profile_id=profile.id,wishlist_id=wishlist.id,sender_name=sender,send_on=send_on,created_by_id=request.current_user.id)
        db.session.add(letter)
        child=db.session.get(User,profile.account_user_id) if profile.account_user_id else None
        if child and child.is_child and child.parent_user_id==request.current_user.id:
            db.session.add(ChildWishlistAccess(user_id=child.id,wishlist_id=wishlist.id))
        letters.append(letter)
    db.session.commit()
    return jsonify(letters=[letter_dict(row) for row in letters]),201


@api.route('/households/<int:home_id>/wishlist-letters/<int:letter_id>',methods=['PATCH','DELETE'])
@authenticated
def update_wishlist_letter(home_id,letter_id):
    failure=managed_home(home_id)
    if failure:
        return failure
    row=WishlistLetter.query.filter_by(id=letter_id,household_id=home_id).first()
    if not row or profile_access(request.current_user,row.profile_id,write=True) is None:
        return error('Wishlist letter not found.',404)
    if request.method=='DELETE':
        db.session.delete(row)
        db.session.commit()
        return jsonify(status='cancelled')
    try:
        title,sender,send_on=values(request.get_json(silent=True) or {})
    except ValueError as exc:
        return error(str(exc),400)
    from .letter_art import validate_letter_art, remember_free_art
    try:
        art=validate_letter_art(home_id,(request.get_json(silent=True) or {}).get('theme_id',row.theme_id),row.theme_id)
    except PermissionError as exc:
        return error(str(exc),402)
    except ValueError as exc:
        return error(str(exc),400)
    remember_free_art(home_id,art,request.current_user.id)
    row.theme_id=art.id if art else None
    db.session.get(Wishlist,row.wishlist_id).title=title
    row.sender_name,row.send_on=sender,send_on
    db.session.commit()
    return jsonify(letter=letter_dict(row))
