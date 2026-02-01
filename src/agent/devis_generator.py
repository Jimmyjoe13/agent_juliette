"""
Générateur de devis intelligent.
Utilise le RAG et OpenAI pour créer des devis personnalisés.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta

from src.models import LeadRequest, DevisContent, DevisItem
from src.agent.prompts import get_system_prompt, build_user_prompt
from src.integrations.openai_service import get_openai_service
from src.integrations.qdrant_service import get_qdrant_service

logger = logging.getLogger(__name__)


class DevisGenerator:
    """
    Générateur de devis utilisant RAG + LLM.
    
    Workflow:
    1. Recherche de contexte pertinent dans Qdrant
    2. Construction du prompt avec le contexte
    3. Génération du devis via OpenAI
    4. Parsing et validation du résultat
    """
    
    def __init__(self):
        self.openai = get_openai_service()
        self.qdrant = get_qdrant_service()
        logger.info("DevisGenerator initialisé")
    
    def generate(self, lead: LeadRequest) -> DevisContent:
        """
        Génère un devis complet pour un lead.
        
        Args:
            lead: Les informations du lead
            
        Returns:
            DevisContent: Le devis structuré
        """
        logger.info(f"Génération du devis pour {lead.full_name} ({lead.service_type.value})")
        
        # 1. Recherche RAG du contexte pertinent
        context = self._get_rag_context(lead)
        logger.debug(f"Contexte RAG: {len(context)} caractères")
        
        # 2. Construction des prompts
        system_prompt = get_system_prompt(lead.service_type)
        user_prompt = build_user_prompt(
            lead_name=lead.full_name,
            company=lead.company,
            website=lead.website,
            project_description=lead.project_description,
            budget_range=lead.budget_range,
            service_type=lead.service_type,
        )
        
        # 3. Génération via LLM
        logger.info("Appel OpenAI pour génération du devis...")
        response = self.openai.generate_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            context=context,
            max_tokens=2500,
            temperature=0.7,
        )
        
        # 4. Parsing du JSON
        devis_data = self._parse_response(response)
        
        # 5. Création du DevisContent
        devis = self._build_devis_content(lead, devis_data)
        
        logger.info(f"✅ Devis généré: {devis.reference} - Total: {devis.total_ttc:.2f}€ TTC")
        
        return devis
    
    def _get_rag_context(self, lead: LeadRequest) -> str:
        """Récupère le contexte pertinent depuis Qdrant."""
        # Construction de la requête de recherche
        query_parts = [
            lead.service_type.value.replace("_", " "),
            lead.project_description,
        ]
        if lead.budget_range:
            query_parts.append(f"budget {lead.budget_range}")
        
        query = " ".join(query_parts)
        
        # Recherche dans Qdrant
        context = self.qdrant.search_with_context(
            query=query,
            limit=5,
            score_threshold=0.4,  # Seuil bas pour avoir plus de contexte
        )
        
        return context
    
    def _parse_response(self, response: str) -> dict:
        """Parse la réponse JSON du LLM."""
        try:
            # Nettoyage de la réponse (parfois le LLM ajoute des backticks)
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON: {e}")
            logger.error(f"Réponse brute: {response[:500]}...")
            
            # Fallback avec un devis minimal
            return {
                "titre": "Devis personnalisé",
                "introduction": "Suite à votre demande, voici notre proposition.",
                "lignes_devis": [
                    {
                        "description": "Prestation sur mesure",
                        "details": "À définir ensemble",
                        "quantite": 1,
                        "prix_unitaire": 1000.00
                    }
                ],
                "conditions": "Devis valable 30 jours. Paiement 50% à la commande, 50% à la livraison.",
                "message_personnel": "N'hésitez pas à me contacter pour en discuter."
            }
    
    def _build_devis_content(self, lead: LeadRequest, data: dict) -> DevisContent:
        """Construit l'objet DevisContent à partir des données générées."""
        # Génération de la référence unique
        date_str = datetime.now().strftime("%Y%m%d")
        short_id = str(uuid.uuid4())[:8].upper()
        reference = f"DEV-{date_str}-{short_id}"
        
        # Conversion des lignes de devis
        items = []
        for ligne in data.get("lignes_devis", []):
            items.append(DevisItem(
                description=ligne.get("description", "Service"),
                quantity=ligne.get("quantite", 1),
                unit_price=float(ligne.get("prix_unitaire", 0)),
            ))
        
        # Construction de l'introduction avec le message personnel
        intro_parts = [data.get("introduction", "")]
        if data.get("message_personnel"):
            intro_parts.append(data["message_personnel"])
        
        return DevisContent(
            reference=reference,
            created_at=datetime.now(),
            valid_until=datetime.now() + timedelta(days=30),
            client_name=lead.full_name,
            client_email=lead.email,
            client_company=lead.company,
            title=data.get("titre", f"Devis {lead.service_type.value}"),
            introduction="\n\n".join(intro_parts),
            items=items,
            conditions=data.get("conditions", "Devis valable 30 jours."),
        )


def get_devis_generator() -> DevisGenerator:
    """Factory pour obtenir une instance du générateur."""
    return DevisGenerator()
