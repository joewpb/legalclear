import logging
import traceback

import stripe

from src.core.config import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeClient:

    def create_payment_intent(
            self, price_usd: int,
            session_id: str, user_email: str,
            metadata: dict = None) -> dict:
        intent = stripe.PaymentIntent.create(
            amount=price_usd * 100,
            currency="usd",
            receipt_email=user_email,
            metadata={
                "session_id": session_id,
                **(metadata or {})
            }
        )
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id
        }

    def create_subscription_checkout(
            self, user_email: str,
            user_id: str,
            success_url: str,
            cancel_url: str) -> dict:
        customer_id = self.create_or_get_customer(
            user_email)
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": (
                    settings.STRIPE_SUBSCRIPTION_PRICE_ID),
                "quantity": 1
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": user_id}
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }

    def create_or_get_customer(
            self, email: str) -> str:
        customers = stripe.Customer.list(
            email=email, limit=1)
        if customers.data:
            return customers.data[0].id
        customer = stripe.Customer.create(email=email)
        return customer.id

    def cancel_subscription(
            self, subscription_id: str) -> bool:
        try:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True)
            return True
        except stripe.error.StripeError:
            logger.error("stripe cancel_subscription(%s) failed:\n%s", subscription_id, traceback.format_exc())
            return False

    def verify_webhook(
            self, payload: bytes,
            sig_header: str) -> dict:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header,
                settings.STRIPE_WEBHOOK_SECRET)
            return event
        except stripe.error.SignatureVerificationError:
            raise ValueError(
                "Invalid webhook signature")

    def get_payment_status(
            self, payment_intent_id: str) -> str:
        intent = stripe.PaymentIntent.retrieve(
            payment_intent_id)
        return intent.status
