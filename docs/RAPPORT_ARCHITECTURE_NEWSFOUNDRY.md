---
title: "Rapport détaillé — NewsFoundry (Projet 14)"
author: "NewsFoundry"
date: "21 mai 2026"
lang: fr-FR
---

# Rapport détaillé — NewsFoundry (Projet 14)

Application **monorepo** d'assistant d'actualités et de **revue de presse assistée par IA** : frontend Next.js, API FastAPI, PostgreSQL en production, intégration World News API et agents PydanticAI.

---

## 1. Vue d'ensemble

### Architecture générale

| Couche | Technologie | Hébergement production |
|--------|-------------|------------------------|
| Frontend | Next.js 15 (App Router), React, Tailwind | **Vercel** (dossier `frontend/`) |
| API | FastAPI, SQLModel, Alembic | **Railway** (Docker) |
| Base de données | PostgreSQL (SQLite en tests) | **Railway** (même projet) |
| Actualités | World News API | Clé `WORLDNEWS_API_KEY` |
| Intelligence artificielle | PydanticAI + LlamaIndex (RAG optionnel) | Mistral / Gemini / OpenAI |

**Flux :** le navigateur (UI Vercel) appelle l'API Railway en HTTPS avec JWT Bearer ; l'API lit/écrit PostgreSQL, appelle World News API et les fournisseurs LLM via les agents PydanticAI.

### URLs documentées (production)

- **Frontend :** `https://news-foundry-nvpt-git-main-pad189-codes-projects.vercel.app/`
- **API :** `https://newsfoundry-api-production.up.railway.app`
- **OpenAPI :** `https://newsfoundry-api-production.up.railway.app/docs`
- **Santé :** `GET /health` → `{"message":"ok","app":"newsfoundry-api"}`

---

## 2. Structure du dépôt

```
P14DevIA-main/
├── backend/                 # API Python
│   ├── src/
│   │   ├── main.py          # Point d'entrée FastAPI
│   │   ├── routes.py        # Tous les endpoints REST
│   │   ├── models.py        # Tables SQLModel
│   │   ├── schemas.py       # DTO Pydantic API
│   │   ├── database.py      # Engine + sessions
│   │   ├── auth_tokens.py   # JWT + bcrypt
│   │   ├── rate_limit.py    # SlowAPI
│   │   └── services/        # IA, news, RAG, persistance
│   ├── alembic/             # Migrations PostgreSQL
│   ├── tests/               # pytest (SQLite mémoire)
│   ├── Dockerfile           # Build si Root = backend/
│   └── railway.toml
├── frontend/                # Next.js
│   └── src/
│       ├── app/             # Pages (routage fichier)
│       ├── components/      # UI chat, revue, breaking news
│       └── lib/             # api.ts, auth.ts
├── docs/                    # Architecture, déploiement, prompts…
├── .github/workflows/       # CI backend
├── railway.toml             # Variante monorepo
└── README.md
```

---

## 3. Backend

### 3.1 Point d'entrée (`main.py`)

- **lifespan** : `init_db()` au démarrage (création tables + seed optionnel).
- **CORS** :
  - Mode strict : `CORS_ORIGINS` + regex Vercel (`*.vercel.app`) + localhost.
  - Mode **relaxed** sur Railway (auto si variables `RAILWAY_*` présentes) : `allow_origins=["*"]`, sans credentials.
- **Sécurité** : en-têtes `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.
- **Rate limiting** : SlowAPI via `app.state.limiter`.
- Routes utilitaires : `GET /` → redirection `/docs`, `GET /health`.

### 3.2 Routage API (`routes.py`)

Toutes les routes métier sont sur un **APIRouter** sans préfixe (chemins à la racine).

#### Authentification (JWT)

| Méthode | Chemin | Auth | Limite | Rôle |
|---------|--------|------|--------|------|
| POST | `/login`, `/auth/login` | Non | 10/min | Connexion → access + refresh |
| POST | `/auth/refresh` | Non | 30/min | Renouvellement des tokens |
| GET | `/me` | Bearer | — | Profil utilisateur |

#### Actualités globales

| Méthode | Chemin | Rôle |
|---------|--------|------|
| GET | `/news/breaking` | Top-news World News pour le panneau d'accueil |

#### Discussions (chats)

| Méthode | Chemin | Rôle |
|---------|--------|------|
| GET | `/chats` | Liste des discussions de l'utilisateur |
| POST | `/chats` | Créer une discussion (+ prompt système figé) |
| DELETE | `/chats/{chat_id}` | Supprimer chat + articles + revues liés |
| GET | `/chats/{chat_id}` | Détail + messages |
| GET | `/chats/{chat_id}/messages` | Alias historique messages |
| POST | `/chats/{chat_id}/messages` | Message user → réponse assistant (agent IA) |
| POST | `/chats/{chat_id}/bootstrap-welcome` | Message d'accueil + articles si chat vide |
| POST | `/chats/{chat_id}/news/fetch` | Recherche World News → table Article |
| GET | `/chats/{chat_id}/articles` | Articles chargés pour la discussion |

#### Revues de presse

| Méthode | Chemin | Rôle |
|---------|--------|------|
| GET | `/reviews` | Toutes les revues de l'utilisateur |
| GET | `/chats/{chat_id}/reviews` | Revues d'une discussion |
| POST | `/chats/{chat_id}/reviews` | Génération structurée + persistance |

**Isolation multi-tenant :** la fonction `_chat_or_404(session, user_id, chat_id)` vérifie `chat.user_id == current.id` ; sinon réponse **404** (pas de fuite « existe mais pas à vous »).

### 3.3 Modèle de données (`models.py`)

| Table | Champs importants |
|-------|-------------------|
| **User** | `email`, `hashed_password` |
| **Chat** | `user_id`, `title`, `messages_json` (historique JSON), `system_prompt_saved`, aperçu revue (`review_*`), `loaded_articles` (URLs) |
| **Article** | `chat_id`, `title`, `url`, `source`, `summary`, `published_at` |
| **PressReview** | `user_id`, `chat_id`, `topic`, `content`, `review_title`, `general_summary`, `articles_breakdown_json` |

Les messages sont stockés **dans le chat** (`messages_json`), pas en table séparée.

### 3.4 Services métier / IA (`backend/src/services/`)

| Module | Fonction principale |
|--------|---------------------|
| `chat_agent.py` | Agent PydanticAI pour le chat ; outil `rechercher_actualites` ; `run_agent_reply()` |
| `chat_live_search.py` | Recherche presse en ligne à chaque message utilisateur |
| `news.py` | Client World News (top-news, search-news), formatage pour prompts |
| `article_tool_persist.py` | Persistance articles + `loaded_articles` après outil/fetch |
| `review_agent.py` | Agent revue avec sortie structurée `PressReviewAgentOutput` |
| `review_rag.py` | RAG LlamaIndex (optionnel, `NEWSFOUNDRY_DISABLE_RAG`) |
| `review_llm.py` | Formatage contexte RAG pour la revue |
| `llm_model_spec.py` | Résolution Mistral > Gemini > OpenAI |
| `llm.py` | Construction modèles natifs (ex. Gemini) |
| `llm_exception_format.py` | Messages d'erreur LLM lisibles |

### 3.5 Flux fonctionnels clés

**A. Envoi d'un message** (`POST /chats/{id}/messages`)

1. Enregistre le message utilisateur dans `messages_json`.
2. Charge le prompt système figé (`system_prompt_saved` = base + top-news au premier accès).
3. `search_press_articles_for_message` : recherche live World News.
4. Construit le contexte articles (live + déjà en BDD).
5. `run_agent_reply` (PydanticAI) → réponse assistant persistée.
6. Met à jour le titre si discussion par défaut.

**B. Création de chat**

- Titre par défaut « Discussion du JJ/MM/AAAA ».
- `_ensure_chat_system_prompt_saved` : intègre les titres/résumés top-news une fois.

**C. Revue de presse** (`POST .../reviews`)

- Transcript du chat + articles triés par date.
- `retrieve_review_context` (RAG) si articles présents.
- `run_press_review_structured` → JSON structuré → Markdown + colonnes BDD + aperçu sur Chat.

**D. Bootstrap welcome**

- Si chat vide : fetch actualités, persiste articles, message d'accueil formaté.

### 3.6 Auth et base

- **JWT** : access (7 j par défaut) + refresh (30 j) ; en-tête `Authorization: Bearer`.
- **BDD** : `DATABASE_URL` PostgreSQL ; normalisation `postgres://` → `postgresql://`.
- **Tests** : `TEST_SQLITE=1` → SQLite en mémoire.
- **Dev** : `SEED_DEFAULT_USER` → `test@test.com` / `test`.
- **Démarrage Docker** : `docker-entrypoint.sh` exécute `alembic upgrade head` puis lance l'API.

---

## 4. Frontend

### 4.1 Routage Next.js (App Router)

| URL | Fichier | Type | Rôle |
|-----|---------|------|------|
| `/` | `app/page.tsx` | Server | Accueil, liens login / chats |
| `/login` | `app/login/page.tsx` | Client | Formulaire connexion |
| `/chats` | `app/chats/page.tsx` | Client | Application principale |

La protection repose sur `isAuthenticated()` + redirection côté client.

### 4.2 Client API (`frontend/src/lib/api.ts`)

- **Base URL** : variable `NEXT_PUBLIC_API_URL`
  - Production : URL Railway absolue.
  - Local : `/api-backend` → proxy Next (`BACKEND_PROXY_TARGET=http://localhost:8000`).
- **withAuthRetry** : sur 401, tente `POST /auth/refresh` puis rejoue la requête.
- **pingBackend()** : vérifie `/health` et le champ `app: "newsfoundry-api"` avant login.

Fonctions exportées : `loginRequest`, `listChats`, `createChat`, `deleteChat`, `listMessages`, `sendMessage`, `bootstrapChatWelcome`, `fetchBreakingNews`, `getBreakingNewsPreview`, `listArticles`, `listReviews`, `listAllPressReviews`, `createPressReview`.

### 4.3 Auth côté navigateur (`auth.ts`)

Stockage **localStorage** : `newsfoundry_token`, `newsfoundry_refresh`, `newsfoundry_email`.

### 4.4 Page `/chats` (cœur UI)

Modes internes : `home` | `chat` | `review`.

Composants : `BreakingNewsPanel`, `ChatMessageBubble`, `ChatMarkdown`, `PressReviewModal`.

### 4.5 Proxy local (`next.config.ts`)

Réécriture : `/api-backend/:path*` → `BACKEND_PROXY_TARGET/:path*` (évite CORS en développement).

---

## 5. Déploiement

### 5.1 Railway (backend + PostgreSQL)

| Configuration | Root Directory | Dockerfile |
|---------------|----------------|------------|
| Pad189 (actuelle) | `backend/` | `backend/Dockerfile` |
| Monorepo | racine repo | `backend/Dockerfile.monorepo` |

**Entrypoint** : migrations Alembic automatiques, puis API sur `0.0.0.0:$PORT`.

**Variables critiques :** `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, clés LLM, `WORLDNEWS_API_KEY`. Ne pas activer `SEED_DEFAULT_USER` en production.

### 5.2 Vercel (frontend)

- Root Directory : `frontend`
- Branche production : `main`
- `NEXT_PUBLIC_API_URL` = URL Railway
- `BACKEND_PROXY_TARGET` : optionnel si proxy `/api-backend`

### 5.3 Chaîne production

1. L'utilisateur ouvre le frontend Vercel.
2. Connexion : frontend → `POST /login` sur Railway → tokens JWT.
3. Messages chat : frontend → API avec Bearer → World News + LLM → PostgreSQL.
4. CORS : origine Vercel autorisée via `CORS_ORIGINS` ou mode relaxed Railway.

---

## 6. CI / qualité

**Workflow** `.github/workflows/backend-ci.yml` : `uv sync` + `pytest -q` avec SQLite mémoire.

Tests notables : autorisation inter-utilisateurs, agents, news, revues, breaking news.

Frontend : `npm run lint` / `npm run build` (pas de workflow CI dédié dans le dépôt).

---

## 7. Documentation projet (`docs/`)

| Fichier | Contenu |
|---------|---------|
| `ARCHITECTURE_ET_CHOIX_TECHNIQUES.md` | Stack, flux, variables |
| `DEPLOIEMENT.md` | Railway + Vercel, variables prod |
| `API_ERREURS.md` | Codes HTTP et detail |
| `PROMPTS.md` | Justification prompts agents |
| `EVOLUTIONS_IA.md` | Pistes d'amélioration IA |
| `REGARD_CRITIQUE_PERFORMANCE.md` | Streaming, latence revue |
| `GRILLE_LIVRABLES.md` | Correspondance critères OCR |

---

## 8. Besoins fonctionnels couverts

| Besoin | Implémentation |
|--------|----------------|
| Connexion | `/login` + JWT + page `/login` |
| Liste discussions | `GET /chats` + UI sidebar |
| Nouvelle / reprise discussion | `POST /chats`, `GET /chats/{id}` |
| Isolation utilisateur | `_chat_or_404` + tests |
| Réponses LLM | `chat_agent` + `POST .../messages` |
| Revue de presse | `review_agent` + `POST .../reviews` |
| Erreurs utilisateur | `parseApiError` + messages agent en texte |

---

## 9. Pistes d'amélioration

Voir la section complète dans **`docs/ARCHITECTURE_ET_CHOIX_TECHNIQUES.md`** (§ 8) et le détail dans **`docs/EVOLUTIONS_IA.md`** et **`docs/REGARD_CRITIQUE_PERFORMANCE.md`**.

| Axe | Piste principale |
|-----|------------------|
| UX / performance | Streaming SSE des réponses chat ; progression visible pour la revue de presse |
| Observabilité | MLflow Tracing (latence p95, tool-calls, erreurs World News / LLM) |
| Qualité IA | Tests golden sur l'outil actualités ; RAG + validation des sources pour la revue |
| Coût | Limites par utilisateur, cache top-news, RAG désactivable en démo |
| Erreurs | Messages utilisateur génériques + `request-id` côté logs |

---

## 10. Points d'attention opérationnels

1. **Deux fichiers railway.toml** : vérifier la configuration dashboard Railway (root `backend/` vs monorepo).
2. **Migrations** : gérées au démarrage Docker ; en local, `alembic upgrade head` si besoin.
3. **Pas de streaming** : réponses chat en une seule requête HTTP (latence perçue).
4. **RAG revue** : souvent `OPENAI_API_KEY` pour embeddings ; désactivable via `NEWSFOUNDRY_DISABLE_RAG=1`.

---

*Document généré pour le projet NewsFoundry — OpenClassrooms Projet 14.*
