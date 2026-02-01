"""
Tests pour l'intégration Tally.
"""

import pytest
from datetime import datetime
from src.integrations.tally import TallyWebhookPayload, TallyField, TallyFieldOption
from src.integrations.tally_service import parse_tally_to_lead
from src.models import ServiceType


# Payload de test basé sur l'exemple réel fourni
SAMPLE_TALLY_PAYLOAD = {
    "eventId": "d23d56d6-6d9f-4b3d-8521-bb358027ac7b",
    "eventType": "FORM_RESPONSE",
    "createdAt": "2026-01-31T21:43:01.771Z",
    "data": {
        "responseId": "GxZYdqj",
        "submissionId": "GxZYdqj",
        "respondentId": "ZjdJRxV",
        "formId": "yPY9Bx",
        "formName": "Demande de devis",
        "createdAt": "2026-01-31T21:43:01.000Z",
        "fields": [
            {
                "key": "question_8KX57P",
                "label": "Prénom",
                "type": "INPUT_TEXT",
                "value": "Jimmy"
            },
            {
                "key": "question_0xK5Nj",
                "label": "Nom",
                "type": "INPUT_TEXT",
                "value": "Gay"
            },
            {
                "key": "question_zqkvP0",
                "label": "Email Pro",
                "type": "INPUT_TEXT",
                "value": "jimmygay13180@gmail.com"
            },
            {
                "key": "question_5zJ5WE",
                "label": "Entreprise",
                "type": "INPUT_TEXT",
                "value": "nana-intelligence"
            },
            {
                "key": "question_d6OVBK",
                "label": "Site Web\n",
                "type": "INPUT_TEXT",
                "value": "https://nana-intelligence.fr/"
            },
            {
                "key": "question_YQ1yNJ",
                "label": "Type de service",
                "type": "DROPDOWN",
                "value": ["10477feb-78b4-4a5d-96d2-c525b23c9896"],
                "options": [
                    {"id": "10477feb-78b4-4a5d-96d2-c525b23c9896", "text": "Mass Mailing & Lead Gen"},
                    {"id": "c30f2b45-95ab-4327-a09f-375c18b471d8", "text": "Automatisation & IA"},
                    {"id": "34e6ddc8-54ed-4948-b62e-9bde294056e3", "text": "SEO & Growth Hacking"}
                ]
            },
            {
                "key": "question_DNjygZ",
                "label": "Votre Besoin",
                "type": "TEXTAREA",
                "value": "Augmenter mon référencement sur google pour capter plus de lead"
            },
            {
                "key": "question_a6RgQv",
                "label": "Budget estimé\n",
                "type": "DROPDOWN",
                "value": ["5c526960-ed53-4f05-a70e-096956f3f7ef"],
                "options": [
                    {"id": "5c526960-ed53-4f05-a70e-096956f3f7ef", "text": "< 1 000€"},
                    {"id": "7ccf8026-f040-432d-90f1-ad9f8c982857", "text": "1–3k€"}
                ]
            },
            {
                "key": "question_67gy8P",
                "label": "Consentement\n",
                "type": "CHECKBOXES",
                "value": ["1d3eb89f-84fe-4b9e-9854-bfd027cd8138"],
                "options": [
                    {"id": "1d3eb89f-84fe-4b9e-9854-bfd027cd8138", "text": "J'accepte d'être recontacté au sujet de ma demande de devis."}
                ]
            }
        ]
    }
}


class TestTallyPayloadParsing:
    """Tests pour le parsing du payload Tally."""
    
    def test_parse_tally_payload(self):
        """Test du parsing du payload complet."""
        payload = TallyWebhookPayload(**SAMPLE_TALLY_PAYLOAD)
        
        assert payload.eventId == "d23d56d6-6d9f-4b3d-8521-bb358027ac7b"
        assert payload.eventType == "FORM_RESPONSE"
        assert payload.data.formName == "Demande de devis"
        assert payload.data.responseId == "GxZYdqj"
    
    def test_get_field_by_label(self):
        """Test de la recherche de champ par label."""
        payload = TallyWebhookPayload(**SAMPLE_TALLY_PAYLOAD)
        
        prenom_field = payload.data.get_field_by_label("Prénom")
        assert prenom_field is not None
        assert prenom_field.get_text_value() == "Jimmy"
    
    def test_get_field_value_dropdown(self):
        """Test de récupération de valeur d'un dropdown."""
        payload = TallyWebhookPayload(**SAMPLE_TALLY_PAYLOAD)
        
        service_type = payload.data.get_field_value("Type de service")
        assert service_type == "Mass Mailing & Lead Gen"
    
    def test_parse_tally_to_lead(self):
        """Test de la transformation vers LeadRequest."""
        payload = TallyWebhookPayload(**SAMPLE_TALLY_PAYLOAD)
        lead = parse_tally_to_lead(payload)
        
        assert lead.first_name == "Jimmy"
        assert lead.last_name == "Gay"
        assert lead.email == "jimmygay13180@gmail.com"
        assert lead.company == "nana-intelligence"
        assert lead.website == "https://nana-intelligence.fr/"
        assert lead.service_type == ServiceType.MASS_MAILING
        assert "référencement" in lead.project_description
        assert lead.budget_range == "< 1 000€"
        assert lead.consent is True
        assert lead.tally_response_id == "GxZYdqj"
    
    def test_lead_full_name(self):
        """Test de la propriété full_name."""
        payload = TallyWebhookPayload(**SAMPLE_TALLY_PAYLOAD)
        lead = parse_tally_to_lead(payload)
        
        assert lead.full_name == "Jimmy Gay"
