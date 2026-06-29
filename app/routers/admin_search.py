"""
Router : recherche globale pour l'admin.

Permet de chercher un client, une commande ou une facture depuis une seule
barre de recherche, sans devoir deviner dans quel onglet l'information se
trouve. Les résultats indiquent le type pour permettre au frontend de
naviguer directement vers le bon onglet / la bonne fiche.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.client import Client
from app.models.order import Order
from app.models.invoice import Invoice

router = APIRouter(prefix="/api/admin/search", tags=["admin-search"])

MAX_RESULTS_PER_TYPE = 8


@router.get("")
def global_search(
    q: str = Query(..., min_length=2),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    like = f"%{q.strip()}%"
    results = []

    clients = (
        db.query(Client)
        .filter(or_(Client.first_name.ilike(like), Client.last_name.ilike(like), Client.email.ilike(like)))
        .limit(MAX_RESULTS_PER_TYPE)
        .all()
    )
    for c in clients:
        results.append({
            "type": "client",
            "id": c.id,
            "title": f"{c.first_name} {c.last_name}",
            "subtitle": c.email,
            "panel": "clients",
        })

    orders = (
        db.query(Order)
        .join(Client, Order.client_id == Client.id)
        .filter(or_(
            Order.order_number.ilike(like),
            Order.product_name.ilike(like),
            Client.first_name.ilike(like),
            Client.last_name.ilike(like),
        ))
        .limit(MAX_RESULTS_PER_TYPE)
        .all()
    )
    for o in orders:
        results.append({
            "type": "order",
            "id": o.id,
            "title": o.order_number,
            "subtitle": f"{o.client.first_name} {o.client.last_name} — {o.product_name}",
            "panel": "orders",
        })

    invoices = (
        db.query(Invoice)
        .join(Client, Invoice.client_id == Client.id)
        .filter(or_(
            Invoice.invoice_number.ilike(like),
            Client.first_name.ilike(like),
            Client.last_name.ilike(like),
        ))
        .limit(MAX_RESULTS_PER_TYPE)
        .all()
    )
    for inv in invoices:
        results.append({
            "type": "invoice",
            "id": inv.id,
            "title": inv.invoice_number,
            "subtitle": f"{inv.client.first_name} {inv.client.last_name} — {inv.total:,.2f} $ CAD",
            "panel": "invoices",
        })

    return {"query": q, "results": results, "count": len(results)}
