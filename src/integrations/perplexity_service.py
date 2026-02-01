"""
Service d'intégration Perplexity.
Utilise l'API Perplexity Sonar pour rechercher des informations sur les entreprises.
"""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from openai import OpenAI

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CompanyResearch:
    """
    Résultat de la recherche sur une entreprise.
    Contient les informations collectées par Perplexity.
    """
    company_name: str
    sector: str = ""
    size: str = ""
    products_services: str = ""
    recent_news: str = ""
    competitors: str = ""
    summary: str = ""
    sources: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    
    def to_context(self) -> str:
        """
        Formate les informations pour injection dans le prompt.
        """
        if not self.success:
            return ""
        
        parts = [f"## Informations sur {self.company_name}"]
        
        if self.sector:
            parts.append(f"**Secteur d'activité:** {self.sector}")
        if self.size:
            parts.append(f"**Taille de l'entreprise:** {self.size}")
        if self.products_services:
            parts.append(f"**Produits/Services:** {self.products_services}")
        if self.recent_news:
            parts.append(f"**Actualités récentes:** {self.recent_news}")
        if self.competitors:
            parts.append(f"**Concurrents identifiés:** {self.competitors}")
        if self.summary:
            parts.append(f"**Résumé:** {self.summary}")
        
        return "\n\n".join(parts)


# Prompt pour la recherche entreprise
COMPANY_RESEARCH_PROMPT = """Recherche des informations sur l'entreprise suivante:
- Nom: {company}
- Site web: {website}

Fournis les informations suivantes de manière concise et factuelle:

1. **Secteur d'activité**: Dans quel secteur opère cette entreprise?
2. **Taille**: Estimation de la taille (startup, PME, ETI, grand groupe) et nombre d'employés si disponible
3. **Produits/Services**: Quels sont leurs principaux produits ou services?
4. **Actualités récentes**: Y a-t-il des actualités récentes importantes (levées de fonds, partenariats, lancements)?
5. **Concurrents**: Quels sont les principaux concurrents sur leur marché?
6. **Résumé**: Un bref résumé de 2-3 phrases sur cette entreprise

Réponds en français de manière structurée et concise.
"""


class PerplexityService:
    """
    Service pour rechercher des informations sur les entreprises via Perplexity.
    Utilise l'API compatible OpenAI de Perplexity.
    """
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.perplexity_api_key
        self.model = settings.perplexity_model
        
        if not self.api_key:
            logger.warning("⚠️ Clé API Perplexity non configurée - recherche entreprise désactivée")
            self.client = None
        else:
            # Perplexity utilise une API compatible OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.perplexity.ai"
            )
            logger.info(f"PerplexityService initialisé (modèle: {self.model})")
    
    def is_available(self) -> bool:
        """Vérifie si le service est disponible (clé API configurée)."""
        return self.client is not None
    
    def research_company(
        self,
        company: str,
        website: str | None = None
    ) -> CompanyResearch:
        """
        Recherche des informations sur une entreprise.
        
        Args:
            company: Nom de l'entreprise
            website: URL du site web (optionnel mais recommandé)
            
        Returns:
            CompanyResearch avec les informations trouvées
        """
        # Vérification que le service est disponible
        if not self.is_available():
            return CompanyResearch(
                company_name=company,
                success=False,
                error="Service Perplexity non configuré"
            )
        
        # Vérification que l'entreprise est renseignée
        if not company or company.strip() == "":
            return CompanyResearch(
                company_name="Inconnu",
                success=False,
                error="Nom d'entreprise non fourni"
            )
        
        logger.info(f"🔍 Recherche Perplexity sur: {company}")
        
        # Construction du prompt
        prompt = COMPANY_RESEARCH_PROMPT.format(
            company=company,
            website=website or "Non fourni"
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un assistant de recherche d'entreprise. Fournis des informations précises et sourcées."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.1,  # Très factuel
            )
            
            content = response.choices[0].message.content
            logger.info(f"✅ Recherche Perplexity terminée ({len(content)} caractères)")
            
            # Parsing de la réponse
            return self._parse_research_response(company, content)
            
        except Exception as e:
            logger.error(f"❌ Erreur Perplexity: {e}")
            return CompanyResearch(
                company_name=company,
                success=False,
                error=str(e)
            )
    
    def _parse_research_response(self, company: str, content: str) -> CompanyResearch:
        """
        Parse la réponse de Perplexity pour extraire les informations structurées.
        """
        research = CompanyResearch(company_name=company, summary=content)
        
        # Extraction simple basée sur les en-têtes markdown
        lines = content.split("\n")
        current_section = None
        current_content = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Détection des sections
            if "secteur" in line_lower and ("activité" in line_lower or ":" in line):
                if current_section:
                    self._set_section(research, current_section, current_content)
                current_section = "sector"
                current_content = [line.split(":", 1)[-1].strip()] if ":" in line else []
            elif "taille" in line_lower and ":" in line:
                if current_section:
                    self._set_section(research, current_section, current_content)
                current_section = "size"
                current_content = [line.split(":", 1)[-1].strip()]
            elif "produit" in line_lower or "service" in line_lower and ":" in line:
                if current_section:
                    self._set_section(research, current_section, current_content)
                current_section = "products"
                current_content = [line.split(":", 1)[-1].strip()] if ":" in line else []
            elif "actualité" in line_lower or "news" in line_lower:
                if current_section:
                    self._set_section(research, current_section, current_content)
                current_section = "news"
                current_content = [line.split(":", 1)[-1].strip()] if ":" in line else []
            elif "concurrent" in line_lower:
                if current_section:
                    self._set_section(research, current_section, current_content)
                current_section = "competitors"
                current_content = [line.split(":", 1)[-1].strip()] if ":" in line else []
            elif "résumé" in line_lower or "summary" in line_lower:
                if current_section:
                    self._set_section(research, current_section, current_content)
                current_section = "summary_section"
                current_content = [line.split(":", 1)[-1].strip()] if ":" in line else []
            elif current_section and line.strip():
                # Ajoute le contenu à la section courante
                current_content.append(line.strip())
        
        # Dernière section
        if current_section:
            self._set_section(research, current_section, current_content)
        
        return research
    
    def _set_section(self, research: CompanyResearch, section: str, content: list[str]) -> None:
        """Affecte le contenu à la section appropriée."""
        text = " ".join(content).strip()
        text = text.lstrip("*-:").strip()  # Nettoie les marqueurs markdown
        
        if section == "sector":
            research.sector = text
        elif section == "size":
            research.size = text
        elif section == "products":
            research.products_services = text
        elif section == "news":
            research.recent_news = text
        elif section == "competitors":
            research.competitors = text
        elif section == "summary_section":
            # Ne remplace le résumé que si on a extrait quelque chose
            if text:
                research.summary = text


# Cache pour éviter les appels redondants (même entreprise dans la même session)
_company_cache: dict[str, CompanyResearch] = {}


def get_perplexity_service() -> PerplexityService:
    """Retourne une instance du service Perplexity."""
    return PerplexityService()


def research_company_cached(company: str, website: str | None = None) -> CompanyResearch:
    """
    Recherche avec cache pour éviter les appels API redondants.
    """
    cache_key = f"{company}|{website or ''}"
    
    if cache_key in _company_cache:
        logger.debug(f"Cache hit pour: {company}")
        return _company_cache[cache_key]
    
    service = get_perplexity_service()
    result = service.research_company(company, website)
    
    # Cache uniquement les succès
    if result.success:
        _company_cache[cache_key] = result
    
    return result
