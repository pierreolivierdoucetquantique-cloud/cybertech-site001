"""
Vérifie si un panier (Order) est éligible au paiement.

Règle métier (v9.11 — panier multi-services) :
- TOUS les OrderItem du panier doivent être débloqués pour que le paiement
  (dépôt ou solde) du panier complet soit autorisé.
- Pour un item WEBSITE / MOBILE_APP : son questionnaire technique doit avoir
  été soumis.
- Pour un item MAINTENANCE : son contrat de maintenance doit être signé
  (statut SIGNED).

Cette règle est appliquée ICI, côté backend, pour qu'elle ne puisse jamais
être contournée même si le frontend est modifié ou si la requête est envoyée
directement (ex: via un outil comme Postman).
"""
from app.models.order import Order, OrderItem, ProductType


def is_item_unlocked(item: OrderItem) -> bool:
    if item.product_type == ProductType.MAINTENANCE:
        contract = item.maintenance_contract
        return contract is not None and contract.status.value == "signed"
    return item.technical_form is not None


def is_payment_unlocked(order: Order) -> bool:
    if not order.items:
        return False
    return all(is_item_unlocked(item) for item in order.items)


def first_locked_item(order: Order) -> OrderItem | None:
    for item in order.items:
        if not is_item_unlocked(item):
            return item
    return None


def assert_payment_unlocked(order: Order) -> None:
    from fastapi import HTTPException
    locked_item = first_locked_item(order)
    if locked_item is not None:
        if locked_item.product_type == ProductType.MAINTENANCE:
            detail = (
                f"Veuillez signer le contrat de maintenance pour « {locked_item.product_name} » "
                "avant de poursuivre le paiement de cette commande."
            )
        else:
            detail = (
                f"Veuillez compléter le questionnaire technique pour « {locked_item.product_name} » "
                "avant de poursuivre le paiement de cette commande."
            )
        raise HTTPException(status_code=400, detail=detail)


def assert_amount_type_allowed(db, order: Order, amount_type) -> None:
    """
    Empêche le double-paiement : une fois qu'un dépôt (ou le montant complet)
    a été confirmé pour une commande, seul le paiement du SOLDE reste possible
    — évite qu'un client paie le "montant total" une deuxième fois après avoir
    déjà versé son dépôt de 40%.
    """
    from fastapi import HTTPException
    from app.models.payment import PaymentAmountType
    from app.services.billing import get_collected_amount

    already_paid = get_collected_amount(db, order_id=order.id)

    if already_paid > 0.01 and order.total - already_paid <= 0.01:
        raise HTTPException(status_code=400, detail="Cette commande est déjà payée intégralement.")

    if amount_type == PaymentAmountType.BALANCE and already_paid <= 0.01:
        raise HTTPException(status_code=400, detail="Aucun dépôt n'a encore été payé pour cette commande — veuillez d'abord payer le dépôt ou le montant total.")

    if amount_type in (PaymentAmountType.DEPOSIT, PaymentAmountType.FULL) and already_paid > 0.01:
        raise HTTPException(status_code=400, detail="Un paiement a déjà été effectué pour cette commande. Veuillez utiliser l'option « Payer le solde ».")
