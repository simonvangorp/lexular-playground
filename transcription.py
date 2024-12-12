import os
from dotenv import load_dotenv
import requests
import time

# Flexible API key loading for Gladia
def load_gladia_api_key():
    """
    Load Gladia API key from either Streamlit secrets or environment variables.
    This function does not interact with Streamlit directly to prevent unintended logging or output.
    """
    # Attempt to load from Streamlit secrets (only if available in the cloud)
    try:
        import streamlit as st
        api_key = st.secrets['gladia_api_key']
    except Exception:
        # If secrets aren't available, fallback to .env
        load_dotenv()
        api_key = os.getenv('gladia_api_key')

    if not api_key:
        raise ValueError("Gladia API key is not properly loaded. Please check your setup.")

    return api_key

# Load the Gladia API key
gladia_api_key = load_gladia_api_key()

# Function to make HTTP requests
def make_request(url, headers, method="GET", data=None, files=None):
    if method == "POST":
        response = requests.post(url, headers=headers, json=data, files=files)
    else:
        response = requests.get(url, headers=headers)
    return response.json()

# Transcription function with Gladia
def transcribe_with_gladia(file_path):
    if not gladia_api_key:
        raise ValueError("Gladia API key not found in environment variables")

    # Step 1: Upload the audio file
    headers = {
        "x-gladia-key": gladia_api_key,
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
            time.sleep(3)

# Function to format the diarization output
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
                    f"Speaker {current_speaker} | {start_time_formatted} - {end_time_formatted} |\n"
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
            f"Speaker {current_speaker} | {start_time_formatted} - {end_time_formatted} |\n"
            f"{' '.join(current_text)}\n"
        )

    # Join blocks with a blank line separator for readability
    return "\n".join(formatted_output)
