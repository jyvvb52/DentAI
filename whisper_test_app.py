import streamlit as st
import requests
import tempfile
import os
from io import BytesIO
import base64
import json
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import numpy as np
import wave
import threading
import queue

st.title("Real-time Audio Transcription with Whisper API")

# API Key input
api_key = st.text_input("Enter your OpenAI API Key", type="password")

# Initialize session state for transcriptions and audio buffer
if "transcriptions" not in st.session_state:
    st.session_state.transcriptions = []

if "audio_buffer" not in st.session_state:
    st.session_state.audio_buffer = []

if "recording" not in st.session_state:
    st.session_state.recording = False

if "audio_queue" not in st.session_state:
    st.session_state.audio_queue = queue.Queue()

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

# Function to save audio data to a WAV file
def save_audio_data(audio_frames, sample_rate=16000):
    if not audio_frames:
        return None
    
    # Create a BytesIO object to hold the WAV file data
    wav_buffer = BytesIO()
    
    # Open the WAV file for writing
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono audio
        wav_file.setsampwidth(2)  # 16-bit audio
        wav_file.setframerate(sample_rate)
        
        # Write audio frames
        for frame in audio_frames:
            wav_file.writeframes(frame.tobytes())
    
    # Reset buffer pointer to beginning
    wav_buffer.seek(0)
    return wav_buffer

# Audio processor function for WebRTC
def audio_processor_factory():
    # Buffer to hold audio samples
    audio_buffer = []
    
    # Counter for frames
    frame_count = 0
    
    # Duration in seconds to collect before sending for transcription
    buffer_duration = 5  # seconds
    sample_rate = 16000
    frames_per_buffer = int(buffer_duration * sample_rate)
    
    def audio_processor(frame):
        nonlocal frame_count
        
        # Convert audio frame to numpy array
        audio_data = frame.to_ndarray()
        
        # Resample to 16kHz (Whisper's preferred rate)
        # This is a simple resampling, for better quality you might want a proper resampler
        if frame.sample_rate != sample_rate:
            # Crude resampling by interpolation
            audio_data = np.interp(
                np.linspace(0, len(audio_data), int(len(audio_data) * sample_rate / frame.sample_rate)),
                np.arange(len(audio_data)),
                audio_data
            )
        
        # Add to buffer
        audio_buffer.append(audio_data)
        frame_count += len(audio_data)
        
        # If we've collected enough data
        if frame_count >= frames_per_buffer and st.session_state.recording:
            # Create a copy of the buffer
            buffer_copy = audio_buffer.copy()
            
            # Add to processing queue
            st.session_state.audio_queue.put(buffer_copy)
            
            # Clear buffer for next batch
            audio_buffer.clear()
            frame_count = 0
        
        return frame
    
    return audio_processor

# Function to process audio queue in a background thread
def process_audio_queue():
    while True:
        try:
            # Check if there's data in the queue
            if not st.session_state.audio_queue.empty() and api_key:
                # Get audio frames from queue
                audio_frames = st.session_state.audio_queue.get(timeout=1)
                
                # Save to WAV file
                wav_buffer = save_audio_data(audio_frames)
                
                if wav_buffer:
                    # Transcribe
                    transcription = transcribe_audio(("audio.wav", wav_buffer), api_key)
                    
                    if transcription and transcription.strip():
                        # Add to transcriptions (thread-safe using st.experimental_rerun)
                        st.session_state.transcriptions.append(transcription)
                        # This will force a rerun on the next user interaction
            
            # Sleep briefly to prevent CPU overuse
            import time
            time.sleep(0.1)
            
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error processing audio: {e}")
            import time
            time.sleep(1)  # Wait a bit before trying again

# Create a WebRTC streamer
rtc_configuration = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

webrtc_ctx = webrtc_streamer(
    key="speech-to-text",
    mode=WebRtcMode.AUDIO_PROCESSING,
    rtc_configuration=rtc_configuration,
    audio_processor_factory=audio_processor_factory,
    desired_playing_state=True,
)

# Recording control
col1, col2 = st.columns(2)
with col1:
    if webrtc_ctx.state.playing:
        if st.button("Start Recording" if not st.session_state.recording else "Stop Recording"):
            st.session_state.recording = not st.session_state.recording
            
            if st.session_state.recording:
                st.success("Recording started! Speak now...")
            else:
                st.info("Recording stopped.")

# Start background processing thread
if webrtc_ctx.state.playing and not hasattr(st.session_state, 'thread_started'):
    thread = threading.Thread(target=process_audio_queue, daemon=True)
    thread.start()
    st.session_state.thread_started = True

# Display transcriptions
st.subheader("Transcriptions")
for i, text in enumerate(st.session_state.transcriptions):
    st.write(f"{i+1}. {text}")

# Add option to clear transcriptions
if st.session_state.transcriptions and st.button("Clear All Transcriptions"):
    st.session_state.transcriptions = []