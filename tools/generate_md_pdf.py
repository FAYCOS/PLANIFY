#!/usr/bin/env python3
"""Convertit un fichier Markdown en PDF simple.

Usage:
    python3 tools/generate_md_pdf.py input.md output.pdf
"""
import sys
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


def md_to_pdf(md_path, out_pdf):
    if not os.path.exists(md_path):
        print(f"Markdown introuvable: {md_path}")
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
            story.append(Paragraph('• ' + line.strip().lstrip('- ').strip(), styles['Normal']))
        elif line.strip() == '':
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(line.strip(), styles['Normal']))

    doc = SimpleDocTemplate(out_pdf, pagesize=A4)
    doc.build(story)
    print(f'PDF généré: {out_pdf}')
    return True


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python3 tools/generate_md_pdf.py input.md output.pdf')
        sys.exit(2)
    md_in = sys.argv[1]
    out_pdf = sys.argv[2]
    success = md_to_pdf(md_in, out_pdf)
    sys.exit(0 if success else 1)
