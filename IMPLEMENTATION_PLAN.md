# MVP implementation and acceptance checklist

Updated October 27, 2026. Earlier unchecked planning notes were obsolete. Current authoritative references: docs/MVP_INVENTORY.md (132 product actions), docs/MVP_READINESS.md (release gates), docs/COPILOT_MVP_REVIEW.md (review prompt), docs/MVP_API_ROUTES.md (179 declared routes).

## Implemented in source; not all integration-verified

- [x] React/Vite/Bootstrap frontend, Flask APIs, MySQL models/migrations and Docker/Render setup.
- [x] Accounts, credential updates/recovery, CSRF, session versions and rate limits.
- [x] Families/company registries, own-profile identity, exact-email joins/follows, separate adult ownership, managed children/pets and selective grants.
- [x] Photos/cartoons, gift preferences/allergies, profile completion, Discover prompts and reminders.
- [x] Everyday/occasion lists, product/link/manual wishes, sharing, suggestions, move/copy/received and delivery addresses.
- [x] Followed-gift search, optional min/max/currency budget and dismissible wishlist price-range ideas.
- [x] Hearts/private plans, holds/expiry, purchase secrecy/history, co-buy percentages and optional emails.
- [x] Secret Santa/White Elephant and restricted compatibility child-mode paths.
- [x] Themes/display, install entry, keyword help, chat escalation and support tickets.
- [x] Developer/staff portal: assignments, consent-bound debug access, invitations/family setup, account/Stripe/affiliate overviews, publishing, advertising inbox/reviews and verified email alerts.
- [x] Frontend automated checks and production build; backend regression sources added.

## Still required for accepted MVP / beta

- [ ] Execute the full current backend suite; Python/Docker could not run it in this review.
- [ ] Verify migration chain through f73d8b26ae10 and fresh-schema parity on disposable MySQL.
- [ ] Prove MySQL reservation/concurrent privacy/organize behavior.
- [ ] Run multi-role browser/privacy/device/accessibility walkthroughs.
- [ ] Verify controlled SMTP invite/recovery/ad-recipient confirmation and alert delivery.
- [ ] Verify actual HTTPS/origin/cookie/Redis/persistent-storage/backup deployment.
- [ ] Validate SerpApi if enabling live search; otherwise test fallback.
- [ ] Validate Stripe TEST-mode checkout/webhooks if enabling paid ads; otherwise keep paid ads off.
- [ ] Review public privacy/support/retention information and operational quotas.
- [ ] Have Copilot independently review the handoff; no Copilot service has been invoked.

## Out of current scope

Retail checkout/automatic store purchase verification, co-buy payments, hidden-address fulfillment, shipping tracking, SMS/push, offline list edits, subscriptions/storage plans, LLM support, gift-card affiliate provider and arbitrary exchange rules. These are not silently counted as MVP-complete features.
