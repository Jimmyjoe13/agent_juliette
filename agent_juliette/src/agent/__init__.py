"""
Module Agent - Logique métier de Juliette.
"""

from src.agent.prompts import get_system_prompt, build_user_prompt, PROMPTS_BY_SERVICE
from src.agent.devis_generator import DevisGenerator, get_devis_generator
from src.agent.pdf_service import PDFService, get_pdf_service
from src.agent.orchestrator import AgentOrchestrator, get_orchestrator, ProcessingResult

__all__ = [
    "get_system_prompt",
    "build_user_prompt",
    "PROMPTS_BY_SERVICE",
    "DevisGenerator",
    "get_devis_generator",
    "PDFService",
    "get_pdf_service",
    "AgentOrchestrator",
    "get_orchestrator",
    "ProcessingResult",
]
