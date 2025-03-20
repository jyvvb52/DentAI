import streamlit as st
import os
import time
import io
from openai import OpenAI

# Try to import the mic_recorder component
try:
    from streamlit_mic_recorder import mic_recorder
    MIC_RECORDER_AVAILABLE = True
except ImportError:
    MIC_RECORDER_AVAILABLE = False
    st.error("streamlit-mic-recorder is not installed. Installing now...")
    os.system("pip install streamlit-mic-recorder")
    st.info("Please restart the app after installation completes.")

st.set_page_config(
    page_title="Simple Whisper Test",
    page_icon="🎤",
    layout="centered"
)

st.title("🎤 Simple OpenAI Whisper Test")
st.markdown("This minimal app tests recording and transcription with Whisper API")

# API Key input
api_key = st.text_input("Enter your OpenAI API Key", type="password")

if not api_key:
    st.warning("Please enter your OpenAI API key to use the transcription feature")
else:
    st.success("API key entered! You can now record and transcribe audio.")

# Create a function to transcribe audio
def transcribe_audio(audio_bytes, api_key):
    try:
        # Create temp directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        
        # Save the audio bytes to a WAV file
        timestamp = int(time.time())
        temp_filename = f"temp/recording_{timestamp}.wav"
        
        with open(temp_filename, "wb") as f:
            f.write(audio_bytes)
        
        # Check file size
        file_size = os.path.getsize(temp_filename)
        st.info(f"Audio file saved: {file_size} bytes")
        
        if file_size < 1000:  # Less than 1KB
            st.warning("Audio file is very small and may be too short for transcription")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Send to Whisper API
        with st.spinner("Transcribing with Whisper API..."):
            with open(temp_filename, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
        
        # Clean up the temp file
        os.remove(temp_filename)
        
        return response.text
    except Exception as e:
        st.error(f"Error during transcription: {str(e)}")
        return None

# Record audio with mic_recorder
if MIC_RECORDER_AVAILABLE:
    st.subheader("1. Record Your Voice")
    st.markdown("Click the microphone button below, speak, then click again to stop recording.")
    
    audio_bytes = mic_recorder(
        key="simple_mic_recorder",
        start_prompt="Start Recording",
        stop_prompt="Stop Recording",
        just_once=True,
        use_container_width=True
    )
    
    # Handle the recorded audio
    if audio_bytes:
        st.success(f"Audio recorded! ({len(audio_bytes)} bytes)")
        
        # Create a safe way to display the audio
        try:
            # Only try to play audio if it's a reasonable size
            if len(audio_bytes) > 1000:
                st.audio(audio_bytes, format="audio/wav")
            else:
                st.warning("Audio file too small to play")
        except Exception as e:
            st.warning(f"Cannot display audio playback: {str(e)}")
        
        # Transcribe button
        if st.button("Transcribe Audio"):
            if not api_key:
                st.error("Please enter your OpenAI API key first")
            else:
                # Transcribe the audio
                transcription = transcribe_audio(audio_bytes, api_key)
                
                if transcription:
                    st.subheader("Transcription Result:")
                    st.success(transcription)
    else:
        st.info("No audio recorded yet. Click the microphone button to start recording.")

# File uploader as fallback
st.subheader("2. Or Upload an Audio File")
uploaded_file = st.file_uploader("Choose a WAV or MP3 file", type=["wav", "mp3"])

if uploaded_file is not None:
    # Read the file
    audio_bytes = uploaded_file.read()
    
    # Display information
    st.success(f"File uploaded: {uploaded_file.name} ({len(audio_bytes)} bytes)")
    
    # Try to play the audio
    try:
        st.audio(audio_bytes)
    except Exception as e:
        st.warning(f"Cannot display audio playback: {str(e)}")
    
    # Transcribe button for uploaded file
    if st.button("Transcribe Uploaded Audio"):
        if not api_key:
            st.error("Please enter your OpenAI API key first")
        else:
            # Transcribe the uploaded audio
            transcription = transcribe_audio(audio_bytes, api_key)
            
            if transcription:
                st.subheader("Transcription Result:")
                st.success(transcription)

# Troubleshooting section
with st.expander("Troubleshooting"):
    st.markdown("""
    ### Common Issues:
    
    1. **Audio Not Recording**
       - Check if your microphone is connected and working
       - Ensure your browser has permission to access the microphone
       - Try using Chrome instead of other browsers
    
    2. **Transcription Errors**
       - Make sure your OpenAI API key is correct
       - Ensure your audio is clear and at least 0.5 seconds long
       - Check if your account has billing enabled for the OpenAI API
    
    3. **Audio Playback Issues**
       - Some audio formats may not play correctly in Streamlit
       - Try uploading a pre-recorded WAV or MP3 file instead
    """) 