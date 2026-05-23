import os
import re
import logging

# Configure logger
logger = logging.getLogger(__name__)

def clean_text(text):
    """
    Cleans extracted text by:
    1. Normalizing spacing (tabs/multiple spaces to single space).
    2. Normalizing multiple line breaks.
    3. Stripping empty lines and whitespace.
    """
    if not text:
        return ""
    
    # Replace multiple spaces/tabs with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Standardize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Replace three or more newlines with double newlines to separate paragraphs cleanly
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean whitespace line by line
    lines = []
    for line in text.split('\n'):
        cleaned_line = line.strip()
        # Keep lines if they are not empty
        if cleaned_line:
            lines.append(cleaned_line)
            
    return '\n'.join(lines)

def extract_text_from_pdf(pdf_path):
    """
    Extracts text page-by-page from the provided PDF file.
    
    Attempts extraction in the following order:
    1. pdfplumber (best text formatting and layout detection)
    2. pypdf (lightweight fallback)
    3. pdf2image + pytesseract (OCR for scanned/image PDFs, if dependencies are installed)
    
    Returns:
        tuple: (list of dicts containing page details like {'page': num, 'text': content}, total_characters)
    """
    pages_data = []
    total_chars = 0
    
    # Try pdfplumber first
    logger.info("Attempting PDF text extraction using pdfplumber...")
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                cleaned = clean_text(text)
                if cleaned:
                    pages_data.append({
                        'page': i + 1,
                        'text': cleaned
                    })
                    total_chars += len(cleaned)
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed or not installed: {str(e)}")
        
    # If pdfplumber extracted nothing or failed, try pypdf as fallback
    if not pages_data:
        logger.info("Attempting PDF text extraction using pypdf fallback...")
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                cleaned = clean_text(text)
                if cleaned:
                    pages_data.append({
                        'page': i + 1,
                        'text': cleaned
                    })
                    total_chars += len(cleaned)
        except Exception as e:
            logger.error(f"pypdf extraction failed: {str(e)}")
            
    # If we still have no text, check if it's a scanned PDF and attempt OCR
    if not pages_data:
        logger.info("No text extracted. Attempting OCR fallback for scanned/image PDF...")
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # This requires tesseract-ocr binary installed on system path
            images = convert_from_path(pdf_path)
            for i, img in enumerate(images):
                text = pytesseract.image_to_string(img)
                cleaned = clean_text(text)
                if cleaned:
                    pages_data.append({
                        'page': i + 1,
                        'text': cleaned
                    })
                    total_chars += len(cleaned)
            logger.info("OCR extraction completed successfully.")
        except ImportError:
            logger.warning("OCR libraries (pdf2image, pytesseract) not fully installed/available.")
        except Exception as e:
            logger.warning(f"OCR fallback failed: {str(e)}. (Ensure Tesseract-OCR is installed on the host system.)")
            
    return pages_data, total_chars
