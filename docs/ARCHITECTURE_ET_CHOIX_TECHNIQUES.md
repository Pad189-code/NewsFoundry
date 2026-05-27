# NewsFoundry — Architecture et choix techniques

Ce document sert d’onboarding pour une nouvelle personne sur le dépôt : vue d’ensemble, organisation du code, comment exécuter les tests, et justification des décisions d’implémentation.

---

## 1. Vue d’ensemble

NewsFoundry est une application **monorepo** composée de :

- un **backend** Python (**FastAPI**) exposant une API REST sécurisée par **JWT** ;
- un **frontend** (**Next.js** / React) consommant cette API ;
- une base **PostgreSQL** en environnement réel, avec possibilité de **SQLite en mémoire** pour le développement local sans Docker.

Les fonctionnalités centrées sur l’IA reposent sur :

- **PydanticAI** pour les agents (chat avec outils, revue de presse avec sortie structurée) ;
- **World News API** pour l’actualité (top-news dans le prompt système, search-news via un outil du chat) ;
- **LlamaIndex** (optionnel) pour un **RAG en mémoire** lors de la génération de revue de presse, afin de sélectionner les articles les plus pertinents pour le sujet choisi.

### Application déployée (production)

| Composant | URL |
|-----------|-----|
| **Site web (frontend Vercel)** | [https://news-foundry-nvpt-git-main-pad189-codes-projects.vercel.app/](https://news-foundry-nvpt-git-main-pad189-codes-projects.vercel.app/) |
| **API backend (Railway)** | [https://newsfoundry-api-production.up.railway.app](https://newsfoundry-api-production.up.railway.app) |
| **Documentation OpenAPI** | [https://newsfoundry-api-production.up.railway.app/docs](https://newsfoundry-api-production.up.railway.app/docs) |
| **Santé API** | `GET https://newsfoundry-api-production.up.railway.app/health` |

Le frontend en production consomme l’API Railway via la variable Vercel **`NEXT_PUBLIC_API_URL`**. Le backend autorise l’origine du site Vercel via **`CORS_ORIGINS`** (ou le mode CORS relaxed sur Railway). Détail des variables et du flux de déploiement : **`docs/DEPLOIEMENT.md`**.

---

## 2. Structure des dossiers (racine du dépôt)

| Chemin | Rôle |
|--------|------|
| **`backend/`** | API FastAPI, modèles SQLModel, migrations Alembic, tests Pytest. |
| **`backend/src/`** | Code applicatif du backend. Point d’entrée : `main.py`. |
| **`backend/src/services/`** | Logique métier et IA : agents (`chat_agent`, `review_agent`), appels news (`news`), RAG (`review_rag`), persistance articles (`article_tool_persist`), résolution des modèles LLM (`llm`, `llm_model_spec`). |
| **`backend/tests/`** | Tests automatisés (`pytest`), avec `conftest.py` (SQLite, utilisateur seed). |
| **`backend/alembic/`** | Migrations de schéma PostgreSQL. |
| **`frontend/`** | Application Next.js (App Router). |
| **`frontend/src/app/`** | Pages (`/`, `/login`, `/chats`). |
| **`frontend/src/lib/`** | Client HTTP (`api.ts`), auth locale (`auth.ts`). |
| **`frontend/src/components/`** | Composants réutilisables (ex. rendu Markdown du chat). |
| **`.github/workflows/`** | CI (tests backend). |
| **`docs/`** | Documentation projet (ce fichier et compléments). |

---

## 3. Backend — fichiers clés

| Fichier | Responsabilité |
|---------|----------------|
| `main.py` | Création de l’app FastAPI, CORS, montage des routes, `lifespan` (`init_db`). |
| `routes.py` | Endpoints : auth, chats, messages, articles, news fetch, revues de presse. |
| `models.py` | Tables SQLModel (`User`, `Chat`, `Article`, `PressReview`). |
| `schemas.py` | Modèles Pydantic pour les corps de requête/réponse API. |
| `database.py` | `create_engine`, session FastAPI, graine utilisateur de test optionnelle. |
| `auth_tokens.py` | JWT access + refresh, dépendance `get_current_user`. |
| `rate_limit.py` | Limitation de débit (SlowAPI) sur certaines routes. |

---

## 4. Flux fonctionnels (résumé)

1. **Connexion** — `/login` ou `/auth/login` ; tokens JWT ; `/me` pour le profil.
2. **Chat** — CRUD discussions (`/chats`), messages (`POST .../messages`). Chaque message utilisateur déclenche un passage dans **PydanticAI** ; le tool **`rechercher_actualites`** appelle **search-news** et peut **persister** les articles + URLs dans `Chat.loaded_articles` et la table `Article`.
3. **Actualité « du jour »** — À la création de discussion, **`GET /top-news`** alimente un bloc titre/résumé intégré au **prompt système figé** `chat.system_prompt_saved` (cohérence dans le temps).
4. **Revue de presse** — `POST /chats/{id}/reviews` : transcription du chat + contexte articles ; agent **`review_agent`** avec **`output_type`** Pydantic ; bloc RAG optionnel via **`review_rag.retrieve_review_context`** si embeddings disponibles.
5. **Liste globale des revues** — `GET /reviews` pour l’utilisateur connecté.

---

## 5. Lancer les tests

Les tests backend utilisent **SQLite en mémoire** (`TEST_SQLITE=1`), sans Postgres ni Docker.

### Windows (PowerShell)

```powershell
cd backend
$env:TEST_SQLITE="1"
$env:DISABLE_RATE_LIMIT="1"
$env:JWT_SECRET="pytest-jwt-secret-at-least-32-characters-long!!"
uv run pytest -q
```

### Linux / macOS

```bash
cd backend
export TEST_SQLITE=1
export DISABLE_RATE_LIMIT=1
export JWT_SECRET=pytest-jwt-secret-at-least-32-characters-long!!
uv run pytest -q
```

La **CI GitHub Actions** (workflow **`Backend CI`**, fichier `.github/workflows/backend-ci.yml`) exécute la même commande depuis le dossier `backend` avec `uv sync` puis `uv run pytest -q`.

Pour le frontend, le script habituel est :

```bash
cd frontend
npm run lint
npm run build
```

---

## 6. Choix techniques et raisons

### Stack générale

| Choix | Raison |
|-------|--------|
| **FastAPI + SQLModel** | Alignement naturel avec Pydantic, documentation OpenAPI automatique, typage fort pour limiter les erreurs à l’interface HTTP / base. |
| **JWT (access + refresh)** | Stateless pour l’API ; refresh pour renouveler l’accès sans redemander mot de passe à chaque action. |
| **PostgreSQL en prod** | Relationnel robuste pour données utilisateur et historiques JSON (`messages_json`, etc.). |
| **SQLite mémoire en tests** | Isolation, rapidité, pas de service externe ; même schéma via `SQLModel.metadata.create_all`. |
| **uv** | Gestion de dépendances et environnement Python reproductibles (`pyproject.toml`, lockfile). |

### Intelligence artificielle

| Choix | Raison |
|-------|--------|
| **PydanticAI** | Intégration unifiée agents / tools / outputs typés ; facilité pour tester avec **`TestModel`**. |
| **Deux agents distincts** | Le chat (outils, conversation) et la revue (sortie structurée sans tools) ont des objectifs différents ; séparer les prompts et modèles évite les compromis inutiles. |
| **Prompt système figé par chat** (`system_prompt_saved`) | Évite que le contexte « top-news » change du jour au lendemain au milieu d’une discussion. |
| **Sortie structurée revue** (`PressReviewAgentOutput`) | Correspondance directe avec les colonnes Base (`review_title`, `general_summary`, `articles_breakdown_json`). |
| **LlamaIndex + RAG optionnel** | Améliorer la pertinence de la revue quand il y a beaucoup d’articles ; index **non persisté** (contrainte brief / simplicité). Fallback sans clé OpenAI : concaténation titre/résumé comme avant. Variable **`NEWSFOUNDRY_DISABLE_RAG=1`** pour forcer ce mode. |
| **Embeddings OpenAI par défaut pour le RAG** | Coût faible vs LLM ; alternative documentée via **`USE_HF_EMBEDDINGS`** et modèle Hugging Face si dépendances ajoutées. |

### Données et API externes

| Choix | Raison |
|-------|--------|
| **World News API** | Contrat clair (top-news / search-news) ; normalisation des réponses dans `news.py` pour des prompts lisibles par le LLM. |
| **`loaded_articles` sur `Chat`** | Traçabilité des URLs « vues » via outil ou fetch ; alignement avec le brief livrable. |

### Frontend

| Choix | Raison |
|-------|--------|
| **Next.js (App Router)** | Routage et rendu adaptés au déploiement Vercel ; séparation pages / client API. |
| **`react-markdown` pour l’assistant** | Les réponses LLM utilisent souvent du Markdown ; rendu correct sans traiter le Markdown côté utilisateur comme du HTML brut non sécurisé (réponses utilisateur laissées en texte). |

### Sécurité et exploitation

| Choix | Raison |
|-------|--------|
| **Contrôle d’accès par `_chat_or_404`** | Les requêtes portant sur un `chat_id` vérifient `chat.user_id == current_user.id` ; évite la fuite inter-utilisateurs. |
| **Tests d’autorisation** | Régression fréquente sur les APIs multi-tenant ; couverts dans `tests/test_api.py`. |
| **Rate limiting** | Réduit l’abus des endpoints sensibles ; désactivé en tests (`DISABLE_RATE_LIMIT=1`). |

---

## 7. Variables d’environnement (résumé)

Les fichiers **`.env.example`** (`backend/`, `frontend/`) listent les variables. Parmi les plus importantes côté backend : **`DATABASE_URL`** (ou **`TEST_SQLITE=1`**), **`JWT_SECRET`**, clés **`GOOGLE_API_KEY`** / **`OPENAI_API_KEY`** selon le fournisseur LLM choisi, **`WORLDNEWS_API_KEY`**, **`CORS_ORIGINS`** pour le frontend en production.

---

## 8. Pistes d’amélioration

Synthèse des axes d’évolution identifiés pour NewsFoundry. Le détail (métriques, objectifs chiffrés, plans d’implémentation) est développé dans **`docs/EVOLUTIONS_IA.md`** (partie IA) et **`docs/REGARD_CRITIQUE_PERFORMANCE.md`** (fluidité, latence, observabilité).

### Performance et expérience utilisateur

| Piste | Constat | Direction |
|-------|---------|-----------|
| **Streaming des réponses chat** | L’utilisateur attend la réponse HTTP complète avant affichage. | Endpoint SSE ou chunked + mise à jour incrémentale côté Next.js ; objectif : réduire le *time-to-first-token* perçu. |
| **Latence revue de presse** | Pipeline synchrone (transcript + RAG optionnel + LLM structuré), durée non journalisée. | Indicateur de progression en UI ; instrumentation des durées `POST /reviews`. |
| **Observabilité** | Peu de corrélation requête HTTP ↔ étapes agent ↔ appels World News. | MLflow Tracing (ou équivalent) sur `run_agent_reply` et `run_press_review_structured` ; métriques p50/p95. |

### Qualité IA et données

| Piste | Constat | Direction |
|-------|---------|-----------|
| **Fiabilité des outils (chat)** | L’outil `rechercher_actualites` peut être sous-utilisé selon le modèle. | Jeux de tests golden avec `TestModel` ; ajustement prompt ou suggestions de recherche en UI. |
| **Qualité revue (RAG)** | Risque d’hallucination si peu de sources ; RAG dépend des embeddings. | URLs obligatoires dans la sortie structurée ; reranking après retrieval ; objectif fidélité aux sources ≥ 4/5 sur échantillon figé. |
| **Coût API** | Chaque message, tool-call et revue consomme des quotas LLM / news / embeddings. | Limites par utilisateur, cache top-news court, `NEWSFOUNDRY_DISABLE_RAG` en démo. |

### Produit et exploitation

| Piste | Constat | Direction |
|-------|---------|-----------|
| **Erreurs utilisateur** | Erreurs LLM parfois visibles en texte dans le chat. | Codes internes + message générique ; corrélation `request-id` dans les logs ; cible &lt; 2 % de réponses « erreur technique » visibles. |
| **Tests de non-régression qualité** | Pas de jeu de référence ni scores en CI pour les réponses IA. | Échantillon de prompts/revues attendues ; évaluation automatisée ou LLM-as-judge en pipeline optionnel. |
| **Conformité maquette** | Non vérifiable dans le dépôt seul. | Captures d’écran ou lien Figma en soutenance si exigé par le formateur. |

Ces pistes restent **réalistes** au regard de la stack actuelle (FastAPI, PydanticAI, Next.js, Railway, Vercel) sans remettre en cause l’architecture monorepo ni l’isolation multi-utilisateur déjà testée.

---

## 9. Documentation complémentaire

- **`EVOLUTIONS_IA.md`** — Pistes d’amélioration qualité / performance de la partie IA, avec exemples de métriques et objectifs mesurables.
- **`API_ERREURS.md`** — Principaux codes HTTP et champs `detail` renvoyés par l’API.
- **`PROMPTS.md`** — Raisons des prompts système et des consignes agents (chat, revue, RAG).
- **`GRILLE_LIVRABLES.md`** — Tableau de correspondance critères de formation / fichiers du dépôt.
- **`REGARD_CRITIQUE_PERFORMANCE.md`** — Analyse critique fluidité et qualité perçue.
- **`RAPPORT_ARCHITECTURE_NEWSFOUNDRY.md`** — Rapport d’architecture détaillé (export Word possible via Pandoc).

Pour le détail installation Postgres, migrations Alembic et déploiement Railway / Vercel / CI sur **`main`**, voir **`backend/README.md`**, **`README.md`** (section Déploiement) et **`docs/DEPLOIEMENT.md`**.
