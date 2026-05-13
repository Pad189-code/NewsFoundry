# Regard critique — Performance perçue et qualité des résultats

Ce document propose une **lecture critique** de la solution NewsFoundry actuelle : fluidité des interactions, pertinence des réponses, et **pistes d’amélioration réalistes**.  

**Note méthodologique** — En l’absence de **télémétrie de production** (APM, traces utilisateurs) dans le dépôt, les « mesures » citées ci‑dessous sont soit des **ordres de grandeur usuels** pour les applications conversationnelles, soit des **indicateurs à instrumenter** ; la mise en place de ces mesures fait partie des recommandations.

---

## Synthèse des limites observables dès l’architecture actuelle

| Zone | Comportement actuel (risque UX) |
|------|----------------------------------|
| **Chat** | Réponse HTTP **complète** après exécution du graphe agent (éventuels appels World News + LLM). L’utilisateur voit un état « chargement » jusqu’à la fin. |
| **Revue de presse** | Pipeline **synchrone** : construction transcript + (optionnel) index LlamaIndex + **deux** passages LLM coûteux conceptuellement (retrieve + génération structurée). Durée **non journalisée** côté API. |
| **Qualité** | Bonnes bases (prompt système figé, revue structurée Pydantic, RAG optionnel), mais **pas de boucle de mesure systématique** (pas de jeu de référence ni de scores en CI). |

Références UX conversationnelles : au‑delà de **~3–10 secondes** sans retour textuel, la perception de « lenteur » augmente fortement ; au‑delà de **~30–60 secondes** pour une action ponctuelle (ex. génération), une **progression visible** (streaming ou étapes) devient quasi indispensable pour limiter l’abandon (*cf.* usages courants des assistants et guides de latence web).

---

## Piste 1 — Observabilité des agents (MLflow Tracing + métriques de latence)

### Constats et exemples concrets

- Aujourd’hui, une défaillance se voit surtout **dans le chat** sous forme de message texte (« Impossible d’appeler le modèle… ») ou via les logs serveur — sans lien automatique entre **requête HTTP**, **étapes agent**, **appel d’outil** et **durée**.
- **Exemple vécu côté utilisateur** : une question qui déclenche `rechercher_actualites` peut prendre nettement plus longtemps qu’une réponse purement contextuelle ; sans trace, on ne sait pas si le goulot est **World News**, **Gemini/OpenAI**, ou la **sérialisation**.

### Pourquoi agir

- La documentation **MLflow Tracing** et l’intégration **PydanticAI ↔ MLflow** permettent de corréler **spans** (tool-call, modèle, erreurs) avec la latence totale — utile pour la **Performance Analysis** (passage des plaintes utilisateurs à des optimisations ciblées).

### Réalisation (grandes lignes)

1. Ajouter **MLflow** (Tracking + Tracing) au backend, avec un **experiment** dédié « NewsFoundry ».
2. Envelopper `run_agent_reply` et `run_press_review_structured` avec le **tracing PydanticAI** documenté par MLflow (runs imbriqués par `chat_id` / `trace_id` corrélé au request-id FastAPI).
3. Émettre des **métriques custom** : durée `POST /messages`, durée `POST /reviews`, nombre de tool-calls, codes HTTP World News.
4. Tableaux de bord : latence **p50 / p95**, taux d’erreur par étape.

**Critère de succès mesurable** — Identifier en **&lt; 1 jour d’exploration** quel span représente **≥ 60 %** du temps sur les requêtes les plus lentes (donnée issue des traces, pas d’intuition).

---

## Piste 2 — Streaming des réponses du chat (meilleure fluidité)

### Constats et exemples concrets

- Le frontend attend la **réponse JSON complète** du message assistant avant affichage — même lorsque le modèle « tape » token par token.
- **Comparaison** : la majorité des chats grand public affichent un **flux de texte** ; la perception de délai est réduite même si la durée totale est identique (effet **time‑to‑first‑token**).

### Pourquoi agir

- Améliorer le **time‑to‑first‑byte** perçu : objectif typique **&lt; 500 ms–1 s** avant le premier fragment affiché sur une connexion correcte (hors cold start), contre plusieurs secondes d’écran figé aujourd’hui.

### Réalisation (grandes lignes)

**Backend**

1. Nouvel endpoint ou variante de `POST /chats/{id}/messages` qui renvoie **`text/event-stream`** (SSE) ou chunked HTTP.
2. Utiliser le **streaming** exposé par le runtime du modèle dans **PydanticAI** / fournisseur (flux de texte du modèle principal ; pour les tours avec **tool-call**, le flux peut être interrompu puis repris après l’outil — UX à clarifier : indicateur « recherche d’articles… »).
3. Toujours **persister le message assistant complet** en base une fois le flux terminé (comme aujourd’hui), pour cohérence historique.

**Frontend**

1. `fetch` avec lecteur de stream ou **`EventSource`** vers l’URL SSE.
2. Mise à jour incrémentale du dernier bulle assistant ; curseur / animation discrète pendant réception.
3. Gestion d’erreur : si le stream coupe, afficher un message d’échec et ne pas dupliquer le message utilisateur.

**Mesure** — Comparer **temps jusqu’au premier caractère affiché** avant/après sur une même question de référence (stopwatch ou événement navigateur `Performance`).

---

## Piste 3 — Temps de génération des revues de presse et lien à la taille du chat

### Ce que l’on peut dire sans métriques internes

Le dépôt **ne publie pas** de temps moyen mesuré pour `POST /chats/{id}/reviews`. Pour répondre objectivement aux questions « temps moyen », « satisfaisant », « variation avec la longueur », il faut **instrumenter** (voir Piste 1) ou un **script de benchmark** local.

### Comportement attendu (à valider par mesure)

| Facteur | Effet probable sur la durée |
|---------|------------------------------|
| **`_messages_as_text(..., limit=120)`** | Plafonne la partie transcript, mais un historique dense peut encore représenter **beaucoup de tokens** envoyés au modèle revue. |
| **RAG LlamaIndex** (si activé) | Coût **supplémentaire** : embeddings des documents + retrieval **avant** la génération structurée ; croît avec le **nombre d’articles** en base plus que avec la longueur du chat seul. |
| **Sortie structurée** (`PressReviewAgentOutput`) | Souvent **plus lente** qu’une simple chaîne libre (schéma imposé). |

### Ordres de grandeur « satisfaisants » (références pratiques)

- **Génération batch** type rapport : au‑delà de **30–45 secondes** sans feedback, l’utilisateur interprète souvent un blocage ; au‑delà de **60–90 secondes**, une **barre de progression** ou une estimation (« ~1 min ») améliore la tolérance.
- Ces seuils sont des **objectifs produit** à affiner ; ils ne remplacent pas une mesure sur vos utilisateurs réels.

### Réalisation (grandes lignes)

1. **Middleware FastAPI** ou décorateur : logger `duration_ms` pour `/reviews` avec dimension **`len(transcript_chars)`** et **`nb_articles`**.
2. **Benchmark reproductible** : suite de chats synthétiques (court / moyen / long) exécutée en CI optionnelle avec **timeout** et rapport CSV (sans appeler les vraies APIs si mocks).
3. **Réductions possibles** si la mesure confirme un goulot :
   - résumer le transcript **avant** revue (modèle léger ou extractif) ;
   - réduire **`similarity_top_k`** ou la taille des chunks RAG ;
   - **async job** + notification lorsque la revue est prête (file Redis/RQ) si la latence dépasse systématiquement le seuil acceptable.

**Critère mesurable** — Documenter la **régression** : p95 temps `/reviews` ne doit pas augmenter de **plus de X %** après une optimisation (X défini par l’équipe, mesure avant/après sur le même bench).

---

## Piste 4 — Qualité des résultats : pertinence et cohérence

### Exemples visibles dans la conception actuelle

- Le chat peut renvoyer des **réponses de secours** lorsque les clés LLM manquent — utile pour la disponibilité, mais risque de **baisser la qualité perçue** si ce mode est trop fréquent en production.
- La **revue** repose sur un transcript **nettoyé** des messages d’erreur technique ; si ce filtrage échoue, la synthèse peut **répéter du bruit** — phénomène déjà anticipé dans le code (`sanitize_transcript_for_review`, `_polish_review_output`).
- Le **RAG** sans embeddings (fallback titre/résumé) peut inclure des articles **peu liés** au sujet choisi si la liste est longue — la pertinence dépend fortement du retrieval lorsque les clés sont présentes.

### Réalisation (grandes lignes)

1. **Jeu d’évaluation fixe** (10–30 couples « contexte chat + sujet ») avec notation humaine ou LLM‑as‑judge **contraint** aux sources fournies.
2. **Guardrails** post‑génération : refus ou reformulation si aucune URL du contexte ne supporte une affirmation forte.
3. **A/B** entre RAG activé / désactivé sur un sous‑ensemble d’utilisateurs une fois MLflow en place.

---

## Piste 5 — Charge et parallélisme côté serveur

### Exemple concret

- Après un tool-call, le backend **ré‑écrit** articles + URLs ; si le trafic augmente, la contention DB + appels externes peut augmenter la queue des requêtes — invisible sans métriques concurrentielles.

### Réalisation (grandes lignes)

- Pool de connexions SQLAlchemy dimensionné ; timeouts explicites sur **httpx** (déjà présents sur World News) ; éventuellement **limite de concurrence** par utilisateur sur `/messages` et `/reviews`.

---

## Liens utiles (ressources du brief)

- **MLflow — Tracing & analyse de performance** : corrélation traces / latence / retours utilisateurs.
- **Intégration MLflow avec PydanticAI** : spans autour des runs d’agents.
- **Streaming LLM** : mécanisme standard **SSE** ou chunks HTTP pour envoyer les tokens au fur et à mesure ; à combiner avec la stratégie tool-call (affichage d’état intermédiaire).

---

## Références croisées

- **`docs/EVOLUTIONS_IA.md`** — autres axes (coût, observabilité erreurs) complémentaires.
- **`docs/ARCHITECTURE_ET_CHOIX_TECHNIQUES.md`** — contexte technique pour implémenter les pistes ci‑dessus.

---

*Document rédigé pour la livraison : les équipes peuvent en faire une checklist priorisée (Impact × Effort) avant passage en prod.*
