from contextlib import asynccontextmanager
import errno
import os

from database import init_db
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from rate_limit import limiter
from routes import router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
configured_origins = [
    origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()
]
default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
# Toujours autoriser le dev local même si CORS_ORIGINS ne liste que la prod (évite « Failed to fetch »).
cors_allow_origins = list(
    dict.fromkeys([*default_origins, *configured_origins]),
)

# 1/true = autorise toutes les origines (tests ou dépannage). allow_credentials=False est obligatoire
# avec allow_origins=["*"] (sinon le navigateur ignore la réponse CORS).
_cors_relaxed = os.getenv("CORS_RELAXED", "").strip().lower() in ("1", "true", "yes")
# Remplace la regex par défaut si besoin (ex. domaine Vercel custom : https://monapp\.com|https://www\.monapp\.com).
_cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", "").strip()
_default_origin_regex = r"https://.*\.vercel\.app|http://[\w.-]+:\d+"
cors_origin_regex = _cors_origin_regex or _default_origin_regex


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="NewsFoundry API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


if _cors_relaxed:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_allow_origins,
        allow_origin_regex=cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router)


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health():
    # Champ « app » : évite qu’un ancien processus sur :8000 (sans /login) fasse croire que l’API est à jour.
    return {"message": "ok", "app": "newsfoundry-api"}


if __name__ == "__main__":
    # Railway (et autres PaaS) injectent PORT ; en local, backend/.env ou défaut 8000.
    port = int(os.environ.get("PORT", "8000"))
    try:
        # 0.0.0.0 : obligatoire derrière un reverse proxy / conteneur (pas 127.0.0.1).
        uvicorn.run(app, host="0.0.0.0", port=port)
    except OSError as exc:
        addr_in_use = exc.errno == errno.EADDRINUSE or getattr(exc, "winerror", None) == 10048
        if addr_in_use:
            raise SystemExit(
                f"Le port {port} est déjà utilisé. Un ancien backend peut encore tourner : "
                f"fermez-le (sous Windows : netstat -ano | findstr :{port} puis taskkill /PID … /F), "
                "puis relancez : uv run --env-file .env src/main.py"
            ) from exc
        raise
