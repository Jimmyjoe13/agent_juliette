"""
Agent Juliette - API FastAPI
Point d'entrée principal de l'application.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.models import WebhookResponse
from src.integrations.tally import TallyWebhookPayload
from src.integrations.tally_service import parse_tally_to_lead

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    logger.info("🚀 Agent Juliette démarré")
    settings = get_settings()
    logger.info(f"   Environnement: {settings.app_env}")
    yield
    logger.info("👋 Agent Juliette arrêté")


app = FastAPI(
    title="Agent Juliette",
    description="Agent IA pour la création et l'envoi automatique de devis - nana-intelligence.fr",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Endpoint de vérification de l'état de l'API."""
    return {"status": "healthy", "agent": "juliette"}


@app.get("/rag/info")
async def rag_info() -> dict:
    """
    Retourne les informations sur la base vectorielle Qdrant.
    Utile pour vérifier la connexion et le nombre de documents.
    """
    try:
        from src.integrations.qdrant_service import get_qdrant_service
        qdrant = get_qdrant_service()
        return qdrant.get_collection_info()
    except Exception as e:
        logger.error(f"Erreur connexion Qdrant: {e}")
        raise HTTPException(status_code=503, detail=f"Qdrant indisponible: {str(e)}")


@app.post("/webhook/tally", response_model=WebhookResponse)
async def webhook_tally(request: Request) -> WebhookResponse:
    """
    Endpoint webhook pour recevoir les soumissions du formulaire Tally.
    
    Tally envoie les données soit comme un objet unique, soit comme un array.
    Cet endpoint gère les deux cas.
    """
    try:
        # Récupération du body brut
        raw_body: Any = await request.json()
        
        # Tally peut envoyer un array ou un objet unique
        if isinstance(raw_body, list):
            if len(raw_body) == 0:
                raise HTTPException(status_code=400, detail="Payload Tally vide")
            # On prend le premier élément si c'est un array
            payload_data = raw_body[0].get("body", raw_body[0])
        else:
            payload_data = raw_body.get("body", raw_body)
        
        # Parsing du payload Tally
        tally_payload = TallyWebhookPayload(**payload_data)
        
        # Vérification du type d'événement
        if tally_payload.eventType != "FORM_RESPONSE":
            logger.warning(f"Type d'événement ignoré: {tally_payload.eventType}")
            return WebhookResponse(
                success=True,
                message=f"Événement ignoré: {tally_payload.eventType}"
            )
        
        # Transformation en LeadRequest
        lead = parse_tally_to_lead(tally_payload)
        
        logger.info(f"✅ Lead reçu: {lead.full_name} ({lead.email})")
        logger.info(f"   Service: {lead.service_type.value}")
        logger.info(f"   Besoin: {lead.project_description[:100]}...")
        
        # TODO: Phase suivante - Traitement par l'agent IA
        # - Recherche RAG dans Qdrant
        # - Génération du devis via OpenAI
        # - Création du PDF
        # - Création du brouillon Gmail
        
        return WebhookResponse(
            success=True,
            message="Lead reçu et en cours de traitement",
            lead_reference=lead.tally_response_id,
        )
        
    except ValueError as e:
        logger.error(f"Erreur de validation: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur inattendue lors du traitement du webhook: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Gestionnaire global des exceptions."""
    logger.exception(f"Erreur non gérée: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Une erreur interne s'est produite"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
