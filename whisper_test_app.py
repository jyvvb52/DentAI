import streamlit as st
import requests
from io import BytesIO
import base64

st.title("Audio Recorder and Transcription with Whisper API")

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

# Add tab navigation for different functionalities
tab1, tab2 = st.tabs(["Record Audio", "Upload Audio"])

with tab1:
    st.header("Record Audio in Browser")
    
    # Create HTML/JavaScript component for audio recording directly in the browser
    audio_recorder_html = """
    <style>
    .recording-controls {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-bottom: 15px;
    }
    button {
        padding: 10px 15px;
        cursor: pointer;
        border: none;
        border-radius: 4px;
        font-weight: bold;
        margin-right: 10px;
    }
    #startButton {
        background-color: #4CAF50;
        color: white;
    }
    #stopButton {
        background-color: #f44336;
        color: white;
    }
    #downloadButton {
        background-color: #2196F3;
        color: white;
    }
    .status {
        margin: 10px 0;
        font-weight: bold;
    }
    </style>

    <div class="recording-controls">
        <div>
            <button id="startButton" onclick="startRecording()">Start Recording</button>
            <button id="stopButton" onclick="stopRecording()" disabled>Stop Recording</button>
            <button id="downloadButton" onclick="downloadRecording()" disabled>Download Recording</button>
        </div>
        <div id="recordingStatus" class="status"></div>
    </div>
    <audio id="audioPlayback" controls style="display: none; width: 100%;"></audio>

    <script>
    let mediaRecorder;
    let audioChunks = [];
    let audioBlob = null;
    let audioUrl = '';

    async function startRecording() {
        document.getElementById('startButton').disabled = true;
        document.getElementById('stopButton').disabled = false;
        document.getElementById('downloadButton').disabled = true;
        document.getElementById('recordingStatus').innerText = "Recording... Speak now!";
        document.getElementById('audioPlayback').style.display = 'none';
        
        audioChunks = [];
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };
            
            mediaRecorder.onstop = () => {
                audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                audioUrl = URL.createObjectURL(audioBlob);
                document.getElementById('audioPlayback').src = audioUrl;
                document.getElementById('audioPlayback').style.display = 'block';
                document.getElementById('recordingStatus').innerText = "Recording complete. You can play it back above.";
                document.getElementById('downloadButton').disabled = false;
                
                // Convert to base64 for use with Streamlit
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);
                reader.onloadend = () => {
                    const base64Audio = reader.result;
                    // Store in sessionStorage for retrieval
                    sessionStorage.setItem('recordedAudio', base64Audio);
                    
                    // Notify that audio is ready for transcription
                    document.dispatchEvent(new CustomEvent('audioRecorded'));
                };
            };
            
            mediaRecorder.start();
        } catch (err) {
            console.error("Error accessing microphone:", err);
            document.getElementById('recordingStatus').innerText = "Error: " + err.message;
            document.getElementById('startButton').disabled = false;
            document.getElementById('stopButton').disabled = true;
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            document.getElementById('stopButton').disabled = true;
            document.getElementById('startButton').disabled = false;
            
            mediaRecorder.stop();
            
            // Stop all tracks to release microphone
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    }

    function downloadRecording() {
        if (audioBlob) {
            const a = document.createElement('a');
            a.href = audioUrl;
            a.download = 'recording.webm';
            a.click();
        }
    }
    </script>
    """
    
    # Display the HTML component
    st.components.v1.html(audio_recorder_html, height=200)
    
    # Note about recording
    st.info("Click 'Start Recording' to begin. Allow microphone access when prompted. Click 'Stop Recording' when finished.")
    
    # Button to trigger the transcription of recorded audio
    if st.button("Transcribe Recorded Audio"):
        if not api_key:
            st.warning("Please enter your OpenAI API key first")
        else:
            # Instructions to check browser local storage
            st.info("Attempting to transcribe the recorded audio...")
            
            # Script to retrieve audio data
            retrieval_script = """
            <script>
            // Function to convert base64 to blob
            function base64ToBlob(base64, mimeType) {
                const byteString = atob(base64.split(',')[1]);
                const ab = new ArrayBuffer(byteString.length);
                const ia = new Uint8Array(ab);
                
                for (let i = 0; i < byteString.length; i++) {
                    ia[i] = byteString.charCodeAt(i);
                }
                
                return new Blob([ab], { type: mimeType });
            }
            
            // Check if we have recorded audio
            const recordedAudio = sessionStorage.getItem('recordedAudio');
            if (recordedAudio) {
                // Create a form element
                const form = document.createElement('form');
                form.method = 'POST';
                form.enctype = 'multipart/form-data';
                
                // Create a hidden input for the audio data
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'audio_data';
                input.value = recordedAudio;
                
                form.appendChild(input);
                document.body.appendChild(form);
                
                // Submit the form
                form.submit();
                
                document.getElementById("status").innerText = "Sending audio data...";
            } else {
                document.getElementById("status").innerText = "No recorded audio found. Please record audio first.";
            }
            </script>
            <div id="status"></div>
            """
            
            st.components.v1.html(retrieval_script, height=100)
            
            # Note: In a real implementation, we would need a way to get the audio data from JavaScript
            # back to Python. This is a limitation of Streamlit's current API.
            st.warning("Due to Streamlit limitations, we can't automatically transfer the recorded audio to the server. Please use the 'Download Recording' button to save your audio, then upload it in the 'Upload Audio' tab.")

with tab2:
    st.header("Upload Audio File")
    
    # File uploader for audio
    st.write("""
    Upload your audio file here.
    Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, and webm
    """)
    
    uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"])
    
    if uploaded_file is not None:
        # Display the uploaded audio
        st.audio(uploaded_file, format=f"audio/{uploaded_file.type}")
        
        # Create a button to start transcription
        if st.button("Transcribe Uploaded Audio"):
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

# Footer with instructions
st.markdown("---")
st.subheader("How to Use This App")
st.markdown("""
1. **Record Tab**: Record audio directly in your browser
   - Click "Start Recording" and allow microphone access
   - Speak clearly into your microphone
   - Click "Stop Recording" when finished
   - Play back your recording to verify it
   - Download your recording if desired
   - Upload the downloaded file in the "Upload Audio" tab for transcription

2. **Upload Tab**: Upload pre-recorded audio files
   - Select an audio file from your device
   - Play back the audio to verify it
   - Click "Transcribe Uploaded Audio" to process it with Whisper API

For best results, speak clearly and minimize background noise.
""")