"""
Orchestrateur principal de l'Agent Juliette.
Coordonne le flux complet: Lead → Devis → PDF → Email.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from src.models import LeadRequest, DevisContent
from src.agent.devis_generator import get_devis_generator
from src.agent.pdf_service import get_pdf_service
from src.agent.email_generator import get_email_generator
from src.integrations.gmail_service import get_gmail_service

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Résultat du traitement complet d'un lead."""
    success: bool
    lead_reference: str
    devis_reference: str | None = None
    pdf_path: str | None = None
    draft_id: str | None = None
    error: str | None = None
    total_ttc: float | None = None
    processing_time_ms: int = 0
    email_subject: str | None = None  # Nouveau: sujet de l'email généré


class AgentOrchestrator:
    """
    Orchestrateur principal de l'Agent Juliette.
    
    Coordonne le flux complet de traitement d'un lead:
    1. Génération du devis (Perplexity + RAG + LLM)
    2. Création du PDF
    3. Génération de l'email personnalisé (LLM)
    4. Création du brouillon Gmail
    """
    
    def __init__(self):
        self.devis_generator = get_devis_generator()
        self.pdf_service = get_pdf_service()
        self.email_generator = get_email_generator()
        self.gmail_service = get_gmail_service()
        logger.info("AgentOrchestrator initialisé (avec email IA)")
    
    def process_lead(self, lead: LeadRequest) -> ProcessingResult:
        """
        Traite un lead de bout en bout.
        
        Args:
            lead: Les informations du lead
            
        Returns:
            ProcessingResult avec tous les détails du traitement
        """
        start_time = datetime.now()
        
        logger.info(f"🚀 Début traitement lead: {lead.full_name} ({lead.tally_response_id})")
        
        try:
            # Étape 1: Génération du devis (avec contexte entreprise pour l'email)
            logger.info("📝 Étape 1/4: Génération du devis...")
            devis, company_context = self.devis_generator.generate_with_context(lead)
            logger.info(f"   → Devis {devis.reference} généré ({devis.total_ttc:.2f}€ TTC)")
            
            # Étape 2: Génération du PDF
            logger.info("📄 Étape 2/4: Génération du PDF...")
            pdf_path = self.pdf_service.generate(devis)
            logger.info(f"   → PDF créé: {pdf_path}")
            
            # Étape 3: Génération de l'email personnalisé par IA
            logger.info("✉️ Étape 3/4: Génération de l'email IA...")
            email = self.email_generator.generate(
                lead=lead,
                devis=devis,
                company_context=company_context if company_context else None,
            )
            logger.info(f"   → Email généré - Sujet: {email.subject[:50]}...")
            
            # Étape 4: Création du brouillon Gmail
            draft_id = None
            logger.info(f"📧 Étape 4/4: Vérification configuration Gmail...")
            if self.gmail_service.is_configured():
                logger.info("📧 Création du brouillon Gmail...")
                try:
                    draft_result = self.gmail_service.create_draft(
                        to=lead.email,
                        subject=email.subject,
                        body_html=email.body_html,
                        attachment_path=pdf_path,
                    )
                    draft_id = draft_result['draft_id']
                    logger.info(f"   → Brouillon {draft_id} créé avec succès")
                except Exception as e:
                    logger.error(f"   ❌ Erreur CRITIQUE création brouillon: {e}", exc_info=True)
            else:
                logger.warning("📧 Gmail non configuré (credentials.json ou token.json manquant/invalide)")
            
            # Calcul du temps de traitement
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            logger.info(f"✅ Lead traité avec succès en {processing_time}ms")
            
            return ProcessingResult(
                success=True,
                lead_reference=lead.tally_response_id,
                devis_reference=devis.reference,
                pdf_path=pdf_path,
                draft_id=draft_id,
                total_ttc=devis.total_ttc,
                processing_time_ms=processing_time,
                email_subject=email.subject,
            )
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.exception(f"❌ Erreur traitement lead: {e}")
            
            return ProcessingResult(
                success=False,
                lead_reference=lead.tally_response_id,
                error=str(e),
                processing_time_ms=processing_time,
            )


def get_orchestrator() -> AgentOrchestrator:
    """Factory pour obtenir une instance de l'orchestrateur."""
    return AgentOrchestrator()
