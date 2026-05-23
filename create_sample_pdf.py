import os
import sys
import subprocess

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Package '{package}' not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Install reportlab for generating the PDF
install_and_import('reportlab')

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf():
    pdf_path = "sample_document.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        spaceAfter=12,
        textColor='#4F46E5'
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        spaceBefore=12,
        spaceAfter=8,
        textColor='#D946EF'
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        spaceAfter=10
    )
    
    story = []
    
    # Page 1
    story.append(Paragraph("VoicePDF - Test Document", title_style))
    story.append(Paragraph("This is a sample PDF document automatically generated to test the capabilities of the PDF to Audio Generator application. Below are different sections with varying text content to verify layout parsing, multi-page handling, and Text-to-Speech synthesis.", body_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("1. Technology Overview", heading_style))
    story.append(Paragraph("Text-to-Speech (TTS) technology converts written text into natural-sounding speech. Modern systems leverage neural network architectures to produce high-fidelity spoken voices with realistic inflections and pauses. By converting books, documents, and research papers into audio formats, users can consume content on-the-go, improving accessibility and learning efficiency.", body_style))
    story.append(Paragraph("This Flask-based backend combines the power of pdfplumber for semantic document parsing and gTTS (Google Text-to-Speech) for clear, cloud-generated audio synthesis. It supports multiple languages, localized accents, and playback speeds.", body_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("2. Page-by-Page Extraction Test", heading_style))
    story.append(Paragraph("This section demonstrates how the text extractor parses content. A key challenge of PDF text extraction is maintaining the flow of text across page boundaries, ignoring headers, footers, and page numbers that might interrupt a sentence. The backend cleaning routine strips extra spaces and collapses unwanted lines to ensure a smooth listening experience.", body_style))
    
    # Force Page Break to Page 2
    story.append(PageBreak())
    
    # Page 2
    story.append(Paragraph("3. Multi-Language Synthesis Check", heading_style))
    story.append(Paragraph("This is the second page of our test document. In addition to standard English, this application supports multiple international languages, such as Spanish, French, German, Italian, Portuguese, Hindi, Japanese, Russian, and Chinese. Selecting a language in the dropdown panel instructs the gTTS synthesis engine to use the corresponding phonetic rules and native speaker pronunciation models.", body_style))
    
    story.append(Paragraph("Here is a brief demonstration paragraph in Spanish to verify accent accents:", body_style))
    story.append(Paragraph("<i>La tecnología de texto a voz convierte el texto escrito en habla audible. Esta herramienta le permite escuchar sus documentos en cualquier lugar, lo que mejora la productividad y el aprendizaje.</i>", body_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("4. Chunking and Long Text Performance", heading_style))
    story.append(Paragraph("When converting long documents, the application automatically divides the text into manageable chunks of approximately 1,500 characters. This prevents timeouts and API limits, allowing users to convert lengthy books or long articles without losing their position. The audio segments are then merged seamlessly into a single downloadable MP3 file.", body_style))
    
    doc.build(story)
    print(f"Generated sample PDF at: {os.path.abspath(pdf_path)}")

if __name__ == "__main__":
    generate_pdf()
