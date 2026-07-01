"""
Configuration centrale de l'application.
Toutes les valeurs sensibles viennent de variables d'environnement.
EN PRODUCTION (Render) : configure ces variables dans le dashboard Render
sous "Environment" — ne jamais les écrire en dur dans le code.
"""
from pydantic_settings import BaseSettings
from pydantic import EmailStr
import secrets


class Settings(BaseSettings):
    # --- Général ---
    APP_NAME: str = "Cyber Teck Q"
    ENVIRONMENT: str = "development"  # "development" | "production"

    # --- Base de données ---
    # En production sur Render, pointe vers le disk monté, ex: /data/cyberteckq.db
    DATABASE_PATH: str = "./data/cyberteckq.db"

    # --- Fichiers téléversés ---
    # Doit vivre sur le même Render Disk que la base de données pour être persistant.
    # Exemple en production : /data/uploads
    UPLOADS_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 15

    # --- Sécurité / JWT ---
    # IMPORTANT : en production, définir JWT_SECRET_KEY dans les variables
    # d'environnement Render avec une valeur longue et aléatoire.
    # Si non définie, une clé temporaire est générée (sessions invalidées à
    # chaque redémarrage du serveur — NE PAS utiliser cela en production).
    JWT_SECRET_KEY: str = secrets.token_urlsafe(48)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 jours pour les clients
    ADMIN_TOKEN_EXPIRE_MINUTES: int = 60 * 4  # 4 heures pour les admins (plus court)

    # --- Cookies de session ---
    COOKIE_NAME: str = "ctq_session"
    ADMIN_COOKIE_NAME: str = "ctq_admin_session"
    COOKIE_SECURE: bool = True  # True en production (HTTPS uniquement)

    # --- Email (Resend) ---
    RESEND_API_KEY: str = ""
    # IMPORTANT : Resend exige que l'adresse "from" appartienne à un domaine
    # VÉRIFIÉ sur Resend. cyberteckq.com est vérifié — mais outlook.com ne
    # pourra JAMAIS l'être (ce domaine appartient à Microsoft, pas à CTQ).
    # On envoie donc depuis une adresse @cyberteckq.com (préfixe ajustable via
    # la variable d'environnement Render EMAIL_FROM, ex: contact@, info@...),
    # avec reply-to vers cyberteckq@outlook.com pour que les réponses des
    # clients arrivent dans cette boîte.
    EMAIL_FROM: str = "Cyber Teck Q <info@cyberteckq.com>"
    EMAIL_REPLY_TO: str = "cyberteckq@outlook.com"
    ADMIN_NOTIFICATION_EMAIL: str = "cyberteckq@outlook.com"

    # --- Facturation ---
    INVOICE_PREFIX: str = "CTQ"
    TAX_RATE_GST: float = 0.05   # TPS 5%
    TAX_RATE_QST: float = 0.09975  # TVQ 9.975%

    # --- Paiements ---
    DEPOSIT_PERCENTAGE: float = 0.40  # 40% pour le dépôt
    INTERAC_EMAIL: str = "cyberteckq@outlook.com"

    # --- Stripe ---
    # Clés obtenues sur https://dashboard.stripe.com/apikeys — NE JAMAIS commiter de vraies valeurs.
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    # Secret du endpoint webhook (https://dashboard.stripe.com/webhooks), nécessaire pour
    # vérifier que les événements reçus proviennent bien de Stripe.
    STRIPE_WEBHOOK_SECRET: str = ""

    # --- Frontend ---
    FRONTEND_URL: str = "http://localhost:8000"
    STATIC_SITE_DIR: str = "./static_site"

    # --- Premier compte admin (créé automatiquement au démarrage si aucun admin n'existe) ---
    INITIAL_ADMIN_EMAIL: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
