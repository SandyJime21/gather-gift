# Custom affiliate companies

Developer portal > Affiliate Management > Add affiliate company accepts a company name, website, public publisher ID, issued affiliate link template and optional server environment variable name. Companies start unapproved and disabled. Enable routing only after actual approval and with a network-issued template containing one `{url}` placeholder.

Enter secret API key values in Render environment settings, never in the publisher ID or public tracking template. The portal stores only the environment variable name. Adding a company does not implement an unfamiliar product-search API; it configures approved outbound link routing. Valid product links keep working directly when no approved route is available.

This uses the existing commerce integration table. Any pending release migrations must ship with their matching code, rather than being applied to the shared database early.
