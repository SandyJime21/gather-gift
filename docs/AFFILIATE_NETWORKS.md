# Network adapters and access — checked October 30, 2026

No partnership approval has been confirmed. Target was rejected, per the owner. Every monetization provider starts disabled and unapproved. A credential is not proof of merchant approval. No accounts were registered, paid services added, or live affiliate calls made during implementation tests.

| Network | Official capabilities and authorization | This MVP |
| --- | --- | --- |
| [Sovrn Commerce](https://developer.sovrn.com/reference/link) | Link Check takes the campaign/site Commerce key and a URL; returns an eligibility flag and optimized link. [Campaign approval is required](https://knowledge.sovrn.com/kb/api-onboarding-guide-for-commerce). Other product/price comparison and reporting services have separate access. | Link Check adapter implemented, subject to credentials, approval and explicit merchant rules. Optimization is off to preserve the selected merchant. Rejects unsafe destinations and any returned link containing the configured key; requires an opaque credential-free issued link. Otherwise uses original URL. Product search and reporting not connected. |
| [Awin](https://help.awin.com/apidocs/introduction-to-awins-apis) | Publisher APIs include Link Builder, offers and performance; most use a UI-issued bearer token. [Feeds](https://help.awin.com/developers/docs/product-feed-publisher-guide-intro) require publisher/advertiser access. | Approved public tracking-template adapter prepared. Automated Link Builder, feed ingestion and reporting require further development and account access. |
| [Impact](https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/tracking/tracking-links/create-and-manage-links/create-tracking-links) | Tracking links are available after partnering with a brand. Partner API authentication uses the account SID and auth token. [Catalog access](https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/marketing-content/product-marketplace-and-catalogs/download-product-catalogs-as-a-partner) depends on brand permissions. | Approved issued link templates supported. Partner API link generation, catalog ingestion and reporting pending. Site verification does not mean Target approval. |
| [CJ](https://docs.cj.com/docs/productfeed-api-search) | Product-feed GraphQL uses a personal access token, company ID and publisher website PID for links. Scope depends on account and advertiser permissions. | Approved issued link templates supported; GraphQL search, advertiser lookup and commission reporting pending development/access. |
| [Rakuten Advertising](https://developers.rakutenadvertising.com/guides/deep_link) | Deep Links API requires an approved advertiser supporting deep links and a bearer token. Other APIs cover advertisers, product search and reporting. | Approved issued link templates supported; token/API integration and reporting pending. |
| [Skimlinks](https://developers.skimlinks.com/) | Merchant API, Link Wrapper, Reporting API and product services have separate documentation and access. Merchant API uses client credentials for an access token. Publisher/site approval is required. | Evaluated as an alternative to Sovrn; approved issued link templates supported. Authenticated merchant/product/reporting adapters pending. Do not enable overlapping automatic wrappers. |

Sovrn documentation sometimes uses a site key inside a public tracking URL. This implementation deliberately refuses to expose the configured API key in any redirect. If the account's API only returns key-bearing links, automatic Sovrn monetization will fall back to direct links until an approved credential-free link format is available. It will not fake a successful integration or silently relax this rule.

## Common adapter contract

`checkMerchantEligibility`, `searchProducts`, `getProductDetails`, `generateAffiliateLink`, `getMerchantInformation`, and `getAvailableReporting` exist with explicit capability flags. Unsupported methods return an unsupported state, not products, conversions or revenue. Network-level documented capabilities are shown separately from methods implemented in this app.

The manual-template adapters accept **issued public tracking templates**, approved merchant domains and exclusions. They are not automated network API adapters. Templates need exactly one URL-encoded `{url}` placeholder and must not contain API credentials. Existing tagged links are kept as entered, and are never wrapped a second time. Merchant exclusions take precedence.

## Credentials (server only)

- `SOVRN_COMMERCE_API_KEY`
- `AWIN_API_TOKEN`, `AWIN_PUBLISHER_ID`
- `IMPACT_ACCOUNT_SID`, `IMPACT_AUTH_TOKEN`
- `CJ_API_TOKEN`, `CJ_COMPANY_ID`, `CJ_WEBSITE_ID`
- `RAKUTEN_API_TOKEN`
- `SKIMLINKS_CLIENT_ID`, `SKIMLINKS_CLIENT_SECRET`

Only Sovrn's key is used by the network API adapter in this MVP. The other names reserve server-only configuration for their future authenticated API work; adding them does not activate unfinished methods. No `VITE_` keys, secrets in the store catalog, or frontend credential entry.

## Current search providers

Existing eBay Browse and SerpApi Shopping credentials retain their current environment names. The common search interface supports aggregation, bounded caching, filters, partial failures, and source signatures. eBay is excluded from child mode. API-returned links may be provider landing/offer pages when the provider does not supply a direct retailer URL; the app does not fabricate a direct product URL. SerpApi plan usage and data rights must be verified for production.

Shopify is not a universal catalog API: individual shops require their own permitted integration or approved affiliate feed. Unknown Shopify/independent-store URLs save manually with no approval required. Generic retailer scraping is not used by the universal flow; HTML metadata fetching is only enabled for explicitly permitted domains and rechecks every redirect.
