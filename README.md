# NewsFoundry

## Besoins fonctionnels

- L'utilisateur peut se connecter.
- L’utilisateur peut voir la liste de ses discussions passées.
- L’utilisateur peut démarrer une nouvelle discussion ou reprendre une ancienne discussion.
- Un utilisateur n’est pas autorisé à accéder aux discussions d’un autre utilisateur.
- Le LLM répond aux messages envoyés par l’utilisateur.
- L'utilisateur peut faire générer une revue de presse à partir d'une discussion.
- L'application doit afficher des messages d'erreur à l'utilisateur final en cas d'erreur.

## Prérequis

- Docker
- Python 3.13
- uv
- Node.js 22.19

## Installation

1. Cloner le repository
2. Démarrer le backend aved les instructions du fichier `backend/README.md`
3. Initialiser un projet Next.js dans un dossier `frontend/`

## Choix technologiques

### Frontend

**Next.js**

### Backend

- **Python** pour bénéficier de son écosystème de librairies IA
- **FastAPI** pour le développement de l'API
- Connection avec des **JWT**
- **SQLModel** comme ORM : fait pour bien marcher avec FastAPI.
  - Branché à une base de données **PostgreSQL**
- **PydanticAI** comme client qui s'intégrera aussi bien avec les autres outils de la stack backend
- Attention à la **sécurité des données**. On ne veut pas qu’un utilisateur puisse accéder aux chats d’un autre utilisateur ou les modifier.
  - Le produit aura rapidement beaucoup d’utilisateurs professionnels il est donc crucial de garantir le fonctionnement correct de cette fonctionnalité par l'**implémentation de tests automatisés qui s'exécutent par une Github Action**.
- Pour les sources de news, on utilisera l’API [**WorldNewsAPI**](https://worldnewsapi.com/).
- Pour déployer on mettra le frontend sur **Vercel** et le backend sur **Railway**.

### Documentation

Le dossier **`docs/`** centralise la documentation de livraison :

- **`docs/ARCHITECTURE_ET_CHOIX_TECHNIQUES.md`** — architecture du dépôt, arborescence des dossiers, commandes pour lancer les tests, choix techniques et raisons.
- **`docs/EVOLUTIONS_IA.md`** — pistes d’amélioration qualité / performance de la partie IA (métriques, implémentations possibles, objectifs mesurables).
- **`docs/REGARD_CRITIQUE_PERFORMANCE.md`** — regard critique sur la fluidité et la qualité des résultats (streaming, MLflow, temps de revue, pistes réalisables).
- **`docs/API_ERREURS.md`** — référence des erreurs HTTP / `detail` renvoyés par l’API.
- **`docs/PROMPTS.md`** — justification des choix de prompts (chat, revue, RAG).
- **`docs/GRILLE_LIVRABLES.md`** — tableau de correspondance entre critères de livrables et fichiers du dépôt.
- **`docs/DEPLOIEMENT.md`** — production Railway + Vercel, déploiement automatique sur `main`, variables.

Pour Postgres, Alembic et variables d’environnement du backend, voir **`backend/README.md`**.

### Déploiement

En production, le **backend** et la **base PostgreSQL** sont hébergés sur **Railway**, le **frontend** sur **Vercel**. Les deux plateformes peuvent être reliées au dépôt Git : un **push sur la branche `main`** déclenche un **nouveau déploiement** (build + mise en ligne). Détail et checklist : **`docs/DEPLOIEMENT.md`**.

#### URL du frontend (production — Vercel)

| | |
|--|--|https://news-foundry-nvpt-git-main-pad189-codes-projects.vercel.app/
| **URL du déploiement** | *Renseigner ici l’URL affichée dans le dashboard Vercel (ex. `https://<votre-projet>.vercel.app` ou domaine personnalisé).* |
| **Où la trouver** | Tableau de bord Vercel : dernier déploiement **Production** → **Visit**, ou **Settings → Domains**. |
| **Variable côté Vercel** | **`NEXT_PUBLIC_API_URL`** = URL HTTPS du backend Railway (voir ci‑dessous). |
| **Variable côté backend Railway** | **`CORS_ORIGINS`** doit contenir l’origine exacte du frontend (URL Vercel). |

#### API backend (Railway — production)

| | |
|--|--|
| **URL de base** | `https://newsfoundry-api-production.up.railway.app` |
| **Documentation OpenAPI** | `https://newsfoundry-api-production.up.railway.app/docs` |
| **Santé** | `GET https://newsfoundry-api-production.up.railway.app/health` → `{"message":"ok","app":"newsfoundry-api"}` |

Exemple pour la variable Vercel : **`NEXT_PUBLIC_API_URL`** = `https://newsfoundry-api-production.up.railway.app` (le client `frontend/src/lib/api.ts` assemble les chemins ; pas de slash final inutile).

#### Frontend (Vercel)

Projet lié au dépôt Git ; **branche de production** : **`main`** ; **Root Directory** : **`frontend`**. Chaque push sur `main` déclenche un déploiement production.

#### Backend + base (Railway)

Service API sur [Railway](https://railway.com/dashboard) : **`railway.toml`** à la racine fixe le Docker **`backend/Dockerfile`** (contexte = racine du monorepo — **ne pas** mettre le Root Directory Railway sur `backend/` seul). Variable de secours possible : **`RAILWAY_DOCKERFILE_PATH`** = `backend/Dockerfile`.

**PostgreSQL** : ajouté dans le **même projet** Railway ; **`DATABASE_URL`** référencée par le service API.

**Variables du service API :** **`DATABASE_URL`** ; **`JWT_SECRET`** ; clés **`GOOGLE_API_KEY`**, **`OPENAI_MODEL`**, **`WORLDNEWS_API_KEY`**, etc. ; **`CORS_ORIGINS`** = URL du frontend Vercel. Ne pas activer **`SEED_DEFAULT_USER`** en production.

Après déploiement : **`GET https://newsfoundry-api-production.up.railway.app/health`** → `{"message":"ok","app":"newsfoundry-api"}`.

## Configuration LLM (référence locale validée)

Pour retrouver la configuration de développement qui fonctionne (Mistral, port 8001, proxy Next, SQLite, etc.), voir **`docs/CONFIG_LLM_REFERENCE.md`** — sans secrets ; les clés restent dans les fichiers `.env` ignorés par Git.
