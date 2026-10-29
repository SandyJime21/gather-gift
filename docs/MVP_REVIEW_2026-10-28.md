# MVP review — October 28, 2026

**Updated later the same day:** see [release readiness](RELEASE_READINESS.md) for fixes to the header/session/payment findings and current deployment preparation.

## Decision

The main family wishlist feature set is implemented and suitable for controlled local acceptance review. Public-launch readiness is not established. No GitHub Copilot service was invoked.

## Child access changes completed

Optional online search, product-link imports, pet wishlist management, sibling switching, and game invitations now default to off. The supervising parent can approve or revoke each activity from the child's Profile settings. API checks enforce approval on every request, including previously returned search results. Manual wishes remain available on approved lists. The child route allowlist now guards all API blueprints, including future endpoints. Adult settings, billing, private gifting, developer tools, and sharing remain unavailable to children. See [child access details](CHILD_SAFETY.md).

Permissions use existing account JSON storage; no schema migration was introduced in this review. The latest existing migration remains `1bc58d704a92`.

## Verification

- Baseline full frontend suite: 151 passed before the new permission component.
- Baseline full backend suite: 159 passed; one failed during Windows file cleanup after SPA route assertions. The test left streamed file responses open; corrected it to close both responses before deleting its fixture directory.
- Final focused backend suite: **30 passed**, covering health/SPA serving, child controls, child access, household modes, pet wishes, and gift games. This includes direct endpoint bypass attempts and parent approval/revocation.
- Production frontend build: passed after the final implementation. Vite warns that the main bundle exceeds its size advisory threshold.
- Final full frontend suite: **152 passed**, using one worker; see `mvp-current-frontend-results.json`. A new permission-switch test initially expected a switch role that React Bootstrap did not supply; switches now explicitly expose that role. Concurrent runs also exposed an existing intermittent 5-second Settings pet test timeout; the final sequential run passed.
- An additional direct regression confirms that a newly registered API endpoint with no authentication decorator is still blocked for a child by the global allowlist (1 passed).

The full backend XML describes the baseline run, including the cleanup failure; it is not rewritten as though that initial run passed. Focused verification after the fix is reported separately above.

## Remaining concrete issues

1. **Header photo fallback:** `HouseholdModeControl` still relies on a separate household-session lookup instead of the canonical `user.active_profile`. Its fallback also requires no `browsing_as`, which normal session payloads populate. A missing own-profile row in the switcher can therefore leave the active user's header photo absent. Confirmed source defect; not changed by the child-safety patch.
2. **Session refresh error handling:** `App.refresh` clears the signed-in user and CSRF state for every failed `/auth/me` request, including temporary server/network failures. A transient outage can appear to sign the user out. Overlapping refresh/login requests also need a browser regression check. Confirmed broad error handling; the timing race remains an inference to reproduce.
3. **Account deletion operational dependency:** deletion requires the list-backup email to succeed. Missing or failing SMTP blocks deletion. Verify delivery and expected failure handling in the deployed environment.
4. **Payment cancellation edge:** a previously created letter-art checkout can finish after family deletion. The webhook avoids restoring deleted data, but an automatic refund path for that case is not implemented. Resolve before enabling paid art for public customers.

## Acceptance still required

- Browser walkthrough of actual sign-in, active user image, child PIN exit, parent switches, mobile/iPad layout, Following, lists, and deletion dialogs.
- SMTP inbox delivery for invites, recovery, advertising requests, and deletion CSVs.
- Stripe TEST checkout/webhook/refund validation, including one-time family unlocks and cancellation/deletion edges. No real purchase was made in this review.
- MySQL concurrency and deployed access checks; backend automated tests use isolated SQLite, not production data.
- A deployment configuration review and independent security/privacy review before public use by families with children. The controls above are not a legal compliance certification.

The developer portal inventory includes support access/tickets, advertising requests and approved campaign management, artwork/theme editing, letter art free/paid pricing and availability, and transaction reporting. The earlier [action inventory](MVP_INVENTORY.md) remains useful for functional walkthroughs; use this review for current limitations and validation evidence.
