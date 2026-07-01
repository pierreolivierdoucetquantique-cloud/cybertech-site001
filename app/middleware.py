"""
Middleware ajoutant des en-têtes de sécurité HTTP standards à chaque réponse.

Ces en-têtes protègent contre des classes entières d'attaques côté navigateur :
- X-Content-Type-Options : empêche le navigateur de "deviner" un type MIME
  différent de celui déclaré (protection contre certaines attaques XSS).
- X-Frame-Options : empêche le site d'être chargé dans un <iframe> sur un
  domaine tiers (protection contre le clickjacking).
- Strict-Transport-Security : force le navigateur à toujours utiliser HTTPS
  pour ce domaine pendant la durée indiquée (actif uniquement en production).
- Referrer-Policy : limite les informations envoyées dans l'en-tête Referer
  lors de la navigation vers un autre site.
- Permissions-Policy : désactive les API navigateur non utilisées par le site.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        return response
