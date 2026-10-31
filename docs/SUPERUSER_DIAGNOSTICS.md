# Superuser diagnostic view

Sign in at `/support/login` with the existing master account. Open **Accounts**, then **User view**. Enter an existing adult family account's email and a testing reason (10-1,000 characters). This opens the actual family interface using that account's normal permissions.

Only a support account with `is_superuser=true` can start this view without customer approval. Regular staff cannot use that endpoint and still require the existing customer-approved, one-hour grant to inspect a support snapshot. Family users cannot use either staff entry point. No account is promoted or given new permissions by this feature.

The diagnostic view is read-only, expires after 30 minutes, and displays a persistent **Support view** banner. Creation, edits, purchases, messages, PIN/password changes and other POST/PATCH/DELETE actions are blocked by the server while viewing. End the view to return to the original staff identity. Target accounts, permissions and credentials are not changed. Direct child-account impersonation is not provided: use the parent's existing family views to inspect managed profiles.

Start, end and data reads are audited under the original master account with the target ID and testing reason. Staff session-version and role changes invalidate the view; expiry restores the original staff account only if it is still valid. A normal customer never receives staff credentials or a reusable impersonation link.

No migration is required for diagnostics; it reuses server-side sessions and audit logs. This feature has not been pushed or deployed. No real account was impersonated during implementation: automated tests use isolated accounts and databases.

## Tickets and customer lookup

On a ticket, the impersonation/access action fills the requester email, household ID and a reason containing the ticket number and subject. Regular staff see the owner-approval request form; superusers see the direct diagnostic entry form instead. Preparing a form does not send an approval request or start impersonation automatically.

Superusers can also search adult family accounts by name or email from User view. Select user fills the email; Impersonate opens that user's read-only interface with the entered reason or an audited diagnostic reason. Ordinary staff cannot use the customer-search or direct-diagnostic endpoints. Customer consent is still required for their approved support snapshots.
