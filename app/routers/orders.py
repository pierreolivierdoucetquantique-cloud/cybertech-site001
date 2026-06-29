"""Router : marketplace et commandes côté client."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_client
from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.schemas.order_schemas import ProductOut, OrderCreate, OrderOut
from app.services.catalog import list_products, get_product
from app.services.numbering import next_order_number
from app.services.audit import log_action
from app.services.email_service import send_order_confirmation_email

router = APIRouter(prefix="/api", tags=["marketplace"])


@router.get("/marketplace", response_model=list[ProductOut])
def get_marketplace():
    return list_products()


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(
    payload: OrderCreate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    product = get_product(payload.product_type)

    order = Order(
        order_number=next_order_number(db),
        client_id=client.id,
        product_type=product.product_type,
        product_name=product.name,
        price=product.price,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    log_action(db, actor_type="client", actor_id=client.id, action="create_order", target_type="order", target_id=order.id)

    # Email de confirmation (best-effort : ne bloque jamais la commande si l'email échoue)
    send_order_confirmation_email(client, order)

    return _to_order_out(order)


@router.get("/orders", response_model=list[OrderOut])
def list_my_orders(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    orders = db.query(Order).filter(Order.client_id == client.id).order_by(Order.created_at.desc()).all()
    return [_to_order_out(o) for o in orders]


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id, Order.client_id == client.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    return _to_order_out(order)


@router.delete("/orders/{order_id}")
def delete_order(
    order_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """
    Permet au client de supprimer une commande de 'son panier'. Seules les
    commandes encore en attente (PENDING) et non payées peuvent être
    supprimées par le client — une fois le travail commencé ou un paiement
    reçu, seul l'admin peut modifier la commande, pour préserver l'historique.
    """
    order = db.query(Order).filter(Order.id == order_id, Order.client_id == client.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Seules les commandes en attente peuvent être supprimées.")

    log_action(db, actor_type="client", actor_id=client.id, action="delete_order", target_type="order", target_id=order.id, details=order.order_number)
    db.delete(order)
    db.commit()
    return {"message": "Commande supprimée."}


def _to_order_out(order: Order) -> OrderOut:
    from app.services.progress_utils import step_label_for, color_for
    from app.services.payment_gate import is_payment_unlocked
    mc = order.maintenance_contract
    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        product_type=order.product_type,
        product_name=order.product_name,
        price=order.price,
        status=order.status,
        payment_status=order.payment_status,
        project_progress=order.project_progress,
        progress_step_label=step_label_for(order.project_progress),
        progress_color=color_for(order.project_progress),
        expected_delivery_date=order.expected_delivery_date,
        updated_at=order.updated_at,
        created_at=order.created_at,
        has_technical_form=order.technical_form is not None,
        has_invoice=order.invoice is not None,
        payment_unlocked=is_payment_unlocked(order),
        has_maintenance_contract=mc is not None,
        maintenance_contract_signed=mc is not None and mc.status.value == "signed",
    )
