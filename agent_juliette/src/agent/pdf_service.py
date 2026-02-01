"""
Service de génération de PDF pour les devis.
Utilise ReportLab pour créer des devis professionnels.
"""

import logging
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, 
    Paragraph, 
    Spacer, 
    Table, 
    TableStyle,
    Image,
    HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from src.models import DevisContent

logger = logging.getLogger(__name__)

# Répertoire pour stocker les PDFs générés
PDF_OUTPUT_DIR = Path("generated_pdfs")
PDF_OUTPUT_DIR.mkdir(exist_ok=True)

# Couleurs nana-intelligence (personnalisables)
COLORS = {
    "primary": colors.HexColor("#6366F1"),      # Indigo
    "secondary": colors.HexColor("#8B5CF6"),    # Violet
    "dark": colors.HexColor("#1F2937"),         # Gris foncé
    "light": colors.HexColor("#F3F4F6"),        # Gris clair
    "accent": colors.HexColor("#10B981"),       # Vert émeraude
}

# Informations de l'entreprise
COMPANY_INFO = {
    "name": "nana-intelligence",
    "tagline": "Automatisation & IA pour TPE/PME",
    "address": "France",
    "email": "contact@nana-intelligence.fr",
    "website": "https://nana-intelligence.fr",
    "siret": "",  # À compléter si nécessaire
}


class PDFService:
    """
    Service de génération de PDF pour les devis.
    Crée des documents professionnels et stylisés.
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        logger.info("PDFService initialisé")
    
    def _setup_custom_styles(self):
        """Configure les styles personnalisés pour le PDF."""
        # Titre principal
        self.styles.add(ParagraphStyle(
            name='DevisTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=COLORS["primary"],
            spaceAfter=20,
            alignment=TA_LEFT,
        ))
        
        # Sous-titre
        self.styles.add(ParagraphStyle(
            name='DevisSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=COLORS["dark"],
            spaceAfter=10,
        ))
        
        # Nom du client
        self.styles.add(ParagraphStyle(
            name='ClientName',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=COLORS["dark"],
            spaceBefore=10,
            spaceAfter=5,
        ))
        
        # Corps de texte (renommé pour éviter conflit)
        self.styles.add(ParagraphStyle(
            name='DevisBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=COLORS["dark"],
            spaceAfter=10,
            leading=16,
        ))
        
        # Texte petit (renommé pour éviter conflit)
        self.styles.add(ParagraphStyle(
            name='DevisSmall',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
        ))
        
        # En-tête de section
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=COLORS["primary"],
            spaceBefore=20,
            spaceAfter=10,
        ))
    
    def generate(self, devis: DevisContent) -> str:
        """
        Génère un PDF à partir du contenu du devis.
        
        Args:
            devis: Le contenu structuré du devis
            
        Returns:
            Le chemin absolu vers le fichier PDF généré
        """
        # Nom du fichier
        filename = f"{devis.reference}.pdf"
        filepath = PDF_OUTPUT_DIR / filename
        
        # Création du document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        # Construction du contenu
        story = []
        
        # En-tête avec infos entreprise
        story.extend(self._build_header(devis))
        
        # Informations client
        story.extend(self._build_client_info(devis))
        
        # Introduction personnalisée
        story.extend(self._build_introduction(devis))
        
        # Tableau des prestations
        story.extend(self._build_items_table(devis))
        
        # Totaux
        story.extend(self._build_totals(devis))
        
        # Conditions
        story.extend(self._build_conditions(devis))
        
        # Pied de page
        story.extend(self._build_footer())
        
        # Génération du PDF
        doc.build(story)
        
        logger.info(f"✅ PDF généré: {filepath}")
        
        return str(filepath.absolute())
    
    def _build_header(self, devis: DevisContent) -> list:
        """Construit l'en-tête du document."""
        elements = []
        
        # Tableau en-tête avec logo/nom et référence
        header_data = [
            [
                Paragraph(f"<b>{COMPANY_INFO['name']}</b>", self.styles['DevisTitle']),
                Paragraph(f"<b>DEVIS</b><br/>{devis.reference}", 
                         ParagraphStyle('ref', fontSize=12, alignment=TA_RIGHT, textColor=COLORS["dark"])),
            ],
            [
                Paragraph(COMPANY_INFO['tagline'], self.styles['DevisSmall']),
                Paragraph(f"Date: {devis.created_at.strftime('%d/%m/%Y')}<br/>Valide jusqu'au: {devis.valid_until.strftime('%d/%m/%Y')}", 
                         ParagraphStyle('dates', fontSize=10, alignment=TA_RIGHT, textColor=colors.grey)),
            ],
        ]
        
        header_table = Table(header_data, colWidths=[10*cm, 7*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Ligne de séparation
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=COLORS["primary"],
            spaceAfter=20,
        ))
        
        return elements
    
    def _build_client_info(self, devis: DevisContent) -> list:
        """Construit la section informations client."""
        elements = []
        
        elements.append(Paragraph("DESTINATAIRE", self.styles['SectionHeader']))
        
        client_info = f"<b>{devis.client_name}</b>"
        if devis.client_company:
            client_info += f"<br/>{devis.client_company}"
        client_info += f"<br/>{devis.client_email}"
        
        elements.append(Paragraph(client_info, self.styles['DevisBody']))
        elements.append(Spacer(1, 0.5*cm))
        
        return elements
    
    def _build_introduction(self, devis: DevisContent) -> list:
        """Construit l'introduction personnalisée."""
        elements = []
        
        elements.append(Paragraph("OBJET", self.styles['SectionHeader']))
        elements.append(Paragraph(f"<b>{devis.title}</b>", self.styles['DevisBody']))
        elements.append(Spacer(1, 0.3*cm))
        
        # Introduction (peut contenir plusieurs paragraphes)
        for para in devis.introduction.split('\n\n'):
            if para.strip():
                elements.append(Paragraph(para.strip(), self.styles['DevisBody']))
        
        elements.append(Spacer(1, 0.5*cm))
        
        return elements
    
    def _build_items_table(self, devis: DevisContent) -> list:
        """Construit le tableau des prestations."""
        elements = []
        
        elements.append(Paragraph("DÉTAIL DES PRESTATIONS", self.styles['SectionHeader']))
        
        # En-têtes du tableau
        table_data = [
            ['Description', 'Qté', 'Prix unitaire HT', 'Total HT'],
        ]
        
        # Lignes de prestations
        for item in devis.items:
            table_data.append([
                Paragraph(item.description, self.styles['DevisBody']),
                str(item.quantity),
                f"{item.unit_price:,.2f} €".replace(",", " "),
                f"{item.total:,.2f} €".replace(",", " "),
            ])
        
        # Création du tableau
        col_widths = [9*cm, 1.5*cm, 3*cm, 3*cm]
        items_table = Table(table_data, colWidths=col_widths)
        
        items_table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["primary"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Corps
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), COLORS["dark"]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            
            # Bordures
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["light"]),
            ('LINEBELOW', (0, 0), (-1, 0), 2, COLORS["primary"]),
            
            # Alternance de couleurs
            *[('BACKGROUND', (0, i), (-1, i), COLORS["light"]) 
              for i in range(2, len(table_data), 2)],
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 0.5*cm))
        
        return elements
    
    def _build_totals(self, devis: DevisContent) -> list:
        """Construit le bloc des totaux."""
        elements = []
        
        # Tableau des totaux aligné à droite
        totals_data = [
            ['Sous-total HT', f"{devis.subtotal:,.2f} €".replace(",", " ")],
            ['TVA (20%)', f"{devis.tva:,.2f} €".replace(",", " ")],
            ['TOTAL TTC', f"{devis.total_ttc:,.2f} €".replace(",", " ")],
        ]
        
        totals_table = Table(totals_data, colWidths=[4*cm, 3*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), COLORS["dark"]),
            
            # Ligne Total TTC en gras avec fond
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 13),
            ('BACKGROUND', (0, -1), (-1, -1), COLORS["primary"]),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('TOPPADDING', (0, -1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
            
            ('TOPPADDING', (0, 0), (-1, -2), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -2), 5),
        ]))
        
        # Wrapper pour aligner à droite
        wrapper_table = Table([[totals_table]], colWidths=[17*cm])
        wrapper_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]))
        
        elements.append(wrapper_table)
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_conditions(self, devis: DevisContent) -> list:
        """Construit la section des conditions."""
        elements = []
        
        elements.append(Paragraph("CONDITIONS", self.styles['SectionHeader']))
        elements.append(Paragraph(devis.conditions, self.styles['DevisBody']))
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_footer(self) -> list:
        """Construit le pied de page."""
        elements = []
        
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=COLORS["light"],
            spaceBefore=20,
            spaceAfter=10,
        ))
        
        footer_text = f"""
        <b>{COMPANY_INFO['name']}</b> | {COMPANY_INFO['email']} | {COMPANY_INFO['website']}
        """
        
        elements.append(Paragraph(
            footer_text.strip(),
            ParagraphStyle('footer', fontSize=9, alignment=TA_CENTER, textColor=colors.grey)
        ))
        
        return elements


def get_pdf_service() -> PDFService:
    """Factory pour obtenir une instance du service PDF."""
    return PDFService()
