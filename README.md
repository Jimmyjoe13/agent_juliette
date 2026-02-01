# Agent Juliette 🤖

**Agent IA pour la création et l'envoi automatique de devis** - nana-intelligence.fr

## 🎯 Fonctionnalités

- **📥 Réception des leads** via webhook Tally
- **🔍 Recherche RAG** dans une base de connaissances Qdrant
- **🤖 Génération IA** de devis personnalisés via OpenAI (GPT-5/GPT-4o)
- **📄 Création de PDF** professionnels avec ReportLab
- **📧 Brouillons Gmail** avec pièce jointe PDF

## 🏗️ Architecture

```
agent_juliette/
├── main.py                    # API FastAPI (webhooks, endpoints)
├── src/
│   ├── config.py              # Configuration (Pydantic Settings)
│   ├── models.py              # Modèles de données
│   ├── agent/
│   │   ├── prompts.py         # Prompts par spécialité
│   │   ├── devis_generator.py # Génération de devis (RAG + LLM)
│   │   ├── pdf_service.py     # Génération de PDF
│   │   └── orchestrator.py    # Orchestration du flux complet
│   └── integrations/
│       ├── tally.py           # Modèles webhook Tally
│       ├── tally_service.py   # Parsing Tally → LeadRequest
│       ├── openai_service.py  # Embeddings & completions
│       ├── qdrant_service.py  # Recherche vectorielle
│       └── gmail_service.py   # API Gmail OAuth2
├── scripts/                   # Scripts utilitaires
├── tests/                     # Tests unitaires
├── generated_pdfs/            # PDFs générés (ignoré par git)
└── .env                       # Configuration locale (ignoré par git)
```

---

## 🚀 Déploiement sur Render

### Prérequis

1. Un compte [Render](https://render.com)
2. Les clés API configurées :
   - OpenAI API Key
   - Qdrant Cloud URL + API Key
   - Gmail OAuth2 (optionnel en production)

### Étape 1 : Créer un Web Service sur Render

1. Va sur [Render Dashboard](https://dashboard.render.com/)
2. Clique sur **New +** → **Web Service**
3. Connecte ton dépôt GitHub : `Jimmyjoe13/agent_juliette`
4. Configure le service :

| Paramètre          | Valeur                                                |
| ------------------ | ----------------------------------------------------- |
| **Name**           | `agent-juliette`                                      |
| **Region**         | `Frankfurt (EU Central)`                              |
| **Branch**         | `main`                                                |
| **Root Directory** | `agent_juliette`                                      |
| **Runtime**        | `Python 3`                                            |
| **Build Command**  | `pip install uv && uv sync`                           |
| **Start Command**  | `uv run uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type**  | `Starter` (ou supérieur)                              |

### Étape 2 : Configurer les Variables d'Environnement

Dans l'onglet **Environment** de Render, ajoute les variables :

```env
# OpenAI (obligatoire)
OPENAI_API_KEY=sk-proj-xxx
OPENAI_MODEL=gpt-5-nano

# Qdrant Cloud (obligatoire)
QDRANT_URL=https://xxx.cloud.qdrant.io
QDRANT_API_KEY=xxx
QDRANT_COLLECTION_NAME=nana_intelligence_knowledge

# Gmail (optionnel - voir section Gmail en production)
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./token.json
GMAIL_SENDER_EMAIL=contact@nana-intelligence.fr

# Application
APP_ENV=production
LOG_LEVEL=INFO
```

### Étape 3 : Déployer

Clique sur **Create Web Service**. Render va :

1. Cloner le dépôt
2. Installer les dépendances
3. Lancer le serveur

Tu obtiendras une URL comme : `https://agent-juliette.onrender.com`

### Étape 4 : Configurer Tally

Dans ton formulaire Tally :

1. Va dans **Integrations** → **Webhooks**
2. Ajoute l'URL : `https://agent-juliette.onrender.com/webhook/tally`
3. Méthode : `POST`

---

## 📧 Gmail en Production

### Option A : Token pré-généré (recommandé pour démarrer)

1. Génère le token en local : `uv run python scripts/init_gmail_auth.py`
2. Encode le contenu de `token.json` en base64
3. Ajoute une variable d'env `GMAIL_TOKEN_BASE64` sur Render
4. Modifie le code pour décoder et créer le fichier au démarrage

### Option B : Compte de service Google Workspace

Si tu as Google Workspace, utilise un compte de service avec délégation de domaine.

### Option C : Désactiver Gmail

Le service fonctionne sans Gmail - les PDFs sont générés mais pas envoyés par email.
Tu peux les récupérer via l'API ou les stocker sur un service cloud (S3, etc.).

---

## 🔧 Installation Locale

### Prérequis

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestionnaire de packages)

### Installation

```bash
# Cloner le projet
git clone https://github.com/Jimmyjoe13/agent_juliette.git
cd agent_juliette/agent_juliette

# Installer les dépendances
uv sync

# Copier la configuration
cp .env.example .env
# Éditer .env avec vos clés API
```

### Lancer en développement

```bash
uv run uvicorn main:app --reload
```

---

## ⚙️ Configuration

### Variables d'environnement

| Variable                 | Description                            | Obligatoire |
| ------------------------ | -------------------------------------- | ----------- |
| `OPENAI_API_KEY`         | Clé API OpenAI                         | ✅          |
| `OPENAI_MODEL`           | Modèle à utiliser (gpt-5-nano, gpt-4o) | ✅          |
| `QDRANT_URL`             | URL du cluster Qdrant Cloud            | ✅          |
| `QDRANT_API_KEY`         | Clé API Qdrant                         | ✅          |
| `QDRANT_COLLECTION_NAME` | Nom de la collection                   | ✅          |
| `GMAIL_CREDENTIALS_PATH` | Chemin vers credentials.json           | ❌          |
| `GMAIL_TOKEN_PATH`       | Chemin vers token.json                 | ❌          |
| `GMAIL_SENDER_EMAIL`     | Email expéditeur                       | ❌          |
| `APP_ENV`                | Environnement (development/production) | ❌          |
| `LOG_LEVEL`              | Niveau de log (DEBUG/INFO/WARNING)     | ❌          |

---

## 🔌 Endpoints API

### Health Check

```http
GET /health

# Réponse
{"status": "healthy", "agent": "juliette"}
```

### Webhook Tally

```http
POST /webhook/tally
Content-Type: application/json

# Reçoit les soumissions du formulaire Tally
# Déclenche automatiquement le flux complet
```

### Informations RAG

```http
GET /rag/info

# Retourne les infos sur la collection Qdrant
```

### Recherche RAG

```http
GET /rag/search?query=automatisation&limit=3

# Teste la recherche dans la base de connaissances
```

### Test génération devis

```http
POST /agent/test-devis
Content-Type: application/json

{
    "first_name": "Jean",
    "last_name": "Dupont",
    "email": "jean@example.com",
    "company": "Ma Société",
    "service_type": "automation_ia",
    "project_description": "Automatiser mes processus...",
    "budget_range": "1-3k€"
}
```

### Test génération PDF

```http
POST /agent/test-pdf
Content-Type: application/json

# Pareil que /agent/test-devis mais génère aussi le PDF
```

---

## 📨 Configuration Tally

Dans Tally, configurez un webhook vers :

```
https://agent-juliette.onrender.com/webhook/tally
```

### Champs du formulaire attendus :

| Label du champ    | Type       | Obligatoire |
| ----------------- | ---------- | ----------- |
| `Prénom`          | Texte      | ✅          |
| `Nom`             | Texte      | ✅          |
| `Email Pro`       | Email      | ✅          |
| `Entreprise`      | Texte      | ❌          |
| `Site Web`        | URL        | ❌          |
| `Type de service` | Sélection  | ✅          |
| `Votre Besoin`    | Texte long | ✅          |
| `Budget estimé`   | Sélection  | ❌          |
| `Consentement`    | Checkbox   | ❌          |

### Options pour "Type de service" :

- Mass Mailing & Lead Gen
- Automatisation & IA
- SEO & Growth Hacking

---

## 🧪 Tests

```bash
# Lancer tous les tests
uv run pytest

# Avec couverture
uv run pytest --cov=src

# Test spécifique
uv run pytest tests/test_tally.py -v
```

---

## 📊 Types de services

| Service         | Description                                    |
| --------------- | ---------------------------------------------- |
| `mass_mailing`  | Campagnes email, cold emailing, scraping leads |
| `automation_ia` | Workflows n8n/Make, agents IA, chatbots        |
| `seo_growth`    | Audit SEO, contenu optimisé, backlinks         |

---

## 🔄 Flux de traitement

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Tally    │───▶│  Webhook    │───▶│     RAG     │
│  Formulaire │    │  /webhook/  │    │   Qdrant    │
└─────────────┘    │   tally     │    └──────┬──────┘
                   └─────────────┘           │
                                             ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Gmail    │◀───│     PDF     │◀───│   OpenAI    │
│  Brouillon  │    │  ReportLab  │    │  GPT-5/4o   │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 📝 Exemple de réponse webhook

```json
{
  "success": true,
  "message": "Devis DEV-20260201-ABC12345 créé avec succès",
  "lead_reference": "tally_id_xxx",
  "data": {
    "devis_reference": "DEV-20260201-ABC12345",
    "pdf_path": "/path/to/DEV-20260201-ABC12345.pdf",
    "draft_id": "gmail_draft_xxx",
    "total_ttc": 3600.0,
    "processing_time_ms": 15234
  }
}
```

---

## 🛠️ Développement

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

### Structure des commits

- `feat:` Nouvelle fonctionnalité
- `fix:` Correction de bug
- `docs:` Documentation
- `refactor:` Refactoring

---

## 🐛 Troubleshooting

### Erreur "Collection not found" sur Qdrant

Vérifie que la collection existe et que le nom correspond à `QDRANT_COLLECTION_NAME`.

### Erreur OpenAI "max_tokens not supported"

Les nouveaux modèles (gpt-5, o1, o3) utilisent `max_completion_tokens`. Le code gère automatiquement ce cas.

### Gmail "Invalid credentials"

Supprime `token.json` et réauthentifie avec `uv run python scripts/init_gmail_auth.py`.

### Webhook Tally ne fonctionne pas

1. Vérifie l'URL du webhook dans Tally
2. Vérifie les labels des champs (doivent correspondre exactement)
3. Consulte les logs sur Render

---

## 📄 Licence

Propriétaire - nana-intelligence.fr

---

**Développé avec ❤️ par nana-intelligence**
