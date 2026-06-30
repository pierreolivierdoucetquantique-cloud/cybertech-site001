"""
Générateur du Contrat de Maintenance (PDF) avec reportlab.

Même approche que invoice_pdf.py : le PDF est généré en mémoire (BytesIO),
sauvegardé sur le disk Render, et les bytes sont retournés pour l'envoi par
email — une seule génération, deux usages.

IMPORTANT — ce texte de contrat est un modèle standard rédigé pour les
besoins de la plateforme. Il ne constitue pas un avis juridique : il est
fortement recommandé de le faire réviser par un juriste avant utilisation
en production, notamment au regard du droit québécois de la consommation
et du Code civil du Québec.
"""
import io
import os
import datetime as dt

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage,
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER, TA_JUSTIFY

from app.config import settings

PRIMARY_COLOR = colors.HexColor("#2563EB")
TEXT_COLOR = colors.HexColor("#0F172A")
SOFT_COLOR = colors.HexColor("#64748B")
BORDER_COLOR = colors.HexColor("#E2E8F0")

MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def _date_fr(d) -> str:
    return f"{d.day} {MONTHS_FR[d.month]} {d.year}"


CTQ_COMMITMENTS = [
    "Maintenance annuelle du site web couvert par le présent contrat.",
    "Correction des bogues relevés sur les fonctionnalités existantes du site (portée couverte).",
    "Mises à jour logicielles courantes (système, dépendances, plugins).",
    "Surveillance de la performance du site.",
    "Surveillance de la sécurité du site.",
    "Assistance technique par courriel pendant la durée du contrat.",
    "Maintenance planifiée selon les besoins identifiés.",
]

CLIENT_COMMITMENTS = [
    "Respecter les conditions du présent contrat.",
    "Maintenir une communication active avec Cyber Teck Q pour toute demande liée au site.",
    "Fournir les informations nécessaires à la bonne exécution de la maintenance.",
    "Respecter l'échéancier de paiement convenu.",
    "S'abstenir de toute modification non autorisée du site sans en informer Cyber Teck Q au préalable.",
]


def generate_maintenance_contract_pdf(
    contract_number: str,
    creation_date: dt.datetime,
    client_full_name: str,
    company_name: str | None,
    client_email: str,
    client_phone: str | None,
    website_concerned: str | None,
    maintenance_plan: str,
    annual_price: float,
    contract_duration_months: int,
    effective_date,
    expiration_date,
    signer_name: str | None,
    signature_type: str | None,
    client_signature_data: str | None,
    accepted_terms: bool,
    signed_at: dt.datetime | None,
    admin_signature_name: str | None,
    admin_signed_at: dt.datetime | None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    style_brand = ParagraphStyle("brand", parent=styles["Heading1"], fontSize=20, textColor=PRIMARY_COLOR, spaceAfter=2)
    style_tagline = ParagraphStyle("tagline", parent=styles["Normal"], fontSize=9, textColor=SOFT_COLOR)
    style_title = ParagraphStyle("title", parent=styles["Heading2"], fontSize=14, textColor=TEXT_COLOR, alignment=TA_RIGHT)
    style_num = ParagraphStyle("num", parent=styles["Normal"], fontSize=10, textColor=SOFT_COLOR, alignment=TA_RIGHT)
    style_value = ParagraphStyle("value", parent=styles["Normal"], fontSize=10, textColor=TEXT_COLOR)
    style_section_title = ParagraphStyle("section", parent=styles["Heading3"], fontSize=12, textColor=PRIMARY_COLOR, spaceBefore=14, spaceAfter=6)
    style_body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5, textColor=TEXT_COLOR, alignment=TA_JUSTIFY, leading=14)
    style_bullet = ParagraphStyle("bullet", parent=style_body, leftIndent=12, spaceAfter=3)
    style_footer = ParagraphStyle("footer", parent=styles["Normal"], fontSize=8.5, textColor=SOFT_COLOR, alignment=TA_CENTER)
    style_label = ParagraphStyle("label", parent=styles["Normal"], fontSize=9, textColor=SOFT_COLOR)

    elements = []

    # --- En-tête ---
    header_table = Table(
        [[
            Paragraph("Cyber Teck Q", style_brand),
            Paragraph(f"CONTRAT DE MAINTENANCE<br/><font size=10 color='#64748B'>{contract_number}</font>", style_title),
        ]],
        colWidths=[None, None],
    )
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(header_table)
    elements.append(Paragraph("Conception &amp; Développement &amp; Performance", style_tagline))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", color=BORDER_COLOR, thickness=1))
    elements.append(Spacer(1, 14))

    # --- Parties ---
    company_line = f"<br/><font size=9 color='#64748B'>{company_name}</font>" if company_name else ""
    phone_line = f"<br/><font size=9 color='#64748B'>{client_phone}</font>" if client_phone else ""
    website_line = f"<br/><font size=9 color='#64748B'>Site concerné : {website_concerned}</font>" if website_concerned else ""

    info_table = Table(
        [[
            Paragraph(
                f"<font color='#64748B' size=9>ENTRE</font><br/>"
                f"<font size=11><b>Cyber Teck Q</b></font><br/>"
                f"<font size=9 color='#64748B'>{settings.ADMIN_NOTIFICATION_EMAIL}</font>",
                style_value,
            ),
            Paragraph(
                f"<font color='#64748B' size=9>ET</font><br/>"
                f"<font size=11><b>{client_full_name}</b></font>{company_line}<br/>"
                f"<font size=9 color='#64748B'>{client_email}</font>{phone_line}{website_line}",
                style_value,
            ),
        ]],
        colWidths=[None, None],
    )
    info_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    # --- Détails du contrat ---
    details_data = [
        ["N° de contrat", contract_number, "Date de création", _date_fr(creation_date)],
        ["Plan de maintenance", maintenance_plan, "Prix annuel", f"{annual_price:,.2f} $ CAD"],
        ["Durée du contrat", f"{contract_duration_months} mois", "Date d'entrée en vigueur", _date_fr(effective_date)],
        ["Date d'expiration", _date_fr(expiration_date), "", ""],
    ]
    label_style = ParagraphStyle("dlabel", parent=styles["Normal"], fontSize=9, textColor=SOFT_COLOR)
    value_style = ParagraphStyle("dvalue", parent=styles["Normal"], fontSize=9, textColor=TEXT_COLOR, fontName="Helvetica-Bold")
    details_data = [
        [Paragraph(r[0], label_style), Paragraph(str(r[1]), value_style) if r[1] else "",
         Paragraph(r[2], label_style) if r[2] else "", Paragraph(str(r[3]), value_style) if r[3] else ""]
        for r in details_data
    ]
    details_table = Table(details_data, colWidths=[95, 160, 115, None])
    details_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER_COLOR),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 4))

    # --- Engagements Cyber Teck Q ---
    elements.append(Paragraph("Engagements de Cyber Teck Q", style_section_title))
    for item in CTQ_COMMITMENTS:
        elements.append(Paragraph(f"•&nbsp;&nbsp;{item}", style_bullet))

    # --- Engagements client ---
    elements.append(Paragraph("Engagements du client", style_section_title))
    for item in CLIENT_COMMITMENTS:
        elements.append(Paragraph(f"•&nbsp;&nbsp;{item}", style_bullet))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "Le présent contrat est conclu pour la durée indiquée ci-dessus et se renouvelle "
        "selon les conditions communiquées par Cyber Teck Q avant l'échéance. Toute "
        "résiliation doit être communiquée par écrit à l'adresse courriel ci-dessus.",
        style_body,
    ))
    elements.append(Spacer(1, 16))

    # --- Signatures ---
    elements.append(HRFlowable(width="100%", color=BORDER_COLOR, thickness=1))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Signatures", style_section_title))

    if accepted_terms:
        elements.append(Paragraph(
            "[X] J'ai lu et j'accepte les termes du présent contrat de maintenance.",
            ParagraphStyle("accept", parent=style_body, textColor=PRIMARY_COLOR, fontName="Helvetica-Bold"),
        ))
        elements.append(Spacer(1, 10))

    sig_cells = []

    # Cellule signature client
    client_sig_flowables = [Paragraph("<font color='#64748B' size=9>SIGNATURE DU CLIENT</font>", style_label), Spacer(1, 6)]
    if signature_type == "drawn" and client_signature_data and client_signature_data.startswith("data:image"):
        try:
            img_bytes = _decode_data_url(client_signature_data)
            img = RLImage(io.BytesIO(img_bytes), width=160, height=60)
            client_sig_flowables.append(img)
        except Exception:
            client_sig_flowables.append(Paragraph(f"<font size=14><i>{signer_name or ''}</i></font>", style_value))
    elif signer_name:
        client_sig_flowables.append(Paragraph(f"<font size=16><i>{signer_name}</i></font>", style_value))
    client_sig_flowables.append(Spacer(1, 8))
    client_sig_flowables.append(Paragraph(f"<font size=9>{signer_name or ''}</font>", style_value))
    if signed_at:
        client_sig_flowables.append(Spacer(1, 2))
        client_sig_flowables.append(Paragraph(f"<font size=8 color='#64748B'>Signé le {_date_fr(signed_at)}</font>", style_label))
    sig_cells.append(client_sig_flowables)

    # Cellule signature admin
    admin_sig_flowables = [Paragraph("<font color='#64748B' size=9>SIGNATURE DE L'ADMINISTRATEUR</font>", style_label), Spacer(1, 6)]
    if admin_signature_name:
        admin_sig_flowables.append(Paragraph(f"<font size=16><i>{admin_signature_name}</i></font>", style_value))
        if admin_signed_at:
            admin_sig_flowables.append(Spacer(1, 8))
            admin_sig_flowables.append(Paragraph(f"<font size=8 color='#64748B'>Signé le {_date_fr(admin_signed_at)}</font>", style_label))
    else:
        admin_sig_flowables.append(Spacer(1, 24))
        admin_sig_flowables.append(Paragraph("<font size=9 color='#64748B'>En attente</font>", style_label))
    sig_cells.append(admin_sig_flowables)

    sig_table = Table([sig_cells], colWidths=[None, None])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 20))

    elements.append(HRFlowable(width="100%", color=BORDER_COLOR, thickness=1))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"Cyber Teck Q &nbsp;•&nbsp; {settings.ADMIN_NOTIFICATION_EMAIL} &nbsp;•&nbsp; Document généré électroniquement",
        style_footer,
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _decode_data_url(data_url: str) -> bytes:
    import base64
    header, encoded = data_url.split(",", 1)
    return base64.b64decode(encoded)


def save_maintenance_contract_pdf(pdf_bytes: bytes, contract_number: str) -> str:
    """Sauvegarde le PDF sur le disk et retourne le chemin."""
    contracts_dir = os.path.join(os.path.dirname(settings.DATABASE_PATH), "maintenance_contracts")
    os.makedirs(contracts_dir, exist_ok=True)
    filename = f"{contract_number}.pdf"
    path = os.path.join(contracts_dir, filename)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path
