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

---

## Variables Railway (service API NewsFoundry)

À jour avec le code actuel (Mistral + Gemini + OpenAI, résolution dans `backend/src/services/llm_model_spec.py`).

### Obligatoires (production)

| Variable | Rôle |
|----------|------|
| **`DATABASE_URL`** | PostgreSQL (service Railway ou URL externe). Ne pas utiliser `TEST_SQLITE` en prod. |
| **`JWT_SECRET`** | Secret fort et unique pour signer les JWT. |
| **`CORS_ORIGINS`** | URL(s) exacte(s) du frontend Vercel, séparées par des virgules si plusieurs (ex. `https://votre-app.vercel.app`). |

### LLM (au moins une combinaison valide)

| Variable | Rôle |
|----------|------|
| **`MISTRAL_API_KEY`** | Clé [La Plateforme Mistral](https://console.mistral.ai) — **à ajouter** si vous utilisez Mistral. |
| **`MISTRAL_MODEL`** | Ex. `mistral-small-latest` — **prioritaire** sur Gemini/OpenAI si défini. |
| **`MISTRAL_REVIEW_MODEL`** | Optionnel : modèle dédié à la revue de presse (sinon alignement sur `MISTRAL_MODEL`). |
| **`GOOGLE_API_KEY`** | Si chat/revue via Gemini (`GEMINI_MODEL` ou défaut Google). |
| **`GEMINI_MODEL`** | Optionnel : ID seul (ex. `gemini-1.5-flash`) ; ignoré si `MISTRAL_MODEL` est défini. |
| **`OPENAI_API_KEY`** | Si chat/revue via OpenAI (`OPENAI_MODEL` en `openai:…`). |
| **`OPENAI_MODEL`** | Ex. `openai:gpt-4o-mini` ou `mistral:mistral-small-latest` ; peut rester vide si Mistral couvre tout via `MISTRAL_MODEL`. |
| **`OPENAI_REVIEW_MODEL`** | Idem pour la revue (ex. `gpt-4o-mini` ou spec `mistral:…`). |
| **`GEMINI_REVIEW_MODEL`** | Optionnel : forcer Gemini pour la revue. |

### Fonctionnalités et réglages

| Variable | Rôle |
|----------|------|
| **`WORLDNEWS_API_KEY`** | Actualités dans le chat (sinon l’outil actualités renvoie un message d’absence de clé). |
| **`WORLDNEWS_SOURCE_COUNTRY`** | Optionnel, ex. `fr`. |
| **`WORLDNEWS_LANGUAGE`** | Optionnel, ex. `fr`. |
| **`PORT`** | Railway l’injecte souvent tout seul ; sinon laisser le défaut du code (`8000`) aligné sur le `Dockerfile`. |
| **`SEED_DEFAULT_USER`** | **Production : laisser vide ou `0`** — ne pas activer le compte démo `test@test.com`. |
| **`SQL_ECHO`** | **Production : laisser vide** — sinon logs SQL très verbeux. |
| **`DISABLE_RATE_LIMIT`** | Production : laisser vide (rate limit actif). |

### Nettoyage si vous passez surtout sur Mistral

- Ajoutez **`MISTRAL_API_KEY`** et **`MISTRAL_MODEL`**.
- Vous pouvez **vider** `GEMINI_MODEL` et `OPENAI_MODEL` si tout le trafic LLM passe par Mistral (tant que `MISTRAL_MODEL` + clé suffisent).
- Conservez **`GOOGLE_API_KEY`** seulement si vous en avez encore besoin ailleurs ; sinon retirable pour réduire la surface.

Après modification des variables : **Redeploy** (ou attendre le redéploiement automatique) sur le service **NewsFoundry-api**.
