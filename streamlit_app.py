import streamlit as st
import os
import requests
import whisper
from time import sleep
#from dotenv import load_dotenv


# Load environment variables
#load_dotenv()

os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']
os.environ['GLADIA_API_KEY'] = st.secrets['GLADIA_API_KEY']


# Define a function for Whisper transcription
def transcribe_with_whisper(file_path):
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result['text']


# Function to make HTTP requests
def make_request(url, headers, method="GET", data=None, files=None):
    if method == "POST":
        response = requests.post(url, headers=headers, json=data, files=files)
    else:
        response = requests.get(url, headers=headers)
    return response.json()


# Function to transcribe audio using Gladia API
def transcribe_with_gladia(file_path):
    if not GLADIA_API_KEY:
        raise ValueError("Gladia API key not found in environment variables")

    # Step 1: Upload the audio file
    headers = {
        "x-gladia-key": GLADIA_API_KEY,
        "accept": "application/json",
    }

    file_name, file_extension = os.path.splitext(file_path)
    with open(file_path, "rb") as f:
        file_content = f.read()

    files = [("audio", (os.path.basename(file_path), file_content, f"audio/{file_extension[1:]}"))]
    upload_response = make_request("https://api.gladia.io/v2/upload/", headers, "POST", files=files)

    audio_url = upload_response.get("audio_url")
    if not audio_url:
        raise ValueError(f"Failed to upload audio file: {upload_response}")

    # Step 2: Send transcription request
    headers["Content-Type"] = "application/json"
    data = {
        "audio_url": audio_url,
        "diarization": False,
        "translation": False,
        "subtitles": False,
        "detect_language": True,
    }
    transcription_response = make_request(
        "https://api.gladia.io/v2/pre-recorded", headers, "POST", data=data
    )

    result_url = transcription_response.get("result_url")
    if not result_url:
        raise ValueError(f"Failed to initiate transcription: {transcription_response}")

    # Step 3: Poll for results
    while True:
        poll_response = make_request(result_url, headers)
        status = poll_response.get("status")

        if status == "done":
            return poll_response.get("result", {}).get("transcription", {}).get("full_transcript", "No transcription found.")
        elif status == "error":
            raise ValueError(f"Transcription failed: {poll_response}")
        else:
            sleep(3)


# Streamlit application
st.title("Audio to Text Converter")

# Initialize session state for transcription
if "transcription" not in st.session_state:
    st.session_state.transcription = None

# Selection for transcription service
service = st.radio("Select Transcription Service:", ('Gladia', 'Whisper'))

# File uploader widget
uploaded_file = st.file_uploader("Upload an audio file", type=["m4a", "mp3", "wav"])

if uploaded_file and st.session_state.transcription is None:
    # Save the uploaded file to a temporary location
    with open("temp_audio_file", "wb") as f:
        f.write(uploaded_file.read())

    st.write(f"Transcribing audio using {service}...")
    if service == 'Gladia':
        transcription = transcribe_with_gladia("temp_audio_file")
    else:
        transcription = transcribe_with_gladia("temp_audio_file")

    st.session_state.transcription = transcription  # Save transcription in session state

    # Optionally delete the temporary file after transcription
    os.remove("temp_audio_file")

# Display the transcription if available
if st.session_state.transcription:
    st.write("### Transcription")
    st.write(st.session_state.transcription)

    # Add option to save as .txt file
    st.download_button(
        label="Download Transcription as .txt",
        data=st.session_state.transcription,
        file_name="transcription.txt",
        mime="text/plain",
    )
