"""
Router : authentification admin.

Différences volontaires par rapport à l'auth client :
- Cookie séparé (ADMIN_COOKIE_NAME) pour ne jamais mélanger les deux contextes.
- Durée de session beaucoup plus courte (4h vs 7 jours).
- Verrouillage de compte après échecs répétés (pas seulement rate-limit par IP).
- Toute connexion/échec est journalisé dans l'audit log.
"""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.admin import Admin, AdminSession
from app.schemas.admin_schemas import AdminLogin, AdminOut
from app.utils.security import verify_password, create_access_token, decode_token
from app.utils.rate_limit import is_locked, record_failed_attempt, reset_attempts
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])

MAX_FAILED_ATTEMPTS_LOCK_ACCOUNT = 5
ACCOUNT_LOCK_MINUTES = 30


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=AdminOut)
def admin_login(payload: AdminLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = _client_ip(request)

    # Rate limit par IP+email (protection brute-force générique)
    locked, seconds_remaining = is_locked(f"admin:{payload.email}", ip)
    if locked:
        minutes = max(1, seconds_remaining // 60)
        raise HTTPException(status_code=429, detail=f"Trop de tentatives échouées. Réessayez dans {minutes} minute(s).")

    admin = db.query(Admin).filter(Admin.email == payload.email.lower()).first()

    # Verrouillage de compte spécifique (indépendant de l'IP, plus difficile à contourner)
    if admin and admin.locked_until and admin.locked_until > dt.datetime.utcnow():
        remaining = int((admin.locked_until - dt.datetime.utcnow()).total_seconds() // 60) + 1
        raise HTTPException(status_code=429, detail=f"Compte temporairement verrouillé. Réessayez dans {remaining} minute(s).")

    if not admin or not verify_password(payload.password, admin.password_hash):
        record_failed_attempt(f"admin:{payload.email}", ip)
        if admin:
            admin.failed_login_attempts += 1
            if admin.failed_login_attempts >= MAX_FAILED_ATTEMPTS_LOCK_ACCOUNT:
                admin.locked_until = dt.datetime.utcnow() + dt.timedelta(minutes=ACCOUNT_LOCK_MINUTES)
                admin.failed_login_attempts = 0
            db.commit()
        log_action(db, actor_type="admin", action="login_failed", details=payload.email, ip_address=ip)
        raise HTTPException(status_code=401, detail="Courriel ou mot de passe invalide.")

    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Ce compte administrateur a été désactivé.")

    reset_attempts(f"admin:{payload.email}", ip)
    admin.failed_login_attempts = 0
    admin.locked_until = None
    admin.last_login_at = dt.datetime.utcnow()
    db.commit()

    token, jti, expires_at = create_access_token(
        subject=admin.id,
        expires_minutes=settings.ADMIN_TOKEN_EXPIRE_MINUTES,
        extra_claims={"scope": "admin"},
    )
    session = AdminSession(
        admin_id=admin.id,
        token_id=jti,
        expires_at=expires_at,
        ip_address=ip,
        user_agent=request.headers.get("user-agent", "")[:255],
    )
    db.add(session)
    db.commit()

    response.set_cookie(
        key=settings.ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",  # plus strict que pour les clients : aucune navigation cross-site
        max_age=settings.ADMIN_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    log_action(db, actor_type="admin", actor_id=admin.id, action="login", ip_address=ip)

    # v9.11 : vérifie et envoie les rappels de fin de contrat de maintenance
    # (pas de scheduler — déclenché à chaque connexion admin, best-effort).
    try:
        from app.services.renewal_reminders import check_and_send_renewal_reminders
        check_and_send_renewal_reminders(db)
    except Exception:
        import logging
        logging.getLogger("ctq.admin_auth").exception("Échec de la vérification des rappels de renouvellement.")

    return admin


@router.post("/logout")
def admin_logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.ADMIN_COOKIE_NAME)
    if token:
        payload = decode_token(token)
        if payload:
            session = db.query(AdminSession).filter(AdminSession.token_id == payload.get("jti")).first()
            if session:
                session.revoked = True
                db.commit()
    response.delete_cookie(settings.ADMIN_COOKIE_NAME, path="/")
    return {"message": "Déconnexion réussie."}
