# PHASE 09 — Stripe Payments
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `backend/src/services/payments.py`
- Stripe products: $5 / $10 / $15 pay-per-document, $20/mo subscription, 1 free document per user
- Webhook handler at `/api/stripe/webhook`
- Access-control middleware checks user payment status before allowing premium endpoints

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f backend/src/services/payments.py && echo "payments present"
grep -E "stripe.checkout|stripe.Webhook" backend/src/services/payments.py && echo "stripe wired ok"
grep -rE "/api/stripe/webhook" backend/src/api/ && echo "webhook route ok"
grep -E "STRIPE_SECRET_KEY|STRIPE_WEBHOOK_SECRET" backend/.env && echo "stripe env ok"
```

## Contract provided to later phases

- **Phase 23 attaches a new $35 product** via `stripe.checkout.Session.create()` with metadata `{packet_id, user_id}`.
- Phase 23 extends the existing webhook handler with a new branch for `checkout.session.completed` events that have `packet_id` metadata — sets `packets.status = 'paid'`.
- Do NOT modify the existing webhook handler structure — only add the new branch.

## What to do if verification fails

STOP. Phase 23 monetization depends on this.

## Final line

```
PHASE 09 VERIFIED — proceed to PHASE 10
```
