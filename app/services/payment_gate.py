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
