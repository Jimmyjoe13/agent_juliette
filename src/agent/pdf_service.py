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

# Chemin du logo
LOGO_PATH = Path(r"C:\Users\jimmy\Projet\agent_juliette\img\logo-nana.png")

# Couleurs nana-intelligence
COLORS = {
    "primary": colors.HexColor("#6366F1"),      # Indigo
    "secondary": colors.HexColor("#8B5CF6"),    # Violet
    "dark": colors.HexColor("#111827"),         # Gris très foncé
    "medium": colors.HexColor("#4B5563"),       # Gris moyen
    "light": colors.HexColor("#F9FAFB"),        # Gris ultra clair
    "accent": colors.HexColor("#10B981"),       # Vert émeraude
    "border": colors.HexColor("#E5E7EB"),       # Bordures
}

# Informations de l'entreprise
COMPANY_INFO = {
    "name": "nana-intelligence",
    "tagline": "Automatisation & IA pour TPE/PME",
    "address": "France",
    "email": "contact@nana-intelligence.fr",
    "website": "nana-intelligence.fr",
    "siret": "",
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
            fontSize=28,
            textColor=COLORS["primary"],
            spaceAfter=5,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
        ))
        
        # Sous-titre (Référence)
        self.styles.add(ParagraphStyle(
            name='DevisRef',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=COLORS["medium"],
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold',
        ))
        
        # En-tête de section
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=11,
            textColor=COLORS["primary"],
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold',
            textTransform='uppercase',
        ))
        
        # Corps de texte standard
        self.styles.add(ParagraphStyle(
            name='DevisBody',
            parent=self.styles['Normal'],
            fontSize=10.5,
            textColor=COLORS["dark"],
            leading=15,
            spaceAfter=8,
        ))
        
        # Détails des prestations (petit texte)
        self.styles.add(ParagraphStyle(
            name='ItemDetails',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=COLORS["medium"],
            leading=12,
            leftIndent=0,
        ))
        
        # Styles pour le tableau
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.white,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
        ))
        
        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=COLORS["dark"],
            alignment=TA_LEFT,
        ))
    
    def generate(self, devis: DevisContent) -> str:
        """
        Génère un PDF à partir du contenu du devis.
        """
        filename = f"{devis.reference}.pdf"
        filepath = PDF_OUTPUT_DIR / filename
        
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm,
        )
        
        story = []
        
        # 1. En-tête (Logo + Infos Entreprise + Ref)
        story.extend(self._build_header(devis))
        
        # 2. Client & Infos Devis
        story.extend(self._build_info_block(devis))
        
        # 3. Objet & Introduction
        story.extend(self._build_introduction(devis))
        
        # 4. Tableau des prestations
        story.extend(self._build_items_table(devis))
        
        # 5. Totaux
        story.extend(self._build_totals(devis))
        
        # 6. Conditions
        story.extend(self._build_conditions(devis))
        
        # 7. Signature (Espace pour signature client)
        story.extend(self._build_signature_block())
        
        # 8. Footer (Pied de page automatique)
        # Note: ReportLab supporte les canvas pour les footers répétitifs, 
        # ici on le met à la fin pour rester simple.
        story.extend(self._build_footer())
        
        # Génération
        doc.build(story)
        
        logger.info(f"✅ PDF généré: {filepath}")
        return str(filepath.absolute())
    
    def _build_header(self, devis: DevisContent) -> list:
        """Construit l'en-tête avec logo et référence."""
        elements = []
        
        logo = None
        if LOGO_PATH.exists():
            try:
                logo = Image(str(LOGO_PATH), width=4*cm, height=1.2*cm, kind='proportional')
                logo.hAlign = 'LEFT'
            except Exception as e:
                logger.error(f"Erreur chargement logo: {e}")
        
        # Tableau en-tête
        left_header = []
        if logo:
            left_header.append(logo)
        else:
            left_header.append(Paragraph(COMPANY_INFO['name'], self.styles['DevisTitle']))
        
        left_header.append(Paragraph(COMPANY_INFO['tagline'], 
                                   ParagraphStyle('tag', fontSize=9, textColor=COLORS["medium"])))
        
        right_header = [
            Paragraph(f"<b>DEVIS #{devis.reference}</b>", self.styles['DevisRef']),
            Paragraph(f"Date: {devis.created_at.strftime('%d/%m/%Y')}", 
                     ParagraphStyle('d', fontSize=10, alignment=TA_RIGHT, textColor=COLORS["medium"])),
            Paragraph(f"Validité: {devis.valid_until.strftime('%d/%m/%Y')} (30j)", 
                     ParagraphStyle('v', fontSize=10, alignment=TA_RIGHT, textColor=COLORS["medium"])),
        ]
        
        header_table = Table([
            [left_header, right_header]
        ], colWidths=[10*cm, 8*cm])
        
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_info_block(self, devis: DevisContent) -> list:
        """Bloc avec infos émetteur et destinataire."""
        elements = []
        
        # Émetteur
        emitter = [
            Paragraph("ÉMETTEUR", self.styles['SectionHeader']),
            Paragraph(f"<b>{COMPANY_INFO['name']}</b>", self.styles['DevisBody']),
            Paragraph(f"{COMPANY_INFO['email']}", ParagraphStyle('e', fontSize=10, textColor=COLORS["medium"])),
            Paragraph(f"{COMPANY_INFO['website']}", ParagraphStyle('w', fontSize=10, textColor=COLORS["medium"])),
        ]
        
        # Destinataire
        receiver_elements = [
            Paragraph("DESTINATAIRE", self.styles['SectionHeader']),
            Paragraph(f"<b>{devis.client_name}</b>", self.styles['DevisBody']),
        ]
        if devis.client_company:
            receiver_elements.append(Paragraph(devis.client_company, self.styles['DevisBody']))
        
        receiver_elements.append(Paragraph(f"{devis.client_email}", ParagraphStyle('e', fontSize=10, textColor=COLORS["medium"])))

        info_table = Table([
            [emitter, receiver_elements]
        ], colWidths=[9*cm, 9*cm])
        
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_introduction(self, devis: DevisContent) -> list:
        """Section objet et intro."""
        elements = []
        
        # Fond coloré pour l'objet
        title_table = Table([[Paragraph(f"OBJET : {devis.title}", 
                                      ParagraphStyle('t', fontSize=12, fontName='Helvetica-Bold', textColor=colors.white))]],
                           colWidths=[18*cm])
        title_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLORS["primary"]),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(title_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Introduction
        for para in devis.introduction.split('\n\n'):
            if para.strip():
                elements.append(Paragraph(para.strip(), self.styles['DevisBody']))
        
        elements.append(Spacer(1, 0.6*cm))
        return elements
    
    def _build_items_table(self, devis: DevisContent) -> list:
        """Tableau détaillé avec livrables."""
        elements = []
        
        elements.append(Paragraph("DÉTAIL DES PRESTATIONS", self.styles['SectionHeader']))
        
        # En-têtes
        table_data = [
            [
                Paragraph("<b>Prestation & Livrables</b>", self.styles['TableHeader']),
                Paragraph("<b>Qté</b>", self.styles['TableHeader']),
                Paragraph("<b>P.U. HT</b>", self.styles['TableHeader']),
                Paragraph("<b>Total HT</b>", self.styles['TableHeader'])
            ]
        ]
        
        # Lignes
        for item in devis.items:
            # Cellule description + détails
            desc_cell = [
                Paragraph(f"<b>{item.description}</b>", self.styles['TableCell']),
            ]
            if item.details:
                desc_cell.append(Spacer(1, 1*mm))
                desc_cell.append(Paragraph(item.details, self.styles['ItemDetails']))
            
            table_data.append([
                desc_cell,
                Paragraph(str(item.quantity), ParagraphStyle('q', fontSize=10, alignment=TA_CENTER)),
                Paragraph(f"{item.unit_price:,.2f} €".replace(",", " "), ParagraphStyle('p', fontSize=10, alignment=TA_RIGHT)),
                Paragraph(f"{item.total:,.2f} €".replace(",", " "), ParagraphStyle('t', fontSize=10, alignment=TA_RIGHT, fontName='Helvetica-Bold')),
            ])
            
        col_widths = [10.5*cm, 1.5*cm, 3*cm, 3*cm]
        items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        items_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["primary"]),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Corps
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 12),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, COLORS["border"]),
            
            # Bordures extérieures
            ('BOX', (0, 0), (-1, -1), 1, COLORS["primary"]),
            
            # Alternance de gris très léger
            *[('BACKGROUND', (0, i), (-1, i), COLORS["light"]) 
              for i in range(2, len(table_data), 2)],
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 0.6*cm))
        
        return elements
    
    def _build_totals(self, devis: DevisContent) -> list:
        """Bloc totaux stylisé."""
        elements = []
        
        totals_data = [
            [Paragraph("Sous-total HT", self.styles['DevisBody']), 
             Paragraph(f"{devis.subtotal:,.2f} €".replace(",", " "), ParagraphStyle('v', alignment=TA_RIGHT, fontSize=11))],
            [Paragraph("TVA (20%)", self.styles['DevisBody']), 
             Paragraph(f"{devis.tva:,.2f} €".replace(",", " "), ParagraphStyle('v', alignment=TA_RIGHT, fontSize=11))],
            [Paragraph("<b>TOTAL TTC</b>", ParagraphStyle('lb', fontSize=14, fontName='Helvetica-Bold', textColor=colors.white)), 
             Paragraph(f"<b>{devis.total_ttc:,.2f} €</b>".replace(",", " "), ParagraphStyle('vb', alignment=TA_RIGHT, fontSize=16, fontName='Helvetica-Bold', textColor=colors.white))],
        ]
        
        totals_table = Table(totals_data, colWidths=[4*cm, 4*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Ligne de séparation
            ('LINEBELOW', (0, 0), (1, 0), 0.5, COLORS["border"]),
            ('LINEBELOW', (0, 1), (1, 1), 0.5, COLORS["border"]),
            
            # Style du total TTC
            ('BACKGROUND', (0, 2), (1, 2), COLORS["primary"]),
            ('TOPPADDING', (0, 2), (1, 2), 12),
            ('BOTTOMPADDING', (0, 2), (1, 2), 12),
            ('LEFTPADDING', (0, 2), (0, 2), 15),
            ('RIGHTPADDING', (1, 2), (1, 2), 15),
        ]))
        
        # Aligné à droite
        elements.append(Table([[Spacer(1, 1), totals_table]], colWidths=[10*cm, 8*cm]))
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_conditions(self, devis: DevisContent) -> list:
        """Section conditions."""
        elements = []
        elements.append(Paragraph("CONDITIONS DE RÈGLEMENT & VALIDITÉ", self.styles['SectionHeader']))
        elements.append(Paragraph(devis.conditions, ParagraphStyle('c', fontSize=9.5, textColor=COLORS["medium"], leading=14)))
        elements.append(Spacer(1, 1*cm))
        return elements
    
    def _build_signature_block(self) -> list:
        """Bloc pour signature."""
        elements = []
        
        sig_data = [
            [Paragraph("Pour nana-intelligence", self.styles['SectionHeader']), 
             Paragraph("Pour le Client (Bon pour accord)", self.styles['SectionHeader'])],
            [Paragraph("<i>Signature életronique certifiée</i>", ParagraphStyle('s', fontSize=8, textColor=colors.grey)), 
             Spacer(1, 2.5*cm)]
        ]
        
        sig_table = Table(sig_data, colWidths=[9*cm, 9*cm])
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (1, 0), (1, 1), 0.5, COLORS["border"]), # Cadre pour signature client
        ]))
        
        elements.append(sig_table)
        return elements
    
    def _build_footer(self) -> list:
        """Pied de page final."""
        elements = []
        elements.append(Spacer(1, 1.5*cm))
        
        footer_text = f"<b>{COMPANY_INFO['name']}</b> | {COMPANY_INFO['email']} | {COMPANY_INFO['website']}"
        elements.append(Paragraph(footer_text, ParagraphStyle('footer', fontSize=8, alignment=TA_CENTER, textColor=colors.grey)))
        
        return elements


def get_pdf_service() -> PDFService:
    """Factory pour obtenir une instance du service PDF."""
    return PDFService()
