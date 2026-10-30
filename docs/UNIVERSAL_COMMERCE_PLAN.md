# Universal shopping implementation plan — October 30, 2026

## Repository inspection

- React 18, React Router, React Bootstrap and Vite; existing styling is in `src/styles.css`.
- Flask API blueprint, SQLAlchemy, Flask-Migrate/Alembic, server-side sessions and CSRF; production MySQL sessions/rate limits are shared through Railway MySQL.
- `User`, `Household`, membership/profile grants and parent-owned child controls enforce existing identity and privacy rules. Support accounts and master-only endpoints already exist.
- `WishlistItem` is the existing product/custom-gift record, `WishlistItemWishlist` links it to registries, `Occasion` represents events. `PersonalWish`, gift suggestions, reservations, quantities and purchase secrecy already work. Do not duplicate these systems.
- Existing shopping code: `product_search.py`, `ebay_search.py`, `link_preview.py`, `affiliate_links.py`, `ProductActions.jsx`, `StoreGiftFinder`, `ManualGiftEntry`, and wishlist/profile routes.
- Render Docker deployment builds Vite and serves the client through Flask. Pre-deploy runs migrations and `/ready` verifies the schema revision. Never migrate the shared production database ahead of undeployed code.
- Current affiliate support is server-held store rules, an Amazon tracking tag and optional eBay campaign links. No network approval has been confirmed; the store catalog marks every retailer unapproved.

## Small phases

1. Universal save: extend existing item creation with opt-in duplicate handling; one URL/manual form, quantity/priority/notes/image editing, and existing registry/suggestion destinations.
2. Resolver: central validation, approved merchant/network configuration, Sovrn Link Check adapter, preserve existing tagged links, permission-checked item redirects, anonymous aggregate event storage and disclosure.
3. Provider search: retain eBay and SerpApi through a common interface, capability/status reporting and retailer/brand/category/price filters. Unconfigured providers return honest empty states.
4. Other networks: official documentation research, named capability interfaces and explicit credentials/approval/development states; no invented endpoint behavior or earnings.
5. Admin/public: master-only integration controls and actual click summaries; unavailable conversion/commission data labeled unavailable; public sample registry and information pages using no family records.

## Verification and rollout

Use mocked network responses and isolated SQLite/MySQL tests for unsafe URLs, permission boundaries, duplicate targets, independent-store fallback, network errors and click-vs-sale reporting. Check mobile layouts, frontend regression tests and the production build. Rehearse migrations locally only. Deliver a file inventory, configuration guide, capability matrix and manual Render deployment instructions. Do not push or deploy automatically.

## Completion checkpoints

All five local implementation phases passed their targeted tests. See `UNIVERSAL_COMMERCE_HANDOFF.md` for capabilities, test results, limitations and manual rollout. Network credentials/approval and live verification remain external requirements; direct gift-link saving does not depend on them. Nothing has been pushed, deployed or migrated on the shared production database.
