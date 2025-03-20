import streamlit as st
import requests
import tempfile
import os
from io import BytesIO

st.title("Audio Transcription with Whisper API")

# API Key input for OpenAI
api_key = st.text_input("Enter your OpenAI API key", type="password")

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

# Instructions for recording audio
st.markdown("---")
st.subheader("How to Record Audio")
st.markdown("""
To use this app:

1. **Record Audio**: Use your device's built-in recording app:
   - **Windows**: Voice Recorder app
   - **macOS**: QuickTime Player or Voice Memos
   - **iOS/Android**: Voice Recorder app
   - **Web Browser**: You can use [Online Voice Recorder](https://online-voice-recorder.com/)
   
2. **Save the File**: Save the recording to your device

3. **Upload**: Use the file uploader above to select your audio file

4. **Transcribe**: Click the "Transcribe Audio" button

For best results, speak clearly and minimize background noise.
""")