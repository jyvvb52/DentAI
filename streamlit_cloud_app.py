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
    conn = sqlite3.connect('dentai.db')
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
    conn = sqlite3.connect('dentai.db')
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
        
        if st.button("Login"):
            if login(username, password):
                st.success("Login successful!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
        
        st.write("Demo credentials: Username: demo, Password: password123")

def dashboard_page():
    st.title("DentAI - Dashboard")
    
    # Sidebar navigation
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}!")
        
        if st.button("Patient Management"):
            st.session_state.current_page = "patients"
            st.experimental_rerun()
        
        if st.button("Clinical Interaction"):
            st.session_state.current_page = "clinical"
            st.experimental_rerun()
        
        if st.button("Medical Questionnaire"):
            st.session_state.current_page = "questionnaire"
            st.experimental_rerun()
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.experimental_rerun()
    
    # Dashboard content
    st.header("Recent Activity")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Patients")
        conn = sqlite3.connect('dentai.db')
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
        conn = sqlite3.connect('dentai.db')
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
        
        if st.button("Dashboard"):
            st.session_state.current_page = "dashboard"
            st.experimental_rerun()
        
        if st.button("Clinical Interaction"):
            st.session_state.current_page = "clinical"
            st.experimental_rerun()
        
        if st.button("Medical Questionnaire"):
            st.session_state.current_page = "questionnaire"
            st.experimental_rerun()
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.experimental_rerun()
    
    # Patient management tabs
    tab1, tab2, tab3 = st.tabs(["Patient List", "Add Patient", "Search Patient"])
    
    with tab1:
        st.subheader("Patient List")
        conn = sqlite3.connect('dentai.db')
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
            
            if st.button("Go to Clinical Interaction"):
                st.session_state.selected_patient = patient_id
                st.session_state.current_page = "clinical"
                st.experimental_rerun()
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
                    conn = sqlite3.connect('dentai.db')
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
            conn = sqlite3.connect('dentai.db')
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
                
                if st.button("Go to Clinical Interaction"):
                    st.session_state.selected_patient = patient_id
                    st.session_state.current_page = "clinical"
                    st.experimental_rerun()
            else:
                st.info("No matching patients found")

def clinical_interaction_page():
    st.title("DentAI - Clinical Interaction")
    
    # Sidebar navigation
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}!")
        
        if st.button("Dashboard"):
            st.session_state.current_page = "dashboard"
            st.experimental_rerun()
        
        if st.button("Patient Management"):
            st.session_state.current_page = "patients"
            st.experimental_rerun()
        
        if st.button("Medical Questionnaire"):
            st.session_state.current_page = "questionnaire"
            st.experimental_rerun()
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.experimental_rerun()
    
    # Check if a patient is selected
    if 'selected_patient' not in st.session_state:
        st.warning("No patient selected. Please select a patient from the Patient Management page.")
        if st.button("Go to Patient Management"):
            st.session_state.current_page = "patients"
            st.experimental_rerun()
        return
    
    # Get patient info
    patient_id = st.session_state.selected_patient
    conn = sqlite3.connect('dentai.db')
    c = conn.cursor()
    c.execute("SELECT first_name, last_name FROM patients WHERE id = ?", (patient_id,))
    patient = c.fetchone()
    conn.close()
    
    if not patient:
        st.error("Patient not found")
        return
    
    st.header(f"Clinical Interaction with {patient[0]} {patient[1]}")
    
    # Initialize session state for recording
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'transcription' not in st.session_state:
        st.session_state.transcription = ""
    
    # Recording controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Start Recording"):
            st.session_state.recording = True
            st.session_state.transcription = ""
            st.success("Recording started... (Simulated in Cloud version)")
    
    with col2:
        if st.button("Stop and Analyze"):
            if st.session_state.recording:
                st.session_state.recording = False
                st.success("Recording stopped. Analyzing...")
                
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
                """
    
    with col3:
        if st.button("Save Record"):
            if st.session_state.transcription:
                # Generate AI analysis (in a real app, this would use GPT-3.5/4)
                ai_analysis = """
                Chief complaint: Tooth sensitivity in upper right molar
                Duration: Two weeks
                Pain characteristics: Intermittent, triggered by cold stimuli
                Relevant history: Previous root canal on adjacent tooth
                Possible diagnoses:
                1. Dentin hypersensitivity
                2. Cracked tooth
                3. Recurrent decay
                Recommended actions:
                - Clinical examination of tooth #14
                - Bitewing X-ray
                - Assess for visible cracks or decay
                """
                
                # Save to database
                conn = sqlite3.connect('dentai.db')
                c = conn.cursor()
                c.execute(
                    "INSERT INTO clinical_records (patient_id, transcription, ai_analysis) VALUES (?, ?, ?)",
                    (patient_id, st.session_state.transcription, ai_analysis)
                )
                conn.commit()
                conn.close()
                
                st.success("Clinical record saved successfully!")
    
    # Display recording status and transcription
    if st.session_state.recording:
        st.markdown("### 🔴 Recording in progress...")
        st.markdown("Speak clearly into your microphone. The transcription will appear here.")
        st.info("Note: Actual recording is disabled in the cloud version.")
    
    if st.session_state.transcription:
        st.subheader("Transcription")
        st.write(st.session_state.transcription)
        
        st.subheader("AI Analysis")
        st.write("""
        Based on the transcription, the following information was extracted:
        - Chief complaint: Tooth sensitivity in the upper right quadrant
        - Duration: 2 weeks
        - Pain level: Moderate, triggered by cold beverages
        - Relevant history: Previous root canal on adjacent tooth
        - Recommended actions: Examination of tooth #14, possible X-ray
        """)
    
    # Previous clinical records
    st.subheader("Previous Clinical Records")
    conn = sqlite3.connect('dentai.db')
    records_df = pd.read_sql_query(
        "SELECT id, record_date, transcription, ai_analysis FROM clinical_records WHERE patient_id = ? ORDER BY record_date DESC",
        conn,
        params=(patient_id,)
    )
    conn.close()
    
    if not records_df.empty:
        for i, row in records_df.iterrows():
            with st.expander(f"Record from {row['record_date']}"):
                st.write("**Transcription:**")
                st.write(row['transcription'])
                st.write("**AI Analysis:**")
                st.write(row['ai_analysis'])
    else:
        st.info("No previous clinical records found for this patient.")

def questionnaire_page():
    st.title("DentAI - Medical Questionnaire")
    
    # Sidebar navigation
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}!")
        
        if st.button("Dashboard"):
            st.session_state.current_page = "dashboard"
            st.experimental_rerun()
        
        if st.button("Patient Management"):
            st.session_state.current_page = "patients"
            st.experimental_rerun()
        
        if st.button("Clinical Interaction"):
            st.session_state.current_page = "clinical"
            st.experimental_rerun()
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.experimental_rerun()
    
    st.header("Medical Questionnaire")
    st.write("This feature is under development for the cloud version.")

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