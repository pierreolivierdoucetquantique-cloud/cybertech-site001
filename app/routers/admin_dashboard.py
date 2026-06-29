"""Router : tableau de bord admin (statistiques)."""
import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.client import Client
from app.models.order import Order, OrderStatus, ProductType, PaymentStatus
from app.models.invoice import Invoice
from app.schemas.admin_schemas import DashboardStats

router = APIRouter(prefix="/api/admin/dashboard", tags=["admin-dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    total_clients = db.query(func.count(Client.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_invoices = db.query(func.count(Invoice.id)).scalar() or 0
    total_revenue = db.query(func.coalesce(func.sum(Invoice.total), 0.0)).scalar() or 0.0

    pending = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.PENDING).scalar() or 0
    processing = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.PROCESSING).scalar() or 0
    delivered = db.query(func.count(Order.id)).filter(Order.status == OrderStatus.DELIVERED).scalar() or 0

    active_maintenance = (
        db.query(func.count(Order.id))
        .filter(
            Order.product_type == ProductType.MAINTENANCE,
            Order.payment_status.in_([PaymentStatus.DEPOSIT_PAID, PaymentStatus.PAID]),
            Order.status != OrderStatus.CANCELLED,
        )
        .scalar() or 0
    )

    thirty_days_ago = dt.datetime.utcnow() - dt.timedelta(days=30)
    recent_registrations = (
        db.query(func.count(Client.id)).filter(Client.created_at >= thirty_days_ago).scalar() or 0
    )

    return DashboardStats(
        total_clients=total_clients,
        total_orders=total_orders,
        total_invoices=total_invoices,
        total_revenue=round(total_revenue, 2),
        pending_orders=pending,
        processing_orders=processing,
        delivered_orders=delivered,
        active_maintenance_contracts=active_maintenance,
        recent_registrations=recent_registrations,
    )
