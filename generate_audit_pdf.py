#!/usr/bin/env python3
"""Génère un PDF simple à partir du fichier AUDIT_CHANGES_REPORT.md

Usage:
    python3 generate_audit_pdf.py
"""
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import os
import logging
logger = logging.getLogger(__name__)

MD_FILE = 'AUDIT_CHANGES_REPORT.md'
OUT_PDF = 'AUDIT_CHANGES_REPORT.pdf'

def md_to_pdf(md_path, out_pdf):
    if not os.path.exists(md_path):
        logger.info(f'Markdown introuvable: {md_path}')
        return False

    with open(md_path, 'r', encoding='utf-8') as f:
        text = f.read()

    styles = getSampleStyleSheet()
    story = []

    for line in text.splitlines():
        if line.strip().startswith('# '):
            story.append(Paragraph(line.strip().lstrip('# ').strip(), styles['Title']))
        elif line.strip().startswith('## '):
            story.append(Paragraph(line.strip().lstrip('#').strip(), styles['Heading2']))
        elif line.strip().startswith('- '):
            story.append(Paragraph(line.strip().lstrip('- ').strip(), styles['Normal']))
        elif line.strip() == '':
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(line.strip(), styles['Normal']))

    doc = SimpleDocTemplate(out_pdf, pagesize=A4)
    doc.build(story)
    logger.info(f'PDF généré: {out_pdf}')
    return True

if __name__ == '__main__':
    md_to_pdf(MD_FILE, OUT_PDF)
