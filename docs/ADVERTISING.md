# Advertising workflow and developer notifications

Updated October 27, 2026. Source implemented; live SMTP/Stripe/storage and backend regressions are not certified by this review.

## Public requests

Visitors can send name, contact email, optional business and message from the landing page or Advertise. This saves an AdvertisingRequest in the private developer inbox; it no longer depends on opening the visitor's mail app. Public submissions have CSRF, input limits and rate limits. A submitted campaign creates a linked inbox entry as well.

## Developer portal

Master developer: /support -> Advertising. The inbox loads/polls while active, counts new requests, shows contact/business/message/time/email delivery state, supports new/reviewed/closed, and opens a linked campaign. Campaign approval/rejection/pause marks its new inbox entry reviewed. Ordinary family accounts and non-master staff cannot use these endpoints.

Advertising notification email accepts a recipient name/address. Send a six-digit confirmation code to that address; only successful confirmation enables email alerts. Codes are hashed, single-use, session-version-bound, expire in 10 minutes and have rate/attempt limits. Pending replacement does not overwrite the current confirmed recipient. Email alerts can be disabled/restored after verification.

Configure SMTP_HOST/SMTP_PORT/SMTP_STARTTLS/MAIL_FROM and required credentials on the server. The UI exposes configuration availability, never SMTP credentials. Requests are committed before email delivery; missing SMTP, disabled/unverified recipients and failed sends do not remove portal records. Delivery is synchronous; there is no background retry worker. A notification link selects Advertising after staff sign-in and focuses the request.

## Campaign review, pricing and payment

Advertisers supply a supported image/video upload (JPEG/PNG/WebP/MP4/WebM, 7 MB maximum) or hosted HTTPS creative, contact/store link, placements, dates, weekdays/hours/timezone, rotation length and optional keywords. Store the private campaign access token securely; it grants status/payment access.

Master review precedes Stripe checkout. Price is server-owned: selected placement daily rates times selected scheduled days, inclusive dates; hours/rotation length do not change daily rates. Current keys are home/wishlist/discover; check actual label/placement wiring. Configure ADS_DAILY_RATE_CENTS and applicable placement overrides. Unconfigured rates are not invented. Keep paid ads disabled until the configured Stripe test flow is verified.

Only valid signed Stripe payment confirmation marks paid; the checkout return page does not. Validate expected campaign/session/currency/amount and idempotency. Public display also requires approval and an active timezone/day/hour schedule. Pause removes eligibility. No automatic refunds/payout UI; use Stripe's dashboard as appropriate.

## Display and storage

Discover uses a labeled sponsored row; other active placements use shared rotation. Videos have controls and no autoplay. No Settings or child-mode ads. No guaranteed impressions or exclusivity. Keyword context comes from eligible saved/personal wishes and is not returned to advertisers.

Uploaded creatives live under UPLOAD_FOLDER/advertising on persistent storage. Pending/unpaid uploads require private token/master access. Hosted creative remains external. Validate formats/content/access and plan quotas, backups and cleanup; no automated media-retention job is implemented.

## Reviewer files

backend/app/advertising.py, invitation_mail.py, models/__init__.py; src/Advertising.jsx and AdvertisingRequests.jsx; migrations through f73d8b26ae10; backend/tests/test_advertising.py and test_advertising_requests.py; src/Advertising.test.jsx and AdvertisingRequests.test.jsx. Run backend, MySQL, SMTP and Stripe TEST-mode checks independently.
