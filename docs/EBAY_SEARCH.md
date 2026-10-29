# eBay product search setup

The integration uses eBay Browse API item search and an OAuth **application token** (client credentials grant). Shoppers do not connect their personal eBay accounts. This integration does not sell, bid, order or check out on anyone's behalf.

1. Open eBay Developer → Application Keys → Production.
2. Put App ID in `EBAY_CLIENT_ID` and Cert ID in `EBAY_CLIENT_SECRET` in the ignored `.env`. Never paste keys into chat or use a `VITE_` prefix.
3. Use `EBAY_ENVIRONMENT=production` and `EBAY_MARKETPLACE_ID=EBAY_US` for US listings. Sandbox keys are for local testing only; production refuses sandbox listings.
4. Run `npm run ebay:check` from the project terminal. The command makes a read-only public product query and reports the result count without displaying credentials. If Python is not on PATH, set PowerShell `$env:PYTHON=(Resolve-Path '.venv/Scripts/python.exe').Path` first.
5. Resolve any keyset activation or Browse API production-access requirements shown in your eBay developer account. Having keys does not guarantee every API permission is approved.
6. When ready, put those same values in Render → Gather Gift → Environment. Changing local `.env` does not configure Render. Push code only with the owner's authorization.

Adult Find gifts, recommendations and price comparison use eBay first when both keys are configured, then the existing SerpApi provider if eBay fails or returns no items. Without eBay keys, existing search keeps working. Results include fixed-price product links, images and available price/currency data. These are listed estimates; shipping, tax and checkout totals may differ.

The eBay integration is excluded entirely from child-mode search. Parent-approved child search continues using the existing child-safe provider and excludes Amazon listings. No family/profile identifiers are sent in eBay requests; only the typed product query is sent.

Tokens stay in server memory, are reused until shortly before expiry, and are refreshed once after an HTTP 401. Secrets and tokens are never included in frontend responses. A configured optional `EBAY_AFFILIATE_CAMPAIGN_ID` requests eBay Partner Network links; developer keys and affiliate approval are separate. Until approved, leave that setting blank and regular product links work.

References: [eBay authorization](https://developer.ebay.com/develop/guides/sell/authorization), [Browse API](https://developer.ebay.com/develop/api/buy/browse_api), [eBay Partner Network](https://partnernetwork.ebay.com/).

# Target verification

The homepage HTML includes the provided passive Impact site-verification meta tag. After deployment, use Impact's **Pasting code** verification method with `https://gather-gift.onrender.com`. This verifies site ownership only; it does not activate Target catalog API access or install automatic link conversion scripts.
