# MVP release preparation

October 28, 2026. Prepared for GitHub and a Render staging deployment. No repository was published and no Render resources were created.

## Fixed

- Header identity now uses the active profile returned with the signed-in user's session, independently of the profile-switcher menu. It does not substitute another family member's photo. Invalid/deleted active profile selections are cleared by the server.
- Temporary network/server failures during session refresh preserve the signed-in identity and show a retry action. Only HTTP 401 clears the session. Older refresh responses cannot overwrite newer ones or resurrect a signed-out user.
- CSRF responses from older sessions cannot replace the token received after sign-in. The login form prevents duplicate submissions and reads the actual form fields, including password-manager values.
- A pending letter-art checkout paid after deletion requests a full refund using a stable Stripe idempotency key. Failed requests remain retryable; repeated events do not recreate family data or issue duplicate refunds. Previously fulfilled purchases retain only a one-way receipt hash so an old webhook does not refund an already delivered design after account deletion.
- Child activities remain default-deny and parent-controlled, including direct API access. Account/payment/developer controls stay unavailable to children.
- API JSON responses use `Cache-Control: no-store`; response headers disable MIME sniffing and framing. Production sends HSTS.
- The checked-in MySQL setup SQL has been regenerated from the complete migration chain through `1bc58d704a92`, including previously missing help/support and letter-art schema. Existing databases continue to use Alembic, not the development bootstrap SQL.

## Deployment prepared

- GitHub Actions: frontend tests/build, backend tests, source credential checks, fresh MySQL migration/schema comparison, Docker image build, and read-only repository permissions.
- Render Blueprint: automatic deploy only after CI passes, migrations in the pre-deploy stage, Redis sessions/rate limits, persistent photo storage, and `/ready` health checking.
- Docker: Node 22 build, Python 3.12 runtime, Gunicorn workers/threads, bounded request timeout, and container logging. Migration commands are separate from worker startup.
- Production validates the public HTTPS origin, sufficiently long app secret, external MySQL, Redis, encrypted SMTP when configured, and paired payment keys. Missing SMTP no longer blocks startup/migrations; email-dependent actions stay unavailable until configured. MySQL connections verify TLS certificates/hostnames and use connection health checks.
- Optional payments, ad prices, product search, and affiliate tracking start disabled. Core manual wishlists/preferences still work.
- Ignore rules and the source packaging script exclude local users, photos, session files, email previews, exports, dependency folders, generated test reports, and environment secrets.

## Verification completed

| Check | Result |
| --- | --- |
| Full frontend suite | **156 passed** |
| Full backend suite | **174 passed** |
| Production frontend build | Passed; main-bundle size advisory remains |
| Compiled SPA/JS asset/API/readiness smoke check | Passed with an isolated in-memory database/session cache |
| Existing local MySQL schema vs models | No upgrade operations detected; read-only comparison |
| Full migration SQL generation | Passed through `1bc58d704a92`; no live schema changes |
| Render Blueprint | Passed Render's official JSON Schema |
| GitHub workflow | YAML parsed successfully; Actions have not run remotely |
| Source credential/privacy check | Passed; filename-only reporting |

Local generated reports are `docs/release-frontend-results.json` and `docs/release-backend-results.xml`; these are intentionally excluded from GitHub/source bundles. Automated backend tests used isolated SQLite databases with live mail/search/payment credentials disabled. Stripe calls in refund/checkout regressions were mocked; no real payment or refund was made.

## What remains outside this workspace

Publish the clean source to your GitHub repository, connect the Render Blueprint, and supply managed MySQL and SMTP credentials. Git is unavailable in the current environment, and no repository URL or connected deployment account was provided. The local Docker daemon is unavailable; the prepared CI includes the actual image-build gate.

Before inviting families, verify deployed MySQL TLS/Redis connectivity, photo persistence after redeployment, SMTP inbox delivery/recovery/export, and desktop/phone/iPad flows. If enabling paid features, complete Stripe test-mode checkout/webhook/refund acceptance first. The app is prepared for this deployment review; external integration checks have not been represented as completed.

Follow [the deployment guide](DEPLOYMENT.md) for exact settings, commands, developer-portal setup, and acceptance steps. [Render Blueprint reference](https://render.com/docs/blueprint-spec), [Render deploys and CI](https://render.com/docs/deploys), [Stripe refunds](https://docs.stripe.com/api/refunds/create).
