"""
Router : webhook Stripe.

Route PUBLIQUE (pas d'authentification cookie) mais sécurisée par la
vérification de signature Stripe (STRIPE_WEBHOOK_SECRET) — seul Stripe
peut déclencher des événements valides ici.

À configurer sur https://dashboard.stripe.com/webhooks avec l'URL :
  https://votre-domaine.com/api/webhooks/stripe
Événement à écouter : checkout.session.completed
"""
import logging

import stripe
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.config import settings
from app.services.stripe_service import handle_checkout_completed

logger = logging.getLogger("ctq.stripe.webhook")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET non configuré — webhook refusé.")
        raise HTTPException(status_code=503, detail="Webhook non configuré.")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Signature invalide.")

    db: Session = SessionLocal()
    try:
        if event["type"] == "checkout.session.completed":
            handle_checkout_completed(db, event["data"]["object"])
    finally:
        db.close()

    return {"received": True}
