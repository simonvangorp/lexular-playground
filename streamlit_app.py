import streamlit as st
import os
import requests
from time import time, sleep
from dotenv import load_dotenv


# Flexible API key loading
try:
    # Try to load API keys from st.secrets
    os.environ['openai_api_key'] = st.secrets['openai_api_key']
    os.environ['gladia_api_key'] = st.secrets['gladia_api_key']
    #st.write("API keys loaded from st.secrets.")
except Exception:
    # If st.secrets is not available, fallback to dotenv
    load_dotenv()
    os.environ['openai_api_key'] = os.getenv('openai_api_key')
    os.environ['gladia_api_key'] = os.getenv('gladia_api_key')
    #st.write("API keys loaded from .env file.")

# Verify that the keys are loaded
if not os.environ.get('openai_api_key') or not os.environ.get('gladia_api_key'):
    st.error("API keys are not properly set. Please check your setup.")


# Define a function for Whisper transcription
def transcribe_with_whisper(file_path):
    import whisper  # Import here to avoid issues if Whisper isn't installed
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


def transcribe_with_gladia(file_path):
    if not os.environ.get('gladia_api_key'):
        raise ValueError("Gladia API key not found in environment variables")

    # Step 1: Upload the audio file
    headers = {
        "x-gladia-key": os.environ['gladia_api_key'],
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

    # Step 2: Send transcription request with diarization enabled
    headers["Content-Type"] = "application/json"
    data = {
        "audio_url": audio_url,
        "diarization": True,  # Enable diarization
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
            # Return detailed diarization data
            return poll_response.get("result", {}).get("transcription", {}).get("utterances", [])
        elif status == "error":
            raise ValueError(f"Transcription failed: {poll_response}")
        else:
            sleep(3)

def format_diarization(utterances):
    """
    Format diarization data into readable text blocks.
    Merge consecutive utterances by the same speaker if the time gap is <= 10 seconds.
    """
    formatted_output = []
    current_speaker = None
    current_start = None
    current_end = None
    current_text = []

    for utterance in utterances:
        speaker = utterance.get("speaker", "Unknown")
        start_time = utterance.get("start", 0)
        end_time = utterance.get("end", 0)
        text = utterance.get("text", "")

        # If the speaker changes or the gap is >10 seconds, finalize the current block
        if speaker != current_speaker or (current_end is not None and start_time - current_end > 10):
            if current_speaker is not None:
                # Finalize the current block
                start_time_formatted = f"{int(current_start // 60):02}:{current_start % 60:.1f}"
                end_time_formatted = f"{int(current_end // 60):02}:{current_end % 60:.1f}"
                formatted_output.append(
                    f"Speaker {current_speaker} | {start_time_formatted} - {end_time_formatted}\n"
                    f"{' '.join(current_text)}\n"
                )
            # Start a new block
            current_speaker = speaker
            current_start = start_time
            current_text = []

        # Update the current block's end time and add the text
        current_end = end_time
        current_text.append(text)

    # Finalize the last block
    if current_speaker is not None:
        start_time_formatted = f"{int(current_start // 60):02}:{current_start % 60:.1f}"
        end_time_formatted = f"{int(current_end // 60):02}:{current_end % 60:.1f}"
        formatted_output.append(
            f"Speaker {current_speaker} | {start_time_formatted} - {end_time_formatted}\n\n"
            f"{' '.join(current_text)}\n"
        )

    # Join blocks with a blank line separator for readability
    return "\n".join(formatted_output)

# Streamlit application
st.title("Audio to Text Converter")

# Initialize session state for transcription and timer
if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "transcription_time" not in st.session_state:
    st.session_state.transcription_time = None

# Selection for transcription service
#service = st.radio("Select Transcription Service:", ('Advanced', 'Simple'))

# File uploader widget
uploaded_file = st.file_uploader("Upload an audio file", type=["m4a", "mp3", "wav"])

if uploaded_file and st.session_state.transcription is None:
    # Save the uploaded file to a temporary location
    with open("temp_audio_file", "wb") as f:
        f.write(uploaded_file.read())

    #st.write(f"Transcribing audio using {service}...")
    start_time = time()  # Start timer

    #if service == 'Advanced':
    utterances = transcribe_with_gladia("temp_audio_file")
    transcription = format_diarization(utterances)
    #else:
   #     transcription = transcribe_with_whisper("temp_audio_file")

    end_time = time()  # End timer
    st.session_state.transcription_time = end_time - start_time
    st.session_state.transcription = transcription  # Save transcription in session state

    # Optionally delete the temporary file after transcription
    os.remove("temp_audio_file")

# Display the transcription if available
if st.session_state.transcription:
    st.write("### Transcription")
    st.write(st.session_state.transcription)

    # Display the time taken for transcription
    st.write(f"### Time Taken: {st.session_state.transcription_time:.0f} seconds")

    # Add option to save as .txt file
    st.download_button(
        label="Download Transcription as .txt",
        data=st.session_state.transcription,
        file_name="transcription.txt",
        mime="text/plain",
    )
