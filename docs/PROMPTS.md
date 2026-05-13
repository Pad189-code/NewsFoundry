# Choix et raisons des prompts (LLM)

Ce document résume **pourquoi** les prompts système et les consignes utilisateur ont été formulés ainsi — pour faciliter la revue de code et l’évolution produit.

---

## Agent chat (`services/chat_agent.py`)

### `SYSTEM_PROMPT_BASE`

- **Rôle** : positionner l’assistant comme **spécialiste revue de presse NewsFoundry**, en français, ton professionnel.
- **Référence au bloc actualités** : le prompt indique qu’un bloc « Dernières actualités » peut être présent **dans le prompt système persisté** (`chat.system_prompt_saved`), construit à partir de **World News API / top-news** (titres + résumés seulement).
- **Raison** : compenser la **cutoff** des LLM sans injecter des articles entiers (taille de contexte et coût).

### Prompt système enrichi à la création de discussion

- Lors de `POST /chats`, le serveur peut concaténer **`SYSTEM_PROMPT_BASE`** + un bloc **top-news** (titres/résumés).
- **Pourquoi le figer en base (`system_prompt_saved`)** : éviter que le même fil de discussion change de « jour à jour » dans son socle factuel si l’utilisateur continue la conversation plus tard.

### Message utilisateur agrégé pour l’agent

- Le runtime assemble **articles déjà chargés**, **historique récent** (texte), puis **message courant**.
- **Raison** : donner au modèle une vue compacte sans rejouer tout l’historique JSON brut.

---

## Outil `rechercher_actualites`

- La **description de l’outil** (docstring PydanticAI) dit explicitement qu’il s’agit d’une recherche d’articles récents via World News.
- **Raison** : guider le **tool-calling** vers une intention claire (recherche par sujet).

---

## Agent revue de presse (`services/review_agent.py`)

### `REVIEW_AGENT_SYSTEM`

- **Tâche** : rédacteur en chef, synthèse **à partir de l’historique** ; extraits d’articles en complément.
- **Consignes de fidélité** : ne pas inventer de faits hors matériel ; **ignorer** les messages d’erreur technique du chat (clés API, erreurs modèle).
- **Raison** : limiter les **hallucinations** et éviter que des réponses de secours (« Impossible d’appeler le modèle ») polluent la revue.

### Bloc utilisateur structuré (`run_press_review_structured`)

- Contient **thématique**, **historique nettoyé**, puis **extraits articles** (RAG ou concaténation).
- **Raison** : séparer clairement les trois sources pour que le modèle privilégie l’historique tout en s’appuyant sur les sources chargées.

---

## RAG revue (`services/review_rag.py`)

- Pas un « prompt créatif » à proprement parler : le retrieval réduit le volume envoyé au modèle revue en privilégiant les documents **sémantiquement proches du sujet**.
- **Fallback** sans embeddings : retour au bloc titre/résumé complet — **stabilité** avant **optimisation** coût/latence.
