import os
import time
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from utils.pdf_processor import extract_text_from_pdf
from utils.tts_processor import text_to_speech, get_languages_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Application Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
AUDIO_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 15 * 1024 * 1024  # 15 MB limit

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure required directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Checks if the uploaded file has a permitted extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """
    Deletes files in upload and audio directories older than 1 hour.
    Prevents storage buildup on server environments.
    """
    now = time.time()
    one_hour_ago = now - 3600
    
    for folder in [UPLOAD_FOLDER, AUDIO_FOLDER]:
        if not os.path.exists(folder):
            continue
        for filename in os.listdir(folder):
            # Keep gitkeep placeholders if present
            if filename == '.gitkeep':
                continue
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime < one_hour_ago:
                        os.remove(file_path)
                        logger.info(f"Deleted expired file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting expired file {file_path}: {str(e)}")

# --- Flask Error Handlers ---
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'error': 'File is too large. Maximum size allowed is 15MB.'
    }), 413

# --- REST APIs ---

@app.route('/')
def index():
    """Serves the main single-page application dashboard."""
    return render_template('index.html')

@app.route('/api/languages', methods=['GET'])
def get_languages():
    """API endpoint to fetch supported TTS languages and accents."""
    return jsonify(get_languages_config())

@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """
    Upload API:
    - Receives a PDF file.
    - Validates extension, structure, and size.
    - Saves the file safely using secure_filename.
    - Extracts basic metadata (number of pages, character count) and a text preview.
    """
    # Clean up expired files periodically on requests
    cleanup_old_files()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type. Only PDF files (.pdf) are allowed.'}), 400
        
    try:
        # Secure and generate unique filename to avoid collision
        filename = secure_filename(file.filename)
        base, ext = os.path.splitext(filename)
        unique_filename = f"{base}_{int(time.time())}{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        file.save(file_path)
        logger.info(f"PDF saved successfully: {unique_filename}")
        
        # Perform quick parsing to return metadata & preview
        pages_data, total_chars = extract_text_from_pdf(file_path)
        
        if not pages_data:
            # File is empty or not parseable
            os.remove(file_path)
            return jsonify({
                'error': 'The PDF file appears to be empty, encrypted, or holds no extractable text. If it is a scanned image, please ensure OCR is configured.'
            }), 422
            
        # Create preview of the first few pages
        preview = ""
        for page in pages_data[:2]:
            preview += f"--- Page {page['page']} ---\n{page['text'][:400]}...\n\n"
            
        return jsonify({
            'success': True,
            'filename': unique_filename,
            'original_filename': file.filename,
            'pages_count': len(pages_data),
            'characters_count': total_chars,
            'preview': preview
        })
        
    except Exception as e:
        logger.exception("Upload processing failed")
        return jsonify({'error': f"Failed to upload and parse PDF: {str(e)}"}), 500

@app.route('/api/convert', methods=['POST'])
def convert_pdf_to_audio():
    """
    Convert API:
    - Triggers PDF text extraction.
    - Passes text to TTS system based on requested parameters.
    - Saves generated audio.
    - Returns URL paths to stream and download the audio.
    """
    cleanup_old_files()
    
    data = request.get_json() or {}
    filename = data.get('filename')
    lang = data.get('lang', 'en')
    tld = data.get('tld', 'com')
    slow = data.get('slow', False)
    
    if not filename:
        return jsonify({'error': 'Filename is required for conversion'}), 400
        
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'PDF file not found. It may have expired or been deleted.'}), 404
        
    try:
        # 1. Extract Full Text
        pages_data, total_chars = extract_text_from_pdf(pdf_path)
        if not pages_data:
            return jsonify({'error': 'No text could be extracted from this PDF.'}), 422
            
        # Join text from all pages
        full_text = "\n\n".join([page['text'] for page in pages_data])
        
        # 2. Setup Audio Output Filename
        base, _ = os.path.splitext(filename)
        audio_filename = f"{base}_{lang}_{tld}.mp3"
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
        
        # 3. Call text-to-speech converter
        text_to_speech(full_text, audio_path, lang=lang, tld=tld, slow=slow)
        
        return jsonify({
            'success': True,
            'filename': audio_filename,
            'audio_url': f"/api/audio/{audio_filename}",
            'download_url': f"/api/download/{audio_filename}"
        })
        
    except Exception as e:
        logger.exception("Text-to-speech conversion failed")
        return jsonify({'error': f"Failed to convert PDF to Audio: {str(e)}"}), 500

@app.route('/api/audio/<filename>', methods=['GET'])
def stream_audio(filename):
    """Streams the generated audio file to the browser."""
    # Prevent directory traversal attacks by securing filename
    filename = secure_filename(filename)
    audio_path = os.path.join(app.config['AUDIO_FOLDER'], filename)
    
    if not os.path.exists(audio_path):
        return jsonify({'error': 'Audio file not found or has expired.'}), 404
        
    return send_from_directory(app.config['AUDIO_FOLDER'], filename)

@app.route('/api/download/<filename>', methods=['GET'])
def download_audio(filename):
    """Forces the download of the generated audio file."""
    # Prevent directory traversal attacks by securing filename
    filename = secure_filename(filename)
    audio_path = os.path.join(app.config['AUDIO_FOLDER'], filename)
    
    if not os.path.exists(audio_path):
        return jsonify({'error': 'Audio file not found or has expired.'}), 404
        
    return send_from_directory(
        app.config['AUDIO_FOLDER'], 
        filename, 
        as_attachment=True,
        download_name=f"pdf_audio_{filename}"
    )

if __name__ == '__main__':
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
