"""
Agent Juliette - API FastAPI
Point d'entrée principal de l'application.
"""

import logging
import time
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

# Cache d'idempotence pour éviter les doublons
# Structure: {response_id: (timestamp, result)}
# Les entrées expirent après 1 heure
PROCESSED_LEADS_CACHE: dict[str, tuple[float, dict]] = {}
CACHE_EXPIRY_SECONDS = 3600  # 1 heure


def cleanup_expired_cache():
    """Nettoie les entrées expirées du cache."""
    current_time = time.time()
    expired_keys = [
        key for key, (timestamp, _) in PROCESSED_LEADS_CACHE.items()
        if current_time - timestamp > CACHE_EXPIRY_SECONDS
    ]
    for key in expired_keys:
        del PROCESSED_LEADS_CACHE[key]


def is_lead_already_processed(response_id: str) -> dict | None:
    """
    Vérifie si un lead a déjà été traité.
    
    Returns:
        Le résultat précédent si déjà traité, None sinon
    """
    cleanup_expired_cache()
    
    if response_id in PROCESSED_LEADS_CACHE:
        timestamp, result = PROCESSED_LEADS_CACHE[response_id]
        logger.warning(f"⚠️ Lead {response_id} déjà traité (cache hit)")
        return result
    
    return None


def mark_lead_as_processed(response_id: str, result: dict):
    """Marque un lead comme traité dans le cache."""
    PROCESSED_LEADS_CACHE[response_id] = (time.time(), result)
    logger.info(f"📝 Lead {response_id} ajouté au cache d'idempotence")


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


@app.get("/")
@app.head("/")
async def root() -> dict[str, str]:
    """
    Endpoint racine - redirige vers le health check.
    Supporte GET et HEAD pour les services de monitoring (UptimeRobot, etc.)
    """
    return {"status": "healthy", "agent": "juliette", "docs": "/docs"}


@app.get("/health")
@app.head("/health")
async def health_check() -> dict[str, str]:
    """
    Endpoint de vérification de l'état de l'API.
    Supporte GET et HEAD pour les services de monitoring (UptimeRobot, etc.)
    """
    return {"status": "healthy", "agent": "juliette"}


@app.get("/cache/status")
async def cache_status() -> dict:
    """
    Retourne le statut du cache d'idempotence.
    Utile pour le debug.
    """
    cleanup_expired_cache()
    return {
        "cached_leads_count": len(PROCESSED_LEADS_CACHE),
        "cached_leads": list(PROCESSED_LEADS_CACHE.keys()),
        "cache_expiry_seconds": CACHE_EXPIRY_SECONDS,
    }


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


@app.get("/rag/search")
async def rag_search(query: str, limit: int = 3) -> dict:
    """
    Teste la recherche RAG avec une requête.
    
    Args:
        query: La requête de recherche
        limit: Nombre de résultats (défaut: 3)
    """
    try:
        from src.integrations.qdrant_service import get_qdrant_service
        qdrant = get_qdrant_service()
        results = qdrant.search(query, limit=limit, score_threshold=0.5)
        
        return {
            "query": query,
            "results_count": len(results),
            "results": [
                {
                    "score": r.score,
                    "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                    "metadata": r.metadata,
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Erreur recherche RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur recherche: {str(e)}")


@app.post("/agent/test-devis")
async def test_devis_generation(request: Request) -> dict:
    """
    Endpoint de test pour la génération de devis.
    Accepte un LeadRequest et retourne le devis généré.
    """
    try:
        from src.models import LeadRequest
        from src.agent.devis_generator import get_devis_generator
        
        data = await request.json()
        lead = LeadRequest(**data)
        
        generator = get_devis_generator()
        devis = generator.generate(lead)
        
        return {
            "success": True,
            "devis": {
                "reference": devis.reference,
                "title": devis.title,
                "client_name": devis.client_name,
                "introduction": devis.introduction,
                "items": [
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "total": item.total,
                    }
                    for item in devis.items
                ],
                "subtotal": devis.subtotal,
                "tva": devis.tva,
                "total_ttc": devis.total_ttc,
                "conditions": devis.conditions,
                "valid_until": devis.valid_until.isoformat(),
            }
        }
    except Exception as e:
        logger.exception(f"Erreur génération devis: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/agent/test-pdf")
async def test_pdf_generation(request: Request) -> dict:
    """
    Endpoint de test pour la génération complète (devis + PDF).
    Accepte un LeadRequest et retourne le chemin du PDF généré.
    """
    try:
        from src.models import LeadRequest
        from src.agent.devis_generator import get_devis_generator
        from src.agent.pdf_service import get_pdf_service
        
        data = await request.json()
        lead = LeadRequest(**data)
        
        # Génération du devis
        generator = get_devis_generator()
        devis = generator.generate(lead)
        
        # Génération du PDF
        pdf_service = get_pdf_service()
        pdf_path = pdf_service.generate(devis)
        
        return {
            "success": True,
            "devis_reference": devis.reference,
            "pdf_path": pdf_path,
            "total_ttc": devis.total_ttc,
        }
    except Exception as e:
        logger.exception(f"Erreur génération PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


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
        
        # ===== IDEMPOTENCE CHECK =====
        # Vérifier si ce lead a déjà été traité (évite les doublons)
        cached_result = is_lead_already_processed(lead.tally_response_id)
        if cached_result:
            logger.warning(f"🔄 Lead {lead.tally_response_id} déjà traité, retour du cache")
            return WebhookResponse(**cached_result)
        # =============================
        
        logger.info(f"✅ Lead reçu: {lead.full_name} ({lead.email})")
        logger.info(f"   Service: {lead.service_type.value}")
        logger.info(f"   Besoin: {lead.project_description[:100]}...")
        
        # Traitement complet par l'orchestrateur
        from src.agent.orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        result = orchestrator.process_lead(lead)
        
        if result.success:
            response_data = {
                "success": True,
                "message": f"Devis {result.devis_reference} créé avec succès",
                "lead_reference": lead.tally_response_id,
                "data": {
                    "devis_reference": result.devis_reference,
                    "pdf_path": result.pdf_path,
                    "draft_id": result.draft_id,
                    "total_ttc": result.total_ttc,
                    "processing_time_ms": result.processing_time_ms,
                }
            }
            # Marquer comme traité dans le cache
            mark_lead_as_processed(lead.tally_response_id, response_data)
            return WebhookResponse(**response_data)
        else:
            logger.error(f"Échec traitement lead: {result.error}")
            return WebhookResponse(
                success=False,
                message=f"Erreur lors du traitement: {result.error}",
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
