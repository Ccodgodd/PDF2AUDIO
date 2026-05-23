import os
import re
import tempfile
import logging
from gtts import gTTS

# Configure logger
logger = logging.getLogger(__name__)

# Dictionary of supported languages and localized accents (using gTTS TLDs)
SUPPORTED_LANGUAGES = {
    'en': {
        'name': 'English',
        'accents': {
            'com': 'United States',
            'co.uk': 'United Kingdom',
            'ca': 'Canada',
            'co.in': 'India',
            'com.au': 'Australia',
            'co.za': 'South Africa',
            'ie': 'Ireland'
        }
    },
    'es': {
        'name': 'Spanish',
        'accents': {
            'com': 'Spain',
            'com.mx': 'Mexico'
        }
    },
    'fr': {
        'name': 'French',
        'accents': {
            'fr': 'France',
            'ca': 'Canada'
        }
    },
    'de': {
        'name': 'German',
        'accents': {
            'de': 'Germany'
        }
    },
    'it': {
        'name': 'Italian',
        'accents': {
            'it': 'Italy'
        }
    },
    'pt': {
        'name': 'Portuguese',
        'accents': {
            'pt': 'Portugal',
            'com.br': 'Brazil'
        }
    },
    'hi': {
        'name': 'Hindi',
        'accents': {
            'co.in': 'India'
        }
    },
    'ja': {
        'name': 'Japanese',
        'accents': {
            'co.jp': 'Japan'
        }
    },
    'zh-CN': {
        'name': 'Chinese (Simplified)',
        'accents': {
            'com': 'China'
        }
    },
    'ru': {
        'name': 'Russian',
        'accents': {
            'ru': 'Russia'
        }
    }
}

def get_languages_config():
    """Returns the list of supported languages and accents for the UI."""
    return SUPPORTED_LANGUAGES

def split_text_into_chunks(text, max_chars=1500):
    """
    Splits text into chunks of maximum max_chars.
    Attempts to split at sentence boundaries to avoid jarring cuts in audio.
    """
    if not text:
        return []
        
    # Split text into sentences using punctuation lookbehind
    sentences = re.split(r'(?<=[.?!])\s+', text)
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # If a single sentence exceeds the maximum chunk size, we force-split it by spaces
        if len(sentence) > max_chars:
            # First dump current chunk if it exists
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
                
            # Split the giant sentence by spaces
            words = sentence.split(" ")
            temp_chunk = []
            temp_len = 0
            for word in words:
                if temp_len + len(word) + 1 > max_chars:
                    if temp_chunk:
                        chunks.append(" ".join(temp_chunk))
                    temp_chunk = [word]
                    temp_len = len(word)
                else:
                    temp_chunk.append(word)
                    temp_len += len(word) + 1
            if temp_chunk:
                current_chunk = temp_chunk
                current_length = temp_len
        else:
            # If adding this sentence exceeds maximum chunk size, save current chunk and start a new one
            if current_length + len(sentence) + 1 > max_chars:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = len(sentence)
            else:
                current_chunk.append(sentence)
                current_length += len(sentence) + 1
                
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def text_to_speech(text, output_file_path, lang='en', tld='com', slow=False):
    """
    Converts text to speech and saves it as an MP3 file.
    Handles long text by chunking, generating temporary MP3s, and merging them.
    
    Parameters:
        text (str): The full text to convert.
        output_file_path (str): The destination path for the final MP3 file.
        lang (str): Language code (e.g., 'en').
        tld (str): Top-level domain for accents (e.g., 'co.uk').
        slow (bool): Generate slow speech if True.
    """
    logger.info(f"Converting text to speech (lang={lang}, tld={tld}, slow={slow})...")
    
    # Split text into chunks to prevent gTTS errors and timeouts
    chunks = split_text_into_chunks(text, max_chars=1500)
    if not chunks:
        raise ValueError("No text provided for conversion.")
        
    logger.info(f"Text split into {len(chunks)} chunks for TTS generation.")
    
    temp_files = []
    
    try:
        # Generate audio for each chunk in a temporary file
        for idx, chunk in enumerate(chunks):
            logger.info(f"Generating audio for chunk {idx+1}/{len(chunks)}")
            tts = gTTS(text=chunk, lang=lang, tld=tld, slow=slow)
            
            # Create a temporary file to store this chunk's audio
            temp_fd, temp_path = tempfile.mkstemp(suffix='.mp3')
            os.close(temp_fd) # Close file descriptor as we will open with gTTS / read later
            temp_files.append(temp_path)
            
            # Save gtts chunk to the temp file
            tts.save(temp_path)
            
        # Merge all temporary MP3 files by appending their raw bytes
        # (This works perfectly for gTTS MP3s since they share identical codecs/bitrates)
        logger.info(f"Merging {len(temp_files)} audio chunks into final file: {output_file_path}")
        with open(output_file_path, 'wb') as merged_file:
            for temp_path in temp_files:
                with open(temp_path, 'rb') as f:
                    merged_file.write(f.read())
                    
        logger.info("TTS generation and merge completed successfully.")
        
    except Exception as e:
        logger.error(f"Error during TTS generation: {str(e)}")
        raise e
        
    finally:
        # Clean up temporary files
        for temp_path in temp_files:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as clean_err:
                logger.warning(f"Failed to delete temp file {temp_path}: {str(clean_err)}")
