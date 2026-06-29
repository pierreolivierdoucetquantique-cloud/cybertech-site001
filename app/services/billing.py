"""Service de facturation : orchestre numérotation, calcul des taxes, PDF, email.

v9.11 : opère désormais sur le panier complet (Order + ses OrderItem), pas
sur un seul produit. Le sous-total est la somme des prix des items, et les
taxes ne sont calculées que si le réglage admin ENABLE_TPS_TVQ est actif au
moment de la création (le résultat est figé sur la facture, comme avant)."""
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
from app.services.settings_service import is_taxes_enabled

PAYMENT_INSTRUCTIONS = (
    "Un dépôt de 40% est requis pour démarrer le projet. Le solde restant est "
    "payable selon l'entente convenue. Les virements bancaires sont acceptés."
)


def calculate_taxes(subtotal: float, apply_taxes: bool = True) -> tuple[float, float, float]:
    """Retourne (gst_amount, qst_amount, total) à partir d'un sous-total."""
    if not apply_taxes:
        return 0.0, 0.0, round(subtotal, 2)
    gst = round(subtotal * settings.TAX_RATE_GST, 2)
    qst = round(subtotal * settings.TAX_RATE_QST, 2)
    total = round(subtotal + gst + qst, 2)
    return gst, qst, total


def finalize_order_totals(db: Session, order: Order) -> None:
    """
    Calcule/fige subtotal, TPS, TVQ et total d'un panier à partir de ses
    items actuels, selon le réglage de taxes EN VIGUEUR AU MOMENT DE L'APPEL.
    Appelé à la création du panier ; les montants restent ensuite figés.
    """
    apply_taxes = is_taxes_enabled(db)
    order.recalculate_totals(settings.TAX_RATE_GST, settings.TAX_RATE_QST, apply_taxes)


def create_invoice_for_order(db: Session, order: Order, client: Client) -> Invoice:
    """
    Crée une facture pour un panier (Order) donné : construit le PDF avec une
    ligne par OrderItem, sauvegarde sur le disk, et envoie l'email avec la
    facture en pièce jointe.

    Idempotent : si une facture existe déjà pour ce panier, la retourne sans
    en recréer une (évite les doublons en cas de double-clic / retry).
    """
    if order.invoice:
        return order.invoice

    invoice_number = next_invoice_number(db)

    address_lines = []
    if client.address:
        address_lines.append(client.address)
    city_line = ", ".join(filter(None, [client.city, client.postal_code]))
    if city_line:
        address_lines.append(city_line)
    if client.country:
        address_lines.append(client.country)

    line_items = [
        {"name": item.product_name, "description": f"Commande {order.order_number}", "price": item.price}
        for item in order.items
    ]

    pdf_bytes = generate_invoice_pdf(
        invoice_number=invoice_number,
        client_full_name=f"{client.first_name} {client.last_name}",
        client_email=client.email,
        client_address_lines=address_lines,
        purchase_date=order.created_at,
        line_items=line_items,
        subtotal=order.subtotal,
        gst_amount=order.gst_amount,
        qst_amount=order.qst_amount,
        total=order.total,
        payment_instructions=PAYMENT_INSTRUCTIONS,
    )
    pdf_path = save_invoice_pdf(pdf_bytes, invoice_number)

    invoice = Invoice(
        invoice_number=invoice_number,
        order_id=order.id,
        client_id=client.id,
        subtotal=order.subtotal,
        gst_amount=order.gst_amount,
        qst_amount=order.qst_amount,
        total=order.total,
        pdf_path=pdf_path,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    log_action(db, actor_type="system", action="create_invoice", target_type="invoice", target_id=invoice.id, details=invoice_number)

    send_invoice_email(client, invoice, pdf_bytes)

    return invoice
