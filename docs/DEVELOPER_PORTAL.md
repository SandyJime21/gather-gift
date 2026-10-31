# Developer and support portal: review inventory

Entry: `/support/login`, then `/support`. Staff accounts remain separate from family accounts. Navigation uses a left sidebar on larger screens and an expandable vertical menu on phones. No horizontal tab rail is needed. Related tickets and customer diagnostics share one workspace; the diagnostic entry form no longer appears again in User accounts.

| Area | Purpose | Role |
| --- | --- | --- |
| Support workspace | Read tickets, reply, change status, inspect linked household IDs, prepare access from a ticket, and merge eligible separate adult logins after confirmation. Superusers can assign tickets. Expand Customer access & diagnostic view for access requests, grants and snapshots. | Staff: assigned tickets and approved access; superuser: all tickets and audited direct read-only diagnostic sessions |
| Family & staff invitations | Prepare a family and email invitation for its future owner. Superusers also invite support staff. Creating a family does not grant ongoing staff access. | Staff; staff invitations superuser only |
| Activity & diagnostics | Recent permission-filtered support audit events and guidance on operational error logs. | Staff; existing server permissions apply |
| Affiliate Management | Add companies, approved merchant templates and server credential references; check provider status, failures and recorded outbound activity. Unknown APIs are not automatically implemented. | Superuser |
| Money & Stripe | Existing payment and financial administration. | Superuser |
| Advertising | Review advertising applications. | Superuser |
| Themes & list artwork | Personal display preview, site light/dark palettes, seasonal themes, letter art and family list backgrounds. | Superuser |
| Profile artwork | Manage shared profile pictures and cartoons. | Superuser |
| Email control | Edit templates and HTML blocks, preview, send selected test templates to an entered email, review delivery and suppression controls. | Superuser |
| Assistant chats | Review existing assistant conversation logs. | Superuser |
| User accounts | Search and administer account records. Customer diagnostic entry lives in Support workspace. | Superuser |

## Error log boundaries

The portal audit log records support actions; it is not a crash log. Gunicorn/Flask exceptions, readiness failures and deploy output are in the Render web service logs. Database service errors are in Railway logs. Affiliate failures/status stay in Affiliate Management, email failures in Email control, and assistant conversations in Assistant chats. A consolidated backend exception collector is not implemented; do not claim these raw server logs are available in the portal.

## Copilot review checklist

- Check sidebar and content at 320px, 390px, iPad and desktop widths; long emails, URLs and tables must not widen the entire page. Wide data tables may scroll within their own container.
- Check the mobile menu opens and closes, the active destination is marked, and each tool has one navigation destination.
- Check ticket access actions prefill the diagnostic/access form inside Support workspace. Ordinary support still requires an owner grant; superuser direct diagnostics remain read-only, time-limited and audited.
- Verify backend authorization independently of hidden navigation. Regular staff must not gain superuser endpoints or access to unassigned tickets.
- Confirm email tests require an intentional send action, private keys never appear in public templates, and pending affiliates leave ordinary links usable.
- Test palette preview/publish and uploaded list artwork without changing other adults' ownership or follower visibility rules.
- Run focused frontend tests and production build. Do not apply pending migrations to the shared Railway database before deploying their matching release.

This navigation cleanup does not migrate the database, send emails or deploy changes.
