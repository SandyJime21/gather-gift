# Quick account switching

Open the profile dropdown and choose **Add account**. Sign in to an existing adult family or staff account using that account's email and password. Separate email addresses are supported. A staff member can also choose **Create a family account** with a different email and a new password; this always creates an ordinary family account, never a staff or superuser account. Switch to it and use the normal family setup flow.

Verified accounts appear under **Your accounts** in the same dropdown. Select one to switch to its family home or support portal. This is a real login to an account whose credentials you verified; it is separate from the read-only superuser diagnostic User view. Each login keeps its own identity and permissions. Ordinary support accounts still need customer permission to inspect customer data.

Up to five verified adult accounts are remembered within this server-side browser session. No passwords are stored in the switcher or localStorage. Logout clears every saved account. A different browser/device or a fresh login may require adding accounts again. Password/session revocation invalidates a saved entry, and staff privileges cannot be restored through an invalid entry. Child profiles cannot use the account switcher.

No schema migration or live account creation was performed during implementation. Automated tests create isolated family/staff accounts and verify switching, stale-session rejection, privilege separation and logout.
