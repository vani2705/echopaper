from flask import Flask, request, render_template, send_file
import os
import re
import pdfplumber
import pyttsx3
from dotenv import load_dotenv
import google.generativeai as genai
import jsonify

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

# Initialize pyttsx3 engine
engine = pyttsx3.init()
engine.setProperty('rate', 155)  # Reduce speed (default is around 200)

# Function to extract text from PDF and clean it
def extract_pdf_text(pdf_file_path):
    """Extracts text from a PDF file and removes asterisks."""
    text = ""
    with pdfplumber.open(pdf_file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    clean_text = re.sub(r'\*+', '', text)  # Remove all asterisks
    return clean_text.strip()

# Function to generate podcast-style script
def generate_conversational_script(pdf_text):
    """Generates a conversational script from extracted PDF text using Gemini AI."""
    if not pdf_text.strip():
        print("ERROR: Extracted PDF text is empty.")
        return None
    
    prompt = f"""
        Content should be highly detailed and a minimum of 2500 words.
        You are hosting a solo podcast discussing a research paper. 
        Expand on key ideas, include examples, anecdotes, and storytelling elements.
        Ensure a natural, engaging story-telling along with actual facts and figures.
        Structure the content with a clear introduction, in-depth discussion, and a conclusion.
        Research Paper Content:
        {pdf_text}
        """

    try:
        response = genai.GenerativeModel("gemini-pro").generate_content(prompt)
        return response.text.strip() if response and response.text else None
    except Exception as e:
        print(f"ERROR: Gemini API failed to generate a script. {e}")
        return None

# Function to convert text to speech using pyttsx3
def text_to_speech_pyttsx3(conversation, audio_output_path):
    """Converts the generated podcast script to speech using pyttsx3."""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    # Select Microsoft Zira's voice
    for voice in voices:
        if "Zira" in voice.name:
            engine.setProperty('voice', voice.id)
            break

    engine.save_to_file(conversation, audio_output_path)
    engine.runAndWait()  # Ensure the speech engine completes processing
    return os.path.exists(audio_output_path)

@app.route('/module', methods=['POST'])
def process_data():
    data = request.json
    response = {"message": "Received", "data": data}
    return jsonify(response)

if __name__ == '__main__':
    app.run(port=5000)  # Flask runs on port 5000

@app.route('/', methods=['GET', 'POST'])
def home():
    """Handles file upload and processing."""
    if request.method == 'POST':
        uploaded_file = request.files.get('pdf_file')
        if not uploaded_file or uploaded_file.filename == "":
            return "Error: No file uploaded.", 400

        pdf_file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(pdf_file_path)

        # Extract text from PDF and clean it
        pdf_text = extract_pdf_text(pdf_file_path)
        if not pdf_text:
            return "Error: No text extracted from the PDF.", 400

        # Generate conversational script
        conversation = generate_conversational_script(pdf_text)
        if not conversation:
            return "Error: Failed to generate a script.", 400
        
        conversation = conversation.replace("\n", "\n\n")
        # Define audio file path
        audio_output_path = os.path.join(UPLOAD_FOLDER, "output_podcast.mp3")

        success = text_to_speech_pyttsx3(conversation, audio_output_path)
        if not success:
            return "Error: Audio file was not generated.", 500

        return send_file(audio_output_path, as_attachment=True)

    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
