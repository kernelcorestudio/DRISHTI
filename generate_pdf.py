import json
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

TRANSCRIPT_PATH = r'C:\Users\Karan Nayal\.gemini\antigravity-ide\brain\ff86f415-3430-4b7b-a326-1809f26a9506\.system_generated\logs\transcript.jsonl'
OUTPUT_PATH = r'C:\Users\Karan Nayal\.gemini\antigravity-ide\brain\ff86f415-3430-4b7b-a326-1809f26a9506\RAHAT_Conversation.pdf'

# Parse transcript
messages = []
with open(TRANSCRIPT_PATH, encoding='utf-8') as f:
    for line in f:
        try:
            step = json.loads(line.strip())
            step_type = step.get('type', '')
            source = step.get('source', '')
            content = step.get('content', '')

            if step_type == 'USER_INPUT' and content and content.strip():
                # Clean content
                text = content.strip()
                if text and len(text) > 2:
                    messages.append(('USER', text))

            elif step_type == 'PLANNER_RESPONSE' and content and content.strip():
                text = content.strip()
                # Remove tool call JSON noise
                if text and len(text) > 10 and not text.startswith('{'):
                    messages.append(('AI', text))
        except:
            continue

print(f"Extracted {len(messages)} messages")

# Build PDF
doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2.5*cm,
    bottomMargin=2*cm
)

styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    'Title',
    parent=styles['Title'],
    fontSize=22,
    textColor=colors.HexColor('#1a1a2e'),
    spaceAfter=6,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

subtitle_style = ParagraphStyle(
    'Subtitle',
    parent=styles['Normal'],
    fontSize=11,
    textColor=colors.HexColor('#666666'),
    spaceAfter=20,
    alignment=TA_CENTER,
    fontName='Helvetica'
)

user_label_style = ParagraphStyle(
    'UserLabel',
    parent=styles['Normal'],
    fontSize=9,
    textColor=colors.HexColor('#ffffff'),
    fontName='Helvetica-Bold',
    leftIndent=0,
    spaceBefore=14
)

ai_label_style = ParagraphStyle(
    'AILabel',
    parent=styles['Normal'],
    fontSize=9,
    textColor=colors.HexColor('#ffffff'),
    fontName='Helvetica-Bold',
    leftIndent=0,
    spaceBefore=14
)

user_text_style = ParagraphStyle(
    'UserText',
    parent=styles['Normal'],
    fontSize=10,
    textColor=colors.HexColor('#1a1a2e'),
    fontName='Helvetica',
    leftIndent=10,
    rightIndent=10,
    spaceBefore=4,
    spaceAfter=4,
    leading=15
)

ai_text_style = ParagraphStyle(
    'AIText',
    parent=styles['Normal'],
    fontSize=10,
    textColor=colors.HexColor('#1a1a1a'),
    fontName='Helvetica',
    leftIndent=10,
    rightIndent=10,
    spaceBefore=4,
    spaceAfter=4,
    leading=15
)

def clean_text(text):
    # Remove markdown bold/italic markers for PDF
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'#{1,6}\s*(.+)', r'<b>\1</b>', text)
    # Remove backticks
    text = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
    # Escape XML chars
    text = text.replace('&', '&amp;').replace('<b>', '\x00B\x00').replace('</b>', '\x00/B\x00')
    text = text.replace('<i>', '\x00I\x00').replace('</i>', '\x00/I\x00')
    text = text.replace('<font name="Courier">', '\x00F\x00').replace('</font>', '\x00/F\x00')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('\x00B\x00', '<b>').replace('\x00/B\x00', '</b>')
    text = text.replace('\x00I\x00', '<i>').replace('\x00/I\x00', '</i>')
    text = text.replace('\x00F\x00', '<font name="Courier">').replace('\x00/F\x00', '</font>')
    return text

story = []

# Title
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("RAHAT Project", title_style))
story.append(Paragraph("Complete Conversation — DisaVu Analysis & RAHAT Study Guide", subtitle_style))
story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a1a2e'), spaceAfter=20))
story.append(Spacer(1, 0.3*cm))

# Messages
for i, (role, text) in enumerate(messages):
    if role == 'USER':
        # User bubble header
        data = [[Paragraph(f'  🧑 YOU — Message {i//2 + 1}', ParagraphStyle('UL', parent=styles['Normal'], fontSize=9, textColor=colors.white, fontName='Helvetica-Bold'))]]
        t = Table(data, colWidths=[16*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#2563eb')),
            ('ROUNDEDCORNERS', [5,5,5,5]),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)

        # User text
        for line in text.split('\n'):
            line = line.strip()
            if line:
                try:
                    story.append(Paragraph(clean_text(line), user_text_style))
                except:
                    story.append(Paragraph(line[:500], user_text_style))

        story.append(Spacer(1, 4))

    else:
        # AI bubble header
        data = [[Paragraph('  🤖 ANTIGRAVITY (AI)', ParagraphStyle('AL', parent=styles['Normal'], fontSize=9, textColor=colors.white, fontName='Helvetica-Bold'))]]
        t = Table(data, colWidths=[16*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#059669')),
            ('ROUNDEDCORNERS', [5,5,5,5]),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)

        # AI text - split by lines
        for line in text.split('\n'):
            line = line.strip()
            if line:
                try:
                    story.append(Paragraph(clean_text(line), ai_text_style))
                except:
                    story.append(Paragraph(line[:500], ai_text_style))

        story.append(Spacer(1, 4))

    # Divider every 10 messages
    if i % 10 == 9:
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e5e7eb'), spaceAfter=5))

# Footer
story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a1a2e')))
story.append(Paragraph("Generated by Antigravity AI | RAHAT Project Study Guide | SIH 2025", subtitle_style))

doc.build(story)
print(f"PDF created at: {OUTPUT_PATH}")
