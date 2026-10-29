# MVP readiness audit

**Superseded:** see [release readiness](RELEASE_READINESS.md) and [deployment guide](DEPLOYMENT.md). The header/session/payment issues from the earlier October 28 review have been addressed; the historical Python/runtime and migration limitations below no longer describe the current workspace.

October 27, 2026. Reviewer: Codex. No GitHub Copilot service was invoked.

## Decision

Feature implementation is substantially complete for the requested family-registry MVP. Release acceptance is NOT complete. Ready for independent local review; private beta/public launch is not certified by this audit.

Evidence: 123 frontend tests pass; production build passes. Backend tests could not execute because Python cannot run here. Docker was checked as fallback, but its engine pipe is unavailable and its user configuration unreadable. No database was upgraded, no customer records changed and no live SMTP/Stripe/retailer request used for verification.

## Findings addressed during this audit

| ID | Trigger/finding | Source change | Verification |
| --- | --- | --- | --- |
| MVP-01 | Advertising email links use /support?advertising_request=ID, but the portal defaulted to Tickets and signed-out redirect discarded the destination. | Preserve staff sign-in next URL and select Advertising for the target. | New frontend routing regressions pass. |
| MVP-02 | Followers with profile access received private-list titles from the list catalog. | Filter metadata by effective sharing or actual family access. | Backend regression added; not executable here. |
| MVP-03 | Changing a list to private left holds reserved for shoppers losing access. | Cancel only ineligible open holds; preserve access through other shared linked lists. | Backend regression added; SQLite/MySQL execution required. |
| MVP-04 | Shared delivery data was returned from a private list or via a reused item linked to public/private lists. Owner preview used older per-item flags. | Enforce list privacy on direct/item delivery data; align shopper preview. | Cross-list privacy regression added; backend unverified. |
| MVP-06 | A personal wish attached to a family-visible profile could bypass its personal audience through generic item/list shopping paths. | Check the personal-wish audience in the shared item-audience helper before applying list policy. | Explicit family-linked private-wish backend regression added; not executable here. |
| MVP-05 | Help escalation promised email follow-up although it creates an in-app ticket. | Point users to Settings > Help & support for replies. | Existing frontend checks pass; no automatic reply email claimed. |

Files: src/App.jsx, src/HelpAssistant.jsx, backend/app/api/__init__.py, src/App.test.jsx, backend/tests/test_pet_profiles.py, backend/tests/test_list_delivery.py, backend/tests/test_personal_wishes.py. Source fixes are not proof the unexecuted backend regressions pass.

## Acceptance gates before real families

1. Run the complete backend suite in isolated Python. New preference, budget, advertising-email and privacy tests have not executed here.
2. Build a disposable MySQL database through migration head f73d8b26ae10. Compare schema.sql fresh setup with Alembic-built schema. Do not assume the existing/deployed DB is upgraded.
3. Exercise simultaneous last-quantity reservations, concurrent privacy/cancellation, moves and received/purchase operations on MySQL. SQLite does not prove row locks.
4. Browser walkthrough as creator, separate adult, follower, unrelated user and staff/master: selective access, photos/allergies, private lists/addresses, suggestions, holds and buyer secrecy.
5. Real SMTP smoke tests with controlled inboxes: joins/follows/setup invites, recovery, ad-recipient code, pending replacement/expiry, failed and successful alert delivery. Mocks do not prove deliverability.
6. Deployment checks: HTTPS/origins/cookies/CORS, Redis, persistent media, backup/restore, migration startup and SPA rewrites.
7. Laptop/iPad install, phone layout, keyboard/screen reader, 150% text and 200% zoom. No real browser/device validation ran here.
8. If enabling live search: SerpApi quota/provider test and metadata/SSRF/blocked-store fallback checks.
9. If enabling paid ads: Stripe TEST-mode approval -> checkout -> signed webhook -> scheduled display, plus bad signature/amount, duplicate event, pause and missing pricing. Otherwise leave paid ads off.
10. Publish accurate privacy/support/retention information for photos, allergy notes and stored help chats before public release. This is not legal certification.

## Remaining limits / review priorities

- Legacy child login/mode APIs remain despite removed setup/password controls. Decide explicitly whether compatibility stays, and test every direct endpoint.
- List Public and personal-wish Public have different audiences. Verify labels and anonymous preview boundaries.
- Independently review linked-adult private data under owner-approved household support grants, legacy item flags, public image serving and reused-item occasion metadata. These are review targets, not certified safe or proven defects here.
- Query caps, per-row authorization and polling need realistic-data measurement. Money totals currently use the latest 200 campaigns, not lifetime accounting.
- Help is keyword retrieval, with client-generated answers and recent signed-in logging; not an LLM. Privacy/logging disclosures and retention need review.
- Hold/chat cleanup is activity-driven; advertising SMTP is synchronous with no background retry worker. Requests are saved before notification delivery.
- Upload quotas/cleanup, scaling/pagination and provider spend remain operational work. Main JavaScript exceeds the advisory 500 KB chunk threshold.
- Older claims about service configuration, applied migrations or backend pass counts refer to an earlier environment. They were not re-certified; secret values were not printed or used.

## Required Copilot evidence

For findings: severity, source line, role, exact trigger/request, expected/actual result, minimal fix/test, and reproduced versus inferred versus hypothetical. Acceptance requires explicit results for the gates, or a deliberate decision to disable the affected optional feature. Frontend pass counts alone are not launch approval.
