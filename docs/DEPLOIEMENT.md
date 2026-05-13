# Déploiement en production

Ce document décrit **l’architecture de production** et le **flux de déploiement automatique** pour NewsFoundry.

---

## Architecture

| Composant | Plateforme | Rôle |
|-----------|------------|------|
| **API FastAPI** | [Railway](https://railway.com/) | Service Docker défini par `railway.toml` / `backend/Dockerfile` (contexte = racine du monorepo). |
| **PostgreSQL** | Railway | Base dans le **même projet** Railway que le backend ; variable **`DATABASE_URL`** injectée dans le service API. |
| **Frontend Next.js** | [Vercel](https://vercel.com/) | **Root Directory** du projet Vercel : **`frontend`**. |

Les URLs de référence (API, santé, OpenAPI) sont regroupées dans le **`README.md`** à la racine du dépôt.

---

## URL du frontend (Vercel)

L’URL de production du frontend est du type **`https://<nom-du-projet>.vercel.app`** (ou domaine personnalisé). Elle est documentée dans le **README** (tableau *URL du frontend*) : **mettez à jour cette ligne** après le premier déploiement réussi pour que les lecteurs du dépôt (correcteurs, équipe) disposent du lien officiel.

Variable d’environnement côté Vercel :

- **`NEXT_PUBLIC_API_URL`** = URL HTTPS du backend Railway (sans slash final superflu si votre client l’assemble déjà avec les chemins).

Côté backend Railway :

- **`CORS_ORIGINS`** doit inclure l’URL exacte du frontend Vercel (origine CORS).

---

## Déploiement automatique (branche `main`)

Configuration attendue pour des mises à jour **à chaque push** sur **`main`** :

1. **Vercel** — Projet connecté au dépôt GitHub/GitLab ; **Production Branch** = **`main`** ; répertoire racine du build = **`frontend`**. Chaque merge ou push sur `main` déclenche un nouveau déploiement production.

2. **Railway** — Service backend connecté au **même dépôt** ; branche de déploiement **`main`** (comportement par défaut du déploiement automatique). Un nouveau commit sur `main` reconstruit et redéploie l’image.

3. **CI GitHub** — Le workflow **`.github/workflows/backend-ci.yml`** exécute **`pytest`** sur les pull requests et pushes ; il peut être utilisé comme garde-fou avant fusion (optionnel : Railway peut attendre la CI selon les réglages du projet).

---

## Après un déploiement

- **Backend** : `GET /health` doit renvoyer `{"message":"ok","app":"newsfoundry-api"}`.
- **Migrations** : sur PostgreSQL Railway, exécuter **`alembic upgrade head`** lors des évolutions de schéma (voir `backend/README.md`).
- **Secrets** : jamais de fichier `.env` committé ; variables uniquement dans Railway / Vercel.
