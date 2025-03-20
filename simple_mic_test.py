import streamlit as st
import base64

st.set_page_config(
    page_title="Simple Microphone Test",
    page_icon="🎤",
    layout="centered"
)

st.title("🎤 Simple Microphone Test")
st.markdown("This app tests browser microphone access using HTML5 audio recording.")

# HTML/JavaScript to capture audio directly from browser
st.markdown("""
### Browser Microphone Test

This test uses pure HTML5/JavaScript for recording, which works differently than the streamlit-mic-recorder component.
""")

# Using HTML components directly to record audio
record_html = """
<div style="padding: 20px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 20px;">
  <h3>Record Audio</h3>
  <div style="display: flex; gap: 10px; margin-bottom: 15px;">
    <button id="startButton" style="padding: 10px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">Start Recording</button>
    <button id="stopButton" style="padding: 10px; background: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer;" disabled>Stop Recording</button>
  </div>
  <p id="recordingStatus">Not recording</p>
  <div id="audioContainer" style="display: none;">
    <h4>Recorded Audio:</h4>
    <audio id="audioPlayer" controls></audio>
    <div style="margin-top: 10px;">
      <a id="downloadLink" style="display: none; padding: 8px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px;">Download Recording</a>
    </div>
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
const downloadLink = document.getElementById('downloadLink');

startButton.addEventListener('click', async () => {
  try {
    audioContainer.style.display = 'none';
    downloadLink.style.display = 'none';
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
      
      downloadLink.href = audioUrl;
      downloadLink.download = 'recording.wav';
      downloadLink.style.display = 'inline-block';
      
      recordingStatus.textContent = 'Recording complete';
      
      // Notify Streamlit the recording is done
      if (window.parent) {
        const message = {
          type: 'recordingComplete',
          size: audioBlob.size
        };
        window.parent.postMessage(JSON.stringify(message), '*');
      }
    });
    
    mediaRecorder.start();
    startButton.disabled = true;
    stopButton.disabled = false;
    recordingStatus.textContent = 'Recording in progress...';
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

# Create a way to save the recording
st.markdown("### Test Results")

results_placeholder = st.empty()
results_placeholder.info("Click 'Start Recording' above, speak into your microphone, then click 'Stop Recording'.")

# Display troubleshooting info
st.markdown("### Troubleshooting")
st.markdown("""
If you encounter issues:

1. **Check browser permissions** - Make sure you click "Allow" when prompted for microphone access
2. **Try a different browser** - Chrome has the best WebRTC support
3. **Refresh the page** - Sometimes this helps reset permissions
4. **Check if microphone works in other web apps** - Try [Online Mic Test](https://mictests.com/)
""")

# Fall back to using the microphone recorder component
st.markdown("### Alternative Method")
st.markdown("If the HTML5 method above doesn't work, try this alternative:")

try:
    from streamlit_mic_recorder import mic_recorder
    
    recorded_audio = mic_recorder(
        key="alternative_method",
        start_prompt="Start Recording",
        stop_prompt="Stop Recording",
        just_once=True
    )
    
    if recorded_audio:
        st.success(f"Recorded {len(recorded_audio)} bytes of audio!")
        st.audio(recorded_audio)
except Exception as e:
    st.error(f"Alternative method not available: {str(e)}")
    st.info("Try installing with: pip install streamlit-mic-recorder")

# Add footer
st.markdown("---")
st.markdown("Created to diagnose microphone access issues with Streamlit apps.") 