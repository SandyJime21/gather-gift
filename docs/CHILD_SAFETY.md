# Child access

October 28, 2026.

Children can view their parent-approved wishlists and add a wish by name and description. They cannot change sharing, edit profile information, manage accounts, purchase anything, access developer/support tools, view private gifting plans, or enter adult pages. Leaving locked child mode requires the parent PIN; PIN recovery requires confirmation sent to the parent's email.

Optional activities default to **off**, including existing child accounts with no saved approval. In Settings, open the child's Profile and expand **Child access · parent approval**:

- Search online for gifts (existing child-safe search).
- Add product links.
- View and edit family pet wishes.
- Switch to enabled sibling wishlists within the locked household session.
- See read-only family game invitations.

Only the supervising parent with profile editing permission can save these switches. Children and unrelated adults cannot grant themselves access. Permissions are checked again on every protected server request, including saving a previously returned search result. Revoking a permission blocks subsequent requests without requiring the child to log out. It does not erase information already displayed in an open browser; reload updates the visible controls.

Sibling access does not grant adult access. With sibling switching disabled, the child sees only their current profile in the locked household chooser. Separate legacy child sign-ins cannot switch siblings. Parents still choose list sharing and which lists the child can access. Optional permissions never grant billing, account deletion, public discovery, or developer access.

Implementation: parent-owned child permission map stored in the existing account JSON settings; no database migration required. Notification preference editing preserves this map and cannot write its keys. Ownership transfer starts with optional permissions off for the new supervising parent unless that parent has separately granted access.

Verification: default-deny API requests, permission validation, unauthorized changes, approval/revocation, cached search-result rejection, manual wishes, enabled links/search/pet flows, locked sibling switching, game restrictions, and parent PIN recovery are covered by backend regressions. Parent permission switches and child UI are covered by frontend tests. This is an access-control implementation, not a legal compliance certification or a guarantee that third-party online results contain only suitable content.
