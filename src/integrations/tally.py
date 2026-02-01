"""
Modèles Pydantic pour le parsing des payloads webhook Tally.
Basé sur la structure réelle des données envoyées par Tally.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class TallyFieldOption(BaseModel):
    """Option d'un champ dropdown ou checkbox."""
    id: str
    text: str


class TallyField(BaseModel):
    """
    Un champ du formulaire Tally.
    Le type 'value' peut être str, list[str], bool selon le type de champ.
    """
    key: str
    label: str
    type: str  # INPUT_TEXT, TEXTAREA, DROPDOWN, CHECKBOXES
    value: str | list[str] | bool | None = None
    options: list[TallyFieldOption] | None = None
    
    def get_text_value(self) -> str | None:
        """Retourne la valeur textuelle du champ."""
        if isinstance(self.value, str):
            return self.value
        elif isinstance(self.value, bool):
            return str(self.value)
        elif isinstance(self.value, list) and self.options:
            # Pour les dropdowns/checkboxes, on récupère le texte de l'option sélectionnée
            selected_texts = []
            for option_id in self.value:
                for option in self.options:
                    if option.id == option_id:
                        selected_texts.append(option.text)
                        break
            return ", ".join(selected_texts) if selected_texts else None
        return None


class TallyFormData(BaseModel):
    """Données du formulaire dans le payload Tally."""
    responseId: str
    submissionId: str
    respondentId: str
    formId: str
    formName: str
    createdAt: datetime
    fields: list[TallyField]
    
    def get_field_by_label(self, label: str) -> TallyField | None:
        """Recherche un champ par son label (insensible à la casse et aux espaces)."""
        normalized_label = label.lower().strip()
        for field in self.fields:
            if field.label.lower().strip().replace("\n", "") == normalized_label:
                return field
        return None
    
    def get_field_value(self, label: str) -> str | None:
        """Retourne la valeur textuelle d'un champ par son label."""
        field = self.get_field_by_label(label)
        if field:
            return field.get_text_value()
        return None


class TallyWebhookPayload(BaseModel):
    """
    Payload complet reçu du webhook Tally.
    """
    eventId: str
    eventType: str  # FORM_RESPONSE
    createdAt: datetime
    data: TallyFormData


class TallyWebhookRequest(BaseModel):
    """
    Requête webhook Tally (peut être un array ou un objet unique).
    Ce modèle gère le cas où Tally envoie un array avec un seul élément.
    """
    body: TallyWebhookPayload
