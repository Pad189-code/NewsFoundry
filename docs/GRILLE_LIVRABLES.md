# Correspondance grille de compétences — preuves dans le dépôt

Ce tableau aide à **justifier les livrables** (portfolio, soutenance) en pointant vers le **code** ou la **documentation** réels du projet NewsFoundry.

| Compétence / critère | Où le trouver |
|----------------------|----------------|
| **Tests d’autorisation — utilisateur B ne doit pas accéder aux chats de A** | `backend/tests/test_api.py` → `test_user_cannot_access_other_users_chat` (GET chat, POST message, news/fetch → **404**). |
| **Tests — cas nominal (propriétaire accède à son chat)** | `backend/tests/test_api.py` → `test_proprietaire_acces_chat_nominal` (**200** sur `GET /chats/{id}`) ; le flux complet création + lecture est aussi couvert par `test_chats_flow`. |
| **CI GitHub — exécution automatique des tests** | `.github/workflows/backend-ci.yml` — `uv run pytest -q` avec variables d’environnement de test. |
| **Connexion, discussions, messages, revue** | Parcours implémenté : `routes.py` (endpoints), `frontend/src/app/chats/page.tsx` ; tests API : `test_login_*`, `test_chats_flow`, `test_chat_message_returns_assistant_reply`, `test_press_review_structured_persisted_and_list_all_reviews`. |
| **Conformité Figma** | Non vérifiable automatiquement dans le dépôt ; à valider par capture d’écran / lien maquette si exigé par le formateur. |
| **Production Railway + Postgres + Vercel, déploiement auto `main`** | **`README.md`** (section Déploiement), **`docs/DEPLOIEMENT.md`** ; renseigner l’URL Vercel réelle dans le tableau du README. |
| **Code lisible, découpé, commentaires sur parties complexes** | Exemples : `routes.py` (helpers `_chat_or_404`, `_ensure_chat_system_prompt_saved`), `services/review_agent.py` (nettoyage transcript), commentaires ciblés dans `frontend` lorsque la logique métier l’exige. |
| **`HTTPException` FastAPI** | Utilisations dans `routes.py`, `auth_tokens.py` — référence synthétique **`docs/API_ERREURS.md`**. |
| **Erreurs World News API** | `services/news.py` (`raise_for_status`), `routes.py` (503 si clé absente). |
| **Erreurs LLM** | `services/chat_agent.py`, `services/review_agent.py` (fallbacks textuels, gestion `ModelHTTPError`). |
| **Erreurs appels API frontend + message utilisateur** | `frontend/src/lib/api.ts` (`parseApiError`, erreurs réseau) ; `chats/page.tsx` → état `error` affiché sous les onglets. |
| **Loader / réactivité pendant appels longs** | `chats/page.tsx` — état `busy`, désactivation des boutons, texte « Traitement en cours » avec **indicateur visuel** (spinner) dans l’en-tête ; pied de page « envoi en cours… ». |
| **Documentation structure + choix techniques** | `docs/ARCHITECTURE_ET_CHOIX_TECHNIQUES.md`. |
| **Documentation erreurs API** | `docs/API_ERREURS.md`. |
| **Documentation des prompts** | `docs/PROMPTS.md`. |
| **Performance — pistes, métriques, implémentations, objectifs** | `docs/REGARD_CRITIQUE_PERFORMANCE.md`, `docs/EVOLUTIONS_IA.md`. |

---

*À adapter si votre barème officiel utilise des intitulés légèrement différents.*
