"""
Schémas Pydantic pour la validation des réponses du LLM.
Utilisés pour parser et valider les devis générés par l'IA.
"""

import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class LLMDevisLine(BaseModel):
    """
    Ligne de devis retournée par le LLM.
    Représente un service ou une prestation avec son prix.
    """
    description: str = Field(..., min_length=1, description="Description du service")
    details: Optional[str] = Field(None, description="Détails supplémentaires")
    quantite: int = Field(ge=1, default=1, description="Quantité")
    prix_unitaire: float = Field(ge=0, description="Prix unitaire HT")
    
    @field_validator('prix_unitaire', mode='before')
    @classmethod
    def coerce_prix_to_float(cls, v):
        """Convertit le prix en float, même si le LLM renvoie une string."""
        if isinstance(v, str):
            # Nettoie les caractères non numériques (€, espaces, etc.)
            cleaned = re.sub(r'[^\d.,]', '', v)
            cleaned = cleaned.replace(',', '.')
            return float(cleaned) if cleaned else 0.0
        return float(v) if v is not None else 0.0
    
    @field_validator('quantite', mode='before')
    @classmethod
    def coerce_quantite_to_int(cls, v):
        """Convertit la quantité en int, même si le LLM renvoie une string."""
        if isinstance(v, str):
            cleaned = re.sub(r'[^\d]', '', v)
            return int(cleaned) if cleaned else 1
        return int(v) if v is not None else 1


class LLMDevisPayload(BaseModel):
    """
    Structure complète d'un devis retourné par le LLM.
    Ce schéma valide et nettoie la réponse JSON du modèle.
    """
    titre: str = Field(..., min_length=1, description="Titre du devis")
    introduction: str = Field(..., min_length=1, description="Texte d'introduction personnalisé")
    lignes_devis: list[LLMDevisLine] = Field(..., min_length=1, description="Lignes du devis")
    conditions: str = Field(
        default="Devis valable 30 jours. Paiement 50% à la commande, 50% à la livraison.",
        description="Conditions de paiement et validité"
    )
    message_personnel: Optional[str] = Field(None, description="Message de conclusion personnalisé")
    
    @field_validator('lignes_devis', mode='before')
    @classmethod
    def ensure_list(cls, v):
        """S'assure que lignes_devis est bien une liste."""
        if v is None:
            return []
        if not isinstance(v, list):
            return [v]
        return v


# Regex pour extraire un objet JSON d'une réponse textuelle
# Capture le premier bloc {...} même si du texte l'entoure
JSON_OBJECT_PATTERN = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL)


def extract_json_from_text(text: str) -> str | None:
    """
    Extrait le premier objet JSON valide d'un texte.
    
    Le LLM peut retourner du texte avant/après le JSON,
    cette fonction isole le bloc JSON.
    
    Args:
        text: Texte potentiellement contenant un objet JSON
        
    Returns:
        Le premier objet JSON trouvé, ou None
    """
    # Cherche tous les candidats JSON
    matches = JSON_OBJECT_PATTERN.findall(text)
    
    # Retourne le match le plus long (probablement le JSON complet)
    if matches:
        return max(matches, key=len)
    
    return None
