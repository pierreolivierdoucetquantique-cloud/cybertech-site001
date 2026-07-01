"""Router : gestion des clients par l'admin (CRM)."""
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.client import Client, ClientSession
from app.models.order import Order
from app.schemas.admin_schemas import ClientAdminOut
from app.services.audit import log_action
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/api/admin/clients", tags=["admin-clients"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("", response_model=list[ClientAdminOut])
def list_clients(
    search: Optional[str] = Query(None, description="Recherche par nom ou courriel"),
    is_active: Optional[bool] = Query(None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Client)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Client.first_name.ilike(like), Client.last_name.ilike(like), Client.email.ilike(like))
        )
    if is_active is not None:
        query = query.filter(Client.is_active == is_active)

    clients = query.order_by(Client.created_at.desc()).all()

    results = []
    for c in clients:
        order_count = db.query(func.count(Order.id)).filter(Order.client_id == c.id).scalar() or 0
        out = ClientAdminOut.model_validate(c)
        out.order_count = order_count
        results.append(out)
    return results


@router.get("/{client_id}/profile")
def get_client_profile(client_id: str, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """
    Fiche client complète : infos de base + tout l'historique (commandes,
    factures, formulaire technique, documents envoyés) sur un seul appel,
    pour éviter d'avoir à chercher dans 4 onglets différents.
    """
    from app.models.invoice import Invoice
    from app.services.billing import get_collected_amount
    from app.models.technical_form import TechnicalForm
    from app.models.upload import UploadedFile
    from app.services.progress_utils import step_label_for

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    orders = db.query(Order).filter(Order.client_id == client_id).order_by(Order.created_at.desc()).all()
    orders_out = []
    for o in orders:
        items_out = [
            {
                "id": item.id,
                "product_type": item.product_type,
                "product_name": item.product_name,
                "price": item.price,
                "project_progress": item.project_progress,
                "progress_step_label": step_label_for(item.project_progress),
                "has_technical_form": item.technical_form is not None,
                "has_maintenance_contract": item.maintenance_contract is not None,
            }
            for item in o.items
        ]
        orders_out.append({
            "id": o.id,
            "order_number": o.order_number,
            "items": items_out,
            "subtotal": o.subtotal,
            "total": o.total,
            "status": o.status,
            "payment_status": o.payment_status,
            "has_invoice": o.invoice is not None,
            "created_at": o.created_at,
        })

    invoices = db.query(Invoice).filter(Invoice.client_id == client_id).order_by(Invoice.created_at.desc()).all()
    invoices_out = [
        {
            "id": inv.id, "invoice_number": inv.invoice_number, "order_id": inv.order_id,
            "total": inv.total, "created_at": inv.created_at,
        }
        for inv in invoices
    ]

    # v9.11 : TechnicalForm est lié à un OrderItem ; on remonte l'order_number via l'item pour l'affichage.
    technical_forms = db.query(TechnicalForm).filter(TechnicalForm.client_id == client_id).all()
    technical_forms_out = [
        {
            "id": f.id,
            "order_item_id": f.order_item_id,
            "order_number": f.order_item.order.order_number if f.order_item else None,
            "company_name": f.company_name,
            "submitted_at": f.submitted_at,
        }
        for f in technical_forms
    ]

    documents = (
        db.query(UploadedFile)
        .filter(UploadedFile.related_client_id == client_id, UploadedFile.category == "client_document")
        .order_by(UploadedFile.created_at.desc())
        .all()
    )
    documents_out = [
        {"id": d.id, "filename": d.original_filename, "created_at": d.created_at}
        for d in documents
    ]

    total_revenue = get_collected_amount(db, client_id=client_id)

    return {
        "client": ClientAdminOut.model_validate(client).model_dump() | {"order_count": len(orders)},
        "orders": orders_out,
        "invoices": invoices_out,
        "technical_forms": technical_forms_out,
        "documents": documents_out,
        "total_revenue": round(total_revenue, 2),
    }


@router.get("/{client_id}", response_model=ClientAdminOut)
def get_client(client_id: str, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable.")
    order_count = db.query(func.count(Order.id)).filter(Order.client_id == client.id).scalar() or 0
    out = ClientAdminOut.model_validate(client)
    out.order_count = order_count
    return out


@router.post("/{client_id}/disable")
def disable_client(client_id: str, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable.")
    client.is_active = False
    # Révoque toutes les sessions actives immédiatement
    db.query(ClientSession).filter(ClientSession.client_id == client.id).update({"revoked": True})
    db.commit()
    log_action(db, actor_type="admin", actor_id=admin.id, action="disable_client", target_type="client", target_id=client.id, ip_address=_client_ip(request))
    return {"message": "Client désactivé."}


@router.post("/{client_id}/enable")
def enable_client(client_id: str, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable.")
    client.is_active = True
    db.commit()
    log_action(db, actor_type="admin", actor_id=admin.id, action="enable_client", target_type="client", target_id=client.id, ip_address=_client_ip(request))
    return {"message": "Client réactivé."}


@router.delete("/{client_id}")
def delete_client(client_id: str, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable.")
    email = client.email
    log_action(db, actor_type="admin", actor_id=admin.id, action="delete_client", target_type="client", target_id=client_id, details=email, ip_address=_client_ip(request))
    db.delete(client)
    db.commit()
    return {"message": "Client et toutes ses données supprimés."}


@router.post("/{client_id}/send-password-reset")
def admin_send_password_reset(client_id: str, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """L'admin déclenche l'envoi d'un lien de réinitialisation au client (sans connaître son mot de passe)."""
    import secrets
    from app.config import settings

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    token = secrets.token_urlsafe(32)
    client.password_reset_token = token
    client.password_reset_expires = dt.datetime.utcnow() + dt.timedelta(hours=1)
    db.commit()

    reset_link = f"{settings.FRONTEND_URL}/reset-password.html?token={token}"

    log_action(db, actor_type="admin", actor_id=admin.id, action="send_password_reset", target_type="client", target_id=client.id, ip_address=_client_ip(request))
    send_password_reset_email(client.email, reset_link, client.first_name)
    return {"message": f"Lien de réinitialisation envoyé à {client.email}."}
