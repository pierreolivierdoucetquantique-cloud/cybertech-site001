"""
Router : contrat de maintenance électronique (côté client), un par OrderItem (v9.11).

Remplace le questionnaire technique pour les OrderItem de type MAINTENANCE.
Cycle de vie : un contrat DRAFT est créé/mis à jour autant de fois que
nécessaire par le client (informations de base), puis signé une seule fois
(passage à SIGNED, verrouillage définitif, génération du PDF, envoi des
emails). Une fois SIGNED, plus aucune modification n'est possible.
"""
import datetime as dt
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_client
from app.models.client import Client
from app.models.order import Order, OrderItem, ProductType
from app.models.maintenance_contract import MaintenanceContract, ContractStatus
from app.schemas.maintenance_contract_schemas import (
    MaintenanceContractInfoIn, MaintenanceContractSignIn, MaintenanceContractOut,
)
from app.services.numbering import next_maintenance_contract_number
from app.services.maintenance_contract_pdf import generate_maintenance_contract_pdf, save_maintenance_contract_pdf
from app.services.email_service import send_maintenance_contract_email
from app.services.audit import log_action

router = APIRouter(prefix="/api/order-items/{order_item_id}/maintenance-contract", tags=["maintenance-contract"])

CONTRACT_DURATION_MONTHS = 12


def _add_months(d: dt.date, months: int) -> dt.date:
    """Ajoute un nombre de mois à une date, sans dépendance externe (gère le débordement de jour)."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    import calendar
    day = min(d.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _get_owned_maintenance_item(order_item_id: str, client: Client, db: Session) -> OrderItem:
    item = (
        db.query(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(OrderItem.id == order_item_id, Order.client_id == client.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Service introuvable dans votre commande.")
    if item.product_type != ProductType.MAINTENANCE:
        raise HTTPException(status_code=400, detail="Ce service n'est pas un contrat de maintenance.")
    return item


@router.get("", response_model=MaintenanceContractOut)
def get_contract(
    order_item_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    item = _get_owned_maintenance_item(order_item_id, client, db)
    if not item.maintenance_contract:
        raise HTTPException(status_code=404, detail="Aucun contrat trouvé pour ce service.")
    return item.maintenance_contract


@router.put("", response_model=MaintenanceContractOut)
def upsert_contract_info(
    order_item_id: str,
    payload: MaintenanceContractInfoIn,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """
    Crée le contrat (DRAFT) s'il n'existe pas encore, ou met à jour ses
    informations s'il existe et n'est pas encore signé.
    """
    item = _get_owned_maintenance_item(order_item_id, client, db)
    contract = item.maintenance_contract

    if contract and contract.status == ContractStatus.SIGNED:
        raise HTTPException(status_code=400, detail="Ce contrat est déjà signé et ne peut plus être modifié.")

    today = dt.date.today()
    if not contract:
        contract = MaintenanceContract(
            contract_number=next_maintenance_contract_number(db),
            order_item_id=item.id,
            client_id=client.id,
            annual_price=item.price,
            effective_date=today,
            expiration_date=_add_months(today, CONTRACT_DURATION_MONTHS),
            contract_duration_months=CONTRACT_DURATION_MONTHS,
            **payload.model_dump(),
        )
        db.add(contract)
    else:
        for key, value in payload.model_dump().items():
            setattr(contract, key, value)

    db.commit()
    db.refresh(contract)
    return contract


@router.get("/download")
def download_contract(
    order_item_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    item = _get_owned_maintenance_item(order_item_id, client, db)
    contract = item.maintenance_contract
    if not contract or contract.status != ContractStatus.SIGNED or not contract.pdf_path or not os.path.exists(contract.pdf_path):
        raise HTTPException(status_code=404, detail="Le PDF de ce contrat n'est pas encore disponible.")
    return FileResponse(
        contract.pdf_path,
        media_type="application/pdf",
        filename=f"{contract.contract_number}.pdf",
    )


@router.post("/sign", response_model=MaintenanceContractOut)
def sign_contract(
    order_item_id: str,
    payload: MaintenanceContractSignIn,
    request: Request,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    item = _get_owned_maintenance_item(order_item_id, client, db)
    contract = item.maintenance_contract

    if not contract:
        raise HTTPException(status_code=400, detail="Veuillez d'abord compléter les informations du contrat.")
    if contract.status == ContractStatus.SIGNED:
        raise HTTPException(status_code=400, detail="Ce contrat a déjà été signé.")
    if not payload.accepted_terms:
        raise HTTPException(status_code=400, detail="Vous devez accepter les termes du contrat pour signer.")

    contract.signer_name = payload.signer_name
    contract.client_signature_data = payload.client_signature_data
    contract.signature_type = payload.signature_type
    contract.accepted_terms = True
    contract.signed_at = dt.datetime.utcnow()
    contract.signed_ip_address = _client_ip(request)

    # Signature administrateur appliquée automatiquement (Cyber Teck Q), au nom de l'entreprise
    contract.admin_signature_name = "Cyber Teck Q"
    contract.admin_signed_at = dt.datetime.utcnow()

    contract.status = ContractStatus.SIGNED
    db.commit()
    db.refresh(contract)

    pdf_bytes = generate_maintenance_contract_pdf(
        contract_number=contract.contract_number,
        creation_date=contract.created_at,
        client_full_name=contract.client_full_name,
        company_name=contract.company_name,
        client_email=contract.client_email,
        client_phone=contract.client_phone,
        website_concerned=contract.website_concerned,
        maintenance_plan=contract.maintenance_plan,
        annual_price=contract.annual_price,
        contract_duration_months=contract.contract_duration_months,
        effective_date=contract.effective_date,
        expiration_date=contract.expiration_date,
        signer_name=contract.signer_name,
        signature_type=contract.signature_type,
        client_signature_data=contract.client_signature_data,
        accepted_terms=contract.accepted_terms,
        signed_at=contract.signed_at,
        admin_signature_name=contract.admin_signature_name,
        admin_signed_at=contract.admin_signed_at,
    )
    pdf_path = save_maintenance_contract_pdf(pdf_bytes, contract.contract_number)
    contract.pdf_path = pdf_path
    db.commit()
    db.refresh(contract)

    log_action(
        db, actor_type="client", actor_id=client.id, action="sign_maintenance_contract",
        target_type="order_item", target_id=item.id, details=contract.contract_number,
        ip_address=_client_ip(request),
    )

    send_maintenance_contract_email(client, contract, pdf_bytes)

    return contract
