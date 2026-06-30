"""Router : factures côté client (liste, téléchargement)."""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_client
from app.models.client import Client
from app.models.invoice import Invoice
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
    return invoices


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
