"""Build a private CSV backup in memory and email it before account deletion."""
import csv
import io
import smtplib
from flask import current_app
from sqlalchemy import or_
from .extensions import db
from . import invitation_mail as mail
from .models import (User, Household, HouseholdMembership, HouseholdProfileAccess, PersonProfile,
                     Wishlist, WishlistItem, WishlistItemWishlist, PersonalWish, SavedGift, PrivateGift, GiftReservation)
from .api import item_audience_allowed, personal_viewer_allowed, profile_access


COLUMNS=['Type','Family','Person','List','Gift','Description','Product link','Price','Currency','Quantity','Store']


def safe_cell(value):
    value='' if value is None else str(value)
    if value.lstrip(' \t\r\n').startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')):
        return "'"+value
    return value


def can_copy(item,user):
    personal=PersonalWish.query.filter_by(item_id=item.id).first()
    if personal:
        return personal.owner_id==user.id or personal_viewer_allowed(personal,user)
    return profile_access(user,item.profile_id) is not None and item_audience_allowed(item,user)


def build_csv(user):
    stream=io.StringIO(newline='')
    writer=csv.writer(stream)
    writer.writerow(COLUMNS)
    def write(kind,family,person,title,item=None,quantity=None):
        writer.writerow([safe_cell(value) for value in [kind,family,person,title,
            item.name if item else '',item.description if item else '',item.product_url if item else '',
            item.estimated_price if item else None,item.currency if item else '',
            quantity if quantity is not None else item.quantity if item else '',item.store_name if item else '']])
    def family_name(profile_id):
        return '; '.join(home.name for home in Household.query.join(HouseholdProfileAccess).join(HouseholdMembership,
            HouseholdMembership.household_id==Household.id).filter(HouseholdProfileAccess.profile_id==profile_id,
            HouseholdMembership.user_id==user.id).order_by(Household.id).all())
    owned=db.session.query(HouseholdProfileAccess.profile_id).join(Household).filter(Household.owner_id==user.id)
    profiles=PersonProfile.query.filter(or_(PersonProfile.account_user_id==user.id,PersonProfile.id.in_(owned))).order_by(PersonProfile.id).all()
    for profile in profiles:
        linked=db.session.get(User,profile.account_user_id) if profile.account_user_id else None
        # A separately signed-in adult keeps their own private wishes.
        if linked and not linked.is_child and linked.id!=user.id:
            continue
        family=family_name(profile.id)
        for wishlist in Wishlist.query.filter_by(profile_id=profile.id).order_by(Wishlist.id).all():
            items=WishlistItem.query.join(WishlistItemWishlist).filter(WishlistItemWishlist.wishlist_id==wishlist.id).order_by(WishlistItem.id).all()
            items=[item for item in items if item_audience_allowed(item,user)]
            if not items:
                write('Wishlist',family,profile.display_name,wishlist.title)
            for item in items:
                write('Wishlist',family,profile.display_name,wishlist.title,item)
    for saved in SavedGift.query.filter_by(user_id=user.id).order_by(SavedGift.id).all():
        item=saved.item
        if can_copy(item,user):
            write('Saved gift',family_name(item.profile_id),item.profile.display_name,'Saved for later',item)
    for reservation in GiftReservation.query.filter_by(shopper_id=user.id).order_by(GiftReservation.id).all():
        item=reservation.item
        if can_copy(item,user):
            write('Gifting',family_name(item.profile_id),item.profile.display_name,reservation.status,item,reservation.quantity)
    for gift in PrivateGift.query.filter_by(user_id=user.id).order_by(PrivateGift.id).all():
        writer.writerow([safe_cell(value) for value in ['Private gifting',gift.household_name,gift.recipient,gift.occasion or gift.status,
            gift.name,'',gift.product_url,gift.estimated_price,gift.currency,1,gift.store_name]])
    return stream.getvalue().encode('utf-8-sig')


def send_backup(email,csv_bytes):
    if not mail.mail_configured():
        return None
    message=mail.new_message('A copy of your Gather & Gift lists and wishes',email)
    message.set_content('A copy of your lists and wishes is attached for you to keep. It includes family members, gift names, product links and prices where provided.\n\n'
        'You requested account deletion. This backup was prepared before deleting your account; the app will confirm when deletion completes. '
        'Your personal account records will then be removed. If your family transfers to another adult, its shared profiles and lists remain with that owner.\n\n'
        'The CSV does not include photos, passwords or payment details.')
    message.add_attachment(csv_bytes,maintype='text',subtype='csv',filename='gather-and-gift-wishlists.csv')
    try:
        mail.deliver(message)
    except (OSError,smtplib.SMTPException):
        current_app.logger.warning('Account deletion backup email could not be sent; deletion stopped.')
        return None
    return 'preview' if current_app.config.get('MAIL_OUTBOX_DIR') else 'sent'
