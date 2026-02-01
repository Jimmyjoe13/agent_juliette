"""
Service d'intégration Gmail.
Gère l'authentification OAuth2 et la création de brouillons avec pièces jointes.
"""

import base64
import logging
import os
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import get_settings

logger = logging.getLogger(__name__)

# Scopes requis pour créer des brouillons
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']


class GmailService:
    """
    Service pour interagir avec l'API Gmail.
    Gère l'authentification OAuth2 et la création de brouillons.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.credentials_path = Path(self.settings.gmail_credentials_path)
        self.token_path = Path(self.settings.gmail_token_path)
        self.sender_email = self.settings.gmail_sender_email
        self.service = None
        self._authenticated = False
        
        logger.info(f"GmailService initialisé (sender: {self.sender_email})")
    
    def _authenticate(self) -> bool:
        """
        Gère l'authentification OAuth2.
        
        Returns:
            True si l'authentification a réussi
        """
        if self._authenticated and self.service:
            return True
        
        creds = None
        
        # Charger le token existant
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
                logger.debug("Token existant chargé")
            except Exception as e:
                logger.warning(f"Erreur chargement token: {e}")
        
        # Rafraîchir ou créer les credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Token rafraîchi avec succès")
                except Exception as e:
                    logger.warning(f"Erreur rafraîchissement token: {e}")
                    creds = None
            
            if not creds:
                if not self.credentials_path.exists():
                    logger.error(f"Fichier credentials non trouvé: {self.credentials_path}")
                    return False
                
                # Lancer le flux OAuth2 (nécessite interaction utilisateur)
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Nouvelle authentification OAuth2 réussie")
            
            # Sauvegarder le token
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
                logger.debug(f"Token sauvegardé: {self.token_path}")
        
        # Créer le service Gmail
        self.service = build('gmail', 'v1', credentials=creds)
        self._authenticated = True
        
        return True
    
    def create_draft(
        self,
        to: str,
        subject: str,
        body_html: str,
        attachment_path: str | None = None,
    ) -> dict:
        """
        Crée un brouillon d'email dans Gmail.
        
        Args:
            to: Adresse email du destinataire
            subject: Sujet de l'email
            body_html: Corps de l'email en HTML
            attachment_path: Chemin vers le fichier à joindre (optionnel)
            
        Returns:
            dict avec 'draft_id' et 'message_id'
        """
        if not self._authenticate():
            raise RuntimeError("Authentification Gmail échouée")
        
        # Création du message MIME
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = self.sender_email
        message['subject'] = subject
        
        # Corps HTML
        html_part = MIMEText(body_html, 'html', 'utf-8')
        message.attach(html_part)
        
        # Pièce jointe
        if attachment_path:
            attachment_path = Path(attachment_path)
            if attachment_path.exists():
                with open(attachment_path, 'rb') as f:
                    attachment = MIMEBase('application', 'pdf')
                    attachment.set_payload(f.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{attachment_path.name}"'
                    )
                    message.attach(attachment)
                    logger.debug(f"Pièce jointe ajoutée: {attachment_path.name}")
            else:
                logger.warning(f"Pièce jointe non trouvée: {attachment_path}")
        
        # Encodage du message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Création du brouillon
        try:
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            draft_id = draft['id']
            message_id = draft['message']['id']
            
            logger.info(f"✅ Brouillon créé: {draft_id}")
            
            return {
                'draft_id': draft_id,
                'message_id': message_id,
                'to': to,
                'subject': subject,
            }
            
        except HttpError as e:
            logger.error(f"Erreur création brouillon: {e}")
            raise
    
    def create_devis_draft(
        self,
        client_name: str,
        client_email: str,
        devis_reference: str,
        devis_title: str,
        total_ttc: float,
        pdf_path: str,
    ) -> dict:
        """
        Crée un brouillon avec le template email pour un devis.
        
        Args:
            client_name: Nom du client
            client_email: Email du client
            devis_reference: Référence du devis
            devis_title: Titre du devis
            total_ttc: Montant total TTC
            pdf_path: Chemin vers le PDF du devis
            
        Returns:
            dict avec les informations du brouillon créé
        """
        subject = f"Votre devis {devis_reference} - nana-intelligence"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #1F2937;
                    max-width: 600px;
                    margin: 0 auto;
                }}
                .header {{
                    background: linear-gradient(135deg, #6366F1, #8B5CF6);
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .header h1 {{
                    color: white;
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    padding: 30px;
                    background: #ffffff;
                    border: 1px solid #E5E7EB;
                }}
                .highlight {{
                    background: #F3F4F6;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .total {{
                    font-size: 24px;
                    color: #6366F1;
                    font-weight: bold;
                }}
                .footer {{
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #6B7280;
                    background: #F9FAFB;
                    border-radius: 0 0 10px 10px;
                }}
                .cta {{
                    display: inline-block;
                    background: #6366F1;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 6px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>nana-intelligence</h1>
            </div>
            
            <div class="content">
                <p>Bonjour <strong>{client_name}</strong>,</p>
                
                <p>Suite à votre demande, j'ai le plaisir de vous transmettre notre proposition commerciale.</p>
                
                <div class="highlight">
                    <p><strong>📄 Devis n° {devis_reference}</strong></p>
                    <p>{devis_title}</p>
                    <p class="total">Total TTC : {total_ttc:,.2f} €</p>
                </div>
                
                <p>Vous trouverez le devis détaillé en pièce jointe de cet email au format PDF.</p>
                
                <p>Ce devis est valable 30 jours. N'hésitez pas à me contacter si vous avez des questions ou si vous souhaitez ajuster certains éléments.</p>
                
                <p>Je reste à votre disposition pour échanger sur votre projet.</p>
                
                <p>
                    Cordialement,<br>
                    <strong>L'équipe nana-intelligence</strong>
                </p>
            </div>
            
            <div class="footer">
                <p>nana-intelligence | Automatisation & IA pour TPE/PME</p>
                <p>contact@nana-intelligence.fr | https://nana-intelligence.fr</p>
            </div>
        </body>
        </html>
        """
        
        return self.create_draft(
            to=client_email,
            subject=subject,
            body_html=body_html,
            attachment_path=pdf_path,
        )
    
    def is_configured(self) -> bool:
        """
        Vérifie si le service Gmail est correctement configuré.
        
        Retourne True si:
        - Le fichier credentials.json existe ET est un client OAuth2 (pas service account)
        - OU si un token.json existe déjà
        """
        # Si on a déjà un token, c'est bon
        if self.token_path.exists():
            return True
        
        # Sinon, vérifier le fichier credentials
        if not self.credentials_path.exists():
            return False
        
        # Vérifier que c'est bien un client OAuth2, pas un service account
        try:
            import json
            with open(self.credentials_path, 'r') as f:
                creds_data = json.load(f)
            
            # Les service accounts ont "type": "service_account"
            if creds_data.get("type") == "service_account":
                logger.warning(
                    "Le fichier credentials.json est un compte de service. "
                    "Pour Gmail, vous devez créer un client OAuth2 (Desktop app) "
                    "via Google Cloud Console > APIs & Services > Credentials > "
                    "+ CREATE CREDENTIALS > OAuth client ID > Desktop application"
                )
                return False
            
            # Les clients OAuth2 ont "installed" ou "web"
            if "installed" in creds_data or "web" in creds_data:
                return True
            
            logger.warning(f"Format credentials.json non reconnu")
            return False
            
        except Exception as e:
            logger.warning(f"Erreur lecture credentials.json: {e}")
            return False


def get_gmail_service() -> GmailService:
    """Factory pour obtenir une instance du service Gmail."""
    return GmailService()
