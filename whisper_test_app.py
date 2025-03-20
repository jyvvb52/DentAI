import pyaudio
import wave
import os
import requests
import streamlit as st

# Audio Recording Parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Whisper prefers 16kHz
CHUNK = 1024
WAVE_OUTPUT_FILENAME = "recorded_audio.wav"

st.title("Audio Recording and Transcription")

# API Key input for OpenAI
api_key = st.text_input("Enter your OpenAI API key", type="password")

# Function to transcribe audio using OpenAI's Whisper API
def transcribe_audio(audio_file_path, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    with open(audio_file_path, "rb") as audio_file:
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

def record_audio(record_seconds):
    p = pyaudio.PyAudio()
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    st.info(f"Recording for {record_seconds} seconds... Speak now!")
    
    frames = []
    
    # Record for record_seconds
    for i in range(0, int(RATE / CHUNK * record_seconds)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    st.success("Recording complete!")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save the recorded data as a WAV file
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return WAVE_OUTPUT_FILENAME

# UI for recording duration
recording_duration = st.slider("Recording Duration (seconds)", min_value=3, max_value=60, value=5)

# Button to start recording
if st.button("Record Audio"):
    audio_file_path = record_audio(recording_duration)
    
    # Display the recorded audio
    st.audio(audio_file_path)
    
    # Transcribe the audio if API key is provided
    if api_key:
        with st.spinner("Transcribing audio..."):
            transcription = transcribe_audio(audio_file_path, api_key)
            if transcription:
                st.session_state.transcriptions.append(transcription)
                st.success("Transcription complete!")
    else:
        st.warning("Please enter your OpenAI API key to transcribe the audio")

# Display all transcriptions
if st.session_state.transcriptions:
    st.subheader("Transcriptions")
    for i, text in enumerate(st.session_state.transcriptions):
        st.write(f"{i+1}. {text}")
    
    # Add option to clear transcriptions
    if st.button("Clear All Transcriptions"):
        st.session_state.transcriptions = []
        st.experimental_rerun()