# Fiche de soutenance — IA & synthèse NewsFoundry (10 minutes)

**Projet** : NewsFoundry — assistant revue de presse (monorepo FastAPI + Next.js)  
**Public** : jury / formateur OCR — focus **intégration IA**, pas démo UI complète  
**Durée cible** : **10 min** (+ 2–3 min questions si prévues)

---

## Timing recommandé

| Min | Thème | À dire en une phrase |
|-----|--------|----------------------|
| 0:00–1:00 | Accroche & objectif | « Veille conversationnelle + revue de presse structurée sur un thème, ancrée sur de vraies sources. » |
| 1:00–2:30 | Où vit la synthèse | « Deux agents PydanticAI : chat avec outils, revue sans outils mais sortie typée. » |
| 2:30–4:00 | Stack IA & modèles | « Multi-fournisseur (Gemini / Mistral / OpenAI), World News, RAG LlamaIndex optionnel. » |
| 4:00–5:30 | Contexte & historique | « Historique borné, prompt figé, articles persistés — la revue réutilise la veille du chat. » |
| 5:30–7:00 | Revue sur un sujet | « POST /reviews : thème + transcript + RAG → JSON structuré → base + UI. » |
| 7:00–8:30 | Qualité & tests | « Prompts de fidélité, nettoyage transcript, Pytest + TestModel, CI GitHub. » |
| 8:30–9:30 | Perf, défis, doc | « Rate limit, plafonds contexte, replis gracieux ; limites assumées et documentées. » |
| 9:30–10:00 | Pistes & conclusion | « Streaming, observabilité, multi-sources — RAG déjà amorcé. » |

---

## 0:00 — Accroche (≈ 1 min)

**Phrase d’ouverture**

> « NewsFoundry aide un journaliste ou un analyste à **constituer une veille** sur l’actualité, puis à **produire une revue de presse** structurée sur un **sujet précis**, sans inventer des articles : tout repose sur **World News API** et sur ce qui a été discuté dans le chat. »

**Contexte technique en 20 secondes**

- Frontend **Next.js** (Vercel) → API **FastAPI** (Railway) → **PostgreSQL**
- Auth **JWT**, isolation par utilisateur (`_chat_or_404`)
- Prod : voir tableau URLs dans `docs/ARCHITECTURE_ET_CHOIX_TECHNIQUES.md`

**Transition** : « La synthèse automatique n’est pas un seul appel LLM : c’est **deux pipelines** complémentaires. »

---

## 1:00 — Intégration de la synthèse (≈ 1 min 30)

### Schéma à dessiner ou montrer (30 s)

```
Utilisateur → Chat → World News (search) → Articles en BDD
                ↓
         Agent chat (réponses + outil recherche)
                ↓
     Modale "Revue" + thème → Agent revue → PressReview persistée
```

### Point clé à marteler

| Agent | Fichier | Rôle |
|-------|---------|------|
| **Chat** | `backend/src/services/chat_agent.py` | Conversation, **outil** `rechercher_actualites`, réponses Markdown |
| **Revue** | `backend/src/services/review_agent.py` | **Aucun outil** — sortie **Pydantic** `PressReviewAgentOutput` |

**Pourquoi deux agents ?**  
Objectifs différents : le chat **explore** et **charge** des sources ; la revue **synthétise** de façon **éditoriale et structurée**. Un seul agent ferait des compromis sur le tool-calling et le format de sortie.

**Recherche proactive** : à chaque message, `chat_live_search.py` interroge World News avec le texte utilisateur et **persiste** les articles — la veille avance même si le modèle n’appelle pas l’outil.

**Transition** : « Côté modèles, on a choisi la **flexibilité multi-fournisseur**. »

---

## 2:30 — Technologies IA & LLM (≈ 1 min 30)

### Framework

- **PydanticAI** : agents, tools, `output_type`, tests avec **`TestModel`** (sans réseau)

### Fournisseurs LLM (variables d’environnement)

| Priorité typique | Modèle par défaut | Clé |
|------------------|-------------------|-----|
| Google | `gemini-1.5-flash` | `GOOGLE_API_KEY` |
| Mistral | `mistral-small-latest` | `MISTRAL_API_KEY` |
| OpenAI | `gpt-4o-mini` | `OPENAI_API_KEY` |

- Résolution : `backend/src/services/llm_model_spec.py`  
- Modèles **chat** et **revue** peuvent diverger (`GEMINI_REVIEW_MODEL`, etc.)

### Données & RAG

| Brique | Rôle |
|--------|------|
| **World News API** | `top-news` (prompt système figé) + `search-news` (chat / outil) |
| **LlamaIndex** | RAG **en mémoire** à la génération de revue (`review_rag.py`) |
| **Embeddings** | OpenAI `text-embedding-3-small` par défaut ; **HF** possible (`USE_HF_EMBEDDINGS`) |

**Pourquoi ces choix ?**

1. **Multi-fournisseur** — pas de dépendance à un seul éditeur (coût, quota, disponibilité).  
2. **Sortie structurée** — champs mappés directement en base (`review_title`, `general_summary`, `articles_breakdown_json`).  
3. **RAG optionnel** — pertinence par thème sans indexer toute la base ; `NEWSFOUNDRY_DISABLE_RAG=1` pour démo / latence.

**Transition** : « La qualité de la revue dépend surtout de **comment on prépare le contexte**. »

---

## 4:00 — Contexte & historique (≈ 1 min 30)

### Trois sources de contexte

1. **Prompt système figé** — `Chat.system_prompt_saved`  
   - Création du chat : `SYSTEM_PROMPT_BASE` + bloc **top-news** (titres + résumés).  
   - **Figé en base** : la discussion ne « change pas de jour » au milieu d’un fil.

2. **Historique conversationnel** — `Chat.messages_json`  
   - Chat : **25** derniers messages en texte `ROLE: contenu`.  
   - Revue : **120** derniers messages (transcript plus long).

3. **Articles persistés** — table `Article` + `loaded_articles`  
   - Chaque recherche (live ou outil) alimente la BDD.  
   - La revue **ne relance pas obligatoirement** une recherche presse : elle s’appuie sur la veille déjà faite.

### Assemblage côté revue

```
Thématique (saisie utilisateur)
+ Historique nettoyé (sanitize_transcript_for_review)
+ Extraits articles (RAG ou liste titre/résumé)
→ run_press_review_structured()
```

**Phrase jury** : « On sépare clairement **ce qui a été dit** et **ce qui a été chargé comme source**, pour que le modèle ne confonde pas erreur technique et contenu éditorial. »

**Transition** : « Voyons le parcours **revue sur un sujet précis**. »

---

## 5:30 — Revue de presse sur un thème (≈ 1 min 30)

### Parcours utilisateur (30 s)

1. Discuter dans le chat → articles chargés.  
2. Modale **« Générer une revue de presse »** → saisir le **thème** (ex. « transition énergétique »).  
3. `POST /chats/{id}/reviews` → affichage + liste `GET /reviews`.

### Côté serveur (`routes.py`, `create_review`) — 60 s

1. Transcript (120 msgs max).  
2. Articles du `chat_id`, triés par date.  
3. Si vide → **400** avec message explicite.  
4. `retrieve_review_context(topic, articles)` — RAG ou fallback.  
5. `run_press_review_structured` → `PressReviewAgentOutput`.  
6. Persistance : Markdown `content` + JSON structuré + aperçu sur `Chat`.

### Sortie structurée (à citer)

- `title` — titre éditorial  
- `general_summary` — synthèse générale sur le thème  
- `articles_mentioned[]` — titre, date, synthèse par source/thème  

**Démo rapide possible** : montrer une revue générée dans l’onglet « Revues de presse » ou la réponse OpenAPI `/docs`.

**Transition** : « Comment on **contrôle la qualité** et on **valide** ? »

---

## 7:00 — Qualité, tests, limites (≈ 1 min 30)

### Qualité du contenu synthétisé

| Mécanisme | Effet |
|-----------|--------|
| Prompt revue | Fidélité aux sources, pas de faits inventés, ignorer erreurs API |
| `sanitize_transcript_for_review` | Retire les messages assistant « Impossible d’appeler le modèle… » |
| `_polish_review_output` | Nettoyage post-génération |
| RAG par thème | Réduit le bruit si beaucoup d’articles |
| Repli sans clé LLM | `_fallback_output` structuré, pas d’hallucination « créative » |

### Tests & CI

```powershell
cd backend
$env:TEST_SQLITE="1"
$env:DISABLE_RATE_LIMIT="1"
uv run pytest -q
```

| Preuve | Fichier |
|--------|---------|
| Agent revue + TestModel | `tests/test_review_agent.py` |
| RAG fallback | `tests/test_review_rag.py` |
| Persistance revue API | `test_press_review_structured_persisted_and_list_all_reviews` |
| Isolation utilisateurs | `test_user_cannot_access_other_users_chat` |
| CI | `.github/workflows/backend-ci.yml` |

**Limite honnête (10 s)** : pas encore de **jeu golden** qualité sémantique en CI — prévu dans `docs/EVOLUTIONS_IA.md`.

**Transition** : « Côté **performance** et **défis**, on a fait des choix pragmatiques. »

---

## 8:30 — Performance, défis, documentation (≈ 1 min)

### Optimisations actuelles

- **Rate limiting** (SlowAPI) sur routes sensibles  
- **Plafonds** historique (25 / 120 messages) et taille des blocs envoyés au LLM  
- **RAG non persisté** — pas de coût stockage vectoriel multi-tenant  
- **Repli gracieux** — pas de HTTP 500 si LLM ou World News indisponible (message utilisateur + extrait contexte)

### Défis surmontés (exemples concrets)

| Défi | Solution |
|------|----------|
| Confondre erreur World News et erreur LLM | Messages distincts dans `chat_agent.py` |
| Noms de modèles invalides (404 Mistral/Gemini) | `llm_model_spec.py` |
| Revue polluée par erreurs chat | Sanitize + polish |
| RAG sans clé OpenAI | Fallback concaténation titre/résumé |

### Limites assumées (à dire sans s’excuser)

- Réponse chat **non streamée** — latence perçue jusqu’à fin HTTP  
- Revue **synchrone** — pas de barre de progression métier côté API  
- Peu de **télémétrie** p50/p95 en prod aujourd’hui  

### Documentation livrée

| Document | Usage jury |
|----------|------------|
| `ARCHITECTURE_ET_CHOIX_TECHNIQUES.md` | Vue d’ensemble + choix |
| `PROMPTS.md` | Pourquoi chaque consigne |
| `EVOLUTIONS_IA.md` | Métriques & objectifs |
| `REGARD_CRITIQUE_PERFORMANCE.md` | Streaming, MLflow, bench |
| `GRILLE_LIVRABLES.md` | Mapping compétences → fichiers |

**Transition** : « En conclusion, où on va ensuite. »

---

## 9:30 — Pistes & phrase de clôture (≈ 30 s)

**Pistes réalistes**

- **Streaming SSE** du chat (time-to-first-token)  
- **MLflow Tracing** sur les agents (p95 `/messages`, `/reviews`)  
- **RAG** : reranking, URLs obligatoires dans le schéma, index persisté  
- **Multi-sources** au-delà de World News  
- **File async** pour revues longues + notification UI  

**Phrase de clôture**

> « En résumé : NewsFoundry sépare **veille interactive** et **synthèse éditoriale structurée**, avec des sources traçables, des tests automatisés et une documentation qui assume aussi les limites. La prochaine étape prioritaire serait le **streaming** et l’**observabilité** pour aligner l’expérience utilisateur sur la qualité déjà posée dans les prompts et le schéma de sortie. »

---

## Aide-mémoire — 3 questions fréquentes du jury

**Q : Pourquoi ne pas un seul agent ?**  
R : Tool-calling + sortie structurée sans tools = objectifs incompatibles ; deux prompts, deux modèles possibles, tests plus simples.

**Q : Comment évitez-vous les hallucinations ?**  
R : Consignes de fidélité, contexte limité aux articles chargés + historique nettoyé, RAG par thème, pas de recherche « libre » à la génération de revue, repli sans invention si pas de LLM.

**Q : Comment validez-vous en CI sans payer les APIs ?**  
R : `TestModel` PydanticAI, SQLite mémoire, mocks sur `run_press_review_structured` dans les tests API ; les tests d’intégration réels LLM restent manuels / staging.

---

## Checklist avant de monter sur scène

- [ ] URL prod frontend + API notées (README / `ARCHITECTURE_ET_CHOIX_TECHNIQUES.md`)
- [ ] Une **revue exemple** déjà générée dans l’app (évite d’attendre 30–60 s en live)
- [ ] Terminal prêt : `uv run pytest -q` (optionnel, 15 s)
- [ ] Onglet `/docs` OpenAPI ouvert en backup
- [ ] Ce fichier imprimé ou sur second écran

---

*Durée totale visée : **10 minutes** à débit normal (~900–1000 mots à l’oral). Ajuster en répétition : viser 9 min de discours + 1 min marge.*
