# Adding gifts before Amazon API approval

In a wishlist's Add gift browser, paste the original affiliate product link and choose Preview link. Review the gift name, enter or correct Estimated price and Currency, then choose + Wish. The original pasted link is passed through unchanged. Missing prices stay blank; no estimated price is inferred from unrelated page text. Manual entry is also available if a store cannot provide a preview.

For supported non-Amazon stores, explicit product-price metadata or Product JSON-LD offers can populate the estimate. Price ranges and unrelated structured data are ignored. Amazon price extraction is excluded pending its approved API integration; adults can enter an estimate. Saved prices are estimates, not continuously updated checkout prices. Existing items without prices are not changed automatically.

## Accounts worth applying for

Checked October 29, 2026. These are options to evaluate, not integrations already enabled.

| Service | Use | Access and limits |
| --- | --- | --- |
| [SerpApi](https://serpapi.com/pricing) | Existing multi-store Google Shopping search | Published free tier: 250 searches/month; confirm current commercial-use terms for your account. The app already supports a server-held SERPAPI_API_KEY. |
| [eBay Developers](https://developer.ebay.com/) + [eBay Partner Network](https://partnernetwork.ebay.com/) | Product search plus affiliate links | Developer membership is free. Production API access and affiliate acceptance are separate; confirm permissions for the planned Browse API use case. |
| [Target Partners](https://partners.target.com/faqs) | Target affiliate links through Impact | Apply for approval. [Impact catalogs](https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/marketing-content/product-marketplace-and-catalogs/download-product-catalogs-as-a-partner) can be delivered via API, subject to the brand's catalog access. Affiliate approval alone does not guarantee a public product-search API. |
| [Walmart Affiliates](https://affiliates.walmart.com/) | Additional retailer affiliate links | Apply for approval; ask which catalog/feed/API access your approved account includes. Do not use seller Marketplace credentials as a consumer shopping API. |

Start with the existing shopping search and pasted links while applications are pending. Do not wait for every retailer before testing gift entry and sharing. Keep provider credentials server-side. Amazon integration remains separate from child mode. No new partner API is enabled merely by listing it here.

## Release checks

Before public sharing: test a pasted link with an estimate, verify its card price and outgoing link as a follower, test an image/price-blocked store's manual fallback, and verify child restrictions. Pending local code must be deployed only with the owner's explicit push authorization. Do not advance the shared production migration marker for undeployed features.
