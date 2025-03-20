import streamlit as st
import requests
import tempfile
import os

st.title("Audio Transcription with Whisper API")

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

# File uploader for audio
st.write("""
## Upload Audio File
Record audio using your device's recorder app, then upload it here.
Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, and webm
""")

uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"])

if uploaded_file is not None:
    # Display the uploaded audio
    st.audio(uploaded_file, format=f"audio/{uploaded_file.type}")
    
    # Create a button to start transcription
    if st.button("Transcribe Audio"):
        # Make sure we have an API key
        if api_key:
            with st.spinner("Transcribing..."):
                # Reset file pointer to beginning
                uploaded_file.seek(0)
                
                # Transcribe the audio
                transcription = transcribe_audio(uploaded_file, api_key)
                if transcription:
                    # Add to session state
                    st.session_state.transcriptions.append(transcription)
                    st.success("Transcription complete!")
        else:
            st.warning("Please enter your OpenAI API key first")

# Display all transcriptions
if st.session_state.transcriptions:
    st.subheader("Transcriptions")
    for i, text in enumerate(st.session_state.transcriptions):
        st.write(f"{i+1}. {text}")
    
    # Add option to clear transcriptions
    if st.button("Clear All Transcriptions"):
        st.session_state.transcriptions = []
        st.experimental_rerun()