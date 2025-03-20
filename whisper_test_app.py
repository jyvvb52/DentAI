import streamlit as st
import base64
import requests
import json
from io import BytesIO
import time

st.title("Audio Transcription with Whisper API")

# API Key input
api_key = st.text_input("Enter your OpenAI API Key", type="password")

# Initialize session state
if "transcriptions" not in st.session_state:
    st.session_state.transcriptions = []

# Function to transcribe audio using OpenAI's Whisper API
def transcribe_audio(audio_data, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "multipart/form-data"
    }
    
    # Convert base64 to bytes
    audio_bytes = base64.b64decode(audio_data.split(",")[1])
    
    # Create file-like object
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "recording.webm"
    
    files = {
        "file": audio_file,
        "model": (None, "whisper-1"),
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files=files
        )
        
        if response.status_code == 200:
            return response.json()["text"]
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Exception occurred: {e}")
        return None

# Create an audio recorder using HTML/JavaScript
st.markdown("## Audio Recorder")
st.markdown("Click the Start button to begin recording, and Stop when you're done speaking.")

# Custom HTML/JavaScript component for audio recording
audio_recorder_html = """
<div>
    <button id="startButton" onclick="startRecording()">Start Recording</button>
    <button id="stopButton" onclick="stopRecording()" disabled>Stop Recording</button>
    <div id="recordingStatus"></div>
    <audio id="audioPlayback" controls style="display: none;"></audio>
</div>

<script>
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

async function startRecording() {
    document.getElementById('startButton').disabled = true;
    document.getElementById('stopButton').disabled = false;
    document.getElementById('recordingStatus').innerText = "Recording...";
    document.getElementById('audioPlayback').style.display = 'none';
    
    audioChunks = [];
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(audioBlob);
            document.getElementById('audioPlayback').src = audioUrl;
            document.getElementById('audioPlayback').style.display = 'block';
            
            // Convert to base64 for sending to Python
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = () => {
                const base64data = reader.result;
                // Send to Streamlit
                sendToStreamlit(base64data);
            };
        };
        
        mediaRecorder.start();
        isRecording = true;
    } catch (err) {
        console.error("Error accessing microphone:", err);
        document.getElementById('recordingStatus').innerText = "Error: " + err.message;
        document.getElementById('startButton').disabled = false;
        document.getElementById('stopButton').disabled = true;
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        document.getElementById('recordingStatus').innerText = "Recording stopped. Processing...";
        document.getElementById('startButton').disabled = false;
        document.getElementById('stopButton').disabled = true;
        
        // Stop all audio tracks to release the microphone
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
}

function sendToStreamlit(base64data) {
    // Using Streamlit's component communication
    const data = {
        audioData: base64data
    };
    
    // Store in sessionStorage for Streamlit to retrieve
    sessionStorage.setItem('audioData', base64data);
    
    // Signal to Streamlit that data is ready
    document.getElementById('recordingStatus').innerText = "Audio ready for transcription";
    
    // This will make the Streamlit app rerun (when the user interacts with it)
    if (window.parent.window.streamlitApp) {
        window.parent.window.streamlitApp.sendMessageToStreamlitClient({
            type: "streamlit:setComponentValue",
            value: true
        });
    }
}
</script>
"""

# Use Streamlit's components to render the HTML/JavaScript
st.components.v1.html(audio_recorder_html, height=200)

# Create a button to trigger transcription
if st.button("Transcribe Recorded Audio"):
    if not api_key:
        st.warning("Please enter your OpenAI API key first")
    else:
        # Run JavaScript to get the audio data from sessionStorage
        js_code = """
        <script>
        const audioData = sessionStorage.getItem('audioData');
        if (audioData) {
            document.getElementById('audioDataField').value = audioData;
            document.getElementById('audioDataForm').submit();
        } else {
            alert("No audio recording found. Please record audio first.");
        }
        </script>
        <form id="audioDataForm" action="" method="post">
            <input type="hidden" id="audioDataField" name="audioData">
        </form>
        """
        st.components.v1.html(js_code, height=0)
        
        # Check if form data exists in the request
        import streamlit as st
        from streamlit import runtime
        
        # Try to get audio data from various places
        # This is a bit hacky but we're working around Streamlit limitations
        audio_data = None
        
        # Try SessionState
        if hasattr(st, 'session_state') and 'audioData' in st.session_state:
            audio_data = st.session_state.audioData
        
        # Try query parameters
        query_params = st.experimental_get_query_params()
        if 'audioData' in query_params:
            audio_data = query_params['audioData'][0]
        
        # If we have audio data, transcribe it
        if audio_data:
            with st.spinner("Transcribing audio..."):
                transcription = transcribe_audio(audio_data, api_key)
                if transcription:
                    st.session_state.transcriptions.append(transcription)
                    st.success("Transcription complete!")
        else:
            st.warning("No audio data found. Please record audio and try again.")

# Display transcriptions
if st.session_state.transcriptions:
    st.subheader("Transcriptions")
    for i, text in enumerate(st.session_state.transcriptions):
        st.write(f"{i+1}. {text}")
    
    # Add option to clear transcriptions
    if st.button("Clear All Transcriptions"):
        st.session_state.transcriptions = []
        st.experimental_rerun()