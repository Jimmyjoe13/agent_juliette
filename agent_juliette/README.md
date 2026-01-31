# Agent Juliette 🤖

Agent IA Python pour la création et l'envoi automatique de devis pour [nana-intelligence.fr](https://nana-intelligence.fr).

## Fonctionnalités

- 📥 **Réception automatique** des leads via webhook Tally
- 🧠 **Analyse intelligente** des besoins avec RAG (Qdrant + OpenAI)
- 📄 **Génération de devis PDF** professionnels
- 📧 **Création de brouillon Gmail** avec le devis en pièce jointe

## Spécialités couvertes

- Mass Mailing & Lead Gen
- Automatisation & IA
- SEO & Growth Hacking

## Installation

```bash
# Cloner et accéder au projet
cd agent_juliette

# Installer les dépendances avec uv
uv sync

# Copier et configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API
```

## Configuration requise

1. **OpenAI API Key** - [Obtenir une clé](https://platform.openai.com/api-keys)
2. **Qdrant Cloud** - [Créer un cluster](https://cloud.qdrant.io/)
3. **Gmail OAuth2** - [Configurer dans Google Cloud Console](https://console.cloud.google.com/)

## Lancement

```bash
# Démarrer le serveur
uv run uvicorn main:app --reload

# Le webhook sera accessible sur http://localhost:8000/webhook/tally
```

## Structure du projet

```
src/
├── agent/           # Logique de l'agent IA
├── integrations/    # Services externes (Tally, Qdrant, OpenAI, Gmail)
├── utils/           # Utilitaires
├── config.py        # Configuration centralisée
└── models.py        # Schémas de données Pydantic
```

## Tests

```bash
uv run pytest tests/ -v
```
