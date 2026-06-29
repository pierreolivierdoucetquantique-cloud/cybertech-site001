"""
Vérifie si une commande est éligible au paiement.

Règle métier :
- Commandes WEBSITE / MOBILE_APP : tant que le questionnaire technique n'a
  pas été soumis, AUCUN paiement (Interac ou Stripe) ne peut être initié.
- Commandes MAINTENANCE : le questionnaire technique ne s'applique pas.
  C'est le Contrat de maintenance qui doit être signé (statut SIGNED) avant
  tout paiement.

Cette règle est appliquée ICI, côté backend, pour qu'elle ne puisse jamais
être contournée même si le frontend est modifié ou si la requête est envoyée
directement (ex: via un outil comme Postman).
"""
from app.models.order import Order, ProductType


def is_payment_unlocked(order: Order) -> bool:
    if order.product_type == ProductType.MAINTENANCE:
        contract = order.maintenance_contract
        return contract is not None and contract.status.value == "signed"
    return order.technical_form is not None


def assert_payment_unlocked(order: Order) -> None:
    from fastapi import HTTPException
    if not is_payment_unlocked(order):
        if order.product_type == ProductType.MAINTENANCE:
            detail = "Veuillez signer le contrat de maintenance avant de poursuivre votre commande."
        else:
            detail = "Veuillez compléter le questionnaire avant de poursuivre votre commande."
        raise HTTPException(status_code=400, detail=detail)
