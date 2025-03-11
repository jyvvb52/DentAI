import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
import hashlib
import sqlite3
import time
from openai import OpenAI

# Set page configuration
st.set_page_config(page_title="DentAI - Dental AI Assistant", layout="wide")

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"

# Database setup
def init_db():
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create patients table
    c.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        date_of_birth DATE,
        gender TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create clinical_records table
    c.execute('''
    CREATE TABLE IF NOT EXISTS clinical_records (
        id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL,
        record_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        transcription TEXT,
        ai_analysis TEXT,
        audio_file_path TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    ''')
    
    # Create medical questionnaires table
    c.execute('''
    CREATE TABLE IF NOT EXISTS medical_questionnaires (
        id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL,
        visit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reason_for_visit TEXT,
        responses TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    ''')
    
    # Create dental history table
    c.execute('''
    CREATE TABLE IF NOT EXISTS dental_history (
        id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL,
        last_dental_visit DATE,
        reason_for_last_visit TEXT,
        previous_dentist TEXT,
        brushing_frequency TEXT,
        flossing_frequency TEXT,
        sensitivity TEXT,
        grinding_clenching BOOLEAN,
        orthodontic_treatment BOOLEAN,
        dental_concerns TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    ''')
    
    # Create allergies table
    c.execute('''
    CREATE TABLE IF NOT EXISTS allergies (
        id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL,
        analgesics BOOLEAN,
        antibiotics BOOLEAN,
        latex BOOLEAN,
        metals BOOLEAN,
        dental_materials BOOLEAN,
        other_allergies TEXT,
        vaccinated BOOLEAN,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    ''')
    
    # Create ai_reports table
    c.execute('''
    CREATE TABLE IF NOT EXISTS ai_reports (
        id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL,
        report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        report_text TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    ''')
    
    # Insert a demo user if none exists
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        demo_password = hashlib.sha256("password123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, full_name, email) VALUES (?, ?, ?, ?)",
                 ("demo", demo_password, "Demo User", "demo@example.com"))
    
    # Insert demo patients if none exist
    c.execute("SELECT COUNT(*) FROM patients")
    if c.fetchone()[0] == 0:
        demo_patients = [
            ("John", "Doe", "1980-05-15", "Male", "555-123-4567", "john.doe@example.com", "123 Main St"),
            ("Jane", "Smith", "1992-08-23", "Female", "555-987-6543", "jane.smith@example.com", "456 Oak Ave"),
            ("Robert", "Johnson", "1975-11-30", "Male", "555-456-7890", "robert.j@example.com", "789 Pine Rd")
        ]
        for patient in demo_patients:
            c.execute('''
            INSERT INTO patients (first_name, last_name, date_of_birth, gender, phone, email, address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', patient)
    
    conn.commit()
    conn.close()

# Authentication functions
def login(username, password):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = c.fetchone()
    
    conn.close()
    
    if user:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.current_page = "dashboard"
        return True
    return False

# Page functions
def login_page():
    st.title("DentAI - Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.write("Welcome to DentAI! Please log in to continue.")
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", key="login_btn"):
            if login(username, password):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")
        
        st.write("Demo credentials: Username: demo, Password: password123")

def dashboard_page():
    st.title("DentAI - Dashboard")
    
    # Sidebar navigation
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}!")
        
        if st.button("Patient Management", key="dash_patient_btn"):
            st.session_state.current_page = "patients"
            st.rerun()
        
        if st.button("Clinical Interaction", key="dash_clinical_btn"):
            st.session_state.current_page = "clinical"
            st.rerun()
        
        if st.button("Medical Questionnaire", key="dash_quest_btn"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
        
        if st.button("Logout", key="dash_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.rerun()
    
    # Dashboard content
    st.header("Recent Activity")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Patients")
        conn = sqlite3.connect('data/dentai.db')
        patients_df = pd.read_sql_query(
            "SELECT id, first_name, last_name, date_of_birth FROM patients ORDER BY created_at DESC LIMIT 5",
            conn
        )
        conn.close()
        
        if not patients_df.empty:
            st.dataframe(patients_df)
        else:
            st.info("No patients found")
    
    with col2:
        st.subheader("Recent Clinical Records")
        conn = sqlite3.connect('data/dentai.db')
        records_df = pd.read_sql_query(
            """
            SELECT cr.id, p.first_name || ' ' || p.last_name as patient_name, cr.record_date
            FROM clinical_records cr
            JOIN patients p ON cr.patient_id = p.id
            ORDER BY cr.record_date DESC LIMIT 5
            """,
            conn
        )
        conn.close()
        
        if not records_df.empty:
            st.dataframe(records_df)
        else:
            st.info("No clinical records found")

def patients_page():
    st.title("DentAI - Patient Management")
    
    # Sidebar navigation
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}!")
        
        if st.button("Dashboard", key="pat_dash_btn"):
            st.session_state.current_page = "dashboard"
            st.rerun()
        
        if st.button("Clinical Interaction", key="pat_clinical_btn"):
            st.session_state.current_page = "clinical"
            st.rerun()
        
        if st.button("Medical Questionnaire", key="pat_quest_btn"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
        
        if st.button("Logout", key="pat_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.rerun()
    
    # Patient management tabs
    tab1, tab2, tab3 = st.tabs(["Patient List", "Add Patient", "Search Patient"])
    
    with tab1:
        st.subheader("Patient List")
        conn = sqlite3.connect('data/dentai.db')
        patients_df = pd.read_sql_query(
            "SELECT id, first_name, last_name, date_of_birth, gender, phone, email FROM patients ORDER BY last_name, first_name",
            conn
        )
        conn.close()
        
        if not patients_df.empty:
            st.dataframe(patients_df)
            
            # Select patient for clinical interaction
            patient_id = st.selectbox(
                "Select a patient for clinical interaction:",
                patients_df['id'].tolist(),
                format_func=lambda x: f"{patients_df[patients_df['id'] == x]['first_name'].iloc[0]} {patients_df[patients_df['id'] == x]['last_name'].iloc[0]}"
            )
            
            if st.button("Go to Clinical Interaction", key="pat_list_go_clinical"):
                st.session_state.selected_patient = patient_id
                st.session_state.current_page = "clinical"
                st.rerun()
        else:
            st.info("No patients found")
    
    with tab2:
        st.subheader("Add New Patient")
        with st.form("add_patient_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name")
                last_name = st.text_input("Last Name")
                dob = st.date_input("Date of Birth")
                gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
            
            with col2:
                phone = st.text_input("Phone Number")
                email = st.text_input("Email Address")
                address = st.text_area("Address")
            
            submitted = st.form_submit_button("Add Patient")
            if submitted:
                if first_name and last_name:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    c.execute(
                        "INSERT INTO patients (first_name, last_name, date_of_birth, gender, phone, email, address) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (first_name, last_name, dob, gender, phone, email, address)
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Patient {first_name} {last_name} added successfully!")
                else:
                    st.error("First name and last name are required")
    
    with tab3:
        st.subheader("Search Patient")
        search_term = st.text_input("Enter patient name")
        
        if search_term:
            conn = sqlite3.connect('data/dentai.db')
            search_results = pd.read_sql_query(
                """
                SELECT id, first_name, last_name, date_of_birth, gender, phone, email
                FROM patients
                WHERE first_name LIKE ? OR last_name LIKE ?
                ORDER BY last_name, first_name
                """,
                conn,
                params=(f"%{search_term}%", f"%{search_term}%")
            )
            conn.close()
            
            if not search_results.empty:
                st.dataframe(search_results)
                
                # Select patient for clinical interaction
                patient_id = st.selectbox(
                    "Select a patient for clinical interaction:",
                    search_results['id'].tolist(),
                    format_func=lambda x: f"{search_results[search_results['id'] == x]['first_name'].iloc[0]} {search_results[search_results['id'] == x]['last_name'].iloc[0]}"
                )
                
                if st.button("Go to Clinical Interaction", key="search_go_clinical"):
                    st.session_state.selected_patient = patient_id
                    st.session_state.current_page = "clinical"
                    st.rerun()
            else:
                st.info("No matching patients found")

def clinical_interaction_page():
    st.title("DentAI - Clinical Interaction")
    
    # Sidebar navigation
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}!")
        
        if st.button("Dashboard", key="clin_dash_btn"):
            st.session_state.current_page = "dashboard"
            st.rerun()
        
        if st.button("Patient Management", key="clin_patient_btn"):
            st.session_state.current_page = "patients"
            st.rerun()
        
        if st.button("Medical Questionnaire", key="clin_quest_btn"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
        
        if st.button("Logout", key="clin_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.rerun()
    
    # Check if a patient is selected
    if 'selected_patient' not in st.session_state:
        st.warning("No patient selected. Please select a patient from the Patient Management page.")
        if st.button("Go to Patient Management", key="clin_go_patient_mgmt"):
            st.session_state.current_page = "patients"
            st.rerun()
        return
    
    # Get patient info
    patient_id = st.session_state.selected_patient
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    c.execute("SELECT first_name, last_name, date_of_birth, gender FROM patients WHERE id = ?", (patient_id,))
    patient = c.fetchone()
    conn.close()
    
    if not patient:
        st.error("Patient not found")
        return
    
    # Calculate age
    try:
        birth_date = datetime.strptime(patient[2], "%Y-%m-%d").date()
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        age = "Unknown"
    
    # Display patient info in a card-like format
    st.markdown(f"""
    <div style="background-color:#f0f2f6;padding:15px;border-radius:10px;margin-bottom:20px;">
        <h3 style="margin-top:0;">Patient: {patient[0]} {patient[1]}</h3>
        <p><strong>Age:</strong> {age} | <strong>Gender:</strong> {patient[3]}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for different clinical interaction features
    tabs = st.tabs(["Clinical Interaction", "Previous Records", "AI Analysis"])
    
    # Clinical Interaction Tab
    with tabs[0]:
        st.subheader("Clinical Interaction Recording")
        
        # Initialize session state for recording
        if 'recording' not in st.session_state:
            st.session_state.recording = False
        if 'transcription' not in st.session_state:
            st.session_state.transcription = ""
        if 'recording_time' not in st.session_state:
            st.session_state.recording_time = 0
        
        # Recording controls
        col1, col2 = st.columns(2)
        
        with col1:
            if not st.session_state.recording:
                if st.button("Start Recording", key="start_recording_btn", use_container_width=True):
                    st.session_state.recording = True
                    st.session_state.transcription = ""
                    st.session_state.recording_time = time.time()
                    st.rerun()
            else:
                if st.button("Stop and Analyze", key="stop_analyze_btn", use_container_width=True, type="primary"):
                    recording_duration = time.time() - st.session_state.recording_time
                    st.session_state.recording = False
                    st.success(f"Recording stopped after {recording_duration:.1f} seconds. Analyzing...")
                    
                    # Simulate transcription (in a real app, this would use the Whisper API)
                    st.session_state.transcription = """
                    Doctor: Hello, how are you feeling today?
                    
                    Patient: I've been having some pain in my upper right molar for about two weeks now.
                    
                    Doctor: I see. Can you describe the pain? Is it constant or does it come and go?
                    
                    Patient: It comes and goes. It's especially bad when I drink something cold.
                    
                    Doctor: Any sensitivity to hot foods or drinks?
                    
                    Patient: Not really, just cold things.
                    
                    Doctor: Have you had any previous work done on that tooth or the ones nearby?
                    
                    Patient: Yes, I had a root canal on the tooth next to it about a year ago.
                    
                    Doctor: I'll take a look at that area. Have you noticed any swelling or tenderness in the gums around that tooth?
                    
                    Patient: No swelling, but it is a bit tender when I brush that area.
                    
                    Doctor: And how would you rate the pain on a scale of 1 to 10?
                    
                    Patient: Probably around a 6 when it's at its worst, especially with cold drinks.
                    """
                    st.rerun()
        
        with col2:
            if st.session_state.transcription:
                if st.button("Save Clinical Record", key="save_record_btn", use_container_width=True):
                    # Generate AI analysis (in a real app, this would use GPT-3.5/4)
                    ai_analysis = """
                    ## Clinical Assessment
                    
                    **Chief Complaint:** Intermittent pain in upper right molar for two weeks
                    
                    **Pain Characteristics:**
                    - Intensity: 6/10 at worst
                    - Trigger: Cold sensitivity
                    - Duration: Two weeks
                    - Location: Upper right molar
                    
                    **Relevant History:**
                    - Previous root canal on adjacent tooth (1 year ago)
                    - Tenderness when brushing the area
                    - No swelling reported
                    
                    **Potential Diagnoses:**
                    1. Dentin hypersensitivity
                    2. Cracked tooth
                    3. Recurrent decay
                    4. Failed root canal on adjacent tooth with referred pain
                    
                    **Recommended Actions:**
                    - Clinical examination of tooth #14 and adjacent teeth
                    - Bitewing X-ray
                    - Percussion and cold testing
                    - Evaluate for visible cracks or decay
                    """
                    
                    # Save to database
                    try:
                        conn = sqlite3.connect('data/dentai.db')
                        c = conn.cursor()
                        c.execute(
                            "INSERT INTO clinical_records (patient_id, transcription, ai_analysis) VALUES (?, ?, ?)",
                            (patient_id, st.session_state.transcription, ai_analysis)
                        )
                        conn.commit()
                        conn.close()
                        
                        st.success("Clinical record saved successfully!")
                    except Exception as e:
                        st.error(f"Error saving record: {str(e)}")
        
        # Display recording status and transcription
        if st.session_state.recording:
            # Create a pulsing red dot animation for recording indicator
            st.markdown("""
            <style>
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.3; }
                100% { opacity: 1; }
            }
            .recording-indicator {
                display: inline-block;
                width: 15px;
                height: 15px;
                background-color: red;
                border-radius: 50%;
                margin-right: 10px;
                animation: pulse 1.5s infinite;
            }
            </style>
            <div>
                <div class="recording-indicator"></div>
                <span style="font-size:18px;font-weight:bold;">Recording in progress...</span>
            </div>
            <p>Speak clearly into your microphone. The transcription will appear here after stopping.</p>
            <p style="color:gray;font-style:italic;">Note: Actual recording is simulated in the cloud version.</p>
            """, unsafe_allow_html=True)
            
            # Show recording time
            elapsed = time.time() - st.session_state.recording_time
            st.write(f"Recording time: {elapsed:.1f} seconds")
        
        if st.session_state.transcription:
            st.subheader("Transcription")
            st.text_area("Conversation", st.session_state.transcription, height=300, key="transcription_display")
            
            st.subheader("AI Analysis")
            
            # Generate AI analysis on demand
            if st.button("Generate AI Analysis", key="gen_analysis_btn"):
                with st.spinner("Analyzing conversation..."):
                    # Simulate AI processing time
                    time.sleep(1.5)
                    
                    # Display AI analysis
                    st.markdown("""
                    ## Clinical Assessment
                    
                    **Chief Complaint:** Intermittent pain in upper right molar for two weeks
                    
                    **Pain Characteristics:**
                    - Intensity: 6/10 at worst
                    - Trigger: Cold sensitivity
                    - Duration: Two weeks
                    - Location: Upper right molar
                    
                    **Relevant History:**
                    - Previous root canal on adjacent tooth (1 year ago)
                    - Tenderness when brushing the area
                    - No swelling reported
                    
                    **Potential Diagnoses:**
                    1. Dentin hypersensitivity
                    2. Cracked tooth
                    3. Recurrent decay
                    4. Failed root canal on adjacent tooth with referred pain
                    
                    **Recommended Actions:**
                    - Clinical examination of tooth #14 and adjacent teeth
                    - Bitewing X-ray
                    - Percussion and cold testing
                    - Evaluate for visible cracks or decay
                    """)
    
    # Previous Records Tab
    with tabs[1]:
        st.subheader("Previous Clinical Records")
        
        try:
            conn = sqlite3.connect('data/dentai.db')
            records_df = pd.read_sql_query(
                "SELECT id, record_date, transcription, ai_analysis FROM clinical_records WHERE patient_id = ? ORDER BY record_date DESC",
                conn,
                params=(patient_id,)
            )
            conn.close()
            
            if not records_df.empty:
                for i, row in records_df.iterrows():
                    with st.expander(f"Clinical Record from {row['record_date']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### Transcription")
                            st.text_area("", row['transcription'], height=200, key=f"trans_{i}")
                        
                        with col2:
                            st.markdown("#### AI Analysis")
                            st.markdown(row['ai_analysis'])
                        
                        # Export options
                        if st.button(f"Export as PDF", key=f"export_pdf_{i}"):
                            st.info("PDF export functionality would be implemented here in a production app.")
                        
                        if st.button(f"Email to Patient", key=f"email_{i}"):
                            st.info("Email functionality would be implemented here in a production app.")
            else:
                st.info("No previous clinical records found for this patient.")
        except Exception as e:
            st.error(f"Error retrieving clinical records: {str(e)}")
    
    # AI Analysis Tab
    with tabs[2]:
        st.subheader("Comprehensive AI Analysis")
        
        # Get patient data for analysis
        try:
            conn = sqlite3.connect('data/dentai.db')
            
            # Get medical questionnaire data
            c = conn.cursor()
            c.execute("SELECT responses FROM medical_questionnaires WHERE patient_id = ?", (patient_id,))
            medical_data = c.fetchone()
            
            # Get dental history
            c.execute("SELECT * FROM dental_history WHERE patient_id = ?", (patient_id,))
            dental_data = c.fetchone()
            
            # Get allergies
            c.execute("SELECT * FROM allergies WHERE patient_id = ?", (patient_id,))
            allergies_data = c.fetchone()
            
            # Get clinical records
            clinical_records = pd.read_sql_query(
                "SELECT transcription, ai_analysis FROM clinical_records WHERE patient_id = ? ORDER BY record_date DESC",
                conn,
                params=(patient_id,)
            )
            
            conn.close()
            
            # Check if we have enough data for analysis
            if medical_data or dental_data or not clinical_records.empty:
                if st.button("Generate Comprehensive Analysis", key="comp_analysis_btn"):
                    with st.spinner("Analyzing all patient data..."):
                        # Simulate AI processing time
                        time.sleep(2)
                        
                        st.markdown(f"""
                        # Comprehensive Health Analysis for {patient[0]} {patient[1]}
                        
                        ## Patient Overview
                        - **Age:** {age}
                        - **Gender:** {patient[3]}
                        - **General Health:** {"Good" if medical_data else "Unknown"}
                        
                        ## Dental Health Summary
                        {f"- Last dental visit: {dental_data[2]}" if dental_data and dental_data[2] else "- No recent dental visit recorded"}
                        {f"- Brushing frequency: {dental_data[4]}" if dental_data and dental_data[4] else "- Brushing habits not recorded"}
                        {f"- Flossing frequency: {dental_data[5]}" if dental_data and dental_data[5] else "- Flossing habits not recorded"}
                        
                        ## Current Concerns
                        - Intermittent pain in upper right molar
                        - Cold sensitivity
                        - History of root canal treatment
                        
                        ## Risk Factors
                        {f"- Grinding/clenching: {'Yes' if dental_data and dental_data[7] else 'No'}" if dental_data else "- Grinding/clenching: Unknown"}
                        {f"- Allergies: {'Present' if allergies_data and any(allergies_data[1:6]) else 'None reported'}" if allergies_data else "- Allergies: Unknown"}
                        
                        ## Treatment Recommendations
                        1. Comprehensive oral examination with focus on upper right quadrant
                        2. Bitewing and periapical radiographs of the affected area
                        3. Evaluate for cracked tooth syndrome
                        4. Consider desensitizing treatment for cold sensitivity
                        5. Assess adjacent tooth with previous root canal for potential issues
                        
                        ## Preventive Recommendations
                        1. Regular 6-month recall appointments
                        2. Daily flossing
                        3. Use of desensitizing toothpaste
                        4. Night guard if grinding/clenching is confirmed
                        
                        ## Long-term Considerations
                        - Monitor for signs of pulpal involvement
                        - Evaluate occlusion and potential need for occlusal adjustment
                        - Consider fluoride treatments for sensitivity management
                        """)
                        
                        # Save analysis to database
                        try:
                            analysis_text = f"""
                            # Comprehensive Health Analysis for {patient[0]} {patient[1]}
                            
                            ## Patient Overview
                            - Age: {age}
                            - Gender: {patient[3]}
                            - General Health: {"Good" if medical_data else "Unknown"}
                            
                            ## Dental Health Summary
                            {f"- Last dental visit: {dental_data[2]}" if dental_data and dental_data[2] else "- No recent dental visit recorded"}
                            {f"- Brushing frequency: {dental_data[4]}" if dental_data and dental_data[4] else "- Brushing habits not recorded"}
                            {f"- Flossing frequency: {dental_data[5]}" if dental_data and dental_data[5] else "- Flossing habits not recorded"}
                            
                            ## Current Concerns
                            - Intermittent pain in upper right molar
                            - Cold sensitivity
                            - History of root canal treatment
                            
                            ## Risk Factors
                            {f"- Grinding/clenching: {'Yes' if dental_data and dental_data[7] else 'No'}" if dental_data else "- Grinding/clenching: Unknown"}
                            {f"- Allergies: {'Present' if allergies_data and any(allergies_data[1:6]) else 'None reported'}" if allergies_data else "- Allergies: Unknown"}
                            
                            ## Treatment Recommendations
                            1. Comprehensive oral examination with focus on upper right quadrant
                            2. Bitewing and periapical radiographs of the affected area
                            3. Evaluate for cracked tooth syndrome
                            4. Consider desensitizing treatment for cold sensitivity
                            5. Assess adjacent tooth with previous root canal for potential issues
                            
                            ## Preventive Recommendations
                            1. Regular 6-month recall appointments
                            2. Daily flossing
                            3. Use of desensitizing toothpaste
                            4. Night guard if grinding/clenching is confirmed
                            
                            ## Long-term Considerations
                            - Monitor for signs of pulpal involvement
                            - Evaluate occlusion and potential need for occlusal adjustment
                            - Consider fluoride treatments for sensitivity management
                            """
                            
                            conn = sqlite3.connect('data/dentai.db')
                            c = conn.cursor()
                            c.execute(
                                "INSERT INTO ai_reports (patient_id, report_text) VALUES (?, ?)",
                                (patient_id, analysis_text)
                            )
                            conn.commit()
                            conn.close()
                            
                            st.success("Comprehensive analysis saved to patient records!")
                        except Exception as e:
                            st.error(f"Error saving analysis: {str(e)}")
            else:
                st.info("Insufficient data for comprehensive analysis. Please complete medical questionnaires and record a clinical interaction.")
        except Exception as e:
            st.error(f"Error retrieving patient data: {str(e)}")
        
        # Display previous AI reports
        try:
            conn = sqlite3.connect('data/dentai.db')
            c = conn.cursor()
            c.execute(
                "SELECT id, report_date, report_text FROM ai_reports WHERE patient_id = ? ORDER BY report_date DESC",
                (patient_id,)
            )
            reports = c.fetchall()
            conn.close()
            
            if reports:
                st.write("### Previous AI Reports")
                for i, report in enumerate(reports):
                    with st.expander(f"Report from {report[1]}"):
                        st.markdown(report[2])
                        
                        # Export options
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"Export as PDF", key=f"report_pdf_{i}"):
                                st.info("PDF export functionality would be implemented here in a production app.")
                        with col2:
                            if st.button(f"Email to Patient", key=f"report_email_{i}"):
                                st.info("Email functionality would be implemented here in a production app.")
            
        except Exception as e:
            st.error(f"Error retrieving AI reports: {str(e)}")

# Main app
def main():
    # Initialize database
    init_db()
    
    # Display appropriate page based on session state
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.current_page == "dashboard":
            dashboard_page()
        elif st.session_state.current_page == "patients":
            patients_page()
        elif st.session_state.current_page == "clinical":
            clinical_interaction_page()
        elif st.session_state.current_page == "questionnaire":
            questionnaire_page()

if __name__ == "__main__":
    main() 