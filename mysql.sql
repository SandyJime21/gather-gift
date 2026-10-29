-- Optional, fake local demo data. Apply after `schema.sql` or `flask --app backend db upgrade`.
-- This file intentionally contains inserts only; schema.sql/Alembic own all table DDL.
-- Demo login for both accounts: GatherGiftDemo!2026

USE family_gifts;

INSERT INTO `user` (name, email, password_hash, created_at)
VALUES
  ('Alex Demo', 'demo.parent@example.com', 'scrypt:32768:8:1$3WNdOgZ3kVnpaBlI$5881f7e4ef27381dd48391756f0a7c49017b6c2c23f4f471f4b9b38bb94f2d44b118c6f0cb9c859ca397ca72adb1790645d649a47375d899477ce5fc4eaf3f97', UTC_TIMESTAMP()),
  ('Sam Demo', 'demo.shopper@example.com', 'scrypt:32768:8:1$3WNdOgZ3kVnpaBlI$5881f7e4ef27381dd48391756f0a7c49017b6c2c23f4f471f4b9b38bb94f2d44b118c6f0cb9c859ca397ca72adb1790645d649a47375d899477ce5fc4eaf3f97', UTC_TIMESTAMP())
ON DUPLICATE KEY UPDATE email = VALUES(email);

SET @demo_parent_id = (SELECT id FROM `user` WHERE email = 'demo.parent@example.com');
SET @demo_shopper_id = (SELECT id FROM `user` WHERE email = 'demo.shopper@example.com');

INSERT INTO household (name, owner_id, created_at)
SELECT 'The Example Family', @demo_parent_id, UTC_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT id FROM household WHERE name = 'The Example Family' AND owner_id = @demo_parent_id
);
SET @demo_household_id = (
  SELECT id FROM household WHERE name = 'The Example Family' AND owner_id = @demo_parent_id
);

INSERT INTO household_membership (household_id, user_id, role, created_at)
SELECT @demo_household_id, @demo_parent_id, 'owner', UTC_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT id FROM household_membership
  WHERE household_id = @demo_household_id AND user_id = @demo_parent_id
);
INSERT INTO household_membership (household_id, user_id, role, created_at)
SELECT @demo_household_id, @demo_shopper_id, 'shopper', UTC_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT id FROM household_membership
  WHERE household_id = @demo_household_id AND user_id = @demo_shopper_id
);

INSERT INTO person_profile (
  account_user_id, display_name, birthday, birthday_shared, favorite_colors,
  favorite_brands, favorite_characters, hobbies, interests, clothing_sizes,
  shoe_sizes, gift_preferences, parent_notes, items_to_avoid, updated_at
)
SELECT @demo_parent_id, 'Alex Demo', '1989-09-14', TRUE, JSON_ARRAY('forest green'),
  JSON_ARRAY('local bookstores'), JSON_ARRAY(), JSON_ARRAY('gardening'),
  JSON_ARRAY('tea', 'mystery novels'), JSON_OBJECT(), JSON_OBJECT(),
  'Small, thoughtful surprises.', NULL, NULL, UTC_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT id FROM person_profile WHERE account_user_id = @demo_parent_id AND display_name = 'Alex Demo'
);
INSERT INTO person_profile (
  account_user_id, display_name, birthday, birthday_shared, favorite_colors,
  favorite_brands, favorite_characters, hobbies, interests, clothing_sizes,
  shoe_sizes, gift_preferences, parent_notes, items_to_avoid, updated_at
)
SELECT NULL, 'Mia Demo', '2017-05-18', TRUE, JSON_ARRAY('lavender', 'yellow'),
  JSON_ARRAY(), JSON_ARRAY(), JSON_ARRAY('baking', 'drawing'),
  JSON_ARRAY('books', 'baking'), JSON_OBJECT('shirt', 'kids medium'),
  JSON_OBJECT('US', '3'), 'Enjoys hands-on activities.', 'Please avoid scented products.',
  'Strong fragrances', UTC_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT id FROM person_profile
  WHERE account_user_id IS NULL AND display_name = 'Mia Demo'
);

SET @demo_parent_profile_id = (
  SELECT id FROM person_profile WHERE account_user_id = @demo_parent_id AND display_name = 'Alex Demo'
);
SET @demo_child_profile_id = (
  SELECT id FROM person_profile WHERE account_user_id IS NULL AND display_name = 'Mia Demo'
);

INSERT INTO household_profile_access (household_id, profile_id, can_edit)
SELECT @demo_household_id, @demo_parent_profile_id, TRUE
WHERE NOT EXISTS (
  SELECT id FROM household_profile_access
  WHERE household_id = @demo_household_id AND profile_id = @demo_parent_profile_id
);
INSERT INTO household_profile_access (household_id, profile_id, can_edit)
SELECT @demo_household_id, @demo_child_profile_id, TRUE
WHERE NOT EXISTS (
  SELECT id FROM household_profile_access
  WHERE household_id = @demo_household_id AND profile_id = @demo_child_profile_id
);
SET @demo_shopper_membership_id = (
  SELECT id FROM household_membership
  WHERE household_id = @demo_household_id AND user_id = @demo_shopper_id
);
INSERT INTO household_member_profile_access (membership_id, profile_id, can_edit)
SELECT @demo_shopper_membership_id, @demo_child_profile_id, FALSE
WHERE NOT EXISTS (
  SELECT id FROM household_member_profile_access
  WHERE membership_id = @demo_shopper_membership_id AND profile_id = @demo_child_profile_id
);

INSERT INTO occasion (household_id, profile_id, name, occasion_type, event_date, description, created_at)
SELECT @demo_household_id, @demo_child_profile_id, 'Mia’s Birthday', 'birthday', '2027-05-18',
  'A little celebration for Mia.', UTC_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT id FROM occasion
  WHERE household_id = @demo_household_id AND profile_id = @demo_child_profile_id
    AND name = 'Mia’s Birthday' AND event_date = '2027-05-18'
);
SET @demo_birthday_id = (
  SELECT id FROM occasion
  WHERE household_id = @demo_household_id AND profile_id = @demo_child_profile_id
    AND name = 'Mia’s Birthday' AND event_date = '2027-05-18'
);

INSERT INTO wishlist (profile_id, occasion_id, title, is_everyday, created_at)
SELECT @demo_child_profile_id, NULL, 'Everyday Wants & Needs', TRUE, UTC_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT id FROM wishlist
  WHERE profile_id = @demo_child_profile_id AND is_everyday = TRUE
);
INSERT INTO wishlist (profile_id, occasion_id, title, is_everyday, created_at)
SELECT @demo_child_profile_id, @demo_birthday_id, 'Birthday wishes', FALSE, UTC_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT id FROM wishlist
  WHERE profile_id = @demo_child_profile_id AND occasion_id = @demo_birthday_id
    AND title = 'Birthday wishes'
);
SET @demo_everyday_wishlist_id = (
  SELECT id FROM wishlist WHERE profile_id = @demo_child_profile_id AND is_everyday = TRUE
);
SET @demo_birthday_wishlist_id = (
  SELECT id FROM wishlist WHERE profile_id = @demo_child_profile_id AND occasion_id = @demo_birthday_id
    AND title = 'Birthday wishes'
);

INSERT INTO wishlist_item (
  profile_id, created_by_id, name, description, image_path, store_name, product_url,
  estimated_price, currency, desired_size, desired_color, quantity, category, notes,
  priority, request_type, created_at, updated_at
)
SELECT @demo_child_profile_id, @demo_parent_id, 'Junior baking kit',
  'A kid-friendly set for weekend baking together.', NULL, 'Example Market', NULL,
  24.99, 'USD', NULL, NULL, 1, 'Experiences', 'Reusable tools preferred.',
  4, 'want', UTC_TIMESTAMP(), UTC_TIMESTAMP()
WHERE NOT EXISTS (
  SELECT id FROM wishlist_item WHERE profile_id = @demo_child_profile_id AND name = 'Junior baking kit'
);
SET @demo_baking_item_id = (
  SELECT id FROM wishlist_item WHERE profile_id = @demo_child_profile_id AND name = 'Junior baking kit'
);

INSERT INTO wishlist_item_wishlist (item_id, wishlist_id)
SELECT @demo_baking_item_id, @demo_everyday_wishlist_id
WHERE NOT EXISTS (
  SELECT id FROM wishlist_item_wishlist
  WHERE item_id = @demo_baking_item_id AND wishlist_id = @demo_everyday_wishlist_id
);
INSERT INTO wishlist_item_wishlist (item_id, wishlist_id)
SELECT @demo_baking_item_id, @demo_birthday_wishlist_id
WHERE NOT EXISTS (
  SELECT id FROM wishlist_item_wishlist
  WHERE item_id = @demo_baking_item_id AND wishlist_id = @demo_birthday_wishlist_id
);
INSERT INTO wishlist_item_occasion (item_id, occasion_id)
SELECT @demo_baking_item_id, @demo_birthday_id
WHERE NOT EXISTS (
  SELECT id FROM wishlist_item_occasion
  WHERE item_id = @demo_baking_item_id AND occasion_id = @demo_birthday_id
);
