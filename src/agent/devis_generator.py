"""
Générateur de devis intelligent.
Utilise le RAG et OpenAI pour créer des devis personnalisés.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta

from pydantic import ValidationError

from src.models import LeadRequest, DevisContent, DevisItem
from src.agent.prompts import get_system_prompt, build_user_prompt
from src.agent.devis_schemas import LLMDevisPayload, extract_json_from_text
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
        
        # 3. Génération via LLM avec mode JSON pour forcer une sortie structurée
        logger.info("Appel OpenAI pour génération du devis (mode JSON activé)...")
        response = self.openai.generate_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            context=context,
            max_tokens=2500,
            temperature=0.5,  # Réduit pour plus de cohérence structurelle
            json_mode=True,   # Force le LLM à retourner du JSON valide
        )
        
        # 4. Parsing du JSON avec validation
        devis_data = self._parse_response(response, lead)
        
        # Log du contexte RAG utilisé pour debugging
        if context:
            logger.info(f"📚 Contexte RAG utilisé: {len(context)} caractères")
        else:
            logger.warning("⚠️ Aucun contexte RAG trouvé - devis basé uniquement sur le prompt")
        
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
    
    def _parse_response(self, response: str, lead: LeadRequest) -> dict:
        """
        Parse et valide la réponse JSON du LLM.
        
        Stratégie en 3 étapes:
        1. Tentative directe de parsing JSON
        2. Extraction du premier objet JSON si texte autour
        3. Fallback contextualisé basé sur le lead (pas un template fixe)
        
        Args:
            response: Réponse brute du LLM
            lead: Informations du lead pour le fallback contextualisé
            
        Returns:
            dict: Données du devis validées
        """
        # Nettoyage initial des backticks markdown
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        # === ÉTAPE 1: Tentative directe ===
        try:
            data = json.loads(cleaned)
            validated = LLMDevisPayload.model_validate(data)
            logger.info("✅ JSON parsé et validé avec succès (stratégie: directe)")
            return validated.model_dump()
        except json.JSONDecodeError:
            logger.debug("Parsing direct échoué, tentative d'extraction...")
        except ValidationError as e:
            logger.warning(f"JSON valide mais structure incorrecte: {e.error_count()} erreurs")
            # On continue pour tenter une extraction plus fine
        
        # === ÉTAPE 2: Extraction du JSON depuis le texte ===
        extracted = extract_json_from_text(response)
        if extracted:
            try:
                data = json.loads(extracted)
                validated = LLMDevisPayload.model_validate(data)
                logger.info("✅ JSON extrait et validé avec succès (stratégie: extraction)")
                return validated.model_dump()
            except json.JSONDecodeError as e:
                logger.warning(f"JSON extrait invalide: {e}")
            except ValidationError as e:
                logger.warning(f"JSON extrait mais validation échouée: {e.error_count()} erreurs")
                for error in e.errors()[:3]:  # Log les 3 premières erreurs
                    logger.warning(f"  - {error['loc']}: {error['msg']}")
        
        # === ÉTAPE 3: Fallback contextualisé ===
        logger.error(f"❌ Impossible de parser la réponse LLM, utilisation du fallback contextualisé")
        logger.error(f"Réponse brute (500 premiers chars): {response[:500]}")
        
        # Fallback basé sur le lead (pas un template fixe!)
        service_name = lead.service_type.value.replace("_", " ").title()
        return {
            "titre": f"Devis {service_name} - {lead.company or lead.full_name}",
            "introduction": f"Cher(e) {lead.first_name}, suite à votre demande concernant {lead.project_description[:100]}..., voici notre proposition personnalisée.",
            "lignes_devis": [
                {
                    "description": f"Prestation {service_name}",
                    "details": f"Selon votre besoin: {lead.project_description[:150]}",
                    "quantite": 1,
                    "prix_unitaire": self._estimate_price_from_budget(lead.budget_range)
                }
            ],
            "conditions": "Devis valable 30 jours. Paiement 50% à la commande, 50% à la livraison.",
            "message_personnel": f"N'hésitez pas à me contacter pour affiner cette proposition, {lead.first_name}."
        }
    
    def _estimate_price_from_budget(self, budget_range: str | None) -> float:
        """
        Estime un prix basé sur la fourchette budgétaire du lead.
        Utilisé uniquement pour le fallback.
        """
        if not budget_range:
            return 1500.0
        
        budget_lower = budget_range.lower()
        if "< 1" in budget_lower or "<1" in budget_lower or "moins de 1" in budget_lower:
            return 800.0
        elif "1" in budget_lower and "3" in budget_lower:  # 1-3k
            return 2000.0
        elif "3" in budget_lower and "5" in budget_lower:  # 3-5k
            return 4000.0
        elif "5" in budget_lower and "10" in budget_lower:  # 5-10k
            return 7500.0
        elif "10" in budget_lower or "+" in budget_lower or ">" in budget_lower:
            return 12000.0
        else:
            return 1500.0
    
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
