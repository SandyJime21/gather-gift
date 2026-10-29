# Copilot MVP review handoff

Prepared October 27, 2026. Paste this into GitHub Copilot Chat in this repository. Copilot has not been invoked by the assistant preparing it.

## Paste this review prompt

Review Gather & Gift independently to decide whether its current family-registry MVP is ready for controlled beta. First read docs/MVP_READINESS.md, docs/MVP_INVENTORY.md, docs/MVP_API_ROUTES.md and docs/MVP_VALIDATION.json. Verify every inventory claim against source and actual tests. Older README/planning notes may be stale; passing frontend tests do not prove backend correctness.

Give findings first, highest severity first. Include severity, exact file/line, affected role/flow, concrete trigger/API request, expected/actual behavior, whether reproduced or inferred, a minimal fix and meaningful regression test. Separate established code defects from hypotheses and environment blockers.

The preceding audit could not run Python or Docker's engine; there is no current backend-suite, migration or live-service certification. Read the current validation JSON rather than historical pass counts, and re-run checks independently.

Do not deploy, upgrade customer databases, use production secrets/data, send messages, create real accounts, charge payments, install packages or contact anyone during review without explicit authorization. Never print .env values, real verification codes, credentials or customer records. Mock external services in unit tests.

### Product acceptance checks

- Wishes from different stores; own/loved-one registries; adult own-login family joins; managed children/pets without required accounts; approved follows/sharing; external retailer purchases.
- Five main screens, redirects and auth-return URLs. People including you first, smaller pet row, only active identity photo in header, no pet login choice.
- Profile sizes, brands/stores/colors/snacks, interests/characters, allergies, birthday/photo and preferences. Blank allergies differ from None known; private parent notes never appear in guides.
- 0-to-100 completion, live updates, shorter child/pet checklists, Discover prompts, missing-detail reminders and correct editor links.
- Personal audiences versus list privacy. Private list titles, addresses and items must remain private through direct APIs and reused public/private item links. Verify revocation releases now-ineligible holds and shopper preview matches reality.
- Optional min/max/currency budgets across followed people, inclusive/zero boundaries, unknown/other-currency exclusion, literal numeric product names and No budget restoration. Optional owner price-range checklist disables/restores account-wide without restricting expensive gifts.
- Search/link/manual gift entry, quantity/priority, manage/rename/open lists, own-only adult edits, suggestion approval, move/copy/received and shared item availability.
- Hearts versus holds, undo, 24-hour expiry, offsite checkout, purchase secrecy, availability, past gifts and co-buy percentages/decline. No retail purchase verification or co-buy money collection is claimed.
- Secret Santa/White Elephant eligibility, join/leave/start/cancel, no self-draws, assignment secrecy, turn/steal/version rules and no accidental list-access grant.
- Direct legacy-child API restrictions despite removed setup UI: adult endpoints, sibling identity, photos, games, addresses, advertising and staff access.
- Install/manual iPad instructions, keyboard/screen-reader/dark/large-text/mobile layouts, loading/error/empty states and network failures.

### Developer portal: verify every section

1. Staff authentication is separate. Master controls must reject direct ordinary-staff/family requests.
2. Tickets: master sees all and assigns/unassigns staff; staff see/reply/update assigned tickets only; customers access their own. Verify contact/time/status/message privacy and assignment revocation.
3. Support access/debug: reason, owner/admin consent, one-hour expiry, revocation, snapshots/profile edits/hold release and audits; no general impersonation or secret buyer leakage. Specifically review independently linked adult private data within a household grant.
4. Family & invites: requested support setup, optional birthday/photo, private email-bound ownership claim, no retained setup-staff access, single-use/expiring staff invitations and no public staff signup.
5. Ticket login merges: eligible candidate matching, explicit agreement/confirmation, ownership/membership/session changes and audit trail. No real merges during review.
6. Money & Stripe: only read-only status/balances, no secret output, campaign paid/pending totals and latest-200-row limitation. Affiliate dashboards/tag status are not imported earnings or payouts.
7. Accounts: master-only name/email search, count/type/join-date overview and cap; no implied deletion/impersonation rights.
8. Themes/cartoons: master publishing, upload validation/access, shared storage/audiences, no child-settings escalation and no claimed image generation.
9. Advertising inbox: inquiries AND campaign submissions persist; new counts, sender contact/message, statuses/review links, role isolation and rate limits. Mail failure cannot lose the request.
10. Advertising alerts: name/email setup, code sent to that exact destination, hashed expiring single-use/session-bound confirmation, attempt/rate limits. A pending replacement never activates; existing confirmed recipient stays active. Disable/re-enable and SMTP-failure behavior must be tested without real mail.
11. Advertising email links: /support?advertising_request=ID survives staff sign-in, opens Advertising and focuses the request. Reviewing a campaign updates the inbox state.
12. Campaigns: server placement pricing/frozen checkout amount, master approve/reject/pause, pending media privacy, signed/idempotent/validated Stripe events, paid/timezone/schedule/keywords, sponsor labels and no Settings/child ads.
13. Assistant chats: keyword help, signed-in logging versus guests, escalation to tickets, master-only recent chat access, client-supplied answer integrity, limits/retention and no false automatic-email promise.

### Infrastructure/security/performance

Inspect CSRF, sessions/invalidation, object authorization, exact invited emails, selective grants/inheritance revocation, public endpoints, files/addresses/notes, URL-preview SSRF/DNS/redirect/TLS/size/time checks and affiliate domain matching. Hidden UI is not authorization.

On disposable MySQL, compare Alembic through f73d8b26ae10 with schema.sql; check a single head and no unapplied schema changes. Exercise last-quantity races, privacy/hold cancellation, received/moves and co-buy. SQLite cannot prove MySQL locking.

Check Docker/Render startup, bundled SPA rewrites, origins/HTTPS/cookies/CORS, Redis, persistent media, backup/restore, upload quotas/cleanup, pagination/caps, N+1 queries, polling and provider spend. Distinguish measured bottlenecks from guesses.

### Local checks

Activate an isolated Python environment; keep SMTP/Stripe/search mocked. Do not execute schema.sql on an existing database.

~~~powershell
npm.cmd test
npm.cmd run build
python -m pytest backend/tests -q --basetemp=backend/instance/copilot-review-UNIQUE-ID
~~~

Use a fresh UNIQUE-ID. Backend fixtures use isolated SQLite. Plan browser/disposable-MySQL/SMTP/Stripe-test-mode checks separately; never silently use production. PowerShell native-stderr redirection can report a shell error for a build warning: inspect actual process/report results instead of equating the chunk advisory with a failed build.

### Required final review output

- Findings with severity, file/line, reproduction and minimal fix/test.
- Checked feature inventory: implemented + verified / implemented + unverified / partial or backend-only / absent.
- Test commands/results, skipped checks and actual reasons.
- Launch blockers versus optional improvements/features to disable for beta.
- Explicit verdict: local demo only, controlled beta ready, or public launch ready, with reasons.

Pay special attention to MVP_READINESS.md fixes: frontend regressions pass but new backend privacy/address/hold tests were not executed in the preceding environment. Do not call the app secure, complete or production-ready based solely on frontend tests.
