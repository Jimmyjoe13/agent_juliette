"""
Agent Juliette - Module principal.
"""

from src.config import get_settings, Settings
from src.models import LeadRequest, DevisContent, EmailDraft, ServiceType

__all__ = [
    "get_settings",
    "Settings",
    "LeadRequest",
    "DevisContent",
    "EmailDraft",
    "ServiceType",
]
