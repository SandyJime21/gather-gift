# Universal shopping handoff

Status: local implementation only. No push, deployment, production migration, real affiliate call or email was performed for this work. No merchant approval is assumed.

## Save a gift

Use **+ Add Gift From Any Store** in My wishes, Discover or a profile. Paste an HTTPS product link, review or enter the name and optional estimated price, choose a recipient and existing registry, then save. A profile entry point preselects its registry. Unknown stores and unavailable metadata still allow manual saving. Private wishes remain private; claimed adults receive suggestions rather than unauthorized edits. Exact duplicate links in the same destination return the existing gift; other registries remain independent.

Automatic metadata retrieval is restricted to `PERMITTED_METADATA_DOMAINS`. Leave this empty unless retrieval is permitted. Redirects must remain on the allowlist and public network targets. No retailer scraping bypass is included. Product images and prices are optional; prices entered by users are estimates.

## Components and files

New backend modules: `backend/app/universal_gifts.py` (preview fallback), `commerce_urls.py` (URL validation), `commerce.py` (protected redirects, settings and event totals), `commerce_adapters.py` (network capability interface), `search_providers.py` (existing search adapters).

Modified backend: `app/__init__.py` configuration/registration; `app/api/__init__.py` existing saves, duplicate handling and outbound fields; `adult_family.py` suggestion quantity/priority; `link_preview.py` permitted metadata redirects; `product_search.py` aggregation/filter/cache/signed provenance; `ebay_search.py` external IDs; `models/__init__.py` three additive commerce models. Existing product, registry, permission, reservation and purchase records are reused.

New UI: `src/UniversalGift.jsx`, `CommerceAdmin.jsx`, `AffiliateDisclosure.jsx`, `PublicInfo.jsx`. `App.jsx` integrates entry points, public routes and master-only Affiliate Management; `ProductActions.jsx` carries signed source provenance; `GiftDetails.jsx` prefers protected shopping links; `styles.css` adds responsive layouts. `.env.example` documents server configuration names. Related compact-card/editor/store-catalog/email changes already pending in this workspace remain preserved.

Tests: `backend/tests/test_universal_gifts.py`, `test_commerce_resolver.py`, `test_search_providers.py`; updated existing link-preview/product-search/linked-adult tests. UI coverage includes `src/UniversalGift.test.jsx` and `PublicInfo.test.jsx`, plus the existing suite.

Migration: `backend/migrations/versions/6ab4e1d092f3_commerce_integrations.py`, parent `51a8c29e7b10`. Adds `commerce_integration`, `commerce_product_metadata`, `commerce_outbound_event`; no replacement product tables. Inspect the migration for exact table names. Downgrade removes only these additions. Isolated upgrade/downgrade was rehearsed; shared Railway has not been migrated ahead of this release.

## Configuration and access

Existing `DATABASE_URL`, session/secret, mail and production origin settings remain required. Do not commit `.env`. Optional new server names are in `.env.example`: `PERMITTED_METADATA_DOMAINS`, `SOVRN_COMMERCE_API_KEY`, Awin/Impact/CJ/Rakuten/Skimlinks credential placeholders. Only the implemented Sovrn Link Check uses its new credential; placeholders do not connect unfinished network APIs. Existing eBay or SerpApi search credentials are still needed for real search. A free universal product-search database is not included.

Optional build-time `VITE_CONTACT_EMAIL` supplies the public contact address; without it the page directs signed-in users to Help & support. Set a real monitored address before public launch. Public information pages are starter content for owner review, not a claim of legal compliance.

Sign in at `/support/login` with an existing master/superuser account and open **Affiliate Management**. Ordinary family accounts cannot access these controls. Configure approved merchant domains and an issued public tracking template only after genuine approval. Network toggles default off; search toggles are separate from commission approval. Never put secrets in templates.

See [network setup and official documentation](AFFILIATE_NETWORKS.md) for signup/access requirements and unsupported features. Awin, Impact, CJ, Rakuten and Skimlinks support explicitly configured issued templates, not automatic API catalogs or reporting. Sovrn responses containing its configured credential are rejected; accounts requiring credential-bearing links fall back to direct shopping. Existing tagged links are preserved, and absent eligibility or provider errors fall back to the saved original URL.

## Reporting and privacy

Recorded outbound events are actual clicks through the protected saved-item route, not conversions or commissions. Event records have item/provider/merchant/random attribution ID/time, without account ID, IP address or browser fingerprint. DNT/GPC and prefetch/HEAD requests do not produce events. Hosting logs are separate. Other legacy direct links do not contribute to these counts. Conversion and earnings reporting remain explicitly unconnected.

`/demo` uses fictional examples and temporary browser state, without real accounts, family data or reservation writes. `/about`, `/contact`, `/privacy`, `/terms`, `/affiliate-disclosure` are public. Child sessions retain the restricted child router and server restrictions.

## Verification and manual rollout

Production build: `npm run build`. Frontend: `npm test -- --maxWorkers=2`. Backend commerce regression: run pytest on universal_gifts, commerce_resolver, search_providers, link_preview, product_search and linked_adults tests using isolated test databases. Network calls in new commerce tests are mocked. Approved credentials and live partner behavior still require later verification.

When the owner explicitly authorizes a release: review the diff, back up Railway, run CI including MySQL migrations, then push the matching application and migration together. Render pre-deploy runs `flask --app backend db upgrade` before the new service becomes ready. Do not run local `db:upgrade` against the shared database before deployment: old deployed code checks its schema head and may become unhealthy. Verify `/ready`, login, manual URL saving, child restrictions and a permitted shopping redirect after release. Credentials stay in Render environment settings.

Remaining external requirements: actual network/site/merchant approvals; issued credentials; provider-specific catalogs and conversion reporting if desired; a real contact address and policy review; live metadata permissions; owner-authorized deployment. None of these blocks manual HTTPS gift-link saving.

## Recorded verification

- Phase 1: 18 backend and 45 frontend checks passed.
- Phase 2: 17 backend and 52 frontend checks passed; isolated migration upgrade/downgrade preserved existing tables.
- Phase 3: 15 backend and 52 frontend checks passed.
- Phase 4: 25 backend checks passed.
- Final regression: all 213 frontend tests passed; 39 backend commerce/access/search/preview tests passed. After the final comparison-target adjustment, 48 focused frontend tests and the production build passed. A subsequent pending-registry recipient-switch regression was fixed and all 3 UniversalGift tests passed.
- `git diff --check` passed (Windows line-ending notices only). Production build warns about the existing large application bundle; bundle splitting is future performance work.
- No live partner API verification or physical iPhone/iPad test was performed in this phase; responsive layouts and automated browser DOM coverage do not replace those checks.
