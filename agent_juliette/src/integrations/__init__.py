"""
Module d'intégrations avec les services externes.
- Tally (webhook)
- Qdrant (RAG)
- OpenAI (LLM)
- Gmail (email)
"""

from src.integrations.tally import TallyWebhookPayload, TallyFormData
from src.integrations.tally_service import parse_tally_to_lead
from src.integrations.openai_service import OpenAIService, get_openai_service
from src.integrations.qdrant_service import QdrantService, get_qdrant_service, SearchResult
from src.integrations.gmail_service import GmailService, get_gmail_service

__all__ = [
    # Tally
    "TallyWebhookPayload",
    "TallyFormData",
    "parse_tally_to_lead",
    # OpenAI
    "OpenAIService",
    "get_openai_service",
    # Qdrant
    "QdrantService",
    "get_qdrant_service",
    "SearchResult",
    # Gmail
    "GmailService",
    "get_gmail_service",
]
