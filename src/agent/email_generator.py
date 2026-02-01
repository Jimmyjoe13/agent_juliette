"""
Générateur d'email professionnel par IA.
Crée des emails personnalisés et contextualisés pour accompagner les devis.
"""

import logging
from dataclasses import dataclass

from src.models import LeadRequest, DevisContent, ServiceType
from src.integrations.openai_service import get_openai_service

logger = logging.getLogger(__name__)


@dataclass
class GeneratedEmail:
    """Résultat de la génération d'email."""
    subject: str
    body_html: str
    body_text: str  # Version texte pour fallback


# =============================================================================
# PROMPT POUR LA GÉNÉRATION D'EMAIL
# =============================================================================

EMAIL_SYSTEM_PROMPT = """Tu es Juliette, consultante commerciale senior chez nana-intelligence.fr.
Tu dois rédiger un email professionnel et chaleureux pour accompagner un devis.

═══════════════════════════════════════════════════════════════════════════════
                          RÈGLES DE RÉDACTION
═══════════════════════════════════════════════════════════════════════════════

1. TON: Professionnel mais chaleureux, pas corporate/froid
2. PERSONNALISATION: Utiliser le prénom du prospect + contexte entreprise
3. STRUCTURE CLAIRE: Introduction → Valeur ajoutée → Récapitulatif → Call-to-action
4. LONGUEUR: 150-250 mots maximum (email lisible en 30 secondes)
5. PAS DE PIÈCE JOINTE mentionnée (sera ajoutée automatiquement)

═══════════════════════════════════════════════════════════════════════════════
                          STRUCTURE ATTENDUE
═══════════════════════════════════════════════════════════════════════════════

L'email DOIT contenir ces sections dans cet ordre:

1. ACCROCHE PERSONNALISÉE (1-2 phrases)
   → Remercier pour la demande + mentionner le contexte
   → Exemple: "Suite à notre échange sur [sujet], j'ai le plaisir..."

2. PROPOSITION DE VALEUR (2-3 phrases)
   → Résumer ce que le devis apporte
   → Mentionner un bénéfice concret lié à leur activité

3. RÉCAPITULATIF CHIFFRÉ (bloc visuel)
   → Nom du projet/prestation
   → Montant total TTC
   → Délai estimé

4. PROCHAINES ÉTAPES (1-2 phrases)
   → Proposer un échange téléphonique ou visio
   → Mentionner la validité du devis

5. SIGNATURE PROFESSIONNELLE
   → Prénom + "Consultante nana-intelligence"
   → Pas de coordonnées (dans le footer)

═══════════════════════════════════════════════════════════════════════════════
                          FORMAT DE SORTIE
═══════════════════════════════════════════════════════════════════════════════

Retourne UNIQUEMENT le contenu de l'email (pas de HTML), formaté ainsi:

SUJET: [Ligne d'objet de l'email - intrigante et personnalisée]

---

[Contenu de l'email avec sauts de ligne naturels]

[Signature]
"""


def _build_email_prompt(lead: LeadRequest, devis: DevisContent, company_context: str | None) -> str:
    """Construit le prompt utilisateur pour la génération d'email."""
    
    # Résumé des prestations
    prestations_summary = "\n".join([
        f"  • {item.description}: {item.unit_price:,.0f}€"
        for item in devis.items[:5]  # Max 5 pour pas surcharger
    ])
    if len(devis.items) > 5:
        prestations_summary += f"\n  • ... et {len(devis.items) - 5} autres prestations"
    
    prompt = f"""
═══════════════════════════════════════════════════════════════════════════════
                    INFORMATIONS POUR L'EMAIL
═══════════════════════════════════════════════════════════════════════════════

👤 PROSPECT:
   Prénom: {lead.first_name}
   Nom complet: {lead.full_name}
   Entreprise: {lead.company or "Non renseignée"}
   
📋 DEMANDE INITIALE:
   Service: {lead.service_type.value.replace('_', ' ').title()}
   Description: {lead.project_description[:200]}...
   
💰 DEVIS GÉNÉRÉ:
   Référence: {devis.reference}
   Titre: {devis.title}
   Nombre de prestations: {len(devis.items)}
   
   Prestations:
{prestations_summary}
   
   ────────────────
   Sous-total HT: {devis.subtotal:,.2f}€
   TVA (20%): {devis.tva:,.2f}€
   TOTAL TTC: {devis.total_ttc:,.2f}€
   ────────────────
   
   Conditions: {devis.conditions[:100]}...
"""

    if company_context:
        prompt += f"""
🔍 CONTEXTE ENTREPRISE:
{company_context[:500]}
"""

    prompt += """

═══════════════════════════════════════════════════════════════════════════════
                    INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

Rédige un email professionnel et personnalisé qui:
1. Utilise le PRÉNOM du prospect (pas "Bonjour Monsieur/Madame")
2. Mentionne leur SECTEUR D'ACTIVITÉ si disponible
3. Résume la VALEUR de la proposition
4. Inclut le MONTANT TOTAL TTC clairement visible
5. Propose une PROCHAINE ÉTAPE concrète

Format attendu:
SUJET: [Ligne d'objet percutante]

---

[Contenu de l'email]
"""
    
    return prompt


def _parse_email_response(response: str, lead: LeadRequest, devis: DevisContent) -> GeneratedEmail:
    """Parse la réponse du LLM pour extraire sujet et corps."""
    
    lines = response.strip().split("\n")
    
    # Extraction du sujet
    subject = f"Votre devis {devis.reference} - nana-intelligence"  # Fallback
    body_lines = []
    in_body = False
    
    for line in lines:
        if line.upper().startswith("SUJET:"):
            subject = line.replace("SUJET:", "").replace("sujet:", "").strip()
            # Nettoyer les guillemets éventuels
            subject = subject.strip('"\'')
        elif line.strip() == "---":
            in_body = True
        elif in_body:
            body_lines.append(line)
    
    # Corps de l'email (texte brut)
    body_text = "\n".join(body_lines).strip()
    
    # Si le parsing a échoué, utiliser tout le contenu
    if not body_text:
        body_text = response.strip()
    
    # Conversion en HTML
    body_html = _convert_to_html(body_text, lead, devis)
    
    return GeneratedEmail(
        subject=subject,
        body_html=body_html,
        body_text=body_text,
    )


def _convert_to_html(text: str, lead: LeadRequest, devis: DevisContent) -> str:
    """Convertit le texte en email HTML avec design professionnel."""
    
    # Conversion des sauts de ligne en paragraphes HTML
    paragraphs = text.split("\n\n")
    html_paragraphs = []
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Remplacer les sauts de ligne simples par <br>
        p = p.replace("\n", "<br>")
        html_paragraphs.append(f"<p>{p}</p>")
    
    body_content = "\n".join(html_paragraphs)
    
    # Template HTML professionnel
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Devis {devis.reference}</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; color: #1a1a2e;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 650px; margin: 0 auto; background-color: #ffffff;">
        <!-- Header avec gradient -->
        <tr>
            <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 40px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 26px; font-weight: 600; letter-spacing: -0.5px;">
                    nana-intelligence
                </h1>
                <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 14px;">
                    Automatisation & IA pour votre croissance
                </p>
            </td>
        </tr>
        
        <!-- Corps de l'email -->
        <tr>
            <td style="padding: 40px;">
                <div style="line-height: 1.7; font-size: 15px; color: #2d2d44;">
                    {body_content}
                </div>
                
                <!-- Bloc récapitulatif -->
                <table role="presentation" width="100%" style="margin: 30px 0; background: linear-gradient(135deg, #f8f9ff 0%, #f0f1f8 100%); border-radius: 12px; border-left: 4px solid #667eea;">
                    <tr>
                        <td style="padding: 25px;">
                            <p style="margin: 0 0 8px; color: #667eea; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">
                                📄 Votre devis
                            </p>
                            <p style="margin: 0 0 5px; font-size: 16px; font-weight: 600; color: #1a1a2e;">
                                {devis.title}
                            </p>
                            <p style="margin: 0; color: #666; font-size: 13px;">
                                Réf. {devis.reference}
                            </p>
                            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 15px 0;">
                            <p style="margin: 0; font-size: 28px; font-weight: 700; color: #667eea;">
                                {devis.total_ttc:,.2f} € <span style="font-size: 14px; font-weight: 400; color: #666;">TTC</span>
                            </p>
                        </td>
                    </tr>
                </table>
                
                <!-- CTA -->
                <table role="presentation" width="100%" style="margin: 25px 0;">
                    <tr>
                        <td style="text-align: center;">
                            <p style="color: #666; font-size: 14px; margin: 0 0 15px;">
                                Prêt à démarrer ? Répondez à cet email ou planifions un appel.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        
        <!-- Footer -->
        <tr>
            <td style="background-color: #f8f9fa; padding: 25px 40px; text-align: center; border-top: 1px solid #e9ecef;">
                <p style="margin: 0 0 5px; font-size: 14px; font-weight: 600; color: #1a1a2e;">
                    Juliette • nana-intelligence
                </p>
                <p style="margin: 0; font-size: 13px; color: #6b7280;">
                    contact@nana-intelligence.fr • nana-intelligence.fr
                </p>
                <p style="margin: 15px 0 0; font-size: 11px; color: #9ca3af;">
                    Cet email et son contenu sont confidentiels. Le devis joint est valable 30 jours.
                </p>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    return html


class EmailGenerator:
    """
    Générateur d'emails personnalisés par IA.
    Crée des emails adaptés au contexte du prospect et du devis.
    """
    
    def __init__(self):
        self.openai = get_openai_service()
        logger.info("EmailGenerator initialisé")
    
    def generate(
        self,
        lead: LeadRequest,
        devis: DevisContent,
        company_context: str | None = None,
    ) -> GeneratedEmail:
        """
        Génère un email personnalisé pour accompagner le devis.
        
        Args:
            lead: Informations du prospect
            devis: Devis généré
            company_context: Contexte entreprise (Perplexity) optionnel
            
        Returns:
            GeneratedEmail avec sujet et corps HTML
        """
        logger.info(f"📧 Génération email IA pour {lead.full_name}")
        
        # Construction du prompt
        user_prompt = _build_email_prompt(lead, devis, company_context)
        
        try:
            # Appel au LLM
            response = self.openai.generate_completion(
                prompt=user_prompt,
                system_prompt=EMAIL_SYSTEM_PROMPT,
                max_tokens=800,
                temperature=0.7,  # Plus créatif pour les emails
            )
            
            # Parsing de la réponse
            email = _parse_email_response(response, lead, devis)
            
            logger.info(f"✅ Email généré - Sujet: {email.subject[:50]}...")
            
            return email
            
        except Exception as e:
            logger.error(f"❌ Erreur génération email: {e}")
            # Fallback vers un email basique mais personnalisé
            return self._generate_fallback_email(lead, devis)
    
    def _generate_fallback_email(self, lead: LeadRequest, devis: DevisContent) -> GeneratedEmail:
        """Génère un email de fallback si l'IA échoue."""
        
        subject = f"{lead.first_name}, votre proposition commerciale {devis.reference}"
        
        body_text = f"""Bonjour {lead.first_name},

Suite à votre demande concernant {lead.service_type.value.replace('_', ' ')}, j'ai le plaisir de vous transmettre notre proposition commerciale.

Vous trouverez ci-joint le devis détaillé pour un montant total de {devis.total_ttc:,.2f}€ TTC.

Ce devis est valable 30 jours. N'hésitez pas à me contacter pour toute question.

À très bientôt,

Juliette
Consultante nana-intelligence"""

        body_html = _convert_to_html(body_text, lead, devis)
        
        return GeneratedEmail(
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )


def get_email_generator() -> EmailGenerator:
    """Factory pour obtenir une instance du générateur d'email."""
    return EmailGenerator()
