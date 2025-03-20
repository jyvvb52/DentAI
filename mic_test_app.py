import streamlit as st
import os
import time
import sys
import platform
from streamlit_mic_recorder import mic_recorder
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

# Set page config
st.set_page_config(
    page_title="Microphone Test App", 
    page_icon="🎙️",
    layout="centered"
)

def main():
    st.title("🎙️ Microphone Testing App")
    st.write("This is a standalone app to test if your microphone works with Streamlit.")
    
    # Display system information
    st.subheader("System Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**OS:** {platform.system()} {platform.release()}")
        st.write(f"**Python:** {sys.version.split()[0]}")
        st.write(f"**Streamlit:** {st.__version__}")
    
    with col2:
        st.write(f"**Mic Recorder Available:** {MIC_RECORDER_AVAILABLE}")
        st.write(f"**Browser User-Agent:** See browser information section")
    
    # Browser information
    st.subheader("Browser Information")
    st.info("Your browser must support WebRTC for microphone access to work. Chrome is recommended.")
    
    # Basic microphone test
    st.subheader("Basic Microphone Test")
    st.write("Click the button below to test recording. This will first request microphone permission.")
    
    if MIC_RECORDER_AVAILABLE:
        test_audio = mic_recorder(
            key="basic_test",
            start_prompt="Start Basic Test",
            stop_prompt="Stop Test", 
            just_once=True,
            use_container_width=True
        )
        
        if test_audio:
            st.success(f"✅ Success! Received {len(test_audio)} bytes of audio data")
            st.audio(test_audio)
            
            # Save the test audio
            try:
                os.makedirs("test_output", exist_ok=True)
                file_path = f"test_output/test_recording_{int(time.time())}.wav"
                with open(file_path, "wb") as f:
                    f.write(test_audio)
                st.success(f"Audio saved to {file_path}")
                
                # Display file info
                file_size = os.path.getsize(file_path)
                st.write(f"File size: {file_size} bytes")
            except Exception as e:
                st.error(f"Failed to save audio file: {str(e)}")
        else:
            st.info("No audio recorded yet. Please click the button above to start recording.")
    else:
        st.error("streamlit-mic-recorder is not available. Please restart the app after installation.")
    
    # Advanced testing options
    st.subheader("Advanced Testing")
    
    # Test with different recorder configurations
    if st.checkbox("Try alternative recorder configuration"):
        st.write("This uses different settings that might work better with some browsers.")
        
        if MIC_RECORDER_AVAILABLE:
            alt_audio = mic_recorder(
                key="alt_test",
                start_prompt="Start Alternative Test",
                stop_prompt="Stop", 
                just_once=True,
                use_container_width=False,
                format="audio/wav"  # Explicitly set format
            )
            
            if alt_audio:
                st.success(f"✅ Alternative test successful! Received {len(alt_audio)} bytes")
                st.audio(alt_audio)
        else:
            st.error("streamlit-mic-recorder is not available.")
    
    # Browser permission guide
    st.subheader("Browser Permission Guide")
    
    browser_tabs = st.tabs(["Chrome", "Firefox", "Edge", "Safari"])
    
    with browser_tabs[0]:
        st.markdown("""
        ### Google Chrome
        
        1. Look for the microphone icon in the address bar
        2. Click it and select "Allow" for the microphone permission
        3. If denied previously, click the lock/info icon → Site Settings → Reset Permissions
        
        **For persistent problems:**
        - Type `chrome://settings/content/microphone` in your address bar
        - Ensure this site is not in the "Blocked" section
        - Try adding this site to the "Allowed" section manually
        """)
    
    with browser_tabs[1]:
        st.markdown("""
        ### Firefox
        
        1. Look for the microphone icon in the address bar
        2. Click it and select "Allow" for the microphone access
        
        **For persistent problems:**
        - Click the lock icon in the address bar
        - Select "Connection secure"
        - Click "More Information"
        - Go to the "Permissions" tab
        - Find "Use the Microphone" and set to "Allow"
        """)
    
    with browser_tabs[2]:
        st.markdown("""
        ### Microsoft Edge
        
        1. Look for the microphone icon in the address bar
        2. Click it and select "Allow" for microphone access
        
        **For persistent problems:**
        - Click the lock icon in the address bar
        - Select "Site permissions"
        - Allow microphone access
        """)
    
    with browser_tabs[3]:
        st.markdown("""
        ### Safari
        
        1. When prompted, click "Allow" for microphone access
        2. If denied, go to Safari Preferences → Websites → Microphone
        3. Find this website and select "Allow"
        
        **Note:** Safari has limited WebRTC support and may not work as well as Chrome or Edge.
        """)
    
    # Troubleshooting section
    st.subheader("Troubleshooting Tips")
    st.markdown("""
    If you're still having issues:
    
    1. **Try a different browser** - Chrome works best with WebRTC
    2. **Check system permissions** - Make sure your OS allows browser microphone access
    3. **Check multiple tabs** - Close other tabs that might be using the microphone
    4. **Restart browser** - Sometimes a complete browser restart helps
    5. **Check hardware** - Ensure your microphone isn't muted at the hardware level
    """)
    
    # Results section
    st.subheader("Test Results")
    
    if st.button("Run Diagnostic Test"):
        results = []
        
        # Test 1: Is mic_recorder available?
        results.append(("Mic recorder component", "Available" if MIC_RECORDER_AVAILABLE else "Not available"))
        
        # Test 2: Can we create the data directory?
        try:
            os.makedirs("test_output", exist_ok=True)
            results.append(("File system access", "Working"))
        except Exception as e:
            results.append(("File system access", f"Error: {str(e)}"))
        
        # Display results
        for test, result in results:
            status = "✅" if "Error" not in result and "Not" not in result else "❌"
            st.write(f"{status} **{test}:** {result}")

    # API Key
    api_key = st.text_input("OpenAI API Key", type="password")

    # Record audio
    audio = mic_recorder(start_prompt="Start", stop_prompt="Stop", just_once=True)

    if audio and api_key:
        # Save audio
        with open("temp_audio.wav", "wb") as f:
            f.write(audio)
        
        # Transcribe
        st.info("Transcribing...")
        client = OpenAI(api_key=api_key)
        with open("temp_audio.wav", "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        # Show result
        st.success(f"Transcription: {transcription.text}")

if __name__ == "__main__":
    main() 