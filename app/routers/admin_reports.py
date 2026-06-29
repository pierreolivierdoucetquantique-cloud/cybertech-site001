"""
Router : statistiques avancées / rapports pour l'admin.

Complète le tableau de bord simple (admin_dashboard.py) avec des séries de
données dans le temps et des répartitions, utiles pour des graphiques :
- revenu mensuel (12 derniers mois)
- nouvelles commandes mensuelles (12 derniers mois)
- nouveaux clients mensuels (12 derniers mois)
- répartition des commandes par statut
- répartition des commandes par type de produit
- top clients par revenu total
"""
import datetime as dt
from collections import OrderedDict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.client import Client
from app.models.order import Order, OrderStatus, ProductType
from app.models.invoice import Invoice

router = APIRouter(prefix="/api/admin/reports", tags=["admin-reports"])

MONTH_LABELS_FR = [
    "Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
    "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc",
]


def _last_n_months(n: int) -> list[tuple[int, int]]:
    """Retourne une liste de (année, mois) pour les n derniers mois, du plus ancien au plus récent."""
    today = dt.date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


@router.get("/revenue-by-month")
def revenue_by_month(
    months: int = 12,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    period = _last_n_months(months)
    buckets = OrderedDict(((y, m), 0.0) for y, m in period)

    earliest = dt.datetime(period[0][0], period[0][1], 1)
    invoices = db.query(Invoice).filter(Invoice.created_at >= earliest).all()
    for inv in invoices:
        key = (inv.created_at.year, inv.created_at.month)
        if key in buckets:
            buckets[key] += inv.total

    return {
        "labels": [f"{MONTH_LABELS_FR[m - 1]} {y}" for y, m in buckets.keys()],
        "values": [round(v, 2) for v in buckets.values()],
    }


@router.get("/orders-by-month")
def orders_by_month(
    months: int = 12,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    period = _last_n_months(months)
    buckets = OrderedDict(((y, m), 0) for y, m in period)

    earliest = dt.datetime(period[0][0], period[0][1], 1)
    orders = db.query(Order).filter(Order.created_at >= earliest).all()
    for o in orders:
        key = (o.created_at.year, o.created_at.month)
        if key in buckets:
            buckets[key] += 1

    return {
        "labels": [f"{MONTH_LABELS_FR[m - 1]} {y}" for y, m in buckets.keys()],
        "values": list(buckets.values()),
    }


@router.get("/clients-by-month")
def clients_by_month(
    months: int = 12,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    period = _last_n_months(months)
    buckets = OrderedDict(((y, m), 0) for y, m in period)

    earliest = dt.datetime(period[0][0], period[0][1], 1)
    clients = db.query(Client).filter(Client.created_at >= earliest).all()
    for c in clients:
        key = (c.created_at.year, c.created_at.month)
        if key in buckets:
            buckets[key] += 1

    return {
        "labels": [f"{MONTH_LABELS_FR[m - 1]} {y}" for y, m in buckets.keys()],
        "values": list(buckets.values()),
    }


@router.get("/orders-by-status")
def orders_by_status(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Order.status, func.count(Order.id))
        .group_by(Order.status)
        .all()
    )
    counts = {status.value: 0 for status in OrderStatus}
    for status, count in rows:
        counts[status.value if hasattr(status, "value") else status] = count
    return counts


@router.get("/orders-by-product-type")
def orders_by_product_type(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Order.product_type, func.count(Order.id))
        .group_by(Order.product_type)
        .all()
    )
    counts = {pt.value: 0 for pt in ProductType}
    for pt, count in rows:
        counts[pt.value if hasattr(pt, "value") else pt] = count
    return counts


@router.get("/top-clients")
def top_clients(
    limit: int = 10,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Client.id, Client.first_name, Client.last_name, Client.email,
            func.coalesce(func.sum(Invoice.total), 0.0).label("total_revenue"),
            func.count(Invoice.id).label("invoice_count"),
        )
        .join(Invoice, Invoice.client_id == Client.id)
        .group_by(Client.id)
        .order_by(func.sum(Invoice.total).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "client_id": r.id,
            "client_name": f"{r.first_name} {r.last_name}",
            "client_email": r.email,
            "total_revenue": round(r.total_revenue, 2),
            "invoice_count": r.invoice_count,
        }
        for r in rows
    ]
