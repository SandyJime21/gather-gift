> Current release preparation (October 28, 2026): [GitHub and Render deployment guide](docs/DEPLOYMENT.md), [MVP fixes and verification](docs/RELEASE_READINESS.md), and [all app actions](docs/MVP_INVENTORY.md).

# Family Gift Registry

Database updates from your terminal: [database commands](docs/DATABASE_COMMANDS.md). Run `npm.cmd run db:upgrade` to apply migrations to the database configured in your environment.

Current feature/navigation inventory and beta launch checklist: [MVP inventory](docs/MVP_INVENTORY.md). Independent reviewer instructions: [Copilot review handoff](docs/COPILOT_MVP_REVIEW.md). These describe the latest application; some older sections below record earlier iterations.


A responsive family gift registry built with React Bootstrap, Flask, MySQL, and Alembic.

## Development setup (Windows PowerShell)

Local development and Render use the same Railway MySQL database. Do not create a second local database or load demo data for this workflow. Existing local database data is left untouched and is no longer used by this setup.

1. Install Node.js 22.12+ and Python 3.12. A local MySQL server and Redis are not needed.
2. Keep the shared Railway connection in the root `.env` as `DATABASE_URL`. Local CORS stays `FRONTEND_ORIGIN=http://localhost:5173`; Render uses its public origin. Verified TLS uses `backend/certs/railway-mysql-ca.crt`.
3. Set up Python dependencies if needed:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r backend\requirements.txt
   ```

4. Install frontend packages with `npm.cmd install`.
5. Start both local processes:

   ```powershell
   npm.cmd run dev:all
   ```

The browser uses <http://localhost:5173>; the local API uses <http://localhost:5000>. The launcher automatically uses `.venv` Python. To start them separately, run `npm.cmd run dev:api` and `npm.cmd start` in separate terminals.

The local API and terminal migration commands read the project `.env` in preference to stale terminal variables. Local startup requires an explicit database URL and will not silently fall back to the old local database. Shared MySQL sessions and request limits are enabled in this computer's private `.env`.

Edits, registrations, wishes, and deletions made locally affect the same database records used by the deployed app. Automated tests still use isolated disposable databases. Uploaded files remain on the server receiving them; sharing MySQL does not by itself synchronize local uploads with Render's disk.

Use `npm.cmd run db:current` to inspect the shared migration revision and `npm.cmd run db:upgrade` to apply reviewed migrations. Do not run the local-only `schema.sql` bootstrap or fake `mysql.sql` demo inserts on this shared database. See [database commands](docs/DATABASE_COMMANDS.md).

## Family profiles and sharing

Households can be created with multiple people or pets, then maintained by a
household owner or administrator. Parents can add birthdays, clothing and shoe
sizes, favorite stores, cartoon avatars, and private photos. The household page
shows shared birthdays coming up in the next 30 days and dated occasions.
Creating an occasion for a profile also creates a wishlist for it; additional
custom wishlists can be created from that profile's page.

Pets can also be added from Settings with an optional photo. Their wishes stay
within the family by default; an owner can explicitly enable sharing with
invited shoppers for each pet. Family members, including child accounts, can
add and remove pet wishes without gaining permission to edit other members'
profiles or wishes. Custom-named wishlists (for example, "Stocking stuffers")
are available on profiles. Personal wishes can separately be shared with
followers, selected family accounts, the public, or kept private.

Household invitations share only the profiles selected by the parent. The app
can send invitation email when SMTP is configured; otherwise use the ready-to-send
email draft or copy the private invitation link. Purchase notifications are shown only to household owners and
administrators, never to the gift recipient.

If MySQL reports `Access denied for user 'gift_registry'@'localhost'`, run only
the following repair statements in MySQL Workbench as root; do not rerun the
full schema against an existing database:

```sql
CREATE USER IF NOT EXISTS 'gift_registry'@'localhost' IDENTIFIED BY 'gift_registry_dev';
ALTER USER 'gift_registry'@'localhost' IDENTIFIED BY 'gift_registry_dev';
GRANT ALL PRIVILEGES ON family_gifts.* TO 'gift_registry'@'localhost';
CREATE USER IF NOT EXISTS 'gift_registry'@'127.0.0.1' IDENTIFIED BY 'gift_registry_dev';
ALTER USER 'gift_registry'@'127.0.0.1' IDENTIFIED BY 'gift_registry_dev';
GRANT ALL PRIVILEGES ON family_gifts.* TO 'gift_registry'@'127.0.0.1';
```

These statements reset the development app password to `gift_registry_dev`;
use the same password in `DATABASE_URL` if you have a `.env` file.
Both seeded demo accounts use `GatherGiftDemo!2026`.
Sign in as `demo.parent@example.com` to administer the sample household or as
`demo.shopper@example.com` to try its shared gift list.

Load the fake sample family into your local MySQL database by running `mysql.sql`
in MySQL Workbench after selecting `family_gifts`. The command below is only for
Docker users:

```powershell
Get-Content -Raw .\mysql.sql | docker compose exec -T db sh -c 'mysql --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" "$MYSQL_DATABASE"'
```

## Family invitations

An owner/admin enters a person's exact email and selects the profile wishlists
to share. The private invitation link prompts the recipient to sign in or register
with that email, then automatically adds the shared household to their account. A shopper can only view the selected gift
lists and reserve items without revealing reservations to their recipients.
Configure `SMTP_HOST`, `SMTP_PORT` (default 587), `MAIL_FROM`, and optional
`SMTP_USERNAME` / `SMTP_PASSWORD` to deliver invitations. STARTTLS is enabled
by default (`SMTP_STARTTLS=true`). Without SMTP, the app offers an email draft
and copyable private link; delivery failures are shown with the same fallback.
Set `FRONTEND_ORIGIN` to the address invitees can open.

Household membership lists and relationship labels are restricted to household
parents/admins. Photos require authorized household or selected-profile access;
they are served with private, no-store caching. Invitations never embed photos.
Development hosting blocks direct access to the private instance/upload folders.

## Support staff

The master support account is created once by an authorized server operator.
From its separate `/support/login` portal, the master can create one-time
invitations for additional staff. There is no public staff registration page;
invitation links are shown only to the signed-in master, expire after three
days, and must be sent directly to the invitee. Email delivery is not configured.

```powershell
python -m flask --app backend create-superuser
```

Only the master can invite staff; invited staff cannot invite others. All support
accounts cannot sign into family routes or see any household by default. An
owner/admin must approve a support agent's access request before the agent can
inspect or edit approved profile information. Approval expires after one hour,
can be revoked early, and each support access/edit is audited. The support portal
also handles help/bug tickets and replies. The approved support view is not user
impersonation: staff can inspect wishlist items and active holds or release an
active hold, but cannot sign in as the customer or see purchase identities.
Support staff can also prepare a new family space at a person's request by
entering its name, a primary adult profile name, an optional birthday and photo,
and the invitee's email. The seven-day invitation is bound to that email. After
the person signs in or registers and accepts it, they become the household owner
and the prepared profile is linked to their account. Support staff do not retain
membership or access to the claimed family; this setup flow is audited and does
not replace owner-approved access to an existing family.

The frontend displays a loading state while the session is checked, offers a
retry if startup requests fail, and catches unexpected interface errors. Flask
returns JSON errors for unmatched routes and logs unexpected server exceptions.

## API overview

The API base path is `/api`. Route groups include `/auth/*`, `/households/*`,
`/invitations/*`, `/profiles/*`, `/wishlists/*`, `/items/*`, `/shopping`,
`/my-shopping`, `/budgets`, and `/support/*`. Protected routes require a server
session cookie. State-changing requests also require the session-bound CSRF
token from `/api/auth/csrf`.

## Tests

```powershell
.\.venv\Scripts\Activate.ps1
pytest
npm.cmd test
npm.cmd run build
```

## Render deployment

The deployment is packaged as one Render Docker Web Service: the multi-stage
root `Dockerfile` builds the React app and serves it from Flask alongside the
`/api` endpoints. This keeps the UI and API on one origin, so production login
cookies and CSRF requests do not depend on cross-origin browser settings.
`render.yaml` defines the service, health check, generated `SECRET_KEY`, and a
persistent disk for photos and advertising uploads. The Render pre-deploy command
applies Alembic migrations before starting Gunicorn; no Procfile or separate
Render Static Site is needed.

1. Push the project to GitHub. Do not commit `.env`; `.gitignore` and
   `.dockerignore` exclude it. Keep all provider credentials in Render's
   Environment settings.
2. In Render, create a Blueprint from the repository and review `render.yaml`.
   The Docker Web Service uses a paid Starter plan because Render persistent
   disks are not available on free web services.
3. Render has no managed MySQL, so the database lives on Railway (or any MySQL
   host). Create a MySQL database there and enable its public TCP proxy. Copy
   the connection URL into `DATABASE_URL` on the Render service. Use the public
   proxy host/port, not Railway's private hostname. The app accepts `mysql://`
   URLs and selects the PyMySQL driver. Keep the URL private. The database user
   needs permission to create/alter tables and indexes.
4. Sessions and request limits use Railway MySQL. No Redis service is needed.
5. Deploy and wait for `/ready` to pass. Render runs
   `flask --app backend db upgrade` in its pre-deploy stage before Gunicorn starts.
6. Create the master Developer & support login once from the Render Shell:

   ```sh
   flask --app backend create-superuser
   ```

   Enter the support email, display name, and a unique password of at least 16
   characters. Additional staff accounts are invited from that portal.
7. Configure optional provider settings only when ready: `SERPAPI_API_KEY` for
   live product search; SMTP variables for invitations and recovery emails;
   Stripe keys and campaign pricing only if enabling paid ads; and
   `AMAZON_ASSOCIATE_TAG` only after Amazon Associates approves the account.
   These backend credentials must never use a `VITE_` prefix.

Render sets `RENDER_EXTERNAL_URL`; the app uses it for invitation links and
same-origin CORS unless `FRONTEND_ORIGIN` is explicitly set. If you attach a
custom domain, set `FRONTEND_ORIGIN` to that exact HTTPS origin and redeploy.
The app serves the built UI and API from the same Render service, so leave
`VITE_API_BASE_URL` empty.

The persistent disk keeps profile photos, family photos, theme artwork, and
uploaded advertising creative across deploys. Configure a backup/export plan;
the disk is not a database backup. Your MySQL host's database needs its own backups and
retention plan. Verify registration, email delivery, photo uploads, migration
success, sign-in, and invitation acceptance on the deployed service before
inviting families. The deployment configuration does not configure live provider accounts, or send production email for you.

### Preview every email

    python -m flask --app backend sample-emails --to you@example.com

Writes each template to instance/email-previews (open the .html files). Add --send with SMTP variables set to deliver them for real.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for system design and
[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for implemented features and
remaining work.

## Gift discovery across stores

The Add a gift dialog supports Google, Google Shopping, Walmart, Target, Amazon,
Etsy, Best Buy, and eBay browsing. Choosing a store saves the gift idea with a
search link, without pasting a URL. These links open search results, not an exact product.

For in-app product results with a one-click **heart to save** action, set
`SERPAPI_API_KEY` in the backend `.env` and restart the backend. The server uses
[SerpApi Google Shopping](https://serpapi.com/google-shopping-api) to retrieve public
product titles, seller names, prices, thumbnails, and product links. Only the typed
search query is sent; family names and profiles are not sent. The key stays on the
server. Google product links can open a product comparison page rather than an
individual seller. Results currently use the US market and USD. Search requests
are limited to 20 per minute per client using the existing rate limiter.

Without a key, store/Google browsing remains available and the app explains that
live product results are unavailable. Provider failures show a retryable message;
the app does not generate fake listings. Prices should be checked at checkout.

## Wishlist and account settings

The five icon destinations are My wishes, Following, Discover, My gifting, and Settings. Navigation is at the bottom on phones and at the top on desktop. Following includes family requests and Games. Discover searches products and previews pasted links; hearts save product details automatically.

My gifting has Buying now and Saved for later tabs, with purchased gifts in a searchable Past gifts dialog. Hearts do not reserve quantity. Buying now creates a 24-hour reservation; release it, save for later, or mark purchased after checkout. Saved fully purchased items retain a gray SOLD overlay.

Personal wish audiences support selected accounts, family accounts, followers, public, or this account only. Custom-named profile wishlists are visible through the same family/profile access grants as the rest of that profile; they do not have a separate follower audience toggle. Joined adults use their own credentials and control their own wishes. Household lists retain their existing selected-profile invitation permissions. Adults sharing one login can access that login's private plans. Settings contains account details, notifications, family/child controls, invitations, appearance, and support.

## Password recovery

Family and support sign-in pages include **Forgot password?**. A configured SMTP
service sends a private link to choose a new password. Set `SMTP_HOST`,
`SMTP_PORT`, `MAIL_FROM`, and any required `SMTP_USERNAME` / `SMTP_PASSWORD`;
STARTTLS is enabled by default. `FRONTEND_ORIGIN` must be reachable by recipients.
Without mail configuration the app reports that recovery email is unavailable;
reset links are never returned in API responses or exposed as copyable drafts.

Reset links expire in 30 minutes, are single-use, and are stored only as hashes.
Requesting another link invalidates earlier links. Resetting a password revokes
existing sessions and requires a fresh login. Changing an email or password in
Settings also invalidates older recovery links and other sessions. The current
Settings session remains signed in after those changes. Invitation continuations
are preserved through recovery so invitees can resume accepting shared lists.

## Parent-managed child access

In the household settings gear, **Child wishlist access** lets a parent/admin
select an existing person profile, approve specific existing wishlists, and
create a username and password. Children do not need email addresses. The
supervising parent can change approved lists, reset the password, or disable
access. Changes revoke existing child sessions. Other adults cannot manage that
child's login unless they are its supervising parent.

Children sign in at `/child/login` and only see an add-only page for their
approved lists. They can add a gift name and short description. They cannot
create lists, edit or delete wishes, search people or stores, open product
links, see family photos, invite users, heart gifts, reserve gifts, buy,
change account details, or access notifications and support. Restrictions are
enforced by the backend as well as the interface. Direct adult API requests
from child sessions are blocked. Child-created wishes appear on the normal
family lists so parents can edit or remove them. If the supervising parent
loses permission to manage the profile, child access to its lists also stops.

## Account appearance

Settings offers built-in palettes and a shared theme catalog. The master developer can publish named seasonal/child artwork and font/background/accent colors. Personal background uploads are disabled. Child accounts can choose only published child/everyone themes. Shared artwork is stored once.

## Company and employee registries

The Home creation form offers **Company / workplace** as well as **Family
household**. Companies have a name/logo, employee profiles, employee wishlists,
workplace labels, and special days. Owners/admins manage employee profiles and
gifts; profiles do not require separate employee accounts. Workplace labels
(Employee, Colleague, Manager, Team member) describe profiles and do not grant
account permissions.

Companies use the existing private invitation flow to share specific employee
wishlists with signed-in gifters. Uninvited users cannot browse the company or
its employees, and invitees can only see the employee profiles selected for them.
Hearts, private plans, holds, co-buying, and purchases work through Wishlist.
Existing registries remain Family households. Child logins are only created in
Family households, not company registries.

## Manual gifts and registry previews

Gift forms support manual titles and shopping links, with store search available
in an expandable section. **Preview link image** reads public HTTPS metadata to
populate a preview image and an optional missing title/store name. An image URL
can be supplied manually when a retailer blocks previews. Link previews do not
require a shopping-search API key. They validate public DNS addresses, pin the
connection address, revalidate redirects, limit response sizes, and never fetch
private-network endpoints. Child sessions cannot request link previews.

Owners/admins can open **Preview registry** on a household or company page and
choose which people to include. This is a read-only illustration of selected
shared lists. Purchase actions are disabled, sample availability is used, and
private plans, parent notes, nonshared birthdays, and actual reservations are
excluded. It does not publish a registry or change invitation access.

## Wishes for me: selected-family sharing

Wishlist > **Wishes for me** is for things the account holder wants to receive,
such as jewelry. New wishes default to public within the eligible invited-family
audience; the owner can uncheck **Public to invited family members** to keep a
wish private to the current login, or choose a narrower audience. The audience
list does not include companies, support accounts, or child accounts. Household
owners/admins can select family members; invited family shoppers can share back
with household owners/admins without exposing the full family membership list.

Personal wishes are stored separately from normal family-profile wishlists and
from private plans for gifts the user is buying for others. Unselected family
members and unrelated accounts cannot see or reserve a personal wish. Selected
viewers can heart, reserve, co-buy, and purchase through
the existing gift flow. Owners do not see purchase or reservation details for
their own wishes. Removing a viewer cancels that viewer's active holds; removing
family membership also stops access. Existing private gift plans stay private to
their creator and are never automatically shared.

## Launch with SerpApi, add Amazon later

Set SERPAPI_API_KEY in the Render backend service Environment panel and redeploy. Local .env files are not copied to Render. Never use a VITE_ prefix for this secret. Search results can be selected in Add a wish, reviewed, and saved with the product link and image. SerpApi does not provide affiliate commissions.

Leave AMAZON_ASSOCIATE_TAG empty for testing. After approval for Amazon US Associates, set it on the backend to your tracking ID (for example, yourname-20) and redeploy. Shared and personal wishlist responses then tag direct HTTPS amazon.com links without modifying saved URLs. Other retailers, shortened amzn.to links, Google Shopping redirects, and other Amazon marketplaces are left unchanged. This does not enable Amazon catalog API access; that requires a separate future integration.

Before launch, verify registration, sign-in, invitation acceptance, uploads, and search against the deployed services. Prefer frontend and API custom domains on the same site (for example app.example.com and api.example.com) with the current SameSite=Lax session cookies. Separate unrelated domains need a deliberate cookie/CORS configuration and browser testing. Configure VITE_API_BASE_URL when building the frontend, FRONTEND_ORIGIN on the backend, and a static-site rewrite /* to /index.html for React routes. Set UPLOAD_FOLDER to an attached persistent disk path. SMTP settings are required for invitation delivery and password-reset emails.

## Adult family accounts and children

For an existing family, its creator adds an adult profile and uses **Edit profiles & family > Their own login > Invite to join family**. The adult signs in or registers with the invited email and accepts the link. This claims the invited profile for that adult; it does not transfer household ownership. Support may separately prepare a new family for an invitee, who becomes its owner only after accepting the email-bound setup invitation. Their login controls their wishes; another adult cannot impersonate them or edit/remove their gifts. Other adults can send suggestions, which the recipient approves into a chosen list or dismisses. Joined adults can add children's gifts, but only the family creator can edit/remove child gifts or change child profiles. Child mode remains add-only and PIN-locked, except that children can add and remove wishes on family pet profiles.

Approved family follow connections and viewing grants are inherited without another follow request. Selective grants remain selective; inherited access is removed when its family connection is removed. External people, families and companies still require their normal invitations. The latest migration adds shared allergy notes and favorite snacks: `e82c4b9510fa`. Run `flask --app backend db upgrade` before starting the updated backend. Pet and child lists have one sharing switch per list: Private keeps wishes in the family; Public permits existing approved viewers. Existing lists keep their previous sharing until changed. Pets are managed family members and never appear as login profiles. Family creators can remove managed members and pets in Settings without deleting their accounts or wishes.

Real join/recovery email needs SMTP. See [the current feature inventory](docs/MVP_INVENTORY.md) for page details and beta prerequisites.

## Main-email recovery codes

Forgot password uses a six-digit email code sent to the shared account main email, not a member contact email. Codes expire after ten minutes, lock after five incorrect attempts, and are stored hashed. A valid code unlocks a one-time password reset; password resets revoke existing sessions, including saved child-mode return sessions. Email changes require the current password and a code sent to the current main email, bound to the exact new address. Member contact emails never authorize account recovery.

Configure SMTP_HOST, SMTP_PORT (587), SMTP_USERNAME, SMTP_PASSWORD, MAIL_FROM, and SMTP_STARTTLS=true on the backend locally and on Render. Use credentials from your email delivery provider and its verified sender address. Missing SMTP configuration produces an explicit unavailable message; verification codes are never shown in the browser or logs.

## Advertising campaigns and Stripe Checkout

The public /advertise page accepts image/video file URLs, business/store links, keywords, home/wishlist placements, date range, weekdays, same-day time window, IANA timezone, and rotation length (5-120 seconds). Creative files must be hosted externally; file uploads are not implemented. Campaigns start pending review. The master support account can approve, reject, or pause them in Support > Advertising campaigns. Advertisers retain a private status/payment URL; keep that URL private.

Set these backend environment variables locally and in Render: STRIPE_SECRET_KEY (start with test mode), STRIPE_WEBHOOK_SECRET, ADS_DAILY_RATE_CENTS (your chosen USD cents per selected day per placement), and FRONTEND_ORIGIN. No Stripe publishable key is required for the hosted Checkout flow. Blank settings disable payment rather than simulate it. Rates exclude any tax calculation; configure the intended pricing/tax handling before accepting live payments.

Create a Stripe webhook destination at https://YOUR_API_HOST/api/ads/stripe-webhook for checkout.session.completed, checkout.session.async_payment_succeeded, charge.refunded, and charge.dispute.created. Set that destination signing secret as STRIPE_WEBHOOK_SECRET. For local testing, forward those events using Stripe CLI and use its local signing secret. Only signed events matching the saved session ID, campaign ID, amount, and USD currency can mark payment confirmed; the success redirect never fulfills a campaign. Duplicate delivery is safe. Use Stripe test mode to verify your account integration before switching to live keys.

Campaigns must be approved before payment. Approved paid campaigns appear only in their schedule and matching placement/keywords, with ad slots rechecking eligibility every 30 seconds. Billing uses selected weekdays in the inclusive date range times placements, at the quoted daily rate; narrower hours do not discount it. Rotations do not guarantee exclusive space or impressions. Ads do not appear in Settings or child mode. Refunds are arranged through the Stripe dashboard; refund/dispute events pause delivery. A checkout session that expires may need a new campaign submission.

## Store links and future affiliate accounts

Public HTTPS store/product links can be pasted or dropped in gift search. If a store refuses metadata requests, the app offers the original link with a title inferred from its URL; it does not invent an image or price. Internal/private network URLs remain blocked. Original saved URLs are retained. Direct Amazon US links use AMAZON_ASSOCIATE_TAG when configured. Other stores use optional STORE_AFFILIATE_RULES JSON on the backend, matched by exact domain (www is normalized). With no matching rule, links stay unchanged.

Examples (replace with the exact format supplied by your approved affiliate provider):

```env
STORE_AFFILIATE_RULES={"shop.example":{"query":{"partner":"YOUR_APPROVED_ID"}},"other.example":{"deeplink":"https://network.example/click?merchant=YOUR_MERCHANT_ID&url={url}"}}
```

The {url} placeholder is replaced with the encoded original product URL. Use only provider-issued tracking parameters/templates; these settings do not enroll you in programs or verify approval. Adding a rule later applies it to existing wishlist and private-plan links at read time. Search-result previews retain the original URL; saved shopping links receive affiliate tracking.

## Main-email approval for sensitive changes

Settings password changes and household photo replacements are pending requests, not immediate updates. The account main email (household owner email for photos) receives an approval link with Yes/No choices. The link expires after 30 minutes, is stored hashed, and is single-use. Opening it only displays the request; a separate confirmation POST applies it. Photo approvals show a protected preview of the proposed image. Cancellation, expiry, or missing/failed email delivery leaves the existing password/photo unchanged. New requests supersede older requests of the same kind. Pending passwords are stored only as password hashes. Approved password changes revoke existing sessions. A mailbox-proven forgot-password reset continues to work through its existing one-time-code flow.

## Gift exchange games

Open Following > Games, or create a game from My wishes. A family owner/admin creates Secret Santa or White Elephant, selects 2-50 eligible participants across connected families/individual registries with person/family/account search, and optionally sets a date and two-decimal USD budget. External invitees receive notifications and must join or decline before the host starts. Games do not grant access to another household or bypass wishlist sharing. Child sessions cannot open game routes; a parent can run the party and reveal an assignment for a child profile, without requiring that child to have a login.

Secret Santa shuffles participants into a no-self recipient cycle once. APIs never expose the full assignment map. Switch Browsing as to your participating profile to reveal your recipient. Parents may select their managed child where permitted. Adults sharing a login can switch adult profiles, so use separate logins when assignments must stay private from one another. Names are revealed in the app, not emailed.

White Elephant requires one wrapped gift per participant, added through product search or a pasted link. Details stay hidden until opened. The host starts a shuffled order and can operate turns for the group; non-hosts act only for their active participant on their turn. A turn opens an unopened gift or steals an eligible opened gift. The person losing a gift plays next. Immediate steal-back is blocked, each gift has a configurable 1-5 steal limit, and there is no final first-player swap. Every write checks the current version and locks the game row to reject stale actions. The game ends once everyone holds one gift. Games do not purchase or reserve wishlist items.

## Main adult identity and Settings quick actions

New family-household setup asks which entered member is the account creator, or adds a separate profile using the account name. That profile is linked to the shared login, marked adult and guardian, and selected for browsing. Login returns to a linked adult profile. Existing owners can use Settings > Family & profiles > This is me; a profile already linked to a child or other account cannot be claimed. The profile switcher marks the linked account as you and blocks switching into another adult with separate credentials. Household/member editing and parent PIN setup are in Settings quick actions; child sessions cannot enter those tools. Settings editing returns to the main account management context, while joined adults control their own wishes and only the family creator manages children.

Shopping search has optional minimum/maximum prices, a currency selector and a No budget action. With a budget, only known item prices in the chosen currency are included; shipping and tax are not included. Search can span all approved followed families and people. Wishlist owners can dismiss the optional price-range checklist and restore it in Settings. This preference is saved to the account and does not restrict wishlist prices or shopper filters.

Advertising inquiries from the landing page and Advertise page now enter the Developer & support portal. Campaign submissions create inbox entries too. The master developer can set a notification recipient name and email in Advertising notification email, confirm the code sent to that address, and toggle alerts. Pending or expired confirmations never replace an existing confirmed recipient. Portal records remain available if SMTP is unavailable or delivery fails. Configure SMTP_HOST, SMTP_PORT, SMTP_STARTTLS, MAIL_FROM and any SMTP credentials on the server; no live credentials are displayed in the portal. Apply migration `f73d8b26ae10` using `flask --app backend db upgrade` before starting the updated backend.
