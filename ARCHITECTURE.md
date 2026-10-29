# Architecture

Updated October 27, 2026. Current feature scope and acceptance status are in docs/MVP_INVENTORY.md and docs/MVP_READINESS.md.

## Runtime

React/Vite/Bootstrap SPA in src; Flask application factory and REST blueprints in backend/app. Development Vite proxies /api and /health. The production Dockerfile builds the SPA, bundles it into the Python image, runs Alembic at startup and serves frontend/API together with Gunicorn. Separate frontend hosting is possible with explicit origin/cookie/CORS configuration.

MySQL is the intended deployment database; SQLAlchemy/Alembic are canonical. schema.sql is a fresh-database snapshot and mysql.sql is optional demo INSERT data, not an upgrade script. Local CacheLib filesystem sessions and production MySQL sessions/rate limits are configured through environment values. Uploaded media needs persistent storage. /ready is the deployment probe.

## Modules

- backend/app/api/__init__.py: core accounts, families/profiles, list/item sharing, shopping, support/tickets, photos, themes/avatars, notifications and compatibility routes.
- adult_family.py: linked adult ownership, family connections, suggestions and inherited grants.
- profile_preferences.py: gift-guide whitelist and completion checklist.
- advertising.py: public inquiries/campaigns, master inbox/reviews, confirmed alert recipient, schedule/pricing/Stripe webhook handling.
- money.py: master-only read-only Stripe status, campaign totals, affiliate configuration and account overview.
- gift_games.py: Secret Santa/White Elephant eligibility and state transitions.
- invitation_mail.py: SMTP invitations/codes/advertising alerts; link_preview.py and product_search.py handle guarded metadata/provider calls; affiliate_links.py rewrites eligible outbound store links.
- models/__init__.py: users, household grants, profiles/lists/items, reservations, personal audiences, games, support/chat/assignment data and advertising requests.
- src/App.jsx and components: screens, navigation, list/shopping actions and portal sections. lib/api.js sends credentialed requests and CSRF headers.
- backend/tests and src/*test*: backend regression sources and frontend automated checks. Current backend execution remains blocked in this workspace.

## Relationships and policy

Accounts differ from profiles. Adults may have own credentials linked to a family; managed children/pets do not require accounts. Household membership and selected-profile grants are separate. A reusable gift may join several lists/occasions, while reservations belong to its item, so stock is shared across copies of that reference.

Personal-wish audiences and managed-list privacy are distinct policies. Private list names/content/addresses must be gated. Public in a managed-list toggle means approved viewers, not anonymous public access. A private/public linked-item combination needs per-list address filtering and careful metadata checks.

Gift guides contain only shared preference fields and require profile-view permission. Private parent/avoidance notes are excluded. Birthday sharing remains explicit. Completion is shown to editors, with shorter child/pet checklists.

Recipients can see availability/hold/purchased quantities without secret buyer identity. Hearts do not reserve items. Buying now creates a hold; offsite retailer checkout is not verified automatically. Co-buy percentages do not collect money. MySQL reservation/concurrency behavior remains an acceptance gate.

Support uses separate staff sessions and customer-approved expiring/revocable grants. Ordinary staff have assigned tickets; master-only controls cover assignment, accounts/money, publishing, advertising and chat review. Grant boundaries around independent adult private data require adversarial verification.

Advertising requests are committed before SMTP delivery. Only confirmed/enabled master-configured recipients receive new alerts. A pending replacement does not supersede the confirmed recipient; failed delivery retains the inbox record. Payment eligibility additionally requires master review, frozen server pricing and a validated signed Stripe event.

Help is keyword retrieval, not an LLM. Signed-in chat logs/escalated tickets contain personal data. Recent-window cleanup and hold expiry are activity-driven; there is no general background job worker, browser push or automated upload retention service.

## Release verification

Do not equate source implementation with readiness. See docs/MVP_VALIDATION.json for current frontend results and blocked backend/live checks, docs/MVP_API_ROUTES.md for the declared route catalog, and docs/COPILOT_MVP_REVIEW.md for the independent review prompt. Test migrations on disposable MySQL, not a customer database; verify actual deployment SMTP/database/storage/cookies/browser behavior separately.
