"""
Configuration centralisée de l'application Agent Juliette.
Utilise pydantic-settings pour la validation et le chargement des variables d'environnement.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application chargée depuis les variables d'environnement."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"

    # Qdrant
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_name: str = "nana_intelligence_knowledge"

    # Gmail OAuth2
    gmail_credentials_path: str = "./credentials.json"
    gmail_token_path: str = "./token.json"
    gmail_sender_email: str

    # Perplexity (recherche entreprise)
    perplexity_api_key: str | None = None
    perplexity_model: str = "sonar"  # sonar (rapide) ou sonar-pro (approfondi)

    # Application
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Retourne une instance singleton des settings.
    Utilise lru_cache pour éviter de recharger les variables à chaque appel.
    """
    return Settings()
