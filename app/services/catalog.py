"""
Catalogue des produits du marketplace client.
Statique pour l'instant (correspond aux tarifs du site public) — pourra être
relié au CMS plus tard si l'admin veut changer les prix sans redéployer.
"""
from app.models.order import ProductType
from app.schemas.order_schemas import ProductOut

CATALOG: dict[ProductType, ProductOut] = {
    ProductType.WEBSITE: ProductOut(
        product_type=ProductType.WEBSITE,
        name="Création de site Web",
        description="Un site conçu autour de vos objectifs, rapide, bien structuré, et pensé pour convertir vos visiteurs en clients.",
        price=1300.00,
        image_url="/assets/marketplace/website.png",
        features=["Responsive", "SEO", "Design sur mesure", "Optimisation de la performance", "3 révisions gratuites"],
    ),
    ProductType.MOBILE_APP: ProductOut(
        product_type=ProductType.MOBILE_APP,
        name="Application Mobile",
        description="Une présence mobile soignée, pensée pour vos clients où qu'ils se trouvent.",
        price=399.00,
        image_url="/assets/marketplace/mobile-app.png",
        features=["Android", "iOS", "Interface moderne (UI)", "Publication sur les boutiques d'applications"],
    ),
    ProductType.MAINTENANCE: ProductOut(
        product_type=ProductType.MAINTENANCE,
        name="Contrat de Maintenance",
        description="Assurez la performance, la sécurité et la tranquillité d'esprit de votre site web, en continu.",
        price=499.00,
        image_url="/assets/marketplace/maintenance.png",
        features=["Mises à jour", "Sauvegardes", "Sécurité renforcée", "Optimisation", "Support prioritaire"],
    ),
}


def get_product(product_type: ProductType) -> ProductOut:
    return CATALOG[product_type]


def list_products() -> list[ProductOut]:
    return list(CATALOG.values())
