"""
Modèles de données Pydantic pour l'Agent Juliette.
Définit les structures pour les leads, devis et emails.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field


class ServiceType(str, Enum):
    """Types de services proposés par nana-intelligence.fr"""
    MASS_MAILING = "mass_mailing"
    AUTOMATION_IA = "automation_ia"
    SEO_GROWTH = "seo_growth"


class LeadRequest(BaseModel):
    """
    Données d'un lead provenant du formulaire Tally.
    Représente une demande de devis entrante.
    """
    # Informations de contact
    first_name: str = Field(..., min_length=2, description="Prénom du lead")
    last_name: str = Field(..., min_length=2, description="Nom du lead")
    email: EmailStr = Field(..., description="Email professionnel du lead")
    company: str | None = Field(None, description="Nom de l'entreprise")
    website: str | None = Field(None, description="Site web de l'entreprise")
    
    # Détails de la demande
    service_type: ServiceType = Field(..., description="Type de service demandé")
    project_description: str = Field(..., min_length=10, description="Description du projet/besoin")
    budget_range: str | None = Field(None, description="Fourchette budgétaire indicative")
    
    # Métadonnées Tally
    tally_response_id: str = Field(..., description="ID de la réponse Tally")
    source: str = Field(default="tally", description="Source du lead")
    received_at: datetime = Field(default_factory=datetime.now)
    consent: bool = Field(default=False, description="Consentement à être recontacté")
    
    @property
    def full_name(self) -> str:
        """Retourne le nom complet du lead."""
        return f"{self.first_name} {self.last_name}"


class DevisItem(BaseModel):
    """Un élément/ligne du devis."""
    description: str
    quantity: int = 1
    unit_price: float
    
    @property
    def total(self) -> float:
        return self.quantity * self.unit_price


class DevisContent(BaseModel):
    """
    Contenu structuré d'un devis généré par l'agent.
    """
    # Référence
    reference: str = Field(..., description="Numéro de référence unique du devis")
    created_at: datetime = Field(default_factory=datetime.now)
    valid_until: datetime = Field(..., description="Date de validité du devis")
    
    # Client
    client_name: str
    client_email: EmailStr
    client_company: str | None = None
    
    # Contenu
    title: str = Field(..., description="Titre du devis")
    introduction: str = Field(..., description="Texte d'introduction personnalisé")
    items: list[DevisItem] = Field(default_factory=list)
    conditions: str = Field(..., description="Conditions et modalités")
    
    # Totaux
    @property
    def subtotal(self) -> float:
        return sum(item.total for item in self.items)
    
    @property
    def tva(self) -> float:
        return self.subtotal * 0.20  # TVA 20%
    
    @property
    def total_ttc(self) -> float:
        return self.subtotal + self.tva


class EmailDraft(BaseModel):
    """
    Structure d'un brouillon d'email à créer dans Gmail.
    """
    to: EmailStr
    subject: str
    body_html: str
    attachment_path: str | None = Field(None, description="Chemin vers le PDF du devis")
    
    # Métadonnées
    lead_reference: str = Field(..., description="Référence du lead associé")
    created_at: datetime = Field(default_factory=datetime.now)


class WebhookResponse(BaseModel):
    """Réponse standard du webhook."""
    success: bool
    message: str
    lead_reference: str | None = None
    draft_id: str | None = None
    data: dict | None = None  # Données additionnelles du traitement
