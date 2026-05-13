# Évolutions possibles — Qualité et performance (IA)

Ce complément répond à la demande de suggestions structurées pour la partie IA : chaque axe propose une **métrique ou un exemple**, une **piste d’implémentation réaliste**, et un **objectif mesurable**.

---

## 1. Fiabilité des appels d’outils (chat)

**Constat** — Le modèle doit décider d’appeler `rechercher_actualites` au bon moment ; selon le modèle et le prompt, l’outil peut être sous-utilisé ou invoqué avec des sujets trop vagues.

| Aspect | Détail |
|--------|--------|
| **Exemple de métrique** | Taux de conversations où au moins un tool-call a lieu parmi les sessions où l’utilisateur pose une question factuelle (à définir via intentions ou mots-clés). |
| **Piste d’implémentation** | Ajouter des tests d’évaluation (golden prompts) avec **`TestModel`** et `call_tools` forcés ; ajuster le prompt système ou proposer des « suggestions de recherche » en UI. |
| **Objectif mesurable** | Par exemple : **+20 %** de sessions avec au moins un appel réussi à l’outil sur un jeu de 50 scénarios fixes après itération prompt (mesure avant/après sur la même suite). |

---

## 2. Latence bout-en-bout (message → réponse)

**Constat** — Enchaînement : persistance message → agent → éventuels tools → réponse.

| Aspect | Détail |
|--------|--------|
| **Exemple de métrique** | **p95** du temps entre `POST /chats/{id}/messages` et la réponse HTTP (logs ou APM). |
| **Piste d’implémentation** | Paralléliser ce qui est indépendant ; réduire les `limit` d’historique ; cache court pour **top-news** côté serveur si la politique produit le permet ; streaming SSE (plus gros chantier). |
| **Objectif mesurable** | **p95 &lt; 8 s** sur un scénario de référence sans tool, **&lt; 15 s** avec un tool search-news (à ajuster selon SLA produit). |

---

## 3. Qualité de la revue de presse (RAG + structured output)

**Constat** — Le RAG dépend des embeddings et du découpage ; la sortie structurée peut encore halluciner si le transcript est pauvre.

| Aspect | Détail |
|--------|--------|
| **Exemple de métrique** | Score humain ou LLM-as-judge sur **fidélité aux sources** (échelle 1–5) sur un échantillon de N revues ; ou taux de « citations » vérifiables vers les URLs présentes dans le contexte RAG. |
| **Piste d’implémentation** | Forcer dans le schéma Pydantic des **URL par bloc** ; post-validation qui rejette les mentions sans source dans le contexte ; chunks plus fins ou **reranking** (cross-encoder léger) après retrieval LlamaIndex. |
| **Objectif mesurable** | Par exemple : note moyenne de fidélité **≥ 4/5** sur un jeu de 20 jeux de données figés après une itération. |

---

## 4. Coût API (World News + LLM + embeddings)

**Constat** — Chaque message, tool-call et revue consomme des quotas.

| Aspect | Détail |
|--------|--------|
| **Exemple de métrique** | Coût moyen par **session active** par jour (agrégation factures OpenAI / Google + quotas World News). |
| **Piste d’implémentation** | Limites par utilisateur (`number` d’articles, fréquence revue), **`NEWSFOUNDRY_DISABLE_RAG`** en environnements de démo, embeddings **HF locaux** pour le RAG hors prod. |
| **Objectif mesurable** | Réduction **≥ 15 %** du coût par session sans baisser la satisfaction (mesure utilisateur ou taux d’erreur inchangé). |

---

## 5. Observabilité et erreurs utilisateur

**Constat** — Les erreurs LLM / API sont parfois renvoyées sous forme de texte dans le chat pour rester disponibles sans HTTP 500.

| Aspect | Détail |
|--------|--------|
| **Exemple de métrique** | Part des réponses assistant contenant une chaîne d’erreur connue (`Impossible d’appeler le modèle`, etc.) — détectable par tests ou logs structurés. |
| **Piste d’implémentation** | Codes d’erreur internes + message utilisateur générique ; corrélation **request-id** dans les logs serveur. |
| **Objectif mesurable** | **&lt; 2 %** des messages assistant avec erreur technique visible sur une semaine de prod (après instrumentation). |

---

*Document évolutif : ajuster les seuils selon le contrat produit et les mesures réelles une fois l’observabilité en place.*
