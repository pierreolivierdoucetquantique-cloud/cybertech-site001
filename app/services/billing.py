"""Service de facturation : orchestre numérotation, calcul des taxes, PDF, email.

v9.11 : opère sur le panier complet (Order + ses OrderItem), pas sur un seul
produit. Le sous-total est la somme des prix des items, et les taxes ne sont
calculées que si le réglage admin ENABLE_TPS_TVQ est actif au moment de la
création (le résultat est figé sur la facture, comme avant).

v9.12 — Logique de facturation automatique (dépôt 40% / paiement complet) :
`sync_invoice_for_order` est LE point d'entrée unique appelé après CHAQUE
paiement confirmé (dépôt, solde, complet, ou remboursement). Il :
  1. Calcule le montant réellement encaissé pour la commande (somme des
     paiements APPROUVÉS, nets des remboursements).
  2. Détermine deposit_amount / remaining_balance / status automatiquement.
  3. Crée la facture si elle n'existe pas encore, ou la met à jour sinon.
  4. Régénère le PDF (les montants affichés reflètent toujours l'état réel).
  5. Envoie/renvoie la facture par courriel au client.
Aucun ajustement manuel n'est requis nulle part ailleurs dans l'application.
"""
import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.order import Order
from app.models.invoice import Invoice, InvoiceStatus
from app.models.client import Client
from app.models.payment import Payment, PaymentRequestStatus
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


def get_collected_amount(db: Session, order_id: str | None = None, client_id: str | None = None) -> float:
    """
    Somme des montants RÉELLEMENT encaissés via le système de paiement (paiements
    Interac/Stripe approuvés, nets des remboursements) POUR UNE COMMANDE DONNÉE.
    Utilisée pour le calcul du montant à payer (dépôt/solde) et la protection
    anti double-paiement — volontairement stricte : ignore les commandes marquées
    payées manuellement par l'admin sans paiement réel (voir get_total_collected_revenue
    pour les statistiques globales, qui elles doivent inclure ce cas).
    """
    query = db.query(Payment).filter(
        Payment.status.in_([PaymentRequestStatus.APPROVED, PaymentRequestStatus.REFUNDED])
    )
    if order_id:
        query = query.filter(Payment.order_id == order_id)
    if client_id:
        query = query.filter(Payment.client_id == client_id)

    total = 0.0
    for p in query.all():
        total += max((p.amount or 0.0) - (p.refunded_amount or 0.0), 0.0)
    return round(total, 2)


def get_total_collected_revenue(db: Session, client_id: str | None = None) -> float:
    """
    Revenu encaissé pour les STATISTIQUES FINANCIÈRES (dashboard, top clients,
    fiche client). Contrairement à get_collected_amount, additionne
    Invoice.amount_paid — qui inclut aussi bien les paiements réels
    (Interac/Stripe approuvés) QUE les commandes marquées payées manuellement
    par l'admin (ex : le temps que les clés Stripe/Interac soient configurées).
    C'est le même montant que celui déjà affiché sur chaque facture, donc le
    dashboard reste cohérent avec ce que voit l'admin/le client.
    """
    query = db.query(func.coalesce(func.sum(Invoice.amount_paid), 0.0))
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    return round(query.scalar() or 0.0, 2)


def _resolve_amount_paid(db: Session, order: Order) -> float:
    """
    Montant encaissé pour une commande, avec repli sur le statut de paiement
    de la commande si aucun enregistrement Payment n'existe (ex : commande
    marquée payée manuellement par l'admin via Admin > Commandes, sans passer
    par le flux Interac/Stripe) — préserve ce cas d'usage existant.
    """
    from app.models.order import PaymentStatus

    amount_paid = get_collected_amount(db, order_id=order.id)
    if amount_paid > 0:
        return amount_paid

    if order.payment_status == PaymentStatus.PAID:
        return order.total
    if order.payment_status == PaymentStatus.DEPOSIT_PAID:
        return round(order.total * settings.DEPOSIT_PERCENTAGE, 2)
    return 0.0


def sync_invoice_for_order(db: Session, order: Order, client: Client) -> Invoice:
    """
    Point d'entrée unique de la logique de facturation automatique. À appeler
    après CHAQUE confirmation de paiement (dépôt, solde, complet) ou
    remboursement. Idempotent et sans effet destructif : peut être appelé
    autant de fois que nécessaire, le résultat reflète toujours l'état actuel.
    """
    amount_paid = _resolve_amount_paid(db, order)
    remaining_balance = round(max(order.total - amount_paid, 0.0), 2)

    from app.models.order import PaymentStatus as _PaymentStatus
    if order.payment_status == _PaymentStatus.REFUNDED:
        status = InvoiceStatus.REFUNDED
        deposit_amount = None
    elif order.payment_status == _PaymentStatus.PARTIALLY_REFUNDED:
        status = InvoiceStatus.PARTIALLY_REFUNDED
        deposit_amount = amount_paid
    elif remaining_balance <= 0.01 and amount_paid > 0:
        status = InvoiceStatus.PAID_IN_FULL
        deposit_amount = None
    else:
        status = InvoiceStatus.DEPOSIT_PAID
        deposit_amount = amount_paid

    invoice = order.invoice
    is_new = invoice is None

    if is_new:
        invoice = Invoice(
            invoice_number=next_invoice_number(db),
            order_id=order.id,
            client_id=client.id,
            subtotal=order.subtotal,
            gst_amount=order.gst_amount,
            qst_amount=order.qst_amount,
            total=order.total,
        )
        db.add(invoice)

    invoice.amount_paid = amount_paid
    invoice.remaining_balance = remaining_balance
    invoice.deposit_amount = deposit_amount
    invoice.status = status.value
    invoice.updated_at = dt.datetime.utcnow()

    pdf_bytes = _build_invoice_pdf(order, client, invoice, status)
    invoice.pdf_path = save_invoice_pdf(pdf_bytes, invoice.invoice_number)

    db.commit()
    db.refresh(invoice)

    log_action(
        db, actor_type="system",
        action="create_invoice" if is_new else "update_invoice",
        target_type="invoice", target_id=invoice.id,
        details=f"{invoice.invoice_number} — {status.value}",
    )

    send_invoice_email(client, invoice, pdf_bytes)

    return invoice


def _build_invoice_pdf(order: Order, client: Client, invoice: Invoice, status: InvoiceStatus) -> bytes:
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

    return generate_invoice_pdf(
        invoice_number=invoice.invoice_number,
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
        status=status.value,
        deposit_amount=invoice.deposit_amount,
        remaining_balance=invoice.remaining_balance,
        amount_paid=invoice.amount_paid,
    )


def create_invoice_for_order(db: Session, order: Order, client: Client) -> Invoice:
    """
    Conservé pour compatibilité (ancien nom utilisé à plusieurs endroits) —
    délègue maintenant entièrement à sync_invoice_for_order, qui gère aussi
    bien la création initiale que les mises à jour ultérieures (ex : solde
    payé après un dépôt).
    """
    return sync_invoice_for_order(db, order, client)
