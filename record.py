import sounddevice as sd
import numpy as np
import wave
import os
import streamlit as st

# Globals for managing recording
audio_data = []
is_recording = False
samplerate = 44100  # Audio sample rate (44.1 kHz)


def start_recording():
    """
    Start recording audio using sounddevice.
    """
    global audio_data, is_recording
    audio_data = []
    is_recording = True

    def callback(indata, frames, time, status):
        if is_recording:
            audio_data.append(indata.copy())

    # Open a stream for recording
    stream = sd.InputStream(
        samplerate=samplerate,
        channels=1,
        callback=callback,
        dtype="int16",
    )
    stream.start()
    st.session_state["stream"] = stream  # Save the stream in session state


def stop_recording():
    """
    Stop the recording process and return the recorded audio data.
    """
    global is_recording
    is_recording = False

    if "stream" in st.session_state:
        st.session_state["stream"].stop()
        st.session_state["stream"].close()

    if audio_data:
        # Combine audio chunks into a single numpy array
        audio_array = np.concatenate(audio_data, axis=0)
        return audio_array
    return None


def save_audio(audio_array, file_path="recorded_audio.wav"):
    """
    Save the recorded audio to a .wav file.
    """
    if audio_array is not None:
        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)  # Mono audio
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(samplerate)
            wf.writeframes(audio_array.tobytes())
        return file_path
    return None
