"""
Service Stripe : Checkout (paiement par carte), webhook, et remboursement.

Le montant payé (dépôt 40% ou total) est calculé côté serveur à partir du
TOTAL réel du panier en base (taxes incluses) — jamais à partir d'une valeur
envoyée par le client — pour empêcher toute manipulation du montant.

v9.11 : le dépôt de 40% se calcule sur order.total (sous-total + taxes), pas
seulement sur le sous-total — conformément à la séquence
SUBTOTAL → TAXES → TOTAL → DEPOSIT(40%) → BALANCE.
"""
import datetime as dt
import logging

import stripe
from sqlalchemy.orm import Session

from app.config import settings
from app.models.order import Order, PaymentStatus
from app.models.client import Client
from app.models.payment import Payment, PaymentMethod, PaymentAmountType, PaymentRequestStatus
from app.services.billing import sync_invoice_for_order, get_collected_amount
from app.services.audit import log_action

logger = logging.getLogger("ctq.stripe")

stripe.api_key = settings.STRIPE_SECRET_KEY


def calculate_payment_amount(db: Session, order: Order, amount_type: PaymentAmountType) -> float:
    """Calcule le montant à payer à partir du TOTAL du panier (taxes incluses)."""
    if amount_type == PaymentAmountType.DEPOSIT:
        return round(order.total * settings.DEPOSIT_PERCENTAGE, 2)
    if amount_type == PaymentAmountType.BALANCE:
        already_paid = get_collected_amount(db, order_id=order.id)
        return round(max(order.total - already_paid, 0.0), 2)
    return order.total


def create_checkout_session(db: Session, order: Order, client: Client, amount_type: PaymentAmountType) -> dict:
    if not settings.STRIPE_SECRET_KEY:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Le paiement par carte n'est pas configuré pour le moment.")

    amount = calculate_payment_amount(db, order, amount_type)
    amount_cents = int(round(amount * 100))

    labels = {
        PaymentAmountType.DEPOSIT: "Dépôt (40%)",
        PaymentAmountType.BALANCE: "Solde restant",
        PaymentAmountType.FULL: "Paiement complet",
    }
    label = labels.get(amount_type, "Paiement")
    items_summary = ", ".join(item.product_name for item in order.items)

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
                    "name": f"Commande {order.order_number} — {label}",
                    "description": items_summary[:500],
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

    # Capture la marque de carte (informatif — affiché dans Admin > Paiements,
    # n'est jamais une méthode de paiement séparée d'INTERAC/STRIPE).
    try:
        if payment_intent_id:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id, expand=["payment_method"])
            pm = getattr(intent, "payment_method", None)
            card = getattr(pm, "card", None) if pm else None
            if card:
                payment.card_brand = card.get("brand") if isinstance(card, dict) else getattr(card, "brand", None)
                payment.card_last4 = card.get("last4") if isinstance(card, dict) else getattr(card, "last4", None)
    except Exception:
        logger.exception("Impossible de récupérer la marque de carte pour le paiement %s", payment.id)

    db.commit()

    order = payment.order
    client = payment.client

    total_collected = get_collected_amount(db, order_id=order.id)
    if total_collected >= order.total - 0.01:
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

    sync_invoice_for_order(db, order, client)


def refund_payment(db: Session, payment: Payment, amount: float | None, reason: str | None) -> Payment:
    """
    Effectue un remboursement RÉEL via l'API Stripe (pas un simple changement
    de statut cosmétique). `amount` en dollars ; si None, remboursement total.
    """
    from fastapi import HTTPException

    if payment.method != PaymentMethod.STRIPE:
        raise HTTPException(status_code=400, detail="Seuls les paiements Stripe peuvent être remboursés automatiquement. Pour un Interac, traitez le remboursement manuellement puis ajustez le statut.")
    if not payment.stripe_payment_intent_id:
        raise HTTPException(status_code=400, detail="Ce paiement n'a pas d'identifiant Stripe confirmé — impossible de le rembourser automatiquement.")
    if payment.status != PaymentRequestStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Seul un paiement approuvé peut être remboursé.")

    refund_kwargs = {"payment_intent": payment.stripe_payment_intent_id}
    if amount is not None:
        refund_kwargs["amount"] = int(round(amount * 100))

    refund = stripe.Refund.create(**refund_kwargs)

    refunded_amount = amount if amount is not None else payment.amount
    payment.refunded_amount = (payment.refunded_amount or 0.0) + refunded_amount
    payment.refund_reason = reason
    payment.refunded_at = dt.datetime.utcnow()
    payment.stripe_refund_id = refund.id
    payment.status = PaymentRequestStatus.REFUNDED
    db.commit()
    db.refresh(payment)

    order = payment.order
    if payment.refunded_amount >= order.total - 0.01:
        order.payment_status = PaymentStatus.REFUNDED
    else:
        order.payment_status = PaymentStatus.PARTIALLY_REFUNDED
    db.commit()

    if order.invoice and order.client:
        sync_invoice_for_order(db, order, order.client)

    return payment
