"""Router : paiements côté client (Interac et Stripe), liés au panier complet (v9.11)."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_client
from app.models.client import Client
from app.models.order import Order, PaymentStatus
from app.models.payment import Payment, PaymentMethod, PaymentAmountType, PaymentRequestStatus
from app.schemas.payment_schemas import InteracPaymentCreate, StripeCheckoutCreate, PaymentOut
from app.services.payment_gate import assert_payment_unlocked, assert_amount_type_allowed
from app.services.file_storage import save_upload
from app.services.stripe_service import create_checkout_session, calculate_payment_amount
from app.services.audit import log_action
from app.config import settings

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _get_owned_order(order_id: str, client: Client, db: Session) -> Order:
    order = db.query(Order).filter(Order.id == order_id, Order.client_id == client.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    return order


@router.get("/order/{order_id}", response_model=list[PaymentOut])
def list_payments_for_order(
    order_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    order = _get_owned_order(order_id, client, db)
    return (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .order_by(Payment.created_at.desc())
        .all()
    )


@router.get("/interac-info")
def get_interac_info():
    """Infos statiques pour le virement Interac (adresse courriel)."""
    return {"email": settings.INTERAC_EMAIL}


@router.post("/interac", response_model=PaymentOut, status_code=201)
def create_interac_payment(
    payload: InteracPaymentCreate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    order = _get_owned_order(payload.order_id, client, db)
    assert_payment_unlocked(order)
    assert_amount_type_allowed(db, order, payload.amount_type)

    amount = calculate_payment_amount(db, order, payload.amount_type)
    payment = Payment(
        order_id=order.id,
        client_id=client.id,
        method=PaymentMethod.INTERAC,
        amount_type=payload.amount_type,
        amount=amount,
        status=PaymentRequestStatus.PENDING_PROOF,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    log_action(db, actor_type="client", actor_id=client.id, action="create_interac_payment", target_type="order", target_id=order.id)
    return payment


@router.post("/interac/{payment_id}/proof", response_model=PaymentOut)
async def upload_payment_proof(
    payment_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """Le client téléverse sa preuve de paiement ('J'ai effectué mon paiement')."""
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.client_id == client.id, Payment.method == PaymentMethod.INTERAC)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")
    if payment.status not in (PaymentRequestStatus.PENDING_PROOF, PaymentRequestStatus.REJECTED):
        raise HTTPException(status_code=400, detail="Une preuve a déjà été soumise pour ce paiement.")

    record = await save_upload(
        db, file, category="payment_proof",
        uploaded_by_type="client", uploaded_by_id=client.id,
        related_order_id=payment.order_id, related_client_id=client.id,
    )

    payment.proof_file_id = record.id
    payment.status = PaymentRequestStatus.PENDING_VALIDATION
    payment.admin_review_note = None
    db.commit()
    db.refresh(payment)

    log_action(db, actor_type="client", actor_id=client.id, action="upload_payment_proof", target_type="payment", target_id=payment.id)
    return payment


@router.post("/stripe/checkout")
def create_stripe_checkout(
    payload: StripeCheckoutCreate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    order = _get_owned_order(payload.order_id, client, db)
    assert_payment_unlocked(order)
    assert_amount_type_allowed(db, order, payload.amount_type)

    result = create_checkout_session(db, order, client, payload.amount_type)
    log_action(db, actor_type="client", actor_id=client.id, action="create_stripe_checkout", target_type="order", target_id=order.id)
    return result
