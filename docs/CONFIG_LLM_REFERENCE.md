# Référence configuration LLM — NewsFoundry (local validé)

Ce fichier sert de **référence stable** pour la configuration qui fonctionne en développement.  
**Ne jamais y coller de secrets** : les clés API et JWT restent uniquement dans `backend/.env` et `frontend/.env` (non versionnés).

## Fournisseur LLM

- **Mistral** (PydanticAI + SDK `mistralai`) pour le chat et la revue lorsque `MISTRAL_MODEL` et `MISTRAL_API_KEY` sont définis dans `backend/.env`.
- Ordre de choix du modèle : voir `backend/src/services/llm_model_spec.py` — en résumé : `MISTRAL_MODEL` → `GEMINI_MODEL` → `OPENAI_MODEL`, puis défaut selon les clés présentes.
- **Identifiants Mistral** : conserver les noms tels que la doc / la console Mistral les donnent (ex. suffixe `-latest` accepté ; ne pas tronquer manuellement).
- **Erreur HTTP 429 / code 3505 / `service_tier_capacity_exceeded`** : capacité du palier ou du modèle côté Mistral — changer `MISTRAL_MODEL` (ex. vers un modèle plus léger ou listé pour votre compte), patienter, ou ajuster le palier sur [La Plateforme Mistral](https://console.mistral.ai).

## Backend (développement)

- **`PORT=8001`** — port HTTP de l’API FastAPI.
- **`TEST_SQLITE=1`** — SQLite en mémoire (données perdues à l’arrêt du processus).
- **`SQL_ECHO=1`** — journalisation SQL (SQLAlchemy) dans le terminal du backend (optionnel en prod).
- **`MISTRAL_MODEL`** — exemple validé côté projet : `mistral-small-latest` (à adapter selon disponibilité Mistral).
- **`OPENAI_MODEL` / `OPENAI_REVIEW_MODEL`** — peuvent rester vides si tout passe par Mistral.

Démarrage : depuis `backend/`, `uv run --env-file .env src/main.py`.

## Frontend (développement)

- **`NEXT_PUBLIC_API_URL=/api-backend`** — appels API en **same-origin** via Next (évite CORS / `NetworkError` entre `localhost` et `127.0.0.1`).
- **`BACKEND_PROXY_TARGET=http://127.0.0.1:8001`** — cible du proxy défini dans `frontend/next.config.ts` (réécriture `/api-backend/:path*` → backend).
- Application : `http://localhost:3000` (ou `http://127.0.0.1:3000`).

Démarrage : depuis `frontend/`, `npm run dev -- -p 3000` (ou `npm run dev:webpack -- -p 3000` en secours).

## Déploiement (rappel)

En production (Vercel + API distante), utiliser en général une **URL absolue** `https://…` pour `NEXT_PUBLIC_API_URL` ; le mode proxy `/api-backend` est surtout pensé pour le **local**.
