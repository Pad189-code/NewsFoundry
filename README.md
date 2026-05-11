# NewsFoundry

## Besoins fonctionnels

- L'utilisateur peut se connecter.
- L’utilisateur peut voir la liste de ses discussions passées.
- L’utilisateur peut démarrer une nouvelle discussion ou reprendre une ancienne discussion.
- Un utilisateur n’est pas autorisé à accéder aux discussions d’un autre utilisateur.
- Le LLM répond aux messages envoyés par l’utilisateur.
- L'utilisateur peut faire générer une revue de presse à partir d'une discussion.
- L'application doit afficher des messages d'erreur à l'utilisateur final en cas d'erreur.

## Prérequis

- Docker
- Python 3.13
- uv
- Node.js 22.19

## Installation

1. Cloner le repository
2. Démarrer le backend aved les instructions du fichier `backend/README.md`
3. Initialiser un projet Next.js dans un dossier `frontend/`

## Choix technologiques

### Frontend

**Next.js**

### Backend

- **Python** pour bénéficier de son écosystème de librairies IA
- **FastAPI** pour le développement de l'API
- Connection avec des **JWT**
- **SQLModel** comme ORM : fait pour bien marcher avec FastAPI.
  - Branché à une base de données **PostgreSQL**
- **PydanticAI** comme client qui s'intégrera aussi bien avec les autres outils de la stack backend
- Attention à la **sécurité des données**. On ne veut pas qu’un utilisateur puisse accéder aux chats d’un autre utilisateur ou les modifier.
  - Le produit aura rapidement beaucoup d’utilisateurs professionnels il est donc crucial de garantir le fonctionnement correct de cette fonctionnalité par l'**implémentation de tests automatisés qui s'exécutent par une Github Action**.
- Pour les sources de news, on utilisera l’API [**WorldNewsAPI**](https://worldnewsapi.com/).
- Pour déployer on mettra le frontend sur **Vercel** et le backend sur **Railway**.

### Documentation

Une documentation claire devra être rédigée et ajoutée dans un dossier `docs/`.

Elle devra inclure des suggestions d'amélioration concernant la qualité et la performance de la partie IA du système. Chaque recommandation doit être illustrée par une une métrique ou un exemple, une proposition d’implémentation réalisable, ainsi qu'un objectif mesurable.


Par ailleurs, pour faciliter la maintenance du projet à long terme, le code du projet devra être clair et bien structuré, accompagné de commentaires qui expliquent les sections de code complexes.

### Déploiement

#### URL du frontend (production)

| | |
|--|--|
| **URL à documenter ici** | `https://____________.vercel.app` *(à remplacer après le premier déploiement — voir ci-dessous)* |
| **Quand l’URL est disponible** | **Dès que le premier déploiement Vercel a réussi** (quelques minutes après le push ou « Deploy »). Elle apparaît dans le tableau de bord du projet Vercel : **Settings → Domains** ou en tête du dernier déploiement (**Visit**). Par défaut c’est `https://<nom-du-projet>.vercel.app` ; un domaine personnalisé s’affiche une fois configuré. Chaque **preview** de branche a aussi sa propre URL (`*.vercel.app`). |
| **Variable côté Vercel** | Définir **`NEXT_PUBLIC_API_URL`** sur l’URL HTTPS publique du backend. |
| **Variable côté backend** | Ajouter l’URL du frontend dans **`CORS_ORIGINS`** (séparateur virgule si plusieurs origines). |

#### Frontend

Déployer le frontend sur [Vercel](https://vercel.com/dashboard). Dans un monorepo, régler le **Root Directory** du projet Vercel sur **`frontend`**.

#### Backend

Déployer le backend sur [Railway](https://railway.com/dashboard). Le `Dockerfile` sous `backend/` suppose un **contexte de build à la racine du dépôt** (`COPY backend/...`) : connecter le dépôt entier et pointer le chemin du Dockerfile vers **`backend/Dockerfile`**.

La base PostgreSQL peut être ajoutée dans le même projet Railway que le backend.
