# Manual wishes and child wishlist letters

In gift search, choose **Can't find it? Add manually**. A name is required; description, price, currency, store, and product link can be supplied without a search result. Existing destination and sharing selections still apply.

Under **Settings > Profiles & account > Create a wishlist letter**, the family creator chooses a sender (Santa or any name), list title, invitation date, and children they manage. Each selected child receives a separate family-only list. No child login setup is required to create the letter.

On or after the invitation date (America/Los_Angeles), opening the child profile shows a colorful letter dialog. **Write my wishlist** selects that letter's list. Children can search, paste a product link, or write a wish manually. They cannot change the sender, invitation date, recipients, or sharing. A child's session can access only that child's active letters.

Parents can edit or cancel each invitation. Cancelling removes the child invitation/access supplied by that letter but preserves its wishlist and saved wishes. These are in-app invitations; they do not send emails or messages to external recipients.

Database migration: 0a94e27c61bd (parent: f73d8b26ae10), adds wishlist_letter only. Applied to the local development database. Other environments need this migration before deploying the new backend.

Validation: backend/tests/test_wishlist_letters.py covers scheduling, parent-only management, sibling isolation, child profile switching without prior login creation, cancellation preserving wishes, and manual adult wishes. Frontend tests cover the parent form, child invitation selection/defer, manual entry, existing gift search, and App behavior.
