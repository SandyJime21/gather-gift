# Gather & Gift: complete MVP action inventory

**Current review:** [release readiness](RELEASE_READINESS.md) and [deployment guide](DEPLOYMENT.md). Later additions include profile/list separation, manual and online favorites, letter previews and family art unlocks, account deletion/export/ownership transfer, and [parent-approved child activities](CHILD_SAFETY.md). Test counts and runtime limitations in the historical verdict below are superseded.

Reviewed October 27, 2026. Replaces the older October 25/26 inventory. This describes current source and reachable UI, not a certification of the deployed app.

## MVP verdict

The main feature set is implemented, but release acceptance is incomplete. 123 frontend tests pass and the production build passes. Backend tests, real migrations, MySQL concurrency, browser/device flows, SMTP and enabled payment/search integrations still need verification. See [MVP_READINESS.md](MVP_READINESS.md).

The app saves wishes from different stores, shares them with family and friends, and helps shoppers choose what people actually want. Ordinary gift purchases happen at retailers; the app coordinates lists and shopping, not retail checkout.

## Roles and boundaries

| Role | Abilities | Limits |
| --- | --- | --- |
| Visitor | Landing page, registration/sign-in, recovery, opted-in public wish preview, advertising requests/campaigns, help/install instructions. | No private family profiles, lists, images or addresses. |
| Family creator / permitted administrator | Create a family, edit permitted family details, add managed people/pets, invite members, manage dependent lists, approve support access. | Separate adult accounts/wishes remain theirs. Sharing one password cannot isolate adults using that login. |
| Joined adult | Own login linked to the family; own wishes; inherited permitted family connections; add permitted child wishes; suggest gifts to adults. | Cannot impersonate another adult or silently change their wishes. Creator restrictions apply to child editing/removal. |
| Approved follower / shopper | Permitted shared people/lists, gift search, hearts, holds, purchases, eligible co-buy/games. | Following is not administration. List Public means approved viewers here, not the anonymous public-wish audience. |
| Managed child / pet | Family-managed profile, wishes and preferences; no separate account required. | Parents manage details/privacy. Pets cannot sign in. Normal child screens do not contain account creation/password reset controls. |
| Legacy child session | Existing restricted child-login, sibling-switching and PIN APIs remain for compatibility; own wish additions, permitted pet wishes and read-only game notices. | No adult shopping/settings/family-search/advertising/staff APIs. Direct-API tests remain necessary despite removed setup UI. |
| Support staff | Separate staff login, assigned tickets, family setup assistance, customer-approved temporary troubleshooting. | No general customer impersonation or master money/accounts/publishing/advertising controls. |
| Master developer | Staff abilities plus assignments/invites, account overview, money/Stripe overview, ads inbox/review/email settings, publishing and chat review. | Private bootstrap, not public registration. Overview tools are not retail payment/payout/account-deletion tools. |

## Public entry, accounts and header

1. Read the short landing page: wishes across stores, sharing, linked adult sign-ins, registries and exchanges. Search/social descriptions match.
2. Register, sign in/out, and use the main sign-in password visibility control.
3. Preserve invitation destinations through registration/sign-in; reject invalid/expired/replaced links.
4. Recover access using account-email codes/reset tokens and a new password. Codes/tokens expire and are single-use; SMTP is required.
5. Edit account name. Change account email using current password; change password using old password. Current settings do not require legacy email-change approval codes.
6. Invalidate older sessions when sensitive credentials change; independently verify session-version handling.
7. Navigate My wishes, Following, Discover, My gifting and Settings on desktop/mobile; support legacy URL redirects.
8. Show only the active identity's own header photo or initial; never use a family/other-person photo. Failed photos fall back to initials.
9. Open Buying now from the header bag and see active-hold count.
10. Open the notification bell, handle pending requests and follow relevant links.
11. Download opens the current web-app install prompt or laptop/iPad Home Screen instructions. Manifest/icons are included; App Store and Microsoft Store downloads are planned for later, not live. No offline list mode is implemented.

## Families, people and pets

12. Create family or existing company/workplace registries.
13. Edit permitted family names/photos and profiles. Family photo upload is a direct authorized change in current code; older email-approval descriptions are stale.
14. Add people, assign relationships/birthdays, and identify which existing adult profile is you.
15. Invite an adult by email to join with separate credentials and claim the existing family profile using the invited email.
16. Preserve selective grants/inherited follows on joining; revoke inherited access when the membership/connection ends.
17. Invite outside family/friends to selected profiles; manage requests/revocation without granting administration.
18. Remove a permitted member/pet from the family. Access is removed; account/wish records are retained, not a full data-deletion workflow.
19. Show all people, including you first, in one family row; pets in a smaller separate row. Long rows scroll.
20. Add a pet with optional cropped photo and manage its wishes without human login controls.
21. Crop/upload supported photos or choose built-in/published cartoons; prevent later saves reverting a real photo to a cartoon.
22. Store month/day birthdays and optionally share with permitted viewers; normalize legacy full dates.
23. Open authorized family/person/pet pages, occasions and everyday/special-event lists.

## Gift profiles and completion

24. Save brands, stores, colors, snacks/treats, current interests, characters, hobbies, clothing/shoe sizes and gift preferences.
25. Save allergy/sensitivity notes. Blank means not provided; an explicit None known counts as supplied information.
26. Show gift guides on permitted profiles/cards. Sizes, colors, snacks, brands, stores and allergies are visible directly; compact cards expand other interests/ideas.
27. Exclude private parent/avoidance notes. Card preferences require profile access, not merely access to an unrelated public wish.
28. Show percent, progress bar, completed count and missing-details checklist. No supplied checklist details means 0%; a name/default cartoon alone does not complete it.
29. Update progress while editing and after photo upload/save.
30. In Discover, prompt favorite brands/stores and provide Complete/Edit gift profile actions.
31. Send in-app completion reminders only to allowed editors; open the correct editor; remove reminders when complete.
32. Use shorter child checklists and current favorites such as Minnie Mouse, painting and pink; collapse optional extra characters/brands/stores.
33. Use a shorter pet treats/toys/activities/allergies version without human sizes. Parents/authorized creators manage both versions.

## Wishlists and wishes

34. Create everyday/named occasion lists; use birthday, Christmas, wedding, baby-shower and anniversary presets or custom names/dates.
35. Manage lists: select a permitted member/list, rename it, edit optional address or open it to edit wishes.
36. Save search results, paste retailer links or manually enter gifts; review details rather than invent missing product data.
37. Save gift title, description, store/link/image, estimated price/currency, quantity, priority, desired size/color, category and notes where supported.
38. Save multiple products without leaving search; detect existing links and allow permitted undo/remove.
39. Reuse gifts across lists/occasions with one shared availability/reservation state.
40. Move/copy between permitted lists; holds/purchases constrain moves; copies omit reservation history.
41. Mark received using organize; avoid duplicate purchase history and release open holds.
42. Delete permitted wishes; do not edit/remove another separately linked adult's wishes.
43. Suggest gifts to joined adults; they choose a list and accept before an item is added, or dismiss it.
44. Group/search My wishes by occasion.
45. Choose personal-wish audiences: private-to-login, family, followers, selected eligible people or opted-in public. These differ from profile-list sharing.
46. Use one child/pet list toggle: Private is family-only; Public permits approved viewers. New managed occasion lists default private; unset legacy flags retain compatibility until changed.
47. Hide private list names/addresses from external viewers and release holds from shoppers losing access. A reused item on another shared list can remain visible there.
48. Preview invited-shopper visibility. Preview now respects list-level sharing; backend regression verification remains required.
49. Show optional price-range ideas: under 25, 25-49.99, 50-99.99, 100+ in the relevant currency. No range is mandatory.
50. Disable/restore price-range suggestions account-wide in Settings without limiting expensive wishes or shopper filters.

## Following and Discover

51. Browse followed families and permitted gifts by occasion.
52. Search adults/families by supported names or exact email with permitted preview results/photos; do not index child names as adult results.
53. Send/accept/decline/revoke follow/invitation requests. Joining a family is distinct from following an outside family.
54. Preview only explicitly public personal wishes before approval; anonymous previews are separate from private grants.
55. Search shared gifts across followed people by gift/person/store/family/occasion, subject to server/client matching.
56. Filter optional min/max price/currency, use presets, priority/price/recent sorts, held/hearted and occasion filters.
57. Budget results require known prices in that currency within inclusive bounds. Unknown/other-currency items are excluded; shipping/tax are extra.
58. Clear budget to show all prices/unpriced gifts; numeric product names are not automatically budgets.
59. Rotate top choices across people without hiding all their other gifts.
60. Discover: search products, paste links, save for yourself/dependents, suggest to adults or keep private gift ideas.
61. Browse simple saved/personal/shared-wish recommendations separately from labeled sponsorships.
62. Browse illustrated inspiration/treat categories. They seed searches, not guarantees of stock, allergen suitability or delivered prices.
63. Use retailer/Google/manual fallback when live search is unconfigured or metadata blocked.
64. Compare listed similar offers where available; not a guaranteed identical product, universal lowest price or automatic allergy filter.

## Shopping and purchase coordination

65. Heart shared gifts into private Saved for later without reserving quantity.
66. Unheart/undo without deleting the recipient's wish or cancelling unrelated holds.
67. Buying now reserves quantity while the shopper uses external retailer checkout.
68. Show availability/ON HOLD/SOLD; reject conflicting reservations using item locking. MySQL concurrency remains unverified.
69. Expire open holds after 24 hours on app activity; no independent real-time expiry worker.
70. Release/remove a hold, or Save for later while releasing it and keeping a private heart.

71. Record a purchase after returning from the store, shipping/in-person/undecided, and buyer secrecy.
72. Hide secret buyer identity/private notes from recipients; recipients may still see quantity/availability.
73. Search/filter purchased gifts/completed private ideas in Past gifts, separate from active Buying now.
74. Show SOLD on gifts bought by someone else; do not offer unavailable quantities.
75. Watch held gifts for availability and notify when released/expired.
76. Invite eligible co-buyers with percentages capped at 100% total; accept/decline with limited purchase rights.
77. Control in-app/email co-buy notices separately. Percentages coordinate people; the app does not collect/split contributions.
78. Add optional list addresses, private until shared with authorized viewers; copy into retailer checkout.
79. Revoke address/list access immediately, including reused gifts on private/shared lists. Children cannot use address endpoints.
80. Keep private histories/gift plans separate from recipient wishlists.
81. Backend private-budget storage APIs remain; do not claim a complete budget-ledger/totals UI. Main shopper budgets are optional price filters.

## Gift exchanges

82. Create Secret Santa, White Elephant or a custom-named exchange using either rule set.
83. Select eligible families/participants without granting new wishlist access.
84. Invite adults; join/decline/leave as supported; organizers start/cancel with eligibility/version checks.
85. Draw Secret Santa without self-draws and reveal only permitted assignments. Restart/leave/secrecy need backend/live verification.
86. Add wrapped gifts and run White Elephant turn/open/steal actions with shuffled order, steal limits and stale-version checks.
87. Show child game notices read-only and allow own notice-read updates without adult game rights/child email.

## Settings, help and display

88. Edit accounts/families/profiles and notification categories, including independent email options where available.
89. Review suggestions, follows, purchases, expiry, availability, games, co-buy and profile reminders with the relevant read/review action.
90. Choose classic/Christmas/Halloween/shared themes. Adults control settings; child mode stays restricted.
91. Use dark mode and 100/115/130/150% text, persisted on that browser. Not cross-device sync or accessibility certification.
92. Search the keyword help index and follow page links. It is not an LLM or a search of private records.
93. Store signed-in help questions/generated responses; do not log guest searches in this flow.
94. Escalate recent signed-in help chat plus optional note into a ticket. Follow replies in Help & support; escalation does not itself send an automatic email reply.
95. Open bug/help/feedback tickets and read own conversations/statuses.
96. Approve/deny/revoke staff support access and inspect household audit history.

## Developer & support portal: detailed actions

At /support, with separate /support/login authentication. Desktop side menu/mobile Portal section selector. Standard staff and the master see different controls.

97. Bootstrap the first master through the private create-superuser CLI. It refuses a second bootstrap and requires a long password. Do not create real accounts in the review.
98. Use a support session, not an impersonated family login.
99. Tickets: master sees all; ordinary staff see assigned tickets only.
100. Read requester name/email, category, opened/updated times, status and messages.
101. Master assigns/unassigns staff. Permitted staff/master reply and change open/in-progress/resolved/closed status. Customers see their own conversations only.
102. Support access/debug/feedback: request household access by ID/reason; wait for owner/admin consent; inspect approved temporary snapshots/grants; troubleshoot permitted holds/profile edits; stop at expiry/revocation.
103. Grants last one hour. UI profile editing focuses on names; the API has a limited field set. Independently review whether household-owner consent covers a separately linked adult's private data.
104. View request/grant queues and audits without leaking buyer identities.
105. From eligible tickets, inspect login-merge candidates and perform an explicitly confirmed merge. Review agreement, ownership/membership/session changes and audits; never merge real accounts during review.
106. Family & invites: prepare a requested family/profile, optional birthday/photo, and a private setup invitation. The invitee becomes owner on acceptance; setup does not retain permanent staff access to the claimed family.
107. Master creates private support-staff invitations, copies/sends links and checks pending invitations. Expiring/single-use; no public staff registration.
108. Money & Stripe: inspect configuration flags, test/live/unknown mode, reachability and read-only available/pending balances. Opening this with real keys can call Stripe; avoid that in isolated review.
109. See campaign review/payment totals, contact and payment-intent references. Current totals use the latest 200 campaigns, not a certified lifetime ledger.
110. Inspect affiliate tagging status and retailer earnings-dashboard links; commissions/payouts are not imported or processed by this app.
111. User accounts: master-only name/email search, types, joined dates and account count; displayed results capped at 200. Not an impersonation/deletion tool.
112. Theme: publish shared names/audiences/colors/optional art using a shared catalog.
113. Profile pictures & cartoons: publish named image choices and inspect the shared catalog.
114. Advertising: automatically see inquiry/campaign records, new counts, contact/business/message/time/delivery status; mark new/reviewed/closed and open linked campaign reviews.
115. Set advertising notification recipient name/email. Send a six-digit code to that address and confirm before enabling alerts. Hashed, expiring after 10 minutes, single-use, session-bound, attempt/rate limited.
116. Keep the old confirmed recipient until a replacement is confirmed; never alert a pending address. Disable/re-enable alerts. SMTP must be configured on the server.
117. Retain advertising requests when SMTP is missing or delivery fails and show delivery state. No background retry worker or browser push.
118. Preserve advertising email-link destinations through staff sign-in; select Advertising and focus the matching request.
119. Review creative/business/contact/schedule/timezone/keywords/frozen price; approve/reject/pause campaigns. Review marks linked new inbox entries reviewed; approval does not charge automatically.
120. Assistant chats: master-only recent signed-in conversations grouped by customer, names/emails/messages/times, 30-day retrieval window and row caps. Cleanup is activity-driven; client-generated answers are not trusted server decisions.

## Advertiser actions

121. Submit a name/email/business/message inquiry from landing or Advertise; store it in the developer inbox instead of opening the visitor's email app.
122. Submit supported image/video uploads or hosted HTTPS creative, placements, schedule, keywords and rotation length.
123. Review per-placement/day pricing. Server placement keys remain home/wishlist/discover; some labels use old page names, so verify actual placement wiring.
124. Retain a private campaign-status/payment link without exposing its token publicly.
125. Pay via Stripe only after approval and valid pricing; signed/validated webhook, not return-page navigation, marks paid.
126. Display approved/paid/scheduled labeled ads with keyword/general matching and controlled video playback; none in Settings/child mode.
127. Protect pending/unpaid media; pause stops eligible public serving. Media quotas/persistence/retention remain operational requirements.

## Backend/deployment and deliberate limits

128. Flask cookie sessions, CSRF, role/object checks, password hashing and rate limits need independent adversarial verification, not just hidden UI controls.
129. MySQL/SQLAlchemy/Alembic, local filesystem sessions or production Redis sessions/rate limiting; /health for deployment checks.
130. Docker builds SPA/API, applies Alembic at startup and serves bundled frontend/API. Separate frontend hosting requires appropriate origins/cookies.
131. Persistent uploads and server-held SerpApi/SMTP/Stripe/affiliate configuration; never expose secrets in frontend output.
132. Review every declared [API route](MVP_API_ROUTES.md), including compatibility, recovery, company and private-budget endpoints not all exposed by the main UI.

Not implemented/certified: retailer checkout/purchase verification, co-buy money collection, shipping tracking, hidden-address fulfillment, gift-card affiliate integration, subscriptions/storage plans, browser push/SMS, offline list editing, an LLM assistant, automatic media retention, arbitrary game rules, full account deletion or formal security/accessibility certification.

## Copilot review files

- [Email control](EMAIL_CONTROL.md): master-only previews and self-addressed tests of all current templates, plus address-wide unsubscribe management and signed recipient preferences links.

Local update: Gift games can be saved with one starting player, then invite adults by name/family search or email. Email links support signup/sign-in and preserve the invitation. Joining the game and allowing the organizer to follow the recipient are separate required Yes/No choices. Follow approval shares only the recipient's own adult profile, never their children or pets. Links expire after seven days and cannot be reused after responding or withdrawal. Only hosts can see pending email addresses and withdraw invitations; pending invitations block starting. Failed email delivery is reported and does not block the game. SMTP must be configured for delivery; SMS is not implemented.

- [Readiness report](MVP_READINESS.md): verdict, audit fixes and remaining acceptance gates.
- [Copilot prompt](COPILOT_MVP_REVIEW.md): independent review and acceptance checklist.
- [API route catalog](MVP_API_ROUTES.md): declared routes, source handlers and guards.
- [Validation summary](MVP_VALIDATION.json) and [frontend raw results](mvp-frontend-results.json). Older backend counts are historical, not a current pass.
