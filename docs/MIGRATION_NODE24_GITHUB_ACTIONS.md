# Plan de migration Node.js 24 — GitHub Actions (NewsFoundry)

**Date d’analyse :** 28 mai 2026  
**Échéance GitHub :** dépréciation Node.js 20 pour les *actions JavaScript* — retrait prévu à l’automne 2026 ; passage au Node 24 par défaut sur les runners à partir du **16 juin 2026** ([changelog GitHub](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)).

---

## 1. Synthèse

Le workflow `backend-ci.yml` n’exécute **pas** Node.js pour l’application (backend Python via `uv`). Seules les **actions GitHub écrites en JavaScript** embarquent un runtime Node.js interne (`runs.using: node20` ou `node24`).

| Action | Version avant | Runtime JS | Version cible | Runtime JS |
|--------|---------------|------------|---------------|------------|
| `actions/checkout` | `@v4` | `node20` | `@v6` | `node24` |
| `astral-sh/setup-uv` | `@v5` | `node20` | `@v8.1.0` | `node24` |

Le job `deploy` n’utilise que `checkout` + scripts `bash` (`curl`, `jq`) — **aucun** `setup-node` ni build frontend.

---

## 2. Inventaire détaillé du workflow

Fichier : `.github/workflows/backend-ci.yml`

### Job `test`

| Étape | Type | Node.js concerné ? |
|-------|------|-------------------|
| `actions/checkout@v4` → **v6** | Action JS | Oui — runtime de l’action |
| `astral-sh/setup-uv@v5` → **v8.1.0** | Action JS | Oui — runtime de l’action |
| `uv sync` | `run:` shell | Non — Python/uv sur le runner |
| `uv run pytest` | `run:` shell | Non |

### Job `deploy`

| Étape | Type | Node.js concerné ? |
|-------|------|-------------------|
| `actions/checkout@v4` → **v6** | Action JS | Oui |
| Déploiement Railway (GraphQL) | `run:` bash | Non |
| Attente déploiement | `run:` bash | Non |

**Conclusion :** aucune étape `actions/setup-node` dans ce dépôt ; la migration porte uniquement sur les **versions d’actions**, pas sur un runtime Node applicatif dans le CI backend.

---

## 3. Changements appliqués

```yaml
# Avant
- uses: actions/checkout@v4
- uses: astral-sh/setup-uv@v5
  with:
    version: "latest"

# Après
- uses: actions/checkout@v6
- uses: astral-sh/setup-uv@v8.1.0
  with:
    version: "latest"
    working-directory: backend
```

### Justification des versions

- **`actions/checkout@v6`** : `action.yml` déclare `using: node24` (v4/v5 utilisaient `node20`).
- **`astral-sh/setup-uv@v8.1.0`** : `using: node24` depuis la v7 ; tag **immuable** recommandé par Astral (v8+ ne publie plus de tags flottants `@v8`).
- **`working-directory: backend`** : `defaults.run.working-directory` ne s’applique pas aux actions `uses:` ; ce paramètre aligne la résolution de `pyproject.toml` / `uv.lock` et les clés de cache sur le dossier backend.

---

## 4. Runtime Node.js dans le workflow

| Contexte | État |
|----------|------|
| Runtime des **actions** JS | Migré vers Node 24 via checkout v6 et setup-uv v8.1.0 |
| Runtime **applicatif** dans `backend-ci.yml` | N/A (Python 3.13+ via uv) |
| `actions/setup-node` | Absent — rien à passer en `node-version: 24` dans ce workflow |

Sur les **runners GitHub** (`ubuntu-latest`), Node 20 sera retiré du toolcache vers **mai–juin 2026** ; le défaut passera à Node 22 puis les actions JS seront forcées en Node 24. Ce workflow n’appelle pas `node`/`npm` en ligne de commande, donc **pas d’impact direct** sur les étapes `run:`.

---

## 5. Compatibilité des dépendances du projet

### Backend (Python) — impact **nul** sur Node 24

- Stack : FastAPI, uv, Python `>=3.13` (`backend/pyproject.toml`).
- Le CI exécute `uv sync` et `pytest` ; indépendant de la version Node des actions.

### Frontend (Next.js 16) — hors scope du workflow actuel

- Fichier : `frontend/package.json` (Next `16.2.4`, React 19).
- Exigence officielle Next.js 16 : **Node.js ≥ 20.9.0** ; Node 24 est compatible pour le développement et le build.
- `@types/node: ^20` : types TypeScript uniquement ; optionnel de monter vers `@types/node@^24` si un futur workflow frontend cible Node 24.
- **Aucun workflow CI frontend** dans le dépôt à ce jour — pas de changement requis pour `backend-ci.yml`.

### Déploiement Railway

- Scripts bash + API GraphQL ; pas de dépendance Node.js.

---

## 6. Calendrier GitHub (référence)

| Date (indicative) | Événement |
|-------------------|-----------|
| Avril 2026 | Fin de vie Node.js 20 (upstream) |
| 16 juin 2026 | Runners : Node 24 par défaut pour les actions JavaScript |
| Automne 2026 | Retrait de Node 20 pour l’exécution des actions |
| Sept. 2026 (mention utilisateur) | Fenêtre de conformité cible pour NewsFoundry |

Opt-out temporaire (non recommandé en production) :  
`ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true` ou test anticipé :  
`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` au niveau `env:` du workflow.

---

## 7. Procédure de validation

### 7.1 Test local du workflow (après push)

1. Pousser sur une branche de test et ouvrir une PR → job `test` doit passer.
2. Vérifier l’onglet **Actions** : plus d’avertissement du type *"Node.js 20 actions are deprecated"*.
3. Sur `main` (si secrets Railway configurés) : valider le job `deploy`.

### 7.2 Test anticipé Node 24 (optionnel, avant merge)

Ajouter temporairement en tête de workflow :

```yaml
env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true
```

Puis retirer une fois les actions mises à jour (redondant avec checkout v6 / setup-uv v8).

### 7.3 Vérifications fonctionnelles

- [ ] `uv sync` réussit (cache setup-uv éventuellement invalidé au premier run — normal après montée v5 → v8).
- [ ] `pytest` vert avec `TEST_SQLITE=1`.
- [ ] Pas de régression sur le déploiement Railway (secrets `RAILWAY_*`).

---

## 8. Risques et mitigations

| Risque | Probabilité | Mitigation |
|--------|-------------|------------|
| Invalidation du cache uv (clés de cache modifiées v5→v8) | Moyenne | Premier run plus long ; runs suivants normaux |
| Tag flottant `@v8` indisponible (politique Astral v8) | N/A si pin `@v8.1.0` | Utiliser tag immuable ou SHA de commit |
| `working-directory` oublié → mauvaise résolution `pyproject.toml` | Faible | Paramètre `working-directory: backend` ajouté |
| Breaking changes `checkout` v4→v6 | Faible | Inputs inchangés pour usage standard (ref, token par défaut) |
| Self-hosted runners sans Node 24 | Faible (projet utilise `ubuntu-latest`) | Mettre à jour le runner ou installer Node 24 |
| Futur CI frontend avec Node 20 implicite | Moyen (futur) | Ajouter `actions/setup-node@v6` avec `node-version: 24` |

### Breaking changes `setup-uv` v5 → v8 (non utilisés ici)

- Suppression des inputs `pyproject-file` / `uv-file` → remplacés par `version-file` (non requis : `version: "latest"`).
- Format `manifest-file` personnalisé : NDJSON (non utilisé).
- Tags majeurs/mineurs flottants supprimés pour setup-uv v8 — **toujours épingler une version exacte**.

---

## 9. Actions futures (hors périmètre immédiat)

1. **Workflow frontend** : si ajouté, utiliser `actions/setup-node@v6` avec `node-version: 24` et `cache: npm`.
2. **`frontend/package.json`** : ajouter `"engines": { "node": ">=20.9.0" }` ou `>=24` selon politique équipe.
3. **Renovate / Dependabot** : surveiller releases `actions/checkout` et `astral-sh/setup-uv` (mises à jour de patch sur tag immuable).
4. **Documentation déploiement** : mentionner dans `docs/DEPLOIEMENT.md` que le CI backend est aligné Node 24 (actions).

---

## 10. Checklist de migration

- [x] Identifier les actions `node20` dans `backend-ci.yml`
- [x] Mettre à jour `actions/checkout` → v6
- [x] Mettre à jour `astral-sh/setup-uv` → v8.1.0 + `working-directory`
- [x] Confirmer l’absence de `setup-node` dans le workflow
- [x] Vérifier compatibilité backend Python / frontend Next (hors CI)
- [ ] Exécuter le workflow sur GitHub et confirmer l’absence d’avertissements
- [ ] (Optionnel) Mettre à jour `@types/node` en v24 lors d’un futur CI frontend

---

## Références

- [Deprecation of Node 20 on GitHub Actions runners](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)
- [actions/checkout — action.yml v6](https://github.com/actions/checkout/blob/v6/action.yml)
- [astral-sh/setup-uv — releases v7+ (node24)](https://github.com/astral-sh/setup-uv/releases)
- [Next.js 16 — Node.js requirements](https://nextjs.org/docs/app/guides/upgrading/version-16)
