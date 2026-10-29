from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.dialects.mysql import MEDIUMBLOB

from ..extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class AppSession(db.Model):
    __tablename__ = 'app_session'
    key_hash = db.Column(db.String(64), primary_key=True)
    data = db.Column(db.LargeBinary().with_variant(MEDIUMBLOB(), 'mysql'), nullable=False)
    expires_at = db.Column(db.BigInteger, nullable=False, index=True)


class RequestLimit(db.Model):
    __tablename__ = 'request_limit'
    key_hash = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.BigInteger, nullable=False)
    expires_at = db.Column(db.BigInteger, nullable=False, index=True)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    notification_preferences = db.Column(db.JSON, nullable=True)
    parent_pin_hash = db.Column(db.String(255))
    theme_key = db.Column(db.String(20), nullable=False, default="classic", server_default="classic")
    theme_image_path = db.Column(db.String(500))
    session_version = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    is_child = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    child_username = db.Column(db.String(80), unique=True)
    parent_user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    child_enabled = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    is_support = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    is_superuser = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    memberships = db.relationship("HouseholdMembership", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def public_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": None if self.is_child else self.email,
            "is_child": self.is_child,
            "is_support": self.is_support,
            "is_superuser": self.is_superuser,
            "wishlist_budget_suggestions": (self.notification_preferences or {}).get("wishlist_budget_suggestions", True),
        }


class Household(db.Model):
    registry_type = db.Column(db.String(20), nullable=False, default="family", server_default="family")
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    access_code_hash = db.Column(db.String(255))
    photo_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    memberships = db.relationship("HouseholdMembership", back_populates="household", cascade="all, delete-orphan")
    profile_access = db.relationship("HouseholdProfileAccess", back_populates="household", cascade="all, delete-orphan")

    def public_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
            "registry_type": self.registry_type,
            "photo_path": self.photo_path,
        }


class HouseholdMembership(db.Model):
    is_family_member = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    inherited_from_household_id = db.Column(db.Integer, nullable=True)
    share_all_profiles = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("household.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="viewer")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        db.UniqueConstraint("household_id", "user_id"),
        db.CheckConstraint("role IN ('owner','admin','profile_manager','editor','shopper','viewer')", name="membership_role"),
    )
    household = db.relationship("Household", back_populates="memberships")
    user = db.relationship("User", back_populates="memberships")


class HouseholdInvitation(db.Model):
    linked_profile_id = db.Column(db.Integer, db.ForeignKey("person_profile.id", ondelete="CASCADE"), nullable=True)
    transfer_owner_on_accept = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    setup_created_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    share_all_profiles = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("household.id", ondelete="CASCADE"), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False, unique=True)
    role = db.Column(db.String(30), nullable=False, default="viewer")
    profile_ids = db.Column(db.JSON, nullable=False, default=list)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    declined_at = db.Column(db.DateTime(timezone=True))
    accepted_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class EmailSuppression(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    source = db.Column(db.String(30), nullable=False, default='recipient')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class SupportInvitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    invited_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    accepted_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    invited_by = db.relationship("User")


class PersonProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), index=True)
    is_adult = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    is_guardian = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    member_email = db.Column(db.String(255))
    display_name = db.Column(db.String(120), nullable=False)
    profile_type = db.Column(db.String(20), nullable=False, default="person")
    share_wishlist = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    birthday = db.Column(db.Date)
    birthday_shared = db.Column(db.Boolean, nullable=False, default=False)
    photo_path = db.Column(db.String(500))
    avatar_key = db.Column(db.String(30), nullable=False, default="flower")
    favorite_colors = db.Column(db.JSON)
    favorite_brands = db.Column(db.JSON)
    favorite_stores = db.Column(db.JSON)
    favorite_characters = db.Column(db.JSON)
    hobbies = db.Column(db.JSON)
    interests = db.Column(db.JSON)
    clothing_sizes = db.Column(db.JSON)
    shoe_sizes = db.Column(db.JSON)
    gift_preferences = db.Column(db.Text)
    parent_notes = db.Column(db.Text)
    favorite_snacks = db.Column(db.JSON)
    allergies = db.Column(db.Text)
    items_to_avoid = db.Column(db.Text)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    household_access = db.relationship("HouseholdProfileAccess", back_populates="profile", cascade="all, delete-orphan")

    def public_dict(self):
        return {
            "id": self.id,
            "display_name": self.display_name,
            "profile_type": self.profile_type,
            "share_wishlist": self.share_wishlist,
            "birthday": self.birthday.strftime("%m-%d") if self.birthday else None,
            "birthday_shared": self.birthday_shared,
            "photo_path": self.photo_path,
            "avatar_key": self.avatar_key,
            "favorite_colors": self.favorite_colors or [],
            "favorite_brands": self.favorite_brands or [],
            "favorite_stores": self.favorite_stores or [],
            "favorite_characters": self.favorite_characters or [],
            "hobbies": self.hobbies or [],
            "interests": self.interests or [],
            "clothing_sizes": self.clothing_sizes or {},
            "shoe_sizes": self.shoe_sizes or {},
            "gift_preferences": self.gift_preferences,
            "parent_notes": self.parent_notes,
            "items_to_avoid": self.items_to_avoid,
            "allergies": self.allergies,
            "favorite_snacks": self.favorite_snacks or [],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class HouseholdProfileAccess(db.Model):
    relationship = db.Column(db.String(30), nullable=False, default="family_member", server_default="family_member")
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("household.id", ondelete="CASCADE"), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey("person_profile.id", ondelete="CASCADE"), nullable=False)
    can_edit = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (db.UniqueConstraint("household_id", "profile_id"),)
    household = db.relationship("Household", back_populates="profile_access")
    profile = db.relationship("PersonProfile", back_populates="household_access")


class HouseholdMemberProfileAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    membership_id = db.Column(db.Integer, db.ForeignKey("household_membership.id", ondelete="CASCADE"), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey("person_profile.id", ondelete="CASCADE"), nullable=False)
    can_edit = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (db.UniqueConstraint("membership_id", "profile_id"),)
    membership = db.relationship("HouseholdMembership")


class Occasion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("person_profile.id", ondelete="CASCADE"), index=True)
    name = db.Column(db.String(160), nullable=False)
    occasion_type = db.Column(db.String(30), nullable=False, default="other")
    event_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    profile = db.relationship("PersonProfile")


class Wishlist(db.Model):
    share_publicly = db.Column(db.Boolean, nullable=True)
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("person_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    occasion_id = db.Column(db.Integer, db.ForeignKey("occasion.id", ondelete="SET NULL"), index=True)
    delivery_address = db.Column(db.Text)
    share_delivery_address = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    title = db.Column(db.String(160), nullable=False)
    is_everyday = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("person_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    family_only = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(500))
    store_name = db.Column(db.String(120))
    product_url = db.Column(db.String(2000))
    estimated_price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(3), nullable=False, default="USD")
    desired_size = db.Column(db.String(80))
    desired_color = db.Column(db.String(80))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    category = db.Column(db.String(100))
    notes = db.Column(db.Text)
    priority = db.Column(db.Integer, nullable=False, default=2)
    request_type = db.Column(db.String(30), nullable=False, default="want")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    profile = db.relationship("PersonProfile")
    wishlists = db.relationship("WishlistItemWishlist", back_populates="item", cascade="all, delete-orphan")
    occasions = db.relationship("WishlistItemOccasion", back_populates="item", cascade="all, delete-orphan")
    reservations = db.relationship("GiftReservation", back_populates="item", cascade="all, delete-orphan")
    __table_args__ = (
        db.CheckConstraint("quantity >= 1", name="item_quantity_positive"),
        db.CheckConstraint("priority BETWEEN 1 AND 4", name="item_priority_range"),
        db.CheckConstraint("request_type IN ('want','need','parent_recommendation')", name="item_request_type"),
    )


class WishlistItemOccasion(db.Model):
    occasion = db.relationship("Occasion")
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("wishlist_item.id", ondelete="CASCADE"), nullable=False)
    occasion_id = db.Column(db.Integer, db.ForeignKey("occasion.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (db.UniqueConstraint("item_id", "occasion_id"),)
    item = db.relationship("WishlistItem", back_populates="occasions")


class WishlistItemWishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("wishlist_item.id", ondelete="CASCADE"), nullable=False)
    wishlist_id = db.Column(db.Integer, db.ForeignKey("wishlist.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (db.UniqueConstraint("item_id", "wishlist_id"),)
    item = db.relationship("WishlistItem", back_populates="wishlists")


class GiftReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("wishlist_item.id", ondelete="CASCADE"), nullable=False, index=True)
    shopper_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="reserved")
    purchase_secret = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    delivery_method = db.Column(db.String(20), nullable=False, default="undecided", server_default="undecided")
    private_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    item = db.relationship("WishlistItem", back_populates="reservations")
    __table_args__ = (
        db.CheckConstraint("quantity >= 1", name="reservation_quantity_positive"),
        db.CheckConstraint("status IN ('reserved','purchased','cancelled')", name="reservation_status"),
        db.Index("ix_reservation_item_status", "item_id", "status"),
    )


class CoBuyInvitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("gift_reservation.id", ondelete="CASCADE"), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    share_percent = db.Column(db.Numeric(5, 2), nullable=False, default=50, server_default="50")
    declined = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    accepted = db.Column(db.Boolean, nullable=False, default=False)
    reservation = db.relationship("GiftReservation")
    __table_args__ = (db.UniqueConstraint("reservation_id", "email"),)


class ShoppingBudget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    household_id = db.Column(db.Integer, db.ForeignKey("household.id", ondelete="CASCADE"), index=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("person_profile.id", ondelete="CASCADE"), index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    __table_args__ = (
        db.CheckConstraint("amount >= 0", name="budget_amount_nonnegative"),
        db.UniqueConstraint("user_id", "household_id", "profile_id"),
    )


class SupportAccessRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True)
    support_user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    decided_at = db.Column(db.DateTime(timezone=True))
    decided_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    household = db.relationship("Household")
    support_user = db.relationship("User", foreign_keys=[support_user_id])
    grant = db.relationship("SupportAccessGrant", back_populates="request", uselist=False)
    __table_args__ = (
        db.CheckConstraint("status IN ('pending','approved','denied','cancelled')", name="support_request_status"),
        db.Index("ix_support_request_household_status", "household_id", "status"),
    )


class SupportAccessGrant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("support_access_request.id", ondelete="CASCADE"), nullable=False, unique=True)
    household_id = db.Column(db.Integer, db.ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True)
    support_user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    approved_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True))
    request = db.relationship("SupportAccessRequest", back_populates="grant")
    household = db.relationship("Household")


class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, default="bug")
    status = db.Column(db.String(20), nullable=False, default="open")
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    user = db.relationship("User", foreign_keys=[user_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    messages = db.relationship("SupportTicketMessage", back_populates="ticket", cascade="all, delete-orphan")
    __table_args__ = (
        db.CheckConstraint("category IN ('bug','feedback','help')", name="support_ticket_category"),
        db.CheckConstraint("status IN ('open','in_progress','resolved','closed')", name="support_ticket_status"),
    )


class SupportTicketMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("support_ticket.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    ticket = db.relationship("SupportTicket", back_populates="messages")
    author = db.relationship("User")


class HelpChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = db.Column(db.String(10), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    user = db.relationship("User")
    __table_args__ = (
        db.CheckConstraint("sender IN ('user','bot')", name="help_chat_sender"),
    )


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), index=True)
    household_id = db.Column(db.Integer, db.ForeignKey("household.id", ondelete="SET NULL"), index=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(80))
    details = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    household_id = db.Column(db.Integer, db.ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("wishlist_item.id", ondelete="CASCADE"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    read_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    user = db.relationship("User")
    household = db.relationship("Household")
    item = db.relationship("WishlistItem")

class SavedGift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('wishlist_item.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    item = db.relationship('WishlistItem')
    __table_args__ = (db.UniqueConstraint('user_id', 'item_id'),)


class PrivateGift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    recipient = db.Column(db.String(120), nullable=False)
    household_name = db.Column(db.String(160))
    occasion = db.Column(db.String(160))
    store_name = db.Column(db.String(120))
    product_url = db.Column(db.String(2000))
    image_url = db.Column(db.String(2000))
    estimated_price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(3), nullable=False, default='USD')
    status = db.Column(db.String(20), nullable=False, default='planned')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (db.CheckConstraint("status IN ('planned','purchased')", name='private_gift_status'),)


class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))
    password_version = db.Column(db.Integer, nullable=False)


class ChildWishlistAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlist.id', ondelete='CASCADE'), nullable=False, index=True)
    __table_args__ = (db.UniqueConstraint('user_id', 'wishlist_id'),)

class PersonalWish(db.Model):
    visibility = db.Column(db.String(20), nullable=False, default="custom", server_default="custom")
    occasion = db.Column(db.String(80), nullable=False, default="", server_default="")
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('wishlist_item.id', ondelete='CASCADE'), nullable=False, unique=True)
    item = db.relationship('WishlistItem')
    viewers = db.relationship('PersonalWishViewer', cascade='all, delete-orphan', back_populates='wish')


class PersonalWishViewer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wish_id = db.Column(db.Integer, db.ForeignKey('personal_wish.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    wish = db.relationship('PersonalWish', back_populates='viewers')
    __table_args__ = (db.UniqueConstraint('wish_id', 'user_id'),)


class AccountEmailCode(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    pending_data = db.Column(db.JSON)
    purpose = db.Column(db.String(30), nullable=False)
    target_email = db.Column(db.String(255))
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))
    attempts = db.Column(db.Integer, nullable=False, default=0)
    session_version = db.Column(db.Integer, nullable=False)


class AdCampaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    data = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='pending_review')
    amount_cents = db.Column(db.Integer, nullable=False, default=0)
    stripe_session_id = db.Column(db.String(255), unique=True)
    payment_intent = db.Column(db.String(255))
    paid = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class GiftExchangeGame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('household.id', ondelete='CASCADE'), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    kind = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    budget = db.Column(db.Numeric(10,2))
    event_date = db.Column(db.Date)
    status = db.Column(db.String(30), nullable=False, default='waiting')
    state = db.Column(db.JSON, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class FamilyFollow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (db.UniqueConstraint('follower_id','followed_id'),)

class SharedTheme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.JSON, nullable=False)


class GiftAvailabilityAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('wishlist_item.id', ondelete='CASCADE'), nullable=False, index=True)
    ready = db.Column(db.Boolean, nullable=False, default=False)
    read_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    item = db.relationship('WishlistItem')
    __table_args__ = (db.UniqueConstraint('user_id', 'item_id'),)


class GiftSuggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('person_profile.id', ondelete='CASCADE'), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class SharedAvatar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)


class AdvertisingRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    business_name = db.Column(db.String(160), nullable=False, default='')
    message = db.Column(db.Text, nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('ad_campaign.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='new', index=True)
    email_delivery = db.Column(db.String(30), nullable=False, default='pending')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_at = db.Column(db.DateTime(timezone=True))


class WishlistLetter(db.Model):
    theme_id = db.Column(db.Integer, db.ForeignKey('shared_theme.id', ondelete='SET NULL'), nullable=True)
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('household.id', ondelete='CASCADE'), nullable=False, index=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('person_profile.id', ondelete='CASCADE'), nullable=False, index=True)
    wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlist.id', ondelete='CASCADE'), nullable=False, unique=True)
    sender_name = db.Column(db.String(120), nullable=False)
    send_on = db.Column(db.Date, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)


class LetterArtPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('household.id', ondelete='CASCADE'), nullable=False, index=True)
    theme_id = db.Column(db.Integer, db.ForeignKey('shared_theme.id', ondelete='CASCADE'), nullable=False, index=True)
    buyer_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    art_name = db.Column(db.String(80), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='usd')
    stripe_session_id = db.Column(db.String(255), unique=True)
    checkout_url = db.Column(db.String(2000))
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    payment_intent = db.Column(db.String(255), index=True)
    paid = db.Column(db.Boolean, nullable=False, default=False)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class EmailTemplateDesign(db.Model):
    template_id = db.Column(db.String(60), primary_key=True)
    blocks = db.Column(db.JSON, nullable=False)
