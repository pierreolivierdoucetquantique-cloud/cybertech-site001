"""Router : factures côté client (liste, téléchargement)."""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_client
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentRequestStatus
from app.schemas.invoice_schemas import InvoiceOut

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("", response_model=list[InvoiceOut])
def list_my_invoices(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    invoices = (
        db.query(Invoice)
        .filter(Invoice.client_id == client.id)
        .order_by(Invoice.created_at.desc())
        .all()
    )
    results = []
    for inv in invoices:
        order = inv.order
        deposit_amount = round(inv.total * 0.40, 2) if inv.total else None

        # Paiements confirmés pour cette commande
        confirmed_payments = (
            db.query(Payment)
            .filter(
                Payment.order_id == inv.order_id,
                Payment.client_id == client.id,
                Payment.status == PaymentRequestStatus.APPROVED,
            )
            .order_by(Payment.reviewed_at.desc())
            .all()
        )
        paid_total = sum(p.amount for p in confirmed_payments)
        balance = round(max(inv.total - paid_total, 0), 2)

        last_payment = confirmed_payments[0] if confirmed_payments else None

        results.append(InvoiceOut(
            id=inv.id,
            invoice_number=inv.invoice_number,
            order_id=inv.order_id,
            order_number=order.order_number if order else None,
            subtotal=inv.subtotal,
            gst_amount=inv.gst_amount,
            qst_amount=inv.qst_amount,
            total=inv.total,
            deposit_amount=deposit_amount,
            balance_remaining=balance,
            payment_status=order.payment_status.value if order else None,
            payment_method=last_payment.method.value if last_payment else None,
            transaction_id=last_payment.stripe_payment_intent_id if last_payment else None,
            payment_date=last_payment.reviewed_at if last_payment else None,
            created_at=inv.created_at,
        ))
    return results


@router.get("/{invoice_id}/download")
def download_invoice(
    invoice_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.client_id == client.id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable.")
    if not invoice.pdf_path or not os.path.exists(invoice.pdf_path):
        raise HTTPException(status_code=404, detail="Le fichier PDF de cette facture est introuvable.")

    return FileResponse(
        invoice.pdf_path,
        media_type="application/pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )
