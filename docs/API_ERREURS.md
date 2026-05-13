# Erreurs renvoyées par l’API backend (référence)

FastAPI renvoie les erreurs au format JSON standard : **`{"detail": ...}`** où `detail` est soit une **chaîne**, soit une **liste de validations** (pour les erreurs de corps de requête Pydantic).

Les routes protégées attendent un en-tête : **`Authorization: Bearer <access_token>`**. Sans token valide : **403** (dépendance `get_current_user`).

---

## Authentification (`auth_tokens.py`, `routes.py`)

| Code HTTP | `detail` (exemple) | Contexte |
|-----------|-------------------|----------|
| **401** | `Identifiants invalides` | `POST /login`, `/auth/login` — email ou mot de passe incorrect. |
| **401** | `Token invalide ou expire` / `Utilisateur introuvable` | Token access absent ou expiré (`get_current_user`). |
| **401** | Messages sur refresh token (`Refresh token invalide`, etc.) | `POST /auth/refresh`. |

---

## Discussions et messages (`routes.py`)

| Code HTTP | `detail` (exemple) | Contexte |
|-----------|-------------------|----------|
| **404** | `Discussion introuvable` | Chat inexistant **ou** chat qui n’appartient pas à l’utilisateur (`_chat_or_404`). Même réponse pour éviter l’énumération d’IDs (pas de fuite « existe mais pas à vous »). |
| **400** | Texte sur absence de contenu pour la revue | `POST .../reviews` — pas de messages ni d’articles exploitables. |

---

## World News API (`routes.py`)

| Code HTTP | `detail` (exemple) | Contexte |
|-----------|-------------------|----------|
| **503** | `WORLDNEWS_API_KEY manquante sur le serveur` | `POST .../news/fetch` sans clé configurée côté backend. |

Les erreurs **réseau** ou **HTTP** lors des appels `httpx` vers World News sont gérées dans `services/news.py` (`raise_for_status`) : elles remontent comme **500** non gérées sauf si encapsulées — en pratique les flux principaux attrapent et normalisent le comportement côté agent ou message utilisateur.

---

## Comportement des LLM (pas toujours une erreur HTTP)

Les échecs du fournisseur LLM (quota, modèle indisponible, clé manquante) sont en général **convertis en texte** dans la réponse assistant ou dans la revue (messages du type « Impossible d’appeler le modèle… ») pour éviter un **500** brut à chaque incident — voir `services/chat_agent.py` et `services/review_agent.py` (`ModelHTTPError`, fallbacks).

---

## Liste utile pour le frontend (`frontend/src/lib/api.ts`)

Le client lit **`detail`** depuis le JSON d’erreur et l’affiche à l’utilisateur lorsque la réponse n’est pas `ok`. Les erreurs réseau (backend arrêté) sont enveloppées dans un message explicite invitant à lancer le serveur.

Pour la liste exhaustive et à jour, ouvrir la doc interactive : **`GET /docs`** (Swagger) sur l’instance backend.
