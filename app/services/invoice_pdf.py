"""
Générateur de factures PDF avec reportlab.

Le PDF est généré en mémoire (BytesIO) puis sauvegardé sur le disk Render
ET retourné en bytes pour l'envoi par email — une seule génération, deux usages.
"""
import io
import os
import datetime as dt

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

from app.config import settings

PRIMARY_COLOR = colors.HexColor("#2563EB")
TEXT_COLOR = colors.HexColor("#0F172A")
SOFT_COLOR = colors.HexColor("#64748B")
BORDER_COLOR = colors.HexColor("#E2E8F0")


def generate_invoice_pdf(
    invoice_number: str,
    client_full_name: str,
    client_email: str,
    client_address_lines: list[str],
    purchase_date: dt.datetime,
    product_name: str,
    product_description: str,
    subtotal: float,
    gst_amount: float,
    qst_amount: float,
    total: float,
    payment_instructions: str,
) -> bytes:
    """Construit le PDF de facture en mémoire et retourne les bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    style_brand = ParagraphStyle("brand", parent=styles["Heading1"], fontSize=20, textColor=PRIMARY_COLOR, spaceAfter=2)
    style_tagline = ParagraphStyle("tagline", parent=styles["Normal"], fontSize=9, textColor=SOFT_COLOR)
    style_invoice_title = ParagraphStyle("invoice_title", parent=styles["Heading2"], fontSize=14, textColor=TEXT_COLOR, alignment=TA_RIGHT)
    style_invoice_num = ParagraphStyle("invoice_num", parent=styles["Normal"], fontSize=10, textColor=SOFT_COLOR, alignment=TA_RIGHT)
    style_label = ParagraphStyle("label", parent=styles["Normal"], fontSize=9, textColor=SOFT_COLOR)
    style_value = ParagraphStyle("value", parent=styles["Normal"], fontSize=10, textColor=TEXT_COLOR)
    style_footer = ParagraphStyle("footer", parent=styles["Normal"], fontSize=8.5, textColor=SOFT_COLOR, alignment=TA_CENTER)
    style_thanks = ParagraphStyle("thanks", parent=styles["Normal"], fontSize=11, textColor=PRIMARY_COLOR, alignment=TA_CENTER, spaceBefore=10)

    elements = []

    # --- En-tête : marque + titre facture ---
    header_table = Table(
        [[
            Paragraph("Cyber Teck Q", style_brand),
            Paragraph(f"FACTURE<br/><font size=10 color='#64748B'>{invoice_number}</font>", style_invoice_title),
        ]],
        colWidths=[None, None],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(header_table)
    elements.append(Paragraph("Conception &amp; Développement &amp; Performance", style_tagline))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", color=BORDER_COLOR, thickness=1))
    elements.append(Spacer(1, 14))

    # --- Informations client / date ---
    MONTHS_FR = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
        7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
    }
    date_fr = f"{purchase_date.day} {MONTHS_FR[purchase_date.month]} {purchase_date.year}"

    address_html = "<br/>".join(client_address_lines) if client_address_lines else ""
    info_table = Table(
        [[
            Paragraph(
                f"<font color='#64748B' size=9>FACTURÉ À</font><br/>"
                f"<font size=11>{client_full_name}</font><br/>"
                f"<font size=9 color='#64748B'>{client_email}</font><br/>"
                f"<font size=9 color='#64748B'>{address_html}</font>",
                style_value,
            ),
            Paragraph(
                f"<font color='#64748B' size=9>DATE D'ACHAT</font><br/>"
                f"<font size=11>{date_fr}</font>",
                ParagraphStyle("dateval", parent=style_value, alignment=TA_RIGHT),
            ),
        ]],
        colWidths=[None, None],
    )
    info_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(info_table)
    elements.append(Spacer(1, 24))

    # --- Tableau des produits ---
    table_header_style = ParagraphStyle("th", parent=styles["Normal"], fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")
    table_cell_style = ParagraphStyle("td", parent=styles["Normal"], fontSize=10, textColor=TEXT_COLOR)
    table_cell_desc_style = ParagraphStyle("tdd", parent=styles["Normal"], fontSize=8.5, textColor=SOFT_COLOR)

    data = [
        [Paragraph("Description", table_header_style), Paragraph("Montant", table_header_style)],
        [
            Paragraph(f"<b>{product_name}</b><br/>{product_description}", table_cell_style),
            Paragraph(f"{subtotal:,.2f} $", ParagraphStyle("amt", parent=table_cell_style, alignment=TA_RIGHT)),
        ],
    ]
    product_table = Table(data, colWidths=[None, 90])
    product_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 12),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 1), (-1, 1), 0.5, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(product_table)
    elements.append(Spacer(1, 14))

    # --- Totaux ---
    totals_data = [
        ["Sous-total", f"{subtotal:,.2f} $"],
        ["TPS (5%)", f"{gst_amount:,.2f} $"],
        ["TVQ (9.975%)", f"{qst_amount:,.2f} $"],
        ["TOTAL", f"{total:,.2f} $ CAD"],
    ]
    totals_table = Table(totals_data, colWidths=[None, 90])
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -2), 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -2), SOFT_COLOR),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), PRIMARY_COLOR),
        ("LINEABOVE", (0, -1), (-1, -1), 1, PRIMARY_COLOR),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    # Aligner le tableau de totaux à droite de la page
    wrapper = Table([[totals_table]], colWidths=[None])
    wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "RIGHT")]))
    elements.append(totals_table)
    elements.append(Spacer(1, 26))

    # --- Instructions de paiement ---
    elements.append(HRFlowable(width="100%", color=BORDER_COLOR, thickness=1))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<font color='#0F172A' size=10><b>Conditions de paiement</b></font>", style_value))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(payment_instructions, style_label))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Merci de faire confiance à Cyber Teck Q pour votre projet.", style_thanks))
    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", color=BORDER_COLOR, thickness=1))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"Cyber Teck Q &nbsp;•&nbsp; {settings.ADMIN_NOTIFICATION_EMAIL} &nbsp;•&nbsp; Facture générée automatiquement",
        style_footer,
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def save_invoice_pdf(pdf_bytes: bytes, invoice_number: str) -> str:
    """Sauvegarde le PDF sur le disk et retourne le chemin relatif."""
    invoices_dir = os.path.join(os.path.dirname(settings.DATABASE_PATH), "invoices")
    os.makedirs(invoices_dir, exist_ok=True)
    filename = f"{invoice_number}.pdf"
    path = os.path.join(invoices_dir, filename)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path
