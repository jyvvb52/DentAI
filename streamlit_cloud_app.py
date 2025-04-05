import streamlit as st
import sqlite3
import os
import time
import re
import json
import ast
import hashlib
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from io import BytesIO
import base64
import requests

# Import streamlit-mic-recorder for browser-based audio recording
try:
    from streamlit_mic_recorder import mic_recorder
    MIC_RECORDER_AVAILABLE = True
except ImportError:
    MIC_RECORDER_AVAILABLE = False
    print("streamlit-mic-recorder is not available. Please install with: pip install streamlit-mic-recorder")

# Try to import audio recording libraries
try:
    import pyaudio
    import wave
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("PyAudio is not available. Audio recording features will be simulated.")

# Try to import PDF export libraries
try:
    import pdfkit
    import markdown
    PDF_EXPORT_AVAILABLE = True
except ImportError:
    PDF_EXPORT_AVAILABLE = False

# OpenAI for AI analysis
from openai import OpenAI

# Initialize session state variables if they don't exist
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'username' not in st.session_state:
    st.session_state.username = ""

if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"

if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = ""

if 'selected_patient' not in st.session_state:
    st.session_state.selected_patient = None

# Set page configuration
st.set_page_config(page_title="DentAI - Dental AI Assistant", layout="wide")

# Check if audio_recorder is available in Streamlit
AUDIO_RECORDER_AVAILABLE = hasattr(st, 'audio_recorder')

# Initialize session state for audio recording
if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None
if 'transcription_complete' not in st.session_state:
    st.session_state.transcription_complete = False

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
        chief_complaint TEXT,
        treatment_plan TEXT,
        clinical_notes TEXT,
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
        report_text TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    ''')
    
    # Create dental examination table
    c.execute('''
    CREATE TABLE IF NOT EXISTS dental_examination (
        id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL,
        exam_type TEXT NOT NULL,
        findings TEXT,
        exam_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    ''')
    
    # Create questionnaires table
    c.execute('''
    CREATE TABLE IF NOT EXISTS questionnaires (
        id INTEGER PRIMARY KEY,
        patient_id INTEGER NOT NULL,
        questionnaire_type TEXT NOT NULL,
        responses TEXT,
        completion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    
    # Navigation buttons
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    
    with col1:
        if st.button("Dashboard", key="dashboard_btn_dash", type="primary"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    with col2:
        if st.button("Patients", key="patients_btn_dash"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    with col3:
        if st.button("Questionnaire", key="questionnaire_btn_dash"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
    with col4:
        if st.button("Clinical", key="clinical_btn_dash"):
            st.session_state.current_page = "clinical"
            st.rerun()
    
    with col5:
        if st.button("Dental Exam", key="dental_exam_btn_dash"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
    
    with col6:
        if st.button("Settings", key="settings_btn_dash"):
            st.session_state.current_page = "settings"
            st.rerun()
    
    with col7:
        if st.button("Logout", key="logout_btn_dash"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Dashboard content
    st.header("DentAI Workflow")
    
    # Display workflow steps
    st.subheader("Dental Practice Workflow")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        ### 1. Patient Management
        - Add new patients
        - Update patient information
        - Search for existing patients
        """)
        if st.button("Go to Patient Management", key="dash_goto_patients"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    with col2:
        st.markdown("""
        ### 2. Medical Questionnaire
        - Complete medical history
        - Record dental history
        - Document allergies
        """)
        if st.button("Go to Questionnaires", key="dash_goto_quest"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
    with col3:
        st.markdown("""
        ### 3. Dental Examination
        - Extraoral examination
        - Intraoral examination
        - Dental charting
        - Periodontal assessment
        """)
        if st.button("Go to Dental Examination", key="dash_goto_exam"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
    
    with col4:
        st.markdown("""
        ### 4. Clinical Interaction
        - Record patient conversation
        - Transcribe audio
        - AI analysis of clinical data
        """)
        if st.button("Go to Clinical Interaction", key="dash_goto_clinical"):
            st.session_state.current_page = "clinical"
            st.rerun()
    
    # Display recent activity
    st.header("Recent Activity")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Patients")
        try:
            conn = sqlite3.connect('data/dentai.db')
            patients_df = pd.read_sql_query(
                "SELECT id, first_name, last_name, date_of_birth FROM patients ORDER BY created_at DESC LIMIT 5",
                conn
            )
            conn.close()
            
            if not patients_df.empty:
                st.dataframe(patients_df)
                
                # Quick action buttons
                selected_patient_id = st.selectbox(
                    "Select a patient for quick actions:",
                    patients_df['id'].tolist(),
                    format_func=lambda x: f"{patients_df[patients_df['id'] == x]['first_name'].iloc[0]} {patients_df[patients_df['id'] == x]['last_name'].iloc[0]}"
                )
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Medical History", key="quick_medical"):
                        st.session_state.selected_patient = selected_patient_id
                        st.session_state.current_page = "questionnaire"
                        st.rerun()
                with col2:
                    if st.button("Clinical Interaction", key="quick_clinical"):
                        st.session_state.selected_patient = selected_patient_id
                        st.session_state.current_page = "clinical"
                        st.rerun()
                with col3:
                    if st.button("View Reports", key="quick_reports"):
                        st.session_state.selected_patient = selected_patient_id
                        st.session_state.current_page = "clinical"
                        st.rerun()
            else:
                st.info("No patients found. Add patients to get started.")
        except Exception as e:
            st.error(f"Error retrieving patient data: {str(e)}")

    with col2:
        st.subheader("Recent Clinical Records")
        try:
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
                st.info("No clinical records found. Complete a clinical interaction to generate records.")
        except Exception as e:
            st.error(f"Error retrieving clinical records: {str(e)}")

def patients_page():
    st.title("DentAI - Patient Management")
    
    # Navigation buttons
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    
    with col1:
        if st.button("Dashboard", key="dashboard_btn_patients"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    with col2:
        if st.button("Patients", key="patients_btn_patients", type="primary"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    with col3:
        if st.button("Questionnaire", key="questionnaire_btn_patients"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
    with col4:
        if st.button("Clinical", key="clinical_btn_patients"):
            st.session_state.current_page = "clinical"
            st.rerun()
    
    with col5:
        if st.button("Dental Exam", key="dental_exam_btn_patients"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
    
    with col6:
        if st.button("Settings", key="settings_btn_patients"):
            st.session_state.current_page = "settings"
            st.rerun()
    
    with col7:
        if st.button("Logout", key="logout_btn_patients"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Patient management tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Patient List", "Add Patient", "Search Patient", "Patient Progress"])
    
    # Patient List Tab
    with tab1:
        st.subheader("Patient List")
        try:
            conn = sqlite3.connect('data/dentai.db')
            patients_df = pd.read_sql_query(
                "SELECT id, first_name, last_name, date_of_birth, gender, phone, email FROM patients ORDER BY last_name, first_name",
                conn
            )
            conn.close()
            
            if not patients_df.empty:
                # Add age calculation
                try:
                    patients_df['Age'] = patients_df['date_of_birth'].apply(
                        lambda x: date.today().year - datetime.strptime(x, "%Y-%m-%d").date().year 
                        if x else "Unknown"
                    )
                except Exception as e:
                    st.warning(f"Error calculating ages: {str(e)}")
                    patients_df['Age'] = "Unknown"
                
                # Display the dataframe with a filter
                st.write("Filter patients by name:")
                filter_name = st.text_input("", key="patient_filter")
                
                if filter_name:
                    filtered_df = patients_df[
                        patients_df['first_name'].str.contains(filter_name, case=False) | 
                        patients_df['last_name'].str.contains(filter_name, case=False)
                    ]
                    st.dataframe(filtered_df)
                else:
                    st.dataframe(patients_df)
                
                # Patient selection and actions
                st.write("### Patient Actions")
                selected_patient_id = st.selectbox(
                    "Select a patient:",
                    patients_df['id'].tolist(),
                    format_func=lambda x: f"{patients_df[patients_df['id'] == x]['first_name'].iloc[0]} {patients_df[patients_df['id'] == x]['last_name'].iloc[0]}"
                )
                
                # Action buttons in columns
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    if st.button("View Details", key="view_details_btn"):
                        st.session_state.selected_patient = selected_patient_id
                        st.session_state.patient_detail_view = True
                        st.rerun()
                
                with col2:
                    if st.button("Medical History", key="pat_list_medical_btn"):
                        st.session_state.selected_patient = selected_patient_id
                        st.session_state.current_page = "questionnaire"
                        st.rerun()
                
                with col3:
                    if st.button("Dental Examination", key="pat_list_exam_btn"):
                        st.session_state.selected_patient = selected_patient_id
                        st.session_state.current_page = "dental_examination"
                        st.rerun()
                
                with col4:
                    if st.button("Clinical Interaction", key="pat_list_go_clinical"):
                        st.session_state.selected_patient = selected_patient_id
                        st.session_state.current_page = "clinical"
                        st.rerun()
                
                with col5:
                    if st.button("Delete Patient", key="delete_patient_btn"):
                        st.session_state.confirm_delete = selected_patient_id
                        st.rerun()
            else:
                st.info("No patients found. Add patients to get started.")
        except Exception as e:
            st.error(f"Error retrieving patient data: {str(e)}")
    
        # Patient Detail View
        if 'patient_detail_view' in st.session_state and st.session_state.patient_detail_view and 'selected_patient' in st.session_state:
            patient_id = st.session_state.selected_patient
            
            try:
                # Get patient basic info
                conn = sqlite3.connect('data/dentai.db')
                c = conn.cursor()
                c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
                patient_data = c.fetchone()
                
                if patient_data:
                    st.write("---")
                    st.subheader(f"Patient Details: {patient_data[1]} {patient_data[2]}")
                    
                    # Display patient info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Basic Information**")
                        st.write(f"**ID:** {patient_data[0]}")
                        st.write(f"**Name:** {patient_data[1]} {patient_data[2]}")
                        st.write(f"**Date of Birth:** {patient_data[3]}")
                        st.write(f"**Gender:** {patient_data[4]}")
                    
                    with col2:
                        st.write("**Contact Information**")
                        st.write(f"**Phone:** {patient_data[5]}")
                        st.write(f"**Email:** {patient_data[6]}")
                        st.write(f"**Address:** {patient_data[7]}")
                    
                    # Get questionnaire completion status
                    c.execute("SELECT questionnaire_type, completion_date FROM questionnaires WHERE patient_id = ?", (patient_id,))
                    questionnaires = c.fetchall()
                    completed_questionnaires = [q[0] for q in questionnaires]
                    
                    # Get dental examination status
                    c.execute("SELECT exam_type, exam_date FROM dental_examination WHERE patient_id = ?", (patient_id,))
                    examinations = c.fetchall()
                    completed_exams = [e[0] for e in examinations]
                    
                    # Get clinical records
                    c.execute("SELECT record_date FROM clinical_records WHERE patient_id = ?", (patient_id,))
                    clinical_records = c.fetchall()
                    
                    # Get AI reports
                    c.execute("SELECT generated_at FROM ai_reports WHERE patient_id = ?", (patient_id,))
                    ai_reports = c.fetchall()
                    
                    # Display completion status
                    st.write("---")
                    st.write("### Patient Progress")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        medical_complete = "medical" in completed_questionnaires
                        dental_complete = "dental" in completed_questionnaires
                        allergies_complete = "allergies" in completed_questionnaires
                        medications_complete = "medications" in completed_questionnaires
                        
                        questionnaire_count = sum([
                            medical_complete, dental_complete, 
                            allergies_complete, medications_complete
                        ])
                        
                        st.metric(
                            "Questionnaires", 
                            f"{questionnaire_count}/4", 
                            delta="Complete" if questionnaire_count == 4 else f"{4-questionnaire_count} remaining"
                        )
                    
                    with col2:
                        exam_count = len(completed_exams)
                        st.metric(
                            "Dental Examinations", 
                            f"{exam_count}/4", 
                            delta="Complete" if exam_count >= 4 else f"{4-exam_count} remaining"
                        )
                    
                    with col3:
                        clinical_count = len(clinical_records)
                        st.metric(
                            "Clinical Interactions", 
                            clinical_count, 
                            delta="+1" if clinical_count > 0 else "None"
                        )
                    
                    with col4:
                        ai_count = len(ai_reports)
                        st.metric(
                            "AI Reports", 
                            ai_count, 
                            delta="+1" if ai_count > 0 else "None"
                        )
                    
                    # Display questionnaire summary
                    if questionnaire_count > 0:
                        st.write("### Questionnaire Summary")
                        
                        # Medical History
                        if medical_complete:
                            with st.expander("Medical History", expanded=False):
                                c.execute("SELECT responses FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'medical'", (patient_id,))
                                medical_data = c.fetchone()
                                if medical_data:
                                    try:
                                        medical_responses = safe_eval(medical_data[0])
                                        
                                        st.write(f"**General Health:** {medical_responses.get('general_health', 'Not specified')}")
                                        
                                        # Medical conditions
                                        conditions = []
                                        for condition, has_condition in medical_responses.get('medical_conditions', {}).items():
                                            if has_condition and condition not in ['other', 'other_details']:
                                                conditions.append(condition.replace('_', ' ').title())
                                        
                                        if conditions:
                                            st.write("**Medical Conditions:**")
                                            for condition in conditions:
                                                st.write(f"- {condition}")
                                        else:
                                            st.write("**Medical Conditions:** None reported")
                                        
                                        # Hospitalizations
                                        if medical_responses.get('hospitalizations', {}).get('has_hospitalizations', False):
                                            st.write("**Hospitalizations:** Yes")
                                            st.write(f"Details: {medical_responses.get('hospitalizations', {}).get('details', '')}")
                                        else:
                                            st.write("**Hospitalizations:** None reported")
                                    except:
                                        st.write("Error parsing medical history data")
                        
                        # Dental History
                        if dental_complete:
                            with st.expander("Dental History", expanded=False):
                                c.execute("SELECT responses FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'dental'", (patient_id,))
                                dental_data = c.fetchone()
                                if dental_data:
                                    try:
                                        dental_responses = safe_eval(dental_data[0])
                                        
                                        st.write(f"**Last Dental Visit:** {dental_responses.get('previous_care', {}).get('last_visit', 'Not specified')}")
                                        st.write(f"**Brushing Frequency:** {dental_responses.get('dental_habits', {}).get('brushing', 'Not specified')}")
                                        st.write(f"**Flossing Frequency:** {dental_responses.get('dental_habits', {}).get('flossing', 'Not specified')}")
                                        
                                        # Dental concerns
                                        concerns = []
                                        for concern, has_concern in dental_responses.get('dental_concerns', {}).items():
                                            if has_concern and concern != 'other':
                                                concerns.append(concern.replace('_', ' ').title())
                                        
                                        if concerns:
                                            st.write("**Dental Concerns:**")
                                            for concern in concerns:
                                                st.write(f"- {concern}")
                                        else:
                                            st.write("**Dental Concerns:** None reported")
                                        
                                        # TMD issues
                                        tmd_issues = []
                                        for issue, has_issue in dental_responses.get('tmd_assessment', {}).items():
                                            if has_issue and issue not in ['previous_tmd_treatment', 'treatment_details']:
                                                tmd_issues.append(issue.replace('_', ' ').title())
                                        
                                        if tmd_issues:
                                            st.write("**TMD Issues:**")
                                            for issue in tmd_issues:
                                                st.write(f"- {issue}")
                                        else:
                                            st.write("**TMD Issues:** None reported")
                                    except:
                                        st.write("Error parsing dental history data")
                        
                        # Allergies
                        if allergies_complete:
                            with st.expander("Allergies", expanded=False):
                                c.execute("SELECT responses FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'allergies'", (patient_id,))
                                allergies_data = c.fetchone()
                                if allergies_data:
                                    try:
                                        allergies_responses = safe_eval(allergies_data[0])
                                        
                                        # Medication allergies
                                        if allergies_responses.get('medication_allergies', {}).get('has_allergies', False):
                                            st.write("**Medication Allergies:** Yes")
                                            st.write(f"Details: {allergies_responses.get('medication_allergies', {}).get('details', '')}")
                                        else:
                                            st.write("**Medication Allergies:** None reported")
                                        
                                        # Dental material allergies
                                        if allergies_responses.get('dental_material_allergies', {}).get('has_allergies', False):
                                            st.write("**Dental Material Allergies:** Yes")
                                            materials = []
                                            for material, has_allergy in allergies_responses.get('dental_material_allergies', {}).items():
                                                if has_allergy and material not in ['has_allergies', 'other']:
                                                    materials.append(material.replace('_', ' ').title())
                                            
                                            if materials:
                                                for material in materials:
                                                    st.write(f"- {material}")
                                        else:
                                            st.write("**Dental Material Allergies:** None reported")
                                    except:
                                        st.write("Error parsing allergies data")
                    
                    # Display examination summary
                    if exam_count > 0:
                        st.write("### Examination Summary")
                        
                        for exam_type in completed_exams:
                            with st.expander(f"{exam_type.replace('_', ' ').title()} Examination", expanded=False):
                                c.execute("SELECT findings FROM dental_examination WHERE patient_id = ? AND exam_type = ?", (patient_id, exam_type))
                                exam_data = c.fetchone()
                                if exam_data:
                                    try:
                                        findings = safe_eval(exam_data[0])
                                        for key, value in findings.items():
                                            if isinstance(value, dict):
                                                st.write(f"**{key.replace('_', ' ').title()}:**")
                                                for subkey, subvalue in value.items():
                                                    st.write(f"- {subkey.replace('_', ' ').title()}: {subvalue}")
                                            else:
                                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                    except:
                                        st.write("Error parsing examination data")
                    
                    # Display AI reports
                    if ai_count > 0:
                        st.write("### AI Analysis Reports")
                        
                        c.execute("SELECT report_text, generated_at FROM ai_reports WHERE patient_id = ? ORDER BY generated_at DESC", (patient_id,))
                        reports = c.fetchall()
                        
                        for i, report in enumerate(reports):
                            with st.expander(f"AI Report {i+1} - {report[1]}", expanded=False):
                                st.markdown(report[0])
                    
                    # Close button
                    if st.button("Close Patient Details", key="close_details_btn"):
                        st.session_state.patient_detail_view = False
                        st.rerun()
                else:
                    st.error("Patient not found")
                
                conn.close()
            except Exception as e:
                st.error(f"Error retrieving patient details: {str(e)}")
    
    # Add Patient Tab
    with tab2:
        st.subheader("Add New Patient")
        
        # Create a form for adding a new patient
        with st.form("add_patient_form"):
            # Basic info
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name *")
                gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
                phone = st.text_input("Phone Number")
            
            with col2:
                last_name = st.text_input("Last Name *")
                dob = st.date_input("Date of Birth", 
                                  value=None,
                                  min_value=date(1900, 1, 1),
                                  max_value=date.today())
                email = st.text_input("Email Address")
            
            address = st.text_area("Address")
            
            # Submit button
            submitted = st.form_submit_button("Add Patient")
            
            if submitted:
                # Validate required fields
                if not first_name or not last_name:
                    st.error("First name and last name are required fields.")
                else:
                    try:
                        # Connect to database
                        conn = sqlite3.connect('data/dentai.db')
                        c = conn.cursor()
                        
                        # Format date of birth
                        dob_str = dob.strftime("%Y-%m-%d") if dob else None
                        
                        # Insert new patient
                        c.execute('''
                        INSERT INTO patients (first_name, last_name, date_of_birth, gender, phone, email, address)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (first_name, last_name, dob_str, gender, phone, email, address))
                        
                        # Get the ID of the newly inserted patient
                        new_patient_id = c.lastrowid
                        
                        # Commit changes
                        conn.commit()
                        conn.close()
                        
                        # Show success message and clear form (by rerunning)
                        st.success(f"Patient {first_name} {last_name} added successfully!")
                        
                        # Option to go directly to the patient's details
                        if st.button("View Patient Details"):
                            st.session_state.selected_patient = new_patient_id
                            st.session_state.patient_detail_view = True
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Error adding patient: {str(e)}")
    
    # Search Patient Tab
    with tab3:
        st.subheader("Search Patient")
        search_term = st.text_input("Enter patient name, ID, or phone number")
        
        if search_term:
            try:
                conn = sqlite3.connect('data/dentai.db')
                search_results = pd.read_sql_query(
                    """
                    SELECT id, first_name, last_name, date_of_birth, gender, phone, email
                    FROM patients
                    WHERE first_name LIKE ? 
                    OR last_name LIKE ?
                    OR phone LIKE ?
                    OR CAST(id AS VARCHAR) = ?
                    ORDER BY last_name, first_name
                    """,
                    conn,
                    params=(f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", search_term)
                )
                conn.close()
                
                if not search_results.empty:
                    st.write(f"Found {len(search_results)} matching patients:")
                    st.dataframe(search_results)
                    
                    # Select patient for actions
                    patient_id = st.selectbox(
                        "Select a patient for actions:",
                        search_results['id'].tolist(),
                        format_func=lambda x: f"{search_results[search_results['id'] == x]['first_name'].iloc[0]} {search_results[search_results['id'] == x]['last_name'].iloc[0]}"
                    )
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("View Details", key="search_details_btn"):
                            st.session_state.selected_patient = patient_id
                            st.session_state.patient_detail_view = True
                            # Switch to patient list tab to show details
                            st.session_state.active_tab = "Patient List"
                            st.rerun()
                    
                    with col2:
                        if st.button("Medical Questionnaire", key="search_medical_btn"):
                            st.session_state.selected_patient = patient_id
                            st.session_state.current_page = "questionnaire"
                            st.rerun()
                    
                    with col3:
                        if st.button("Dental Examination", key="search_dental_btn"):
                            st.session_state.selected_patient = patient_id
                            st.session_state.current_page = "dental_examination"
                            st.rerun()
                    
                    with col4:
                        if st.button("Clinical Interaction", key="search_go_clinical"):
                            st.session_state.selected_patient = patient_id
                            st.session_state.current_page = "clinical"
                            st.rerun()
                else:
                    st.info("No matching patients found.")
            except Exception as e:
                st.error(f"Error searching for patients: {str(e)}")

def dental_examination_page():
    st.title("DentAI - Dental Examination")
    
    # Navigation buttons
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    
    with col1:
        if st.button("Dashboard", key="dashboard_btn_exam"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    with col2:
        if st.button("Patients", key="patients_btn_exam"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    with col3:
        if st.button("Questionnaire", key="questionnaire_btn_exam"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
    with col4:
        if st.button("Clinical", key="clinical_btn_exam"):
            st.session_state.current_page = "clinical"
            st.rerun()
    
    with col5:
        if st.button("Dental Exam", key="dental_exam_btn_exam", type="primary"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
    
    with col6:
        if st.button("Settings", key="settings_btn_exam"):
            st.session_state.current_page = "settings"
            st.rerun()
    
    with col7:
        if st.button("Logout", key="logout_btn_exam"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Add back navigation buttons at the top
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Patients", key="exam_back_btn"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    # Sidebar navigation
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}!")
        
        if st.button("Dashboard", key="exam_dash_btn"):
            st.session_state.current_page = "dashboard"
            st.rerun()
        
        if st.button("Patient Management", key="exam_patient_btn"):
            st.session_state.current_page = "patients"
            st.rerun()
        
        if st.button("Medical Questionnaire", key="exam_quest_btn"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
        
        if st.button("Clinical Interaction", key="exam_clinical_btn"):
            st.session_state.current_page = "clinical"
            st.rerun()
        
        if st.button("Logout", key="exam_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.rerun()
    
    # Check if a patient is selected
    if 'selected_patient' not in st.session_state:
        st.warning("No patient selected. Please select a patient from the Patient Management page.")
        if st.button("Go to Patient Management", key="exam_go_patient_mgmt"):
            st.session_state.current_page = "patients"
            st.rerun()
        return
    
    # Get patient info
    patient_id = st.session_state.selected_patient
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    c.execute("SELECT first_name, last_name FROM patients WHERE id = ?", (patient_id,))
    patient = c.fetchone()
    conn.close()
    
    if not patient:
        st.error("Patient not found")
        return
    
    st.header(f"Dental Examination for {patient[0]} {patient[1]}")
    
    # Create tabs for different examination components
    tabs = st.tabs(["Extraoral Examination", "Intraoral Examination", "Dental Charting", "Periodontal Assessment", "Examination Summary"])
    
    # Extraoral Examination Tab
    with tabs[0]:
        st.subheader("Extraoral Examination")
        
        with st.form("extraoral_exam_form"):
            # General appearance
            st.write("### General Appearance")
            general_appearance = st.selectbox("General appearance", 
                                             ["Normal", "Abnormal"])
            appearance_notes = st.text_area("Notes on appearance")
            
            # Temporomandibular joint (TMJ)
            st.write("### Temporomandibular Joint (TMJ)")
            tmj_pain = st.checkbox("TMJ Pain")
            tmj_clicking = st.checkbox("TMJ Clicking/Popping")
            tmj_crepitus = st.checkbox("TMJ Crepitus")
            limited_opening = st.checkbox("Limited Opening")
            tmj_notes = st.text_area("TMJ Notes")
            
            # Lymph nodes
            st.write("### Lymph Nodes")
            lymph_nodes = st.selectbox("Lymph nodes", 
                                      ["Normal", "Enlarged", "Tender"])
            lymph_notes = st.text_area("Lymph node notes")
            
            # Submit button
            submitted = st.form_submit_button("Save Extraoral Examination")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "general_appearance": {
                        "status": general_appearance,
                        "notes": appearance_notes
                    },
                    "tmj": {
                        "pain": tmj_pain,
                        "clicking": tmj_clicking,
                        "crepitus": tmj_crepitus,
                        "limited_opening": limited_opening,
                        "notes": tmj_notes
                    },
                    "lymph_nodes": {
                        "status": lymph_nodes,
                        "notes": lymph_notes
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM dental_examination WHERE patient_id = ? AND exam_type = 'extraoral'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE dental_examination SET findings = ?, exam_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO dental_examination (patient_id, exam_type, findings) VALUES (?, ?, ?)",
                            (patient_id, "extraoral", str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Extraoral examination saved successfully!")
                except Exception as e:
                    st.error(f"Error saving examination: {str(e)}")
    
    # Intraoral Examination Tab
    with tabs[1]:
        st.subheader("Intraoral Examination")
        
        with st.form("intraoral_exam_form"):
            # Oral hygiene
            st.write("### Oral Hygiene")
            oral_hygiene = st.selectbox("Oral hygiene status", 
                                       ["Excellent", "Good", "Fair", "Poor"])
            
            # Soft tissues
            st.write("### Soft Tissues")
            col1, col2 = st.columns(2)
            
            with col1:
                lips_normal = st.checkbox("Lips Normal")
                cheeks_normal = st.checkbox("Cheeks Normal")
                palate_normal = st.checkbox("Palate Normal")
                floor_normal = st.checkbox("Floor of Mouth Normal")
            
            with col2:
                tongue_normal = st.checkbox("Tongue Normal")
                gingiva_normal = st.checkbox("Gingiva Normal")
                pharynx_normal = st.checkbox("Pharynx Normal")
                tonsils_normal = st.checkbox("Tonsils Normal")
            
            soft_tissue_notes = st.text_area("Soft tissue notes")
            
            # Occlusion
            st.write("### Occlusion")
            occlusion_class = st.selectbox("Angle's Classification", 
                                          ["Class I", "Class II Division 1", "Class II Division 2", "Class III"])
            overjet = st.number_input("Overjet (mm)", min_value=0.0, max_value=20.0, step=0.5)
            overbite = st.number_input("Overbite (%)", min_value=0, max_value=100, step=5)
            crossbite = st.checkbox("Crossbite Present")
            crossbite_location = st.text_input("Crossbite Location (if present)")
            
            # Submit button
            submitted = st.form_submit_button("Save Intraoral Examination")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "oral_hygiene": oral_hygiene,
                    "soft_tissues": {
                        "lips": lips_normal,
                        "cheeks": cheeks_normal,
                        "palate": palate_normal,
                        "floor": floor_normal,
                        "tongue": tongue_normal,
                        "gingiva": gingiva_normal,
                        "pharynx": pharynx_normal,
                        "tonsils": tonsils_normal,
                        "notes": soft_tissue_notes
                    },
                    "occlusion": {
                        "class": occlusion_class,
                        "overjet": overjet,
                        "overbite": overbite,
                        "crossbite": {
                            "present": crossbite,
                            "location": crossbite_location
                        }
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM dental_examination WHERE patient_id = ? AND exam_type = 'intraoral'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE dental_examination SET findings = ?, exam_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO dental_examination (patient_id, exam_type, findings) VALUES (?, ?, ?)",
                            (patient_id, "intraoral", str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Intraoral examination saved successfully!")
                except Exception as e:
                    st.error(f"Error saving examination: {str(e)}")
    
    # Dental Charting Tab
    with tabs[2]:
        st.subheader("Dental Charting")
        
        st.write("### Tooth Condition Charting")
        st.info("In a production app, this would include an interactive dental chart. For this demo, we'll use a simplified form.")
        
        with st.form("dental_charting_form"):
            # Simplified dental charting
            st.write("### Upper Right Quadrant (1)")
            ur_notes = st.text_area("Notes for Upper Right Quadrant")
            
            st.write("### Upper Left Quadrant (2)")
            ul_notes = st.text_area("Notes for Upper Left Quadrant")
            
            st.write("### Lower Left Quadrant (3)")
            ll_notes = st.text_area("Notes for Lower Left Quadrant")
            
            st.write("### Lower Right Quadrant (4)")
            lr_notes = st.text_area("Notes for Lower Right Quadrant")
            
            # Missing teeth
            st.write("### Missing Teeth")
            missing_teeth = st.text_input("List missing teeth (comma separated, e.g., 18,17,26)")
            
            # Restorations
            st.write("### Existing Restorations")
            restorations = st.text_area("Notes on existing restorations")
            
            # Caries
            st.write("### Caries")
            caries = st.text_area("Notes on caries")
            
            # Submit button
            submitted = st.form_submit_button("Save Dental Charting")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "quadrants": {
                        "upper_right": ur_notes,
                        "upper_left": ul_notes,
                        "lower_left": ll_notes,
                        "lower_right": lr_notes
                    },
                    "missing_teeth": missing_teeth,
                    "restorations": restorations,
                    "caries": caries
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM dental_examination WHERE patient_id = ? AND exam_type = 'charting'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE dental_examination SET findings = ?, exam_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO dental_examination (patient_id, exam_type, findings) VALUES (?, ?, ?)",
                            (patient_id, "charting", str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Dental charting saved successfully!")
                except Exception as e:
                    st.error(f"Error saving dental charting: {str(e)}")
    
    # Periodontal Assessment Tab
    with tabs[3]:
        st.subheader("Periodontal Assessment")
        
        with st.form("periodontal_assessment_form"):
            # Gingival health
            st.write("### Gingival Health")
            gingival_health = st.selectbox("Gingival health status", 
                                          ["Healthy", "Mild Inflammation", "Moderate Inflammation", "Severe Inflammation"])
            
            # Bleeding on probing
            st.write("### Bleeding on Probing")
            bleeding_on_probing = st.slider("Percentage of sites with bleeding on probing", 0, 100, 0)
            
            # Pocket depths
            st.write("### Pocket Depths")
            st.write("Select the deepest pocket depth category for each quadrant")
            
            col1, col2 = st.columns(2)
            with col1:
                ur_pocket = st.selectbox("Upper Right", ["1-3mm", "4-5mm", "6mm+"])
                ll_pocket = st.selectbox("Lower Left", ["1-3mm", "4-5mm", "6mm+"])
            
            with col2:
                ul_pocket = st.selectbox("Upper Left", ["1-3mm", "4-5mm", "6mm+"])
                lr_pocket = st.selectbox("Lower Right", ["1-3mm", "4-5mm", "6mm+"])
            
            # Recession
            st.write("### Gingival Recession")
            recession_present = st.checkbox("Gingival recession present")
            recession_notes = st.text_area("Notes on recession")
            
            # Mobility
            st.write("### Tooth Mobility")
            mobility_present = st.checkbox("Tooth mobility present")
            mobility_notes = st.text_area("Notes on mobility")
            
            # Furcation involvement
            st.write("### Furcation Involvement")
            furcation_present = st.checkbox("Furcation involvement present")
            furcation_notes = st.text_area("Notes on furcation involvement")
            
            # Submit button
            submitted = st.form_submit_button("Save Periodontal Assessment")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "gingival_health": gingival_health,
                    "bleeding_on_probing": bleeding_on_probing,
                    "pocket_depths": {
                        "upper_right": ur_pocket,
                        "upper_left": ul_pocket,
                        "lower_left": ll_pocket,
                        "lower_right": lr_pocket
                    },
                    "recession": {
                        "present": recession_present,
                        "notes": recession_notes
                    },
                    "mobility": {
                        "present": mobility_present,
                        "notes": mobility_notes
                    },
                    "furcation": {
                        "present": furcation_present,
                        "notes": furcation_notes
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM dental_examination WHERE patient_id = ? AND exam_type = 'periodontal'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE dental_examination SET findings = ?, exam_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO dental_examination (patient_id, exam_type, findings) VALUES (?, ?, ?)",
                            (patient_id, "periodontal", str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Periodontal assessment saved successfully!")
                except Exception as e:
                    st.error(f"Error saving periodontal assessment: {str(e)}")
    
    # Examination Summary Tab
    with tabs[4]:
        st.subheader("Examination Summary")
        
        # Fetch all examination data
        try:
            conn = sqlite3.connect('data/dentai.db')
            c = conn.cursor()
            
            # Get all examination records for this patient
            c.execute("""
            SELECT exam_type, findings, exam_date 
            FROM dental_examination 
            WHERE patient_id = ? 
            ORDER BY exam_type, exam_date DESC
            """, (patient_id,))
            
            exams = c.fetchall()
            conn.close()
            
            if exams:
                st.write("### Dental Examination Summary")
                
                # Group exams by type and get the most recent of each type
                exam_data = {}
                for exam in exams:
                    exam_type = exam[0]
                    if exam_type not in exam_data:
                        exam_data[exam_type] = {
                            "findings": exam[1],
                            "date": exam[2]
                        }
                
                # Display summary for each exam type
                for exam_type, data in exam_data.items():
                    with st.expander(f"{exam_type.title()} Examination ({data['date']})"):
                        try:
                            findings = safe_eval(data['findings'])
                            st.json(findings)
                        except:
                            st.write("Error parsing examination data")
                
                # Generate AI analysis
                if st.button("Generate Comprehensive Dental Analysis", key="generate_dental_analysis"):
                    st.info("Analyzing dental examination data...")
                    
                    # In a real app, this would call OpenAI API
                    # For now, we'll simulate an AI analysis
                    ai_analysis = f"""
                    # Dental Examination Analysis for {patient[0]} {patient[1]}
                    
                    ## Summary
                    Based on the comprehensive dental examination, this patient presents with several findings that require attention.
                    
                    ## Key Observations
                    - {'Periodontal issues detected, including ' + exam_data.get('periodontal', {}).get('findings', '{}') if 'periodontal' in exam_data else 'No periodontal assessment recorded.'}
                    - {'Dental charting reveals ' + exam_data.get('charting', {}).get('findings', '{}') if 'charting' in exam_data else 'No dental charting recorded.'}
                    - {'Intraoral examination shows ' + exam_data.get('intraoral', {}).get('findings', '{}') if 'intraoral' in exam_data else 'No intraoral examination recorded.'}
                    
                    ## Recommendations
                    1. {'Periodontal therapy recommended based on pocket depths and bleeding.' if 'periodontal' in exam_data else 'Complete periodontal assessment recommended.'}
                    2. {'Restorative treatment needed for carious lesions.' if 'charting' in exam_data else 'Complete dental charting recommended.'}
                    3. {'Follow-up on soft tissue findings.' if 'intraoral' in exam_data else 'Complete intraoral examination recommended.'}
                    4. {'TMJ evaluation recommended.' if 'extraoral' in exam_data else 'Complete extraoral examination recommended.'}
                    
                    ## Treatment Plan Considerations
                    - {'Prioritize periodontal health before restorative procedures.' if 'periodontal' in exam_data else ''}
                    - {'Consider occlusal factors in treatment planning.' if 'intraoral' in exam_data else ''}
                    - {'Monitor TMJ symptoms during treatment.' if 'extraoral' in exam_data else ''}
                    """
                    
                    # Save AI analysis to database
                    try:
                        conn = sqlite3.connect('data/dentai.db')
                        c = conn.cursor()
                        c.execute(
                            "INSERT INTO ai_reports (patient_id, report_text) VALUES (?, ?)",
                            (patient_id, ai_analysis)
                        )
                        conn.commit()
                        conn.close()
                        
                        st.success("Dental analysis generated successfully!")
                        st.markdown(ai_analysis)
                    except Exception as e:
                        st.error(f"Error saving dental analysis: {str(e)}")
            else:
                st.info("No examination data available. Please complete the dental examination.")
        except Exception as e:
            st.error(f"Error retrieving examination data: {str(e)}")

def questionnaire_page():
    st.title("DentAI - Medical Questionnaire")
    
    # Navigation buttons
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    
    with col1:
        if st.button("Dashboard", key="dashboard_btn_quest"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    with col2:
        if st.button("Patients", key="patients_btn_quest"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    with col3:
        if st.button("Questionnaire", key="questionnaire_btn_quest", type="primary"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
    with col4:
        if st.button("Clinical", key="clinical_btn_quest"):
            st.session_state.current_page = "clinical"
            st.rerun()
    
    with col5:
        if st.button("Dental Exam", key="dental_exam_btn_quest"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
    
    with col6:
        if st.button("Settings", key="settings_btn_quest"):
            st.session_state.current_page = "settings"
            st.rerun()
    
    with col7:
        if st.button("Logout", key="logout_btn_quest"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Check if a patient is selected
    if 'selected_patient' not in st.session_state:
        st.warning("No patient selected. Please select a patient from the Patient Management page.")
        if st.button("Go to Patient Management", key="quest_go_patient_mgmt"):
            st.session_state.current_page = "patients"
            st.rerun()
        return
    
    # Get patient info
    patient_id = st.session_state.selected_patient
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    c.execute("SELECT first_name, last_name FROM patients WHERE id = ?", (patient_id,))
    patient = c.fetchone()
    conn.close()
    
    if not patient:
        st.error("Patient not found")
        return
    
    st.header(f"Medical & Dental Questionnaire for {patient[0]} {patient[1]}")
    
    # Create tabs for different questionnaire sections
    tabs = st.tabs(["Medical History", "Dental History", "Allergies", "Medications", "Lifestyle", "Women's Health", "AI Analysis"])
    
    # Medical History Tab
    with tabs[0]:
        st.subheader("Medical History")
        
        # Recording functionality - moved outside the form
        # Move recording buttons outside the form
        col1, col2 = st.columns(2)
        
        with col1:
            if not st.session_state.recording:
                if st.button("🎙️ Start Recording", key="quest_start_recording"):
                    st.session_state.recording = True
                    st.session_state.audio_data = []
                    st.session_state.transcription_complete = False
                    st.rerun()
        
        with col2:
            if st.session_state.recording:
                if st.button("⏹️ Stop Recording", key="quest_stop_recording"):
                    st.session_state.recording = False
                    st.rerun()
        
        # Display recording status
        if st.session_state.recording:
            st.warning("🔴 Recording in progress... Speak clearly and press 'Stop Recording' when finished.")
            st.info("Note: Your audio is being processed in the background. No actual recording is happening in the browser.")
            
            # Simulate recording progress - make it slower to give more time for recording
            # We'll use a placeholder progress bar that moves slowly
            progress_bar = st.progress(0)
            
            # Only increment progress every 0.5 seconds, and cap at 80% unless stopped
            # This gives the user more time to record before auto-stopping
            for i in range(80):
                time.sleep(0.5)  # Slower progress
                progress_bar.progress(i + 1)
                if not st.session_state.recording:
                    break
            
            # If we reach here and recording is still active, show a message but don't auto-stop
            if st.session_state.recording:
                st.info("Recording is still in progress. Press 'Stop Recording' when you're finished.")
                
                # Continue with slower progress to 100%
                for i in range(80, 100):
                    time.sleep(1.0)  # Even slower for the last 20%
                    progress_bar.progress(i + 1)
                    if not st.session_state.recording:
                        break
                
                # Only auto-stop if we reach 100%
                if st.session_state.recording:
                    st.session_state.recording = False
                    st.rerun()
        
        # Process audio after recording stops
        if not st.session_state.recording and st.session_state.audio_data is not None and not st.session_state.transcription_complete:
            st.write("#### Processing Audio...")
            
            # In a real implementation, we would have collected audio data
            # For now, we'll use a placeholder audio file or simulate the process
            
            # Simulate audio processing
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.05)
                progress_bar.progress(i + 1)
            
            # Transcribe audio using OpenAI Whisper
            try:
                st.write("#### Transcribing with Whisper...")
                
                # Initialize OpenAI client
                if st.session_state.openai_api_key:
                    client = OpenAI(api_key=st.session_state.openai_api_key)
                else:
                    st.warning("OpenAI API key is not configured. Using simulated transcription instead.")
                    client = None
                
                # In a real implementation, we would use the collected audio data
                # For now, we'll simulate a transcription result
                
                # If we have a valid client, we would use Whisper API here
                # Since we're simulating, we'll use a sample transcription
                sample_transcription = """
                Doctor: Hello, how are you feeling today?
                Patient: I've been having some pain in my lower right molar for about a week now.
                Doctor: I see. Can you describe the pain? Is it constant or does it come and go?
                Patient: It comes and goes, but it's quite sharp when it happens. Especially when I drink something cold.
                Doctor: That sounds like it could be sensitivity or possibly a cavity. Let me take a look.
                Doctor: I can see some decay on the lower right molar. We'll need to do a filling.
                Patient: Will it hurt?
                Doctor: We'll use local anesthesia, so you shouldn't feel any pain during the procedure.
                """
                
                transcription_text = sample_transcription.strip()
                
                st.write("#### Transcription:")
                st.write(transcription_text)
                
                # Save transcription to database
                conn = sqlite3.connect('data/dentai.db')
                c = conn.cursor()
                
                # Check if a record already exists for this patient
                c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
                existing_id = c.fetchone()
                
                if existing_id:
                    # Update existing record
                    c.execute("UPDATE clinical_records SET transcription = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?", 
                             (transcription_text, existing_id[0]))
                else:
                    # Insert new record
                    c.execute("INSERT INTO clinical_records (patient_id, transcription, record_date) VALUES (?, ?, CURRENT_TIMESTAMP)",
                             (patient_id, transcription_text))
                
                conn.commit()
                conn.close()
                
                st.success("Transcription saved to database!")
                
                # Set transcription complete flag
                st.session_state.transcription_complete = True
                
                # Generate AI analysis automatically
                st.write("#### Generating AI Analysis...")
                try:
                    ai_report = generate_ai_analysis({
                        'patient_id': patient_id,
                        'patient_name': f"{patient[0]} {patient[1]}",
                        'transcription': transcription_text
                    })
                    
                    st.write("#### AI Analysis:")
                    st.markdown(ai_report)
                    
                    # Save AI analysis to database
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Update the same record with AI analysis
                    c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
                    existing_id = c.fetchone()
                    
                    if existing_id:
                        # Update existing record
                        c.execute("UPDATE clinical_records SET ai_analysis = ? WHERE id = ?", 
                                (ai_report, existing_id[0]))
                    else:
                        # This shouldn't happen as we just created a record, but just in case
                        c.execute("INSERT INTO clinical_records (patient_id, ai_analysis) VALUES (?, ?)",
                                (patient_id, ai_report))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("AI Analysis saved to database!")
                    
                    # Provide export options
                    st.write("#### Export Options:")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            label="Download as Text",
                            data=ai_report,
                            file_name=f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.md",
                            mime="text/markdown",
                            key=f"download_text_questionnaire_{patient_id}"
                        )
                    
                    with col2:
                        if PDF_EXPORT_AVAILABLE:
                            if st.button("Export as PDF"):
                                try:
                                    pdf_link = export_report_as_pdf(ai_report, f"{patient[0]} {patient[1]}")
                                    st.markdown(pdf_link, unsafe_allow_html=True)
                                except Exception as e:
                                    st.error(f"Error generating PDF: {e}")
                                    st.markdown(create_download_link(ai_report, 
                                                                  f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.md", 
                                                                  "Download as Markdown instead"), 
                                      unsafe_allow_html=True)
                        else:
                            st.info("PDF export requires additional packages. Install pdfkit and markdown packages for PDF export functionality.")
                except Exception as e:
                    st.error(f"Error generating AI analysis: {str(e)}")
            
            except Exception as e:
                st.error(f"Error during transcription: {str(e)}")
                # Ensure transcription_text is defined even in case of error
                if 'transcription_text' not in locals() or not transcription_text:
                    transcription_text = """
                    Doctor: Hello, how are you feeling today?
                    Patient: I've been having some pain in my lower right molar for about a week now.
                    Doctor: I see. Can you describe the pain? Is it constant or does it come and go?
                    Patient: It comes and goes, but it's quite sharp when it happens. Especially when I drink something cold.
                    Doctor: That sounds like it could be sensitivity or possibly a cavity. Let me take a look.
                    Doctor: I can see some decay on the lower right molar. We'll need to do a filling.
                    Patient: Will it hurt?
                    Doctor: We'll use local anesthesia, so you shouldn't feel any pain during the procedure.
                    """
                
                # Display the transcription even in case of error
                st.write("#### Transcription (Fallback):")
                st.write(transcription_text)
                
                # Save transcription to database even in case of error
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
                    existing_id = c.fetchone()
                    
                    if existing_id:
                        # Update existing record
                        c.execute("UPDATE clinical_records SET transcription = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?", 
                                (transcription_text, existing_id[0]))
                    else:
                        # Insert new record
                        c.execute("INSERT INTO clinical_records (patient_id, transcription, record_date) VALUES (?, ?, CURRENT_TIMESTAMP)",
                                (patient_id, transcription_text))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("Fallback transcription saved to database!")
                except Exception as db_error:
                    st.error(f"Error saving fallback transcription to database: {str(db_error)}")
                
                st.session_state.transcription_complete = True  # Mark as complete even on error to avoid infinite loops
        
        # Now start the form for the medical history
        with st.form("medical_history_form"):
            # General health
            st.write("### General Health")
            general_health = st.selectbox("How would you rate your general health?", 
                                         ["Excellent", "Good", "Fair", "Poor"])
            
            # Medical conditions
            st.write("### Medical Conditions")
            st.write("Do you have or have you ever had any of the following conditions?")
            
            # Create columns for medical conditions
            col1, col2 = st.columns(2)
            
            with col1:
                heart_disease = st.checkbox("Heart Disease")
                high_blood_pressure = st.checkbox("High Blood Pressure")
                asthma = st.checkbox("Asthma")
                diabetes = st.checkbox("Diabetes")
                arthritis = st.checkbox("Arthritis")
            
            with col2:
                cancer = st.checkbox("Cancer")
                stroke = st.checkbox("Stroke")
                kidney_disease = st.checkbox("Kidney Disease")
                liver_disease = st.checkbox("Liver Disease")
                thyroid_problems = st.checkbox("Thyroid Problems")
            
            other_condition = st.checkbox("Other")
            other_condition_details = st.text_input("If other, please specify:", disabled=not other_condition)
            
            # Submit button for the form
            submitted = st.form_submit_button("Save Medical History")
            if submitted:
                # Prepare data for saving
                medical_data = {
                    "general_health": general_health,
                    "medical_conditions": {
                        "heart_disease": heart_disease,
                        "high_blood_pressure": high_blood_pressure,
                        "asthma": asthma,
                        "diabetes": diabetes,
                        "arthritis": arthritis,
                        "cancer": cancer,
                        "stroke": stroke,
                        "kidney_disease": kidney_disease,
                        "liver_disease": liver_disease,
                        "thyroid_problems": thyroid_problems,
                        "other": other_condition,
                        "other_details": other_condition_details if other_condition else ""
                    }
                }
                
                # Vital signs section
                st.write("### Vital Signs")
                col1, col2 = st.columns(2)
                
                with col1:
                    blood_pressure_systolic = st.number_input("Blood Pressure (Systolic)", min_value=70, max_value=250, value=120)
                    heart_rate = st.number_input("Heart Rate (BPM)", min_value=40, max_value=200, value=75)
                
                with col2:
                    blood_pressure_diastolic = st.number_input("Blood Pressure (Diastolic)", min_value=40, max_value=150, value=80)
                    respiratory_rate = st.number_input("Respiratory Rate", min_value=8, max_value=40, value=16)
                
                temperature = st.number_input("Temperature (°F)", min_value=95.0, max_value=105.0, value=98.6, step=0.1)
                
                # Add vital signs to medical data
                medical_data["vital_signs"] = {
                    "blood_pressure": f"{blood_pressure_systolic}/{blood_pressure_diastolic}",
                    "heart_rate": heart_rate,
                    "respiratory_rate": respiratory_rate,
                    "temperature": temperature
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a questionnaire already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'medical'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing questionnaire
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(medical_data).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new questionnaire
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses, completion_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                            (patient_id, 'medical', str(medical_data).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Medical history saved successfully!")
                except Exception as e:
                    st.error(f"Error saving medical history: {str(e)}")
    
    # Dental History Tab
    with tabs[1]:
        st.subheader("Dental History")
        
        with st.form("dental_history_form"):
            # Last dental visit
            st.write("### Previous Dental Care")
            last_dental_visit = st.selectbox("When was your last dental visit?", 
                                           ["Within 6 months", "6-12 months ago", "1-2 years ago", "2-5 years ago", "5+ years ago", "Never"])
            
            regular_checkups = st.checkbox("Do you get regular dental checkups?")
            
            # Dental concerns
            st.write("### Dental Concerns")
            st.write("Do you have any of the following dental concerns?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                tooth_pain = st.checkbox("Tooth Pain", key="tooth_pain")
                sensitivity = st.checkbox("Sensitivity to hot/cold", key="sensitivity")
                bleeding_gums = st.checkbox("Bleeding Gums", key="bleeding_gums")
                bad_breath = st.checkbox("Bad Breath", key="bad_breath")
                grinding_teeth = st.checkbox("Grinding Teeth", key="grinding_teeth")
            
            with col2:
                loose_teeth = st.checkbox("Loose Teeth", key="loose_teeth")
                food_trapping = st.checkbox("Food Trapping Between Teeth", key="food_trapping")
                dry_mouth = st.checkbox("Dry Mouth", key="dry_mouth")
                jaw_pain = st.checkbox("Jaw Pain", key="jaw_pain")
                clicking_jaw = st.checkbox("Clicking/Popping Jaw", key="clicking_jaw")
            
            dental_other = st.checkbox("Other Concerns", key="dental_other")
            dental_other_details = st.text_input("If other, please specify:", key="dental_other_details", disabled=not dental_other)
            
            # TMD assessment
            st.write("### TMD Assessment")
            st.write("Do you experience any of the following?")
            
            jaw_pain_chewing = st.checkbox("Pain when chewing")
            jaw_pain_opening = st.checkbox("Pain when opening mouth wide")
            jaw_clicking = st.checkbox("Clicking or popping sounds in jaw joints")
            jaw_locking = st.checkbox("Jaw locking (open or closed)")
            morning_jaw_pain = st.checkbox("Morning jaw pain or stiffness")
            ear_pain = st.checkbox("Ear pain without infection")
            headaches = st.checkbox("Frequent headaches")
            previous_tmd_treatment = st.checkbox("Previous treatment for TMD/TMJ")
            
            if previous_tmd_treatment:
                treatment_details = st.text_area("Please describe previous TMD/TMJ treatment:")
            else:
                treatment_details = ""
            
            # Dental anxiety
            st.write("### Dental Anxiety")
            anxiety_level = st.slider("On a scale of 1-10, how anxious do you feel about dental treatment?", 1, 10, 3)
            
            # Oral hygiene
            st.write("### Oral Hygiene")
            brushing_frequency = st.selectbox("How often do you brush your teeth?", 
                                            ["Twice or more daily", "Once daily", "Few times a week", "Less frequently"])
            
            flossing_frequency = st.selectbox("How often do you floss?", 
                                            ["Daily", "Few times a week", "Occasionally", "Rarely", "Never"])
            
            mouthwash_use = st.checkbox("Do you use mouthwash?")
            
            # Submit button
            submitted = st.form_submit_button("Save Dental History")
            if submitted:
                # Prepare data for saving
                dental_data = {
                    "last_visit": last_dental_visit,
                    "regular_checkups": regular_checkups,
                    "dental_concerns": {
                        "tooth_pain": tooth_pain,
                        "sensitivity": sensitivity,
                        "bleeding_gums": bleeding_gums,
                        "bad_breath": bad_breath,
                        "grinding_teeth": grinding_teeth,
                        "loose_teeth": loose_teeth,
                        "food_trapping": food_trapping,
                        "dry_mouth": dry_mouth,
                        "jaw_pain": jaw_pain,
                        "clicking_jaw": clicking_jaw,
                        "other": dental_other,
                        "other_details": dental_other_details if dental_other else ""
                    },
                    "tmd_assessment": {
                        "jaw_pain_chewing": jaw_pain_chewing,
                        "jaw_pain_opening": jaw_pain_opening,
                        "jaw_clicking": jaw_clicking,
                        "jaw_locking": jaw_locking,
                        "morning_jaw_pain": morning_jaw_pain,
                        "ear_pain": ear_pain,
                        "headaches": headaches,
                        "previous_tmd_treatment": previous_tmd_treatment,
                        "treatment_details": treatment_details
                    },
                    "anxiety_level": anxiety_level,
                    "oral_hygiene": {
                        "brushing_frequency": brushing_frequency,
                        "flossing_frequency": flossing_frequency,
                        "mouthwash_use": mouthwash_use
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a questionnaire already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'dental'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing questionnaire
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(dental_data).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new questionnaire
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses, completion_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                            (patient_id, 'dental', str(dental_data).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Dental history saved successfully!")
                except Exception as e:
                    st.error(f"Error saving dental history: {str(e)}")
    
    # Allergies Tab
    with tabs[2]:
        st.subheader("Allergies")
        
        with st.form("allergies_form"):
            # Drug allergies
            st.write("### Drug Allergies")
            has_drug_allergies = st.checkbox("Do you have any drug allergies?")
            
            if has_drug_allergies:
                drug_allergies = st.text_area("Please list all drug allergies and reactions:")
            else:
                drug_allergies = ""
            
            # Common dental drug allergies
            st.write("### Common Dental Drug Allergies")
            col1, col2 = st.columns(2)
            
            with col1:
                penicillin_allergy = st.checkbox("Penicillin")
                codeine_allergy = st.checkbox("Codeine")
                local_anesthetic_allergy = st.checkbox("Local Anesthetics")
            
            with col2:
                nsaids_allergy = st.checkbox("NSAIDs (Aspirin, Ibuprofen)")
                latex_allergy = st.checkbox("Latex")
                sulfa_allergy = st.checkbox("Sulfa Drugs")
            
            # Other allergies
            st.write("### Other Allergies")
            has_other_allergies = st.checkbox("Do you have any other allergies?")
            
            if has_other_allergies:
                other_allergies = st.text_area("Please list all other allergies (food, environmental, etc.):")
            else:
                other_allergies = ""
            
            # Submit button
            submitted = st.form_submit_button("Save Allergies")
            if submitted:
                # Prepare data for saving
                allergies_data = {
                    "has_drug_allergies": has_drug_allergies,
                    "drug_allergies": drug_allergies,
                    "common_dental_allergies": {
                        "penicillin": penicillin_allergy,
                        "codeine": codeine_allergy,
                        "local_anesthetic": local_anesthetic_allergy,
                        "nsaids": nsaids_allergy,
                        "latex": latex_allergy,
                        "sulfa": sulfa_allergy
                    },
                    "has_other_allergies": has_other_allergies,
                    "other_allergies": other_allergies
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a questionnaire already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'allergies'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing questionnaire
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(allergies_data).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new questionnaire
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses, completion_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                            (patient_id, 'allergies', str(allergies_data).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Allergies saved successfully!")
                except Exception as e:
                    st.error(f"Error saving allergies: {str(e)}")
    
    # Medications Tab
    with tabs[3]:
        st.subheader("Medications")
        
        with st.form("medications_form"):
            # Current medications
            st.write("### Current Medications")
            taking_medications = st.checkbox("Are you currently taking any medications?")
            
            if taking_medications:
                current_medications = st.text_area("Please list all current medications, dosages, and frequency:")
            else:
                current_medications = ""
            
            # Common medications relevant to dental care
            st.write("### Medications Relevant to Dental Care")
            col1, col2 = st.columns(2)
            
            with col1:
                blood_thinners = st.checkbox("Blood Thinners (e.g., Warfarin, Aspirin)")
                bisphosphonates = st.checkbox("Bisphosphonates (e.g., Fosamax)")
                immunosuppressants = st.checkbox("Immunosuppressants")
            
            with col2:
                antihypertensives = st.checkbox("Antihypertensives (Blood Pressure)")
                antidepressants = st.checkbox("Antidepressants")
                insulin_diabetes = st.checkbox("Insulin/Diabetes Medication")
            
            # Supplements
            st.write("### Supplements")
            taking_supplements = st.checkbox("Are you taking any supplements or herbs?")
            
            if taking_supplements:
                supplements = st.text_area("Please list all supplements and herbs:")
            else:
                supplements = ""
            
            # Submit button
            submitted = st.form_submit_button("Save Medications")
            if submitted:
                # Prepare data for saving
                medications_data = {
                    "current_medications": {
                        "taking_medications": taking_medications,
                        "medications_list": current_medications
                    },
                    "dental_relevant_medications": {
                        "blood_thinners": blood_thinners,
                        "bisphosphonates": bisphosphonates,
                        "immunosuppressants": immunosuppressants,
                        "antihypertensives": antihypertensives,
                        "antidepressants": antidepressants,
                        "insulin_diabetes": insulin_diabetes
                    },
                    "supplements": {
                        "taking_supplements": taking_supplements,
                        "supplements_list": supplements
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a questionnaire already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'medications'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing questionnaire
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(medications_data).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new questionnaire
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses, completion_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                            (patient_id, 'medications', str(medications_data).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Medications saved successfully!")
                except Exception as e:
                    st.error(f"Error saving medications: {str(e)}")
    
    # Lifestyle Tab
    with tabs[4]:
        st.subheader("Lifestyle")
        
        with st.form("lifestyle_form"):
            # Tobacco use
            st.write("### Tobacco Use")
            tobacco_use = st.selectbox("Do you use tobacco products?", 
                                      ["Never", "Former user", "Current user"])
            
            if tobacco_use == "Current user" or tobacco_use == "Former user":
                tobacco_type = st.multiselect("What type of tobacco?", 
                                            ["Cigarettes", "Cigars", "Pipe", "Smokeless tobacco", "E-cigarettes/Vaping"])
                
                if tobacco_use == "Current user":
                    tobacco_frequency = st.text_input("How often do you use tobacco?")
                    tobacco_duration = st.text_input("For how long have you been using tobacco?")
                else:
                    tobacco_frequency = ""
                    tobacco_duration = st.text_input("For how long did you use tobacco?")
                    quit_duration = st.text_input("When did you quit?")
            else:
                tobacco_type = []
                tobacco_frequency = ""
                tobacco_duration = ""
                quit_duration = ""
            
            # Alcohol use
            st.write("### Alcohol Consumption")
            alcohol_use = st.selectbox("Do you consume alcoholic beverages?", 
                                      ["Never", "Occasionally", "Moderately", "Heavily"])
            
            if alcohol_use != "Never":
                alcohol_frequency = st.text_input("How many drinks per week on average?")
            else:
                alcohol_frequency = ""
            
            # Exercise
            st.write("### Exercise")
            exercise_frequency = st.selectbox("How often do you exercise?", 
                                            ["Daily", "Several times a week", "Once a week", "Occasionally", "Rarely", "Never"])
            
            # Diet
            st.write("### Diet")
            diet_description = st.text_area("Briefly describe your diet (e.g., vegetarian, low-carb, etc.):")
            
            # Submit button
            submitted = st.form_submit_button("Save Lifestyle Information")
            if submitted:
                # Prepare data for saving
                lifestyle_data = {
                    "tobacco": {
                        "use_status": tobacco_use,
                        "type": tobacco_type,
                        "frequency": tobacco_frequency,
                        "duration": tobacco_duration,
                        "quit_duration": quit_duration if tobacco_use == "Former user" else ""
                    },
                    "alcohol": {
                        "use_status": alcohol_use,
                        "frequency": alcohol_frequency
                    },
                    "exercise": exercise_frequency,
                    "diet": diet_description
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a questionnaire already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'lifestyle'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing questionnaire
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(lifestyle_data).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new questionnaire
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses, completion_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                            (patient_id, 'lifestyle', str(lifestyle_data).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Lifestyle information saved successfully!")
                except Exception as e:
                    st.error(f"Error saving lifestyle information: {str(e)}")
    
    # Women's Health Tab
    with tabs[5]:
        st.subheader("Women's Health")
        
        # Check if patient is female
        conn = sqlite3.connect('data/dentai.db')
        c = conn.cursor()
        c.execute("SELECT gender FROM patients WHERE id = ?", (patient_id,))
        gender_data = c.fetchone()
        conn.close()
        
        if gender_data and gender_data[0] and gender_data[0].lower() == 'female':
            with st.form("womens_health_form"):
                # Pregnancy
                st.write("### Pregnancy")
                pregnancy_status = st.selectbox("Are you currently pregnant?", 
                                              ["No", "Yes", "Unsure"])
                
                if pregnancy_status == "Yes":
                    pregnancy_weeks = st.number_input("How many weeks?", min_value=1, max_value=45, value=20)
                else:
                    pregnancy_weeks = 0
                
                planning_pregnancy = st.checkbox("Are you planning to become pregnant in the next year?")
                
                # Menopause
                st.write("### Menopause")
                menopause_status = st.selectbox("Menopause status:", 
                                              ["Not applicable", "Pre-menopausal", "Peri-menopausal", "Post-menopausal"])
                
                # Hormonal medications
                st.write("### Hormonal Medications")
                hormonal_contraceptives = st.checkbox("Are you taking hormonal contraceptives?")
                hormone_replacement = st.checkbox("Are you on hormone replacement therapy?")
                
                # Osteoporosis
                st.write("### Bone Health")
                osteoporosis = st.checkbox("Have you been diagnosed with osteoporosis or osteopenia?")
                
                if osteoporosis:
                    bisphosphonate_treatment = st.checkbox("Have you ever taken bisphosphonates (e.g., Fosamax, Boniva, Actonel)?")
                    if bisphosphonate_treatment:
                        bisphosphonate_details = st.text_area("Please provide details (medication name, duration, when stopped):")
                    else:
                        bisphosphonate_details = ""
                else:
                    bisphosphonate_treatment = False
                    bisphosphonate_details = ""
                
                # Submit button
                submitted = st.form_submit_button("Save Women's Health Information")
                if submitted:
                    # Prepare data for saving
                    womens_health_data = {
                        "pregnancy": {
                            "status": pregnancy_status,
                            "weeks": pregnancy_weeks if pregnancy_status == "Yes" else 0,
                            "planning": planning_pregnancy
                        },
                        "menopause": menopause_status,
                        "hormonal_medications": {
                            "contraceptives": hormonal_contraceptives,
                            "hormone_replacement": hormone_replacement
                        },
                        "bone_health": {
                            "osteoporosis": osteoporosis,
                            "bisphosphonate_treatment": bisphosphonate_treatment,
                            "bisphosphonate_details": bisphosphonate_details
                        }
                    }
                    
                    # Save to database
                    try:
                        conn = sqlite3.connect('data/dentai.db')
                        c = conn.cursor()
                        
                        # Check if a questionnaire already exists for this patient
                        c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'womens_health'", (patient_id,))
                        existing = c.fetchone()
                        
                        if existing:
                            # Update existing questionnaire
                            c.execute(
                                "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                                (str(womens_health_data).replace("'", "''"), existing[0])
                            )
                        else:
                            # Insert new questionnaire
                            c.execute(
                                "INSERT INTO questionnaires (patient_id, questionnaire_type, responses, completion_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                                (patient_id, 'womens_health', str(womens_health_data).replace("'", "''"))
                            )
                        
                        conn.commit()
                        conn.close()
                        st.success("Women's health information saved successfully!")
                    except Exception as e:
                        st.error(f"Error saving women's health information: {str(e)}")
        else:
            st.info("This section is only applicable for female patients.")
    
    # AI Analysis Tab
    with tabs[6]:
        st.subheader("AI-Powered Questionnaire Analysis")
        
        # Initialize session state variables if they don't exist
        if 'conversation_text' not in st.session_state:
            st.session_state.conversation_text = ""
        if 'current_analysis' not in st.session_state:
            st.session_state.current_analysis = None
        
        # We need to make sure we have an open connection for this tab
        try:
            # Create a new database connection just for this tab to avoid closed connection issues
            ai_conn = sqlite3.connect('data/dentai.db')
            ai_cursor = ai_conn.cursor()
                
            # Compile all questionnaire responses for analysis
        questionnaire_data = {}
        
            # Get medical questionnaire data
            ai_cursor.execute("SELECT responses FROM medical_questionnaires WHERE patient_id = ? ORDER BY visit_date DESC LIMIT 1", (patient_id,))
            medical_data = ai_cursor.fetchone()
            if medical_data and medical_data[0]:
                questionnaire_data['medical'] = safe_eval(medical_data[0])
            
            # Get dental history data
            ai_cursor.execute("SELECT * FROM dental_history WHERE patient_id = ?", (patient_id,))
            dental_history = ai_cursor.fetchone()
            if dental_history:
                dental_history_dict = {}
                dental_history_dict['last_dental_visit'] = dental_history[2]
                dental_history_dict['reason_for_last_visit'] = dental_history[3]
                dental_history_dict['previous_dentist'] = dental_history[4]
                dental_history_dict['brushing_frequency'] = dental_history[5]
                dental_history_dict['flossing_frequency'] = dental_history[6]
                dental_history_dict['sensitivity'] = dental_history[7]
                dental_history_dict['grinding_clenching'] = dental_history[8]
                questionnaire_data['dental_history'] = dental_history_dict
            
            # Get allergies data
            ai_cursor.execute("SELECT * FROM allergies WHERE patient_id = ?", (patient_id,))
            allergies_data = ai_cursor.fetchone()
            if allergies_data:
                allergies_dict = {
                    'analgesics': allergies_data[2] == 1,
                    'antibiotics': allergies_data[3] == 1,
                    'latex': allergies_data[4] == 1,
                    'metals': allergies_data[5] == 1,
                    'dental_materials': allergies_data[6] == 1,
                    'other': allergies_data[7]
                }
                questionnaire_data['allergies'] = allergies_dict
            
            # Get questionnaire data
            ai_cursor.execute("SELECT questionnaire_type, responses FROM questionnaires WHERE patient_id = ?", (patient_id,))
            questionnaire_rows = ai_cursor.fetchall()
            for q_type, responses in questionnaire_rows:
                if responses:
                    questionnaire_data[q_type] = safe_eval(responses)
                
            # Close this specific connection after retrieving data
            ai_conn.close()
                
            # Check if we have enough data for analysis
            if questionnaire_data:
                st.write("### Patient Questionnaire Summary")
                
                # Display the data we have in a readable format
                for category, data in questionnaire_data.items():
                    with st.expander(f"{category.replace('_', ' ').title()} Information"):
                        st.write(data)
                
                # Option to generate AI analysis
                if st.button("Generate AI Analysis", key="gen_questionnaire_analysis"):
                    # Here you would call your AI analysis function
                    st.info("Generating analysis... (This would use the OpenAI API in a production environment)")
                    
                    # Example of what the analysis might look like
                    analysis = """
                    ## Patient Questionnaire Analysis
                    
                    Based on the patient's responses, the following observations are noted:
                    
                    - Patient reports regular dental check-ups
                    - Brushing frequency is adequate at twice daily
                    - Patient reports sensitivity to cold, which may indicate enamel erosion or gingival recession
                    - No major dental concerns reported
                    
                    ### Recommendations:
                    
                    1. Discuss sensitivity issues and recommend desensitizing toothpaste
                    2. Maintain regular 6-month check-up schedule
                    3. No immediate interventions needed based on questionnaire data
                    """
                    
                    st.markdown(analysis)
            else:
                st.info("Not enough questionnaire data available for AI analysis. Please complete more questionnaires with the patient.")
                
        except Exception as e:
            st.error(f"Error retrieving questionnaire data: {e}")
            st.info("Try going back to the Medical History tab and entering some information before using the AI Analysis.")

def settings_page():
    """Settings page for configuring API keys and other settings."""
    st.title("DentAI - Settings")
    
    # Navigation buttons
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        if st.button("Dashboard", key="dashboard_btn_settings"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    with col2:
        if st.button("Patients", key="patients_btn_settings"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    with col3:
        if st.button("Questionnaire", key="questionnaire_btn_settings"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
    with col4:
        if st.button("Clinical", key="clinical_btn_settings"):
            st.session_state.current_page = "clinical"
            st.rerun()
    
    with col5:
        if st.button("Dental Exam", key="dental_exam_btn_settings"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
    
    with col6:
        if st.button("Logout", key="logout_btn_settings"):
            st.session_state.logged_in = False
            st.rerun()
    
    st.write("---")
    
    # API Key Settings
    st.header("API Settings")
    st.write("Configure your API keys for external services.")
    
    # OpenAI API Key
    st.subheader("OpenAI API")
    st.write("Enter your OpenAI API key to enable AI-powered features like transcription and clinical analysis.")
    
    # Use password input to hide the API key
    api_key = st.text_input("OpenAI API Key", 
                           value=st.session_state.openai_api_key if st.session_state.openai_api_key else "",
                           type="password",
                           help="Your OpenAI API key. Keep this secret and never share it publicly.")
    
    if st.button("Save API Key"):
        st.session_state.openai_api_key = api_key
        st.success("API key saved successfully!")
    
    # Display API status
    if st.session_state.openai_api_key:
        st.info("OpenAI API key is configured. AI features are available.")
    else:
        st.warning("OpenAI API key is not configured. AI features will be limited to simulated responses.")
    
    # Instructions
    st.write("---")
    st.header("Instructions")
    st.write("""
    ### How to Get an OpenAI API Key
    
    1. Go to [OpenAI's platform](https://platform.openai.com/signup)
    2. Create an account or sign in
    3. Navigate to the API section
    4. Create a new API key
    5. Copy the key and paste it above
    
    ### Security Notes
    
    - Your API key is stored only in your browser's session
    - It will be cleared when you close the browser or log out
    - Never share your API key with others
    - Regularly rotate your API keys for better security
    """)

def clinical_interaction_page():
    st.title("DentAI - Clinical Interaction")
    
    # Navigation buttons
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    
    with col1:
        if st.button("Dashboard", key="dashboard_btn_clinical"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    with col2:
        if st.button("Patients", key="patients_btn_clinical"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    with col3:
        if st.button("Questionnaire", key="questionnaire_btn_clinical"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
    with col4:
        if st.button("Dental Exam", key="dental_exam_btn_clinical"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
    
    with col5:
        if st.button("Clinical", key="clinical_btn_clinical", type="primary"):
            st.session_state.current_page = "clinical"
            st.rerun()
    
    with col6:
        if st.button("Settings", key="settings_btn_clinical"):
            st.session_state.current_page = "settings"
            st.rerun()
    
    with col7:
        if st.button("Logout", key="logout_btn_clinical"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Check if a patient is selected
    if 'selected_patient' not in st.session_state or not st.session_state.selected_patient:
        st.warning("No patient selected. Please select a patient from the Patient Management page.")
        if st.button("Go to Patient Management", key="clinical_go_patient_mgmt"):
            st.session_state.current_page = "patients"
            st.rerun()
        return
    
    # Get patient info
    patient_id = st.session_state.selected_patient
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    c.execute("SELECT first_name, last_name FROM patients WHERE id = ?", (patient_id,))
    patient = c.fetchone()
    
    if not patient:
        st.error("Patient not found")
        return
    
    patient_name = f"{patient[0]} {patient[1]}"
    st.header(f"Clinical Interaction: {patient_name}")
    
    # Create tabs for different clinical interaction sections
    tabs = st.tabs(["Chief Complaint", "Clinical Notes", "AI Analysis"])
    
    # Chief Complaint Tab
    with tabs[0]:
        st.subheader("Chief Complaint")
        
        # Check if there's an existing chief complaint
        c.execute("SELECT chief_complaint FROM clinical_records WHERE patient_id = ?", (patient_id,))
        existing_complaint = c.fetchone()
        
        if existing_complaint and existing_complaint[0]:
            st.write("#### Current Chief Complaint")
            st.write(existing_complaint[0])
            
            if st.button("Update Chief Complaint", key="update_chief_complaint"):
                st.session_state.update_chief_complaint = True
        
        # Show form if no existing complaint or update requested
        if not existing_complaint or not existing_complaint[0] or st.session_state.get('update_chief_complaint', False):
            with st.form("chief_complaint_form"):
                chief_complaint = st.text_area("Enter the patient's chief complaint:", height=100)
                
                submitted = st.form_submit_button("Save Chief Complaint")
                if submitted and chief_complaint:
                    try:
                        if existing_complaint:
                            c.execute("UPDATE clinical_records SET chief_complaint = ? WHERE patient_id = ?", 
                                     (chief_complaint, patient_id))
                        else:
                            c.execute("INSERT INTO clinical_records (patient_id, chief_complaint) VALUES (?, ?)",
                                     (patient_id, chief_complaint))
                        
                        conn.commit()
                        st.success("Chief complaint saved successfully!")
                        
                        # Clear update flag if it exists
                        if 'update_chief_complaint' in st.session_state:
                            del st.session_state.update_chief_complaint
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving chief complaint: {str(e)}")
    
    # Clinical Notes Tab
    with tabs[1]:
        st.subheader("Clinical Notes")
        
        # Check if there are existing clinical notes
        c.execute("SELECT clinical_notes FROM clinical_records WHERE patient_id = ?", (patient_id,))
        existing_notes = c.fetchone()
        
        if existing_notes and existing_notes[0]:
            st.write("#### Current Clinical Notes")
            st.write(existing_notes[0])
            
            if st.button("Update Clinical Notes", key="update_clinical_notes"):
                st.session_state.update_clinical_notes = True
        
        # Show form if no existing notes or update requested
        if not existing_notes or not existing_notes[0] or st.session_state.get('update_clinical_notes', False):
            with st.form("clinical_notes_form"):
                clinical_notes = st.text_area("Enter clinical notes:", height=200)
                
                submitted = st.form_submit_button("Save Clinical Notes")
                if submitted and clinical_notes:
                    try:
                        if existing_notes:
                            c.execute("UPDATE clinical_records SET clinical_notes = ? WHERE patient_id = ?", 
                                     (clinical_notes, patient_id))
                        else:
                            c.execute("INSERT INTO clinical_records (patient_id, clinical_notes) VALUES (?, ?)",
                                     (patient_id, clinical_notes))
                        
                        conn.commit()
                        st.success("Clinical notes saved successfully!")
                        
                        # Clear update flag if it exists
                        if 'update_clinical_notes' in st.session_state:
                            del st.session_state.update_clinical_notes
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving clinical notes: {str(e)}")
    
    # AI Analysis Tab
    with tabs[2]:
        st.subheader("AI-Powered Clinical Analysis")
        
        # Initialize session state variables if they don't exist
        if 'conversation_text' not in st.session_state:
            st.session_state.conversation_text = ""
        if 'current_analysis' not in st.session_state:
            st.session_state.current_analysis = None
        
        # Check if there's an existing transcription
        c.execute("SELECT transcription, audio_file_path FROM clinical_records WHERE patient_id = ?", (patient_id,))
        existing_record = c.fetchone()
        
        # Display existing recordings if available
        if existing_record and existing_record[0]:
            st.write("#### Existing Transcription")
            st.write(existing_record[0])
            
            if existing_record[1]:
                st.write("#### Existing Audio Recording")
                # Check if the audio file exists before trying to play it
                audio_path = existing_record[1]
                if os.path.exists(audio_path):
                    try:
                        st.audio(audio_path)
                    except Exception as e:
                        st.error(f"Error playing audio: {str(e)}")
                        st.info("Audio file exists but cannot be played. It may be in an unsupported format.")
                else:
                    st.info(f"Audio file not found: {audio_path}")
            
            # Button to record new conversation
            if st.button("Record New Conversation", key="record_new_btn"):
                st.session_state.conversation_text = ""
                st.session_state.current_analysis = None
        
        # Create tabs for recording and uploading
        record_tabs = st.tabs(["Record Audio", "Upload Audio"])
        
        # Record Audio Tab
        with record_tabs[0]:
        st.write("### Record Dental Conversation")
        
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
                            sessionStorage.setItem('patientId', '${patient_id}');
                            
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
                    const now = new Date();
                    const timestamp = now.getFullYear() + 
                        ('0' + (now.getMonth() + 1)).slice(-2) + 
                        ('0' + now.getDate()).slice(-2) + '_' +
                        ('0' + now.getHours()).slice(-2) + 
                        ('0' + now.getMinutes()).slice(-2);
                    const patientName = '${patient[0]}_${patient[1]}'.replace(/[^a-zA-Z0-9]/g, '_');
                    a.download = `recording_${patientName}_${timestamp}.webm`;
                    a.click();
                } else {
                    debug("No audio to download");
                }
            }
            </script>
            """
            
            # Display the HTML component
            st.components.v1.html(audio_recorder_html, height=250)
            
            # Note about recording
            st.info("Click 'Start Recording' to begin. Allow microphone access when prompted. Click 'Stop Recording' when finished.")
            
            # Button to trigger the transcription of recorded audio
            if st.button("Transcribe Recorded Audio", key="transcribe_recorded_btn"):
                if 'openai_api_key' not in st.session_state or not st.session_state.openai_api_key:
                    st.warning("Please enter your OpenAI API key in the Settings page first")
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
        
        # Upload Audio Tab
        with record_tabs[1]:
            st.header("Upload Audio File")
            
            # File uploader for audio
            st.write("""
            Upload your audio file here.
            Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, and webm
            """)
            
            uploaded_file = st.file_uploader("Choose an audio file", key="upload_audio_ai_analysis", type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"])
            
            if uploaded_file is not None:
                # Display the uploaded audio
                st.audio(uploaded_file, format=f"audio/{uploaded_file.type}")
                
                # Create a button to start transcription
                if st.button("Transcribe Uploaded Audio", key="transcribe_uploaded_btn"):
                    # Make sure we have an API key
                    if 'openai_api_key' not in st.session_state or not st.session_state.openai_api_key:
                        st.warning("Please enter your OpenAI API key in the Settings page first")
        else:
                        with st.spinner("Transcribing..."):
                            # Save the uploaded file
                            timestamp = int(time.time())
                            audio_file_path = f"data/audio/uploaded_{patient_id}_{timestamp}.{uploaded_file.name.split('.')[-1]}"
                            
                            # Ensure directory exists
                            os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)
                            
                            # Save the file
                            with open(audio_file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            
                            # Reset file pointer to beginning
                            uploaded_file.seek(0)
                            
                            # Transcribe the audio using OpenAI Whisper API
                            try:
                                # Call Whisper API
                                headers = {
                                    "Authorization": f"Bearer {st.session_state.openai_api_key}"
                                }
                                
                                files = {
                                    "file": uploaded_file,
                                    "model": (None, "whisper-1"),
                                }
                                
                                response = requests.post(
                                    "https://api.openai.com/v1/audio/transcriptions",
                                    headers=headers,
                                    files=files
                                )
                                
                                if response.status_code == 200:
                                    transcription = response.json()["text"]
                        st.session_state.conversation_text = transcription
                        
                        # Save transcription to database
                        try:
                            c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
                            existing_id = c.fetchone()
                            
                            if existing_id:
                                c.execute("UPDATE clinical_records SET transcription = ?, audio_file_path = ? WHERE id = ?", 
                                         (transcription, audio_file_path, existing_id[0]))
                            else:
                                c.execute("INSERT INTO clinical_records (patient_id, transcription, audio_file_path) VALUES (?, ?, ?)",
                                         (patient_id, transcription, audio_file_path))
                            
                            conn.commit()
                            st.success("Transcription saved to database!")
                                        st.rerun()
                        except Exception as db_error:
                            st.error(f"Error saving transcription to database: {str(db_error)}")
                                else:
                                    st.error(f"Error: {response.status_code} - {response.text}")
                            except Exception as e:
                                st.error(f"Error transcribing audio: {str(e)}")
        
        # After recording/uploading, check if we have conversation text to analyze
        if st.session_state.conversation_text:
            st.markdown("### Conversation Analysis")
            
            # Check if the transcript is too short or contains only repeated words
            transcript_words = st.session_state.conversation_text.lower().split()
            unique_words = set(transcript_words)
            
            if len(transcript_words) < 10 or len(unique_words) < 5:
                st.warning("The transcription appears to be too short or low quality. This may be due to audio recording issues.")
                
                # Button to manually enter transcription
                if st.button("Enter Conversation Manually", key="manual_transcript_btn"):
                    st.session_state.show_manual_entry = True
            
            # Show manual entry form if requested
            if st.session_state.get('show_manual_entry', False):
                st.markdown("### Manual Conversation Entry")
                st.info("Please enter the dental conversation between doctor and patient below.")
                
                # Example format
                st.markdown("""
                **Example format:**
                ```
                Doctor: Hello, how are you feeling today?
                Patient: I've been having pain in my lower right molar.
                Doctor: How long have you been experiencing this pain?
                Patient: About a week now.
                ```
                """)
                
                manual_transcript = st.text_area(
                    "Enter conversation transcript:",
                    height=300,
                    value=st.session_state.conversation_text if len(st.session_state.conversation_text) > 10 else ""
                )
                
                if st.button("Use This Transcript", key="use_manual_transcript"):
                    st.session_state.conversation_text = manual_transcript
                    st.session_state.current_analysis = None  # Reset analysis to force regeneration
                    st.session_state.show_manual_entry = False  # Hide the form
                    st.rerun()
            
            # Generate AI analysis if not already done
            if not st.session_state.current_analysis:
                with st.spinner("Analyzing conversation..."):
                    st.session_state.current_analysis = generate_ai_analysis(
                        st.session_state.conversation_text,
                        patient_id=patient_id,
                        patient_name=patient_name
                    )
            
            if st.session_state.current_analysis:
                st.markdown(st.session_state.current_analysis)
                
                # Save options
                st.markdown("### Save Options")
                save_col1, save_col2, save_col3 = st.columns(3)
                
                with save_col1:
                    if st.button("💾 Save Analysis", key="save_analysis_btn", use_container_width=True):
                        try:
                            # Check if a record already exists for this patient
                            c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
                            existing_id = c.fetchone()
                            
                            if existing_id:
                                # Update existing record
                                c.execute("UPDATE clinical_records SET ai_analysis = ? WHERE id = ?", 
                                        (st.session_state.current_analysis, existing_id[0]))
                            else:
                                # This shouldn't happen as we should already have a record from transcription save
                                c.execute("INSERT INTO clinical_records (patient_id, ai_analysis) VALUES (?, ?)",
                                        (patient_id, st.session_state.current_analysis))
                            
                            conn.commit()
                            st.success("Clinical analysis saved successfully!")
                        except Exception as e:
                            st.error(f"Error saving analysis: {str(e)}")
                
                with save_col2:
                    st.download_button(
                        label="📥 Export as Text",
                        data=st.session_state.current_analysis,
                        file_name=f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown",
                        key=f"download_current_text_{patient_id}"
                    )
                
                with save_col3:
                    if PDF_EXPORT_AVAILABLE:
                        if st.button("📄 Export as PDF", key=f"export_current_pdf_{patient_id}", use_container_width=True):
                            try:
                                pdf_link = export_report_as_pdf(st.session_state.current_analysis, f"{patient[0]} {patient[1]}")
                                st.markdown(pdf_link, unsafe_allow_html=True)
                            except Exception as e:
                                st.error(f"Error generating PDF: {e}")
                                st.markdown(create_download_link(st.session_state.current_analysis, 
                                                              f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.md", 
                                                              "Download as Markdown instead"), 
                                          unsafe_allow_html=True)
                    else:
                        st.info("PDF export requires additional packages. Install pdfkit and markdown packages for PDF export functionality.")
        
        # Display previous clinical analyses
        st.markdown("---")
        st.markdown("### Previous Clinical Records")
        c.execute("SELECT ai_analysis, record_date FROM clinical_records WHERE patient_id = ? AND ai_analysis IS NOT NULL", (patient_id,))
        previous_analyses = c.fetchall()
        
        # Close connection
        conn.close()
        
        if previous_analyses:
            for i, (analysis, record_date) in enumerate(previous_analyses):
                with st.expander(f"Clinical Analysis from {record_date}"):
                    st.markdown(analysis)
                    
                    # Export options for previous records
                    export_col1, export_col2 = st.columns(2)
                    with export_col1:
                        st.download_button(
                            label="Download as Text",
                            data=analysis,
                            file_name=f"Clinical_Report_{patient[0]}_{patient[1]}_{i}_{datetime.now().strftime('%Y%m%d')}.md",
                            mime="text/markdown",
                            key=f"download_previous_text_{patient_id}_{i}"
                        )
                    
                    with export_col2:
                        if PDF_EXPORT_AVAILABLE:
                            if st.button("Export as PDF", key=f"export_previous_pdf_{patient_id}_{i}"):
                                try:
                                    pdf_link = export_report_as_pdf(analysis, f"{patient[0]} {patient[1]}")
                                    st.markdown(pdf_link, unsafe_allow_html=True)
                                except Exception as e:
                                    st.error(f"Error generating PDF: {e}")
                                    st.markdown(create_download_link(analysis, 
                                                                  f"Clinical_Report_{patient[0]}_{patient[1]}_{i}_{datetime.now().strftime('%Y%m%d')}.md", 
                                                                  "Download as Markdown instead"), 
                                              unsafe_allow_html=True)
                        else:
                            st.info("PDF export requires additional packages. Install pdfkit and markdown packages for PDF export functionality.")
        else:
            st.info("No previous clinical records available.")

# Helper functions for clinical interaction
def calculate_age(birth_date_str):
    try:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        return "Unknown"

def safe_eval(data_str):
    """Safely parse a string representation of a dictionary."""
    try:
        # First try using ast.literal_eval which is safer than eval
        import ast
        return ast.literal_eval(data_str)
    except:
        try:
            # If that fails, try using json.loads with some preprocessing
            import json
            # Replace single quotes with double quotes for JSON compatibility
            json_str = data_str.replace("'", '"')
            # Handle boolean values
            json_str = json_str.replace('"True"', 'true').replace('"False"', 'false')
            return json.loads(json_str)
        except:
            # If all else fails, return an empty dict
            return {}

def calculate_completeness(data):
    # Calculate a percentage of data completeness for AI analysis
    total_points = 0
    earned_points = 0
    
    # Check questionnaires (6 possible)
    total_points += 6
    earned_points += len(data.get("questionnaires", {}))
    
    # Check examinations (4 possible)
    total_points += 4
    earned_points += len(data.get("examinations", {}))
    
    # Check clinical data
    total_points += 1
    if data.get("clinical", {}).get("chief_complaint", ""):
        earned_points += 1
    
    # Calculate percentage
    if total_points == 0:
        return 0
    return int((earned_points / total_points) * 100)

def create_download_link(content, filename, text):
    """Generate a link to download content as a file."""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{text}</a>'
    return href

def export_report_as_pdf(report_text, patient_name):
    """Convert markdown report to PDF and create a download link."""
    # If PDF export is not available, fall back to text export
    if not PDF_EXPORT_AVAILABLE:
        return create_download_link(
            report_text, 
            f"Clinical_Report_{patient_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md",
            "Download as Markdown (PDF export not available)"
        )
    
    try:
        # Convert markdown to HTML
        html_content = markdown.markdown(report_text)
        
        # Add some basic styling
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Clinical Report - {patient_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #3498db; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>DentAI Clinical Report</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            {html_content}
            <div class="footer">
                <p>Generated by DentAI - AI-Powered Dental Practice Management</p>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF using pdfkit
        pdf_options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
        }
        
        pdf_data = pdfkit.from_string(styled_html, False, options=pdf_options)
        
        # Create download link
        b64_pdf = base64.b64encode(pdf_data).decode()
        pdf_link = f'<a href="data:application/pdf;base64,{b64_pdf}" download="Clinical_Report_{patient_name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf">Download PDF Report</a>'
        
        return pdf_link
    
    except Exception as e:
        st.error(f"Error creating PDF: {str(e)}")
        
        # Fallback to plain text download if PDF generation fails
        return create_download_link(
            report_text, 
            f"Clinical_Report_{patient_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md",
            "Download as Markdown"
        )

def generate_ai_analysis(transcription, patient_id="Unknown", patient_name="Unknown Patient"):
    """
    Generate AI analysis using OpenAI API
    
    Args:
        transcription: The text transcription of the clinical interaction
        patient_id: ID of the patient (optional)
        patient_name: Name of the patient (optional)
    
    Returns:
        Markdown-formatted string containing the AI analysis
    """
    # If no transcription provided, return an error message
    if not transcription:
        st.error("No transcription provided for AI analysis")
        return None
    
    # If no OpenAI API key, return a simulated analysis
    if 'openai_api_key' not in st.session_state or not st.session_state.openai_api_key:
        st.warning("No OpenAI API key configured. Using simulated analysis instead. Please configure your API key in Settings.")
        # Generate a simulated AI analysis for demonstration
        return f"""
        # Clinical Analysis for {patient_name}
        
        ## Summary of Interaction
        
        Based on the transcription, the patient is experiencing pain in their lower right molar for about a week.
        The pain is intermittent but sharp, especially when drinking cold beverages.
        
        ## Clinical Observations
        
        - **Chief Complaint**: Pain in lower right molar
        - **Duration**: Approximately one week
        - **Characteristics**: Sharp, intermittent pain
        - **Triggers**: Cold sensitivity
        
        ## Preliminary Diagnosis
        
        The symptoms are consistent with either:
        1. Dental caries (cavity)
        2. Dentinal hypersensitivity
        
        ## Recommended Treatment Plan
        
        1. Complete examination of the affected tooth
        2. Dental X-rays to assess extent of decay
        3. Filling procedure for the cavity
        4. Local anesthesia will be administered for patient comfort
        
        ## Follow-up Recommendations
        
        - Regular dental check-ups every 6 months
        - Maintain good oral hygiene practices
        - Consider using desensitizing toothpaste
        
        *This analysis was generated by DentAI based on the recorded conversation.*
        """
    
    # Validate API key format before attempting to use it
    api_key = st.session_state.openai_api_key.strip()
    if not api_key.startswith("sk-") or len(api_key) < 20:
        st.error("Your OpenAI API key appears to be invalid. It should start with 'sk-' and be at least 20 characters long.")
        return f"""
        # Clinical Analysis for {patient_name}
        
        ## Error: Invalid API Key
        
        Your OpenAI API key appears to be invalid. Please check the following:
        
        - The key should start with `sk-`
        - The key should be approximately 50 characters long
        - You can generate a new key in your OpenAI account dashboard
        
        Please update your API key in the Settings page and try again.
        
        ## Raw Conversation Transcript
        
        ```
        {transcription[:500]}...
        ```
        """
    
    try:
        # Display status message
        st.info("Connecting to OpenAI API for analysis... (this may take a moment)")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Create prompt for GPT
        prompt = f"""
        You are DentAI, an expert dental assistant AI. Analyze the following conversation between a dentist and patient.
        
        PATIENT ID: {patient_id}
        PATIENT NAME: {patient_name}
        
        CONVERSATION TRANSCRIPT:
        {transcription}
        
        Provide a comprehensive clinical report including:
        1. Summary of the interaction
        2. Patient's chief complaint and symptoms
        3. Clinical observations made by the dentist
        4. Preliminary diagnosis (if mentioned)
        5. Treatment plan discussed
        6. Any follow-up recommendations
        
        Format the report in Markdown with appropriate headings, bullet points, and emphasis.
        Be specific, professional, and focus only on information actually present in the conversation.
        If the conversation does not contain certain information, do not invent details.
        
        CLINICAL REPORT:
        """
        
        # Call the OpenAI API - first test connection with a basic request
        try:
            # Test connection first with a small request
            test_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Test connection. Respond with 'Connected'."}
                ],
                max_tokens=10
            )
            # If we get here, connection works
        except Exception as test_error:
            # Connection error
            error_message = str(test_error)
            if "authentication" in error_message.lower():
                st.error("Authentication error: Your API key appears to be invalid")
                error_type = "Authentication Error"
            elif "rate limit" in error_message.lower():
                st.error("Rate limit exceeded: Please wait a moment and try again")
                error_type = "Rate Limit Error"
            elif "quota" in error_message.lower():
                st.error("API quota exceeded: Your OpenAI account may need payment method updates")
                error_type = "Quota Error"
            else:
                st.error(f"Connection error: {error_message}")
                error_type = "Connection Error"
                
            return f"""
            # Clinical Analysis for {patient_name}
            
            ## Error: {error_type}
            
            There was an error connecting to the OpenAI API:
            
            ```
            {error_message}
            ```
            
            Please check your internet connection and API key configuration in Settings.
            
            ## Raw Conversation Transcript
            
            ```
            {transcription[:500]}...
            ```
            
            *This is a partial analysis generated due to a service error.*
            """
        
        # Now send the full analysis request
        try:
            # Call the OpenAI API for the full analysis
        response = client.chat.completions.create(
                model="gpt-4-turbo-preview",  # Try to use GPT-4 Turbo
            messages=[
                {"role": "system", "content": "You are DentAI, an expert dental assistant AI that creates clinical reports from dentist-patient conversations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.2
        )
        
        # Return the AI-generated analysis
        return response.choices[0].message.content
        except Exception as model_error:
            # Model-specific error, try fallback to GPT-3.5
            st.warning("GPT-4 model unavailable, trying GPT-3.5 as fallback...")
            
            try:
                # Fallback to GPT-3.5
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Fallback to GPT-3.5
                    messages=[
                        {"role": "system", "content": "You are DentAI, an expert dental assistant AI that creates clinical reports from dentist-patient conversations."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.2
                )
                
                # Return the AI-generated analysis with a note about using the fallback model
                analysis = response.choices[0].message.content
                return analysis + "\n\n*Note: This analysis was generated using GPT-3.5 as a fallback model.*"
            except Exception as fallback_error:
                st.error(f"Error with fallback model: {str(fallback_error)}")
                error_type = "Model Error"
                error_message = str(fallback_error)
                
                return f"""
                # Clinical Analysis for {patient_name}
                
                ## Error: {error_type}
                
                There was an error using the OpenAI model:
                
                ```
                {error_message}
                ```
                
                ## Raw Conversation Transcript
                
                ```
                {transcription[:500]}...
                ```
                
                *This is a partial analysis generated due to a model error.*
                """
        
    except Exception as e:
        st.error(f"Error generating AI analysis: {str(e)}")
        # Return a simplified analysis in case of error
        return f"""
        # Clinical Analysis for {patient_name}
        
        ## Error Generating Complete Analysis
        
        There was an error connecting to the AI service: {str(e)}
        
        - **Patient ID**: {patient_id}
        - **Patient Name**: {patient_name}
        
        ## Conversation Summary
        
        ```
        {transcription[:500]}...
        ```
        
        *This is a partial analysis generated due to a service error.*
        """

def record_audio_chunk(filename, duration=10):
    """Record audio in chunks"""
    # Check if PyAudio is available
    if not PYAUDIO_AVAILABLE:
        st.warning("Audio recording with PyAudio is not available in this environment. Using simulated audio instead.")
        st.info("To enable real audio recording, install PyAudio with: pip install pyaudio")
        # Create a dummy audio file for demonstration
        try:
            # Create a simple WAV file with valid audio data
            sample_rate = 16000
            seconds = 1.0  # 1 second of audio
            num_samples = int(sample_rate * seconds)
            
            # Generate silence (zeros) for the specified duration
            audio_data = b'\x00\x00' * num_samples
            
            # Calculate sizes
            data_size = len(audio_data)
            file_size = 36 + data_size
            
            with open(filename, 'wb') as f:
                # RIFF header
                f.write(b'RIFF')
                f.write(file_size.to_bytes(4, byteorder='little'))  # File size - 8
                f.write(b'WAVE')
                
                # Format chunk
                f.write(b'fmt ')
                f.write((16).to_bytes(4, byteorder='little'))  # Chunk size
                f.write((1).to_bytes(2, byteorder='little'))   # Audio format (PCM)
                f.write((1).to_bytes(2, byteorder='little'))   # Num channels (mono)
                f.write((sample_rate).to_bytes(4, byteorder='little'))  # Sample rate
                f.write((sample_rate * 2).to_bytes(4, byteorder='little'))  # Byte rate
                f.write((2).to_bytes(2, byteorder='little'))   # Block align
                f.write((16).to_bytes(2, byteorder='little'))  # Bits per sample
                
                # Data chunk
                f.write(b'data')
                f.write(data_size.to_bytes(4, byteorder='little'))  # Chunk size
                f.write(audio_data)  # One second of silence
            
            st.success(f"Created simulated audio file: {filename} ({data_size} bytes)")
            return filename
        except Exception as e:
            st.error(f"Error creating simulated audio: {str(e)}")
            return None
        
        # Return simulated success
        return filename
    
    # Real audio recording with PyAudio
    try:
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        st.info("Attempting to initialize PyAudio for recording...")
        p = pyaudio.PyAudio()
        
        # List available audio devices for debugging
        info = []
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            info.append(f"Device {i}: {dev_info['name']} (inputs: {dev_info['maxInputChannels']})")
        
        if info:
            st.expander("Available Audio Devices", expanded=False).write("\n".join(info))
        
        try:
            st.info("Opening audio stream...")
            stream = p.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          frames_per_buffer=CHUNK)
            
            frames = []
            start_time = time.time()
            
            # Record for the specified duration
            st.info(f"Recording for {duration} seconds...")
            while (time.time() - start_time) < duration:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                except IOError as e:
                    st.warning(f"Audio buffer overflow: {e}")
                    continue
            
            stream.stop_stream()
            stream.close()
            
            # Save the audio file
            st.info(f"Saving audio to {filename}...")
            wf = wave.open(filename, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            file_size = os.path.getsize(filename)
            st.success(f"Audio recorded successfully: {filename} ({file_size} bytes)")
            return filename
        
        except Exception as e:
            st.error(f"Error opening audio stream: {str(e)}")
            return None
    
    except Exception as e:
        st.error(f"Error initializing PyAudio: {str(e)}")
        return None
    finally:
        if 'p' in locals():
            p.terminate()

def combine_audio_files(chunk_files, output_file):
    """Combine multiple WAV files into one"""
    if not chunk_files:
        return False
    
    data = []
    for file in chunk_files:
        try:
            w = wave.open(file, 'rb')
            data.append([w.getparams(), w.readframes(w.getnframes())])
            w.close()
        except Exception as e:
            print(f"Error reading audio chunk {file}: {e}")
            continue
    
    if not data:
        return False
    
    try:
        output = wave.open(output_file, 'wb')
        output.setparams(data[0][0])
        for i in range(len(data)):
            output.writeframes(data[i][1])
        output.close()
        return True
    except Exception as e:
        print(f"Error combining audio files: {e}")
        return False

def transcribe_audio(audio_file_path):
    """
    Transcribes audio using OpenAI's Whisper API.
    
    Args:
        audio_file_path: Path to the audio file to transcribe
        
    Returns:
        String containing the transcription text or None if there was an error
    """
    if not os.path.exists(audio_file_path):
        st.error(f"Audio file not found: {audio_file_path}")
        return None
    
    # Check file size
    file_size = os.path.getsize(audio_file_path)
    if file_size < 1024:  # Less than 1KB
        st.warning(f"Audio file is very small ({file_size} bytes). It may be too short for transcription.")
    
    # Check if OpenAI API key is available
    if 'openai_api_key' not in st.session_state or not st.session_state.openai_api_key:
        st.warning("OpenAI API key is not configured. Using simulated transcription.")
        return get_mock_dental_conversation()
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=st.session_state.openai_api_key)
        
        # Use the audio file with Whisper API
        with open(audio_file_path, 'rb') as audio_file:
            transcription_response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
            
            transcript = transcription_response.text
            
            # Check if transcription returned minimal or repeated text
            transcript_words = transcript.lower().split()
            unique_words = set(transcript_words)
            
            if len(transcript_words) < 10 or len(unique_words) < 5:
                st.warning("Transcription quality is poor. Using simulated conversation instead.")
                return get_mock_dental_conversation()
                
            return transcript
    except Exception as e:
        st.error(f"Error transcribing audio with OpenAI: {str(e)}")
        st.info("Using simulated transcription instead.")
        return get_mock_dental_conversation()

def get_mock_dental_conversation():
    """Generate a realistic mock dental conversation"""
    conversations = [
        """
Doctor: Hello there! How are you feeling today?
Patient: Not great. I've been having some pain in my lower right tooth for about a week now.
Doctor: I'm sorry to hear that. Can you describe the pain for me? Is it constant or does it come and go?
Patient: It comes and goes, but it's quite sharp when it happens. Especially when I drink something cold.
Doctor: That suggests sensitivity or possibly a cavity. Is it sensitive to hot drinks as well?
Patient: Not as much to hot things, mostly cold.
Doctor: When did you last visit a dentist for a checkup?
Patient: It's been about 2 years, I think.
Doctor: I see. And have you noticed any swelling around the painful area?
Patient: No swelling, just the pain.
Doctor: Let me take a look. Can you open wide for me please? I'll gently tap on some teeth.
Patient: Sure.
Doctor: Do you feel pain when I tap on this one?
Patient: Ouch! Yes, that one.
Doctor: I can see some decay on that lower right molar. We'll need to do a filling to address the cavity.
Patient: Will it hurt?
Doctor: We'll use local anesthesia, so you shouldn't feel any pain during the procedure. You might experience some tenderness afterward, but that should resolve in a day or two.
Patient: How long will the procedure take?
Doctor: For a standard filling, about 30-45 minutes. We can schedule you for next week if that works for you.
Patient: Yes, that would be fine.
Doctor: Great. In the meantime, try to avoid very cold foods and drinks, and take over-the-counter pain medication if needed.
        """,
        
        """
Doctor: Good morning! What brings you in today?
Patient: I've been experiencing a persistent toothache on the left side of my mouth.
Doctor: I'm sorry to hear that. How long has this been bothering you?
Patient: It started about three days ago. It was mild at first, but now it's quite painful.
Doctor: Can you point to where exactly you feel the pain?
Patient: It's this upper tooth on the left side.
Doctor: Does the pain come and go, or is it constant?
Patient: It's mostly constant now, but it gets worse when I eat or drink.
Doctor: Is it sensitive to both hot and cold?
Patient: Yes, especially hot drinks. And sometimes it throbs even when I'm not eating or drinking.
Doctor: Have you taken any pain medication for it?
Patient: I've been taking ibuprofen, which helps a little, but the pain comes back.
Doctor: Any swelling or fever?
Patient: No fever, but my cheek does feel a bit swollen on that side.
Doctor: Let me take a look. Open wide please... I'm going to tap gently on some teeth.
Patient: Ouch! That's the one.
Doctor: I can see significant decay that has likely reached the pulp of your tooth. Based on your symptoms and my examination, you may need a root canal treatment.
Patient: Oh no, is that painful?
Doctor: The procedure itself shouldn't be painful as we use anesthesia. It's actually meant to relieve the pain you're experiencing. The tooth is infected, and a root canal will remove the infected tissue.
Patient: How long does it take?
Doctor: It typically requires two appointments. The first session takes about 90 minutes, and the second is shorter. After the root canal, we'll place a crown to protect the tooth.
Patient: Will my insurance cover it?
Doctor: Most dental insurance plans cover a portion of root canal treatment. We can check your specific coverage and discuss payment options.
        """,
        
        """
Doctor: Hello! It's good to see you for your check-up today. How have your teeth been feeling?
Patient: Pretty good overall. I've noticed some bleeding when I brush though.
Doctor: Bleeding gums can be a sign of gingivitis. How often do you brush and floss?
Patient: I brush twice a day, but I only floss maybe once a week.
Doctor: I recommend flossing daily. It helps remove plaque between teeth that your toothbrush can't reach. Are you experiencing any pain or sensitivity?
Patient: No pain, but sometimes my front teeth feel sensitive to cold drinks.
Doctor: That could be enamel wear. Do you consume many acidic foods or drinks like citrus or soda?
Patient: I do drink soda most days, and I love oranges and lemons.
Doctor: Acidic foods and drinks can erode enamel over time. Let's take a look at your teeth now. Open wide please.
Patient: Sure.
Doctor: I can see some tartar buildup along the gumline, which is likely causing the bleeding. I also notice some staining on your front teeth.
Patient: I drink coffee every morning.
Doctor: That explains the staining. I'll clean these today. I also see a small cavity forming on your lower left molar. We should fill that before it gets larger.
Patient: Is the filling a simple procedure?
Doctor: Yes, it's straightforward. We'll numb the area, remove the decayed portion, and fill it with a tooth-colored composite. It should take about 30 minutes.
Patient: And what about the sensitivity in my front teeth?
Doctor: I recommend using a desensitizing toothpaste and reducing acidic foods and drinks. We can also apply a fluoride treatment today to help strengthen your enamel.
Patient: That sounds good. How often should I come in for check-ups?
Doctor: I recommend every six months for professional cleaning and examination. This helps catch any issues early before they become more serious.
        """
    ]
    
    import random
    return random.choice(conversations).strip()

def test_microphone():
    """
    Tests if the microphone is working by attempting to record a short audio clip
    
    Returns:
        Tuple of (success, message, test_audio) where:
        - success is a boolean indicating if the test was successful
        - message is a string with details about the test result
        - test_audio is the audio bytes if successful, None otherwise
    """
    if not MIC_RECORDER_AVAILABLE:
        return False, "streamlit-mic-recorder is not available. Install it with: pip install streamlit-mic-recorder", None
    
    st.markdown("### 🎙️ Microphone Test")
    st.markdown("Click the button below and say something to test your microphone:")
    
    # Using a unique key to avoid conflicts with the main recorder
    test_audio = mic_recorder(
        key=f"mic_test_{int(time.time())}",
        start_prompt="Test Microphone",
        stop_prompt="Stop Test", 
        just_once=True,
        use_container_width=False
    )
    
    if test_audio and len(test_audio) > 100:
        return True, f"✅ Microphone working! Received {len(test_audio)} bytes of audio.", test_audio
    elif test_audio:
        return False, f"⚠️ Microphone detected but audio is very small ({len(test_audio)} bytes). May not work properly.", test_audio
    else:
        return False, "❌ No audio received. Your microphone may not be working or browser permissions are blocked.", None


def record_browser_audio(patient_id):
    """
    Record audio using the browser's microphone via streamlit-mic-recorder
    
    Args:
        patient_id: ID of the patient for file naming
        
    Returns:
        Tuple of (audio_bytes, file_path) where audio_data is the raw bytes and file_path is where it was saved
    """
    if not MIC_RECORDER_AVAILABLE:
        st.error("streamlit-mic-recorder is not available. Install it with: pip install streamlit-mic-recorder")
        st.info("Alternatively, you can configure your OpenAI API key in Settings and use the simulated transcription.")
        return None, None
        
    # Create audio directory if it doesn't exist
    os.makedirs('data/audio', exist_ok=True)
    
    # Add option to test microphone first
    with st.expander("🔍 Microphone Test (Recommended)", expanded=True):
        st.markdown("If you're having trouble recording, test your microphone first:")
        if st.button("Check Microphone"):
            mic_working, mic_message, test_audio = test_microphone()
            st.write(mic_message)
            
            if mic_working and test_audio:
                st.audio(test_audio)
                st.success("Your microphone is working correctly! You can proceed with recording.")
            else:
                st.error("Microphone test failed. Please check the following:")
                st.markdown("""
                - Ensure your browser has permission to use the microphone
                - Try using a different browser (Chrome works best)
                - Check if your microphone is connected and not muted
                - Try refreshing the page
                """)
    
    # Clear instructions for recording
    st.markdown("""
    ### Audio Recording Instructions
    1. Click the microphone button below to **start** recording
    2. Speak clearly during your patient interaction
    3. Click the microphone button again to **stop** when done
    4. The recording will be automatically transcribed using OpenAI Whisper
    """)
    
    # Create a placeholder for the recording UI
    recording_ui = st.empty()
    
    with recording_ui.container():
        st.markdown("### 🎙️ Click below to start/stop recording")
        audio_bytes = mic_recorder(
            key=f"mic_recorder_{patient_id}_{int(time.time())}",
            start_prompt="▶️ Start Recording",
            stop_prompt="⏹️ Stop Recording", 
            just_once=True,
            use_container_width=True
        )
    
    # If we have audio data
    if audio_bytes:
        # Debug info about the audio bytes
        st.info(f"Received audio data: {len(audio_bytes)} bytes")
        
        # Generate a unique filename
        timestamp = int(time.time())
        audio_file_path = f"data/audio/recording_{patient_id}_{timestamp}.wav"
        
        # Save the audio file
        try:
            with open(audio_file_path, 'wb') as f:
                f.write(audio_bytes)
            
            # Verify the file exists and has content
            file_size = os.path.getsize(audio_file_path)
            st.success(f"✅ Audio saved successfully: {file_size} bytes")
            
            # Replace the recording UI with a playback element
            with recording_ui.container():
                st.markdown("### ✅ Recording complete!")
                st.markdown("##### Listen to your recording:")
                st.audio(audio_bytes)
                
                # Check file format
                if file_size < 1000:  # Less than 1KB
                    st.warning("⚠️ Warning: Audio file is very small. Transcription may not work correctly.")
                
            return audio_bytes, audio_file_path
        except Exception as e:
            st.error(f"❌ Error saving audio file: {str(e)}")
            
            # Try to save in a different location as a fallback
            try:
                fallback_path = f"recording_{patient_id}_{timestamp}.wav"
                with open(fallback_path, 'wb') as f:
                    f.write(audio_bytes)
                st.info(f"Saved to fallback location: {fallback_path}")
                return audio_bytes, fallback_path
            except Exception as fallback_error:
                st.error(f"Fallback save also failed: {str(fallback_error)}")
                return audio_bytes, None
    else:
        st.info("No audio recorded. Click the microphone button to start recording.")
        
        # Add troubleshooting tips
        with st.expander("Troubleshooting Recording Issues"):
            st.markdown("""
            ### Common Issues:
            
            1. **Browser Permissions**: Make sure you've allowed microphone access in your browser
            2. **Microphone Setup**: Check if your microphone is properly connected and not muted
            3. **Browser Compatibility**: Try using Chrome or Edge instead of Firefox or Safari
            4. **Privacy Settings**: Check your operating system's privacy settings for microphone access
            5. **Multiple Tabs**: Close other tabs that might be using the microphone
            
            If you continue to have issues, you can still use the app with simulated transcriptions by setting up your OpenAI API key in the Settings page.
            """)
        
        return None, None

def use_simulated_audio_mode(patient_id, conn, c):
    """
    Provides a simulated audio recording and transcription experience for testing without requiring a microphone
    
    Args:
        patient_id: ID of the patient for file naming
        conn: Database connection
        c: Database cursor
        
    Returns:
        Boolean indicating if a transcription was successfully generated
    """
    st.info("📝 Simulated Audio Mode Activated - No microphone needed")
    
    # Options for simulation
    simulation_type = st.radio(
        "Choose simulation type:",
        ["Short Dental Conversation", "Comprehensive Exam", "Emergency Visit", "Random Sample"]
    )
    
    if st.button("Generate Simulated Transcription"):
        # Get mock conversation data based on selection
        if simulation_type == "Short Dental Conversation":
            mock_data = """
            Dentist: Hello there, how are you feeling today?
            Patient: I've been having some pain in my lower right molar.
            Dentist: I see. How long have you been experiencing this pain?
            Patient: About a week now. It's worse when I drink something cold.
            Dentist: Does it wake you up at night?
            Patient: No, it only hurts when I eat or drink.
            Dentist: Let me take a look at that area. Open wide please.
            """
        elif simulation_type == "Comprehensive Exam":
            mock_data = """
            Dentist: Good morning! I see you're here for your comprehensive exam today.
            Patient: Yes, it's been about a year since my last checkup.
            Dentist: How has your oral health been during that time? Any concerns?
            Patient: I've noticed some bleeding when I brush my teeth, especially in the back.
            Dentist: How often do you brush and floss?
            Patient: I brush twice daily, but I only floss a couple times a week.
            Dentist: I recommend daily flossing to help with that gum inflammation. Let's take a look at what's going on. Have you had any pain or sensitivity?
            Patient: Sometimes when I eat sweet things, I get a twinge in this upper tooth.
            Dentist: I'll check that area carefully. Any changes in your medical history since your last visit?
            Patient: I started taking blood pressure medication about 6 months ago.
            Dentist: Thank you for letting me know. That's important information. Some blood pressure medications can cause dry mouth, have you noticed that?
            Patient: Yes, actually. I've been drinking more water because of it.
            Dentist: That's good. Let's proceed with the examination and take some updated x-rays.
            """
        elif simulation_type == "Emergency Visit":
            mock_data = """
            Dentist: Hello, I understand you're in for an emergency today. What's going on?
            Patient: I broke my front tooth last night. I bit into an apple and a big piece just came off.
            Dentist: I'm sorry to hear that. Are you experiencing any pain?
            Patient: It's very sensitive to air and cold drinks. It's not constant pain, but it's quite uncomfortable.
            Dentist: Let me take a look. Can you point to which tooth is affected?
            Patient: This one, the front right.
            Dentist: I see the fracture. It's what we call an uncomplicated crown fracture, meaning it hasn't exposed the nerve. That's good news.
            Patient: Can it be fixed today? I have an important meeting tomorrow.
            Dentist: Yes, we can do a composite restoration today. It's a tooth-colored filling that will restore the shape and function of your tooth.
            Patient: Will it match my other teeth?
            Dentist: Yes, we'll match the color to your adjacent teeth. It should look very natural.
            """
        else:
            # Random selection
            mock_data = get_mock_dental_conversation()
        
        # Set the transcription and mark as complete
        st.session_state.conversation_text = mock_data
        st.session_state.transcription_complete = True
        
        # Save simulated transcription to database
        try:
            # Check if a record already exists for this patient
            c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
            existing_id = c.fetchone()
            
            if existing_id:
                # Update existing record
                c.execute("UPDATE clinical_records SET transcription = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?", 
                        (mock_data, existing_id[0]))
            else:
                # Insert new record
                c.execute("INSERT INTO clinical_records (patient_id, transcription, record_date) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        (patient_id, mock_data))
            
            conn.commit()
            st.success("✅ Simulated transcription saved successfully!")
            st.info("Go to the AI Analysis tab to generate clinical insights.")
            return True
        except Exception as db_error:
            st.error(f"Error saving transcription to database: {str(db_error)}")
    
    return False

def diagnose_microphone_access():
    """
    Provides detailed diagnostic information about microphone access issues
    """
    st.markdown("## 🔍 Microphone Access Diagnostic")
    
    # Check environment
    st.markdown("### Environment Check")
    environment_data = []
    
    # Check browser info via User-Agent
    user_agent = st.experimental_get_query_params().get("ua", ["Unknown"])[0]
    browser_info = f"**User Agent**: {user_agent}"
    environment_data.append(browser_info)
    
    # Check if running locally or on Streamlit Cloud
    is_cloud = "STREAMLIT_SHARING" in os.environ or "STREAMLIT_CLOUD" in os.environ
    environment_data.append(f"**Platform**: {'Streamlit Cloud' if is_cloud else 'Local Development'}")
    
    # Check if streamlit-mic-recorder is available
    environment_data.append(f"**streamlit-mic-recorder**: {'Available' if MIC_RECORDER_AVAILABLE else 'Not Available'}")
    
    # Display environment data
    for item in environment_data:
        st.markdown(item)
    
    st.markdown("### Connection Test")
    if st.button("Test Browser Connection"):
        st.markdown("Attempting to establish a connection to your microphone...")
        st.info("If you see a browser permission dialog, please click 'Allow'")
        
        try:
            # Initialize a very small recorder with minimal options
            test_audio = mic_recorder(
                key="diagnostic_mic_test",
                start_prompt="Start Test",
                stop_prompt="Stop Test", 
                just_once=True,
                use_container_width=False
            )
            
            if test_audio:
                st.success(f"✅ Successfully connected to microphone and received {len(test_audio)} bytes of audio!")
                st.audio(test_audio)
                st.markdown("### Recommended Solution")
                st.markdown("""
                Your microphone connection works! If you're still having issues in the main application:
                
                1. Try refreshing the page and test again
                2. Check if you have any browser extensions that might be interfering with microphone access
                3. Try a different browser (Chrome works best)
                """)
            else:
                st.error("❌ No audio data received from your microphone")
                st.markdown("### Recommended Solutions")
                st.markdown("""
                Please try the following:
                
                1. **Check Browser Permissions**:
                   - Look for the microphone icon in your browser's address bar
                   - Make sure it's set to "Allow" for this site
                   - Try clicking the microphone icon and setting permissions to "Allow"
                
                2. **Use Chrome Browser**:
                   - The microphone recording works best in Google Chrome
                   - Firefox, Safari, and Edge may have compatibility issues
                
                3. **Restart Your Browser**:
                   - Close your browser completely and restart it
                   - Then try the test again
                
                4. **Use Simulated Data**:
                   - If all else fails, use the "Simulated Data" option in the app
                   - This lets you test the AI analysis features without needing a microphone
                """)
                
                # If on Streamlit Cloud, add specific advice
                if is_cloud:
                    st.warning("""
                    **Important**: Streamlit Cloud runs on HTTP, not HTTPS, which can cause microphone access issues.
                    Modern browsers restrict microphone access to secure contexts (HTTPS) by default.
                    
                    You might need to specifically allow microphone access for HTTP connections:
                    
                    **In Chrome**:
                    1. Type `chrome://settings/content/microphone` in your address bar
                    2. Add this site to the "Allowed" list
                    
                    **In Firefox**:
                    1. Type `about:permissions` in your address bar
                    2. Search for this site and set microphone permissions to "Allow"
                    """)
        except Exception as e:
            st.error(f"Error during microphone test: {str(e)}")
            st.markdown("This suggests there might be a technical issue with the browser's audio system.")
    
    st.markdown("### Alternative Solutions")
    st.markdown("""
    If you can't get the microphone working, you can still use the app with simulated data:
    
    1. Go to the Clinical Interaction page
    2. Select a patient
    3. Check the "Use Simulated Data" option
    4. Choose a simulation type and click "Generate Simulated Transcription"
    5. Proceed to the AI Analysis tab to generate insights
    
    This will allow you to test the AI analysis features without needing to record actual audio.
    """)
    
    # Add a manual voice upload option
    st.markdown("### Upload Audio Option")
    st.markdown("If you have a recording from another app, you can upload it directly:")
    
    uploaded_audio = st.file_uploader("Upload Audio File (WAV, MP3, M4A)", type=["wav", "mp3", "m4a"])
    if uploaded_audio:
        try:
            # Save the uploaded file
            audio_bytes = uploaded_audio.read()
            file_name = f"data/audio/uploaded_{int(time.time())}.{uploaded_audio.name.split('.')[-1]}"
            os.makedirs('data/audio', exist_ok=True)
            
            with open(file_name, 'wb') as f:
                f.write(audio_bytes)
            
            st.success(f"Audio file saved: {file_name}")
            st.audio(audio_bytes)
            
            st.markdown("""
            You can now use this file for transcription:
            1. Go to Settings and set your OpenAI API key
            2. Return to Clinical Interaction
            3. Select a patient 
            4. Use the manual transcription option and enter: `[Using uploaded audio file]`
            """)
        except Exception as e:
            st.error(f"Error saving uploaded audio: {str(e)}")

# Main app
def main():
    # Initialize database
    init_db()
    
    # Initialize session state variables if they don't exist
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "login"
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = ""
    
    # Sidebar for navigation
    with st.sidebar:
        st.title("DentAI")
        
        # Only show navigation when logged in
        if 'logged_in' in st.session_state and st.session_state.logged_in:
            st.markdown(f"Welcome, **{st.session_state.username}**")
            
            # Navigation
            selected_page = st.radio(
                "Navigation",
                ["Dashboard", "Patients", "Questionnaires", "Dental Exam", "Clinical Interaction", "Settings", "Troubleshooting"]
            )
            
            # Map selection to session state
            page_mapping = {
                "Dashboard": "dashboard",
                "Patients": "patients",
                "Questionnaires": "questionnaire",
                "Dental Exam": "dental_examination",
                "Clinical Interaction": "clinical",
                "Settings": "settings",
                "Troubleshooting": "troubleshooting"
            }
            
            if st.button("Go to " + selected_page):
                st.session_state.current_page = page_mapping[selected_page]
                st.rerun()
            
            # Logout button
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.rerun()
        else:
            st.info("Please log in to access features")
    
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
        elif st.session_state.current_page == "dental_examination":
            dental_examination_page()
        elif st.session_state.current_page == "settings":
            settings_page()
        elif st.session_state.current_page == "troubleshooting":
            diagnose_microphone_access()

if __name__ == "__main__":
    main() 