"""
Tests pour le générateur de devis.
Valide le parsing JSON robuste et le fallback contextualisé.
"""

import pytest
import json
from unittest.mock import MagicMock, patch

from src.agent.devis_generator import DevisGenerator
from src.agent.devis_schemas import LLMDevisPayload, extract_json_from_text
from src.models import LeadRequest, ServiceType


# Fixtures pour les tests
@pytest.fixture
def sample_lead() -> LeadRequest:
    """Lead de test standard."""
    return LeadRequest(
        first_name="Alice",
        last_name="Martin",
        email="alice@example.com",
        company="TechCorp",
        website="https://techcorp.fr",
        service_type=ServiceType.SEO_GROWTH,
        project_description="Améliorer notre référencement Google pour augmenter le trafic organique",
        budget_range="3-5k€",
        consent=True,
        tally_response_id="test-alice-001",
    )


@pytest.fixture
def automation_lead() -> LeadRequest:
    """Lead pour service automation."""
    return LeadRequest(
        first_name="Bob",
        last_name="Dupont",
        email="bob@startup.io",
        company="StartupIO",
        service_type=ServiceType.AUTOMATION_IA,
        project_description="Automatiser notre CRM avec des workflows n8n et intégrer ChatGPT",
        budget_range="5-10k€",
        consent=True,
        tally_response_id="test-bob-002",
    )


@pytest.fixture
def valid_json_response() -> str:
    """Réponse JSON valide du LLM."""
    return json.dumps({
        "titre": "Devis SEO & Growth Hacking",
        "introduction": "Cher(e) Alice, suite à notre échange, voici notre proposition personnalisée.",
        "lignes_devis": [
            {
                "description": "Audit SEO complet",
                "details": "Analyse technique, sémantique et concurrentielle",
                "quantite": 1,
                "prix_unitaire": 800.00
            },
            {
                "description": "Optimisation on-page",
                "details": "Méta-tags, structure, contenu",
                "quantite": 10,
                "prix_unitaire": 150.00
            },
            {
                "description": "Stratégie de backlinks",
                "details": "Acquisition de 20 backlinks de qualité",
                "quantite": 1,
                "prix_unitaire": 1200.00
            }
        ],
        "conditions": "Devis valable 30 jours. Paiement 50% à la commande.",
        "message_personnel": "Je reste disponible pour échanger sur ce projet."
    })


class TestExtractJsonFromText:
    """Tests pour la fonction d'extraction JSON."""
    
    def test_extract_json_simple(self):
        """Extrait un JSON simple."""
        text = '{"titre": "Test"}'
        result = extract_json_from_text(text)
        assert result is not None
        assert json.loads(result)["titre"] == "Test"
    
    def test_extract_json_with_text_before(self):
        """Extrait JSON avec texte avant."""
        text = 'Voici votre devis: {"titre": "Devis Test", "introduction": "Hello"}'
        result = extract_json_from_text(text)
        assert result is not None
        data = json.loads(result)
        assert data["titre"] == "Devis Test"
    
    def test_extract_json_with_text_after(self):
        """Extrait JSON avec texte après."""
        text = '{"titre": "Test"} Cordialement, Juliette'
        result = extract_json_from_text(text)
        assert result is not None
    
    def test_extract_no_json(self):
        """Retourne None si pas de JSON."""
        text = "Ceci est un texte sans JSON"
        result = extract_json_from_text(text)
        # La regex peut matcher des accolades simples, donc on vérifie le parsing
        if result:
            with pytest.raises(json.JSONDecodeError):
                json.loads(result)


class TestLLMDevisPayloadValidation:
    """Tests pour la validation Pydantic du payload."""
    
    def test_valid_payload(self, valid_json_response):
        """Valide un payload correct."""
        data = json.loads(valid_json_response)
        payload = LLMDevisPayload.model_validate(data)
        
        assert payload.titre == "Devis SEO & Growth Hacking"
        assert len(payload.lignes_devis) == 3
        assert payload.lignes_devis[0].prix_unitaire == 800.00
    
    def test_coerce_prix_string(self):
        """Convertit un prix en string vers float."""
        data = {
            "titre": "Test",
            "introduction": "Intro",
            "lignes_devis": [{
                "description": "Service",
                "quantite": 1,
                "prix_unitaire": "1500€"  # String au lieu de float
            }]
        }
        payload = LLMDevisPayload.model_validate(data)
        assert payload.lignes_devis[0].prix_unitaire == 1500.0
    
    def test_coerce_quantite_string(self):
        """Convertit une quantité en string vers int."""
        data = {
            "titre": "Test",
            "introduction": "Intro",
            "lignes_devis": [{
                "description": "Service",
                "quantite": "5",  # String au lieu de int
                "prix_unitaire": 100
            }]
        }
        payload = LLMDevisPayload.model_validate(data)
        assert payload.lignes_devis[0].quantite == 5
    
    def test_default_conditions(self):
        """Applique les conditions par défaut."""
        data = {
            "titre": "Test",
            "introduction": "Intro",
            "lignes_devis": [{"description": "S", "quantite": 1, "prix_unitaire": 100}]
            # Pas de "conditions"
        }
        payload = LLMDevisPayload.model_validate(data)
        assert "30 jours" in payload.conditions


class TestDevisGeneratorParseResponse:
    """Tests pour la méthode _parse_response du générateur."""
    
    @pytest.fixture
    def generator(self):
        """Crée un générateur mocké (sans connexion externe)."""
        with patch('src.agent.devis_generator.get_openai_service') as mock_openai, \
             patch('src.agent.devis_generator.get_qdrant_service') as mock_qdrant:
            mock_openai.return_value = MagicMock()
            mock_qdrant.return_value = MagicMock()
            return DevisGenerator()
    
    def test_parse_valid_json_direct(self, generator, sample_lead, valid_json_response):
        """Parse un JSON valide directement."""
        result = generator._parse_response(valid_json_response, sample_lead)
        
        assert result["titre"] == "Devis SEO & Growth Hacking"
        assert len(result["lignes_devis"]) == 3
    
    def test_parse_json_with_markdown_backticks(self, generator, sample_lead, valid_json_response):
        """Parse un JSON entouré de backticks markdown."""
        response = f"```json\n{valid_json_response}\n```"
        result = generator._parse_response(response, sample_lead)
        
        assert result["titre"] == "Devis SEO & Growth Hacking"
    
    def test_parse_json_with_text_around(self, generator, sample_lead, valid_json_response):
        """Parse un JSON avec du texte avant/après."""
        response = f"Voici le devis demandé:\n\n{valid_json_response}\n\nCordialement, Juliette"
        result = generator._parse_response(response, sample_lead)
        
        assert result["titre"] == "Devis SEO & Growth Hacking"
    
    def test_fallback_with_invalid_json(self, generator, sample_lead):
        """Utilise le fallback contextualisé si JSON invalide."""
        response = "Ceci n'est pas du JSON valide, désolé!"
        result = generator._parse_response(response, sample_lead)
        
        # Le fallback doit être basé sur le lead, pas un template fixe
        assert "SEO" in result["titre"] or "Seo" in result["titre"]
        assert "TechCorp" in result["titre"] or sample_lead.full_name in result["titre"]
        assert sample_lead.first_name in result["introduction"]
    
    def test_fallback_uses_budget_for_pricing(self, generator, sample_lead):
        """Le fallback estime le prix selon le budget."""
        response = "Invalid JSON"
        result = generator._parse_response(response, sample_lead)
        
        # Budget "3-5k€" devrait donner un prix autour de 4000€
        prix = result["lignes_devis"][0]["prix_unitaire"]
        assert prix == 4000.0
    
    def test_different_leads_produce_different_fallbacks(self, generator, sample_lead, automation_lead):
        """Deux leads différents produisent des fallbacks différents."""
        invalid_response = "Not JSON"
        
        result_alice = generator._parse_response(invalid_response, sample_lead)
        result_bob = generator._parse_response(invalid_response, automation_lead)
        
        # Les titres doivent être différents
        assert result_alice["titre"] != result_bob["titre"]
        
        # Les prix doivent être différents (budgets différents)
        prix_alice = result_alice["lignes_devis"][0]["prix_unitaire"]
        prix_bob = result_bob["lignes_devis"][0]["prix_unitaire"]
        assert prix_alice != prix_bob


class TestEstimatePriceFromBudget:
    """Tests pour l'estimation du prix depuis le budget."""
    
    @pytest.fixture
    def generator(self):
        with patch('src.agent.devis_generator.get_openai_service') as mock_openai, \
             patch('src.agent.devis_generator.get_qdrant_service') as mock_qdrant:
            mock_openai.return_value = MagicMock()
            mock_qdrant.return_value = MagicMock()
            return DevisGenerator()
    
    def test_budget_less_than_1k(self, generator):
        assert generator._estimate_price_from_budget("< 1 000€") == 800.0
        assert generator._estimate_price_from_budget("<1000€") == 800.0
    
    def test_budget_1_to_3k(self, generator):
        assert generator._estimate_price_from_budget("1-3k€") == 2000.0
        assert generator._estimate_price_from_budget("1 000 - 3 000€") == 2000.0
    
    def test_budget_3_to_5k(self, generator):
        assert generator._estimate_price_from_budget("3-5k€") == 4000.0
    
    def test_budget_5_to_10k(self, generator):
        assert generator._estimate_price_from_budget("5-10k€") == 7500.0
    
    def test_budget_10k_plus(self, generator):
        assert generator._estimate_price_from_budget("10k€+") == 12000.0
        assert generator._estimate_price_from_budget("> 10 000€") == 12000.0
    
    def test_budget_none(self, generator):
        assert generator._estimate_price_from_budget(None) == 1500.0
    
    def test_budget_unknown(self, generator):
        assert generator._estimate_price_from_budget("À définir") == 1500.0
