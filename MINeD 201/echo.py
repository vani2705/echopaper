from flask import Flask, request, render_template, send_file, jsonify
import os
import re
import pdfplumber
from dotenv import load_dotenv
import google.generativeai as genai
import elevenlabs
from elevenlabs import Client, generate, save

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Gemini API Setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("ERROR: Gemini API key is missing. Set it in the .env file.")

genai.configure(api_key=GEMINI_API_KEY)

# ElevenLabs API Setup
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("ERROR: ElevenLabs API key is missing. Set it in the .env file.")

# Initialize the ElevenLabs client
eleven_client = Client(api_key=ELEVENLABS_API_KEY)

# Retrieve available voices
def get_available_voices():
    try:
        voices = eleven_client.get_voices()
        return {voice["name"]: voice["model_id"] for voice in voices}
    except Exception as e:
        print(f"ERROR: Unable to fetch ElevenLabs voices. {e}")
        return {}

available_voices = get_available_voices()

def extract_pdf_text(pdf_file_path):
    """Extracts text from a PDF file and removes asterisks."""
    text = ""
    with pdfplumber.open(pdf_file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return re.sub(r'\*+', '', text).strip()

def generate_conversational_script(pdf_text, length='long'):
    """Generates a conversational script from extracted PDF text using Gemini AI."""
    if not pdf_text.strip():
        return None
    
    prompt = f"""
        Generate a {'detailed podcast script (2500+ words)' if length == 'long' else 'short, engaging script (under 500 words)'}
        for a research paper discussion. Ensure a natural storytelling approach.
        Research Paper Content:
        {pdf_text}
    """
    
    try:
        response = genai.GenerativeModel("gemini-pro").generate_content(prompt)
        return response.text.strip() if response and response.text else None
    except Exception as e:
        print(f"ERROR: Gemini API failed to generate a script. {e}")
        return None

def text_to_speech_elevenlabs(conversation, audio_output_path, voice='Bella'):
    """Converts text to speech using ElevenLabs with the selected voice model."""
    if voice not in available_voices:
        print(f"ERROR: Selected voice '{voice}' is not available.")
        return False
    
    try:
        audio = elevenlabs.generate(
            text=conversation,
            voice=voice,
            model=available_voices[voice]
        )
        elevenlabs.save(audio, audio_output_path)
        return os.path.exists(audio_output_path)
    except Exception as e:
        print(f"ERROR: ElevenLabs TTS failed. {e}")
        return False

@app.route('/', methods=['GET', 'POST'])
def home():
    """Handles file upload and processing."""
    if request.method == 'POST':
        uploaded_file = request.files.get('pdf_file')
        if not uploaded_file or uploaded_file.filename == "":
            return jsonify({"error": "No file uploaded."}), 400

        pdf_file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(pdf_file_path)

        pdf_text = extract_pdf_text(pdf_file_path)
        if not pdf_text:
            return jsonify({"error": "No text extracted from the PDF."}), 400

        script_length = request.form.get("length", "long")
        voice = request.form.get("voice", "Bella")
        
        if voice not in available_voices:
            return jsonify({"error": "Selected voice is not available."}), 400

        conversation = generate_conversational_script(pdf_text, length=script_length)
        if not conversation:
            return jsonify({"error": "Failed to generate a script."}), 400

        # Double newlines for better readability in TTS output.
        conversation = conversation.replace("\n", "\n\n")
        audio_output_path = os.path.join(UPLOAD_FOLDER, "output_podcast.mp3")
        
        success = text_to_speech_elevenlabs(conversation, audio_output_path, voice=voice)
        if not success:
            return jsonify({"error": "Audio file was not generated."}), 500

        return send_file(audio_output_path, as_attachment=True)
    
    return render_template('index.html', voices=available_voices.keys())

if __name__ == "__main__":
    app.run(debug=True)