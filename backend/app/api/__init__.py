from ..profile_preferences import completion as profile_completion, gift_guide
import re
import hashlib
import secrets
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlsplit, urlencode
from uuid import uuid4

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, jsonify, request, send_from_directory, session
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db, limiter
from ..invitation_mail import prepare_invitation, prepare_family_setup_invitation, send_password_reset, send_account_code, send_change_approval
from ..product_search import search_products, safe_product_url, search_configured
from ..link_preview import preview_link
from ..affiliate_links import shopping_link
from ..models import (
    GiftAvailabilityAlert,
    GiftReservation,
    SavedGift,
    PrivateGift,
    PersonalWish,
    PersonalWishViewer,
    PasswordReset,
    AccountEmailCode,
    ChildWishlistAccess,
    CoBuyInvitation,
    Household,
    HouseholdInvitation,
    FamilyFollow,
    SharedTheme,
    HouseholdMemberProfileAccess,
    HouseholdMembership,
    HouseholdProfileAccess,
    Notification,
    Occasion,
    PersonProfile,
    AuditLog,
    ShoppingBudget,
    SupportAccessGrant,
    SupportAccessRequest,
    HelpChatMessage,
    SupportInvitation,
    SupportTicket,
    SupportTicketMessage,
    User,
    Wishlist,
    WishlistItem,
    WishlistItemOccasion,
    WishlistItemWishlist,
)

api = Blueprint("api", __name__)

FAMILY_RELATIONSHIPS = {"employee", "colleague", "manager", "team_member", "family_member", "dad", "mom", "parent", "son", "daughter", "child", "brother", "sister", "sibling", "cousin", "grandpa", "grandma", "grandparent", "grandchild", "aunt", "uncle", "niece", "nephew", "partner", "friend", "other"}

ADULT_RELATIONSHIPS = {'mom', 'dad', 'parent', 'grandma', 'grandpa', 'grandparent'}

PROFILE_AVATARS = {"flower", "paw", "star", "sun", "cat", "dog", "rabbit", "bird", "fish"}
IMAGE_SIGNATURES = {
    ".jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    ".jpg": lambda data: data.startswith(b"\xff\xd8\xff"),
    ".png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    ".gif": lambda data: data.startswith((b"GIF87a", b"GIF89a")),
    ".webp": lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
}


def error(message, status):
    return jsonify({"error": message}), status


def valid_profile_avatar(key):
    from ..models import SharedAvatar
    return isinstance(key, str) and (key in PROFILE_AVATARS or bool(re.fullmatch(r'a[0-9]{1,9}', key) and db.session.get(SharedAvatar, int(key[1:]))))


def normalized_email(value):
    try:
        return validate_email(value, check_deliverability=False).normalized
    except (EmailNotValidError, TypeError):
        return None


def _csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@api.before_request
def validate_csrf():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = session.get("csrf_token")
        supplied = request.headers.get("X-CSRF-Token")
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            return error("A valid CSRF token is required.", 400)
        if request.is_json:
            payload = request.get_json(silent=True)
            if payload is not None and not isinstance(payload, dict):
                return error("JSON request body must be an object.", 400)


@api.before_app_request
def restrict_child_session():
    if not request.path.startswith('/api/'):
        return None
    user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
    if user and user.is_child and request.endpoint in {'api.child_game_notifications', 'api.child_game_notification_read'}:
        from ..child_controls import controls_for
        if not controls_for(user)['game_invites']:
            return error('Ask your parent to allow game invitations.', 403)
    if user and user.is_child and request.endpoint not in {
        'api.csrf', 'api.current_user', 'api.logout', 'api.child_me', 'api.child_add_gift', 'api.child_add_link', 'api.child_gift_search', 'api.child_pet_add_gift', 'api.child_pet_remove_gift', 'api.exit_child_mode', 'api.request_parent_pin_reset', 'api.confirm_parent_pin_reset', 'api.child_profiles', 'api.switch_child_profile', 'api.theme_art', 'api.child_game_notifications', 'api.child_game_notification_read', 'api.avatar_art', 'api.child_profile_photo'
    }:
        return error("Child accounts can only view approved wishlists and add gift ideas.", 403)


def authenticated(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if user is None:
            return error("Authentication required.", 401)
        if user.is_child and (not user.child_enabled or session.get("auth_mode") != "child"):
            session.clear()
            return error("Child access is unavailable. Ask your parent for help.", 401)
        if user.is_support != (session.get("auth_mode") == "support"):
            return error("Please sign in through the correct portal.", 403)
        if user.is_support and not (
            request.path.startswith("/api/support/")
            or request.path in {"/api/auth/me", "/api/auth/logout"}
        ):
            return error("Support accounts must use the separate support portal.", 403)
        if session.get("auth_version", 0) != user.session_version:
            session.clear()
            return error("Your session has expired. Please sign in again.", 401)
        request.current_user = user
        from ..adult_family import sync_family_connections
        sync_family_connections(user)
        expire_gift_holds()
        return view(*args, **kwargs)
    return wrapped


def support_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if user is None or not user.is_support or session.get("auth_mode") != "support":
            return error("Support portal access required.", 403)
        if session.get("auth_version", 0) != user.session_version:
            session.clear()
            return error("Your session has expired. Please sign in again.", 401)
        request.current_user = user
        expire_gift_holds()
        return view(*args, **kwargs)
    return wrapped


def superuser_required(view):
    @wraps(view)
    @support_required
    def wrapped(*args, **kwargs):
        if not request.current_user.is_superuser:
            return error("Master support account required.", 403)
        return view(*args, **kwargs)
    return wrapped


def membership_for(user, household_id):
    if user is None:
        return None
    return HouseholdMembership.query.filter_by(
        user_id=user.id,
        household_id=household_id,
    ).first()


def pet_family_access(user, profile):
    if profile is None or profile.profile_type != "pet":
        return False
    household_ids = {
        row[0] for row in db.session.query(HouseholdProfileAccess.household_id)
        .join(Household, Household.id == HouseholdProfileAccess.household_id)
        .filter(
            HouseholdProfileAccess.profile_id == profile.id,
            Household.registry_type == "family",
        )
    }
    if not household_ids:
        return False
    memberships = HouseholdMembership.query.filter(
        HouseholdMembership.user_id == user.id,
        HouseholdMembership.household_id.in_(household_ids),
    ).all()
    if any(
        membership.is_family_member
        or membership.role in {"owner", "admin", "profile_manager"}
        for membership in memberships
    ):
        return True
    if not user.is_child or not user.parent_user_id:
        return False
    child_profile = PersonProfile.query.filter_by(
        account_user_id=user.id,
        profile_type="person",
    ).first()
    if child_profile is None:
        return False
    child_household_ids = {
        row[0] for row in db.session.query(HouseholdProfileAccess.household_id)
        .filter(HouseholdProfileAccess.profile_id == child_profile.id)
    }
    if not household_ids.intersection(child_household_ids):
        return False
    return HouseholdMembership.query.filter(
        HouseholdMembership.user_id == user.parent_user_id,
        HouseholdMembership.household_id.in_(household_ids),
        (
            HouseholdMembership.is_family_member.is_(True)
            | HouseholdMembership.role.in_(("owner", "admin", "profile_manager"))
        ),
    ).first() is not None


def profile_access(user, profile_id, write=False):
    profile = db.session.get(PersonProfile, profile_id)
    if profile is None:
        return None
    if not write and pet_family_access(user, profile):
        return profile
    linked = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
    if not write and linked and not linked.is_child and profile.is_adult and not HouseholdProfileAccess.query.filter_by(profile_id=profile.id).first() and FamilyFollow.query.filter_by(follower_id=user.id, followed_id=linked.id).first():
        return profile
    if write and linked and not linked.is_child and linked.id != user.id:
        return None
    if write and not profile.is_adult:
        family_homes = Household.query.join(HouseholdProfileAccess).filter(
            HouseholdProfileAccess.profile_id==profile.id, Household.registry_type=='family').all()
        if family_homes and not any(home.owner_id==user.id for home in family_homes):
            return None
    if linked and not linked.is_child and linked.id==user.id:
        return profile
    active_id = session.get('active_member_profile_id') if session.get('user_id') == user.id else None
    if write and active_id and active_id != profile.id and not (profile.is_adult and profile.account_user_id is None):
        active = db.session.get(PersonProfile, active_id)
        if not active or not active.is_guardian or profile.is_adult:
            return None
    if profile.account_user_id == user.id and not write:
        return profile
    grants = (
        db.session.query(HouseholdProfileAccess, HouseholdMembership)
        .join(HouseholdMembership, HouseholdMembership.household_id == HouseholdProfileAccess.household_id)
        .filter(
            HouseholdProfileAccess.profile_id == profile.id,
            HouseholdMembership.user_id == user.id,
        )
        .all()
    )
    for household_access, membership in grants:
        if membership.role in {"owner", "admin"}:
            if not write or household_access.can_edit:
                return profile
            continue
        if write:
            continue
        if membership.share_all_profiles or membership.is_family_member:
            return profile
        member_access = HouseholdMemberProfileAccess.query.filter_by(
            membership_id=membership.id,
            profile_id=profile.id,
        ).first()
        if member_access and not write:
            return profile
    return None


def can_manage_wishes(user, profile):
    if profile and profile.profile_type == "pet":
        return pet_family_access(user, profile)
    if profile is None:
        return False
    if profile_access(user, profile.id, write=True) is None:
        return False
    # Authorized family managers can manage unclaimed profiles; linked adults use their own login.
    return bool(session.get('active_member_profile_id') or not profile.is_adult or profile.account_user_id in (None,user.id))


def record_audit(actor_id, action, entity_type, entity_id=None, household_id=None, details=None):
    db.session.add(AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        household_id=household_id,
        details=details or {},
    ))


def profile_dict(profile, user):
    data = profile.public_dict()
    from ..adult_family import can_add_child_gift, can_suggest_profile
    data['can_add'] = (
        profile_access(user, profile.id, write=True) is not None
        or can_add_child_gift(user, profile)
        or pet_family_access(user, profile)
    )
    data['can_suggest'] = can_suggest_profile(user, profile)
    data['has_login'] = profile.account_user_id is not None
    data["is_you"] = profile.account_user_id == user.id
    manager = profile.account_user_id == user.id
    if not manager:
        manager = (
            db.session.query(HouseholdProfileAccess.id)
            .join(HouseholdMembership, HouseholdMembership.household_id == HouseholdProfileAccess.household_id)
            .filter(
                HouseholdProfileAccess.profile_id == profile.id,
                HouseholdProfileAccess.can_edit.is_(True),
                HouseholdMembership.user_id == user.id,
                HouseholdMembership.role.in_(("owner", "admin", "profile_manager")),
            )
            .first()
            is not None
        )
    if manager:
        linked_account = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
        data.update({"is_adult": profile.is_adult, "is_guardian": profile.is_guardian, "member_email": linked_account.email if linked_account and not linked_account.is_child else profile.member_email})
    if not manager:
        data["parent_notes"] = None
        data["items_to_avoid"] = None
        if not profile.birthday_shared:
            data["birthday"] = None
    if profile_access(user, profile.id, write=True) is not None:
        data["completion"] = profile_completion(profile)
    return data


def household_dict(household):
    membership = membership_for(request.current_user, household.id)
    return {
        **household.public_dict(),
        "role": ("family_member" if membership.is_family_member else membership.role) if membership else "support",
        "is_family_member": bool(membership and membership.is_family_member),
    }


def parse_birthday(value):
    if not value:
        return None
    if not isinstance(value, str):
        raise ValueError("Birthday must contain a valid month and day.")
    # Accept older clients' full dates, but retain only month/day for new writes.
    parts = value.split("-")
    if len(parts) not in {2, 3}:
        raise ValueError("Birthday must contain a valid month and day.")
    month, day = parts[-2:]
    return date(2000, int(month), int(day))


def create_household_profile(household_id, membership, payload):
    if not isinstance(payload, dict):
        raise ValueError("Each family profile must be an object.")
    name = str(payload.get("display_name", "")).strip()
    profile_type = payload.get("profile_type", "person")
    household = db.session.get(Household, household_id)
    is_company = household.registry_type == "company"
    if is_company and profile_type != "person":
        raise ValueError("Company registries use employee profiles.")
    relationship = payload.get("relationship", "employee" if is_company else "family_member")
    if is_company and relationship == "family_member":
        relationship = "employee"
    if not isinstance(relationship, str) or relationship not in FAMILY_RELATIONSHIPS:
        raise ValueError("Choose a supported family relationship.")
    avatar_key = payload.get("avatar_key", "paw" if profile_type == "pet" else "flower")
    if not name or len(name) > 120:
        raise ValueError("Each family member needs a name up to 120 characters.")
    if profile_type not in {"person", "pet"}:
        raise ValueError("Profile type must be person or pet.")
    if not valid_profile_avatar(avatar_key):
        raise ValueError("Choose a supported cartoon avatar.")
    if "allergies" in payload and (not isinstance(payload["allergies"], str) or len(payload["allergies"]) > 2000):
        raise ValueError("Allergies must be text within 2000 characters.")
    account_user_id = payload.get("account_user_id")
    if account_user_id is not None and account_user_id != request.current_user.id:
        raise ValueError("You may only link a profile to your own account.")
    birthday = None
    if payload.get("birthday"):
        try:
            birthday = parse_birthday(payload["birthday"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Birthday must contain a valid month and day.") from exc
    birthday_shared = payload.get("birthday_shared", False)
    if not isinstance(birthday_shared, bool):
        raise ValueError("birthday_shared must be a boolean.")
    for key in ("favorite_colors", "favorite_brands", "favorite_stores", "favorite_characters", "hobbies", "interests", "favorite_snacks"):
        if key in payload and not isinstance(payload[key], list):
            raise ValueError(f"{key} must be a list.")
    for key in ("clothing_sizes", "shoe_sizes"):
        if key in payload and not isinstance(payload[key], dict):
            raise ValueError(f"{key} must be an object.")
    profile = PersonProfile(
        account_user_id=account_user_id,
        display_name=name,
        profile_type=profile_type,
        is_adult=profile_type == "person" and (relationship in ADULT_RELATIONSHIPS or payload.get("is_adult") is True),
        birthday=birthday,
        birthday_shared=birthday_shared,
        avatar_key=avatar_key,
        favorite_colors=payload.get("favorite_colors") or [],
        favorite_brands=payload.get("favorite_brands") or [],
        favorite_stores=payload.get("favorite_stores") or [],
        favorite_characters=payload.get("favorite_characters") or [],
        hobbies=payload.get("hobbies") or [],
        interests=payload.get("interests") or [],
        clothing_sizes=payload.get("clothing_sizes") or {},
        shoe_sizes=payload.get("shoe_sizes") or {},
        gift_preferences=payload.get("gift_preferences"),
        allergies=payload.get("allergies"),
        favorite_snacks=payload.get("favorite_snacks") or [],
    )
    db.session.add(profile)
    db.session.flush()
    db.session.add(HouseholdProfileAccess(household_id=household_id, profile_id=profile.id, relationship=relationship))
    return profile


def save_profile_image(file_storage, entity_id):
    if file_storage is None or not file_storage.filename:
        return None, "Choose an image to upload."
    extension = Path(file_storage.filename or "").suffix.lower()
    signature_check = IMAGE_SIGNATURES.get(extension)
    if signature_check is None:
        return None, "Upload a JPG, JPEG, PNG, GIF, or WebP image."
    data = file_storage.stream.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        return None, "Images must be 5 MB or smaller."
    if not signature_check(data):
        return None, "The uploaded file does not match a supported image format."
    filename = f"{entity_id}-{uuid4().hex}{extension}"
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)
    (upload_folder / filename).write_bytes(data)
    return f"/api/uploads/{filename}", None


def require_household_admin(household_id):
    membership = membership_for(request.current_user, household_id)
    if not membership or membership.role not in {"owner", "admin"}:
        return None, error("Only a household parent or administrator can make changes.", 403)
    return membership, None


def reservation_summary(item, user):
    if user.is_child:
        return None
    active = GiftReservation.query.filter(
        GiftReservation.item_id == item.id,
        GiftReservation.status.in_(("reserved", "purchased")),
    ).all()
    reserved = sum(row.quantity for row in active if row.status == "reserved")
    purchased = sum(row.quantity for row in active if row.status == "purchased")
    buyers = []
    for row in active:
        if row.status == "purchased" and not row.purchase_secret:
            home = Household.query.filter_by(owner_id=row.shopper_id, registry_type="family").first()
            buyer = db.session.get(User, row.shopper_id)
            label = home.name if home else buyer.name if buyer else None
            if label and label not in buyers:
                buyers.append(label)
    return {
        **({"purchased_by": buyers} if buyers else {}),
        "reserved": reserved,
        "held_by_you": any(row.shopper_id == user.id and row.status == "reserved" for row in active),
        "purchased": purchased,
        "available": max(0, item.quantity - reserved - purchased),
    }


def item_dict(item, user):
    from ..commerce import shopping_url
    data = {
        "id": item.id,
        "profile_id": item.profile_id,
        "family_only": item.family_only,
        "list_managed": item.profile.profile_type == "pet" or not item.profile.is_adult,
        "name": item.name,
        "description": item.description,
        "image_path": item.image_path,
        "store_name": item.store_name,
        "product_url": shopping_link(item.product_url),
        "original_product_url": item.product_url,
        "shopping_url": shopping_url(item),
        "estimated_price": str(item.estimated_price) if item.estimated_price is not None else None,
        "currency": item.currency,
        "desired_size": item.desired_size,
        "desired_color": item.desired_color,
        "quantity": item.quantity,
        "category": item.category,
        "notes": item.notes,
        "priority": item.priority,
        "request_type": item.request_type,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }
    if data["list_managed"]:
        managed_lists = Wishlist.query.join(WishlistItemWishlist, WishlistItemWishlist.wishlist_id == Wishlist.id).filter(WishlistItemWishlist.item_id == item.id, Wishlist.share_publicly.isnot(None)).all()
        if managed_lists:
            data["family_only"] = not any(row.share_publicly for row in managed_lists)
    recipient_access = profile_access(user, item.profile_id) is not None
    data["recipient_preferences"] = gift_guide(item.profile) if recipient_access else None
    data["recipient_photo_path"] = item.profile.photo_path if recipient_access else None
    data["recipient_avatar_key"] = item.profile.avatar_key if recipient_access else None
    data["availability_alert"] = GiftAvailabilityAlert.query.filter_by(user_id=user.id, item_id=item.id, ready=False).first() is not None
    data["is_hearted"] = SavedGift.query.filter_by(user_id=user.id, item_id=item.id).first() is not None
    personal = PersonalWish.query.filter_by(item_id=item.id).first()
    data["personal_wish"] = personal is not None
    data["personal_owner_id"] = personal.owner_id if personal else None
    from ..adult_family import followed_ids
    data["followed_by_you"] = bool(personal and personal.owner_id in followed_ids(user))
    owner = db.session.get(User, personal.owner_id) if personal else None
    data["recipient"] = owner.name if owner else item.profile.display_name
    homes = db.session.query(Household).join(HouseholdProfileAccess).join(
        HouseholdMembership, HouseholdMembership.household_id == Household.id
    ).filter(HouseholdProfileAccess.profile_id == item.profile_id, HouseholdMembership.user_id == user.id).all()
    if personal and data['followed_by_you'] and personal_viewer_allowed(personal, user):
        existing_home_ids = {home.id for home in homes}
        homes += [home for home in Household.query.filter_by(owner_id=personal.owner_id, registry_type='family').all() if home.id not in existing_home_ids]
    data["households"] = [{"id": home.id, "name": home.name} for home in homes]
    home_ids = [home.id for home in homes]
    data["occasions"] = [link.occasion.name for link in item.occasions if link.occasion.household_id in home_ids]
    data["occasion_details"] = [{"name": link.occasion.name, "date": link.occasion.event_date.isoformat() if link.occasion.event_date else None} for link in item.occasions if link.occasion.household_id in home_ids]
    creator = db.session.get(User, item.created_by_id) if item.created_by_id else None
    data["added_by"] = creator.name if creator else "Family wishlist"
    summary = reservation_summary(item, user)
    if summary is not None:
        data["availability"] = summary
    return data


@api.get("/")
def index():
    return jsonify({"name": "Family Gift Registry API", "status": "ok"})


@api.get("/auth/csrf")
def csrf():
    return jsonify({"csrf_token": _csrf_token()})


@api.post("/auth/register")
@limiter.limit("5 per hour")
def register():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = normalized_email(payload.get("email"))
    password = payload.get("password", "")
    if not name or len(name) > 120 or not email or len(email) > 255:
        return error("Enter a valid name and email address.", 400)
    if not isinstance(password, str) or len(password) < 10:
        return error("Password must be at least 10 characters.", 400)
    if User.query.filter(func.lower(User.email) == email).first():
        return error("An account with that email already exists.", 409)
    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("An account with that email already exists.", 409)
    session.clear()
    session["user_id"] = user.id
    session["auth_version"] = user.session_version
    session["auth_mode"] = "family"
    current_app.session_interface.regenerate(session)
    return jsonify(session_payload(user)), 201


@api.post("/auth/login")
@limiter.limit("10 per minute")
def login():
    payload = request.get_json(silent=True) or {}
    email = normalized_email(payload.get("email")) or ""


    password = payload.get("password", "")
    user = User.query.filter(func.lower(User.email) == email).first()
    if user is None or not isinstance(password, str) or not user.check_password(password):
        return error("Email or password is incorrect.", 401)
    if user.is_child:
        return error("Use the child sign-in page for this account.", 403)
    if user.is_support:
        return error("This is a support account. Please use the separate support sign-in.", 403)
    session.clear()
    session["user_id"] = user.id
    session["auth_version"] = user.session_version
    session["auth_mode"] = "family"
    own = PersonProfile.query.filter_by(account_user_id=user.id, is_adult=True).order_by(PersonProfile.photo_path.isnot(None).desc(), PersonProfile.id).first()
    if own:
        session['active_member_profile_id'] = own.id
    current_app.session_interface.regenerate(session)
    from ..adult_family import sync_family_connections
    sync_family_connections(user)
    return jsonify(session_payload(user))


@api.post("/auth/support/login")
@limiter.limit("10 per minute")
def support_login():
    payload = request.get_json(silent=True) or {}
    email = normalized_email(payload.get("email")) or ""
    password = payload.get("password", "")
    user = User.query.filter(func.lower(User.email) == email).first()
    if user is None or not user.is_support or not isinstance(password, str) or not user.check_password(password):
        return error("Support email or password is incorrect.", 401)
    session.clear()
    session["user_id"] = user.id
    session["auth_version"] = user.session_version
    session["auth_mode"] = "support"
    current_app.session_interface.regenerate(session)
    return jsonify(session_payload(user))


@api.post("/auth/support/accept-invitation")
@limiter.limit("10 per hour")
def accept_support_invitation():
    payload = request.get_json(silent=True) or {}
    token = payload.get("token")
    name = payload.get("name")
    password = payload.get("password")
    if not isinstance(token, str) or not token or len(token) > 200:
        return error("This staff invitation is invalid or expired.", 400)
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        return error("Enter a name up to 120 characters.", 400)
    if not isinstance(password, str) or len(password) < 16:
        return error("Staff passwords must be at least 16 characters.", 400)

    invitation = SupportInvitation.query.filter_by(
        token_hash=hashlib.sha256(token.encode()).hexdigest()
    ).first()
    if invitation is None or invitation.accepted_at is not None:
        return error("This staff invitation is invalid or has already been used.", 400)
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        return error("This staff invitation has expired. Ask the master support account for a new one.", 400)
    if User.query.filter(func.lower(User.email) == invitation.email.lower()).first():
        return error("An account with this invited email already exists.", 409)

    user = User(name=name.strip(), email=invitation.email, is_support=True)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.flush()
        invitation.accepted_at = datetime.now(timezone.utc)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("This invitation could not be accepted. It may have already been used.", 409)
    session.clear()
    session["user_id"] = user.id
    session["auth_version"] = user.session_version
    session["auth_mode"] = "support"
    current_app.session_interface.regenerate(session)
    return jsonify({"user": user.public_dict(), "csrf_token": _csrf_token()}), 201


@api.post("/auth/logout")
@authenticated
def logout():
    session.clear()
    return jsonify({"status": "ok"})


def repair_accepted_family_sharing(user, commit=True):
    # Only automatic family invitations authorize reciprocal registry sharing.
    invitations = HouseholdInvitation.query.join(Household, Household.id == HouseholdInvitation.household_id).filter(
        HouseholdInvitation.accepted_at.isnot(None), HouseholdInvitation.share_all_profiles.is_(True),
        Household.registry_type == 'family', HouseholdInvitation.role.in_(('shopper','viewer')),
        or_(Household.owner_id == user.id, func.lower(HouseholdInvitation.email) == user.email.lower())).all()
    for invitation in invitations:
        sender_home = db.session.get(Household, invitation.household_id)
        recipient = User.query.filter(func.lower(User.email) == invitation.email.lower(), User.is_child.is_(False), User.is_support.is_(False)).first()
        if recipient is None or recipient.id == sender_home.owner_id:
            continue
        for home in Household.query.filter_by(owner_id=recipient.id, registry_type='family').all():
            membership = HouseholdMembership.query.filter_by(household_id=home.id, user_id=sender_home.owner_id).first()
            if membership is None:
                db.session.add(HouseholdMembership(household_id=home.id, user_id=sender_home.owner_id, role='shopper', share_all_profiles=True))
            elif membership.role in ('shopper','viewer'):
                membership.share_all_profiles = True
    if commit:
        db.session.commit()


def session_payload(user):
    """Return the current identity directly, independently of profile-switcher grants."""
    active_id = session.get('active_member_profile_id')
    profile = db.session.get(PersonProfile, active_id) if active_id else None
    if active_id and (not profile or profile.profile_type != 'person' or profile.account_user_id not in (None, user.id)
                    or profile_access(user, profile.id) is None):
        session.pop('active_member_profile_id', None)
        active_id = None
        profile = None
    if profile is None and not user.is_support:
        profile = PersonProfile.query.filter_by(account_user_id=user.id, profile_type='person').order_by(
            PersonProfile.is_adult.desc(), PersonProfile.photo_path.isnot(None).desc(), PersonProfile.id).first()
    identity = None
    if profile:
        photo = ('/api/child/profiles/'+str(user.id)+'/photo' if user.is_child and profile.photo_path else profile.photo_path)
        identity = {'id':profile.id, 'name':profile.display_name, 'photo_path':photo,
                    'avatar_key':profile.avatar_key, 'is_you':profile.account_user_id == user.id}
    homes = []
    if not user.is_support and not user.is_child:
        rows = db.session.query(Household, HouseholdMembership).join(HouseholdMembership,
            HouseholdMembership.household_id == Household.id).filter(HouseholdMembership.user_id == user.id).order_by(Household.name).all()
        homes = [{**home.public_dict(), 'role':'family_member' if membership.is_family_member else membership.role,
                  'is_family_member':membership.is_family_member} for home, membership in rows]
    return {'user':{**user.public_dict(), 'theme_key':user.theme_key,
                    'shared_theme':selected_shared_theme(user), 'theme_image_path':user.theme_image_path,
                    'active_member_profile_id':active_id, 'active_profile':identity,
                    'photo_path':identity['photo_path'] if identity else None,
                    'avatar_key':identity['avatar_key'] if identity else None,
                    'child_mode_locked':bool(session.get('household_return_user_id')),
                    'browsing_as':profile.display_name if active_id and profile else user.name},
            'households':homes, 'csrf_token':_csrf_token()}


@api.get("/auth/me")
@authenticated
def current_user():
    repair_accepted_family_sharing(request.current_user)
    return jsonify(session_payload(request.current_user))


@api.patch("/auth/profile")
@authenticated
def update_account():
    payload = request.get_json(silent=True) or {}
    user = request.current_user
    name = payload.get("name", user.name)
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        return error("Name is required and must be at most 120 characters.", 400)
    email = normalized_email(payload.get("email", user.email))
    if not email:
        return error("Enter a valid email address.", 400)
    if email.lower() != user.email.lower():
        password = payload.get("current_password", "")
        if not isinstance(password, str) or not user.check_password(password):
            return error("Enter your current password to change your email address.", 400)
        if User.query.filter(func.lower(User.email) == email.lower(), User.id != user.id).first():
            return error("An account with that email already exists.", 409)
        CoBuyInvitation.query.filter_by(email=user.email, accepted=True).update({"email": email})
        user.email = email
        user.session_version += 1
        session["auth_version"] = user.session_version
    user.name = name.strip()
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("This email address is already in use.", 409)
    return jsonify({"user": user.public_dict()})


@api.post("/auth/password")
@authenticated
@limiter.limit("5 per hour")
def change_password():
    payload = request.get_json(silent=True) or {}
    old_password = payload.get("old_password", "")
    new_password = payload.get("new_password", "")
    if not request.current_user.check_password(old_password):
        return error("Current password is incorrect.", 400)
    if not isinstance(new_password, str) or not 10 <= len(new_password) <= 1024:
        return error("New password must be at least 10 characters.", 400)
    user = request.current_user
    user.set_password(new_password)
    user.session_version += 1
    session['auth_version'] = user.session_version
    db.session.commit()
    return jsonify(status='updated', message='Password updated.')


@api.get("/households")
@authenticated
def list_households():
    households = (
        Household.query.join(HouseholdMembership)
        .filter(HouseholdMembership.user_id == request.current_user.id)
        .order_by(Household.name)
        .all()
    )
    return jsonify({"households": [household_dict(row) for row in households]})


@api.post("/households")
@authenticated
def create_household():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name or len(name) > 160:
        return error("Household name is required and must be at most 160 characters.", 400)
    profiles = payload.get("profiles", [])
    if not isinstance(profiles, list) or len(profiles) > 30:
        return error("Add no more than 30 family members at a time.", 400)
    registry_type = payload.get("registry_type", "family")
    if registry_type not in ("family", "company"):
        return error("Choose a family household or company registry.", 400)
    household = Household(name=name, owner_id=request.current_user.id, registry_type=registry_type)
    db.session.add(household)
    db.session.flush()
    membership = HouseholdMembership(
        household_id=household.id,
        user_id=request.current_user.id,
        role="owner",
    )
    db.session.add(membership)
    db.session.flush()
    own = None
    try:
        created = [create_household_profile(household.id, membership, profile_payload) for profile_payload in profiles]
        if registry_type == 'family' and 'self_profile_index' in payload:
            selected = payload['self_profile_index']
            if selected == 'new':
                own = create_household_profile(household.id, membership, {'display_name': request.current_user.name, 'account_user_id': request.current_user.id})
            elif type(selected) is int and 0 <= selected < len(created) and created[selected].profile_type == 'person':
                own = created[selected]
                own.account_user_id = request.current_user.id
            else:
                raise ValueError('Choose which adult family member is you, or add yourself.')
            own.is_adult = True
            own.is_guardian = True
            own.member_email = request.current_user.email
            session['active_member_profile_id'] = own.id
    except ValueError as exc:
        db.session.rollback()
        return error(str(exc), 400)
    db.session.commit()
    return jsonify({"household": household_dict(household), "self_profile_id": own.id if own else None}), 201


@api.get("/households/<int:household_id>")
@authenticated
def get_household(household_id):
    membership = membership_for(request.current_user, household_id)
    if not membership:
        return error("Household not found.", 404)
    household = db.session.get(Household, household_id)
    profile_query = PersonProfile.query.join(HouseholdProfileAccess).filter(
        HouseholdProfileAccess.household_id == household_id
    )
    if membership.role not in {"owner", "admin"} and not membership.share_all_profiles:
        shared_profile_ids = db.session.query(HouseholdMemberProfileAccess.profile_id).filter(
            HouseholdMemberProfileAccess.membership_id == membership.id
        )
        profile_query = profile_query.filter(HouseholdProfileAccess.profile_id.in_(shared_profile_ids))
    profiles = profile_query.order_by(PersonProfile.display_name).all()
    visible_profile_ids = [profile.id for profile in profiles]
    occasions_query = Occasion.query.filter(
        Occasion.household_id == household_id,
        or_(Occasion.profile_id.is_(None), Occasion.profile_id.in_(visible_profile_ids)),
    )
    occasions = occasions_query.order_by(Occasion.event_date).all()
    return jsonify({
        "household": household_dict(household),
        "profiles": [{
            **profile_dict(profile, request.current_user),
            "relationship": HouseholdProfileAccess.query.filter_by(household_id=household_id, profile_id=profile.id).first().relationship if membership.role in {"owner", "admin"} or membership.is_family_member else None,
            "can_edit": profile_access(request.current_user, profile.id, write=True) is not None,
            "can_remove_from_family": household.owner_id == request.current_user.id and profile.account_user_id != request.current_user.id,
            "can_add": profile_access(request.current_user, profile.id, write=True) is not None or __import__("backend.app.adult_family",fromlist=["can_add_child_gift"]).can_add_child_gift(request.current_user,profile),
        } for profile in profiles],
        "occasions": [{
            "id": row.id,
            "profile_id": row.profile_id,
            "profile_name": row.profile.display_name if row.profile_id else None,
            "name": row.name,
            "type": row.occasion_type,
            "date": row.event_date.isoformat(),
        } for row in occasions],
    })


@api.patch("/households/<int:household_id>")
@authenticated
def rename_household(household_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    payload = request.get_json(silent=True) or {}
    household = db.session.get(Household, household_id)
    if "name" in payload:
        name = str(payload.get("name", "")).strip()
        if not name or len(name) > 160:
            return error("Household name is required and must be at most 160 characters.", 400)
        household.name = name
    if "photo_path" in payload:
        photo_path = payload["photo_path"]
        if photo_path is not None:
            return error("Upload a household image using the photo upload endpoint.", 400)
        household.photo_path = photo_path
    db.session.commit()
    return jsonify({"household": household_dict(household)})


@api.post("/households/<int:household_id>/photo")
@authenticated
@limiter.limit("5 per hour")
def upload_household_photo(household_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    household = db.session.get(Household, household_id)
    image, failure = save_profile_image(request.files.get("image"), household_id)
    if failure:
        return error(failure, 400)
    AccountEmailCode.query.filter_by(user_id=household.owner_id, purpose='family_photo_change', used_at=None).update({'used_at': datetime.now(timezone.utc)})
    household.photo_path = image
    db.session.commit()
    return jsonify(photo_path=image, message='Photo updated.')


@api.post("/profiles/<int:profile_id>/photo")
@authenticated
def upload_profile_photo(profile_id):
    profile = profile_access(request.current_user, profile_id, write=True)
    if profile is None:
        return error("Profile not found or edit permission denied.", 404)
    image, failure = save_profile_image(request.files.get("image"), profile_id)
    if failure:
        return error(failure, 400)
    profile.photo_path = image
    db.session.commit()
    return jsonify({"photo_path": image, "completion": profile_completion(profile)})


@api.get("/uploads/<path:filename>")
@authenticated
def get_uploaded_image(filename):
    image_path = f"/api/uploads/{filename}"
    if request.current_user.theme_image_path == image_path:
        response = send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
        response.headers["Cache-Control"] = "private, no-store"
        return response
    household = Household.query.filter_by(photo_path=image_path).first()
    if household and membership_for(request.current_user, household.id):
        response = send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
        response.headers["Cache-Control"] = "private, no-store"
        return response
    profile = PersonProfile.query.filter_by(photo_path=image_path).first()
    if profile and profile_access(request.current_user, profile.id):
        response = send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
        response.headers["Cache-Control"] = "private, no-store"
        return response
    return error("Image not found.", 404)


@api.get("/households/<int:household_id>/members")
@authenticated
def list_members(household_id):
    membership = membership_for(request.current_user, household_id)
    if not membership:
        return error("Household not found.", 404)
    if membership.role not in {"owner", "admin"}:
        return error("Household owner or administrator permission required.", 403)
    members = (
        db.session.query(HouseholdMembership, User)
        .join(User, User.id == HouseholdMembership.user_id)
        .filter(HouseholdMembership.household_id == household_id)
        .order_by(User.name)
        .all()
    )
    invitations = HouseholdInvitation.query.filter_by(
        household_id=household_id,
        accepted_at=None,
    ).order_by(HouseholdInvitation.created_at.desc()).all()
    return jsonify({
        "members": [{
            **user.public_dict(),
            "role": row.role,
        } for row, user in members],
        "invitations": [{
            "id": row.id,
            "email": row.email,
            "role": row.role,
            "expires_at": row.expires_at.isoformat(),
        } for row in invitations],
    })


@api.delete("/households/<int:household_id>/members/<int:user_id>")
@authenticated
def remove_member(household_id, user_id):
    actor_membership = membership_for(request.current_user, household_id)
    target_user = db.session.get(User, user_id)
    target_membership = membership_for(target_user, household_id) if target_user else None
    if not actor_membership or actor_membership.role not in {"owner", "admin"}:
        return error("Household owner or administrator permission required.", 403)
    if not target_membership or target_membership.role == "owner":
        return error("Household member not found or cannot be removed.", 404)
    if actor_membership.role == "admin" and target_membership.role == "admin":
        return error("Only the household owner can remove an administrator.", 403)
    db.session.delete(target_membership)
    db.session.commit()
    return jsonify({"status": "removed"})


@api.post("/households/<int:household_id>/profiles/<int:profile_id>/share")
@authenticated
def share_profile(household_id, profile_id):
    actor_membership = membership_for(request.current_user, household_id)
    if not actor_membership or actor_membership.role not in {"owner", "admin"}:
        return error("Household owner or administrator permission required.", 403)
    profile = profile_access(request.current_user, profile_id, write=True)
    if profile is None:
        return error("Profile not found or edit permission denied.", 404)
    existing = HouseholdProfileAccess.query.filter_by(
        household_id=household_id,
        profile_id=profile_id,
    ).first()
    if existing:
        return error("Profile is already shared with this household.", 409)
    can_edit = (request.get_json(silent=True) or {}).get("can_edit", True)
    if not isinstance(can_edit, bool):
        return error("can_edit must be a boolean.", 400)
    access = HouseholdProfileAccess(
        household_id=household_id,
        profile_id=profile_id,
        can_edit=can_edit,
    )
    db.session.add(access)
    db.session.commit()
    return jsonify({"status": "shared", "profile_id": profile_id}), 201


@api.post("/households/<int:household_id>/invitations")
@authenticated
def invite_member(household_id):
    membership = membership_for(request.current_user, household_id)
    if not membership or (membership.role not in {"owner", "admin"} and not membership.is_family_member):
        return error("Household owner or administrator permission required.", 403)
    payload = request.get_json(silent=True) or {}
    if membership.is_family_member and payload.get('role', 'viewer') not in {'shopper', 'viewer'}:
        return error('Family members can invite followers, not grant administration.', 403)
    email = normalized_email(payload.get("email")) or ""
    if 'recipient_user_id' in payload:
        recipient_id = payload['recipient_user_id']
        recipient = db.session.get(User, recipient_id) if type(recipient_id) is int else None
        if not recipient or recipient.is_child or recipient.is_support or recipient.id == request.current_user.id:
            return error('Choose an adult account.', 400)
        email = recipient.email
    role = payload.get("role", "viewer")
    roles = {"admin", "profile_manager", "editor", "shopper", "viewer"}
    if not email or len(email) > 255 or role not in roles:
        return error("Enter a valid email and invitation role.", 400)
    share_all = payload.get('share_all_profiles', False)
    if type(share_all) is not bool or (share_all and role not in ('shopper','viewer')):
        return error('Automatic sharing is only for viewing family wishlists.',400)
    profile_ids = [row.profile_id for row in HouseholdProfileAccess.query.filter_by(household_id=household_id).all()] if share_all else payload.get("profile_ids", [])
    if not isinstance(profile_ids, list) or any(
        not isinstance(profile_id, int) or isinstance(profile_id, bool)
        for profile_id in profile_ids
    ):
        return error("Select one or more valid family profiles to share.", 400)
    profile_ids = sorted(set(profile_ids))
    if role in {"shopper", "viewer"} and not profile_ids and not share_all:
        return error("Choose the family members whose wishlists this invitation can view.", 400)
    if profile_ids:
        allowed_profile_ids = {
            row[0] for row in db.session.query(HouseholdProfileAccess.profile_id)
            .filter(
                HouseholdProfileAccess.household_id == household_id,
                HouseholdProfileAccess.profile_id.in_(profile_ids),
            )
        }
        if allowed_profile_ids != set(profile_ids):
            return error("One or more selected profiles are not in this household.", 404)
    token = secrets.token_urlsafe(32)
    invitation = HouseholdInvitation(
        household_id=household_id,
        email=email,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        role=role,
        profile_ids=profile_ids,
        share_all_profiles=share_all,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.session.add(invitation)
    db.session.commit()
    message = prepare_invitation(email, token, db.session.get(Household, household_id).name, db.session.get(Household, household_id).registry_type)
    return jsonify({
        "email_message": message,
        "invitation": {
            "email": email,
            "role": role,
            "profile_ids": profile_ids,
            "expires_at": invitation.expires_at.isoformat(),
            "token": token,
        },
    }), 201


@api.delete("/households/<int:household_id>/invitations/<int:invitation_id>")
@authenticated
def revoke_invitation(household_id, invitation_id):
    membership = membership_for(request.current_user, household_id)
    if not membership or membership.role not in {"owner", "admin"}:
        return error("Household owner or administrator permission required.", 403)
    invitation = HouseholdInvitation.query.filter_by(
        id=invitation_id,
        household_id=household_id,
        accepted_at=None,
    ).first()
    if invitation is None:
        return error("Invitation not found.", 404)
    db.session.delete(invitation)
    db.session.commit()
    return jsonify({"status": "revoked"})


@api.post("/invitations/accept")
@authenticated
def accept_invitation():
    token = str((request.get_json(silent=True) or {}).get("token", ""))
    invitation_id = (request.get_json(silent=True) or {}).get('invitation_id')
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        invitation = HouseholdInvitation.query.filter_by(token_hash=token_hash).with_for_update().first()
    elif type(invitation_id) is int:
        invitation = HouseholdInvitation.query.filter_by(id=invitation_id, email=request.current_user.email).with_for_update().first()
    else:
        return error('Invitation token or request is required.', 400)
    now = datetime.now(timezone.utc)
    if not invitation or invitation.declined_at or invitation.expires_at.replace(tzinfo=timezone.utc) <= now:
        return error("Invitation is invalid or expired.", 400)
    if invitation.email.lower() != request.current_user.email.lower():
        return error("This invitation was sent to a different email address.", 403)
    if invitation.transfer_owner_on_accept:
        if invitation.accepted_at:
            return jsonify({
                "status": "accepted",
                "household_id": invitation.household_id,
                "profile_ids": invitation.profile_ids or [],
                "joined_family": True,
            })
        household = db.session.get(Household, invitation.household_id)
        profile = db.session.get(PersonProfile, invitation.linked_profile_id) if invitation.linked_profile_id else None
        setup_creator = db.session.get(User, invitation.setup_created_by_id) if invitation.setup_created_by_id else None
        profile_access_row = HouseholdProfileAccess.query.filter_by(
            household_id=invitation.household_id,
            profile_id=invitation.linked_profile_id,
        ).first() if invitation.linked_profile_id else None
        if (
            request.current_user.is_child
            or request.current_user.is_support
            or household is None
            or household.registry_type != "family"
            or setup_creator is None
            or not setup_creator.is_support
            or household.owner_id != setup_creator.id
            or profile is None
            or profile_access_row is None
            or profile.account_user_id is not None
        ):
            return error("This family setup invitation is no longer available.", 409)

        membership = membership_for(request.current_user, household.id)
        if membership is None:
            membership = HouseholdMembership(
                household_id=household.id,
                user_id=request.current_user.id,
                role="owner",
            )
            db.session.add(membership)
        else:
            membership.role = "owner"
        household.owner_id = request.current_user.id
        profile.account_user_id = request.current_user.id
        profile.member_email = request.current_user.email
        profile.is_adult = True
        profile.is_guardian = True
        invitation.accepted_at = now
        session["active_member_profile_id"] = profile.id
        record_audit(
            request.current_user.id,
            "family.support_setup_claimed",
            "household",
            household.id,
            household.id,
            {"profile_id": profile.id},
        )
        db.session.commit()
        return jsonify({
            "status": "accepted",
            "household_id": household.id,
            "profile_ids": [profile.id],
            "joined_family": True,
        })
    if invitation.linked_profile_id:
        from ..adult_family import accept_adult_invitation
        return accept_adult_invitation(invitation, request.current_user)
    if invitation.accepted_at:
        return jsonify({"status": "accepted", "household_id": invitation.household_id, "profile_ids": invitation.profile_ids or []})
    existing_membership = membership_for(request.current_user, invitation.household_id)
    if existing_membership:
        if existing_membership.role == "viewer" and invitation.role in {
            "owner", "admin", "profile_manager", "editor", "shopper"
        }:
            existing_membership.role = invitation.role
    else:
        db.session.add(HouseholdMembership(
            household_id=invitation.household_id,
            user_id=request.current_user.id,
            role=invitation.role,
        ))
    if invitation.share_all_profiles:
        db.session.flush()
        membership_for(request.current_user, invitation.household_id).share_all_profiles = True
    for profile_id in invitation.profile_ids or []:
        access = HouseholdProfileAccess.query.filter_by(
            household_id=invitation.household_id,
            profile_id=profile_id,
        ).first()
        if access is None:
            db.session.rollback()
            return error("A shared profile is no longer available.", 409)
        if invitation.role in {"owner", "admin", "profile_manager", "editor"}:
            access.can_edit = True
        membership = membership_for(request.current_user, invitation.household_id)
        existing_access = HouseholdMemberProfileAccess.query.filter_by(
            membership_id=membership.id,
            profile_id=profile_id,
        ).first()
        if existing_access is None:
            db.session.add(HouseholdMemberProfileAccess(
                membership_id=membership.id,
                profile_id=profile_id,
                can_edit=invitation.role in {"profile_manager", "editor"},
            ))
    household = db.session.get(Household, invitation.household_id)
    if household.registry_type == 'family' and household.owner_id != request.current_user.id:
        for follower, followed in ((household.owner_id, request.current_user.id), (request.current_user.id, household.owner_id)):
            if not FamilyFollow.query.filter_by(follower_id=follower, followed_id=followed).first():
                db.session.add(FamilyFollow(follower_id=follower, followed_id=followed))
    invitation.accepted_at = now
    db.session.flush()
    repair_accepted_family_sharing(request.current_user, commit=False)
    record_audit(
        request.current_user.id,
        "invitation.accepted",
        "household_invitation",
        invitation.id,
        invitation.household_id,
        {"role": invitation.role, "profile_ids": invitation.profile_ids or []},
    )
    db.session.commit()
    return jsonify({
        "status": "accepted",
        "household_id": invitation.household_id,
        "profile_ids": invitation.profile_ids or [],
    })


@api.post("/households/<int:household_id>/profiles")
@authenticated
def create_profile(household_id):
    membership, failure = require_household_admin(household_id)
    if failure:
        return failure
    payload = request.get_json(silent=True) or {}
    try:
        profile = create_household_profile(household_id, membership, payload)
    except ValueError as exc:
        return error(str(exc), 400)
    profile.favorite_brands = payload.get("favorite_brands") or []
    profile.favorite_stores = payload.get("favorite_stores") or []
    profile.clothing_sizes = payload.get("clothing_sizes") or {}
    profile.shoe_sizes = payload.get("shoe_sizes") or {}
    db.session.commit()
    return jsonify({"profile": {
        **profile_dict(profile, request.current_user),
        "can_edit": True,
    }}), 201


@api.get("/profiles/<int:profile_id>")
@authenticated
def get_profile(profile_id):
    profile = profile_access(request.current_user, profile_id)
    if profile is None:
        return error("Profile not found.", 404)
    return jsonify({"profile": {
        **profile_dict(profile, request.current_user),
        "can_edit": profile_access(request.current_user, profile_id, write=True) is not None,
        "can_remove_wishes": can_manage_wishes(request.current_user, profile),
    }})


@api.patch("/profiles/<int:profile_id>")
@authenticated
def update_profile(profile_id):
    profile = profile_access(request.current_user, profile_id, write=True)
    if profile is None:
        return error("Profile not found or edit permission denied.", 404)
    payload = request.get_json(silent=True) or {}
    linked_account = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
    if linked_account and not linked_account.is_child and payload.get('is_adult') is False:
        return error('An adult login must keep an adult profile.', 400)
    for flag in ("is_adult", "is_guardian"):
        if flag in payload:
            if not isinstance(payload[flag], bool):
                return error("Adult and guardian options must be true or false.", 400)
            setattr(profile, flag, payload[flag])
    if profile.is_guardian and not profile.is_adult:
        return error("Only an adult profile can be a parent or guardian.", 400)
    if "member_email" in payload:
        email = normalized_email(payload["member_email"]) if payload["member_email"] else None
        if payload["member_email"] and not email:
            return error("Enter a valid member email.", 400)
        profile.member_email = email
    allowed = {
        "display_name", "profile_type", "avatar_key", "share_wishlist", "birthday_shared", "favorite_colors", "favorite_brands",
        "favorite_stores",
        "favorite_characters", "hobbies", "interests", "clothing_sizes",
        "shoe_sizes", "gift_preferences", "parent_notes", "items_to_avoid", "allergies", "favorite_snacks",
    }
    if "display_name" in payload and (
        not isinstance(payload["display_name"], str)
        or not payload["display_name"].strip()
        or len(payload["display_name"].strip()) > 120
    ):
        return error("Profile name is required and must be at most 120 characters.", 400)
    if "birthday_shared" in payload and not isinstance(payload["birthday_shared"], bool):
        return error("birthday_shared must be a boolean.", 400)
    if "profile_type" in payload and payload["profile_type"] not in {"person", "pet"}:
        return error("Profile type must be person or pet.", 400)
    if "share_wishlist" in payload:
        if not isinstance(payload["share_wishlist"], bool):
            return error("Pet wishlist sharing must be true or false.", 400)
        if profile.profile_type != "pet":
            return error("Wishlist sharing is only available for pet profiles.", 400)
    if "avatar_key" in payload and not valid_profile_avatar(payload["avatar_key"]):
        return error("Choose a supported cartoon avatar.", 400)
    if payload.get('use_avatar') is True and 'avatar_key' in payload:
        profile.photo_path = None
    for key in ("favorite_colors", "favorite_brands", "favorite_stores", "favorite_characters", "hobbies", "interests", "favorite_snacks"):
        if key in payload and not isinstance(payload[key], list):
            return error(f"{key} must be a list.", 400)
    for key in ("clothing_sizes", "shoe_sizes"):
        if key in payload and not isinstance(payload[key], dict):
            return error(f"{key} must be an object.", 400)
    birthday = None
    if "birthday" in payload and payload["birthday"]:
        try:
            birthday = parse_birthday(payload["birthday"])
        except (TypeError, ValueError):
            return error("Birthday must contain a valid month and day.", 400)
    if "allergies" in payload and (not isinstance(payload["allergies"], str) or len(payload["allergies"]) > 2000):
        return error("Allergies must be text within 2000 characters. Enter none known if applicable.", 400)
    for key in allowed.intersection(payload):
        value = payload[key]
        if key == "display_name":
            value = value.strip()
        setattr(profile, key, value)
    if profile.profile_type == "pet":
        profile.is_adult = False
        profile.is_guardian = False
        profile.account_user_id = None
        profile.share_wishlist = bool(profile.share_wishlist)
    elif "profile_type" in payload:
        profile.share_wishlist = False
    if "birthday" in payload:
        profile.birthday = birthday
    db.session.commit()
    return jsonify({"profile": {
        **profile_dict(profile, request.current_user),
        "can_edit": True,
        "can_remove_wishes": can_manage_wishes(request.current_user, profile),
    }})


@api.post('/profiles/<int:profile_id>/favorite-stores')
@authenticated
def add_favorite_store(profile_id):
    profile = PersonProfile.query.filter_by(id=profile_id).with_for_update().first()
    if request.current_user.is_child or request.current_user.is_support or not profile or profile_access(request.current_user, profile_id, write=True) is None:
        return error('You can only update favorite stores for profiles you manage.', 403)
    name = (request.get_json(silent=True) or {}).get('store')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        return error('Choose a store name within 120 characters.', 400)
    stores = [value.strip() for value in (profile.favorite_stores or [])
              if isinstance(value, str) and value.strip() and value.strip().casefold() != 'none']
    if not any(value.casefold() == name.strip().casefold() for value in stores):
        if len(stores) >= 100:
            return error('You already have 100 favorite stores. Edit the profile to remove one first.', 400)
        stores.append(name.strip())
    profile.favorite_stores = stores
    db.session.commit()
    return jsonify(favorite_stores=stores, completion=profile_completion(profile))


@api.get("/profiles/<int:profile_id>/occasions")
@authenticated
def list_occasions(profile_id):
    profile = profile_access(request.current_user, profile_id)
    if profile is None:
        return error("Profile not found.", 404)
    households = db.session.query(HouseholdProfileAccess.household_id).join(
        HouseholdMembership, HouseholdMembership.household_id == HouseholdProfileAccess.household_id
    ).filter(HouseholdProfileAccess.profile_id == profile_id, HouseholdMembership.user_id == request.current_user.id)
    rows = Occasion.query.filter(or_(Occasion.profile_id == profile_id,
        (Occasion.profile_id.is_(None) & Occasion.household_id.in_(households)))).order_by(Occasion.event_date).all()
    return jsonify({"occasions": [{
        "id": row.id,
        "household_id": row.household_id,
        "profile_id": row.profile_id,
        "name": row.name,
        "type": row.occasion_type,
        "date": row.event_date.isoformat(),
        "description": row.description,
    } for row in rows]})


@api.post("/households/<int:household_id>/occasions")
@authenticated
def create_occasion(household_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    occasion_type = payload.get("type", "other")
    profile_id = payload.get("profile_id")
    try:
        event_date = date.fromisoformat(payload.get("date", ""))
    except (TypeError, ValueError):
        return error("A valid occasion date is required.", 400)
    if not name or len(name) > 160 or occasion_type not in {
        "christmas", "halloween", "easter", "hanukkah", "diwali", "eid", "birthday",
        "anniversary", "baby_shower", "graduation", "wedding", "communion", "other",
    }:
        return error("Enter an occasion name and supported type.", 400)
    if profile_id and not HouseholdProfileAccess.query.filter_by(
        household_id=household_id, profile_id=profile_id
    ).first():
        return error("Profile not found in this household.", 404)
    if profile_id and profile_access(request.current_user, profile_id, write=True) is None:
        return error("Profile is not shared with your account or edit permission is denied.", 403)
    occasion = Occasion(
        household_id=household_id,
        profile_id=profile_id,
        name=name,
        occasion_type=occasion_type,
        event_date=event_date,
        description=payload.get("description"),
    )
    db.session.add(occasion)
    if profile_id:
        db.session.flush()
        db.session.add(Wishlist(
            profile_id=profile_id,
            occasion_id=occasion.id,
            title=f"{name} wishes",
        ))
    db.session.commit()
    return jsonify({"occasion": {
        "id": occasion.id, "name": occasion.name, "type": occasion.occasion_type,
        "date": occasion.event_date.isoformat(), "profile_id": occasion.profile_id,
    }}), 201


def empty_legacy_default_list(row):
    return (row.is_everyday and row.title == 'Everyday Wants & Needs'
            and not WishlistItemWishlist.query.filter_by(wishlist_id=row.id).first())


@api.get("/profiles/<int:profile_id>/wishlists")
@authenticated
def list_wishlists(profile_id):
    profile = profile_access(request.current_user, profile_id)
    if profile is None:
        return error("Profile not found.", 404)
    rows = Wishlist.query.filter_by(profile_id=profile_id).order_by(Wishlist.is_everyday.desc(), Wishlist.id).all()
    rows = [row for row in rows if not empty_legacy_default_list(row)]
    family_view = bool(rows and list_family_access(rows[0], request.current_user))
    populated = set()
    if not family_view:
        for item, list_id in db.session.query(WishlistItem, WishlistItemWishlist.wishlist_id).join(
                WishlistItemWishlist, WishlistItemWishlist.item_id == WishlistItem.id).filter(
                WishlistItemWishlist.wishlist_id.in_([row.id for row in rows]),
                WishlistItem.profile_id == profile_id).all():
            if item_audience_allowed(item, request.current_user):
                populated.add(list_id)
    return jsonify({"wishlists": [{
        "id": row.id, "title": row.title, "is_everyday": row.is_everyday, "occasion_id": row.occasion_id, "share_publicly": list_is_shared(row),
    } for row in rows if (family_view or row.id in populated)
        and (list_is_shared(row) or family_view)]})


@api.post("/profiles/<int:profile_id>/wishlists")
@authenticated
def create_wishlist(profile_id):
    profile = profile_access(request.current_user, profile_id, write=True)
    if profile is None:
        return error("Profile not found or edit permission denied.", 404)
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    if not title or len(title) > 160:
        return error("Wishlist title is required.", 400)
    occasion_id = payload.get("occasion_id")
    if payload.get("occasion_type"):
        kind = payload["occasion_type"]
        if kind not in {"christmas", "birthday", "wedding", "baby_shower", "anniversary", "other"}:
            return error("Choose a supported occasion.", 400)
        today = date.today()
        if payload.get("occasion_date"):
            try:
                event_date = date.fromisoformat(payload["occasion_date"])
            except (ValueError, TypeError):
                return error("Enter a valid occasion date.", 400)
        elif kind == "christmas":
            event_date = date(today.year, 12, 25)
            if event_date < today:
                event_date = date(today.year + 1, 12, 25)
        elif kind == "birthday" and profile.birthday:
            # February 29 birthdays use February 28 in non-leap years.
            import calendar
            year = today.year
            day = min(profile.birthday.day, calendar.monthrange(year, profile.birthday.month)[1])
            event_date = date(year, profile.birthday.month, day)
            if event_date < today:
                year += 1
                day = min(profile.birthday.day, calendar.monthrange(year, profile.birthday.month)[1])
                event_date = date(year, profile.birthday.month, day)
        else:
            return error("Choose a date for this occasion, or save a birthday in the profile first.", 400)
        household = db.session.query(HouseholdProfileAccess).join(
            HouseholdMembership, HouseholdMembership.household_id == HouseholdProfileAccess.household_id
        ).filter(HouseholdProfileAccess.profile_id == profile_id,
                 HouseholdMembership.user_id == request.current_user.id).first()
        if household is None:
            return error("Household not found.", 404)
        occasion = Occasion(household_id=household.household_id, profile_id=profile_id,
            name=title, occasion_type=kind, event_date=event_date)
        db.session.add(occasion)
        db.session.flush()
        occasion_id = occasion.id
    elif occasion_id:
        occasion = db.session.get(Occasion, occasion_id)
        if not occasion or (occasion.profile_id != profile_id and (occasion.profile_id is not None or
            not HouseholdProfileAccess.query.filter_by(profile_id=profile_id, household_id=occasion.household_id).first() or
            not membership_for(request.current_user, occasion.household_id))):
            return error("Occasion not found for this profile.", 404)
    wishlist = Wishlist(profile_id=profile_id, title=title, occasion_id=occasion_id, share_publicly=False if profile.profile_type == "pet" or not profile.is_adult else None)
    db.session.add(wishlist)
    db.session.commit()
    return jsonify({"wishlist": {
        "id": wishlist.id, "title": wishlist.title, "is_everyday": wishlist.is_everyday,
        "occasion_id": wishlist.occasion_id, "share_publicly": list_is_shared(wishlist),
    }}), 201


@api.get("/wishlists/<int:wishlist_id>/items")
@authenticated
def list_wishlist_items(wishlist_id):
    wishlist = db.session.get(Wishlist, wishlist_id)
    if not wishlist or not profile_access(request.current_user, wishlist.profile_id):
        return error("Wishlist not found.", 404)
    if not list_is_shared(wishlist) and not list_family_access(wishlist, request.current_user):
        return jsonify(items=[])
    items = (
        WishlistItem.query.join(WishlistItemWishlist)
        .filter(
            WishlistItemWishlist.wishlist_id == wishlist_id,
            WishlistItem.profile_id == wishlist.profile_id,
        )
        .order_by(WishlistItem.priority.desc(), WishlistItem.created_at.desc())
        .all()
    )
    return jsonify({"items": [item_dict(row, request.current_user) for row in items if item_audience_allowed(row, request.current_user)]})


@api.post("/wishlists/<int:wishlist_id>/items")
@authenticated
def create_gift(wishlist_id):
    wishlist = db.session.get(Wishlist, wishlist_id)
    from ..adult_family import can_add_child_gift
    if not wishlist or not (can_manage_wishes(request.current_user, db.session.get(PersonProfile, wishlist.profile_id)) or
            can_add_child_gift(request.current_user, db.session.get(PersonProfile, wishlist.profile_id))):
        return error("Wishlist not found or edit permission denied.", 404)
    payload = request.get_json(silent=True) or {}
    if type(payload.get('avoid_duplicate',False)) is not bool:
        return error('Choose a valid duplicate-save option.',400)
    if payload.get('avoid_duplicate'):
        from ..commerce_urls import validated_product_url
        try:
            validated_product_url(payload.get('product_url'))
            if payload.get('image_url'):
                validated_product_url(payload['image_url'])
            for field,limit in (('description',2000),('notes',2000),('store_name',120)):
                if payload.get(field) is not None and (not isinstance(payload[field],str) or len(payload[field])>limit):
                    raise ValueError('Keep gift details within their field limits.')
        except ValueError as exc:
            return error(str(exc),400)
        db.session.query(Wishlist.id).filter_by(id=wishlist.id).with_for_update().first()
        existing=WishlistItem.query.join(WishlistItemWishlist).filter(WishlistItemWishlist.wishlist_id==wishlist.id,WishlistItem.product_url==payload['product_url']).first()
        if existing:
            return jsonify(item=item_dict(existing,request.current_user),already_saved=True),200
    name = str(payload.get("name", "")).strip()
    try:
        quantity = int(payload.get("quantity", 1))
        priority = int(payload.get("priority", 2))
        price = Decimal(str(payload["estimated_price"])) if payload.get("estimated_price") not in (None, "") else None
    except (TypeError, ValueError, InvalidOperation):
        return error("Quantity, priority, or price is invalid.", 400)
    if not name or len(name) > 200 or quantity < 1 or priority not in {1, 2, 3, 4}:
        return error("Enter a gift name, positive quantity, and priority from 1 to 4.", 400)
    if price is not None and (
        not price.is_finite() or price < 0 or price > Decimal("99999999.99")
    ):
        return error("Price must be a non-negative amount.", 400)
    product_url = payload.get("product_url")
    if product_url:
        if not isinstance(product_url, str) or len(product_url) > 2000:
            return error("Product URL must be a valid URL up to 2000 characters.", 400)
        parsed_url = urlsplit(product_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
            return error("Product URL must use HTTP or HTTPS and include a host.", 400)
    if not isinstance(payload.get('family_only',False),bool):
        return error('Family-only visibility must be true or false.',400)
    item = WishlistItem(
        profile_id=wishlist.profile_id,
        family_only=payload.get('family_only',False),
        created_by_id=request.current_user.id,
        name=name,
        description=payload.get("description"),
        store_name=payload.get("store_name"),
        product_url=product_url,
        image_path=safe_product_url(payload.get("image_url")),
        estimated_price=price,
        currency=str(payload.get("currency", "USD")).upper()[:3],
        desired_size=payload.get("desired_size"),
        desired_color=payload.get("desired_color"),
        quantity=quantity,
        category=payload.get("category"),
        notes=payload.get("notes"),
        priority=priority,
        request_type=payload.get("request_type", "want"),
    )
    if not isinstance(item.request_type, str) or item.request_type not in {
        "want", "need", "parent_recommendation"
    }:
        return error("Request type must be want, need, or parent_recommendation.", 400)
    currency = payload.get("currency", "USD")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
        return error("Currency must be a three-letter code.", 400)
    item.currency = currency.upper()
    db.session.add(item)
    db.session.flush()
    db.session.add(WishlistItemWishlist(item_id=item.id, wishlist_id=wishlist.id))
    if wishlist.occasion_id:
        db.session.add(WishlistItemOccasion(item_id=item.id, occasion_id=wishlist.occasion_id))
    from ..commerce import record_product_metadata
    record_product_metadata(item)
    db.session.commit()
    return jsonify({"item": item_dict(item, request.current_user)}), 201


@api.patch("/items/<int:item_id>")
@authenticated
def update_gift(item_id):
    item = db.session.get(WishlistItem, item_id)
    if item is None or not can_manage_wishes(request.current_user, item.profile):
        return error("Gift not found or edit permission denied.", 404)
    payload = request.get_json(silent=True) or {}
    if 'currency' in payload and (not isinstance(payload['currency'],str) or not re.fullmatch('[A-Za-z]{3}',payload['currency'])):
        return error('Choose a valid three-letter currency.',400)
    if 'currency' in payload:
        payload['currency']=payload['currency'].upper()
    if "family_only" in payload:
        if not isinstance(payload["family_only"], bool):
            return error("Family-only visibility must be true or false.", 400)
        item.family_only = payload["family_only"]
        if item.family_only:
            for hold in GiftReservation.query.filter_by(item_id=item.id, status="reserved").all():
                shopper = db.session.get(User, hold.shopper_id)
                if not item_audience_allowed(item, shopper):
                    hold.status = "cancelled"
    string_fields = {
        "name", "description", "store_name", "product_url", "currency", "desired_size",
        "desired_color", "category", "notes", "request_type",
    }
    for key in string_fields.intersection(payload):
        setattr(item, key, payload[key])
    if "quantity" in payload:
        try:
            quantity = int(payload["quantity"])
        except (TypeError, ValueError):
            return error("Quantity must be a positive integer.", 400)
        if quantity < 1:
            return error("Quantity must be a positive integer.", 400)
        item.quantity = quantity
    if "priority" in payload:
        try:
            priority = int(payload["priority"])
        except (TypeError, ValueError):
            return error("Priority must be from 1 to 4.", 400)
        if priority not in {1, 2, 3, 4}:
            return error("Priority must be from 1 to 4.", 400)
        item.priority = priority
    if "request_type" in payload and (
        not isinstance(payload["request_type"], str)
        or payload["request_type"] not in {"want", "need", "parent_recommendation"}
    ):
        return error("Request type must be want, need, or parent_recommendation.", 400)
    if "name" in payload and (not str(payload["name"]).strip() or len(str(payload["name"])) > 200):
        return error("Gift name is required and must be at most 200 characters.", 400)
    if "product_url" in payload and payload["product_url"]:
        if not isinstance(payload["product_url"], str) or len(payload["product_url"]) > 2000:
            return error("Product URL must be a valid URL up to 2000 characters.", 400)
        parsed_url = urlsplit(payload["product_url"])
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
            return error("Product URL must use HTTP or HTTPS and include a host.", 400)
    if "estimated_price" in payload:
        try:
            price = Decimal(str(payload["estimated_price"])) if payload["estimated_price"] not in (None, "") else None
        except (TypeError, ValueError, InvalidOperation):
            return error("Price is invalid.", 400)
        if price is not None and (not price.is_finite() or price < 0 or price > Decimal("99999999.99")):
            return error("Price must be a non-negative amount.", 400)
        item.estimated_price = price
    db.session.commit()
    return jsonify({"item": item_dict(item, request.current_user)})


@api.get('/wish-edit-targets')
@authenticated
def wish_edit_targets():
    from ..adult_family import family_ids
    homes = family_ids(request.current_user)
    profiles = PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id.in_(homes)).distinct().all()
    return jsonify(profiles=[{'id': p.id, 'name': p.display_name, 'wishlists': [{'id': w.id, 'title': w.title} for w in Wishlist.query.filter_by(profile_id=p.id).all()]} for p in profiles if profile_access(request.current_user, p.id, write=True)])


@api.post('/items/<int:item_id>/organize')
@authenticated
def organize_wish(item_id):
    item = WishlistItem.query.filter_by(id=item_id).with_for_update().first()
    if not item or not can_manage_wishes(request.current_user, item.profile):
        return error('Wish edit permission denied.', 403)
    payload = request.get_json()
    action = payload.get('action')
    if action == 'received':
        purchased = sum(r.quantity for r in item.reservations if r.status == 'purchased')
        for hold in item.reservations:
            if hold.status == 'reserved':
                hold.status = 'cancelled'
        if purchased < item.quantity:
            db.session.add(GiftReservation(item_id=item.id, shopper_id=request.current_user.id, quantity=item.quantity-purchased, status='purchased', purchase_secret=True))
        db.session.commit()
        return jsonify(status='purchased')
    if action not in ('move', 'copy'):
        return error('Choose move, copy or received.', 400)
    target = db.session.get(Wishlist, payload.get('wishlist_id')) if type(payload.get('wishlist_id')) is int else None
    from ..adult_family import family_ids
    allowed = target and HouseholdProfileAccess.query.filter(HouseholdProfileAccess.profile_id == target.profile_id, HouseholdProfileAccess.household_id.in_(family_ids(request.current_user))).first()
    if not allowed or not profile_access(request.current_user, target.profile_id, write=True):
        return error('Choose an editable list in your family.', 403)
    if action == 'move' and any(r.status in ('reserved', 'purchased') for r in item.reservations):
        return error('Held or purchased wishes cannot be moved. Copy the wish instead.', 409)
    if action == 'copy':
        values = {column.name: getattr(item, column.name) for column in WishlistItem.__table__.columns if column.name not in ('id', 'profile_id', 'created_by_id', 'created_at', 'updated_at')}
        result = WishlistItem(profile_id=target.profile_id, created_by_id=request.current_user.id, **values)
        db.session.add(result); db.session.flush()
    else:
        result = item
        PersonalWish.query.filter_by(item_id=item.id).delete()
        SavedGift.query.filter_by(item_id=item.id).delete()
        item.wishlists.clear(); item.occasions.clear()
        item.profile_id = target.profile_id
    result.family_only = True
    db.session.add(WishlistItemWishlist(item_id=result.id, wishlist_id=target.id))
    if target.occasion_id:
        db.session.add(WishlistItemOccasion(item_id=result.id, occasion_id=target.occasion_id))
    db.session.commit()
    return jsonify(item=item_dict(result, request.current_user))


@api.delete("/items/<int:item_id>")
@authenticated
def delete_gift(item_id):
    item = db.session.get(WishlistItem, item_id)
    if item is None or not can_manage_wishes(request.current_user, item.profile):
        return error("Gift not found or edit permission denied.", 404)
    SavedGift.query.filter_by(item_id=item.id).delete()
    reservation_ids = db.session.query(GiftReservation.id).filter_by(item_id=item.id)
    CoBuyInvitation.query.filter(CoBuyInvitation.reservation_id.in_(reservation_ids)).delete(synchronize_session=False)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "deleted"})


@api.post("/items/<int:item_id>/wishlists")
@authenticated
def link_gift_to_wishlist(item_id):
    item = db.session.get(WishlistItem, item_id)
    if item is None or not profile_access(request.current_user, item.profile_id, write=True):
        return error("Gift not found or edit permission denied.", 404)
    payload = request.get_json(silent=True) or {}
    wishlist_id = payload.get("wishlist_id")
    wishlist = db.session.get(Wishlist, wishlist_id) if wishlist_id else None
    if wishlist is None or wishlist.profile_id != item.profile_id:
        return error("Wishlist not found for this profile.", 404)
    if WishlistItemWishlist.query.filter_by(item_id=item.id, wishlist_id=wishlist.id).first():
        return error("Gift is already on that wishlist.", 409)
    db.session.add(WishlistItemWishlist(item_id=item.id, wishlist_id=wishlist.id))
    if wishlist.occasion_id and not WishlistItemOccasion.query.filter_by(
        item_id=item.id,
        occasion_id=wishlist.occasion_id,
    ).first():
        db.session.add(WishlistItemOccasion(item_id=item.id, occasion_id=wishlist.occasion_id))
    db.session.commit()
    return jsonify({"status": "linked"}), 201


def expire_gift_holds():
    # A conditional update lets only one request release and notify for each hold.
    rows = GiftReservation.query.filter(GiftReservation.status == 'reserved',
        GiftReservation.created_at <= datetime.now(timezone.utc)-timedelta(hours=24)).all()
    for row in rows:
        changed = GiftReservation.query.filter_by(id=row.id,status='reserved').update(
            {GiftReservation.status:'cancelled'},synchronize_session=False)
        if not changed: continue
        home = Household.query.join(HouseholdProfileAccess).filter(
            HouseholdProfileAccess.profile_id==row.item.profile_id).first()
        if home:
            db.session.add(Notification(user_id=row.shopper_id,household_id=home.id,item_id=row.item_id,
                message='Your hold expired: '+row.item.name[:180]+'. The gift has been released.'))
    if rows:
        db.session.commit()
        db.session.expire_all()


def hold_expiry(row):
    return (row.created_at.replace(tzinfo=timezone.utc) + timedelta(hours=24)).isoformat()


def list_is_shared(row):
    if row.share_publicly is not None:
        return row.share_publicly
    profile = db.session.get(PersonProfile, row.profile_id)
    if profile.profile_type == "pet" and not profile.share_wishlist:
        return False
    return not db.session.query(WishlistItem.id).join(WishlistItemWishlist).filter(
        WishlistItemWishlist.wishlist_id == row.id, WishlistItem.family_only.is_(True)).first()


def list_family_access(row, user):
    profile = db.session.get(PersonProfile, row.profile_id)
    return profile.account_user_id == user.id or db.session.query(HouseholdMembership.id).join(HouseholdProfileAccess,
        HouseholdProfileAccess.household_id == HouseholdMembership.household_id).filter(
        HouseholdProfileAccess.profile_id == row.profile_id, HouseholdMembership.user_id == user.id,
        or_(HouseholdMembership.is_family_member.is_(True), HouseholdMembership.role.in_(('owner', 'admin', 'profile_manager')))).first() is not None


def item_audience_allowed(item, user):
    personal = PersonalWish.query.filter_by(item_id=item.id).first()
    if personal and personal.owner_id != user.id and not personal_viewer_allowed(personal, user):
        return False
    lists = Wishlist.query.join(WishlistItemWishlist, WishlistItemWishlist.wishlist_id == Wishlist.id).filter(WishlistItemWishlist.item_id == item.id).all()
    explicit = [row for row in lists if row.share_publicly is not None]
    if explicit:
        family = item.profile.account_user_id == user.id or db.session.query(HouseholdMembership.id).join(HouseholdProfileAccess,
            HouseholdProfileAccess.household_id == HouseholdMembership.household_id).filter(
            HouseholdProfileAccess.profile_id == item.profile_id, HouseholdMembership.user_id == user.id,
            or_(HouseholdMembership.is_family_member.is_(True), HouseholdMembership.role.in_(('owner', 'admin', 'profile_manager')))).first() is not None
        return family or any(row.share_publicly for row in explicit)
    if item.profile.profile_type == "pet" and not item.profile.share_wishlist and not pet_family_access(user, item.profile):
        return False
    if not item.family_only or item.profile.account_user_id == user.id:
        return True
    return db.session.query(HouseholdMembership.id).join(HouseholdProfileAccess,
        HouseholdProfileAccess.household_id == HouseholdMembership.household_id).filter(
        HouseholdProfileAccess.profile_id == item.profile_id, HouseholdMembership.user_id == user.id,
        HouseholdMembership.role.in_(('owner', 'admin', 'profile_manager'))).first() is not None


def shopper_can_see(item, user):
    if not item_audience_allowed(item, user):
        return False
    if item.profile.account_user_id == user.id or session.get('active_member_profile_id') == item.profile_id:
        return False
    personal = PersonalWish.query.filter_by(item_id=item.id).first()
    if personal:
        return personal_viewer_allowed(personal, user)
    return profile_access(user, item.profile_id) is not None


@api.post("/items/<int:item_id>/reservations")
@authenticated
def reserve_gift(item_id):
    user = request.current_user
    item = WishlistItem.query.filter_by(id=item_id).with_for_update().first()
    if item is None or not shopper_can_see(item, user):
        return error("Gift not found.", 404)
    payload = request.get_json(silent=True) or {}
    try:
        quantity = int(payload.get("quantity", 1))
    except (TypeError, ValueError):
        return error("Reservation quantity must be a positive integer.", 400)
    if quantity < 1:
        return error("Reservation quantity must be a positive integer.", 400)
    if payload.get("reuse_existing") is True:
        existing = GiftReservation.query.filter_by(item_id=item.id, shopper_id=user.id, status="reserved").first()
        if existing:
            return jsonify({"reservation": {"id": existing.id, "item_id": existing.item_id,
                "quantity": existing.quantity, "status": existing.status}})
    totals = db.session.query(
        func.coalesce(func.sum(GiftReservation.quantity), 0)
    ).filter(
        GiftReservation.item_id == item.id,
        GiftReservation.status.in_(("reserved", "purchased")),
    ).scalar()
    if totals + quantity > item.quantity:
        return error("Not enough units are available.", 409)
    row = GiftReservation(
        item_id=item.id,
        shopper_id=user.id,
        quantity=quantity,
        status="reserved",
        private_note=str(payload.get("private_note", ""))[:2000] or None,
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"reservation": {
        "id": row.id,
        "item_id": row.item_id,
        "quantity": row.quantity,
        "status": row.status,
        "private_note": row.private_note,
    }}), 201


@api.get("/my-shopping")
@authenticated
def my_shopping():
    rows = GiftReservation.query.filter(
        or_(GiftReservation.shopper_id == request.current_user.id,
            GiftReservation.id.in_(db.session.query(CoBuyInvitation.reservation_id).filter_by(email=request.current_user.email, accepted=True))),
        GiftReservation.status.in_(("reserved", "purchased")),
    ).order_by(GiftReservation.updated_at.desc()).all()
    return jsonify({"reservations": [{
        "id": row.id,
        "item": item_dict(row.item, request.current_user),
        "quantity": row.quantity,
        "status": row.status,
        "private_note": row.private_note if row.shopper_id == request.current_user.id else None,
        "is_owner": row.shopper_id == request.current_user.id,
        "expires_at": hold_expiry(row) if row.status == "reserved" else None,
        "delivery_method": row.delivery_method,
        "co_buyers": [{"email": invite.email, "accepted": invite.accepted, "declined": invite.declined, "share_percent": str(invite.share_percent)} for invite in CoBuyInvitation.query.filter_by(reservation_id=row.id).all()],
    } for row in rows if shopper_can_see(row.item, request.current_user)]})


@api.patch("/reservations/<int:reservation_id>")
@authenticated
def update_reservation(reservation_id):
    row = GiftReservation.query.filter_by(
        id=reservation_id,
    ).with_for_update().first()
    participant = CoBuyInvitation.query.filter_by(reservation_id=reservation_id, email=request.current_user.email, accepted=True).first()
    if row is None or not shopper_can_see(row.item, request.current_user) or (row.shopper_id != request.current_user.id and not participant):
        return error("Reservation not found.", 404)
    payload = request.get_json(silent=True) or {}
    status = payload.get("status", row.status)
    if row.status == "cancelled" and status != "cancelled":
        return error("This hold was released or expired. Place a new hold if the gift is still available.", 409)
    if row.shopper_id != request.current_user.id and (status != "purchased" or "private_note" in payload):
        return error("Co-buyers can only mark the gift purchased.", 403)
    if status not in {"reserved", "purchased", "cancelled"}:
        return error("Unsupported reservation status.", 400)
    if "private_note" in payload:
        row.private_note = str(payload["private_note"])[:2000]
    if status != row.status and status in {"reserved", "purchased"}:
        item = WishlistItem.query.filter_by(id=row.item_id).with_for_update().first()
        total = db.session.query(func.coalesce(func.sum(GiftReservation.quantity), 0)).filter(
            GiftReservation.item_id == row.item_id,
            GiftReservation.status.in_(("reserved", "purchased")),
            GiftReservation.id != row.id,
        ).scalar()
        if total + row.quantity > item.quantity:
            return error("Not enough units are available.", 409)
    if 'delivery_method' in payload:
        if payload['delivery_method'] not in ('undecided', 'shipping', 'in_person'):
            return error('Choose shipping, giving in person or undecided.', 400)
        row.delivery_method = payload['delivery_method']
    if "purchase_secret" in payload:
        if type(payload["purchase_secret"]) is not bool:
            return error("Choose whether to keep the purchase secret.", 400)
        row.purchase_secret = payload["purchase_secret"]
    previous_status = row.status
    row.status = status
    if status == "purchased" and previous_status != "purchased":
        heads_query = db.session.query(
            HouseholdMembership.user_id,
            HouseholdMembership.household_id,
        ).join(
            HouseholdProfileAccess,
            HouseholdProfileAccess.household_id == HouseholdMembership.household_id,
        ).filter(
            HouseholdProfileAccess.profile_id == row.item.profile_id,
            HouseholdMembership.role.in_(("owner", "admin")),
            HouseholdMembership.user_id != request.current_user.id,
        )
        if row.item.profile.account_user_id is not None:
            heads_query = heads_query.filter(
                HouseholdMembership.user_id != row.item.profile.account_user_id
            )
        heads = heads_query.all()
        for user_id, household_id in heads:
            db.session.add(Notification(
                user_id=user_id,
                household_id=household_id,
                item_id=row.item_id,
                message=f"{row.item.name} was purchased.",
            ))
    db.session.commit()
    return jsonify({"reservation": {
        "id": row.id, "item_id": row.item_id, "quantity": row.quantity,
        "status": row.status, "private_note": row.private_note,
    }})


NOTIFICATION_TYPES = ('follow_requests', 'co_buy', 'co_buy_emails', 'games', 'game_emails', 'purchases', 'availability', 'holds', 'suggestions')


@api.route('/notification-preferences', methods=['GET', 'PATCH'])
@authenticated
def notification_preferences():
    user = request.current_user
    values = {key: (user.notification_preferences or {}).get(key, True) for key in NOTIFICATION_TYPES}
    if request.method == 'PATCH':
        payload = request.get_json(silent=True) or {}
        if set(payload) - set(NOTIFICATION_TYPES) or any(type(v) is not bool for v in payload.values()):
            return error('Choose a notification switch.', 400)
        values.update(payload)
        user.notification_preferences = {**(user.notification_preferences or {}), **values}
        db.session.commit()
    return jsonify(preferences=values)


@api.get("/notifications")
@authenticated
def list_notifications():
    from ..gift_games import pending_game_notifications
    rows = Notification.query.filter_by(user_id=request.current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(100).all()
    from ..adult_family import suggestion_notifications
    from ..wishlist_price_requests import price_request_notifications
    notifications = suggestion_notifications(request.current_user) + availability_notifications(request.current_user) + pending_follow_notifications(request.current_user) + pending_co_buy_notifications(request.current_user) + pending_game_notifications(request.current_user) + [{
        "id": row.id,
        "hold_expired": row.message.startswith("Your hold expired:"),
        "url": "/gifting" if row.message.startswith("Your hold expired:") else None,
        "household_id": row.household_id,
        "household_name": row.household.name,
        "item_name": row.item.name,
        "profile_id": row.item.profile_id,
        "wishlist_id": row.item.wishlists[0].wishlist_id if row.item.wishlists else None,
        "message": row.message,
        "read": row.read_at is not None,
        "created_at": row.created_at.isoformat(),
    } for row in rows]
    notifications = price_request_notifications(request.current_user) + notifications
    profile_reminders = []
    editable_profiles = PersonProfile.query.join(HouseholdProfileAccess).join(HouseholdMembership,
        HouseholdMembership.household_id == HouseholdProfileAccess.household_id).filter(HouseholdMembership.user_id == request.current_user.id).distinct().all()
    editable_profiles = list({profile.id: profile for profile in editable_profiles + PersonProfile.query.filter_by(account_user_id=request.current_user.id).all()}.values())
    for profile in editable_profiles:
        if profile_access(request.current_user, profile.id, write=True) is None:
            continue
        if profile.is_adult and profile.profile_type == 'person' and profile.account_user_id != request.current_user.id:
            continue
        progress = profile_completion(profile)
        if progress["percent"] < 100:
            profile_reminders.append({"id": "profile-completion-"+str(profile.id), "profile_completion": True, "profile_name": profile.display_name,
                "profile_id": profile.id, "is_you": profile.account_user_id == request.current_user.id, "message": "Complete your profile" if profile.account_user_id == request.current_user.id else f"Complete {profile.display_name}'s family profile",
                "url": "/profiles/"+str(profile.id)+"?edit=1", "read": False,
                "created_at": profile.updated_at.isoformat(), "household_name": "Gift profile", "completion": progress})
    preferences = request.current_user.notification_preferences or {}
    read_ids = set(preferences.get('read_notification_ids', []))
    for row in notifications + profile_reminders:
        if str(row['id']) in read_ids:
            row['read'] = True
    profile_reminders.sort(key=lambda row: (not row["is_you"], row["profile_name"].casefold()))
    dismissed_ids = set(preferences.get("dismissed_notification_ids", []))
    dismissed_profiles = preferences.get("dismissed_profile_reminders", [])
    profile_reminders = [row for row in profile_reminders if row["profile_id"] not in dismissed_profiles and str(row["id"]) not in dismissed_ids]
    def enabled(row):
        if str(row["id"]) in dismissed_ids:
            return False
        if row.get("profile_completion") or row.get("price_request"):
            return True
        kind = "suggestions" if row.get("suggestion_id") else "holds" if row.get("hold_expired") else "availability" if row.get("availability_alert_id") else "follow_requests" if row.get("invitation_id") else "co_buy" if row.get("co_buy_invitation_id") else "games" if row.get("game_id") else "purchases"
        return preferences.get(kind, True)
    return jsonify(notifications=[row for row in notifications if enabled(row)], profile_reminders=profile_reminders)


@api.post('/notifications/clear')
@authenticated
def clear_notifications():
    visible = list_notifications.__wrapped__().get_json()
    preferences = dict(request.current_user.notification_preferences or {})
    ids = set(preferences.get('dismissed_notification_ids', []))
    ids.update(str(row['id']) for row in visible['notifications'] + visible['profile_reminders'])
    preferences['dismissed_notification_ids'] = sorted(ids)
    preferences['wishlist_budget_suggestions'] = False
    request.current_user.notification_preferences = preferences
    db.session.commit()
    return jsonify(status='cleared')


@api.post('/profile-reminders/<int:profile_id>/dismiss')
@authenticated
def dismiss_profile_reminder(profile_id):
    if profile_access(request.current_user, profile_id, write=True) is None:
        return error('Profile not found.', 404)
    preferences = dict(request.current_user.notification_preferences or {})
    dismissed = set(preferences.get('dismissed_profile_reminders', []))
    dismissed.add(profile_id)
    preferences['dismissed_profile_reminders'] = sorted(dismissed)
    request.current_user.notification_preferences = preferences
    db.session.commit()
    return jsonify(status='dismissed')


@api.post("/notifications/<int:notification_id>/read")
@authenticated
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=request.current_user.id,
    ).first()
    if notification is None:
        return error("Notification not found.", 404)
    notification.read_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"status": "read"})


@api.get("/shopping")
@authenticated
def shopping_hub():
    user = request.current_user
    membership_ids = db.session.query(HouseholdMembership.id).filter(
        HouseholdMembership.user_id == user.id
    )
    privileged_profile_ids = (
        db.session.query(HouseholdProfileAccess.profile_id)
        .join(HouseholdMembership, HouseholdMembership.household_id == HouseholdProfileAccess.household_id)
        .filter(
            HouseholdMembership.user_id == user.id,
            or_(HouseholdMembership.role.in_(("owner", "admin")), HouseholdMembership.share_all_profiles.is_(True)),
        )
    )
    specifically_shared_profile_ids = db.session.query(
        HouseholdMemberProfileAccess.profile_id
    ).filter(HouseholdMemberProfileAccess.membership_id.in_(membership_ids))
    visible_profile_ids = privileged_profile_ids.union(specifically_shared_profile_ids)
    personal_ids = [row.item_id for row in visible_personal_candidates(user).all() if personal_viewer_allowed(row, user)]
    query = WishlistItem.query.filter(or_(WishlistItem.profile_id.in_(visible_profile_ids), WishlistItem.id.in_(personal_ids)))
    if user.id:
        query = query.filter(
            ~WishlistItem.profile_id.in_(
                db.session.query(PersonProfile.id).filter(PersonProfile.account_user_id == user.id)
            )
        )
    if request.args.get("scope") == "following":
        from ..adult_family import followed_ids
        followed = followed_ids(user)
        external_profiles = db.session.query(HouseholdProfileAccess.profile_id).join(HouseholdMembership,
            HouseholdMembership.household_id == HouseholdProfileAccess.household_id).filter(
            HouseholdMembership.user_id == user.id, HouseholdMembership.is_family_member.is_(False),
            ~HouseholdMembership.role.in_(("owner", "admin")))
        followed_wishes = db.session.query(PersonalWish.item_id).filter(PersonalWish.owner_id.in_(followed))
        query = query.filter(or_(WishlistItem.profile_id.in_(external_profiles), WishlistItem.id.in_(followed_wishes)))
    search = request.args.get("q", "").strip()
    for word in search.split():
        pattern = "%" + word.replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.filter(or_(
            WishlistItem.name.ilike(pattern),
            WishlistItem.store_name.ilike(pattern),
            WishlistItem.category.ilike(pattern),
            WishlistItem.profile_id.in_(db.session.query(HouseholdProfileAccess.profile_id).join(Household,
                Household.id == HouseholdProfileAccess.household_id).join(HouseholdMembership,
                HouseholdMembership.household_id == Household.id).filter(HouseholdMembership.user_id == user.id, Household.name.ilike(pattern))),
            WishlistItem.id.in_(db.session.query(WishlistItemOccasion.item_id).join(Occasion,
                Occasion.id == WishlistItemOccasion.occasion_id).filter(Occasion.name.ilike(pattern),
                Occasion.household_id.in_(db.session.query(HouseholdMembership.household_id).filter(HouseholdMembership.user_id == user.id)))),
            WishlistItem.profile_id.in_(
                db.session.query(PersonProfile.id).filter(PersonProfile.display_name.ilike(pattern))
            ),
        ))
    if request.args.get("priority"):
        try:
            query = query.filter(WishlistItem.priority == int(request.args["priority"]))
        except ValueError:
            return error("Priority filter must be an integer from 1 to 4.", 400)
    if request.args.get("category"):
        query = query.filter(WishlistItem.category.ilike(f"%{request.args['category'].strip()}%"))
    bounds = {}
    for key in ("min_price", "max_price"):
        raw = request.args.get(key)
        if raw not in (None, ""):
            try:
                value = Decimal(raw)
            except InvalidOperation:
                return error("Price filters must be valid amounts.", 400)
            if not value.is_finite() or value < 0:
                return error("Price filters must be non-negative amounts.", 400)
            bounds[key] = value
    if bounds.get("min_price", 0) > bounds.get("max_price", Decimal("Infinity")):
        return error("Minimum price must not exceed maximum price.", 400)
    if bounds:
        currency = request.args.get("currency", "USD").upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            return error("Choose a three-letter currency.", 400)
        query = query.filter(WishlistItem.estimated_price.isnot(None), func.upper(WishlistItem.currency) == currency)
        if "min_price" in bounds:
            query = query.filter(WishlistItem.estimated_price >= bounds["min_price"])
        if "max_price" in bounds:
            query = query.filter(WishlistItem.estimated_price <= bounds["max_price"])
    sort = request.args.get("sort", "recent")
    if sort == "price":
        query = query.order_by(
            WishlistItem.estimated_price.is_(None),
            WishlistItem.estimated_price.asc(),
        )
    elif sort == "priority":
        query = query.order_by(WishlistItem.priority.desc(), WishlistItem.created_at.desc())
    else:
        query = query.order_by(WishlistItem.created_at.desc())
    items = query.limit(200).all()
    return jsonify({"items": [{
        **item_dict(row, user),
        "recipient": row.profile.display_name,
    } for row in items if item_audience_allowed(row, request.current_user)]})


@api.put("/budgets")
@authenticated
def put_budget():
    payload = request.get_json(silent=True) or {}
    try:
        amount = Decimal(str(payload.get("amount", "")))
    except (InvalidOperation, ValueError):
        return error("Budget amount must be a valid non-negative number.", 400)
    if not amount.is_finite() or amount < 0 or amount > Decimal("99999999.99"):
        return error("Budget amount must be a valid non-negative number.", 400)
    household_id = payload.get("household_id")
    profile_id = payload.get("profile_id")
    if household_id and not membership_for(request.current_user, household_id):
        return error("Household not found.", 404)
    if profile_id and not profile_access(request.current_user, profile_id):
        return error("Profile not found.", 404)
    query = ShoppingBudget.query.filter_by(
        user_id=request.current_user.id,
        household_id=household_id,
        profile_id=profile_id,
    )
    budget = query.first()
    if budget is None:
        budget = ShoppingBudget(
            user_id=request.current_user.id,
            household_id=household_id,
            profile_id=profile_id,
            amount=amount,
            currency=str(payload.get("currency", "USD")).upper()[:3],
        )
        db.session.add(budget)
    else:
        budget.amount = amount
    db.session.commit()
    return jsonify({"budget": {
        "amount": str(budget.amount),
        "currency": budget.currency,
        "household_id": budget.household_id,
        "profile_id": budget.profile_id,
    }})


@api.get("/budgets")
@authenticated
def list_budgets():
    rows = ShoppingBudget.query.filter_by(user_id=request.current_user.id).all()
    return jsonify({"budgets": [{
        "amount": str(row.amount),
        "currency": row.currency,
        "household_id": row.household_id,
        "profile_id": row.profile_id,
    } for row in rows]})


@api.get("/support/staff-invitations")
@superuser_required
def list_support_staff_invitations():
    now = datetime.now(timezone.utc)
    rows = SupportInvitation.query.filter_by(
        invited_by_id=request.current_user.id,
        accepted_at=None,
    ).order_by(SupportInvitation.created_at.desc()).limit(100).all()
    pending = []
    for row in rows:
        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > now:
            pending.append({
                "id": row.id,
                "email": row.email,
                "expires_at": row.expires_at.isoformat(),
                "created_at": row.created_at.isoformat(),
            })
    return jsonify({"invitations": pending})


@api.post("/support/staff-invitations")
@superuser_required
@limiter.limit("20 per hour")
def create_support_staff_invitation():
    payload = request.get_json(silent=True) or {}
    email = normalized_email(payload.get("email"))
    if not email:
        return error("Enter a valid email address.", 400)
    if User.query.filter(func.lower(User.email) == email.lower()).first():
        return error("An account with this email already exists.", 409)
    now = datetime.now(timezone.utc)
    pending_rows = SupportInvitation.query.filter_by(email=email, accepted_at=None).all()
    for existing in pending_rows:
        expires_at = existing.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > now:
            return error("A staff invitation for this email is already pending.", 409)

    token = secrets.token_urlsafe(32)
    invitation = SupportInvitation(
        email=email,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        invited_by_id=request.current_user.id,
        expires_at=now + timedelta(days=3),
    )
    db.session.add(invitation)
    db.session.flush()
    record_audit(
        request.current_user.id,
        "support.staff_invited",
        "support_invitation",
        invitation.id,
        details={"email": email},
    )
    db.session.commit()
    return jsonify({
        "invitation": {
            "id": invitation.id,
            "email": email,
            "token": token,
            "expires_at": invitation.expires_at.isoformat(),
        }
    }), 201


@api.post("/support/family-setup-invitations")
@support_required
@limiter.limit("20 per hour")
def create_support_family_setup_invitation():
    email = normalized_email(request.form.get("email"))
    household_name = str(request.form.get("household_name", "")).strip()
    profile_name = str(request.form.get("profile_name", "")).strip()
    birthday = request.form.get("birthday", "").strip()
    if not email or len(email) > 255:
        return error("Enter a valid email address.", 400)
    existing_user = User.query.filter(func.lower(User.email) == email.lower()).first()
    if existing_user and (existing_user.is_child or existing_user.is_support):
        return error("Family setup invitations require a non-support adult email address.", 400)
    if not household_name or len(household_name) > 160:
        return error("Family name is required and must be at most 160 characters.", 400)
    if not profile_name or len(profile_name) > 120:
        return error("The primary adult profile name is required and must be at most 120 characters.", 400)
    if birthday:
        try:
            parse_birthday(birthday)
        except (TypeError, ValueError):
            return error("Birthday must contain a valid month and day.", 400)

    now = datetime.now(timezone.utc)
    pending = HouseholdInvitation.query.filter_by(
        email=email,
        transfer_owner_on_accept=True,
        accepted_at=None,
        declined_at=None,
    ).all()
    for existing in pending:
        expires_at = existing.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > now:
            return error("A family setup invitation for this email is already pending.", 409)

    household = Household(name=household_name, owner_id=request.current_user.id)
    db.session.add(household)
    db.session.flush()
    try:
        profile = create_household_profile(
            household.id,
            None,
            {
                "display_name": profile_name,
                "profile_type": "person",
                "relationship": "parent",
                "is_adult": True,
                "birthday": birthday,
            },
        )
    except ValueError as exc:
        db.session.rollback()
        return error(str(exc), 400)
    profile.is_adult = True
    profile.is_guardian = True
    profile.member_email = email

    image = request.files.get("image")
    if image and image.filename:
        image_path, failure = save_profile_image(image, profile.id)
        if failure:
            db.session.rollback()
            return error(failure, 400)
        profile.photo_path = image_path

    token = secrets.token_urlsafe(32)
    invitation = HouseholdInvitation(
        household_id=household.id,
        email=email,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        role="owner",
        profile_ids=[profile.id],
        linked_profile_id=profile.id,
        transfer_owner_on_accept=True,
        setup_created_by_id=request.current_user.id,
        expires_at=now + timedelta(days=7),
    )
    db.session.add(invitation)
    db.session.flush()
    record_audit(
        request.current_user.id,
        "support.family_setup_created",
        "household",
        household.id,
        household.id,
        {"invited_email": email, "profile_id": profile.id},
    )
    db.session.commit()

    email_message = prepare_family_setup_invitation(email, token, household_name)
    return jsonify({
        "household": household.public_dict(),
        "profile": profile.public_dict(),
        "email_message": email_message,
        "invitation": {
            "email": email,
            "expires_at": invitation.expires_at.isoformat(),
            "token": token,
        },
    }), 201


@api.post("/support/access-requests")
@support_required
@limiter.limit("20 per hour")
def create_support_access_request():
    payload = request.get_json(silent=True) or {}
    household_id = payload.get("household_id")
    reason = str(payload.get("reason", "")).strip()
    household = db.session.get(Household, household_id) if isinstance(household_id, int) else None
    if household is None:
        return error("Household not found.", 404)
    if not reason or len(reason) > 1000:
        return error("Explain the support task in 1 to 1000 characters.", 400)
    existing = SupportAccessRequest.query.filter_by(
        household_id=household_id,
        support_user_id=request.current_user.id,
        status="pending",
    ).first()
    if existing:
        return error("A support access request is already awaiting approval.", 409)
    support_request = SupportAccessRequest(
        household_id=household_id,
        support_user_id=request.current_user.id,
        reason=reason,
    )
    db.session.add(support_request)
    db.session.flush()
    record_audit(
        request.current_user.id,
        "support.access_requested",
        "support_access_request",
        support_request.id,
        household_id,
    )
    db.session.commit()
    return jsonify({
        "request": {
            "id": support_request.id,
            "household_id": household_id,
            "status": support_request.status,
            "reason": support_request.reason,
            "created_at": support_request.created_at.isoformat(),
        }
    }), 201


@api.get("/support/access-requests")
@authenticated
def list_support_access_requests():
    household_id = request.args.get("household_id", type=int)
    if request.current_user.is_support and session.get("auth_mode") == "support":
        query = SupportAccessRequest.query
        if household_id:
            query = query.filter_by(household_id=household_id)
    else:
        if not household_id:
            return error("Household ID is required.", 400)
        membership = membership_for(request.current_user, household_id)
        if not membership or membership.role not in {"owner", "admin"}:
            return error("Household owner or administrator permission required.", 403)
        query = SupportAccessRequest.query.filter_by(household_id=household_id)
    rows = query.order_by(SupportAccessRequest.created_at.desc()).limit(100).all()
    return jsonify({"requests": [{
        "id": row.id,
        "household_id": row.household_id,
        "support_name": row.support_user.name,
        "support_email": row.support_user.email,
        "reason": row.reason,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "expires_at": row.grant.expires_at.isoformat() if row.grant else None,
        "grant_id": row.grant.id if row.grant else None,
    } for row in rows]})


@api.patch("/support/access-requests/<int:request_id>")
@authenticated
def decide_support_access_request(request_id):
    support_request = db.session.get(SupportAccessRequest, request_id)
    if support_request is None:
        return error("Support access request not found.", 404)
    membership = membership_for(request.current_user, support_request.household_id)
    if not membership or membership.role not in {"owner", "admin"}:
        return error("Only a household owner or administrator can approve support access.", 403)
    if support_request.status != "pending":
        return error("This support access request has already been decided.", 409)
    decision = (request.get_json(silent=True) or {}).get("decision")
    if decision not in {"approve", "deny"}:
        return error("Decision must be approve or deny.", 400)
    support_request.status = "approved" if decision == "approve" else "denied"
    support_request.decided_at = datetime.now(timezone.utc)
    support_request.decided_by_id = request.current_user.id
    if decision == "approve":
        grant = SupportAccessGrant(
            request_id=support_request.id,
            household_id=support_request.household_id,
            support_user_id=support_request.support_user_id,
            approved_by_id=request.current_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.session.add(grant)
    action_name = {
        "approve": "support.access_approved",
        "deny": "support.access_denied",
    }[decision]
    record_audit(
        request.current_user.id,
        action_name,
        "support_access_request",
        support_request.id,
        support_request.household_id,
    )
    db.session.commit()
    return jsonify({"status": support_request.status})


@api.delete("/support/grants/<int:grant_id>")
@authenticated
def revoke_support_access(grant_id):
    grant = db.session.get(SupportAccessGrant, grant_id)
    if grant is None:
        return error("Support access grant not found.", 404)
    membership = membership_for(request.current_user, grant.household_id)
    if not membership or membership.role not in {"owner", "admin"}:
        return error("Only a household owner or administrator can revoke support access.", 403)
    if grant.revoked_at is None:
        grant.revoked_at = datetime.now(timezone.utc)
        record_audit(
            request.current_user.id,
            "support.access_revoked",
            "support_access_grant",
            grant.id,
            grant.household_id,
        )
        db.session.commit()
    return jsonify({"status": "revoked"})


@api.get("/support/requests")
@support_required
def support_request_queue():
    rows = SupportAccessRequest.query.filter_by(
        support_user_id=request.current_user.id
    ).order_by(SupportAccessRequest.created_at.desc()).limit(100).all()
    return jsonify({"requests": [{
        "id": row.id,
        "household_id": row.household_id,
        "household_name": row.household.name,
        "reason": row.reason,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "expires_at": row.grant.expires_at.isoformat() if row.grant else None,
    } for row in rows]})


@api.get("/support/grants")
@support_required
def support_active_grants():
    rows = SupportAccessGrant.query.filter(
        SupportAccessGrant.support_user_id == request.current_user.id,
        SupportAccessGrant.revoked_at.is_(None),
        SupportAccessGrant.expires_at > datetime.now(timezone.utc),
    ).order_by(SupportAccessGrant.expires_at).all()
    return jsonify({"grants": [{
        "id": row.id,
        "household_id": row.household_id,
        "household_name": row.household.name,
        "expires_at": row.expires_at.isoformat(),
        "reason": row.request.reason,
    } for row in rows]})


@api.get("/support/grants/<int:grant_id>/snapshot")
@support_required
def support_household_snapshot(grant_id):
    grant = SupportAccessGrant.query.filter_by(
        id=grant_id,
        support_user_id=request.current_user.id,
        revoked_at=None,
    ).filter(SupportAccessGrant.expires_at > datetime.now(timezone.utc)).first()
    if grant is None:
        return error("Approved support access is missing, revoked, or expired.", 403)
    profiles = (
        PersonProfile.query.join(HouseholdProfileAccess)
        .filter(HouseholdProfileAccess.household_id == grant.household_id)
        .order_by(PersonProfile.display_name)
        .all()
    )
    snapshot = []
    for profile in profiles:
        items = WishlistItem.query.filter_by(profile_id=profile.id).order_by(
            WishlistItem.created_at.desc()
        ).all()
        snapshot.append({
            "profile": profile.public_dict(),
            "items": [item_dict(row, request.current_user) for row in items],
        })
    record_audit(
        request.current_user.id,
        "support.household_snapshot_viewed",
        "household",
        grant.household_id,
        grant.household_id,
        {"grant_id": grant.id, "profile_count": len(profiles)},
    )
    db.session.commit()
    return jsonify({
        "grant_id": grant.id,
        "household": {
            "id": grant.household.id,
            "name": grant.household.name,
        },
        "reason": grant.request.reason,
        "expires_at": grant.expires_at.isoformat(),
        "profiles": snapshot,
    })


@api.patch("/support/grants/<int:grant_id>/profiles/<int:profile_id>")
@support_required
def support_edit_profile(grant_id, profile_id):
    grant = SupportAccessGrant.query.filter_by(
        id=grant_id,
        support_user_id=request.current_user.id,
        revoked_at=None,
    ).filter(SupportAccessGrant.expires_at > datetime.now(timezone.utc)).first()
    profile = PersonProfile.query.join(HouseholdProfileAccess).filter(
        PersonProfile.id == profile_id,
        HouseholdProfileAccess.household_id == grant.household_id if grant else False,
    ).first() if grant else None
    if grant is None or profile is None:
        return error("Approved support access or profile not found.", 403)
    payload = request.get_json(silent=True) or {}
    fields = {
        "display_name", "birthday", "birthday_shared", "favorite_colors", "favorite_brands",
        "favorite_characters", "hobbies", "interests", "clothing_sizes",
        "shoe_sizes", "gift_preferences", "parent_notes", "items_to_avoid",
    }
    changed_fields = fields.intersection(payload)
    if not changed_fields:
        return error("No supported profile fields were provided.", 400)
    if "display_name" in changed_fields:
        if not isinstance(payload["display_name"], str) or not payload["display_name"].strip() or len(payload["display_name"]) > 120:
            return error("Profile name is required and must be at most 120 characters.", 400)
    if "birthday_shared" in changed_fields and not isinstance(payload["birthday_shared"], bool):
        return error("birthday_shared must be a boolean.", 400)
    list_fields = {"favorite_colors", "favorite_brands", "favorite_characters", "hobbies", "interests"}
    dict_fields = {"clothing_sizes", "shoe_sizes"}
    text_fields = {"gift_preferences", "parent_notes", "items_to_avoid"}
    for key in changed_fields.intersection(list_fields):
        if not isinstance(payload[key], list) or any(
            not isinstance(value, str) or len(value) > 120 for value in payload[key]
        ):
            return error(f"{key} must be a list of short text values.", 400)
    for key in changed_fields.intersection(dict_fields):
        if not isinstance(payload[key], dict):
            return error(f"{key} must be an object.", 400)
    for key in changed_fields.intersection(text_fields):
        if payload[key] is not None and (
            not isinstance(payload[key], str) or len(payload[key]) > 10000
        ):
            return error(f"{key} must be text up to 10000 characters.", 400)
    for key in changed_fields:
        if key != "birthday_shared":
            setattr(profile, key, payload[key])
    profile.birthday_shared = payload.get("birthday_shared", profile.birthday_shared)
    if "birthday" in payload:
        try:
            profile.birthday = parse_birthday(payload["birthday"]) if payload["birthday"] else None
            changed_fields.add("birthday")
        except (TypeError, ValueError):
            return error("Birthday must contain a valid month and day.", 400)
    record_audit(
        request.current_user.id,
        "support.profile_edited",
        "person_profile",
        profile.id,
        grant.household_id,
        {"grant_id": grant.id, "changed_fields": sorted(changed_fields)},
    )
    db.session.commit()
    return jsonify({"profile": profile.public_dict()})


def ticket_dict(ticket, include_messages=True):
    data = {
        "id": ticket.id,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }
    if include_messages:
        data["messages"] = [{
            "id": row.id,
            "author_name": row.author.name,
            "is_support": row.author.is_support,
            "message": row.message,
            "created_at": row.created_at.isoformat(),
        } for row in ticket.messages]
    return data


HELP_CHAT_RETENTION_DAYS = 30


def recent_help_chat(user_id, since):
    return HelpChatMessage.query.filter(
        HelpChatMessage.user_id == user_id, HelpChatMessage.created_at >= since,
    ).order_by(HelpChatMessage.created_at, HelpChatMessage.id).all()


@api.post("/help/chat")
@authenticated
@limiter.limit("120 per hour")
def log_help_chat():
    if request.current_user.is_support:
        return error("Support agents do not use the help assistant.", 403)
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    answer = str(payload.get("answer", "")).strip()
    if not question or len(question) > 1000 or len(answer) > 2000:
        return error("A question of at most 1000 characters is required.", 400)
    now = datetime.now(timezone.utc)
    HelpChatMessage.query.filter(
        HelpChatMessage.created_at < now - timedelta(days=HELP_CHAT_RETENTION_DAYS),
    ).delete(synchronize_session=False)
    db.session.add(HelpChatMessage(user_id=request.current_user.id, sender="user", message=question, created_at=now))
    if answer:
        db.session.add(HelpChatMessage(user_id=request.current_user.id, sender="bot", message=answer, created_at=now + timedelta(microseconds=1)))
    db.session.commit()
    return jsonify({"ok": True}), 201


@api.post("/help/chat/escalate")
@authenticated
@limiter.limit("10 per hour")
def escalate_help_chat():
    if request.current_user.is_support:
        return error("Support agents cannot open customer tickets.", 403)
    note = str((request.get_json(silent=True) or {}).get("note", "")).strip()
    if len(note) > 2000:
        return error("Note must be at most 2000 characters.", 400)
    rows = recent_help_chat(request.current_user.id, datetime.now(timezone.utc) - timedelta(hours=24))[-60:]
    if not rows:
        return error("Ask the assistant a question first.", 400)
    transcript = "\n".join(f"{'Customer' if row.sender == 'user' else 'Assistant'}: {row.message}" for row in rows)
    user = request.current_user
    description = (
        f"Escalated from the help assistant.\nContact: {user.name} <{user.email}>\n"
        + (f"\nCustomer note: {note}\n" if note else "")
        + f"\n--- Chat transcript ---\n{transcript}"
    )[:10000]
    ticket = SupportTicket(
        user_id=user.id,
        subject=f"Help assistant chat: {rows[0].message[:120]}",
        description=description,
        category="help",
    )
    db.session.add(ticket)
    db.session.flush()
    db.session.add(SupportTicketMessage(ticket_id=ticket.id, author_id=user.id, message=description))
    record_audit(user.id, "support.ticket_created", "support_ticket", ticket.id, details={"source": "help_chat"})
    db.session.commit()
    return jsonify({"ticket": ticket_dict(ticket)}), 201


@api.get("/support/help-chats")
@superuser_required
def list_help_chats():
    since = datetime.now(timezone.utc) - timedelta(days=HELP_CHAT_RETENTION_DAYS)
    rows = HelpChatMessage.query.filter(HelpChatMessage.created_at >= since).order_by(
        HelpChatMessage.created_at, HelpChatMessage.id).limit(5000).all()
    chats = {}
    for row in rows:
        chat = chats.setdefault(row.user_id, {
            "user_id": row.user_id, "user_name": row.user.name, "user_email": row.user.email, "messages": [],
        })
        chat["messages"].append({"sender": row.sender, "message": row.message, "created_at": row.created_at.isoformat()})
    ordered = sorted(chats.values(), key=lambda chat: chat["messages"][-1]["created_at"], reverse=True)
    return jsonify({"days": HELP_CHAT_RETENTION_DAYS, "chats": ordered})


def staff_session():
    return request.current_user.is_support and session.get("auth_mode") == "support"


def staff_can_access_ticket(ticket):
    return request.current_user.is_superuser or ticket.assigned_to_id == request.current_user.id


def staff_ticket_dict(ticket):
    return {
        **ticket_dict(ticket),
        "user_name": ticket.user.name,
        "user_email": ticket.user.email,
        "assigned_to": {"id": ticket.assigned_to.id, "name": ticket.assigned_to.name} if ticket.assigned_to else None,
    }


@api.get("/support/tickets")
@authenticated
def list_support_tickets():
    query = SupportTicket.query
    if not staff_session():
        query = query.filter_by(user_id=request.current_user.id)
    elif not request.current_user.is_superuser:
        query = query.filter_by(assigned_to_id=request.current_user.id)
    rows = query.order_by(SupportTicket.updated_at.desc()).limit(100).all()
    if staff_session():
        return jsonify({"tickets": [staff_ticket_dict(row) for row in rows]})
    return jsonify({"tickets": [ticket_dict(row) for row in rows]})


@api.get("/support/staff")
@superuser_required
def list_support_staff():
    rows = User.query.filter(User.is_support.is_(True)).order_by(User.name).all()
    return jsonify({"staff": [{"id": row.id, "name": row.name, "email": row.email, "is_superuser": row.is_superuser} for row in rows]})


@api.post("/support/tickets")
@authenticated
@limiter.limit("10 per hour")
def create_support_ticket():
    if request.current_user.is_support:
        return error("Support agents cannot open customer feedback tickets.", 403)
    payload = request.get_json(silent=True) or {}
    subject = str(payload.get("subject", "")).strip()
    description = str(payload.get("description", "")).strip()
    category = payload.get("category", "bug")
    if not subject or len(subject) > 180 or not description or len(description) > 10000:
        return error("Subject and a description of at most 10000 characters are required.", 400)
    if category not in {"bug", "feedback", "help"}:
        return error("Category must be bug, feedback, or help.", 400)
    ticket = SupportTicket(
        user_id=request.current_user.id,
        subject=subject,
        description=description,
        category=category,
    )
    db.session.add(ticket)
    db.session.flush()
    db.session.add(SupportTicketMessage(
        ticket_id=ticket.id,
        author_id=request.current_user.id,
        message=description,
    ))
    record_audit(request.current_user.id, "support.ticket_created", "support_ticket", ticket.id)
    db.session.commit()
    return jsonify({"ticket": ticket_dict(ticket)}), 201


@api.post("/support/tickets/<int:ticket_id>/messages")
@authenticated
@limiter.limit("30 per hour")
def reply_support_ticket(ticket_id):
    ticket = db.session.get(SupportTicket, ticket_id)
    if ticket is None:
        return error("Support ticket not found.", 404)
    is_staff = request.current_user.is_support and session.get("auth_mode") == "support"
    if not is_staff and ticket.user_id != request.current_user.id:
        return error("Support ticket not found.", 404)
    if is_staff and not staff_can_access_ticket(ticket):
        return error("Support ticket not found.", 404)
    message = str((request.get_json(silent=True) or {}).get("message", "")).strip()
    if not message or len(message) > 10000:
        return error("Message is required and must be at most 10000 characters.", 400)
    db.session.add(SupportTicketMessage(
        ticket_id=ticket.id,
        author_id=request.current_user.id,
        message=message,
    ))
    if is_staff and ticket.status == "open":
        ticket.status = "in_progress"
    ticket.updated_at = datetime.now(timezone.utc)
    record_audit(
        request.current_user.id,
        "support.ticket_replied",
        "support_ticket",
        ticket.id,
        details={"is_support": is_staff},
    )
    db.session.commit()
    return jsonify({"ticket": ticket_dict(ticket)})


@api.patch("/support/tickets/<int:ticket_id>")
@support_required
def update_support_ticket(ticket_id):
    ticket = db.session.get(SupportTicket, ticket_id)
    if ticket is None or not staff_can_access_ticket(ticket):
        return error("Support ticket not found.", 404)
    payload = request.get_json(silent=True) or {}
    old_status = ticket.status
    if "assigned_to_id" in payload:
        if not request.current_user.is_superuser:
            return error("Only the master support account can assign tickets.", 403)
        assignee_id = payload["assigned_to_id"]
        if assignee_id is not None:
            assignee = db.session.get(User, assignee_id) if type(assignee_id) is int else None
            if assignee is None or not assignee.is_support:
                return error("Choose a support staff member.", 400)
        ticket.assigned_to_id = assignee_id
        record_audit(request.current_user.id, "support.ticket_assigned", "support_ticket", ticket.id,
                     details={"assigned_to_id": assignee_id})
    if "status" in payload or "assigned_to_id" not in payload:
        status = payload.get("status")
        if status not in {"open", "in_progress", "resolved", "closed"}:
            return error("Unsupported support ticket status.", 400)
        ticket.status = status
        record_audit(
            request.current_user.id,
            "support.ticket_status_changed",
            "support_ticket",
            ticket.id,
            details={"from": old_status, "to": status},
        )
    ticket.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"ticket": staff_ticket_dict(ticket)})


def merge_candidates_for(requester):
    rows = db.session.query(PersonProfile, Household, User).join(
        HouseholdProfileAccess, HouseholdProfileAccess.profile_id == PersonProfile.id).join(
        Household, Household.id == HouseholdProfileAccess.household_id).join(
        HouseholdMembership, HouseholdMembership.household_id == Household.id).join(
        User, User.id == PersonProfile.account_user_id).filter(
        HouseholdMembership.user_id == requester.id, Household.registry_type == "family",
        PersonProfile.is_adult.is_(True), PersonProfile.account_user_id != requester.id,
        User.is_child.is_(False), User.is_support.is_(False)).all()
    return [(profile, household, linked) for profile, household, linked in rows]


@api.get("/support/tickets/<int:ticket_id>/merge-candidates")
@support_required
def ticket_merge_candidates(ticket_id):
    ticket = db.session.get(SupportTicket, ticket_id)
    if ticket is None or not staff_can_access_ticket(ticket):
        return error("Support ticket not found.", 404)
    return jsonify({"requester_email": ticket.user.email, "candidates": [{
        "profile_id": profile.id,
        "profile_name": profile.display_name,
        "household_id": household.id,
        "household_name": household.name,
        "login_email": linked.email,
        "profile_email": profile.member_email,
    } for profile, household, linked in merge_candidates_for(ticket.user)]})


@api.post("/support/tickets/<int:ticket_id>/merge-login")
@support_required
def merge_ticket_login(ticket_id):
    ticket = db.session.get(SupportTicket, ticket_id)
    if ticket is None or not staff_can_access_ticket(ticket):
        return error("Support ticket not found.", 404)
    payload = request.get_json(silent=True) or {}
    if payload.get("confirmed") is not True or type(payload.get("profile_id")) is not int:
        return error("Choose a profile and confirm the account holders agreed to merge.", 400)
    requester = ticket.user
    match = next((row for row in merge_candidates_for(requester) if row[0].id == payload["profile_id"]), None)
    if match is None:
        return error("That profile cannot be merged into this account.", 404)
    profile, household, linked = match
    membership = membership_for(requester, household.id)
    membership.role = "owner"
    household.owner_id = requester.id
    old_membership = membership_for(linked, household.id)
    if old_membership:
        HouseholdMemberProfileAccess.query.filter_by(membership_id=old_membership.id).delete()
        db.session.delete(old_membership)
    profile.account_user_id = requester.id
    profile.member_email = linked.email
    profile.is_adult = True
    linked.session_version += 1
    requester.session_version += 1
    ticket.status = "resolved"
    ticket.updated_at = datetime.now(timezone.utc)
    record_audit(request.current_user.id, "support.logins_merged", "person_profile", profile.id, household.id,
        {"ticket_id": ticket.id, "merged_from_user_id": linked.id, "merged_into_user_id": requester.id})
    db.session.commit()
    return jsonify({"status": "merged", "ticket": ticket_dict(ticket)})


@api.get("/support/audit-logs")
@support_required
def list_support_audit_logs():
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify({"logs": [{
        "id": row.id,
        "actor_id": row.actor_id,
        "household_id": row.household_id,
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "details": row.details,
        "created_at": row.created_at.isoformat(),
    } for row in rows]})


@api.get("/households/<int:household_id>/support-audit-logs")
@authenticated
def household_support_audit_logs(household_id):
    membership = membership_for(request.current_user, household_id)
    if not membership or membership.role not in {"owner", "admin"}:
        return error("Household owner or administrator permission required.", 403)
    rows = AuditLog.query.filter(
        AuditLog.household_id == household_id,
        AuditLog.action.like("support.%"),
    ).order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify({"logs": [{
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "details": row.details,
        "created_at": row.created_at.isoformat(),
    } for row in rows]})

@api.get("/households/search")
@authenticated
def search_families():
    term = request.args.get("q", "").strip().lower()
    if len(term) < 3:
        return jsonify({"households": []})
    allowed = db.session.query(HouseholdMembership.household_id).filter_by(user_id=request.current_user.id)
    rows = db.session.query(Household, User.email).join(
        HouseholdMembership, HouseholdMembership.household_id == Household.id
    ).join(User, User.id == HouseholdMembership.user_id).filter(
        Household.id.in_(allowed), HouseholdMembership.role.in_(("owner", "admin")),
        User.email.contains(term, autoescape=True),
    ).order_by(Household.name, User.email).limit(10).all()
    return jsonify({"households": [{"id": home.id, "name": home.name, "email": email} for home, email in rows]})


def eligible_co_buyer_ids(user):
    from ..adult_family import followed_ids, family_account_ids
    followed = followed_ids(user)
    ids = followed | family_account_ids(user)
    homes = db.session.query(Household.id).join(HouseholdMembership).filter(HouseholdMembership.user_id==user.id, Household.owner_id.in_(followed))
    ids.update(m.user_id for m in HouseholdMembership.query.filter(HouseholdMembership.household_id.in_(homes), or_(HouseholdMembership.is_family_member.is_(True), HouseholdMembership.role.in_(('owner','admin')))).all())
    return ids


@api.get('/reservations/<int:reservation_id>/co-buyers/options')
@authenticated
def co_buyer_options(reservation_id):
    row = GiftReservation.query.filter_by(id=reservation_id, shopper_id=request.current_user.id, status='reserved').first()
    if not row or not shopper_can_see(row.item, request.current_user):
        return error('Reservation not found.', 404)
    from ..adult_family import followed_ids, family_account_ids
    followed = list(eligible_co_buyer_ids(request.current_user))
    people = User.query.filter(User.id.in_(followed), User.is_child.is_(False), User.is_support.is_(False)).order_by(User.name).all()
    return jsonify(people=[{'id': p.id, 'name': p.name, 'families': [h.name for h in Household.query.join(HouseholdMembership).filter(HouseholdMembership.user_id==p.id, Household.registry_type=='family', or_(HouseholdMembership.is_family_member.is_(True), HouseholdMembership.role.in_(('owner','admin')))).all()]} for p in people if p.id != request.current_user.id and shopper_can_see(row.item, p)])


@api.post("/reservations/<int:reservation_id>/co-buyers")
@authenticated
def invite_co_buyer(reservation_id):
    row = GiftReservation.query.filter_by(id=reservation_id, shopper_id=request.current_user.id, status="reserved").with_for_update().first()
    if row is None or not shopper_can_see(row.item, request.current_user):
        return error("Reservation not found.", 404)
    email = str((request.get_json(silent=True) or {}).get("email", "")).strip().lower()
    target_id = (request.get_json(silent=True) or {}).get('user_id')
    if target_id is not None:
        target = db.session.get(User, target_id) if type(target_id) is int else None
        if not target or target.is_child or target.is_support or target.id not in eligible_co_buyer_ids(request.current_user):
            return error('Choose an adult in your family or followed families.', 400)
        email = target.email

    user = User.query.filter_by(email=email).first()
    if user is None or user.is_child or user.is_support or user.id == request.current_user.id or not shopper_can_see(row.item, user):
        return error("Choose another registered user who already has access to this gift list.", 400)
    if CoBuyInvitation.query.filter_by(reservation_id=row.id, email=email).first():
        return error("This person has already been invited.", 409)
    try:
        share = Decimal(str(request.get_json().get('share_percent', 50)))
        if not share.is_finite() or not 0 < share <= 100 or share != share.quantize(Decimal('.01')):
            raise ValueError()
    except (ValueError, InvalidOperation):
        return error('Enter a contribution percentage from 0.01 to 100, with up to two decimal places.', 400)
    allocated = sum(i.share_percent for i in CoBuyInvitation.query.filter_by(reservation_id=row.id, declined=False).all())
    if allocated + share > 100:
        return error('Requested co-buy contributions cannot total more than 100%.', 400)
    db.session.add(CoBuyInvitation(reservation_id=row.id, email=email, share_percent=share))
    db.session.commit()
    warning = None
    if (user.notification_preferences or {}).get('co_buy_emails', True):
        from ..invitation_mail import send_co_buy_invitation
        if not send_co_buy_invitation(user.email, row.item.name, request.current_user.name, format(share, '.2f')):
            warning = 'Invitation sent in app, but the email could not be delivered.'
    return jsonify(status='invited', email_warning=warning), 201


@api.get("/co-buy-invitations")
@authenticated
def co_buy_invitations():
    rows = CoBuyInvitation.query.filter_by(email=request.current_user.email, accepted=False, declined=False).all()
    return jsonify({"invitations": [{"id": row.id, "item_name": row.reservation.item.name, "share_percent": str(row.share_percent)}
        for row in rows if row.reservation.status == "reserved" and shopper_can_see(row.reservation.item, request.current_user)]})


@api.post("/co-buy-invitations/<int:invitation_id>/accept")
@authenticated
def accept_co_buy(invitation_id):
    row = CoBuyInvitation.query.filter_by(id=invitation_id, email=request.current_user.email).first()
    if row is None or row.reservation.status != "reserved" or not shopper_can_see(row.reservation.item, request.current_user):
        return error("Invitation not found.", 404)
    if row.declined:
        return error("This invitation was declined.", 409)
    row.accepted = True
    db.session.commit()
    return jsonify({"status": "accepted"})


@api.patch("/households/<int:household_id>/profiles/<int:profile_id>/relationship")
@authenticated
def update_family_relationship(household_id, profile_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    access = HouseholdProfileAccess.query.filter_by(household_id=household_id, profile_id=profile_id).first()
    if access is None:
        return error("Profile not found in this household.", 404)
    if profile_access(request.current_user, profile_id, write=True) is None:
        return error('Profile edit permission denied.', 403)
    relationship = (request.get_json(silent=True) or {}).get("relationship")
    if not isinstance(relationship, str) or relationship not in FAMILY_RELATIONSHIPS:
        return error("Choose a supported family relationship.", 400)
    access.relationship = relationship
    if relationship in ADULT_RELATIONSHIPS:
        db.session.get(PersonProfile, profile_id).is_adult = True
    db.session.commit()
    return jsonify({"relationship": relationship})


def household_holds(household_id, hide_recipient_id=None):
    query = GiftReservation.query.join(WishlistItem).join(PersonProfile).join(
        HouseholdProfileAccess, HouseholdProfileAccess.profile_id == WishlistItem.profile_id
    ).filter(HouseholdProfileAccess.household_id == household_id, GiftReservation.status == "reserved")
    if hide_recipient_id is not None:
        query = query.filter(or_(PersonProfile.account_user_id.is_(None), PersonProfile.account_user_id != hide_recipient_id))
    return query.order_by(GiftReservation.created_at).all()


def hold_management_dict(row):
    return {"id": row.id, "item_name": row.item.name, "recipient": row.item.profile.display_name,
            "quantity": row.quantity, "expires_at": hold_expiry(row)}


def release_managed_hold(rows, reservation_id, household_id, action):
    row = next((row for row in rows if row.id == reservation_id), None)
    if row is None:
        return error("Active hold not found.", 404)
    row = GiftReservation.query.filter_by(id=reservation_id, status="reserved").populate_existing().with_for_update().first()
    if row is None:
        return error("Active hold not found.", 404)
    row.status = "cancelled"
    record_audit(request.current_user.id, action, "gift_reservation", row.id, household_id)
    db.session.commit()
    return jsonify({"status": "released"})


@api.get("/households/<int:household_id>/holds")
@authenticated
def list_household_holds(household_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    return jsonify({"holds": [hold_management_dict(row) for row in household_holds(household_id, request.current_user.id)]})


@api.delete("/households/<int:household_id>/holds/<int:reservation_id>")
@authenticated
def release_household_hold(household_id, reservation_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    return release_managed_hold(household_holds(household_id, request.current_user.id), reservation_id, household_id, "household.hold_released")


def hold_support_grant(grant_id):
    return SupportAccessGrant.query.filter_by(id=grant_id, support_user_id=request.current_user.id,
        revoked_at=None).filter(SupportAccessGrant.expires_at > datetime.now(timezone.utc)).first()


@api.get("/support/grants/<int:grant_id>/holds")
@support_required
def list_support_holds(grant_id):
    grant = hold_support_grant(grant_id)
    if grant is None:
        return error("Approved support access is missing, revoked, or expired.", 403)
    record_audit(request.current_user.id, "support.holds_viewed", "household", grant.household_id, grant.household_id)
    db.session.commit()
    return jsonify({"holds": [hold_management_dict(row) for row in household_holds(grant.household_id)]})


@api.delete("/support/grants/<int:grant_id>/holds/<int:reservation_id>")
@support_required
def release_support_hold(grant_id, reservation_id):
    grant = hold_support_grant(grant_id)
    if grant is None:
        return error("Approved support access is missing, revoked, or expired.", 403)
    return release_managed_hold(household_holds(grant.household_id), reservation_id, grant.household_id, "support.hold_released")


@api.get('/gift-recommendations')
@authenticated
@limiter.limit('10 per minute')
def gift_recommendations():
    user=request.current_user
    saved=SavedGift.query.filter_by(user_id=user.id).order_by(SavedGift.id.desc()).limit(10).all()
    wishes=PersonalWish.query.filter_by(owner_id=user.id).order_by(PersonalWish.id.desc()).limit(10).all()
    seeds=[r.item for r in saved]+[r.item for r in wishes]
    words={w for item in seeds for w in re.findall(r'[a-z]{3,}', (item.category or '')+' '+item.name.lower()) if w not in {'the','and','for','with'}}
    # Reuse the shopping visibility checks; recommendations never broaden access.
    shopping=shopping_hub().get_json()['items']
    own_homes={m.household_id for m in HouseholdMembership.query.filter(HouseholdMembership.user_id==user.id,HouseholdMembership.role.in_(('owner','admin'))).all()}
    candidates=[i for i in shopping if not any(h['id'] in own_homes for h in i['households']) and (i.get('followed_by_you') or i['households'])]
    candidates.sort(key=lambda i:(sum(w in i['name'].lower() for w in words),i.get('priority') or 0),reverse=True)
    products=[]
    query=(seeds[0].category or seeds[0].name)[:120] if seeds else 'gift ideas books games crafts'
    if search_configured():
        cache=current_app.extensions.setdefault('gift_recommendations_cache',{})
        key=(user.id,query)
        cached=cache.get(key)
        now=datetime.now(timezone.utc)
        if cached and (now-cached[0]).total_seconds()<1800:
            products=cached[1]
        else:
            try:
                products=search_products(query)[:12]
                if len(cache)>=200: cache.clear()
                cache[key]=(now,products)
            except (OSError,ValueError,TypeError):
                pass
    return jsonify(wishes=products,buys=candidates[:12],personalized=bool(seeds))


@api.get("/gift-discovery")
@authenticated
@limiter.limit("20 per minute")
def gift_discovery():
    query = request.args.get("q", "").strip()
    if not query or len(query) > 200:
        return error("Enter a gift search up to 200 characters.", 400)
    if not search_configured():
        return jsonify({"enabled": False, "products": [], "message": "Live product results are not available yet. Browse Google or a store below, or save your idea with an automatic shopping link."})
    try:
        selected={key:request.args[key] for key in ('store','brand','category','min_price','max_price','currency') if key in request.args}
        from ..product_search import validate_filters
        try:validate_filters(selected)
        except ValueError as exc:return error(str(exc),400)
        products = search_products(query,filters=selected) if selected else search_products(query)
    except (OSError, ValueError, TypeError):
        return error("Product search is temporarily unavailable. You can still browse Google or the stores below.", 502)
    return jsonify({"enabled": True, "products": [{**product, "shopping_url": shopping_link(product["product_url"])} for product in products]})


@api.route('/items/<int:item_id>/availability-alert', methods=['PUT', 'DELETE'])
@authenticated
def watch_gift_availability(item_id):
    item = db.session.get(WishlistItem, item_id)
    if not item or not shopper_can_see(item, request.current_user):
        return error('Gift not found.', 404)
    row = GiftAvailabilityAlert.query.filter_by(user_id=request.current_user.id,item_id=item_id).first()
    if request.method == 'DELETE':
        if row: db.session.delete(row)
    else:
        summary = reservation_summary(item, request.current_user)
        if not summary or summary['available'] > 0 or not summary['reserved'] or summary['held_by_you']:
            return error('This gift is not on hold by another shopper.', 409)
        if row is None:
            row = GiftAvailabilityAlert(user_id=request.current_user.id,item_id=item_id)
            db.session.add(row)
        row.ready=False
        row.read_at=None
    db.session.commit()
    return jsonify(watching=request.method=='PUT')


@api.post('/availability-alerts/<int:alert_id>/read')
@authenticated
def read_availability_alert(alert_id):
    row=GiftAvailabilityAlert.query.filter_by(id=alert_id,user_id=request.current_user.id,ready=True).first()
    if not row: return error('Notification not found.',404)
    row.read_at=datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(status='read')


def availability_notifications(user):
    result=[]
    for row in GiftAvailabilityAlert.query.filter_by(user_id=user.id).all():
        if not shopper_can_see(row.item,user): continue
        summary=reservation_summary(row.item,user)
        if not summary: continue
        if not row.ready and summary['available']>0:
            row.ready=True
            row.created_at=datetime.now(timezone.utc)
        if row.ready:
            result.append({'id':'availability-'+str(row.id),'availability_alert_id':row.id,
                'message':row.item.name+' is available again.', 'household_name':'',
                'created_at':row.created_at.isoformat(),'read':row.read_at is not None,'url':'/following'})
    db.session.commit()
    return result


@api.put("/items/<int:item_id>/heart")
@authenticated
def heart_gift(item_id):
    item = db.session.get(WishlistItem, item_id)
    if item is None or not shopper_can_see(item, request.current_user):
        return error("Gift not found.", 404)
    if not SavedGift.query.filter_by(user_id=request.current_user.id, item_id=item_id).first():
        db.session.add(SavedGift(user_id=request.current_user.id, item_id=item_id))
        db.session.commit()
    return jsonify({"is_hearted": True})


@api.delete("/items/<int:item_id>/heart")
@authenticated
def unheart_gift(item_id):
    SavedGift.query.filter_by(user_id=request.current_user.id, item_id=item_id).delete()
    db.session.commit()
    return jsonify({"is_hearted": False})


def set_private_buying(row, buying):
    user = db.session.get(User, row.user_id)
    preferences = dict(user.notification_preferences or {})
    ids = set(preferences.get('buying_private_gift_ids', []))
    ids.discard(row.id)
    if buying and row.status == 'planned':
        ids.add(row.id)
    preferences['buying_private_gift_ids'] = sorted(ids)
    user.notification_preferences = preferences


def private_gift_dict(row):
    return {"id": row.id, "name": row.name, "recipient": row.recipient,
        "household_name": row.household_name, "occasion": row.occasion,
        "store_name": row.store_name, "product_url": shopping_link(row.product_url), "original_product_url": row.product_url, "image_url": row.image_url,
        "estimated_price": str(row.estimated_price) if row.estimated_price is not None else None,
        "currency": row.currency, "status": row.status, "buying_now": row.status == "planned" and row.id in (db.session.get(User, row.user_id).notification_preferences or {}).get("buying_private_gift_ids", [])}


@api.get("/wishlist")
@authenticated
def personal_wishlist():
    user = request.current_user
    hearts = SavedGift.query.filter_by(user_id=user.id).order_by(SavedGift.created_at.desc()).all()
    private = PrivateGift.query.filter_by(user_id=user.id).order_by(PrivateGift.created_at.desc()).all()
    profiles = db.session.query(PersonProfile, Household).join(
        HouseholdProfileAccess, HouseholdProfileAccess.profile_id == PersonProfile.id
    ).join(Household, Household.id == HouseholdProfileAccess.household_id).join(
        HouseholdMembership, HouseholdMembership.household_id == Household.id
    ).filter(HouseholdMembership.user_id == user.id, or_(
        HouseholdMembership.role.in_(("owner", "admin")),
        PersonProfile.account_user_id == user.id,
        HouseholdMembership.share_all_profiles.is_(True),
        PersonProfile.id.in_(db.session.query(HouseholdMemberProfileAccess.profile_id).filter(
            HouseholdMemberProfileAccess.membership_id == HouseholdMembership.id).correlate(HouseholdMembership))
    )).order_by(Household.name, PersonProfile.display_name).all()
    return jsonify({"hearted": [item_dict(row.item, user) for row in hearts if shopper_can_see(row.item, user)],
        "private_gifts": [private_gift_dict(row) for row in private],
        "family_profiles": [{"id": profile.id, "display_name": profile.display_name,
            "preferences": gift_guide(profile),
            "completion": profile_completion(profile) if profile_access(user, profile.id, write=True) is not None else None,
            "profile_type": profile.profile_type, "is_adult": profile.is_adult, "photo_path": profile.photo_path, "avatar_key": profile.avatar_key,
            "household_id": home.id, "household_name": home.name,
            "can_edit": profile_access(user, profile.id, write=True) is not None,
            "can_add": profile_dict(profile, user)['can_add'],
            "can_suggest": profile_dict(profile, user)['can_suggest'],
            "is_me": profile.account_user_id == user.id}
            for profile, home in profiles if profile_access(user, profile.id) is not None]})


@api.post("/private-gifts")
@authenticated
def create_private_gift():
    payload = request.get_json(silent=True) or {}
    if 'buying_now' in payload and type(payload['buying_now']) is not bool:
        return error('Choose a valid buying state.', 400)
    values = {}
    for field, limit in (("name", 200), ("recipient", 120), ("household_name", 160), ("occasion", 160), ("store_name", 120)):
        value = payload.get(field, "")
        if not isinstance(value, str) or len(value.strip()) > limit or (field in {"name", "recipient"} and not value.strip()):
            return error("Enter a gift name and recipient, and keep the details within their length limits.", 400)
        values[field] = value.strip()
    for field in ("product_url", "image_url"):
        value = payload.get(field)
        if value and not safe_product_url(value):
            return error("Shopping and image links must be valid HTTPS URLs.", 400)
        values[field] = value or None
    try:
        price = Decimal(str(payload["estimated_price"])) if payload.get("estimated_price") not in (None, "") else None
        if price is not None and (not price.is_finite() or price < 0 or price > Decimal("99999999.99")):
            raise ValueError()
    except (ValueError, InvalidOperation):
        return error("Enter a valid non-negative price.", 400)
    currency = payload.get("currency", "USD")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
        return error("Currency must contain three letters.", 400)
    row = PrivateGift(user_id=request.current_user.id, estimated_price=price, currency=currency.upper(), **values)
    db.session.add(row)
    db.session.flush()
    if payload.get('buying_now'):
        set_private_buying(row, True)
    db.session.commit()
    return jsonify({"gift": private_gift_dict(row)}), 201


@api.patch("/private-gifts/<int:gift_id>")
@authenticated
def update_private_gift(gift_id):
    row = PrivateGift.query.filter_by(id=gift_id, user_id=request.current_user.id).first()
    if row is None:
        return error("Gift not found.", 404)
    payload = request.get_json(silent=True) or {}
    if 'buying_now' in payload and type(payload['buying_now']) is not bool:
        return error('Choose a valid buying state.', 400)
    status = payload.get('status', row.status if 'buying_now' in payload else None)
    if status not in {"planned", "purchased"}:
        return error("Choose planned or purchased.", 400)
    row.status = status
    if 'buying_now' in payload or status == 'purchased':
        set_private_buying(row, payload.get('buying_now', False))
    db.session.commit()
    return jsonify({"gift": private_gift_dict(row)})


@api.delete("/private-gifts/<int:gift_id>")
@authenticated
def delete_private_gift(gift_id):
    row = PrivateGift.query.filter_by(id=gift_id, user_id=request.current_user.id).first()
    if row is None:
        return error("Gift not found.", 404)
    set_private_buying(row, False)
    db.session.delete(row)
    db.session.commit()
    return jsonify({"status": "removed"})


@api.post("/auth/forgot-password")
@limiter.limit("5 per hour")
def forgot_password():
    payload = request.get_json(silent=True) or {}
    email = normalized_email(payload.get("email"))
    if not email:
        return error("Enter a valid email address.", 400)
    if not current_app.config.get("SMTP_HOST") or not current_app.config.get("MAIL_FROM"):
        return error("Password reset email is not available yet. Please contact the app administrator.", 503)
    user = User.query.filter(func.lower(User.email) == email.lower(), User.is_child.is_(False)).with_for_update().first()
    if user:
        now = datetime.now(timezone.utc)
        PasswordReset.query.filter_by(user_id=user.id, used_at=None).update({"used_at": now})
        token = secrets.token_urlsafe(32)
        db.session.add(PasswordReset(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=now + timedelta(minutes=30), password_version=user.session_version))
        db.session.commit()
        parameters = {"token": token}
        next_path = payload.get("next", "")
        if isinstance(next_path, str) and next_path.startswith("/accept-invitation/") and "\\" not in next_path:
            parameters["next"] = next_path
        link = current_app.config['FRONTEND_ORIGIN'].rstrip('/') + '/reset-password?' + urlencode(parameters)
        send_password_reset(user.email, link)
    return jsonify({"message": "If an account uses that email address, a password reset link will be sent. Check your inbox and spam folder."})


@api.post("/auth/reset-password")
@limiter.limit("10 per hour")
def reset_password():
    payload = request.get_json(silent=True) or {}
    token = payload.get("token", "")
    password = payload.get("password", "")
    if not isinstance(password, str) or len(password) < 10 or len(password) > 1024:
        return error("Choose a password between 10 and 1024 characters.", 400)
    if not isinstance(token, str) or not token or len(token) > 256:
        return error("This reset link is invalid or expired. Request a new one.", 400)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    candidate = PasswordReset.query.filter_by(token_hash=token_hash).first()
    if candidate is None:
        return error("This reset link is invalid or expired. Request a new one.", 400)
    user = User.query.filter_by(id=candidate.user_id).populate_existing().with_for_update().first()
    reset = PasswordReset.query.filter_by(token_hash=token_hash).populate_existing().with_for_update().first()
    now = datetime.now(timezone.utc)
    if not user or not reset or reset.used_at or reset.expires_at.replace(tzinfo=timezone.utc) <= now or reset.password_version != user.session_version:
        return error("This reset link is invalid or expired. Request a new one.", 400)
    user.set_password(password)
    user.session_version += 1
    reset.used_at = now
    record_audit(user.id, "account.password_reset", "user", user.id)
    db.session.commit()
    login_path = "/support/login" if user.is_support else "/login"
    session.clear()
    return jsonify({"message": "Your password has been reset. Sign in with your new password.", "login_path": login_path, "csrf_token": _csrf_token()})


def child_lists_allowed(profile_id, values):
    if not isinstance(values, list) or not values or any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        return False
    return {row.id for row in Wishlist.query.filter(Wishlist.profile_id == profile_id, Wishlist.id.in_(values)).all()} == set(values)


@api.post("/households/<int:household_id>/child-accounts")
@authenticated
def create_child_account(household_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload.get('profile_id'), int) or isinstance(payload.get('profile_id'), bool):
        return error("Choose a valid child profile.", 400)
    if db.session.get(Household, household_id).registry_type == 'company':
        return error("Child accounts are managed in family households, not company registries.", 400)
    profile = PersonProfile.query.filter_by(id=payload.get('profile_id'), profile_type='person').with_for_update().first()
    if profile is None or not HouseholdProfileAccess.query.filter_by(household_id=household_id, profile_id=profile.id).first() or profile_access(request.current_user, profile.id, write=True) is None:
        return error("Choose a child profile in this household.", 404)
    if profile.account_user_id is not None:
        return error("This profile already has a linked account.", 409)
    password = payload.get('password', '')
    if not isinstance(password, str) or not 10 <= len(password) <= 1024:
        return error("Choose a child password between 10 and 1024 characters.", 400)
    lists = payload.get('wishlist_ids')
    if lists is None or lists == []:
        return error('Create a wishlist in Lists & gifts, then choose it for child mode.', 400)
    if not child_lists_allowed(profile.id, lists):
        return error("Choose existing wishlists for this child only.", 400)
    username = 'wish-' + secrets.token_hex(5)
    child = User(name=profile.display_name, email=username + '@child.accounts.invalid',
        is_child=True, child_username=username, parent_user_id=request.current_user.id)
    child.set_password(password)
    db.session.add(child)
    db.session.flush()
    profile.account_user_id = child.id
    for wishlist_id in set(lists):
        db.session.add(ChildWishlistAccess(user_id=child.id, wishlist_id=wishlist_id))
    record_audit(request.current_user.id, 'child.access_created', 'user', child.id, household_id)
    db.session.commit()
    return jsonify({'child': {'id': child.id, 'name': child.name, 'username': username, 'enabled': True}}), 201


@api.get("/households/<int:household_id>/child-accounts")
@authenticated
def list_child_accounts(household_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    profiles = PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id == household_id).all()
    result = []
    for profile in profiles:
        child = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
        if child and child.is_child and child.parent_user_id == request.current_user.id:
            allowed = ChildWishlistAccess.query.filter_by(user_id=child.id).all()
            result.append({'id': child.id, 'name': profile.display_name, 'profile_id': profile.id,
                'username': child.child_username, 'enabled': child.child_enabled,
                'wishlist_ids': [row.wishlist_id for row in allowed]})
    return jsonify({'children': result})


@api.patch("/households/<int:household_id>/child-accounts/<int:child_id>")
@authenticated
def manage_child_account(household_id, child_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    child = User.query.filter_by(id=child_id, is_child=True, parent_user_id=request.current_user.id).with_for_update().first()
    profile = PersonProfile.query.filter_by(account_user_id=child_id).first()
    if not child or not profile or not HouseholdProfileAccess.query.filter_by(household_id=household_id, profile_id=profile.id).first():
        return error("Child account not found.", 404)
    payload = request.get_json(silent=True) or {}
    if not payload or set(payload) - {'enabled', 'password', 'wishlist_ids'}:
        return error("Choose access, a password, or approved wishlists to update.", 400)
    if 'enabled' in payload:
        if not isinstance(payload['enabled'], bool):
            return error("Access must be enabled or disabled.", 400)
        child.child_enabled = payload['enabled']
    if 'password' in payload:
        password = payload['password']
        if not isinstance(password, str) or not 10 <= len(password) <= 1024:
            return error("Choose a password between 10 and 1024 characters.", 400)
        child.set_password(password)
    if 'wishlist_ids' in payload:
        if not child_lists_allowed(profile.id, payload['wishlist_ids']):
            return error("Choose wishlists belonging to this child.", 400)
        ChildWishlistAccess.query.filter_by(user_id=child.id).delete()
        for wishlist_id in set(payload['wishlist_ids']):
            db.session.add(ChildWishlistAccess(user_id=child.id, wishlist_id=wishlist_id))
    child.session_version += 1
    record_audit(request.current_user.id, 'child.access_updated', 'user', child.id, household_id)
    db.session.commit()
    return jsonify({'status': 'updated'})


@api.post("/child/login")
@limiter.limit("10 per minute")
def child_login():
    payload = request.get_json(silent=True) or {}
    username = payload.get('username', '')
    password = payload.get('password', '')
    child = User.query.filter_by(child_username=username, is_child=True, child_enabled=True).first() if isinstance(username, str) else None
    if child is None or not isinstance(password, str) or not child.check_password(password):
        return error("Username or password is incorrect. Ask your parent for help.", 401)
    session.clear()
    session['user_id'] = child.id
    session['auth_version'] = child.session_version
    session['auth_mode'] = 'child'
    current_app.session_interface.regenerate(session)
    return jsonify({'user': child.public_dict(), 'csrf_token': _csrf_token()})


def default_child_wishlist(profile_id):
    return next((row for row in Wishlist.query.filter_by(profile_id=profile_id).order_by(
        Wishlist.is_everyday.desc(), Wishlist.id).all() if not empty_legacy_default_list(row)), None)


def approved_child_lists(child):
    profile = PersonProfile.query.filter_by(account_user_id=child.id).first()
    if not profile:
        return []
    # Access also depends on the supervising parent retaining permission to manage this profile.
    parent = db.session.get(User, child.parent_user_id)
    if not parent or profile_access(parent, profile.id, write=True) is None:
        return []
    ids = db.session.query(ChildWishlistAccess.wishlist_id).filter_by(user_id=child.id)
    lists = Wishlist.query.filter(Wishlist.id.in_(ids), Wishlist.profile_id == profile.id).all()
    explicit_lists=((parent.notification_preferences or {}).get('child_access',{}).get(str(child.id),{})).get('lists_configured',False)
    if not lists and not explicit_lists:
        wishlist = default_child_wishlist(profile.id)
        if wishlist is not None:
            db.session.add(ChildWishlistAccess(user_id=child.id, wishlist_id=wishlist.id))
            db.session.commit()
            lists = [wishlist]
    from ..wishlist_letters import active_letters
    from ..models import WishlistLetter
    letter_ids = [row.wishlist_id for row in active_letters(profile.id)]
    scheduled_ids={row.wishlist_id for row in WishlistLetter.query.filter_by(profile_id=profile.id).all()}
    lists=[row for row in lists if row.id not in scheduled_ids or row.id in letter_ids]
    if explicit_lists:
        return lists
    extra = Wishlist.query.filter(Wishlist.id.in_(letter_ids), Wishlist.profile_id == profile.id).all()
    return list({row.id: row for row in lists + extra}.values())


@api.get('/child/gift-search')
@authenticated
@limiter.limit('20 per minute')
def child_gift_search():
    from ..child_controls import controls_for
    if not controls_for(request.current_user)["web_search"]:
        return error("Ask your parent to allow online gift search.", 403)
    query = request.args.get('q', '').strip()
    if not request.current_user.is_child:
        return error('Child account required.', 403)
    if not query or len(query) > 120:
        return error('What gift would you like to find?', 400)
    if not search_configured(child_safe=True):
        return error('Gift search is unavailable. You can still add ideas or a product link.', 503)
    try:
        products = search_products(query, child_safe=True)
    except (OSError, ValueError, TypeError):
        return error('Search is taking a break. Please try again.', 502)
    session['child_search_products'] = {'user_id': request.current_user.id, 'products': products}
    return jsonify(products=[{'index': index, 'name': p['name'], 'thumbnail': p.get('thumbnail'), 'store_name': p.get('store_name')} for index, p in enumerate(products)])


@api.get("/child/me")
@authenticated
def child_me():
    child = request.current_user
    if not child.is_child:
        return error("Child account required.", 403)
    from ..child_controls import controls_for
    controls = controls_for(child)
    lists = approved_child_lists(child)
    child_profile = PersonProfile.query.filter_by(account_user_id=child.id, profile_type="person").first()
    household_ids = []
    if child_profile:
        household_ids = [
            row[0] for row in db.session.query(HouseholdProfileAccess.household_id)
            .join(Household, Household.id == HouseholdProfileAccess.household_id)
            .filter(
                HouseholdProfileAccess.profile_id == child_profile.id,
                Household.registry_type == "family",
            )
        ]
    pets = PersonProfile.query.join(HouseholdProfileAccess).filter(
        HouseholdProfileAccess.household_id.in_(household_ids),
        PersonProfile.profile_type == "pet",
    ).order_by(PersonProfile.display_name).all() if household_ids and controls["manage_pets"] else []
    from ..wishlist_letters import active_letters, letter_dict
    allowed_ids={row.id for row in lists}
    letters = [letter_dict(row) for row in active_letters(child_profile.id) if row.wishlist_id in allowed_ids] if child_profile and lists else []
    return jsonify({'name': child.name, 'controls': controls, 'letters': letters, 'wishlists': [{'id': wishlist.id, 'title': wishlist.title,
        'items': [{'id': row.id, 'name': row.name, 'description': row.description}
            for row in WishlistItem.query.join(WishlistItemWishlist).filter(WishlistItemWishlist.wishlist_id == wishlist.id).order_by(WishlistItem.created_at.desc()).all()]}
        for wishlist in lists],
        'pets': [{
            'id': pet.id,
            'name': pet.display_name,
            'avatar_key': pet.avatar_key,
            'photo_path': pet.photo_path,
            'items': [{
                'id': item.id,
                'name': item.name,
                'description': item.description,
            } for item in WishlistItem.query.filter_by(profile_id=pet.id).order_by(WishlistItem.created_at.desc()).all()],
        } for pet in pets if pet_family_access(child, pet)]})


@api.post("/child/pets/<int:profile_id>/items")
@authenticated
@limiter.limit("30 per hour", key_func=lambda: str(request.current_user.id))
def child_pet_add_gift(profile_id):
    from ..child_controls import controls_for
    if not controls_for(request.current_user)["manage_pets"]:
        return error("Ask your parent to allow pet wishlists.", 403)
    child = request.current_user
    profile = db.session.get(PersonProfile, profile_id)
    if not child.is_child or not pet_family_access(child, profile):
        return error("Pet wishlist is not available.", 404)
    payload = request.get_json(silent=True) or {}
    name = payload.get("name", "")
    description = payload.get("description", "")
    if set(payload) - {"name", "description"} or not isinstance(name, str) or not name.strip() or len(name.strip()) > 200 or not isinstance(description, str) or len(description) > 2000:
        return error("Enter a gift name up to 200 characters and a short description.", 400)
    wishlist = Wishlist.query.filter_by(profile_id=profile.id).order_by(Wishlist.is_everyday.desc(), Wishlist.id).first()
    if wishlist is None:
        wishlist = Wishlist(profile_id=profile.id, title="Everyday wishes", is_everyday=True)
        db.session.add(wishlist)
        db.session.flush()
    item = WishlistItem(
        profile_id=profile.id,
        created_by_id=child.id,
        name=name.strip(),
        description=description.strip(),
    )
    db.session.add(item)
    db.session.flush()
    db.session.add(WishlistItemWishlist(item_id=item.id, wishlist_id=wishlist.id))
    if wishlist.occasion_id:
        db.session.add(WishlistItemOccasion(item_id=item.id, occasion_id=wishlist.occasion_id))
    db.session.commit()
    return jsonify(item={"id": item.id, "name": item.name, "description": item.description}), 201


@api.delete("/child/pets/<int:profile_id>/items/<int:item_id>")
@authenticated
def child_pet_remove_gift(profile_id, item_id):
    from ..child_controls import controls_for
    if not controls_for(request.current_user)["manage_pets"]:
        return error("Ask your parent to allow pet wishlists.", 403)
    child = request.current_user
    profile = db.session.get(PersonProfile, profile_id)
    item = db.session.get(WishlistItem, item_id)
    if not child.is_child or not pet_family_access(child, profile) or item is None or item.profile_id != profile.id:
        return error("Pet wishlist item is not available.", 404)
    SavedGift.query.filter_by(item_id=item.id).delete()
    reservation_ids = db.session.query(GiftReservation.id).filter_by(item_id=item.id)
    CoBuyInvitation.query.filter(CoBuyInvitation.reservation_id.in_(reservation_ids)).delete(synchronize_session=False)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "removed"})


@api.post("/child/wishlists/<int:wishlist_id>/items")
@authenticated
@limiter.limit("30 per hour", key_func=lambda: str(request.current_user.id))
def child_add_gift(wishlist_id):
    child = request.current_user
    if not child.is_child:
        return error("Child account required.", 403)
    wishlist = next((row for row in approved_child_lists(child) if row.id == wishlist_id), None)
    if wishlist is None:
        return error("Wishlist not available. Ask your parent for help.", 404)
    payload = request.get_json(silent=True) or {}
    if set(payload) == {'product_index'}:
        from ..child_controls import controls_for
        if not controls_for(child)['web_search']:
            return error('Ask your parent to allow online gift search.', 403)
        results = session.get('child_search_products', {})
        index = payload['product_index']
        products = results.get('products', [])
        if results.get('user_id') != child.id or type(index) is not int or not 0 <= index < len(products):
            return error('Search again to add this gift.', 400)
        product = products[index]
        item = WishlistItem(profile_id=wishlist.profile_id, created_by_id=child.id,
            name=product['name'], product_url=product['product_url'], image_path=product.get('thumbnail'),
            store_name=product.get('store_name'), estimated_price=product.get('estimated_price') or None)
        db.session.add(item)
        db.session.flush()
        db.session.add(WishlistItemWishlist(item_id=item.id, wishlist_id=wishlist.id))
        if wishlist.occasion_id:
            db.session.add(WishlistItemOccasion(item_id=item.id, occasion_id=wishlist.occasion_id))
        db.session.commit()
        return jsonify(item={'id': item.id, 'name': item.name}), 201
    if set(payload) - {'name', 'description'}:
        return error("Only a gift name and description can be added here.", 400)
    name, description = payload.get('name', ''), payload.get('description', '')
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 200 or not isinstance(description, str) or len(description) > 2000:
        return error("Enter a gift name up to 200 characters and a short description.", 400)
    item = WishlistItem(profile_id=wishlist.profile_id, created_by_id=child.id, name=name.strip(), description=description.strip())
    db.session.add(item)
    db.session.flush()
    db.session.add(WishlistItemWishlist(item_id=item.id, wishlist_id=wishlist.id))
    if wishlist.occasion_id:
        db.session.add(WishlistItemOccasion(item_id=item.id, occasion_id=wishlist.occasion_id))
    db.session.commit()
    return jsonify({'item': {'id': item.id, 'name': item.name, 'description': item.description}}), 201


@api.post('/child/wishlists/<int:wishlist_id>/links')
@authenticated
@limiter.limit('10 per hour', key_func=lambda: str(request.current_user.id))
def child_add_link(wishlist_id):
    from ..child_controls import controls_for
    if not controls_for(request.current_user)["product_links"]:
        return error("Ask your parent to allow product links.", 403)
    child = request.current_user
    if not child.is_child:
        return error('Child account required.', 403)
    wishlist = next((row for row in approved_child_lists(child) if row.id == wishlist_id), None)
    if wishlist is None:
        return error('Wishlist not available. Ask your parent for help.', 404)
    payload = request.get_json(silent=True) or {}
    if set(payload) != {'url'} or not safe_product_url(payload.get('url')):
        return error('Paste a public HTTPS product link.', 400)
    try:
        preview = preview_link(payload['url'])
    except (ValueError, OSError):
        return error('This store could not provide gift details. Ask your parent for help.', 400)
    if not preview.get('title'):
        return error('This link has no gift name. Ask your parent for help.', 400)
    item = WishlistItem(profile_id=wishlist.profile_id, created_by_id=child.id,
        name=preview['title'], product_url=payload['url'], image_path=preview.get('image_url'),
        store_name=preview.get('store_name'), quantity=1, priority=2, request_type='want')
    db.session.add(item)
    db.session.flush()
    db.session.add(WishlistItemWishlist(item_id=item.id, wishlist_id=wishlist.id))
    if wishlist.occasion_id:
        db.session.add(WishlistItemOccasion(item_id=item.id, occasion_id=wishlist.occasion_id))
    db.session.commit()
    return jsonify({'item': {'id': item.id, 'name': item.name, 'description': item.description}}), 201


@api.patch("/auth/theme")
@authenticated
def update_account_theme():
    key = (request.get_json(silent=True) or {}).get('theme_key')
    shared = SharedTheme.query.filter_by(id=int(key[1:])).first() if isinstance(key, str) and key.startswith('t') and key[1:].isdigit() else None
    if shared and (shared.data.get('purpose','app')!='app' or not shared.data.get('active',True)):
        return error('Choose an available app theme.',400)
    if key not in ('classic', 'christmas', 'halloween', 'kids') and not shared:
        return error('Choose a supported theme.', 400)
    if request.current_user.is_child and (not shared or shared.data['audience'] not in ('kids', 'everyone')):
        return error('Choose a kids theme.', 400)
    request.current_user.theme_key = key
    db.session.commit()
    return jsonify({'theme_key': key})


@api.post("/auth/theme/photo")
@authenticated
def upload_account_background():
    return error('Personal background uploads have been replaced by shared themes.', 410)


@api.delete("/auth/theme/photo")
@authenticated
def remove_account_background():
    request.current_user.theme_image_path = None
    if request.current_user.theme_key == 'custom':
        request.current_user.theme_key = 'classic'
    db.session.commit()
    return jsonify({'theme_key': request.current_user.theme_key})


@api.post("/link-preview")
@authenticated
@limiter.limit("20 per minute")
def product_link_preview():
    try:
        result = preview_link((request.get_json(silent=True) or {}).get('url'))
    except (OSError, ValueError, TimeoutError):
        return error("This link could not be previewed. Use a public HTTPS product link, or add the gift without a preview image.", 400)
    return jsonify({'preview': result})


@api.get("/households/<int:household_id>/shopper-preview")
@authenticated
def registry_shopper_preview(household_id):
    _, failure = require_household_admin(household_id)
    if failure:
        return failure
    home = db.session.get(Household, household_id)
    profiles = PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id == household_id).all()
    result = []
    for profile in profiles:
        lists = Wishlist.query.filter_by(profile_id=profile.id).all()
        wishes = []
        for wishlist in lists:
            if not list_is_shared(wishlist):
                continue
            query = WishlistItem.query.join(WishlistItemWishlist).filter(WishlistItemWishlist.wishlist_id == wishlist.id)
            if wishlist.share_publicly is None:
                query = query.filter(WishlistItem.family_only.is_(False))
            items = query.all()
            wishes.append({'title': wishlist.title, 'items': [{
                'name': item.name, 'description': item.description, 'store_name': item.store_name,
                'product_url': item.product_url, 'image_url': item.image_path,
                'estimated_price': str(item.estimated_price) if item.estimated_price is not None else None,
                'currency': item.currency, 'quantity': item.quantity,
            } for item in items]})
        result.append({'id': profile.id, 'display_name': profile.display_name,
            'photo_path': profile.photo_path, 'birthday': profile.birthday.strftime('%m-%d') if profile.birthday and profile.birthday_shared else None,
            'wishlists': wishes})
    return jsonify({'household': {'name': home.name, 'photo_path': home.photo_path, 'registry_type': home.registry_type},
        'profiles': result})


def personal_wish_audience(user):
    mine = aliased(HouseholdMembership)
    theirs = aliased(HouseholdMembership)
    rows = db.session.query(User, Household).join(theirs, theirs.user_id == User.id).join(
        Household, Household.id == theirs.household_id).join(mine, mine.household_id == Household.id).filter(
        mine.user_id == user.id, or_(mine.role.in_(('owner', 'admin')), theirs.role.in_(('owner', 'admin'))), Household.registry_type == 'family',
        User.id != user.id, User.is_child.is_(False), User.is_support.is_(False)).order_by(User.name).all()
    people = {}
    for person, home in rows:
        people.setdefault(person.id, {'id': person.id, 'name': person.name, 'families': []})['families'].append(home.name)
    own_ids = {row.household_id for row in HouseholdMembership.query.filter(HouseholdMembership.user_id == user.id, HouseholdMembership.role.in_(('owner', 'admin'))).all()}
    own_names = {home.name for home in Household.query.filter(Household.id.in_(own_ids)).all()}
    for person in people.values():
        person['is_my_family'] = bool(own_names.intersection(person['families']))
    return sorted(people.values(), key=lambda person: (not person['is_my_family'], person['name'].lower()))


def personal_viewer_allowed(wish, user):
    if user.is_child or user.is_support or wish.owner_id == user.id:
        return False
    if wish.visibility == 'public':
        return True
    if wish.visibility == 'followers':
        from ..adult_family import followed_ids
        return wish.owner_id in followed_ids(user)
    if wish.visibility == 'family':
        owner_homes = db.session.query(HouseholdMembership.household_id).filter(HouseholdMembership.user_id == wish.owner_id, or_(HouseholdMembership.role.in_(('owner','admin')),HouseholdMembership.is_family_member.is_(True)))
        return HouseholdMembership.query.filter(HouseholdMembership.user_id == user.id, HouseholdMembership.household_id.in_(owner_homes), HouseholdMembership.role.in_(('owner','admin','profile_manager','editor'))).first() is not None
    if wish.visibility == 'private':
        return False
    if not PersonalWishViewer.query.filter_by(wish_id=wish.id, user_id=user.id).first():
        return False
    owner = db.session.get(User, wish.owner_id)
    return owner is not None and user.id in {person['id'] for person in personal_wish_audience(owner)}


def personal_wish_dict(wish, user, owned=False):
    result = {'id': wish.id, 'occasion': wish.occasion, 'visibility': wish.visibility, 'item': {**item_dict(wish.item, user), 'occasion': wish.occasion}}
    if owned:
        result['viewer_ids'] = [row.user_id for row in wish.viewers]
    return result


@api.get('/personal-wishes')
@authenticated
def list_personal_wishes():
    user = request.current_user
    mine = PersonalWish.query.filter_by(owner_id=user.id).order_by(PersonalWish.id.desc()).all()
    shared = visible_personal_candidates(user).order_by(PersonalWish.id.desc()).all()
    return jsonify({'mine': [personal_wish_dict(row, user, True) for row in mine],
        'shared': [personal_wish_dict(row, user) for row in shared if personal_viewer_allowed(row, user)],
        'audience': personal_wish_audience(user)})


def personal_wish_values(payload, user, existing=None):
    values = {}
    for field, maximum in (('name', 200), ('description', 2000), ('store_name', 120)):
        value = payload.get(field, getattr(existing, field, '') if existing else '') or ''
        if not isinstance(value, str) or len(value.strip()) > maximum or (field == 'name' and not value.strip()):
            raise ValueError('Enter a wish title and keep the details within their length limits.')
        values[field] = value.strip()
    for field, attribute in (('product_url', 'product_url'), ('image_url', 'image_path')):
        value = payload.get(field, getattr(existing, attribute, None) if existing else None)
        if value and not safe_product_url(value):
            raise ValueError('Use valid HTTPS shopping and image links.')
        values[attribute] = value or None
    price = payload.get('estimated_price', existing.estimated_price if existing else None)
    try:
        price = Decimal(str(price)) if price not in (None, '') else None
        if price is not None and (not price.is_finite() or price < 0 or price > Decimal('99999999.99')):
            raise ValueError()
    except (InvalidOperation, ValueError):
        raise ValueError('Enter a valid price.')
    values['estimated_price'] = price
    currency=payload.get('currency',existing.currency if existing else 'USD')
    if not isinstance(currency,str) or not re.fullmatch('[A-Za-z]{3}',currency):
        raise ValueError('Choose a valid three-letter currency.')
    values['currency']=currency.upper()
    try:
        quantity=int(payload.get('quantity',existing.quantity if existing else 1))
    except (TypeError,ValueError):
        raise ValueError('Choose a positive quantity.')
    if quantity<1 or quantity>10000:
        raise ValueError('Choose a quantity between 1 and 10,000.')
    values['quantity']=quantity
    for field in ('notes','category'):
        value=payload.get(field,getattr(existing,field,'') if existing else '') or ''
        if not isinstance(value,str) or len(value)> (120 if field=='category' else 2000):
            raise ValueError('Keep gift notes and category within their length limits.')
        values[field]=value
    try:
        priority = int(payload.get('priority', existing.priority if existing else 2))
    except (ValueError, TypeError):
        raise ValueError('Priority must be from 1 to 4.')
    if priority not in (1, 2, 3, 4):
        raise ValueError('Priority must be from 1 to 4.')
    values['priority'] = priority
    eligible = {person['id'] for person in personal_wish_audience(user)}
    viewers = payload.get('viewer_ids', list(eligible))
    if not isinstance(viewers, list) or any(not isinstance(value, int) or isinstance(value, bool) for value in viewers) or not set(viewers).issubset(eligible):
        raise ValueError('Choose signed-in family members from the audience list.')
    return values, set(viewers)


@api.post('/personal-wishes')
@authenticated
def create_personal_wish():
    user = User.query.filter_by(id=request.current_user.id).with_for_update().first()
    payload = request.get_json(silent=True) or {}
    if type(payload.get('avoid_duplicate',False)) is not bool:
        return error('Choose a valid duplicate-save option.',400)
    if payload.get('avoid_duplicate'):
        from ..commerce_urls import validated_product_url
        try:
            validated_product_url(payload.get('product_url'))
            if payload.get('image_url'):
                validated_product_url(payload['image_url'])
        except ValueError as exc:
            return error(str(exc),400)
        existing=PersonalWish.query.join(WishlistItem).filter(PersonalWish.owner_id==user.id,WishlistItem.product_url==payload['product_url'],PersonalWish.occasion==str(payload.get('occasion','')).strip()).first()
        if existing:
            return jsonify(wish=personal_wish_dict(existing,user,True),already_saved=True),200
    try:
        values, viewers = personal_wish_values(payload, user)
    except ValueError as exc:
        return error(str(exc), 400)
    profile = PersonProfile.query.filter_by(account_user_id=user.id,is_adult=True).order_by(PersonProfile.id).first()
    if not profile:
        profile = PersonProfile(account_user_id=user.id, display_name=user.name)
        db.session.add(profile)
        db.session.flush()
    wishlist = Wishlist.query.filter_by(profile_id=profile.id, is_everyday=True).first()
    if not wishlist:
        wishlist = Wishlist(profile_id=profile.id, title='Wishes for me', is_everyday=True)
        db.session.add(wishlist)
        db.session.flush()
    item = WishlistItem(profile_id=profile.id, created_by_id=user.id, **values)
    db.session.add(item)
    db.session.flush()
    db.session.add(WishlistItemWishlist(item_id=item.id, wishlist_id=wishlist.id))
    occasion = payload.get('occasion', '')
    if not isinstance(occasion, str) or len(occasion) > 80:
        return error('Choose an occasion within 80 characters.', 400)
    visibility = payload.get('visibility', 'custom')
    if visibility not in ('private','family','followers','public','custom'):
        return error('Choose a supported audience.',400)
    wish = PersonalWish(owner_id=user.id, item_id=item.id, occasion=occasion.strip(), visibility=visibility)
    db.session.add(wish)
    db.session.flush()
    for viewer_id in viewers:
        db.session.add(PersonalWishViewer(wish_id=wish.id, user_id=viewer_id))
    from ..commerce import record_product_metadata
    record_product_metadata(item)
    db.session.commit()
    return jsonify({'wish': personal_wish_dict(wish, user, True)}), 201


@api.patch('/personal-wishes/<int:wish_id>')
@authenticated
def update_personal_wish(wish_id):
    user = request.current_user
    wish = PersonalWish.query.filter_by(id=wish_id, owner_id=user.id).with_for_update().first()
    if wish is None:
        return error('Wish not found.', 404)
    payload = request.get_json(silent=True) or {}
    occasion = payload.get('occasion', wish.occasion)
    if not isinstance(occasion, str) or len(occasion) > 80:
        return error('Choose an occasion within 80 characters.', 400)
    wish.occasion = occasion.strip()
    visibility = payload.get('visibility', wish.visibility)
    if visibility not in ('private','family','followers','public','custom'):
        return error('Choose a supported audience.',400)
    wish.visibility = visibility
    if 'viewer_ids' not in payload:
        payload['viewer_ids'] = [row.user_id for row in wish.viewers if row.user_id in {person['id'] for person in personal_wish_audience(user)}]
    try:
        values, viewers = personal_wish_values(payload, user, wish.item)
    except ValueError as exc:
        return error(str(exc), 400)
    for field, value in values.items():
        setattr(wish.item, field, value)
    removed = {row.user_id for row in wish.viewers} - viewers
    if removed:
        GiftReservation.query.filter(GiftReservation.item_id == wish.item_id, GiftReservation.shopper_id.in_(removed), GiftReservation.status == 'reserved').update({'status': 'cancelled'}, synchronize_session='fetch')
    for row in list(wish.viewers):
        if row.user_id not in viewers:
            db.session.delete(row)
    current = {row.user_id for row in wish.viewers}
    for viewer_id in viewers - current:
        db.session.add(PersonalWishViewer(wish_id=wish.id, user_id=viewer_id))
    db.session.flush()
    for hold in GiftReservation.query.filter_by(item_id=wish.item_id, status='reserved').all():
        shopper = db.session.get(User, hold.shopper_id)
        if not shopper or not personal_viewer_allowed(wish, shopper):
            hold.status = 'cancelled'
    db.session.commit()
    return jsonify({'status': 'updated'})


@api.delete('/personal-wishes/<int:wish_id>')
@authenticated
def delete_personal_wish(wish_id):
    wish = PersonalWish.query.filter_by(id=wish_id, owner_id=request.current_user.id).first()
    if wish is None:
        return error('Wish not found.', 404)
    item = wish.item
    SavedGift.query.filter_by(item_id=item.id).delete()
    reservation_ids = db.session.query(GiftReservation.id).filter_by(item_id=item.id)
    CoBuyInvitation.query.filter(CoBuyInvitation.reservation_id.in_(reservation_ids)).delete(synchronize_session=False)
    db.session.delete(wish)
    db.session.flush()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'status': 'removed'})


@api.get('/household-session')
@authenticated
def household_session():
    user = request.current_user
    if user.is_child or user.is_support:
        return error('Household account required.', 403)
    profiles = PersonProfile.query.join(HouseholdProfileAccess).join(HouseholdMembership,
        HouseholdMembership.household_id == HouseholdProfileAccess.household_id).filter(
        HouseholdMembership.user_id == user.id, or_(HouseholdMembership.role.in_(('owner', 'admin')),PersonProfile.account_user_id==user.id),
        HouseholdProfileAccess.can_edit.is_(True), PersonProfile.profile_type != "pet").distinct().all()
    return jsonify({'has_parent_pin': bool(user.parent_pin_hash), 'active_profile_id': session.get('active_member_profile_id'),
        'profiles': [{'id': profile.id, 'name': profile.display_name, 'photo_path': profile.photo_path, 'avatar_key': profile.avatar_key, 'is_you': profile.account_user_id == user.id, 'is_adult': profile.is_adult,
            'is_guardian': profile.is_guardian, 'child_login_available': bool(profile.account_user_id and db.session.get(User, profile.account_user_id).is_child), 'uses_separate_login': bool(profile.account_user_id and profile.account_user_id!=user.id and not db.session.get(User,profile.account_user_id).is_child)} for profile in profiles]})


@api.post('/household-session/pin')
@authenticated
@limiter.limit('5 per minute')
def set_parent_pin():
    user = request.current_user
    payload = request.get_json(silent=True) or {}
    pin = payload.get('pin', '')
    if user.is_child or user.is_support or not user.check_password(payload.get('password', '')):
        return error('Enter the household account password.', 403)
    if not isinstance(pin, str) or not pin.isascii() or not pin.isdigit() or not 6 <= len(pin) <= 12:
        return error('Choose a PIN of 6 to 12 digits.', 400)
    user.parent_pin_hash = generate_password_hash(pin)
    db.session.commit()
    return jsonify({'status': 'saved'})


@api.post('/household-session/switch')
@authenticated
def switch_household_profile():
    user = request.current_user
    if user.is_child or user.is_support:
        return error('Household account required.', 403)
    profile_id = (request.get_json(silent=True) or {}).get('profile_id')
    # Adult profiles are an open switcher within a shared household account.
    if profile_id is None:
        session.pop('active_member_profile_id', None)
        return jsonify({'status': 'household'})
    profile = profile_access(user, profile_id)
    if profile and profile.profile_type == "pet":
        return error("Pets have wishlists, not login profiles.", 400)
    if profile and profile.account_user_id and profile.account_user_id != user.id:
        linked_user = db.session.get(User, profile.account_user_id)
        if linked_user and not linked_user.is_child:
            return error('This adult uses their own login.', 403)
    if profile and profile.account_user_id == user.id and profile.is_adult:
        session['active_member_profile_id'] = profile.id
        return jsonify(status='adult', profile_id=profile.id)
    grant = db.session.query(HouseholdProfileAccess).join(HouseholdMembership,
        HouseholdMembership.household_id == HouseholdProfileAccess.household_id).filter(
        HouseholdProfileAccess.profile_id == profile_id, HouseholdProfileAccess.can_edit.is_(True),
        HouseholdMembership.user_id == user.id, HouseholdMembership.role.in_(('owner', 'admin'))).first()
    if not profile or not grant:
        return error('Member profile not available.', 404)
    if profile.is_adult:
        session['active_member_profile_id'] = profile.id
        return jsonify({'status': 'adult', 'profile_id': profile.id})
    child = db.session.get(User, profile.account_user_id) if profile.account_user_id else None
    if not user.parent_pin_hash:
        return error('Set a parent PIN before entering child mode.', 400)
    if child is None and profile.account_user_id is None:
        wishlist = default_child_wishlist(profile.id)
        if wishlist is None:
            return error('Create a wishlist in Lists & gifts and approve it in Child access & PIN first.', 400)
        username = 'wish-' + secrets.token_hex(5)
        child = User(name=profile.display_name, email=username + '@child.accounts.invalid',
            is_child=True, child_username=username, parent_user_id=user.id)
        child.set_password(secrets.token_urlsafe(48))
        db.session.add(child)
        db.session.flush()
        profile.account_user_id = child.id
        db.session.add(ChildWishlistAccess(user_id=child.id, wishlist_id=wishlist.id))
        db.session.commit()
    if not child or not child.is_child or child.parent_user_id != user.id or not child.child_enabled:
        return error('Child profile is unavailable. Check family settings.', 400)
    session.clear()
    session.update({'user_id': child.id, 'auth_version': child.session_version, 'auth_mode': 'child',
        'household_return_user_id': user.id, 'household_return_version': user.session_version})
    current_app.session_interface.regenerate(session)
    return jsonify({'status': 'child', 'csrf_token': _csrf_token()})


def pin_reset_parent():
    user = request.current_user
    if not user.is_child:
        return user
    parent = db.session.get(User, session.get('household_return_user_id'))
    return parent if parent and user.parent_user_id == parent.id and parent.session_version == session.get('household_return_version') else None


@api.post('/household-session/pin/reset')
@authenticated
@limiter.limit('3 per hour')
def request_parent_pin_reset():
    parent = pin_reset_parent()
    if parent is None:
        return error('Sign in to your household first.', 403)
    if not account_mail_available():
        return error('Email delivery is not configured. Sign in as an adult to change the PIN.', 503)
    challenge = issue_email_code(parent, 'parent_pin')
    if not challenge:
        return error('The PIN email could not be sent.', 503)
    return jsonify(challenge_id=challenge, message='Check the main email for your new 6-digit PIN. Enter it to confirm.')


@api.post('/household-session/pin/reset/confirm')
@authenticated
@limiter.limit('10 per hour')
def confirm_parent_pin_reset():
    parent = pin_reset_parent()
    if parent is None:
        return error('Sign in to your household first.', 403)
    payload = request.get_json(silent=True) or {}
    row, failure = consume_email_code(payload.get('challenge_id'), payload.get('code'), 'parent_pin', parent)
    if failure:
        return failure
    parent.parent_pin_hash = generate_password_hash(payload['code'])
    db.session.commit()
    return jsonify(message='Parent PIN updated. Use this PIN to leave child mode.')


@api.post('/household-session/exit-child')
@authenticated
@limiter.limit('5 per minute')
def exit_child_mode():
    return_user_id = session.get('household_return_user_id')
    parent = db.session.get(User, return_user_id) if return_user_id else None
    child = request.current_user
    if not child.is_child or not parent or child.parent_user_id != parent.id or parent.session_version != session.get('household_return_version'):
        return error('No household session to return to. Sign in again.', 403)
    pin = (request.get_json(silent=True) or {}).get('pin', '')
    if not isinstance(pin, str) or not parent.parent_pin_hash or not check_password_hash(parent.parent_pin_hash, pin):
        return error('Parent PIN is incorrect.', 403)
    session.clear()
    session.update({'user_id': parent.id, 'auth_version': parent.session_version, 'auth_mode': 'family'})
    current_app.session_interface.regenerate(session)
    return jsonify({'status': 'household', 'csrf_token': _csrf_token()})


def consume_email_code(challenge_id, code, purpose, user, target=None):
    if not isinstance(challenge_id, str) or not isinstance(code, str):
        return None, error('Enter the one-time code sent to the main email.', 400)
    row = AccountEmailCode.query.filter_by(id=challenge_id).with_for_update().first()
    now = datetime.now(timezone.utc)
    if not row or row.user_id != user.id or row.purpose != purpose or row.target_email != target or row.used_at or row.attempts >= 5 or row.expires_at.replace(tzinfo=timezone.utc) <= now or row.session_version != user.session_version:
        return None, error('Code is invalid or expired. Request a new code.', 400)
    row.attempts += 1
    if not check_password_hash(row.code_hash, code):
        db.session.commit()
        return None, error('Code is incorrect. Request a new code after five attempts.', 400)
    row.used_at = now
    return row, None


def issue_email_code(user, purpose, target=None):
    now = datetime.now(timezone.utc)
    AccountEmailCode.query.filter_by(user_id=user.id, purpose=purpose, used_at=None).update({'used_at': now})
    code = str(secrets.randbelow(1000000)).zfill(6)
    row = AccountEmailCode(id=secrets.token_urlsafe(24), user_id=user.id, purpose=purpose, target_email=target,
        code_hash=generate_password_hash(code), expires_at=now + timedelta(minutes=10), session_version=user.session_version)
    db.session.add(row)
    db.session.commit()
    if not send_account_code(user.email, code, purpose):
        row.used_at = now
        db.session.commit()
        return None
    return row.id


def account_mail_available():
    return bool(current_app.config.get('SMTP_HOST') and current_app.config.get('MAIL_FROM'))


@api.post('/auth/recovery-code')
@limiter.limit('5 per hour')
def request_recovery_code():
    payload = request.get_json(silent=True) or {}
    email = normalized_email(payload.get('email'))
    if not email:
        return error('Enter the main household email address.', 400)
    if not account_mail_available():
        return error('Recovery email is not configured yet. Contact the app administrator.', 503)
    user = User.query.filter(func.lower(User.email) == email.lower(), User.is_child.is_(False)).with_for_update().first()
    challenge_id = secrets.token_urlsafe(24)
    if user:
        # Generic response also covers delivery failure to avoid exposing account existence.
        challenge_id = issue_email_code(user, 'password') or challenge_id
    return jsonify({'challenge_id': challenge_id, 'message': 'If this is the main account email, a one-time code will be sent. Check your inbox and spam folder.'})


@api.post('/auth/recovery-code/verify')
@limiter.limit('20 per hour')
def verify_recovery_code():
    payload = request.get_json(silent=True) or {}
    email = normalized_email(payload.get('email'))
    user = User.query.filter(func.lower(User.email) == (email or '').lower(), User.is_child.is_(False)).with_for_update().first()
    if not user:
        return error('Code is invalid or expired. Request a new code.', 400)
    row, failure = consume_email_code(payload.get('challenge_id'), payload.get('code'), 'password', user)
    if failure:
        return failure
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    PasswordReset.query.filter_by(user_id=user.id, used_at=None).update({'used_at': now})
    db.session.add(PasswordReset(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=now + timedelta(minutes=10), password_version=user.session_version))
    db.session.commit()
    return jsonify({'token': token})


@api.post('/auth/email-change-code')
@authenticated
@limiter.limit('5 per hour')
def request_email_change_code():
    user = request.current_user
    payload = request.get_json(silent=True) or {}
    email = normalized_email(payload.get('email'))
    password = payload.get('current_password')
    if not isinstance(password, str) or not user.check_password(password):
        return error('Enter the current household password.', 400)
    if not email or email.lower() == user.email.lower():
        return error('Enter a different valid main email address.', 400)
    if User.query.filter(func.lower(User.email) == email.lower(), User.id != user.id).first():
        return error('That email is already in use.', 409)
    if not account_mail_available():
        return error('Verification email is not configured yet. Contact the app administrator.', 503)
    challenge_id = issue_email_code(user, 'email_change', email)
    if not challenge_id:
        return error('The code could not be emailed. Try again later.', 503)
    return jsonify({'challenge_id': challenge_id, 'message': 'A verification code was sent to your current main email.'})


def discard_pending_photo(row):
    if row.purpose != 'family_photo_change' or not row.pending_data:
        return
    image = row.pending_data.get('photo_path')
    if not image or Household.query.filter_by(photo_path=image).first() or PersonProfile.query.filter_by(photo_path=image).first():
        return
    root = Path(current_app.config['UPLOAD_FOLDER']).resolve()
    candidate = (root / Path(image).name).resolve()
    if candidate.parent == root:
        try:
            candidate.unlink(missing_ok=True)
        except OSError:
            current_app.logger.warning('An unused pending photo could not be removed.')


def request_change_approval(user, purpose, pending_data):
    if not account_mail_available():
        return error('Main-email approval is required. Configure email delivery before making this change.', 503)
    now = datetime.now(timezone.utc)
    for previous in AccountEmailCode.query.filter_by(user_id=user.id, purpose=purpose, used_at=None).all():
        discard_pending_photo(previous)
        previous.used_at = now
        previous.pending_data = None
    token = secrets.token_urlsafe(32)
    row = AccountEmailCode(id=secrets.token_urlsafe(24), user_id=user.id, purpose=purpose,
        code_hash=generate_password_hash(token), expires_at=now + timedelta(minutes=30),
        session_version=user.session_version, pending_data=pending_data)
    db.session.add(row); db.session.commit()
    link = current_app.config['FRONTEND_ORIGIN'].rstrip('/') + '/approve-change?' + urlencode({'id': row.id, 'token': token})
    if not send_change_approval(user.email, link, purpose):
        discard_pending_photo(row)
        row.used_at = now; row.pending_data = None; db.session.commit()
        return error('Approval email could not be delivered. Nothing has changed.', 503)
    return jsonify({'status': 'pending_approval', 'message': 'Check the main household email to approve or cancel. Nothing has changed yet.'})


def pending_approval(payload):
    row_id, token = payload.get('id'), payload.get('token')
    if not isinstance(row_id, str) or not isinstance(token, str) or len(row_id) > 64 or len(token) > 100:
        return None, None
    row = AccountEmailCode.query.filter_by(id=row_id).with_for_update().first()
    if not row or row.purpose not in ('password_change', 'family_photo_change') or row.used_at or row.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        return None, None
    owner = db.session.get(User, row.user_id)
    if not owner or owner.session_version != row.session_version or not check_password_hash(row.code_hash, token):
        return None, None
    return row, owner


@api.post('/auth/change-approval/details')
@limiter.limit('20 per hour')
def change_approval_details():
    row, owner = pending_approval(request.get_json(silent=True) or {})
    if not row:
        return error('Approval link is invalid, expired, or already used.', 400)
    return jsonify({'purpose': row.purpose, 'message': 'Nothing has changed yet. Choose approve or cancel.'})


@api.get('/auth/change-approval/photo')
@limiter.limit('20 per hour')
def change_approval_photo():
    row, owner = pending_approval(request.args)
    if not row or row.purpose != 'family_photo_change':
        return error('Photo approval not available.', 404)
    filename = Path(row.pending_data['photo_path']).name
    response = send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@api.post('/auth/change-approval')
@limiter.limit('20 per hour')
def confirm_account_change():
    payload = request.get_json(silent=True) or {}
    row, owner = pending_approval(payload)
    if not row or type(payload.get('approve')) is not bool:
        return error('Approval link is invalid, expired, or already used.', 400)
    if payload['approve']:
        if row.purpose == 'password_change':
            owner.password_hash = row.pending_data['password_hash']
            owner.session_version += 1
        else:
            household = db.session.get(Household, row.pending_data['household_id'])
            if not household or household.owner_id != owner.id:
                return error('This household is no longer available.', 400)
            household.photo_path = row.pending_data['photo_path']
        record_audit(owner.id, row.purpose + '.email_approved', 'user', owner.id)
    if not payload['approve']:
        discard_pending_photo(row)
    row.used_at = datetime.now(timezone.utc)
    row.pending_data = None
    db.session.commit()
    if payload['approve'] and row.purpose == 'password_change':
        session.clear()
    return jsonify({'message': 'Change approved.' if payload['approve'] else 'Change cancelled. Nothing was changed.', 'password_changed': bool(payload['approve'] and row.purpose == 'password_change')})


@api.post('/households/<int:household_id>/identify-me')
@authenticated
def identify_household_owner(household_id):
    user = request.current_user
    home = db.session.get(Household, household_id)
    if not home or home.owner_id != user.id:
        return error('Only the main household account can choose its owner profile.', 403)
    pid = (request.get_json(silent=True) or {}).get('profile_id')
    if type(pid) is not int:
        return error('Choose your adult family profile.', 400)
    profile = db.session.get(PersonProfile, pid)
    if not profile or profile.profile_type != 'person' or not HouseholdProfileAccess.query.filter_by(household_id=household_id, profile_id=pid).first():
        return error('Choose a person in this household.', 404)
    if profile.account_user_id not in (None, user.id):
        return error('This profile already has a different account or child login.', 409)
    own_profiles = PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id == household_id, PersonProfile.account_user_id == user.id).all()
    for previous in own_profiles:
        if previous.id != pid:
            previous.account_user_id = None
    profile.account_user_id = user.id
    profile.is_adult = True
    profile.is_guardian = True
    profile.member_email = user.email
    session['active_member_profile_id'] = profile.id
    db.session.commit()
    return jsonify({'profile_id': profile.id, 'message': 'This is your main adult profile.'})


@api.get('/family-connections')
@authenticated
def family_connections():
    repair_accepted_family_sharing(request.current_user)
    user = request.current_user
    from ..adult_family import followed_ids
    followed_accounts = User.query.filter(User.id.in_(followed_ids(user))).order_by(User.name).all()
    result = []
    for person in followed_accounts:
        if not person or person.is_child or person.is_support:
            continue
        homes = Household.query.join(HouseholdMembership, HouseholdMembership.household_id == Household.id).filter(
            Household.owner_id == person.id, Household.registry_type == 'family', HouseholdMembership.user_id == user.id).all()
        result.append({'user_id': person.id, 'name': person.name,
            'mutual': FamilyFollow.query.filter_by(follower_id=person.id, followed_id=user.id).first() is not None,
            'shared_households': [{'id': home.id, 'name': home.name} for home in homes]})
    return jsonify(connections=result)


@api.post('/family-connections/<int:other_id>/share')
@authenticated
@limiter.limit('20 per hour')
def share_back_with_connection(other_id):
    user = request.current_user
    if not FamilyFollow.query.filter_by(follower_id=user.id, followed_id=other_id).first():
        return error('Family connection not found.', 404)
    other = db.session.get(User, other_id)
    if not other or other.is_child or other.is_support:
        return error('Family connection not found.', 404)
    payload = request.get_json(silent=True) or {}
    home_id, profile_ids = payload.get('household_id'), payload.get('profile_ids')
    member = membership_for(user, home_id) if type(home_id) is int else None
    home = db.session.get(Household, home_id) if member else None
    if not home or home.registry_type != 'family' or member.role not in ('owner','admin'):
        return error('Choose a family household you manage.',403)
    share_all = payload.get('share_all_profiles',False)
    if type(share_all) is not bool:
        return error('Choose valid sharing.',400)
    if share_all:
        profile_ids = [row.profile_id for row in HouseholdProfileAccess.query.filter_by(household_id=home.id).all()]
    if not isinstance(profile_ids,list) or (not profile_ids and not share_all) or any(type(pid) is not int for pid in profile_ids):
        return error('Select the family lists to share back.',400)
    allowed = {row.profile_id for row in HouseholdProfileAccess.query.filter_by(household_id=home.id).all()}
    if not set(profile_ids) <= allowed:
        return error('One or more profiles are not in this family.',400)
    membership = membership_for(other,home.id)
    if not membership:
        membership=HouseholdMembership(household_id=home.id,user_id=other.id,role='shopper')
        db.session.add(membership);db.session.flush()
    if share_all:
        membership.share_all_profiles = True
    for pid in set(profile_ids):
        if not HouseholdMemberProfileAccess.query.filter_by(membership_id=membership.id,profile_id=pid).first():
            db.session.add(HouseholdMemberProfileAccess(membership_id=membership.id,profile_id=pid,can_edit=False))
    record_audit(user.id,'family_connection.shared_back','household',home.id,home.id,{'profile_ids':profile_ids})
    db.session.commit()
    return jsonify(message='Family wishlists shared. Private and family-only gifts stay protected.')


def child_mode_siblings():
    child = request.current_user
    parent_id = session.get('household_return_user_id')
    parent = db.session.get(User, parent_id) if parent_id else None
    if not child.is_child or not parent or child.parent_user_id != parent.id or parent.session_version != session.get('household_return_version'):
        return []
    from ..child_controls import controls_for
    if not controls_for(child)['switch_siblings']:
        return [child]
    return User.query.filter_by(parent_user_id=parent.id, is_child=True, child_enabled=True).all()


@api.get('/child/profiles')
@authenticated
def child_profiles():
    rows = child_mode_siblings()
    profiles = {row.id: PersonProfile.query.filter_by(account_user_id=row.id).first() for row in rows}
    return jsonify(profiles=[{'id': row.id, 'name': row.name, 'active': row.id == request.current_user.id, 'avatar_key': profiles[row.id].avatar_key if profiles[row.id] else 'flower', 'photo_path': '/api/child/profiles/'+str(row.id)+'/photo' if profiles[row.id] and profiles[row.id].photo_path else None} for row in rows])


@api.post('/child/profiles/switch')
@authenticated
def switch_child_profile():
    target_id = (request.get_json(silent=True) or {}).get('child_id')
    target = next((row for row in child_mode_siblings() if type(target_id) is int and row.id == target_id), None)
    if not target:
        return error('Child profile not available.', 403)
    parent_id, version = session['household_return_user_id'], session['household_return_version']
    session.clear()
    session.update({'user_id': target.id, 'auth_version': target.session_version, 'auth_mode': 'child',
        'household_return_user_id': parent_id, 'household_return_version': version})
    current_app.session_interface.regenerate(session)
    return jsonify(status='child', csrf_token=_csrf_token())


def selected_shared_theme(user):
    key = user.theme_key or ''
    row = db.session.get(SharedTheme, int(key[1:])) if key.startswith('t') and key[1:].isdigit() else None
    return {'key': key, **row.data} if row else None


@api.get('/themes')
@authenticated
def theme_catalog():
    rows = SharedTheme.query.order_by(SharedTheme.id.desc()).all()
    return jsonify(themes=[{'key': 't' + str(row.id), **row.data} for row in rows if row.data.get('purpose','app')=='app' and row.data.get('active',True) and (not request.current_user.is_child or row.data['audience'] in ('kids', 'everyone'))])


@api.post('/support/themes')
@authenticated
def create_shared_theme():
    if not request.current_user.is_superuser or not request.current_user.is_support:
        return error('Master developer account required.', 403)
    payload = request.form
    name = payload.get('name', '').strip()
    audience = payload.get('audience', 'everyone')
    colors = {key: payload.get(key, '') for key in ('background', 'foreground', 'accent')}
    if not name or len(name) > 80 or audience not in ('adults', 'kids', 'everyone') or any(not re.fullmatch(r'#[0-9a-fA-F]{6}', color) for color in colors.values()):
        return error('Enter a name, audience and valid colors.', 400)
    from ..letter_art import theme_metadata
    try:
        metadata=theme_metadata(payload)
    except ValueError as exc:
        return error(str(exc),400)
    image = None
    if request.files.get('image'):
        image, failure = save_profile_image(request.files['image'], request.current_user.id)
        if failure:
            return error(failure, 400)
    row = SharedTheme(data={**metadata, 'name': name, 'season': payload.get('season', '')[:80], 'audience': audience, **colors})
    db.session.add(row); db.session.flush()
    row.data = {**row.data, 'art': '/api/themes/' + str(row.id) + '/art' if image else None, 'image_path': image}
    db.session.commit()
    return jsonify(theme={'key': 't' + str(row.id), **row.data}), 201


@api.get('/themes/<int:theme_id>/art')
@authenticated
def theme_art(theme_id):
    row = db.session.get(SharedTheme, theme_id)
    if not row or not row.data.get('image_path') or (request.current_user.is_child and row.data['audience'] == 'adults'):
        return error('Theme artwork not found.', 404)
    response = send_from_directory(current_app.config['UPLOAD_FOLDER'], row.data['image_path'].rsplit('/', 1)[-1])
    response.headers['Cache-Control'] = 'private, max-age=86400'
    return response


@api.get('/families/<int:user_id>/public-wishes')
@authenticated
def family_public_wishes(user_id):
    person = User.query.filter_by(id=user_id, is_child=False, is_support=False).first()
    if person is None:
        return error('Family not found.', 404)
    rows = PersonalWish.query.filter_by(owner_id=user_id, visibility='public').order_by(PersonalWish.id.desc()).limit(100).all()
    return jsonify(wishes=[{'id': w.id, 'name': w.item.name, 'image': w.item.image_path,
        'occasion': w.occasion, 'store_name': w.item.store_name} for w in rows])


@api.post('/families/name-search')
@authenticated
@limiter.limit('15 per minute')
def search_adult_families():
    query = (request.get_json(silent=True) or {}).get('query', '')
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 120:
        return error('Enter at least two letters of an adult name.', 400)
    words = query.strip().lower().split()
    adult_homes = db.session.query(HouseholdProfileAccess.household_id).join(PersonProfile,
        PersonProfile.id == HouseholdProfileAccess.profile_id).filter(PersonProfile.is_adult.is_(True),
        *[func.lower(PersonProfile.display_name).contains(word, autoescape=True) for word in words])
    rows = db.session.query(Household, User).join(User, Household.owner_id == User.id).filter(
        Household.registry_type == 'family', User.is_child.is_(False), User.is_support.is_(False),
        User.id != request.current_user.id,
        or_(db.and_(*[func.lower(User.name).contains(word, autoescape=True) for word in words]),
            db.and_(*[func.lower(Household.name).contains(word, autoescape=True) for word in words]),
            Household.id.in_(adult_homes))
    ).order_by(Household.name).limit(20).all()
    session['invite_lookup_homes'] = [home.id for home, _ in rows]
    return jsonify(matches=[{'user_id': user.id, 'name': home.name,
        'photo': '/api/families/lookup-photo/' + str(home.id) if home.photo_path else None} for home, user in rows])


@api.post('/families/lookup')
@authenticated
@limiter.limit('15 per minute')
def lookup_invite_family():
    email = normalized_email((request.get_json(silent=True) or {}).get('email'))
    if not email:
        return error('Enter a complete email address.', 400)
    person = User.query.filter(db.func.lower(User.email) == email.lower(), User.is_child.is_(False), User.is_support.is_(False)).first()
    home = Household.query.filter_by(owner_id=person.id, registry_type='family').order_by(Household.id).first() if person else None
    session['invite_lookup_home'] = home.id if home else None
    return jsonify(match={'user_id': person.id, 'name': home.name if home else person.name, 'photo': '/api/families/lookup-photo/' + str(home.id) if home and home.photo_path else None} if person else None)


@api.get('/families/lookup-photo/<int:home_id>')
@authenticated
def invite_lookup_photo(home_id):
    if session.get('invite_lookup_home') != home_id and home_id not in session.get('invite_lookup_homes', []):
        return error('Photo not available.', 404)
    home = db.session.get(Household, home_id)
    if not home or not home.photo_path:
        return error('Photo not available.', 404)
    response = send_from_directory(current_app.config['UPLOAD_FOLDER'], Path(home.photo_path).name)
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def pending_co_buy_notifications(user):
    invitations = CoBuyInvitation.query.filter_by(email=user.email, accepted=False, declined=False).all()
    return [{'id': 'co-buy-'+str(i.id), 'co_buy_invitation_id': i.id,
        'message': db.session.get(User, i.reservation.shopper_id).name + ' invited you to co-buy ' + i.reservation.item.name + ' (' + str(i.share_percent) + '%)',
        'household_name': '', 'read': False, 'created_at': i.reservation.created_at.isoformat(), 'url': '/gifting'}
        for i in invitations if i.reservation.status == 'reserved' and shopper_can_see(i.reservation.item, user)]


def pending_follow_notifications(user):
    invites = HouseholdInvitation.query.filter(db.func.lower(HouseholdInvitation.email) == user.email.lower(), HouseholdInvitation.accepted_at.is_(None), HouseholdInvitation.declined_at.is_(None), HouseholdInvitation.expires_at > datetime.now(timezone.utc)).all()
    return [{'id': 'invite-' + str(row.id), 'invitation_id': row.id, 'join_family': row.linked_profile_id is not None, 'household_name': db.session.get(Household, row.household_id).name, 'family_photo': ('/api/invitations/' + str(row.id) + '/photo' if db.session.get(Household, row.household_id).photo_path else None),
        'message': 'You received a family follow request. Accept to connect and see the shared lists.', 'read': False,
        'created_at': row.created_at.isoformat(), 'url': '/following'} for row in invites]


@api.get('/invitations/<int:invitation_id>/photo')
@authenticated
def invitation_family_photo(invitation_id):
    invitation = HouseholdInvitation.query.filter(HouseholdInvitation.id == invitation_id,
        db.func.lower(HouseholdInvitation.email) == request.current_user.email.lower(),
        HouseholdInvitation.accepted_at.is_(None), HouseholdInvitation.declined_at.is_(None),
        HouseholdInvitation.expires_at > datetime.now(timezone.utc)).first()
    if invitation is None:
        return error('Image not found.', 404)
    household = db.session.get(Household, invitation.household_id)
    if not household or not household.photo_path:
        return error('Image not found.', 404)
    response = send_from_directory(current_app.config['UPLOAD_FOLDER'], Path(household.photo_path).name)
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@api.get('/invitations')
@authenticated
def invitation_inbox():
    user = request.current_user
    managed = db.session.query(HouseholdMembership.household_id).filter(HouseholdMembership.user_id == user.id, HouseholdMembership.role.in_(('owner', 'admin')))
    rows = HouseholdInvitation.query.filter(db.or_(HouseholdInvitation.household_id.in_(managed), db.func.lower(HouseholdInvitation.email) == user.email.lower())).order_by(HouseholdInvitation.created_at.desc()).all()
    now = datetime.now(timezone.utc)
    def summary(row):
        recipient = User.query.filter(db.func.lower(User.email) == row.email.lower(), User.is_child.is_(False), User.is_support.is_(False)).first()
        return {'id': row.id, 'family': db.session.get(Household, row.household_id).name, 'email': row.email, 'recipient_name': recipient.name if recipient else None,
            'status': 'declined' if row.declined_at else 'accepted' if row.accepted_at else 'expired' if row.expires_at.replace(tzinfo=timezone.utc) <= now else 'pending', 'created_at': row.created_at.isoformat()}
    managed_ids = {row[0] for row in managed.all()}
    return jsonify(sent=[summary(row) for row in rows if row.household_id in managed_ids], received=[summary(row) for row in rows if row.email.lower() == user.email.lower()])


@api.post('/invitations/<int:invitation_id>/decline')
@authenticated
def decline_family_invitation(invitation_id):
    row = HouseholdInvitation.query.filter(HouseholdInvitation.id == invitation_id, db.func.lower(HouseholdInvitation.email) == request.current_user.email.lower()).with_for_update().first()
    if not row:
        return error('Invitation not found.', 404)
    if row.accepted_at:
        return error('This invitation was already accepted.', 409)
    row.declined_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(status='declined')



def visible_personal_candidates(user):
    from ..adult_family import followed_ids
    following = list(followed_ids(user))
    explicit = db.session.query(PersonalWishViewer.wish_id).filter_by(user_id=user.id)
    return PersonalWish.query.filter(db.or_(PersonalWish.id.in_(explicit),PersonalWish.visibility.in_(('public','family')),
        db.and_(PersonalWish.visibility=='followers',PersonalWish.owner_id.in_(following))))


@api.get('/public-wishes')
@authenticated
def public_wish_catalog():
    rows = PersonalWish.query.filter_by(visibility='public').order_by(PersonalWish.id.desc()).limit(100).all()
    return jsonify(wishes=[personal_wish_dict(row,request.current_user) for row in rows])


@api.get('/public/wishes')
def public_wish_preview():
    rows = PersonalWish.query.filter_by(visibility='public').order_by(PersonalWish.id.desc()).limit(100).all()
    return jsonify(wishes=[{'name':row.item.name,'image_url':row.item.image_path,'occasion':row.occasion,
        'product_url':shopping_link(row.item.product_url),'recipient':db.session.get(User,row.owner_id).name} for row in rows])


@api.delete('/wishlists/<int:list_id>')
@authenticated
def delete_wishlist(list_id):
    row = Wishlist.query.filter_by(id=list_id).with_for_update().first()
    if not row or profile_access(request.current_user, row.profile_id, write=True) is None:
        return error('Wishlist not found or edit permission denied.', 404)
    from ..models import WishlistLetter
    links = WishlistItemWishlist.query.filter_by(wishlist_id=row.id).all()
    for link in links:
        item = db.session.get(WishlistItem, link.item_id)
        elsewhere = WishlistItemWishlist.query.filter(
            WishlistItemWishlist.item_id == link.item_id, WishlistItemWishlist.wishlist_id != row.id).first()
        if item and item.profile_id == row.profile_id and not elsewhere:
            SavedGift.query.filter_by(item_id=item.id).delete()
            reservation_ids = db.session.query(GiftReservation.id).filter_by(item_id=item.id)
            CoBuyInvitation.query.filter(CoBuyInvitation.reservation_id.in_(reservation_ids)).delete(synchronize_session=False)
            db.session.delete(item)
        else:
            db.session.delete(link)
    affected = [access.user_id for access in ChildWishlistAccess.query.filter_by(wishlist_id=row.id).all()]
    ChildWishlistAccess.query.filter_by(wishlist_id=row.id).delete()
    for child_id in affected:
        child = db.session.get(User, child_id)
        parent = db.session.get(User, child.parent_user_id) if child and child.is_child else None
        if parent:
            preferences = dict(parent.notification_preferences or {})
            access = dict(preferences.get('child_access', {}))
            access[str(child.id)] = {**access.get(str(child.id), {}), 'lists_configured': True}
            parent.notification_preferences = {**preferences, 'child_access': access}
            child.session_version += 1
    WishlistLetter.query.filter_by(wishlist_id=row.id).delete()
    db.session.delete(row)
    db.session.commit()
    return jsonify(status='deleted')


@api.patch('/wishlists/<int:list_id>')
@authenticated
def rename_wishlist(list_id):
    row = db.session.get(Wishlist,list_id)
    if not row or not profile_access(request.current_user,row.profile_id,write=True):
        return error('Wishlist not found or edit permission denied.',404)
    payload = request.get_json(silent=True) or {}
    if 'share_publicly' in payload:
        if not isinstance(payload['share_publicly'], bool):
            return error('List sharing must be true or false.', 400)
        row.share_publicly = payload['share_publicly']
    title = payload.get('title', row.title)
    if not isinstance(title,str) or not title.strip() or len(title.strip())>160:
        return error('Enter a list name within 160 characters.',400)
    row.title = title.strip()
    if payload.get('share_publicly') is False:
        items = WishlistItem.query.join(WishlistItemWishlist).filter(
            WishlistItemWishlist.wishlist_id == row.id, WishlistItem.profile_id == row.profile_id).all()
        for item in items:
            for hold in GiftReservation.query.filter_by(item_id=item.id, status='reserved').all():
                shopper = db.session.get(User, hold.shopper_id)
                if not shopper or not item_audience_allowed(item, shopper):
                    hold.status = 'cancelled'
    db.session.commit()
    return jsonify(wishlist={'id':row.id,'title':row.title,'share_publicly':row.share_publicly})


@api.get('/child/game-notifications')
@authenticated
def child_game_notifications():
    if not request.current_user.is_child:
        return error('Child account required.', 403)
    from ..models import GiftExchangeGame
    profiles = {p.id for p in PersonProfile.query.filter_by(account_user_id=request.current_user.id).all()}
    rows = GiftExchangeGame.query.order_by(GiftExchangeGame.id.desc()).all()
    return jsonify(notifications=[{'id': g.id, 'message': 'You are invited to ' + g.title + '. Ask your parent about joining.', 'read': request.current_user.id in g.state.get('child_notification_read', [])} for g in rows if g.status not in ('cancelled', 'completed') and profiles.intersection(g.state['participants'])])


@api.post('/child/game-notifications/<int:game_id>/read')
@authenticated
def child_game_notification_read(game_id):
    if not request.current_user.is_child:
        return error('Child account required.', 403)
    from ..models import GiftExchangeGame
    game = GiftExchangeGame.query.filter_by(id=game_id).with_for_update().first()
    profiles = {p.id for p in PersonProfile.query.filter_by(account_user_id=request.current_user.id).all()}
    if not game or not profiles.intersection(game.state['participants']):
        return error('Notification not found.', 404)
    game.state = {**game.state, 'child_notification_read': sorted(set(game.state.get('child_notification_read', []) + [request.current_user.id]))}
    db.session.commit()
    return jsonify(status='read')


@api.post('/co-buy-invitations/<int:invitation_id>/decline')
@authenticated
def decline_co_buy(invitation_id):
    invite = CoBuyInvitation.query.filter_by(id=invitation_id, email=request.current_user.email).first()
    if not invite or invite.reservation.status != 'reserved':
        return error('Invitation not found.', 404)
    invite.accepted = False
    invite.declined = True
    db.session.commit()
    return jsonify(status='declined')


@api.route('/wishlists/<int:list_id>/delivery', methods=['GET', 'PATCH'])
@authenticated
def list_delivery(list_id):
    wishlist = db.session.get(Wishlist, list_id)
    if not wishlist or not profile_access(request.current_user, wishlist.profile_id):
        return error('Wishlist not found.', 404)
    if not list_is_shared(wishlist) and not list_family_access(wishlist, request.current_user):
        return error('Wishlist not found.', 404)
    editable = can_manage_wishes(request.current_user, db.session.get(PersonProfile, wishlist.profile_id))
    if request.method == 'PATCH':
        if not editable:
            return error('Only the list manager can change its delivery address.', 403)
        payload = request.get_json()
        address = payload.get('address', '')
        shared = payload.get('shared', False)
        if not isinstance(address, str) or len(address) > 1000 or type(shared) is not bool:
            return error('Enter an address up to 1,000 characters and choose its sharing setting.', 400)
        if shared and not address.strip():
            return error('Enter an address before sharing it.', 400)
        wishlist.delivery_address = address.strip() or None
        wishlist.share_delivery_address = shared
        db.session.commit()
    response = jsonify(address=wishlist.delivery_address if editable or wishlist.share_delivery_address else None, shared=wishlist.share_delivery_address, can_edit=editable)
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@api.get('/items/<int:item_id>/delivery')
@authenticated
def item_delivery(item_id):
    item = db.session.get(WishlistItem, item_id)
    if not item or not shopper_can_see(item, request.current_user):
        return error('Gift not found.', 404)
    lists = Wishlist.query.join(WishlistItemWishlist).filter(WishlistItemWishlist.item_id==item.id, Wishlist.profile_id==item.profile_id, Wishlist.share_delivery_address.is_(True)).all()
    response = jsonify(addresses=[{'list': w.title, 'address': w.delivery_address} for w in lists if w.delivery_address and (list_is_shared(w) or list_family_access(w, request.current_user))])
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@api.get('/avatars')
@authenticated
def avatar_catalog():
    from ..models import SharedAvatar
    return jsonify(avatars=[{'key':'a'+str(a.id), 'name':a.name, 'image':'/api/avatars/'+str(a.id)+'/art'} for a in SharedAvatar.query.order_by(SharedAvatar.id.desc()).all()])


@api.post('/support/avatars')
@authenticated
def publish_avatar():
    if not request.current_user.is_support or not request.current_user.is_superuser:
        return error('Master developer account required.', 403)
    from ..models import SharedAvatar
    name = request.form.get('name', '').strip()
    if not name or len(name)>80 or not request.files.get('image'):
        return error('Enter a cartoon name and image.', 400)
    image, failure = save_profile_image(request.files['image'], request.current_user.id)
    if failure:
        return error(failure, 400)
    row=SharedAvatar(name=name,image_path=image)
    db.session.add(row);db.session.commit()
    return jsonify(avatar={'key':'a'+str(row.id), 'name':row.name, 'image':'/api/avatars/'+str(row.id)+'/art'}),201


@api.get('/avatars/<int:avatar_id>/art')
@authenticated
def avatar_art(avatar_id):
    from ..models import SharedAvatar
    row=db.session.get(SharedAvatar,avatar_id)
    if not row:
        return error('Cartoon not found.',404)
    response=send_from_directory(current_app.config['UPLOAD_FOLDER'], row.image_path.rsplit('/',1)[-1])
    response.headers['Cache-Control']='private, max-age=86400'
    return response


@api.get('/child/profiles/<int:child_id>/photo')
@authenticated
def child_profile_photo(child_id):
    if child_id not in {c.id for c in child_mode_siblings()}:
        return error('Photo not found.',404)
    profile = PersonProfile.query.filter_by(account_user_id=child_id).first()
    if not profile or not profile.photo_path:
        return error('Photo not found.',404)
    response=send_from_directory(current_app.config['UPLOAD_FOLDER'], profile.photo_path.rsplit('/',1)[-1])
    response.headers['Cache-Control']='private, no-store'
    return response


@api.delete('/households/<int:household_id>/profiles/<int:profile_id>/member')
@authenticated
def remove_linked_family_profile(household_id, profile_id):
    home = db.session.get(Household, household_id)
    if not home or home.owner_id != request.current_user.id:
        return error('Only the family creator can remove a family member.',403)
    profile = PersonProfile.query.filter_by(id=profile_id).with_for_update().first()
    access = HouseholdProfileAccess.query.filter_by(household_id=household_id,profile_id=profile_id).first()
    account = db.session.get(User, profile.account_user_id) if profile and profile.account_user_id else None
    if not access or (account and account.id == request.current_user.id):
        return error('Choose another family member or pet.',400)
    if not account or account.is_child or not profile.is_adult:
        HouseholdInvitation.query.filter_by(household_id=household_id, linked_profile_id=profile_id).delete()
        member_ids = db.session.query(HouseholdMembership.id).filter_by(household_id=household_id)
        HouseholdMemberProfileAccess.query.filter(HouseholdMemberProfileAccess.membership_id.in_(member_ids), HouseholdMemberProfileAccess.profile_id==profile_id).delete(synchronize_session=False)
        db.session.delete(access)
        db.session.commit()
        return jsonify(status='removed')
    membership = membership_for(account, household_id)
    if not membership or not membership.is_family_member:
        return error('Linked family member not found.',404)
    HouseholdInvitation.query.filter_by(household_id=household_id,linked_profile_id=profile_id).delete()
    member_ids = db.session.query(HouseholdMembership.id).filter_by(household_id=household_id)
    HouseholdMemberProfileAccess.query.filter(HouseholdMemberProfileAccess.membership_id.in_(member_ids),HouseholdMemberProfileAccess.profile_id==profile_id).delete(synchronize_session=False)
    db.session.delete(access);db.session.flush()
    other = PersonProfile.query.join(HouseholdProfileAccess).filter(HouseholdProfileAccess.household_id==household_id,PersonProfile.account_user_id==account.id).first()
    if not other:
        HouseholdMemberProfileAccess.query.filter_by(membership_id=membership.id).delete()
        db.session.delete(membership)
    record_audit(request.current_user.id,'family.member_removed','person_profile',profile_id,household_id)
    db.session.commit()
    from ..adult_family import sync_family_connections
    sync_family_connections(account)
    return jsonify(status='removed')


@api.route('/wishlist-budget-preferences', methods=['GET', 'PATCH'])
@authenticated
def wishlist_budget_preferences():
    user = request.current_user
    if request.method == 'PATCH':
        payload = request.get_json(silent=True) or {}
        if set(payload) != {'enabled'} or type(payload['enabled']) is not bool:
            return error('Choose whether to show wishlist price suggestions.', 400)
        user.notification_preferences = {**(user.notification_preferences or {}), 'wishlist_budget_suggestions': payload['enabled']}
        db.session.commit()
    return jsonify(enabled=(user.notification_preferences or {}).get('wishlist_budget_suggestions', True))
