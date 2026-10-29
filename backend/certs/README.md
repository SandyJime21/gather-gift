# Railway MySQL public CA

This public CA was retrieved from the selected Railway MySQL service over authenticated SSH. It contains no private key or database credentials.

SHA-256 certificate fingerprint: `a43e6ae20d495dc724b4c741b162cad487ac4cb4706a39e63b9f7bd5dca1afcc`.

With approval, the database server certificate was replaced to include its public hostname. The existing CA and server private key remain on Railway. The original public server certificate is backed up at `/var/lib/mysql/gather-gift-tls.BtQ6IF/server-cert.original.pem`.

The replacement certificate expires October 28, 2027 (Pacific time). Renew before then, preserving hostname entries. Check exact expiry on the server with `openssl x509 -in /var/lib/mysql/server-cert.pem -noout -dates`. If the database hostname or CA changes, update and verify the trust configuration.

Render loads `/app/backend/certs/railway-mysql-ca.crt`. Both certificate-chain and hostname verification remain enabled. Other database hosts use normal public trust roots unless `DATABASE_SSL_CA` explicitly selects another CA.
