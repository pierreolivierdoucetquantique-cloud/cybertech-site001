"""
Service d'envoi d'emails via Resend.

IMPORTANT : toutes les fonctions de ce module sont "best-effort" — une
défaillance d'envoi d'email (clé API manquante, Resend indisponible, etc.)
ne doit JAMAIS faire échouer l'action principale (création de commande,
inscription, etc.). Les erreurs sont journalisées mais avalées.
"""
import logging
from typing import TYPE_CHECKING

import resend

from app.config import settings

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.order import Order, OrderItem
    from app.models.invoice import Invoice

logger = logging.getLogger("ctq.email")

resend.api_key = settings.RESEND_API_KEY


def _send(to: str, subject: str, html: str, attachments: list | None = None) -> bool:
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY non configurée — email non envoyé (sujet: %s)", subject)
        return False
    try:
        params = {
            "from": settings.EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "html": html,
            "reply_to": settings.EMAIL_REPLY_TO,
        }
        if attachments:
            params["attachments"] = attachments
        resend.Emails.send(params)
        return True
    except Exception:
        logger.exception("Échec d'envoi d'email à %s (sujet: %s)", to, subject)
        return False


def send_welcome_email(client: "Client") -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:#2563EB;">Bienvenue chez Cyber Teck Q, {client.first_name} !</h2>
      <p>Votre espace client a été créé avec succès. Vous pouvez maintenant
      commander vos services et suivre vos projets directement depuis votre tableau de bord.</p>
      <p>Au plaisir de concrétiser votre projet avec vous.</p>
      <p style="color:#888;font-size:13px;margin-top:30px;">— L'équipe Cyber Teck Q</p>
    </div>
    """
    return _send(client.email, "Bienvenue chez Cyber Teck Q", html)


def send_order_confirmation_email(client: "Client", order: "Order") -> bool:
    rows_html = ""
    next_steps_html = ""
    for item in order.items:
        is_maintenance = getattr(item.product_type, "value", item.product_type) == "maintenance"
        rows_html += (
            f"<tr><td style='padding:6px 0;color:#666;'>{item.product_name}</td>"
            f"<td style='padding:6px 0;text-align:right;'>{item.price:,.2f} $</td></tr>"
        )
        if is_maintenance:
            next_steps_html += (
                f"<li>Signer le <strong>contrat de maintenance</strong> pour « {item.product_name} » "
                "depuis votre espace client.</li>"
            )
        else:
            next_steps_html += (
                f"<li>Remplir le <strong>questionnaire technique</strong> pour « {item.product_name} » "
                "depuis votre espace client.</li>"
            )

    totals_html = f"<tr><td style='padding:6px 0;color:#666;'>Sous-total</td><td style='padding:6px 0;text-align:right;'>{order.subtotal:,.2f} $</td></tr>"
    if order.gst_amount > 0 or order.qst_amount > 0:
        totals_html += f"<tr><td style='padding:6px 0;color:#666;'>TPS (5%)</td><td style='padding:6px 0;text-align:right;'>{order.gst_amount:,.2f} $</td></tr>"
        totals_html += f"<tr><td style='padding:6px 0;color:#666;'>TVQ (9.975%)</td><td style='padding:6px 0;text-align:right;'>{order.qst_amount:,.2f} $</td></tr>"
    totals_html += f"<tr><td style='padding:6px 0;font-weight:bold;'>Total</td><td style='padding:6px 0;text-align:right;font-weight:bold;'>{order.total:,.2f} $ CAD</td></tr>"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:#2563EB;">Merci pour votre commande chez Cyber Teck Q</h2>
      <p>Bonjour {client.first_name},</p>
      <p>Nous avons bien reçu votre commande <strong>{order.order_number}</strong> :</p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0;">
        {rows_html}
        <tr><td colspan="2"><hr style="border:none;border-top:1px solid #E2E8F0;margin:8px 0;"></td></tr>
        {totals_html}
      </table>
      <p>Prochaine(s) étape(s) :</p>
      <ul>{next_steps_html}</ul>
      <p>Une rencontre par Messenger ou Zoom sera ensuite planifiée pour discuter des détails.</p>
      <p style="color:#888;font-size:13px;margin-top:30px;">— L'équipe Cyber Teck Q<br>{settings.ADMIN_NOTIFICATION_EMAIL}</p>
    </div>
    """
    success = _send(client.email, "Merci pour votre commande chez Cyber Teck Q", html)
    _notify_admin_new_order(client, order)
    return success


def _notify_admin_new_order(client: "Client", order: "Order") -> bool:
    items_list = "".join(f"<li>{item.product_name} — {item.price:,.2f} $ CAD</li>" for item in order.items)
    html = f"""
    <div style="font-family:Arial,sans-serif;">
      <h3>Nouvelle commande reçue</h3>
      <p><strong>Client :</strong> {client.first_name} {client.last_name} ({client.email})</p>
      <p><strong>Commande :</strong> {order.order_number} — Total : {order.total:,.2f} $ CAD</p>
      <ul>{items_list}</ul>
    </div>
    """
    return _send(settings.ADMIN_NOTIFICATION_EMAIL, f"Nouvelle commande : {order.order_number}", html)


def send_technical_form_email(client: "Client", order_item: "OrderItem", form_summary_html: str) -> bool:
    order_number = order_item.order.order_number
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:#2563EB;">Questionnaire technique reçu</h2>
      <p>Bonjour {client.first_name},</p>
      <p>Merci d'avoir complété le questionnaire technique pour « <strong>{order_item.product_name}</strong> »
      (commande <strong>{order_number}</strong>). Notre équipe va l'analyser et vous
      contactera prochainement par Messenger ou Zoom pour planifier une rencontre.</p>
      <p style="color:#888;font-size:13px;margin-top:30px;">— L'équipe Cyber Teck Q</p>
    </div>
    """
    client_success = _send(client.email, "Questionnaire technique reçu — Cyber Teck Q", html)

    admin_html = f"""
    <div style="font-family:Arial,sans-serif;">
      <h3>Formulaire technique soumis — {order_number} ({order_item.product_name})</h3>
      <p><strong>Client :</strong> {client.first_name} {client.last_name} ({client.email})</p>
      {form_summary_html}
    </div>
    """
    _send(settings.ADMIN_NOTIFICATION_EMAIL, f"Formulaire technique — {order_number}", admin_html)
    return client_success


def send_maintenance_contract_email(client: "Client", contract, pdf_bytes: bytes) -> bool:
    import base64
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:#2563EB;">Votre contrat de maintenance signé</h2>
      <p>Bonjour {client.first_name},</p>
      <p>Merci d'avoir signé votre contrat de maintenance <strong>{contract.contract_number}</strong>.
      Vous le trouverez ci-joint en format PDF, et vous pouvez également le consulter à tout
      moment dans votre espace client.</p>
      <p>Notre équipe vous contactera prochainement pour les prochaines étapes.</p>
      <p style="color:#888;font-size:13px;margin-top:30px;">— L'équipe Cyber Teck Q</p>
    </div>
    """
    attachment = {
        "filename": f"{contract.contract_number}.pdf",
        "content": list(base64.b64encode(pdf_bytes)),
    }
    client_success = _send(client.email, f"Contrat de maintenance signé — {contract.contract_number}", html, attachments=[attachment])

    admin_html = f"""
    <div style="font-family:Arial,sans-serif;">
      <h3>Contrat de maintenance signé — {contract.contract_number}</h3>
      <p><strong>Client :</strong> {client.first_name} {client.last_name} ({client.email})</p>
      <p><strong>Plan :</strong> {contract.maintenance_plan} — {contract.annual_price:,.2f} $ CAD/an</p>
    </div>
    """
    _send(
        settings.ADMIN_NOTIFICATION_EMAIL,
        f"Contrat de maintenance signé — {contract.contract_number}",
        admin_html,
        attachments=[attachment],
    )
    return client_success


def send_invoice_email(client: "Client", invoice: "Invoice", pdf_bytes: bytes) -> bool:
    import base64
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:#2563EB;">Votre facture Cyber Teck Q</h2>
      <p>Bonjour {client.first_name},</p>
      <p>Vous trouverez ci-joint votre facture <strong>{invoice.invoice_number}</strong>
      d'un montant total de {invoice.total:,.2f} $ CAD.</p>
      <p>Vous pouvez également la consulter à tout moment dans votre espace client.</p>
      <p style="color:#888;font-size:13px;margin-top:30px;">— L'équipe Cyber Teck Q</p>
    </div>
    """
    attachment = {
        "filename": f"{invoice.invoice_number}.pdf",
        "content": list(base64.b64encode(pdf_bytes)),
    }
    return _send(client.email, f"Facture {invoice.invoice_number} — Cyber Teck Q", html, attachments=[attachment])


def send_contact_form_email(prenom: str, nom: str, courriel: str, telephone: str, sujet: str, message: str) -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;">
      <h3>Nouveau message via le formulaire de contact</h3>
      <p><strong>Nom :</strong> {prenom} {nom}</p>
      <p><strong>Courriel :</strong> {courriel}</p>
      <p><strong>Téléphone :</strong> {telephone or 'Non fourni'}</p>
      <p><strong>Sujet :</strong> {sujet}</p>
      <p><strong>Message :</strong><br>{message}</p>
    </div>
    """
    return _send(settings.ADMIN_NOTIFICATION_EMAIL, f"Contact — {sujet}", html)


def send_password_reset_email(to_email: str, reset_link: str, recipient_name: str = "") -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:#2563EB;">Réinitialisation de mot de passe</h2>
      <p>Bonjour {recipient_name or ''},</p>
      <p>Une demande de réinitialisation de mot de passe a été effectuée.
      Si vous n'êtes pas à l'origine de cette demande, ignorez ce courriel.</p>
      <p><a href="{reset_link}" style="background:#2563EB;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;">Réinitialiser mon mot de passe</a></p>
      <p style="color:#888;font-size:13px;">Ce lien est valide pendant 1 heure.</p>
    </div>
    """
    return _send(to_email, "Réinitialisation de votre mot de passe — Cyber Teck Q", html)


def send_maintenance_renewal_reminder_email(client: "Client", contract) -> bool:
    """
    Rappel envoyé au client (et copie à l'admin) lorsqu'un contrat de
    maintenance approche de sa date d'expiration (déclenché à la connexion
    admin — voir app/services/renewal_reminders.py).
    """
    expiration_str = contract.expiration_date.strftime("%d/%m/%Y")
    renewal_link = f"{settings.FRONTEND_URL}/mon-compte.html?renew_contract={contract.id}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <h2 style="color:#2563EB;">Votre contrat de maintenance arrive à échéance</h2>
      <p>Bonjour {client.first_name},</p>
      <p>Votre contrat de maintenance <strong>{contract.contract_number}</strong> arrivera à
      échéance le <strong>{expiration_str}</strong>.</p>
      <p>Pour assurer la continuité de la maintenance de votre site (mises à jour, sauvegardes,
      sécurité), nous vous invitons à le renouveler depuis votre espace client.</p>
      <p><a href="{renewal_link}" style="background:#2563EB;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;">Renouveler mon contrat</a></p>
      <p style="color:#888;font-size:13px;margin-top:30px;">— L'équipe Cyber Teck Q</p>
    </div>
    """
    client_success = _send(client.email, f"Votre contrat {contract.contract_number} expire bientôt", html)

    admin_html = f"""
    <div style="font-family:Arial,sans-serif;">
      <h3>Rappel de renouvellement envoyé — {contract.contract_number}</h3>
      <p><strong>Client :</strong> {client.first_name} {client.last_name} ({client.email})</p>
      <p><strong>Expiration :</strong> {expiration_str}</p>
    </div>
    """
    _send(settings.ADMIN_NOTIFICATION_EMAIL, f"Rappel envoyé — contrat {contract.contract_number}", admin_html)
    return client_success
