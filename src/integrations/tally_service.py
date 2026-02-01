"""
Service de transformation des données Tally vers les modèles internes.
"""

import logging
from src.integrations.tally import TallyFormData, TallyWebhookPayload
from src.models import LeadRequest, ServiceType

logger = logging.getLogger(__name__)

# Mapping des textes Tally vers les ServiceType
SERVICE_TYPE_MAPPING = {
    "mass mailing & lead gen": ServiceType.MASS_MAILING,
    "automatisation & ia": ServiceType.AUTOMATION_IA,
    "seo & growth hacking": ServiceType.SEO_GROWTH,
}


def parse_tally_to_lead(payload: TallyWebhookPayload) -> LeadRequest:
    """
    Transforme un payload webhook Tally en LeadRequest.
    
    Args:
        payload: Le payload complet reçu de Tally
        
    Returns:
        LeadRequest: Les données du lead normalisées
        
    Raises:
        ValueError: Si des champs requis sont manquants
    """
    form_data: TallyFormData = payload.data
    
    # Extraction des champs
    first_name = form_data.get_field_value("Prénom")
    last_name = form_data.get_field_value("Nom")
    email = form_data.get_field_value("Email Pro")
    company = form_data.get_field_value("Entreprise")
    website = form_data.get_field_value("Site Web")
    service_type_text = form_data.get_field_value("Type de service")
    project_description = form_data.get_field_value("Votre Besoin")
    budget_range = form_data.get_field_value("Budget estimé")
    consent_text = form_data.get_field_value("Consentement")
    
    # Validation des champs requis
    if not first_name:
        raise ValueError("Le champ 'Prénom' est requis")
    if not last_name:
        raise ValueError("Le champ 'Nom' est requis")
    if not email:
        raise ValueError("Le champ 'Email Pro' est requis")
    if not service_type_text:
        raise ValueError("Le champ 'Type de service' est requis")
    if not project_description:
        raise ValueError("Le champ 'Votre Besoin' est requis")
    
    # Mapping du type de service
    service_type = SERVICE_TYPE_MAPPING.get(
        service_type_text.lower().strip(),
        ServiceType.MASS_MAILING  # Fallback
    )
    
    # Vérification du consentement
    consent = bool(consent_text)
    
    logger.info(
        f"Lead parsé: {first_name} {last_name} ({email}) - "
        f"Service: {service_type.value} - Consent: {consent}"
    )
    
    return LeadRequest(
        first_name=first_name,
        last_name=last_name,
        email=email,
        company=company,
        website=website,
        service_type=service_type,
        project_description=project_description,
        budget_range=budget_range,
        tally_response_id=form_data.responseId,
        received_at=form_data.createdAt,
        consent=consent,
    )
