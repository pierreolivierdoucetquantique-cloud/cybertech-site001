"""
Service Stripe : Checkout (paiement par carte) et traitement du webhook.

Le montant payé (dépôt 40% ou total) est calculé côté serveur à partir du
prix réel de la commande en base — jamais à partir d'une valeur envoyée par
le client — pour empêcher toute manipulation du montant.
"""
import logging

import stripe
from sqlalchemy.orm import Session

from app.config import settings
from app.models.order import Order, PaymentStatus
from app.models.client import Client
from app.models.payment import Payment, PaymentMethod, PaymentAmountType, PaymentRequestStatus
from app.services.billing import create_invoice_for_order
from app.services.audit import log_action

logger = logging.getLogger("ctq.stripe")

stripe.api_key = settings.STRIPE_SECRET_KEY


def calculate_payment_amount(order: Order, amount_type: PaymentAmountType) -> float:
    if amount_type == PaymentAmountType.DEPOSIT:
        return round(order.price * settings.DEPOSIT_PERCENTAGE, 2)
    return order.price


def create_checkout_session(db: Session, order: Order, client: Client, amount_type: PaymentAmountType) -> dict:
    if not settings.STRIPE_SECRET_KEY:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Le paiement par carte n'est pas configuré pour le moment.")

    amount = calculate_payment_amount(order, amount_type)
    amount_cents = int(round(amount * 100))

    label = "Dépôt (40%)" if amount_type == PaymentAmountType.DEPOSIT else "Paiement complet"

    success_url = f"{settings.FRONTEND_URL}/mon-compte.html?stripe=success&order={order.id}"
    cancel_url = f"{settings.FRONTEND_URL}/mon-compte.html?stripe=cancel&order={order.id}"

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        customer_email=client.email,
        line_items=[{
            "price_data": {
                "currency": "cad",
                "unit_amount": amount_cents,
                "product_data": {
                    "name": f"{order.product_name} — {label}",
                    "description": f"Commande {order.order_number}",
                },
            },
            "quantity": 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "order_id": order.id,
            "client_id": client.id,
            "amount_type": amount_type.value,
        },
    )

    payment = Payment(
        order_id=order.id,
        client_id=client.id,
        method=PaymentMethod.STRIPE,
        amount_type=amount_type,
        amount=amount,
        status=PaymentRequestStatus.STRIPE_INITIATED,
        stripe_checkout_session_id=session.id,
    )
    db.add(payment)
    db.commit()

    return {"checkout_url": session.url, "session_id": session.id}


def handle_checkout_completed(db: Session, session: dict) -> None:
    """Appelé par le webhook lors de l'événement checkout.session.completed."""
    session_id = session.get("id")
    payment_intent_id = session.get("payment_intent")

    payment = db.query(Payment).filter(Payment.stripe_checkout_session_id == session_id).first()
    if not payment:
        logger.warning("Webhook Stripe : session %s introuvable en base.", session_id)
        return

    if payment.status == PaymentRequestStatus.APPROVED:
        return  # déjà traité (idempotence : Stripe peut renvoyer l'événement plusieurs fois)

    payment.status = PaymentRequestStatus.APPROVED
    payment.stripe_payment_intent_id = payment_intent_id
    db.commit()

    order = payment.order
    client = payment.client

    if payment.amount_type == PaymentAmountType.FULL:
        order.payment_status = PaymentStatus.PAID
    else:
        order.payment_status = PaymentStatus.DEPOSIT_PAID
    db.commit()
    db.refresh(order)

    log_action(
        db, actor_type="system", action="stripe_payment_confirmed",
        target_type="order", target_id=order.id,
        details=f"{payment.amount_type.value} — {payment.amount} $ CAD",
    )

    if not order.invoice:
        create_invoice_for_order(db, order, client)
