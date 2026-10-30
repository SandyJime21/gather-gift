# Store suggestions, icons and affiliate ordering

The public store catalog is [src/data/affiliate-stores.json](../src/data/affiliate-stores.json). No credentials belong in this file. All stores currently have `affiliate_approved: false`, reflecting the owner's confirmation that no program has approved the app yet. Verification alone is not affiliate approval.

Each store has a display name, website domain, search URL and approval flag. Optional `logo_url` can point to an approved public HTTPS store logo. Without that field, known stores use Google's favicon service for a website icon. If an image fails, an initial appears. These are website icons rather than downloaded full brand-logo artwork.

Favorite store names remain saved in the profile as before. Matching a known name or domain supplies its icon every time the profile is opened. For a custom store, add its correct domain or approved logo URL to the catalog; the app does not guess a domain or automatically save an unverified Google Images result. Manual favorite names still work and count toward profile completion.

When a program actually approves the app, set only that store's `affiliate_approved` to `true`. Store browsing, matching favorite-store suggestions and displayed product results put approved stores first. Non-partner stores remain available. The flag orders suggestions; it does not create tracking links or grant API access. Keep actual affiliate link rules in the existing server configuration and provider integrations.

Brands and stores remain separate: Nike is an example brand, and Target is an example store. This preserves useful gift preferences without assuming every retailer is a product brand.

# Gift editing and ownership

Manual gift entry asks for a name, optional estimate and link; additional notes, store and currency are under More details. Save & add another keeps the entry open for rapid additions. Edit gift opens the same details editor, preserving photos unless a separate photo action changes them.

Compact gift rows show the item image, name, person, store and saved estimate. Click the image or name for the full notes and shopping details. Owners and authorized managers get edit/remove actions. Unclaimed adult profiles can be managed by authorized family managers; claiming an adult profile retains their own edit control, with gift suggestions available to family members for the adult to approve.
