# Payment adapters

The default simulator requires no external credentials. HMAC signs requests and responses. A separate SQLite ledger stores each order's decision, and a C++ rule kernel evaluates policy. The delayed scenario saves a decision before delaying the first response, demonstrating safe recovery from an unknown outcome.

## Stripe test checkout setup

Only `sk_test_` keys are accepted. The adapter also rejects live-mode responses. Use Stripe test card data only.

1. Run `python tools/deploy.py configure`.
2. Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and `GROCERY_PUBLIC_BASE_URL=http://localhost:8080` to the ignored `deployment/.env` file locally. Never commit keys.
3. Authenticate the Stripe CLI to your test account and run:

```sh
stripe listen --forward-to localhost:8080/payments/stripe/webhook/
```

Use the listener's signing secret as `STRIPE_WEBHOOK_SECRET`. Run `python tools/deploy.py up` to recreate configured containers. Select **Stripe test checkout** in the cart, place the order, then follow **Continue to Stripe test checkout** on the status page.

The secret stays server-side. Hosted Checkout needs no publishable key in this app. A public deployment needs its own HTTPS URL and registered webhook; this sandbox binds to localhost.

## Confirmation and recovery

The worker retrieves the session and verifies order ID, CAD currency, exact snapshotted amount, and test mode. Only a paid session sells stock. Verified unpaid expiry releases stock. A declined card may be retried on the same Checkout page; it does not immediately terminate the local order.

Webhooks use SDK verification of the raw body with a five-minute tolerance. They only expedite reconciliation. Repeated or out-of-order notifications cannot apply stock changes themselves; a guarded completion transaction prevents double deduction. Polling every 15 seconds also recovers missed notifications. Browser return URLs never confirm payment.

Returning from Checkout does not cancel its session. Stock remains protected until payment or verified expiry. Creation uses an order-based idempotency key and a fixed two-hour expiry. Creation retries stop after 89 minutes, leaving the minimum 30-minute session lifetime required by Stripe. Uncertain failures keep reservations for review rather than creating a new payment. Five consecutive provider failures also require review. Administrator retry keeps the original order and key.

Supported Stripe totals are CAD $0.50–$999,999.99; the simulator also permits zero. Taxes, delivery, refunds, saved cards, and real charges are outside this demo.

Tests mock the API contract and exercise signatures, amount checks, retries, and reservation transitions. They do not claim a transaction against your Stripe account. The final integration check needs your local test credentials and hosted Checkout.

References: [Checkout creation](https://docs.stripe.com/api/checkout/sessions/create), [fulfillment](https://docs.stripe.com/checkout/fulfillment), [webhook handling](https://docs.stripe.com/events/manage-webhook-endpoints).
