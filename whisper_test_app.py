import streamlit as st
import requests
import time
import tempfile
import os
from io import BytesIO
from datetime import datetime

st.title("Real-time Audio Transcription with Whisper API")

# API Key input
api_key = st.text_input("Enter your OpenAI API Key", type="password")

# Function to transcribe audio using OpenAI's Whisper API
def transcribe_audio(audio_file, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    files = {
        "file": audio_file,
        "model": (None, "whisper-1"),
    }
    
    response = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers=headers,
        files=files
    )
    
    if response.status_code == 200:
        return response.json()["text"]
    else:
        st.error(f"Error: {response.status_code} - {response.text}")
        return None

# Initialize session state to store transcriptions
if "transcriptions" not in st.session_state:
    st.session_state.transcriptions = []

# Use Streamlit's audio recorder
st.write("Click the microphone icon to start recording")
audio_bytes = st.audio_recorder(pause_threshold=5.0)

if audio_bytes:
    # Save the recorded audio to a temporary file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_filepath = tmp_file.name
    
    st.audio(audio_bytes, format="audio/webm")
    
    # Make sure we have an API key
    if api_key:
        with open(tmp_filepath, "rb") as audio_file:
            with st.spinner("Transcribing..."):
                # Transcribe the audio
                transcription = transcribe_audio(audio_file, api_key)
                if transcription:
                    # Add to session state
                    st.session_state.transcriptions.append(transcription)
                    # Clear display and show all transcriptions
                    st.success("Transcription complete!")
    else:
        st.warning("Please enter your OpenAI API key first")
    
    # Clean up temporary file
    os.unlink(tmp_filepath)

# Display all transcriptions
st.subheader("Transcriptions")
for i, text in enumerate(st.session_state.transcriptions):
    st.write(f"{i+1}. {text}")

# Add option to clear transcriptions
if st.session_state.transcriptions and st.button("Clear All Transcriptions"):
    st.session_state.transcriptions = []
    st.experimental_rerun()