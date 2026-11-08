# Input and integrity boundaries

This learning application demonstrates controls in code; it is not a production security audit.

- Forms bound text/numeric inputs, parse UUIDs, and validate email syntax. Services recheck stock and authorization. Database constraints enforce uniqueness and stock limits.
- The ORM binds SQL values. Log queries use parameters and fixed column names. Templates escape user/imported text rather than rendering it as trusted HTML.
- Mutations use POST and CSRF protection. The Stripe webhook is exempt because it verifies Stripe signatures. Store permissions are checked in both controllers and services.
- Django uses salted password hashing. Registration cannot grant staff or manager roles. Cookies are HttpOnly/SameSite=Lax; HTTPS/secure cookies are required outside explicit localhost sandbox mode.
- Guest access is bound to a server-side session. An order ID or submitted customer ID does not grant access. Guest recovery and account/cart merging are not implemented.
- Food search uses a fixed HTTPS endpoint, response limits, timeout, field allowlist, finite numeric checks, and validated barcodes. Imports require a signed, expiring preview. No arbitrary image/fetch URLs are accepted.
- Stripe accepts test keys only, verifies identity/amount/currency/test status, and uses raw-body SDK signature checks. Card data never enters the app. Credentials belong in ignored local configuration.
- Simulator HMACs authenticate messages; idempotency handles replay. Store-ledger HMACs detect changes only while the key remains trusted. Verification checks the chain, head, and final stock projection. Warehouse records do not yet have hash chaining.

Hashing is not encryption or authorization. An attacker controlling both database and signing key can rewrite the ledger. The demo uses a domain-separated application secret; a real audit system needs independently managed keys and external checkpoints or immutable storage.

Login throttling is process-local and guest abuse controls are limited. Before public exposure, add shared rate limiting, guest reservation quotas, HTTPS ingress, backups, data retention, and deployment-specific secrets management. Compose disables DEBUG and exposes only localhost.
