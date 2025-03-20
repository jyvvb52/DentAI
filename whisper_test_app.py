import streamlit as st
import os
import time
import base64
from io import BytesIO

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    st.error("OpenAI package is not installed. Installing now...")
    os.system("pip install openai")
    st.info("Please restart the app after installation completes.")

st.set_page_config(
    page_title="Whisper Real-Time Transcription",
    page_icon="🎤",
    layout="centered"
)

st.title("🎤 Whisper Real-Time Transcription")
st.markdown("This app automatically transcribes your voice using OpenAI Whisper API.")

# Initialize session state
if 'recorded_audio' not in st.session_state:
    st.session_state.recorded_audio = None
if 'transcription' not in st.session_state:
    st.session_state.transcription = None
if 'is_transcribing' not in st.session_state:
    st.session_state.is_transcribing = False

# API Key Input
st.subheader("1. Enter Your OpenAI API Key")
api_key = st.text_input("OpenAI API Key", type="password", help="Your key will not be stored permanently")

if api_key:
    st.success("API Key entered! You can now record audio for automatic transcription.")
else:
    st.info("Please enter your OpenAI API Key to use the Whisper transcription service.")

# Create a function to transcribe audio using Whisper API
def transcribe_with_whisper(api_key, audio_bytes):
    try:
        # Create a temporary file to store the audio
        os.makedirs("temp", exist_ok=True)
        temp_file = f"temp/recording_{int(time.time())}.wav"
        
        # Save the audio to the temporary file
        with open(temp_file, "wb") as f:
            f.write(audio_bytes)
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Transcribe the audio
        with open(temp_file, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        
        # Clean up the temporary file
        os.remove(temp_file)
        
        return response.text
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
        return None

# HTML/JavaScript to capture audio directly from browser
st.subheader("2. Record Audio & Get Instant Transcription")
st.markdown("Click 'Start Recording', speak, then 'Stop Recording' to automatically transcribe.")

# Display transcription status
transcription_status = st.empty()

# Placeholder for transcription results
transcription_result = st.container()

# Using HTML components directly to record audio with auto-transcription
record_html = """
<div style="padding: 20px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 20px;">
  <div style="display: flex; gap: 10px; margin-bottom: 15px;">
    <button id="startButton" style="padding: 10px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">Start Recording</button>
    <button id="stopButton" style="padding: 10px; background: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer;" disabled>Stop Recording</button>
  </div>
  <p id="recordingStatus">Ready to record. Click 'Start Recording' button above.</p>
  <div id="audioContainer" style="display: none;">
    <h4>Recorded Audio:</h4>
    <audio id="audioPlayer" controls></audio>
    <p id="audioInfo"></p>
  </div>
</div>

<script>
let mediaRecorder;
let audioChunks = [];
let audioBlob;
let audioUrl;

const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const recordingStatus = document.getElementById('recordingStatus');
const audioContainer = document.getElementById('audioContainer');
const audioPlayer = document.getElementById('audioPlayer');
const audioInfo = document.getElementById('audioInfo');

startButton.addEventListener('click', async () => {
  try {
    audioContainer.style.display = 'none';
    audioChunks = [];
    
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    
    mediaRecorder.addEventListener('dataavailable', event => {
      audioChunks.push(event.data);
    });
    
    mediaRecorder.addEventListener('stop', () => {
      audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      audioUrl = URL.createObjectURL(audioBlob);
      audioPlayer.src = audioUrl;
      audioContainer.style.display = 'block';
      
      audioInfo.textContent = `Recording size: ${(audioBlob.size / 1024).toFixed(2)} KB`;
      recordingStatus.textContent = 'Recording complete. Transcribing...';
      
      // Convert blob to base64 and send to Streamlit for auto-transcription
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      reader.onloadend = function() {
        const base64data = reader.result.split(',')[1];
        
        // Send message to Streamlit
        if (window.parent) {
          const message = {
            type: 'autoTranscribe',
            audio: base64data,
            size: audioBlob.size
          };
          window.parent.postMessage(JSON.stringify(message), '*');
        }
      };
    });
    
    mediaRecorder.start();
    startButton.disabled = true;
    stopButton.disabled = false;
    recordingStatus.textContent = 'Recording in progress... (Speak now)';
  } catch (error) {
    console.error('Error accessing microphone:', error);
    recordingStatus.textContent = 'Error: ' + error.message;
  }
});

stopButton.addEventListener('click', () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    startButton.disabled = false;
    stopButton.disabled = true;
    
    // Stop all audio tracks
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
  }
});
</script>
"""

st.components.v1.html(record_html, height=300)

# Monitor for audio recording events from JavaScript
components_js = """
<script>
window.addEventListener('message', function(event) {
    try {
        const data = JSON.parse(event.data);
        if (data.type === 'autoTranscribe') {
            const audioData = data.audio;
            const size = data.size;
            
            // Send the audio data to Streamlit
            const stringVal = JSON.stringify({
                type: 'autoTranscribe',
                audio: audioData,
                size: size
            });
            
            // Use Streamlit's setComponentValue
            if (window.parent.Streamlit) {
                window.parent.Streamlit.setComponentValue(stringVal);
            }
        }
    } catch (error) {
        console.error('Error handling message:', error);
    }
});
</script>
"""

# Add the JavaScript event listener
st.components.v1.html(components_js, height=0)

# Alternative method using streamlit-mic-recorder with auto-transcription
st.subheader("Alternative Recording Method")
st.write("If the above method doesn't work, try this alternative:")

try:
    from streamlit_mic_recorder import mic_recorder
    
    audio_bytes = mic_recorder(
        key="mic_recorder",
        start_prompt="Start Recording",
        stop_prompt="Stop Recording",
        just_once=True,
        use_container_width=True
    )
    
    if audio_bytes and not st.session_state.is_transcribing:
        st.session_state.recorded_audio = audio_bytes
        st.audio(audio_bytes)
        st.success(f"Successfully recorded {len(audio_bytes)} bytes of audio!")
        
        # Auto-transcribe if API key is provided
        if api_key:
            st.session_state.is_transcribing = True
            transcription_status.info("Transcribing audio automatically...")
            
            # Transcribe the audio
            transcription = transcribe_with_whisper(api_key, audio_bytes)
            
            if transcription:
                st.session_state.transcription = transcription
                st.session_state.is_transcribing = False
                transcription_status.success("Transcription complete!")
                
                # Display the transcription
                with transcription_result:
                    st.subheader("Transcription Result")
                    st.markdown("---")
                    st.markdown(f"**Transcription:**")
                    st.markdown(f'"{transcription}"')
                    st.markdown("---")
        else:
            st.warning("OpenAI API Key is required for automatic transcription.")
            
except Exception as e:
    st.warning(f"Alternative recording method not available: {str(e)}")
    st.info("Try installing with: pip install streamlit-mic-recorder")

# Handle auto-transcription from JavaScript component
if st.session_state.recorded_audio and not st.session_state.is_transcribing and api_key:
    # Auto-transcribe the audio
    st.session_state.is_transcribing = True
    transcription_status.info("Transcribing audio automatically...")
    
    # Transcribe the audio
    transcription = transcribe_with_whisper(api_key, st.session_state.recorded_audio)
    
    if transcription:
        st.session_state.transcription = transcription
        st.session_state.is_transcribing = False
        transcription_status.success("Transcription complete!")
        
        # Display the transcription
        with transcription_result:
            st.subheader("Transcription Result")
            st.markdown("---")
            st.markdown(f"**Transcription:**")
            st.markdown(f'"{transcription}"')
            st.markdown("---")

# Display the transcription if we have one
if 'transcription' in st.session_state and st.session_state.transcription:
    with transcription_result:
        st.subheader("Transcription Result")
        st.markdown("---")
        st.markdown(f"**Transcription:**")
        st.markdown(f'"{st.session_state.transcription}"')
        st.markdown("---")
    
    # Add a button to clear the transcription and start fresh
    if st.button("Clear and Start Fresh"):
        st.session_state.transcription = None
        st.session_state.recorded_audio = None
        st.session_state.is_transcribing = False
        st.experimental_rerun()

# File uploader for testing with existing audio files
with st.expander("Upload Existing Audio File (Optional)"):
    st.write("If you prefer, you can upload an existing audio file to transcribe:")
    
    uploaded_file = st.file_uploader("Choose a WAV or MP3 file", type=["wav", "mp3"])
    if uploaded_file is not None:
        # Display the uploaded audio
        st.audio(uploaded_file)
        
        # Add a button to transcribe the uploaded audio
        if st.button("Transcribe Uploaded Audio"):
            if not api_key:
                st.error("Please enter your OpenAI API key first.")
            else:
                # Read the uploaded file
                audio_bytes = uploaded_file.read()
                
                # Transcribe the audio
                with st.spinner("Transcribing uploaded audio..."):
                    transcription = transcribe_with_whisper(api_key, audio_bytes)
                    
                    if transcription:
                        st.success("Transcription complete!")
                        st.session_state.transcription = transcription
                        
                        # The transcription will be displayed in the main area

# Troubleshooting section
with st.expander("Troubleshooting"):
    st.markdown("""
    ### Common Issues:
    
    #### Microphone Access Problems:
    - Make sure your browser has permission to access your microphone
    - Try using Chrome, which has the best WebRTC support
    - Check that your microphone is not being used by another application
    
    #### Transcription Problems:
    - Ensure your OpenAI API key is correct and has access to the Whisper API
    - Check that your audio file is not too large (Whisper has a 25MB limit)
    - Make sure your audio contains clear speech in a supported language
    - If you get an "audio file is too short" error, try recording for longer
    
    #### API Key Issues:
    - If you're getting authentication errors, verify your API key
    - Make sure your OpenAI account has billing enabled
    - Try generating a new API key if problems persist
    """)

# Footer
st.markdown("---")
st.markdown("Created to demonstrate real-time audio transcription with OpenAI Whisper API.") 