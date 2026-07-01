"""Router : authentification client (inscription, connexion, déconnexion)."""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.client import Client, ClientSession
from app.schemas.client_schemas import ClientRegister, ClientLogin, ClientOut
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.rate_limit import is_locked, record_failed_attempt, reset_attempts
from app.services.audit import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, token: str, expires_minutes: int):
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=expires_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def register(payload: ClientRegister, request: Request, response: Response, db: Session = Depends(get_db)):
    existing = db.query(Client).filter(Client.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Un compte existe déjà avec ce courriel.")

    client = Client(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    log_action(db, actor_type="client", actor_id=client.id, action="register", ip_address=_client_ip(request))

    # Connexion automatique après inscription
    _create_session_and_cookie(db, client, request, response)

    return client


def _create_session_and_cookie(db: Session, client: Client, request: Request, response: Response):
    token, jti, expires_at = create_access_token(
        subject=client.id,
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    session = ClientSession(
        client_id=client.id,
        token_id=jti,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent", "")[:255],
        ip_address=_client_ip(request),
    )
    db.add(session)
    db.commit()
    _set_session_cookie(response, token, settings.ACCESS_TOKEN_EXPIRE_MINUTES)


@router.post("/login", response_model=ClientOut)
def login(payload: ClientLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    locked, seconds_remaining = is_locked(payload.email, ip)
    if locked:
        minutes = max(1, seconds_remaining // 60)
        raise HTTPException(
            status_code=429,
            detail=f"Trop de tentatives échouées. Veuillez réessayer dans environ {minutes} minute(s).",
        )

    client = db.query(Client).filter(Client.email == payload.email.lower()).first()
    if not client or not verify_password(payload.password, client.password_hash):
        record_failed_attempt(payload.email, ip)
        log_action(db, actor_type="client", action="login_failed", details=payload.email, ip_address=ip)
        raise HTTPException(status_code=401, detail="Courriel ou mot de passe invalide.")

    if not client.is_active:
        raise HTTPException(status_code=403, detail="Ce compte a été désactivé. Contactez le support.")

    reset_attempts(payload.email, ip)
    _create_session_and_cookie(db, client, request, response)

    client.updated_at = dt.datetime.utcnow()
    db.commit()
    log_action(db, actor_type="client", actor_id=client.id, action="login", ip_address=ip)

    return client


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        from app.utils.security import decode_token
        payload = decode_token(token)
        if payload:
            jti = payload.get("jti")
            session = db.query(ClientSession).filter(ClientSession.token_id == jti).first()
            if session:
                session.revoked = True
                db.commit()

    response.delete_cookie(settings.COOKIE_NAME, path="/")
    return {"message": "Déconnexion réussie."}
