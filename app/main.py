"""
Point d'entrée principal de l'application FastAPI.

Sert à la fois :
- l'API (/api/...)
- le site statique existant (HTML/CSS/JS) compilé dans le même service,
  exactement comme demandé : "1 seul site fonctionnel".
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db, SessionLocal
from app.config import settings
from app.middleware import SecurityHeadersMiddleware
from app.routers import (
    auth_client, profile, orders, technical_form, invoices, auth_admin,
    admin_dashboard, admin_clients, admin_orders, password_reset,
    portfolio_public, admin_projects, cms_public, admin_cms,
    admin_audit, admin_profile, contact, admin_contact,
    uploads, payments, stripe_webhook, admin_payments, admin_media,
    admin_invoices, admin_maintenance, admin_technical_forms, admin_reports,
    admin_search, maintenance_contract,
)
from app.services.bootstrap import bootstrap_initial_admin
from app.services.cms_seed import seed_default_cms_content


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        bootstrap_initial_admin(db)
        seed_default_cms_content(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routers API ----------
app.include_router(auth_client.router)
app.include_router(password_reset.router)
app.include_router(profile.router)
app.include_router(orders.router)
app.include_router(technical_form.router)
app.include_router(maintenance_contract.router)
app.include_router(invoices.router)
app.include_router(portfolio_public.router)
app.include_router(cms_public.router)
app.include_router(contact.router)
app.include_router(uploads.router)
app.include_router(payments.router)
app.include_router(stripe_webhook.router)

app.include_router(auth_admin.router)
app.include_router(admin_profile.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_clients.router)
app.include_router(admin_orders.router)
app.include_router(admin_projects.router)
app.include_router(admin_cms.router)
app.include_router(admin_audit.router)
app.include_router(admin_contact.router)
app.include_router(admin_payments.router)
app.include_router(admin_media.router)
app.include_router(admin_invoices.router)
app.include_router(admin_maintenance.router)
app.include_router(admin_technical_forms.router)
app.include_router(admin_reports.router)
app.include_router(admin_search.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


# ---------- Site statique (frontend) ----------
# Servi en dernier pour ne jamais entrer en conflit avec les routes /api/...
STATIC_DIR = settings.STATIC_SITE_DIR

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """
        Sert les fichiers statiques (HTML/CSS/JS) du site.
        Si le chemin demandé correspond à un fichier existant, le sert tel quel.
        Sinon, retombe sur index.html (utile pour des routes futures côté client).
        """
        requested_path = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(requested_path):
            return FileResponse(requested_path)

        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)

        return {"detail": "Not Found"}
