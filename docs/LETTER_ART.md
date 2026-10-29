# Letter art and one-time family unlocks

In Developer portal > Themes > Theme studio, choose **Wishlist letter art**. Set a name, artwork, colors, availability and **Free** or a USD price (for example 3.00). Published designs can be edited later, including price and availability. App themes remain separate and free. Letter art must target children or everyone.

In Settings > Profiles & account > Create a wishlist letter, parents can preview the catalog and select free designs or unlock paid designs. The built-in Classic magic design stays free. A successful purchase unlocks one design for one family, reusable across children and future letters. A free design used by a family also stays unlocked if its price increases later. Archived designs remain available to families that already unlocked them.

Paid designs use Stripe-hosted checkout. The server chooses the amount and currency; browser-supplied prices cannot grant access. The existing signed webhook at /api/ads/stripe-webhook now dispatches letter purchases as well as ads. Only a matching, paid checkout grants access. Returning to Settings does not by itself unlock art. The letter draft is kept in browser session storage for checkout return; the catalog can refresh payment confirmation. No child can start checkout or set paid art directly.

Refunds or disputes revoke future use of that paid unlock. Duplicate events are safe; late payment events cannot revive a refunded unlock or a deleted family. Existing saved letters retain their design. The family unlock stays with the family when account deletion transfers ownership; deleting the entire family cascades its purchase records. Shared developer artwork is retained for other families.

Developer portal > Money shows letter-art payments separately from advertising, including confirmed amounts and refunded/disputed records. Prices and availability remain in Theme studio.

Migration 1bc58d704a92 (parent 0a94e27c61bd) adds an optional letter theme reference and letter_art_purchase. Applied to the verified local database. Other environments require the migration before deploying this code. Existing shared themes default to app themes; existing letters keep their included design.

Payment setup uses STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET. The configured Stripe webhook must deliver checkout.session.completed, checkout.session.async_payment_succeeded, charge.refunded and charge.dispute.created to the existing endpoint. This follows Stripe fulfillment guidance: https://docs.stripe.com/checkout/fulfillment . Live checkout and real-money payment were not exercised during implementation. Tests use mocked Stripe responses and signed synthetic events.

Regression tests: backend/tests/test_letter_art.py, backend/tests/test_wishlist_letters.py, backend/tests/test_shared_themes.py, backend/tests/test_advertising.py, backend/tests/test_money.py; src/SharedThemes.test.jsx, src/LetterArtPicker.test.jsx, src/WishlistLetters.test.jsx, src/MoneyPanel.test.jsx, and src/App.test.jsx.


October 28 deployment update: pending checkouts paid after deletion now request a full Stripe refund with a stable idempotency key and retry on failure. Previously fulfilled designs are distinguished using one-way payment receipt hashes so deletion does not refund an already delivered purchase on a duplicate webhook. See [deployment guide](DEPLOYMENT.md). Live payment verification is still required before enabling payments.
