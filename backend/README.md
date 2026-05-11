# NewsFoundry Backend

1. Copier le fichier `.env.example` dans `.env`


2. Installer les dépendances:
```bash
uv sync
```

2. Démarrer la base de données:
```bash
docker run \
  --name newsfoundry_db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=newsfoundry \
  -p 5432:5432 \
  postgres:17
```

3. **Migrations Alembic (PostgreSQL, anciennes tables `conversation` / `message`)**

Si vous mettez à jour une base qui contenait encore l’ancien schéma (discussions en lignes séparées), **sauvegardez** la base (`pg_dump`), puis :

```bash
cd backend
# Sans TEST_SQLITE : Alembic doit pointer vers la même DATABASE_URL que la prod / le dev Postgres
uv run --env-file .env alembic upgrade head
```

La révision `20260211_legacy_to_chat` : crée `chat`, copie chaque ligne `conversation` avec l’historique agrégé en `messages_json`, renomme les FK `article` / `pressreview` en `chat_id`, supprime `message` et `conversation`. Elle **ne s’exécute pas** sur SQLite et ne fait **rien** si `conversation` est déjà absente (schéma actuel).

4. Lancer le backend:
```bash
uv run --env-file .env src/main.py
```

**Cutoff des LLM / actualité du jour** : à l’ouverture d’une discussion (`POST /chats`), le serveur appelle **World News API** `GET /top-news`, compose un bloc **titre + résumé** (pas le corps des articles) et enregistre le **prompt système complet** dans `chat.system_prompt_saved`. Les messages suivants réutilisent ce même prompt pour garder une continuité cohérente. Variables optionnelles : `WORLDNEWS_SOURCE_COUNTRY`, `WORLDNEWS_LANGUAGE` (voir `.env.example`).

## Tests automatises

Les tests utilisent SQLite en memoire (aucun Docker requis) :

```bash
cd backend
set TEST_SQLITE=1
set DISABLE_RATE_LIMIT=1
set JWT_SECRET=pytest-jwt-secret-at-least-32-characters-long!!
uv run pytest -q
```

Sur Linux/macOS : `export TEST_SQLITE=1` etc. La CI GitHub Actions execute la meme suite (workflow `Backend CI`).

## Deploiement (ex. Railway) — points verifies

| Point | Statut |
|--------|--------|
| **Contexte Docker** | Le `Dockerfile` attend la **racine du monorepo** comme contexte (`COPY backend/...`). Sur Railway : repo complet, Dockerfile `backend/Dockerfile`. |
| **Port** | `PORT` est lu dans `main.py` (variable injectee par Railway). |
| **Migrations** | L'image inclut `alembic/` et `alembic.ini`. Avant ou au demarrage : `uv run alembic upgrade head` (meme `DATABASE_URL` que l'app). `init_db()` fait surtout `create_all` ; Alembic reste la source de verite pour l'evolution du schema. |
| **`DATABASE_URL`** | Si l'URL commence par `postgres://`, elle est normalisee en `postgresql://` (app + Alembic). |
| **Compte demo** | `test@test.com` / `test` n'est cree que si `TEST_SQLITE=1` (tests) **ou** `SEED_DEFAULT_USER=1`. En production : **ne pas** definir `SEED_DEFAULT_USER` (ou `0`). |
| **Logs SQL** | Par defaut `echo=False` sur le moteur Postgres. Activer avec `SQL_ECHO=1` seulement en debug. |
| **CORS** | Definir `CORS_ORIGINS` avec l'URL du frontend (ex. Vercel). |
| **Secrets** | `JWT_SECRET`, cles API news / LLM, etc. uniquement dans les variables du service (pas de `.env` dans l'image). |
