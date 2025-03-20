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
    
    # Add troubleshooting section
    with st.expander("Troubleshooting Audio Issues"):
        st.markdown("""
        ### Audio Playback Troubleshooting
        
        If you can't hear your recording when playing it back, try these solutions:
        
        1. **Make sure your system volume is turned up** and not muted
        2. **Try a different browser** - Chrome or Firefox work best for audio recording
        3. **Check browser permissions** - Make sure you granted microphone access
        4. **Adjust input level** - Make sure your microphone input volume is high enough in your system settings
        5. **Record for longer** - Very short recordings might not work properly
        
        After recording, you should see the file size displayed. If it shows "0 KB" or a very small size, no audio was captured.
        """)
    
    # Create HTML/JavaScript component for audio recording with additional debugging
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
    #testAudioButton {
        background-color: #FF9800;
        color: white;
    }
    .status {
        margin: 10px 0;
        font-weight: bold;
    }
    #debugInfo {
        margin-top: 10px;
        font-size: 12px;
        font-family: monospace;
        white-space: pre-wrap;
        padding: 10px;
        background-color: #f5f5f5;
        border-radius: 4px;
        max-height: 100px;
        overflow-y: auto;
        display: none;
    }
    </style>

    <div class="recording-controls">
        <div>
            <button id="startButton" onclick="startRecording()">Start Recording</button>
            <button id="stopButton" onclick="stopRecording()" disabled>Stop Recording</button>
            <button id="downloadButton" onclick="downloadRecording()" disabled>Download Recording</button>
            <button id="testAudioButton" onclick="playTestSound()">Test Audio Output</button>
        </div>
        <div id="recordingStatus" class="status"></div>
        <audio id="audioPlayback" controls style="display: none; width: 100%;"></audio>
        <div id="debugInfo"></div>
    </div>

    <script>
    let mediaRecorder;
    let audioChunks = [];
    let audioBlob = null;
    let audioUrl = '';
    let debugLog = [];
    
    // Function to log debug info
    function debug(msg) {
        const date = new Date();
        const timestamp = date.toLocaleTimeString() + '.' + date.getMilliseconds();
        const logMsg = `${timestamp}: ${msg}`;
        debugLog.push(logMsg);
        console.log(logMsg);
        
        const debugInfoElem = document.getElementById('debugInfo');
        debugInfoElem.textContent = debugLog.join('\\n');
        debugInfoElem.style.display = 'block';
        
        // Keep only the most recent messages
        if (debugLog.length > 20) {
            debugLog.shift();
        }
    }
    
    // Function to play a test sound
    function playTestSound() {
        debug("Playing test sound...");
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(440, audioContext.currentTime); // A4 note
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);
        oscillator.start();
        setTimeout(function() {
            oscillator.stop();
            debug("Test sound ended");
        }, 1000);
    }

    // Check for browser audio support
    function checkBrowserSupport() {
        debug("Checking browser audio support...");
        
        // Check MediaRecorder
        if (!window.MediaRecorder) {
            debug("ERROR: MediaRecorder not supported");
            return false;
        }
        
        // Check getUserMedia
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            debug("ERROR: getUserMedia not supported");
            return false;
        }
        
        // Check AudioContext
        if (!window.AudioContext && !window.webkitAudioContext) {
            debug("ERROR: AudioContext not supported");
            return false;
        }
        
        // Check Blob support
        if (!window.Blob) {
            debug("ERROR: Blob not supported");
            return false;
        }
        
        debug("Browser supports all required audio APIs");
        
        // Check supported MIME types
        let supportedTypes = [];
        ['audio/webm', 'audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'].forEach(type => {
            if (MediaRecorder.isTypeSupported(type)) {
                supportedTypes.push(type);
            }
        });
        
        debug("Supported audio MIME types: " + supportedTypes.join(', '));
        return true;
    }

    // Check browser support on load
    document.addEventListener('DOMContentLoaded', checkBrowserSupport);

    async function startRecording() {
        document.getElementById('startButton').disabled = true;
        document.getElementById('stopButton').disabled = false;
        document.getElementById('downloadButton').disabled = true;
        document.getElementById('recordingStatus').innerText = "Recording... Speak now!";
        document.getElementById('audioPlayback').style.display = 'none';
        
        audioChunks = [];
        debug("Starting recording...");
        
        try {
            debug("Requesting microphone access");
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });
            
            debug("Microphone access granted");
            
            // Check for supported MIME types
            let mimeType = 'audio/webm;codecs=opus';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                if (MediaRecorder.isTypeSupported('audio/webm')) {
                    mimeType = 'audio/webm';
                } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
                    mimeType = 'audio/ogg;codecs=opus';
                } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
                    mimeType = 'audio/mp4';
                }
            }
            
            debug(`Using MIME type: ${mimeType}`);
            
            // Check audio levels before recording
            const audioContext = new AudioContext();
            const analyser = audioContext.createAnalyser();
            const microphone = audioContext.createMediaStreamSource(stream);
            const scriptProcessor = audioContext.createScriptProcessor(2048, 1, 1);
            
            analyser.smoothingTimeConstant = 0.8;
            analyser.fftSize = 1024;
            
            microphone.connect(analyser);
            analyser.connect(scriptProcessor);
            scriptProcessor.connect(audioContext.destination);
            
            scriptProcessor.onaudioprocess = function() {
                const array = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(array);
                const arraySum = array.reduce((a, value) => a + value, 0);
                const average = arraySum / array.length;
                debug(`Mic input level: ${Math.round(average)}`);
                
                // Only need to check once
                scriptProcessor.disconnect();
                analyser.disconnect();
                microphone.disconnect();
                audioContext.close();
            };
            
            mediaRecorder = new MediaRecorder(stream, {
                mimeType: mimeType,
                audioBitsPerSecond: 128000
            });
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    debug(`Received audio chunk: ${event.data.size} bytes`);
                    audioChunks.push(event.data);
                } else {
                    debug("Warning: Received empty audio chunk");
                }
            };
            
            mediaRecorder.onstop = () => {
                debug(`Recording stopped. Total chunks: ${audioChunks.length}`);
                
                if (audioChunks.length === 0 || (audioChunks.length === 1 && audioChunks[0].size === 0)) {
                    document.getElementById('recordingStatus').innerText = "No audio data recorded. Please try again.";
                    document.getElementById('startButton').disabled = false;
                    debug("ERROR: No audio data was recorded");
                    return;
                }
                
                audioBlob = new Blob(audioChunks, { type: mimeType });
                debug(`Created audio blob: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
                
                audioUrl = URL.createObjectURL(audioBlob);
                debug(`Created audio URL: ${audioUrl}`);
                
                const audioPlayback = document.getElementById('audioPlayback');
                audioPlayback.src = audioUrl;
                audioPlayback.style.display = 'block';
                audioPlayback.volume = 1.0; // Ensure volume is at maximum
                audioPlayback.controls = true;
                
                document.getElementById('recordingStatus').innerText = 
                    `Recording complete (${(audioBlob.size/1024).toFixed(1)} KB). You can play it back above.`;
                document.getElementById('downloadButton').disabled = false;
                
                // Try to play automatically to test
                audioPlayback.oncanplaythrough = function() {
                    debug("Audio ready for playback");
                    // Uncomment to auto-play (may be blocked by browsers)
                    // audioPlayback.play();
                };
                
                audioPlayback.onerror = function(e) {
                    debug(`Audio playback error: ${e}`);
                };
                
                // Convert to base64 for use with Streamlit
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);
                reader.onloadend = () => {
                    const base64Audio = reader.result;
                    debug(`Converted to base64: ${base64Audio.substring(0, 50)}...`);
                    // Store in sessionStorage for retrieval
                    sessionStorage.setItem('recordedAudio', base64Audio);
                    sessionStorage.setItem('audioSize', audioBlob.size);
                    
                    // Notify that audio is ready for transcription
                    document.dispatchEvent(new CustomEvent('audioRecorded'));
                };
            };
            
            mediaRecorder.onerror = (event) => {
                debug(`MediaRecorder error: ${event.error}`);
            };
            
            // Ensure we get data at regular intervals
            debug("Starting MediaRecorder");
            mediaRecorder.start(1000); // Collect data every second
        } catch (err) {
            debug(`ERROR accessing microphone: ${err.message}`);
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
            
            debug(`Stopping MediaRecorder (state: ${mediaRecorder.state})`);
            mediaRecorder.stop();
            
            // Stop all tracks to release microphone
            mediaRecorder.stream.getTracks().forEach(track => {
                debug(`Stopping track: ${track.kind}`);
                track.stop();
            });
        } else {
            debug("Cannot stop recording - MediaRecorder not active");
        }
    }

    function downloadRecording() {
        if (audioBlob) {
            debug(`Downloading audio (${audioBlob.size} bytes)`);
            const a = document.createElement('a');
            a.href = audioUrl;
            a.download = 'recording.webm';
            a.click();
        } else {
            debug("No audio to download");
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