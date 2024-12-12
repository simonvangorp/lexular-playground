import os
import streamlit as st

# Set up the Streamlit page configuration
st.set_page_config(page_title="Transcriptie en ChatGPT Tool", layout="wide")

from record import start_recording, stop_recording, save_audio
from transcription import transcribe_with_gladia, format_diarization
from llm import initialize_chatbot, display_chat, handle_user_input, generate_first_response



# Title of the application
st.title("Transcriptie en ChatGPT Tool")

# Global variables
transcript = ""

# Tabs for "Record Audio", "Upload Bestand", "Transcriptie", and "ChatGPT"
tab1, tab2, tab3, tab4 = st.tabs(["Record Audio", "Upload Bestand", "Transcriptie", "ChatGPT"])

# Tab 1: Record Audio
with tab1:
    st.header("Audio Recorder")
    st.markdown("Gebruik de knoppen hieronder om audio op te nemen en te verwerken.")

    if "is_recording" not in st.session_state:
        st.session_state.is_recording = False

    if st.button("Start Recording"):
        if not st.session_state.is_recording:
            start_recording()
            st.session_state.is_recording = True
            st.success("Opname gestart.")

    if st.button("Stop Recording"):
        if st.session_state.is_recording:
            audio_array = stop_recording()
            st.session_state.is_recording = False
            if audio_array is not None:
                st.success("Opname gestopt. Klaar om op te slaan.")
                st.session_state["audio_array"] = audio_array

    if st.button("Save Recording"):
        if "audio_array" in st.session_state:
            file_path = save_audio(st.session_state["audio_array"])
            if file_path:
                st.success(f"Bestand opgeslagen als {file_path}.")
                # Trigger transcription flow automatically
                with st.spinner("Transcriberen..."):
                    utterances = transcribe_with_gladia(file_path)
                    transcript = format_diarization(utterances)
                    st.session_state["transcript"] = transcript
                    st.success("Transcripteerflow voltooid.")

# Tab 2: Upload Bestand
with tab2:
    uploaded_file = st.file_uploader("Upload een bestand (.txt of audio)", type=["txt", "m4a", "mp3", "wav"])

    if uploaded_file:
        if uploaded_file.type == "text/plain":
            transcript = uploaded_file.read().decode("utf-8")
            st.success("TXT-bestand succesvol geladen!")
        else:
            with st.spinner("Transcriberen..."):
                temp_dir = "temp"
                os.makedirs(temp_dir, exist_ok=True)
                temp_file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                utterances = transcribe_with_gladia(temp_file_path)
                transcript = format_diarization(utterances)
                os.remove(temp_file_path)
            st.success("Audio-bestand succesvol getranscribeerd!")

        st.session_state["transcript"] = transcript

# Tab 3: Transcriptie
with tab3:
    if "transcript" not in st.session_state:
        st.info("Upload een bestand in de eerste tab om transcriptie te bekijken.")
    else:
        st.text_area("Transcriptie:", st.session_state["transcript"], height=400)
        st.download_button(
            label="Download Transcriptie als .txt",
            data=st.session_state["transcript"],
            file_name="transcriptie.txt",
            mime="text/plain",
        )

# Tab 4: ChatGPT
with tab4:
    if "transcript" not in st.session_state:
        st.info("Upload een bestand in een andere tab om de chatbot te activeren.")
    else:
        initialize_chatbot()

        if "messages" not in st.session_state or not st.session_state.messages:
            st.write("Initializing messages...")
            cleaned_transcript = "\n".join(
                line.split("|")[0].strip() if "|" in line else line.strip()
                for line in st.session_state["transcript"].splitlines()
            )
            st.session_state.messages = [
                {
                    "role": "system",
                    "content": (
                        "Je bent een assistent die vragen beantwoordt op basis van een transcriptie. "
                        "De transcriptie is van een opname of een vergadering. "
                        "Gebruikers kunnen verwijzen naar deze transcriptie als 'de opname' of 'de vergadering'. "
                        "Hieronder staat een deel van een transcriptie van een gesprek. "
                        "Vat dit gedeelte beknopt samen in bulletpoints, en geef vervolgens de actiepunten in bulletpoints. "
                        "Zorg ervoor dat elk actiepunt de verantwoordelijke persoon tussen vierkante haken toont.\n\n"
                        f"{cleaned_transcript}"
                    ),
                }
            ]
            with st.spinner("De samenvatting en actiepunten worden gegenereerd..."):
                try:
                    first_response = generate_first_response(st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": first_response})
                    st.success("De samenvatting en actiepunten zijn gegenereerd!")
                except Exception as e:
                    st.error(f"Fout bij het ophalen van de initiële reactie: {e}")

        # Display chat and handle user input for follow-up questions
        display_chat()
        handle_user_input()
