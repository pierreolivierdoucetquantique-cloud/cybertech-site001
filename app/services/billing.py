"""Service de facturation : orchestre numérotation, calcul des taxes, PDF, email."""
import datetime as dt

from sqlalchemy.orm import Session

from app.config import settings
from app.models.order import Order
from app.models.invoice import Invoice
from app.models.client import Client
from app.services.numbering import next_invoice_number
from app.services.invoice_pdf import generate_invoice_pdf, save_invoice_pdf
from app.services.email_service import send_invoice_email
from app.services.audit import log_action

PAYMENT_INSTRUCTIONS = (
    "Un dépôt de 40% est requis pour démarrer le projet. Le solde restant est "
    "payable selon l'entente convenue. Les virements bancaires sont acceptés."
)


def calculate_taxes(subtotal: float) -> tuple[float, float, float]:
    """Retourne (gst_amount, qst_amount, total) à partir d'un sous-total."""
    gst = round(subtotal * settings.TAX_RATE_GST, 2)
    qst = round(subtotal * settings.TAX_RATE_QST, 2)
    total = round(subtotal + gst + qst, 2)
    return gst, qst, total


def create_invoice_for_order(db: Session, order: Order, client: Client) -> Invoice:
    """
    Crée une facture pour une commande donnée : calcule les taxes, génère le
    numéro séquentiel, construit le PDF, le sauvegarde sur le disk, et envoie
    l'email avec la facture en pièce jointe.

    Idempotent : si une facture existe déjà pour cette commande, la retourne
    sans en recréer une (évite les doublons en cas de double-clic / retry).
    """
    if order.invoice:
        return order.invoice

    gst, qst, total = calculate_taxes(order.price)
    invoice_number = next_invoice_number(db)

    address_lines = []
    if client.address:
        address_lines.append(client.address)
    city_line = ", ".join(filter(None, [client.city, client.postal_code]))
    if city_line:
        address_lines.append(city_line)
    if client.country:
        address_lines.append(client.country)

    pdf_bytes = generate_invoice_pdf(
        invoice_number=invoice_number,
        client_full_name=f"{client.first_name} {client.last_name}",
        client_email=client.email,
        client_address_lines=address_lines,
        purchase_date=order.created_at,
        product_name=order.product_name,
        product_description=f"Commande {order.order_number}",
        subtotal=order.price,
        gst_amount=gst,
        qst_amount=qst,
        total=total,
        payment_instructions=PAYMENT_INSTRUCTIONS,
    )
    pdf_path = save_invoice_pdf(pdf_bytes, invoice_number)

    invoice = Invoice(
        invoice_number=invoice_number,
        order_id=order.id,
        client_id=client.id,
        subtotal=order.price,
        gst_amount=gst,
        qst_amount=qst,
        total=total,
        pdf_path=pdf_path,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    log_action(db, actor_type="system", action="create_invoice", target_type="invoice", target_id=invoice.id, details=invoice_number)

    send_invoice_email(client, invoice, pdf_bytes)

    return invoice
