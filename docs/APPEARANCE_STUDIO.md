# App colors and developer email testing

Sign in to `/support/login` with the master account. Open **Theme** for display mode, text size, separate light/dark palettes, the everyday preset and the Christmas preset. The inline card preview changes immediately as you edit colors. **Preview on this browser** temporarily applies the draft to the portal/app; **Clear preview** restores published colors. Leaving the editor clears a temporary preview. Browser dark-mode preference stays separate from the published palettes.

**Publish app colors** explicitly saves the two palettes and season. Other browsers receive them on reload. The server accepts only hex colors and checks text contrast against page/card backgrounds. Settings are stored in the existing SharedTheme JSON storage as an internal site-palette record, excluded from selectable artwork and letter designs. No new database migration is required. Existing account-selected artwork themes remain separate.

Open **Email control** for the template list, HTML blocks, fonts and colors. Enter your test recipient, then Send selected template or Send all templates and confirm. Existing suppression, SMTP configuration, delivery-mode and audit checks remain enforced. Website color changes do not silently recolor outgoing emails: each email template has its own design. No real emails were sent during implementation; regression tests use mocked delivery/outboxes.

The source includes richer pink/lavender light colors, plum dark colors and matching dark loading artwork. No settings were published to the shared database and nothing was pushed during this task.
