-- Full MySQL schema for a fresh database, generated from the Alembic history.
-- Run as a MySQL administrator. This creates the app database and local app user.
-- Apply only to a fresh database; this records the current Alembic revision.
CREATE DATABASE IF NOT EXISTS family_gifts
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

CREATE USER IF NOT EXISTS 'gift_registry'@'127.0.0.1'
  IDENTIFIED BY 'gift_registry_dev';
ALTER USER 'gift_registry'@'127.0.0.1'
  IDENTIFIED BY 'gift_registry_dev';
GRANT ALL PRIVILEGES ON family_gifts.* TO 'gift_registry'@'127.0.0.1';

CREATE USER IF NOT EXISTS 'gift_registry'@'localhost'
  IDENTIFIED BY 'gift_registry_dev';
ALTER USER 'gift_registry'@'localhost'
  IDENTIFIED BY 'gift_registry_dev';
GRANT ALL PRIVILEGES ON family_gifts.* TO 'gift_registry'@'localhost';

USE family_gifts;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> d4d99e38bedb

CREATE TABLE user (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    name VARCHAR(120) NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_user PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_user_email ON user (email);

CREATE TABLE household (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    name VARCHAR(160) NOT NULL, 
    owner_id INTEGER NOT NULL, 
    access_code_hash VARCHAR(255), 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_household PRIMARY KEY (id), 
    CONSTRAINT fk_household_owner_id_user FOREIGN KEY(owner_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE person_profile (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    account_user_id INTEGER, 
    display_name VARCHAR(120) NOT NULL, 
    birthday DATE, 
    birthday_shared BOOL NOT NULL, 
    photo_path VARCHAR(500), 
    favorite_colors JSON, 
    favorite_brands JSON, 
    favorite_characters JSON, 
    hobbies JSON, 
    interests JSON, 
    clothing_sizes JSON, 
    shoe_sizes JSON, 
    gift_preferences TEXT, 
    parent_notes TEXT, 
    items_to_avoid TEXT, 
    updated_at DATETIME NOT NULL, 
    CONSTRAINT pk_person_profile PRIMARY KEY (id), 
    CONSTRAINT fk_person_profile_account_user_id_user FOREIGN KEY(account_user_id) REFERENCES user (id) ON DELETE SET NULL
);

CREATE INDEX ix_person_profile_account_user_id ON person_profile (account_user_id);

CREATE TABLE household_invitation (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    household_id INTEGER NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    token_hash VARCHAR(255) NOT NULL, 
    `role` VARCHAR(30) NOT NULL, 
    expires_at DATETIME NOT NULL, 
    accepted_at DATETIME, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_household_invitation PRIMARY KEY (id), 
    CONSTRAINT fk_household_invitation_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT uq_household_invitation_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_household_invitation_email ON household_invitation (email);

CREATE TABLE household_membership (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    household_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    `role` VARCHAR(30) NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_household_membership PRIMARY KEY (id), 
    CONSTRAINT ck_household_membership_membership_role CHECK (role IN ('owner','admin','profile_manager','editor','shopper','viewer')), 
    CONSTRAINT fk_household_membership_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_household_membership_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT uq_household_membership_household_id UNIQUE (household_id, user_id)
);

CREATE TABLE household_profile_access (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    household_id INTEGER NOT NULL, 
    profile_id INTEGER NOT NULL, 
    can_edit BOOL NOT NULL, 
    CONSTRAINT pk_household_profile_access PRIMARY KEY (id), 
    CONSTRAINT fk_household_profile_access_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_household_profile_access_profile_id_person_profile FOREIGN KEY(profile_id) REFERENCES person_profile (id) ON DELETE CASCADE, 
    CONSTRAINT uq_household_profile_access_household_id UNIQUE (household_id, profile_id)
);

CREATE TABLE occasion (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    household_id INTEGER NOT NULL, 
    profile_id INTEGER, 
    name VARCHAR(160) NOT NULL, 
    occasion_type VARCHAR(30) NOT NULL, 
    event_date DATE NOT NULL, 
    description TEXT, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_occasion PRIMARY KEY (id), 
    CONSTRAINT fk_occasion_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_occasion_profile_id_person_profile FOREIGN KEY(profile_id) REFERENCES person_profile (id) ON DELETE CASCADE
);

CREATE INDEX ix_occasion_household_id ON occasion (household_id);

CREATE INDEX ix_occasion_profile_id ON occasion (profile_id);

CREATE TABLE shopping_budget (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    household_id INTEGER, 
    profile_id INTEGER, 
    amount NUMERIC(10, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    CONSTRAINT pk_shopping_budget PRIMARY KEY (id), 
    CONSTRAINT ck_shopping_budget_budget_amount_nonnegative CHECK (amount >= 0), 
    CONSTRAINT fk_shopping_budget_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_shopping_budget_profile_id_person_profile FOREIGN KEY(profile_id) REFERENCES person_profile (id) ON DELETE CASCADE, 
    CONSTRAINT fk_shopping_budget_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT uq_shopping_budget_user_id UNIQUE (user_id, household_id, profile_id)
);

CREATE INDEX ix_shopping_budget_household_id ON shopping_budget (household_id);

CREATE INDEX ix_shopping_budget_profile_id ON shopping_budget (profile_id);

CREATE INDEX ix_shopping_budget_user_id ON shopping_budget (user_id);

CREATE TABLE wishlist_item (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    profile_id INTEGER NOT NULL, 
    created_by_id INTEGER, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    image_path VARCHAR(500), 
    store_name VARCHAR(120), 
    product_url VARCHAR(2000), 
    estimated_price NUMERIC(10, 2), 
    currency VARCHAR(3) NOT NULL, 
    desired_size VARCHAR(80), 
    desired_color VARCHAR(80), 
    quantity INTEGER NOT NULL, 
    category VARCHAR(100), 
    notes TEXT, 
    priority INTEGER NOT NULL, 
    request_type VARCHAR(30) NOT NULL, 
    created_at DATETIME NOT NULL, 
    updated_at DATETIME NOT NULL, 
    CONSTRAINT pk_wishlist_item PRIMARY KEY (id), 
    CONSTRAINT ck_wishlist_item_item_request_type CHECK (request_type IN ('want','need','parent_recommendation')), 
    CONSTRAINT ck_wishlist_item_item_priority_range CHECK (priority BETWEEN 1 AND 4), 
    CONSTRAINT ck_wishlist_item_item_quantity_positive CHECK (quantity >= 1), 
    CONSTRAINT fk_wishlist_item_created_by_id_user FOREIGN KEY(created_by_id) REFERENCES user (id) ON DELETE SET NULL, 
    CONSTRAINT fk_wishlist_item_profile_id_person_profile FOREIGN KEY(profile_id) REFERENCES person_profile (id) ON DELETE CASCADE
);

CREATE INDEX ix_wishlist_item_profile_id ON wishlist_item (profile_id);

CREATE TABLE gift_reservation (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    item_id INTEGER NOT NULL, 
    shopper_id INTEGER NOT NULL, 
    quantity INTEGER NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    private_note TEXT, 
    created_at DATETIME NOT NULL, 
    updated_at DATETIME NOT NULL, 
    CONSTRAINT pk_gift_reservation PRIMARY KEY (id), 
    CONSTRAINT ck_gift_reservation_reservation_status CHECK (status IN ('reserved','purchased','cancelled')), 
    CONSTRAINT ck_gift_reservation_reservation_quantity_positive CHECK (quantity >= 1), 
    CONSTRAINT fk_gift_reservation_item_id_wishlist_item FOREIGN KEY(item_id) REFERENCES wishlist_item (id) ON DELETE CASCADE, 
    CONSTRAINT fk_gift_reservation_shopper_id_user FOREIGN KEY(shopper_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX ix_gift_reservation_item_id ON gift_reservation (item_id);

CREATE INDEX ix_gift_reservation_shopper_id ON gift_reservation (shopper_id);

CREATE INDEX ix_reservation_item_status ON gift_reservation (item_id, status);

CREATE TABLE wishlist (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    profile_id INTEGER NOT NULL, 
    occasion_id INTEGER, 
    title VARCHAR(160) NOT NULL, 
    is_everyday BOOL NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_wishlist PRIMARY KEY (id), 
    CONSTRAINT fk_wishlist_occasion_id_occasion FOREIGN KEY(occasion_id) REFERENCES occasion (id) ON DELETE SET NULL, 
    CONSTRAINT fk_wishlist_profile_id_person_profile FOREIGN KEY(profile_id) REFERENCES person_profile (id) ON DELETE CASCADE
);

CREATE INDEX ix_wishlist_occasion_id ON wishlist (occasion_id);

CREATE INDEX ix_wishlist_profile_id ON wishlist (profile_id);

CREATE TABLE wishlist_item_occasion (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    item_id INTEGER NOT NULL, 
    occasion_id INTEGER NOT NULL, 
    CONSTRAINT pk_wishlist_item_occasion PRIMARY KEY (id), 
    CONSTRAINT fk_wishlist_item_occasion_item_id_wishlist_item FOREIGN KEY(item_id) REFERENCES wishlist_item (id) ON DELETE CASCADE, 
    CONSTRAINT fk_wishlist_item_occasion_occasion_id_occasion FOREIGN KEY(occasion_id) REFERENCES occasion (id) ON DELETE CASCADE, 
    CONSTRAINT uq_wishlist_item_occasion_item_id UNIQUE (item_id, occasion_id)
);

INSERT INTO alembic_version (version_num) VALUES ('d4d99e38bedb');

-- Running upgrade d4d99e38bedb -> 52726a957525

CREATE TABLE wishlist_item_wishlist (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    item_id INTEGER NOT NULL, 
    wishlist_id INTEGER NOT NULL, 
    CONSTRAINT pk_wishlist_item_wishlist PRIMARY KEY (id), 
    CONSTRAINT fk_wishlist_item_wishlist_item_id_wishlist_item FOREIGN KEY(item_id) REFERENCES wishlist_item (id) ON DELETE CASCADE, 
    CONSTRAINT fk_wishlist_item_wishlist_wishlist_id_wishlist FOREIGN KEY(wishlist_id) REFERENCES wishlist (id) ON DELETE CASCADE, 
    CONSTRAINT uq_wishlist_item_wishlist_item_id UNIQUE (item_id, wishlist_id)
);

UPDATE alembic_version SET version_num='52726a957525' WHERE alembic_version.version_num = 'd4d99e38bedb';

-- Running upgrade 52726a957525 -> 3b3939b1bffb

CREATE TABLE support_ticket (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    subject VARCHAR(180) NOT NULL, 
    description TEXT NOT NULL, 
    category VARCHAR(30) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    created_at DATETIME NOT NULL, 
    updated_at DATETIME NOT NULL, 
    CONSTRAINT pk_support_ticket PRIMARY KEY (id), 
    CONSTRAINT ck_support_ticket_support_ticket_category CHECK (category IN ('bug','feedback','help')), 
    CONSTRAINT ck_support_ticket_support_ticket_status CHECK (status IN ('open','in_progress','resolved','closed')), 
    CONSTRAINT fk_support_ticket_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX ix_support_ticket_user_id ON support_ticket (user_id);

CREATE TABLE audit_log (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    actor_id INTEGER, 
    household_id INTEGER, 
    action VARCHAR(100) NOT NULL, 
    entity_type VARCHAR(80) NOT NULL, 
    entity_id VARCHAR(80), 
    details JSON NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_audit_log PRIMARY KEY (id), 
    CONSTRAINT fk_audit_log_actor_id_user FOREIGN KEY(actor_id) REFERENCES user (id) ON DELETE SET NULL, 
    CONSTRAINT fk_audit_log_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_log_actor_id ON audit_log (actor_id);

CREATE INDEX ix_audit_log_created_at ON audit_log (created_at);

CREATE INDEX ix_audit_log_household_id ON audit_log (household_id);

CREATE TABLE support_access_request (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    household_id INTEGER NOT NULL, 
    support_user_id INTEGER NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    reason TEXT NOT NULL, 
    created_at DATETIME NOT NULL, 
    decided_at DATETIME, 
    decided_by_id INTEGER, 
    CONSTRAINT pk_support_access_request PRIMARY KEY (id), 
    CONSTRAINT ck_support_access_request_support_request_status CHECK (status IN ('pending','approved','denied','cancelled')), 
    CONSTRAINT fk_support_access_request_decided_by_id_user FOREIGN KEY(decided_by_id) REFERENCES user (id) ON DELETE SET NULL, 
    CONSTRAINT fk_support_access_request_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_support_access_request_support_user_id_user FOREIGN KEY(support_user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX ix_support_access_request_household_id ON support_access_request (household_id);

CREATE INDEX ix_support_access_request_support_user_id ON support_access_request (support_user_id);

CREATE INDEX ix_support_request_household_status ON support_access_request (household_id, status);

CREATE TABLE support_ticket_message (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    ticket_id INTEGER NOT NULL, 
    author_id INTEGER NOT NULL, 
    message TEXT NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_support_ticket_message PRIMARY KEY (id), 
    CONSTRAINT fk_support_ticket_message_author_id_user FOREIGN KEY(author_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT fk_support_ticket_message_ticket_id_support_ticket FOREIGN KEY(ticket_id) REFERENCES support_ticket (id) ON DELETE CASCADE
);

CREATE INDEX ix_support_ticket_message_ticket_id ON support_ticket_message (ticket_id);

CREATE TABLE support_access_grant (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    request_id INTEGER NOT NULL, 
    household_id INTEGER NOT NULL, 
    support_user_id INTEGER NOT NULL, 
    approved_by_id INTEGER, 
    approved_at DATETIME NOT NULL, 
    expires_at DATETIME NOT NULL, 
    revoked_at DATETIME, 
    CONSTRAINT pk_support_access_grant PRIMARY KEY (id), 
    CONSTRAINT fk_support_access_grant_approved_by_id_user FOREIGN KEY(approved_by_id) REFERENCES user (id) ON DELETE SET NULL, 
    CONSTRAINT fk_support_access_grant_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_support_access_grant_request_id_support_access_request FOREIGN KEY(request_id) REFERENCES support_access_request (id) ON DELETE CASCADE, 
    CONSTRAINT fk_support_access_grant_support_user_id_user FOREIGN KEY(support_user_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT uq_support_access_grant_request_id UNIQUE (request_id)
);

CREATE INDEX ix_support_access_grant_expires_at ON support_access_grant (expires_at);

CREATE INDEX ix_support_access_grant_household_id ON support_access_grant (household_id);

CREATE INDEX ix_support_access_grant_support_user_id ON support_access_grant (support_user_id);

ALTER TABLE household_invitation ADD COLUMN profile_ids JSON;

UPDATE household_invitation SET profile_ids = '[]' WHERE profile_ids IS NULL;

ALTER TABLE household_invitation MODIFY profile_ids JSON NOT NULL;

ALTER TABLE user ADD COLUMN is_support BOOL NOT NULL DEFAULT '0';

UPDATE alembic_version SET version_num='3b3939b1bffb' WHERE alembic_version.version_num = '52726a957525';

-- Running upgrade 3b3939b1bffb -> b2a1fa57d7f7

CREATE TABLE household_member_profile_access (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    membership_id INTEGER NOT NULL, 
    profile_id INTEGER NOT NULL, 
    can_edit BOOL NOT NULL, 
    CONSTRAINT pk_household_member_profile_access PRIMARY KEY (id), 
    CONSTRAINT fk_household_member_profile_access_membership_id_househo_e494 FOREIGN KEY(membership_id) REFERENCES household_membership (id) ON DELETE CASCADE, 
    CONSTRAINT fk_household_member_profile_access_profile_id_person_profile FOREIGN KEY(profile_id) REFERENCES person_profile (id) ON DELETE CASCADE, 
    CONSTRAINT uq_household_member_profile_access_membership_id UNIQUE (membership_id, profile_id)
);

UPDATE alembic_version SET version_num='b2a1fa57d7f7' WHERE alembic_version.version_num = '3b3939b1bffb';

-- Running upgrade b2a1fa57d7f7 -> a981c5d42e10

ALTER TABLE user ADD COLUMN is_superuser BOOL NOT NULL DEFAULT false;

CREATE TABLE support_invitation (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    email VARCHAR(255) NOT NULL, 
    token_hash VARCHAR(64) NOT NULL, 
    invited_by_id INTEGER NOT NULL, 
    expires_at DATETIME NOT NULL, 
    accepted_at DATETIME, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_support_invitation PRIMARY KEY (id), 
    CONSTRAINT fk_support_invitation_invited_by_id_user FOREIGN KEY(invited_by_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT uq_support_invitation_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_support_invitation_email ON support_invitation (email);

CREATE INDEX ix_support_invitation_expires_at ON support_invitation (expires_at);

CREATE INDEX ix_support_invitation_invited_by_id ON support_invitation (invited_by_id);

UPDATE alembic_version SET version_num='a981c5d42e10' WHERE alembic_version.version_num = 'b2a1fa57d7f7';

-- Running upgrade a981c5d42e10 -> 78c0d1e94a62

ALTER TABLE household ADD COLUMN photo_path VARCHAR(500);

ALTER TABLE person_profile ADD COLUMN profile_type VARCHAR(20) NOT NULL DEFAULT 'person';

ALTER TABLE person_profile ADD COLUMN avatar_key VARCHAR(30) NOT NULL DEFAULT 'flower';

CREATE TABLE notification (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    household_id INTEGER NOT NULL, 
    item_id INTEGER NOT NULL, 
    message VARCHAR(255) NOT NULL, 
    read_at DATETIME, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_notification PRIMARY KEY (id), 
    CONSTRAINT fk_notification_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT fk_notification_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_notification_item_id_wishlist_item FOREIGN KEY(item_id) REFERENCES wishlist_item (id) ON DELETE CASCADE
);

CREATE INDEX ix_notification_user_id ON notification (user_id);

CREATE INDEX ix_notification_household_id ON notification (household_id);

CREATE INDEX ix_notification_created_at ON notification (created_at);

UPDATE alembic_version SET version_num='78c0d1e94a62' WHERE alembic_version.version_num = 'a981c5d42e10';

-- Running upgrade 78c0d1e94a62 -> 0b7f21a4d9ce

ALTER TABLE person_profile ADD COLUMN favorite_stores JSON;

UPDATE alembic_version SET version_num='0b7f21a4d9ce' WHERE alembic_version.version_num = '78c0d1e94a62';

-- Running upgrade 0b7f21a4d9ce -> c921b46a830f

CREATE TABLE co_buy_invitation (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    reservation_id INTEGER NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    accepted BOOL NOT NULL, 
    CONSTRAINT pk_co_buy_invitation PRIMARY KEY (id), 
    CONSTRAINT uq_co_buy_invitation_reservation_id UNIQUE (reservation_id, email), 
    CONSTRAINT fk_co_buy_invitation_reservation_id_gift_reservation FOREIGN KEY(reservation_id) REFERENCES gift_reservation (id) ON DELETE CASCADE
);

CREATE INDEX ix_co_buy_invitation_reservation_id ON co_buy_invitation (reservation_id);

UPDATE alembic_version SET version_num='c921b46a830f' WHERE alembic_version.version_num = '0b7f21a4d9ce';

-- Running upgrade c921b46a830f -> e2c51480a7d6

ALTER TABLE household_profile_access ADD COLUMN relationship VARCHAR(30) NOT NULL DEFAULT 'family_member';

UPDATE alembic_version SET version_num='e2c51480a7d6' WHERE alembic_version.version_num = 'c921b46a830f';

-- Running upgrade e2c51480a7d6 -> f72d09c1ab84

CREATE TABLE saved_gift (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    item_id INTEGER NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_saved_gift PRIMARY KEY (id), 
    CONSTRAINT uq_saved_gift_user_id UNIQUE (user_id, item_id), 
    CONSTRAINT fk_saved_gift_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT fk_saved_gift_item_id_wishlist_item FOREIGN KEY(item_id) REFERENCES wishlist_item (id) ON DELETE CASCADE
);

CREATE INDEX ix_saved_gift_user_id ON saved_gift (user_id);

CREATE INDEX ix_saved_gift_item_id ON saved_gift (item_id);

CREATE TABLE private_gift (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    recipient VARCHAR(120) NOT NULL, 
    household_name VARCHAR(160), 
    occasion VARCHAR(160), 
    store_name VARCHAR(120), 
    product_url VARCHAR(2000), 
    image_url VARCHAR(2000), 
    estimated_price NUMERIC(10, 2), 
    currency VARCHAR(3) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_private_gift PRIMARY KEY (id), 
    CONSTRAINT ck_private_gift_private_gift_status CHECK (status IN ('planned','purchased')), 
    CONSTRAINT fk_private_gift_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX ix_private_gift_user_id ON private_gift (user_id);

UPDATE alembic_version SET version_num='f72d09c1ab84' WHERE alembic_version.version_num = 'e2c51480a7d6';

-- Running upgrade f72d09c1ab84 -> a48cd9217b03

ALTER TABLE user ADD COLUMN session_version INTEGER NOT NULL DEFAULT '0';

CREATE TABLE password_reset (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    token_hash VARCHAR(64) NOT NULL, 
    expires_at DATETIME NOT NULL, 
    used_at DATETIME, 
    password_version INTEGER NOT NULL, 
    CONSTRAINT pk_password_reset PRIMARY KEY (id), 
    CONSTRAINT fk_password_reset_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT uq_password_reset_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_password_reset_user_id ON password_reset (user_id);

UPDATE alembic_version SET version_num='a48cd9217b03' WHERE alembic_version.version_num = 'f72d09c1ab84';

-- Running upgrade a48cd9217b03 -> b59de0328c14

ALTER TABLE user ADD COLUMN is_child BOOL NOT NULL DEFAULT '0';

ALTER TABLE user ADD COLUMN child_username VARCHAR(80);

ALTER TABLE user ADD COLUMN parent_user_id INTEGER;

ALTER TABLE user ADD COLUMN child_enabled BOOL NOT NULL DEFAULT '1';

ALTER TABLE user ADD CONSTRAINT uq_user_child_username UNIQUE (child_username);

ALTER TABLE user ADD CONSTRAINT fk_user_parent_user_id_user FOREIGN KEY(parent_user_id) REFERENCES user (id) ON DELETE CASCADE;

CREATE TABLE child_wishlist_access (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    wishlist_id INTEGER NOT NULL, 
    CONSTRAINT pk_child_wishlist_access PRIMARY KEY (id), 
    CONSTRAINT uq_child_wishlist_access_user_id UNIQUE (user_id, wishlist_id), 
    CONSTRAINT fk_child_wishlist_access_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT fk_child_wishlist_access_wishlist_id_wishlist FOREIGN KEY(wishlist_id) REFERENCES wishlist (id) ON DELETE CASCADE
);

CREATE INDEX ix_child_wishlist_access_user_id ON child_wishlist_access (user_id);

CREATE INDEX ix_child_wishlist_access_wishlist_id ON child_wishlist_access (wishlist_id);

UPDATE alembic_version SET version_num='b59de0328c14' WHERE alembic_version.version_num = 'a48cd9217b03';

-- Running upgrade b59de0328c14 -> c60ef1439d25

ALTER TABLE user ADD COLUMN theme_key VARCHAR(20) NOT NULL DEFAULT 'classic';

ALTER TABLE user ADD COLUMN theme_image_path VARCHAR(500);

UPDATE alembic_version SET version_num='c60ef1439d25' WHERE alembic_version.version_num = 'b59de0328c14';

-- Running upgrade c60ef1439d25 -> d71fa254ae36

ALTER TABLE household ADD COLUMN registry_type VARCHAR(20) NOT NULL DEFAULT 'family';

UPDATE alembic_version SET version_num='d71fa254ae36' WHERE alembic_version.version_num = 'c60ef1439d25';

-- Running upgrade d71fa254ae36 -> e82ab365bf47

CREATE TABLE personal_wish (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    owner_id INTEGER NOT NULL, 
    item_id INTEGER NOT NULL, 
    CONSTRAINT pk_personal_wish PRIMARY KEY (id), 
    CONSTRAINT fk_personal_wish_owner_id_user FOREIGN KEY(owner_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT uq_personal_wish_item_id UNIQUE (item_id), 
    CONSTRAINT fk_personal_wish_item_id_wishlist_item FOREIGN KEY(item_id) REFERENCES wishlist_item (id) ON DELETE CASCADE
);

CREATE INDEX ix_personal_wish_owner_id ON personal_wish (owner_id);

CREATE TABLE personal_wish_viewer (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    wish_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    CONSTRAINT pk_personal_wish_viewer PRIMARY KEY (id), 
    CONSTRAINT uq_personal_wish_viewer_wish_id UNIQUE (wish_id, user_id), 
    CONSTRAINT fk_personal_wish_viewer_wish_id_personal_wish FOREIGN KEY(wish_id) REFERENCES personal_wish (id) ON DELETE CASCADE, 
    CONSTRAINT fk_personal_wish_viewer_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX ix_personal_wish_viewer_wish_id ON personal_wish_viewer (wish_id);

CREATE INDEX ix_personal_wish_viewer_user_id ON personal_wish_viewer (user_id);

UPDATE alembic_version SET version_num='e82ab365bf47' WHERE alembic_version.version_num = 'd71fa254ae36';

-- Running upgrade e82ab365bf47 -> f93bc476ca58

ALTER TABLE wishlist_item ADD COLUMN family_only BOOL NOT NULL DEFAULT false;

UPDATE alembic_version SET version_num='f93bc476ca58' WHERE alembic_version.version_num = 'e82ab365bf47';

-- Running upgrade f93bc476ca58 -> a04cd587db69

ALTER TABLE user ADD COLUMN parent_pin_hash VARCHAR(255);

ALTER TABLE person_profile ADD COLUMN is_adult BOOL NOT NULL DEFAULT false;

ALTER TABLE person_profile ADD COLUMN is_guardian BOOL NOT NULL DEFAULT false;

ALTER TABLE person_profile ADD COLUMN member_email VARCHAR(255);

UPDATE alembic_version SET version_num='a04cd587db69' WHERE alembic_version.version_num = 'f93bc476ca58';

-- Running upgrade a04cd587db69 -> b15de698ec70

CREATE TABLE account_email_code (
    id VARCHAR(64) NOT NULL, 
    user_id INTEGER NOT NULL, 
    purpose VARCHAR(30) NOT NULL, 
    target_email VARCHAR(255), 
    code_hash VARCHAR(255) NOT NULL, 
    expires_at DATETIME NOT NULL, 
    used_at DATETIME, 
    attempts INTEGER NOT NULL, 
    session_version INTEGER NOT NULL, 
    CONSTRAINT pk_account_email_code PRIMARY KEY (id), 
    CONSTRAINT fk_account_email_code_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX ix_account_email_code_user_id ON account_email_code (user_id);

UPDATE alembic_version SET version_num='b15de698ec70' WHERE alembic_version.version_num = 'a04cd587db69';

-- Running upgrade b15de698ec70 -> c26ef709fd81

CREATE TABLE ad_campaign (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    token_hash VARCHAR(64) NOT NULL, 
    data JSON NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    amount_cents INTEGER NOT NULL, 
    stripe_session_id VARCHAR(255), 
    payment_intent VARCHAR(255), 
    paid BOOL NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_ad_campaign PRIMARY KEY (id), 
    CONSTRAINT uq_ad_campaign_token_hash UNIQUE (token_hash), 
    CONSTRAINT uq_ad_campaign_stripe_session_id UNIQUE (stripe_session_id)
);

UPDATE alembic_version SET version_num='c26ef709fd81' WHERE alembic_version.version_num = 'b15de698ec70';

-- Running upgrade c26ef709fd81 -> d370081a0e92

ALTER TABLE account_email_code ADD COLUMN pending_data JSON;

UPDATE alembic_version SET version_num='d370081a0e92' WHERE alembic_version.version_num = 'c26ef709fd81';

-- Running upgrade d370081a0e92 -> e481192b1fa3

CREATE TABLE gift_exchange_game (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    household_id INTEGER NOT NULL, 
    created_by_id INTEGER, 
    kind VARCHAR(30) NOT NULL, 
    title VARCHAR(160) NOT NULL, 
    budget NUMERIC(10, 2), 
    event_date DATE, 
    status VARCHAR(30) NOT NULL, 
    state JSON NOT NULL, 
    version INTEGER NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_gift_exchange_game PRIMARY KEY (id), 
    CONSTRAINT fk_gift_exchange_game_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_gift_exchange_game_created_by_id_user FOREIGN KEY(created_by_id) REFERENCES user (id) ON DELETE SET NULL
);

CREATE INDEX ix_gift_exchange_game_household_id ON gift_exchange_game (household_id);

UPDATE alembic_version SET version_num='e481192b1fa3' WHERE alembic_version.version_num = 'd370081a0e92';

-- Running upgrade e481192b1fa3 -> f5922a3c20b4

CREATE TABLE family_follow (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    follower_id INTEGER NOT NULL, 
    followed_id INTEGER NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_family_follow PRIMARY KEY (id), 
    CONSTRAINT uq_family_follow_follower_id UNIQUE (follower_id, followed_id), 
    CONSTRAINT fk_family_follow_follower_id_user FOREIGN KEY(follower_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT fk_family_follow_followed_id_user FOREIGN KEY(followed_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX ix_family_follow_follower_id ON family_follow (follower_id);

CREATE INDEX ix_family_follow_followed_id ON family_follow (followed_id);

UPDATE alembic_version SET version_num='f5922a3c20b4' WHERE alembic_version.version_num = 'e481192b1fa3';

-- Running upgrade f5922a3c20b4 -> a6033b4d31c5

CREATE TABLE shared_theme (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    data JSON NOT NULL, 
    CONSTRAINT pk_shared_theme PRIMARY KEY (id)
);

UPDATE alembic_version SET version_num='a6033b4d31c5' WHERE alembic_version.version_num = 'f5922a3c20b4';

-- Running upgrade a6033b4d31c5 -> b7144c5e42d6

ALTER TABLE personal_wish ADD COLUMN occasion VARCHAR(80) NOT NULL DEFAULT '';

UPDATE alembic_version SET version_num='b7144c5e42d6' WHERE alembic_version.version_num = 'a6033b4d31c5';

-- Running upgrade b7144c5e42d6 -> c8255d6f53e7

ALTER TABLE household_invitation ADD COLUMN declined_at DATETIME;

UPDATE alembic_version SET version_num='c8255d6f53e7' WHERE alembic_version.version_num = 'b7144c5e42d6';

-- Running upgrade c8255d6f53e7 -> d9366e7064f8

ALTER TABLE personal_wish ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'custom';

UPDATE alembic_version SET version_num='d9366e7064f8' WHERE alembic_version.version_num = 'c8255d6f53e7';

-- Running upgrade d9366e7064f8 -> ea477f817509

ALTER TABLE household_membership ADD COLUMN share_all_profiles BOOL NOT NULL DEFAULT false;

ALTER TABLE household_invitation ADD COLUMN share_all_profiles BOOL NOT NULL DEFAULT false;

UPDATE alembic_version SET version_num='ea477f817509' WHERE alembic_version.version_num = 'd9366e7064f8';

-- Running upgrade ea477f817509 -> fb5880928610

ALTER TABLE user ADD COLUMN notification_preferences JSON;

UPDATE alembic_version SET version_num='fb5880928610' WHERE alembic_version.version_num = 'ea477f817509';

-- Running upgrade fb5880928610 -> ac6991a39721

CREATE TABLE gift_availability_alert (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    item_id INTEGER NOT NULL, 
    ready BOOL NOT NULL, 
    read_at DATETIME, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_gift_availability_alert PRIMARY KEY (id), 
    CONSTRAINT uq_gift_availability_alert_user_id UNIQUE (user_id, item_id), 
    CONSTRAINT fk_gift_availability_alert_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT fk_gift_availability_alert_item_id_wishlist_item FOREIGN KEY(item_id) REFERENCES wishlist_item (id) ON DELETE CASCADE
);

CREATE INDEX ix_gift_availability_alert_user_id ON gift_availability_alert (user_id);

CREATE INDEX ix_gift_availability_alert_item_id ON gift_availability_alert (item_id);

UPDATE alembic_version SET version_num='ac6991a39721' WHERE alembic_version.version_num = 'fb5880928610';

-- Running upgrade ac6991a39721 -> bd70a2b4a832

ALTER TABLE household_membership ADD COLUMN is_family_member BOOL NOT NULL DEFAULT false;

ALTER TABLE household_membership ADD COLUMN inherited_from_household_id INTEGER;

ALTER TABLE household_invitation ADD COLUMN linked_profile_id INTEGER;

ALTER TABLE household_invitation ADD CONSTRAINT fk_invitation_linked_profile FOREIGN KEY(linked_profile_id) REFERENCES person_profile (id) ON DELETE CASCADE;

CREATE TABLE gift_suggestion (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    sender_id INTEGER NOT NULL, 
    recipient_id INTEGER NOT NULL, 
    profile_id INTEGER NOT NULL, 
    data JSON NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_gift_suggestion PRIMARY KEY (id), 
    CONSTRAINT fk_gift_suggestion_sender_id_user FOREIGN KEY(sender_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT fk_gift_suggestion_recipient_id_user FOREIGN KEY(recipient_id) REFERENCES user (id) ON DELETE CASCADE, 
    CONSTRAINT fk_gift_suggestion_profile_id_person_profile FOREIGN KEY(profile_id) REFERENCES person_profile (id) ON DELETE CASCADE
);

CREATE INDEX ix_gift_suggestion_recipient_id ON gift_suggestion (recipient_id);

UPDATE alembic_version SET version_num='bd70a2b4a832' WHERE alembic_version.version_num = 'ac6991a39721';

-- Running upgrade bd70a2b4a832 -> ce81b3c5b943

ALTER TABLE gift_reservation ADD COLUMN purchase_secret BOOL NOT NULL DEFAULT true;

UPDATE alembic_version SET version_num='ce81b3c5b943' WHERE alembic_version.version_num = 'bd70a2b4a832';

-- Running upgrade ce81b3c5b943 -> df92c4d6ca54

ALTER TABLE co_buy_invitation ADD COLUMN share_percent NUMERIC(5, 2) NOT NULL DEFAULT '50';

ALTER TABLE co_buy_invitation ADD COLUMN declined BOOL NOT NULL DEFAULT false;

UPDATE alembic_version SET version_num='df92c4d6ca54' WHERE alembic_version.version_num = 'ce81b3c5b943';

-- Running upgrade df92c4d6ca54 -> ea03d5e7db65

ALTER TABLE wishlist ADD COLUMN delivery_address TEXT;

ALTER TABLE wishlist ADD COLUMN share_delivery_address BOOL NOT NULL DEFAULT false;

ALTER TABLE gift_reservation ADD COLUMN delivery_method VARCHAR(20) NOT NULL DEFAULT 'undecided';

UPDATE alembic_version SET version_num='ea03d5e7db65' WHERE alembic_version.version_num = 'df92c4d6ca54';

-- Running upgrade ea03d5e7db65 -> fb14e6f8ec76

CREATE TABLE shared_avatar (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    name VARCHAR(80) NOT NULL, 
    image_path VARCHAR(500) NOT NULL, 
    CONSTRAINT pk_shared_avatar PRIMARY KEY (id)
);

UPDATE alembic_version SET version_num='fb14e6f8ec76' WHERE alembic_version.version_num = 'ea03d5e7db65';

-- Running upgrade fb14e6f8ec76 -> c13a60234a91

ALTER TABLE person_profile ADD COLUMN share_wishlist BOOL NOT NULL DEFAULT false;

UPDATE alembic_version SET version_num='c13a60234a91' WHERE alembic_version.version_num = 'fb14e6f8ec76';

-- Running upgrade c13a60234a91 -> 7fe12c6a9d34

ALTER TABLE household_invitation ADD COLUMN transfer_owner_on_accept BOOL NOT NULL DEFAULT false;

ALTER TABLE household_invitation ADD COLUMN setup_created_by_id INTEGER;

CREATE INDEX ix_household_invitation_setup_created_by_id ON household_invitation (setup_created_by_id);

ALTER TABLE household_invitation ADD CONSTRAINT fk_household_invitation_setup_created_by_id_user FOREIGN KEY(setup_created_by_id) REFERENCES user (id) ON DELETE SET NULL;

UPDATE alembic_version SET version_num='7fe12c6a9d34' WHERE alembic_version.version_num = 'c13a60234a91';

-- Running upgrade 7fe12c6a9d34 -> d71e82a940cb

ALTER TABLE wishlist ADD COLUMN share_publicly BOOL;

UPDATE alembic_version SET version_num='d71e82a940cb' WHERE alembic_version.version_num = '7fe12c6a9d34';

-- Running upgrade d71e82a940cb -> e82c4b9510fa

ALTER TABLE person_profile ADD COLUMN allergies TEXT;

ALTER TABLE person_profile ADD COLUMN favorite_snacks JSON;

UPDATE alembic_version SET version_num='e82c4b9510fa' WHERE alembic_version.version_num = 'd71e82a940cb';

-- Running upgrade e82c4b9510fa -> a7c3e91d5b20

CREATE TABLE help_chat_message (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    sender VARCHAR(10) NOT NULL, 
    message TEXT NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_help_chat_message PRIMARY KEY (id), 
    CONSTRAINT ck_help_chat_message_ck_help_chat_message_help_chat_sender CHECK (sender IN ('user','bot')), 
    CONSTRAINT fk_help_chat_message_user_id_user FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX ix_help_chat_message_user_id ON help_chat_message (user_id);

CREATE INDEX ix_help_chat_message_created_at ON help_chat_message (created_at);

UPDATE alembic_version SET version_num='a7c3e91d5b20' WHERE alembic_version.version_num = 'e82c4b9510fa';

-- Running upgrade a7c3e91d5b20 -> b8d4f02e6c31

ALTER TABLE support_ticket ADD COLUMN assigned_to_id INTEGER;

CREATE INDEX ix_support_ticket_assigned_to_id ON support_ticket (assigned_to_id);

ALTER TABLE support_ticket ADD CONSTRAINT fk_support_ticket_assigned_to_id_user FOREIGN KEY(assigned_to_id) REFERENCES user (id) ON DELETE SET NULL;

UPDATE alembic_version SET version_num='b8d4f02e6c31' WHERE alembic_version.version_num = 'a7c3e91d5b20';

-- Running upgrade b8d4f02e6c31 -> f73d8b26ae10

CREATE TABLE advertising_request (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    name VARCHAR(120) NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    business_name VARCHAR(160) NOT NULL, 
    message TEXT NOT NULL, 
    campaign_id INTEGER, 
    status VARCHAR(20) NOT NULL, 
    email_delivery VARCHAR(30) NOT NULL, 
    created_at DATETIME NOT NULL, 
    reviewed_at DATETIME, 
    CONSTRAINT pk_advertising_request PRIMARY KEY (id), 
    CONSTRAINT fk_advertising_request_campaign_id_ad_campaign FOREIGN KEY(campaign_id) REFERENCES ad_campaign (id) ON DELETE SET NULL
);

CREATE INDEX ix_advertising_request_status ON advertising_request (status);

UPDATE alembic_version SET version_num='f73d8b26ae10' WHERE alembic_version.version_num = 'b8d4f02e6c31';

-- Running upgrade f73d8b26ae10 -> 0a94e27c61bd

CREATE TABLE wishlist_letter (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    household_id INTEGER NOT NULL, 
    profile_id INTEGER NOT NULL, 
    wishlist_id INTEGER NOT NULL, 
    sender_name VARCHAR(120) NOT NULL, 
    send_on DATE NOT NULL, 
    created_by_id INTEGER NOT NULL, 
    CONSTRAINT pk_wishlist_letter PRIMARY KEY (id), 
    CONSTRAINT fk_wishlist_letter_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_wishlist_letter_profile_id_person_profile FOREIGN KEY(profile_id) REFERENCES person_profile (id) ON DELETE CASCADE, 
    CONSTRAINT uq_wishlist_letter_wishlist_id UNIQUE (wishlist_id), 
    CONSTRAINT fk_wishlist_letter_wishlist_id_wishlist FOREIGN KEY(wishlist_id) REFERENCES wishlist (id) ON DELETE CASCADE, 
    CONSTRAINT fk_wishlist_letter_created_by_id_user FOREIGN KEY(created_by_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE INDEX ix_wishlist_letter_household_id ON wishlist_letter (household_id);

CREATE INDEX ix_wishlist_letter_profile_id ON wishlist_letter (profile_id);

UPDATE alembic_version SET version_num='0a94e27c61bd' WHERE alembic_version.version_num = 'f73d8b26ae10';

-- Running upgrade 0a94e27c61bd -> 1bc58d704a92

ALTER TABLE wishlist_letter ADD COLUMN theme_id INTEGER;

ALTER TABLE wishlist_letter ADD CONSTRAINT fk_wishlist_letter_theme_id_shared_theme FOREIGN KEY(theme_id) REFERENCES shared_theme (id) ON DELETE SET NULL;

CREATE TABLE letter_art_purchase (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    household_id INTEGER NOT NULL, 
    theme_id INTEGER NOT NULL, 
    buyer_user_id INTEGER, 
    art_name VARCHAR(80) NOT NULL, 
    amount_cents INTEGER NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    stripe_session_id VARCHAR(255), 
    checkout_url VARCHAR(2000), 
    expires_at DATETIME NOT NULL, 
    payment_intent VARCHAR(255), 
    paid BOOL NOT NULL, 
    revoked BOOL NOT NULL, 
    created_at DATETIME NOT NULL, 
    CONSTRAINT pk_letter_art_purchase PRIMARY KEY (id), 
    CONSTRAINT fk_letter_art_purchase_household_id_household FOREIGN KEY(household_id) REFERENCES household (id) ON DELETE CASCADE, 
    CONSTRAINT fk_letter_art_purchase_theme_id_shared_theme FOREIGN KEY(theme_id) REFERENCES shared_theme (id) ON DELETE CASCADE, 
    CONSTRAINT fk_letter_art_purchase_buyer_user_id_user FOREIGN KEY(buyer_user_id) REFERENCES user (id) ON DELETE SET NULL, 
    CONSTRAINT uq_letter_art_purchase_stripe_session_id UNIQUE (stripe_session_id)
);

CREATE INDEX ix_letter_art_purchase_household_id ON letter_art_purchase (household_id);

CREATE INDEX ix_letter_art_purchase_theme_id ON letter_art_purchase (theme_id);

CREATE INDEX ix_letter_art_purchase_payment_intent ON letter_art_purchase (payment_intent);

UPDATE alembic_version SET version_num='1bc58d704a92' WHERE alembic_version.version_num = '0a94e27c61bd';

