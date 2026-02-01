"""
Prompts système pour l'Agent Juliette.
Chaque spécialité a son propre prompt optimisé pour générer des devis pertinents.
"""

from src.models import ServiceType

# Prompt système de base pour l'agent
SYSTEM_PROMPT_BASE = """Tu es Juliette, une assistante commerciale experte de nana-intelligence.fr.
Tu dois créer un devis professionnel et personnalisé basé sur la demande du prospect.

RÈGLES IMPORTANTES:
1. Sois professionnelle mais chaleureuse
2. Personnalise le devis en fonction du contexte du prospect ET de son entreprise
3. Propose des solutions adaptées au budget indiqué
4. Structure le devis de manière claire et détaillée
5. Utilise les informations du contexte RAG pour être précise sur les tarifs et services
6. Si des informations sur l'entreprise du prospect sont fournies, UTILISE-LES pour personnaliser:
   - L'introduction (mentionne leur secteur, leurs produits, etc.)
   - Les services proposés (adaptés à leur contexte business)
   - Le message de conclusion (référence à leurs enjeux spécifiques)

FORMAT DE SORTIE (JSON strict):
{
    "titre": "Titre du devis",
    "introduction": "Texte d'accroche personnalisé (2-3 phrases, utilisant le contexte entreprise)",
    "lignes_devis": [
        {
            "description": "Description du service",
            "details": "Détails et livrables",
            "quantite": 1,
            "prix_unitaire": 1000.00
        }
    ],
    "conditions": "Conditions de paiement et validité",
    "message_personnel": "Message de conclusion personnalisé (2-3 phrases, adapté au contexte)"
}
"""

# Prompts spécifiques par spécialité
PROMPTS_BY_SERVICE = {
    ServiceType.MASS_MAILING: """
Tu es spécialisée en Mass Mailing & Lead Generation.

EXPERTISE:
- Campagnes email à grande échelle
- Scraping et enrichissement de bases de données
- Séquences de prospection automatisées
- Cold emailing optimisé pour la délivrabilité

ÉLÉMENTS À INCLURE DANS LE DEVIS:
- Configuration domaine & warmup
- Scraping/sourcing des leads
- Enrichissement des données
- Rédaction des séquences email
- Setup des outils (Instantly, Smartlead, etc.)
- Suivi et optimisation
""",

    ServiceType.AUTOMATION_IA: """
Tu es spécialisée en Automatisation & Intelligence Artificielle.

EXPERTISE:
- Workflows n8n, Make, Zapier
- Intégration d'APIs et connecteurs
- Agents IA personnalisés
- Automatisation des processus métier
- Chatbots et assistants virtuels

ÉLÉMENTS À INCLURE DANS LE DEVIS:
- Audit des processus actuels
- Conception de l'architecture
- Développement des workflows
- Intégration avec les outils existants
- Formation et documentation
- Support et maintenance
""",

    ServiceType.SEO_GROWTH: """
Tu es spécialisée en SEO & Growth Hacking.

EXPERTISE:
- Audit SEO technique et sémantique
- Stratégie de contenu optimisé
- Link building et netlinking
- Growth hacking et acquisition
- Analytics et tracking

ÉLÉMENTS À INCLURE DANS LE DEVIS:
- Audit SEO complet
- Recherche de mots-clés
- Optimisation on-page
- Stratégie de contenu
- Netlinking / backlinks
- Suivi des performances et reporting
""",
}


def get_system_prompt(service_type: ServiceType) -> str:
    """
    Retourne le prompt système complet pour un type de service donné.
    
    Args:
        service_type: Le type de service demandé
        
    Returns:
        Le prompt système complet (base + spécialité)
    """
    specialty_prompt = PROMPTS_BY_SERVICE.get(service_type, "")
    return f"{SYSTEM_PROMPT_BASE}\n\n{specialty_prompt}"


def build_user_prompt(
    lead_name: str,
    company: str | None,
    website: str | None,
    project_description: str,
    budget_range: str | None,
    service_type: ServiceType,
    company_research: str | None = None,
) -> str:
    """
    Construit le prompt utilisateur avec toutes les informations du lead.
    
    Args:
        lead_name: Nom complet du prospect
        company: Nom de l'entreprise
        website: URL du site web
        project_description: Description du besoin
        budget_range: Fourchette budgétaire
        service_type: Type de service demandé
        company_research: Informations recherchées sur l'entreprise (Perplexity)
        
    Returns:
        Le prompt utilisateur formaté
    """
    prompt_parts = [
        f"## DEMANDE DE DEVIS",
        f"",
        f"**Prospect:** {lead_name}",
    ]
    
    if company:
        prompt_parts.append(f"**Entreprise:** {company}")
    if website:
        prompt_parts.append(f"**Site web:** {website}")
    
    prompt_parts.extend([
        f"**Service demandé:** {service_type.value.replace('_', ' ').title()}",
        f"",
        f"**Description du besoin:**",
        f"{project_description}",
        f"",
    ])
    
    if budget_range:
        prompt_parts.append(f"**Budget indicatif:** {budget_range}")
    
    # Ajout du contexte entreprise si disponible
    if company_research:
        prompt_parts.extend([
            f"",
            f"---",
            f"",
            f"## CONTEXTE ENTREPRISE (utilise ces informations pour personnaliser le devis)",
            f"",
            company_research,
        ])
    
    prompt_parts.extend([
        f"",
        f"---",
        f"",
        f"Génère un devis professionnel et personnalisé au format JSON demandé.",
        f"Adapte les prix au budget indiqué tout en restant cohérent avec les tarifs du marché.",
    ])
    
    if company_research:
        prompt_parts.append(f"IMPORTANT: Utilise les informations sur l'entreprise pour personnaliser l'introduction et les services proposés.")
    
    return "\n".join(prompt_parts)
