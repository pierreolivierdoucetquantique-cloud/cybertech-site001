"""Router : gestion des factures par l'admin (liste, détail, téléchargement, renvoi par courriel)."""
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.order import Order
from app.services.audit import log_action
from app.services.email_service import send_invoice_email

router = APIRouter(prefix="/api/admin/invoices", tags=["admin-invoices"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _invoice_to_dict(invoice: Invoice, order: Optional[Order], client: Optional[Client]) -> dict:
    items_summary = ", ".join(i.product_name for i in order.items) if order else None
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "order_id": invoice.order_id,
        "order_number": order.order_number if order else None,
        "items_summary": items_summary,
        "client_id": invoice.client_id,
        "client_name": f"{client.first_name} {client.last_name}" if client else "—",
        "client_email": client.email if client else "—",
        "subtotal": invoice.subtotal,
        "gst_amount": invoice.gst_amount,
        "qst_amount": invoice.qst_amount,
        "total": invoice.total,
        "deposit_amount": invoice.deposit_amount,
        "amount_paid": invoice.amount_paid,
        "remaining_balance": invoice.remaining_balance,
        "status": invoice.status,
        "has_pdf": bool(invoice.pdf_path and os.path.exists(invoice.pdf_path)),
        "created_at": invoice.created_at,
    }


@router.get("")
def list_invoices(
    search: Optional[str] = Query(None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Invoice).order_by(Invoice.created_at.desc())
    invoices = query.all()

    results = []
    for invoice in invoices:
        order = db.query(Order).filter(Order.id == invoice.order_id).first()
        client = db.query(Client).filter(Client.id == invoice.client_id).first()
        results.append((invoice, order, client))

    if search:
        s = search.strip().lower()
        results = [
            (inv, o, c) for inv, o, c in results
            if s in inv.invoice_number.lower()
            or (c and (s in c.first_name.lower() or s in c.last_name.lower() or s in c.email.lower()))
            or (o and s in o.order_number.lower())
        ]

    return [_invoice_to_dict(inv, o, c) for inv, o, c in results]


@router.get("/{invoice_id}/download")
def admin_download_invoice(
    invoice_id: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable.")
    if not invoice.pdf_path or not os.path.exists(invoice.pdf_path):
        raise HTTPException(status_code=404, detail="Le fichier PDF de cette facture est introuvable.")

    return FileResponse(
        invoice.pdf_path,
        media_type="application/pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )


@router.post("/{invoice_id}/resend")
def resend_invoice_email(
    invoice_id: str,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Renvoie la facture par courriel au client (utile si l'email initial a échoué)."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable.")
    if not invoice.pdf_path or not os.path.exists(invoice.pdf_path):
        raise HTTPException(status_code=404, detail="Le fichier PDF de cette facture est introuvable.")

    client = db.query(Client).filter(Client.id == invoice.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    with open(invoice.pdf_path, "rb") as f:
        pdf_bytes = f.read()

    send_invoice_email(client, invoice, pdf_bytes)

    log_action(
        db, actor_type="admin", actor_id=admin.id, action="resend_invoice",
        target_type="invoice", target_id=invoice.id, ip_address=_client_ip(request),
    )

    return {"message": f"Facture {invoice.invoice_number} renvoyée à {client.email}."}
