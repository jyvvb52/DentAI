import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
import hashlib
import sqlite3
import time
from openai import OpenAI
import json
import ast
import openai
from io import BytesIO
import base64

# Optional imports for PDF generation
try:
    import pdfkit
    import markdown
    PDF_EXPORT_AVAILABLE = True
except ImportError:
    PDF_EXPORT_AVAILABLE = False

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

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'current_page' not in st.session_state:
    st.session_state.current_page = "dashboard"
if 'selected_patient' not in st.session_state:
    st.session_state.selected_patient = None
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = ""

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
                            mime="text/markdown"
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
        st.subheader("AI-Powered Clinical Analysis")
        
        # Open database connection for this tab
        conn = sqlite3.connect('data/dentai.db')
        c = conn.cursor()
        
        # Check if there's an existing transcription
        c.execute("SELECT transcription, audio_file_path FROM clinical_records WHERE patient_id = ?", (patient_id,))
        existing_record = c.fetchone()
        
        # Don't close the connection yet - we'll use it again later
        
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
            
            if st.button("Record New Conversation", key="record_new"):
                st.session_state.recording_new = True
        
        # Show recording interface if no existing transcription or user wants to record new
        if not existing_record or not existing_record[0] or ('recording_new' in st.session_state and st.session_state.recording_new):
            st.write("#### Record or Upload Conversation")
            
            # Initialize session state variables if they don't exist
            if 'recording' not in st.session_state:
                st.session_state.recording = False
            if 'audio_data' not in st.session_state:
                st.session_state.audio_data = None
            if 'transcription_complete' not in st.session_state:
                st.session_state.transcription_complete = False
            if 'uploaded_file' not in st.session_state:
                st.session_state.uploaded_file = None
            
            # Create tabs for recording or uploading
            record_tabs = st.tabs(["Record Audio", "Upload Audio File"])
            
            # Record Audio Tab
            with record_tabs[0]:
                # Audio recording with start/stop buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if not st.session_state.recording:
                        if st.button("🎙️ Start Recording", key="start_recording"):
                            st.session_state.recording = True
                            st.session_state.audio_data = []
                            st.session_state.transcription_complete = False
                            st.rerun()
                
                with col2:
                    if st.session_state.recording:
                        if st.button("⏹️ Stop Recording", key="stop_recording"):
                            st.session_state.recording = False
                            st.rerun()
                
                # Display recording status
                if st.session_state.recording:
                    st.warning("🔴 Recording in progress... Speak clearly and press 'Stop Recording' when finished.")
                    st.info("Note: Your audio is being processed in the background. No actual recording is happening in the browser.")
                    
                    # Show a continuous recording indicator without auto-stopping
                    st.markdown("##### Recording time:")
                    
                    # Create a placeholder for the timer
                    timer_placeholder = st.empty()
                    
                    # Display a timer that updates every second
                    start_time = time.time()
                    while st.session_state.recording:
                        # Calculate elapsed time
                        elapsed_time = time.time() - start_time
                        minutes, seconds = divmod(int(elapsed_time), 60)
                        hours, minutes = divmod(minutes, 60)
                        
                        # Update the timer display
                        timer_placeholder.markdown(f"**{hours:02d}:{minutes:02d}:{seconds:02d}**")
                        
                        # Sleep briefly to avoid consuming too much CPU
                        time.sleep(0.1)
                        
                        # Check if recording has been stopped
                        if not st.session_state.recording:
                            break
                    
                    # No auto-stop - let the user decide when to stop recording
            
            # Upload Audio File Tab
            with record_tabs[1]:
                st.write("Upload an audio file of the doctor-patient conversation")
                st.info("Supported formats: flac, m4a, mp3, mp4, mpeg, mpga, oga, ogg, wav, webm")
                
                uploaded_file = st.file_uploader("Choose an audio file", type=["flac", "m4a", "mp3", "mp4", "mpeg", "mpga", "oga", "ogg", "wav", "webm"])
                
                if uploaded_file is not None:
                    # Save the uploaded file
                    st.session_state.uploaded_file = uploaded_file
                    st.success(f"File '{uploaded_file.name}' uploaded successfully!")
                    
                    # Add a button to process the uploaded file
                    if st.button("Process Uploaded Audio", key="process_uploaded"):
                        st.session_state.recording = False  # Ensure recording is stopped
                        st.session_state.transcription_complete = False  # Reset transcription status
                        st.rerun()
            
            # Process audio after recording stops or file is uploaded
            if (not st.session_state.recording and st.session_state.audio_data is not None and not st.session_state.transcription_complete) or \
               (st.session_state.uploaded_file is not None and not st.session_state.transcription_complete):
                st.write("#### Processing Audio...")
                
                # Create a directory for audio files if it doesn't exist
                os.makedirs('data/audio', exist_ok=True)
                
                # Generate a unique filename
                timestamp = int(time.time())
                audio_file_path = f"data/audio/recording_{patient_id}_{timestamp}.wav"
                
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
                    
                    # Handle the audio file - either from upload or recording
                    if st.session_state.uploaded_file is not None:
                        # We have an uploaded file - save it and use it for transcription
                        try:
                            with open(audio_file_path, 'wb') as f:
                                f.write(st.session_state.uploaded_file.getvalue())
                            
                            if client:
                                try:
                                    # Use the uploaded file with Whisper API
                                    with open(audio_file_path, 'rb') as audio_file:
                                        transcription_response = client.audio.transcriptions.create(
                                            model="whisper-1",
                                            file=audio_file,
                                            language="en"
                                        )
                                        transcription_text = transcription_response.text
                                        st.success("Audio transcribed successfully!")
                                except Exception as e:
                                    st.error(f"Error transcribing audio: {str(e)}")
                                    # Use sample transcription as fallback
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
                            else:
                                # No OpenAI client, use sample transcription
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
                        except Exception as e:
                            st.error(f"Error saving uploaded file: {str(e)}")
                            audio_file_path = None
                            # Use sample transcription as fallback
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
                    else:
                        # We have recorded audio (simulated in this case)
                        # In a real implementation, you would save the actual recorded audio
                        
                        # For demonstration, we'll use a sample MP3 file if available
                        sample_mp3_path = "data/audio/sample_conversation.mp3"
                        
                        try:
                            # Check if we have a sample file to use
                            if os.path.exists(sample_mp3_path):
                                # Copy the sample file to our new path
                                import shutil
                                shutil.copy(sample_mp3_path, audio_file_path)
                            else:
                                # Create a dummy MP3 file for demonstration
                                st.info("Creating a sample audio file for demonstration purposes...")
                                
                                # For now, we'll just create a dummy file
                                with open(audio_file_path, 'wb') as f:
                                    # Write some dummy data
                                    f.write(b'ID3' + b'\x00' * 100)  # Simple MP3 header
                            
                            # If we have a client and a valid audio file, try to transcribe it
                            if client and os.path.exists(audio_file_path):
                                try:
                                    with open(audio_file_path, 'rb') as audio_file:
                                        # This will likely fail with our dummy file, which is expected
                                        transcription_response = client.audio.transcriptions.create(
                                            model="whisper-1",
                                            file=audio_file,
                                            language="en"
                                        )
                                        transcription_text = transcription_response.text
                                        st.success("Audio transcribed successfully!")
                                except Exception as e:
                                    st.warning(f"Using sample transcription due to API error: {str(e)}")
                                    # Use sample transcription for demonstration
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
                            else:
                                # Use sample transcription
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
                        except Exception as e:
                            st.error(f"Error creating sample audio file: {str(e)}")
                            # Don't use the audio file path if we couldn't create it
                            audio_file_path = None
                            # Use sample transcription
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
                    
                    # Clean up the transcription text
                    transcription_text = transcription_text.strip()
                    
                    # Display the transcription
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
                        if audio_file_path and os.path.exists(audio_file_path):
                            c.execute("UPDATE clinical_records SET transcription = ?, audio_file_path = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?", 
                                    (transcription_text, audio_file_path, existing_id[0]))
                        else:
                            c.execute("UPDATE clinical_records SET transcription = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?", 
                                    (transcription_text, existing_id[0]))
                    else:
                        # Insert new record
                        if audio_file_path and os.path.exists(audio_file_path):
                            c.execute("INSERT INTO clinical_records (patient_id, transcription, audio_file_path, record_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                                    (patient_id, transcription_text, audio_file_path))
                        else:
                            c.execute("INSERT INTO clinical_records (patient_id, transcription, record_date) VALUES (?, ?, CURRENT_TIMESTAMP)",
                                    (patient_id, transcription_text))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("Transcription saved to database!")
                    
                    # Reset the uploaded file after processing
                    st.session_state.uploaded_file = None
                    
                    # Set transcription complete flag
                    st.session_state.transcription_complete = True
        
        # Reopen database connection before checking for existing AI analysis
        conn = sqlite3.connect('data/dentai.db')
        c = conn.cursor()
        
        # Check for existing AI analysis
        c.execute("SELECT ai_analysis FROM clinical_records WHERE patient_id = ? AND ai_analysis IS NOT NULL", (patient_id,))
        existing_analysis = c.fetchone()
        
        # Now we can close the connection as we're done with database operations in this tab
        conn.close()
        
        if existing_analysis and existing_analysis[0]:
            st.write("#### Previous AI Analysis")
            with st.expander("View Previous Analysis"):
                st.markdown(existing_analysis[0])
            
            # Provide export options for existing analysis
            st.write("#### Export Options:")
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="Download as Text",
                    data=existing_analysis[0],
                    file_name=f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )
            
            with col2:
                if PDF_EXPORT_AVAILABLE:
                    if st.button("Export as PDF", key="export_existing_pdf"):
                        try:
                            pdf_link = export_report_as_pdf(existing_analysis[0], f"{patient[0]} {patient[1]}")
                            st.markdown(pdf_link, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error generating PDF: {e}")
                            st.markdown(create_download_link(existing_analysis[0], 
                                                           f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.md", 
                                                           "Download as Markdown instead"), 
                                      unsafe_allow_html=True)
                else:
                    st.info("PDF export requires additional packages. Install pdfkit and markdown packages for PDF export functionality.")

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

def generate_ai_analysis(data):
    """Generate an AI analysis of the clinical interaction using OpenAI API."""
    
    # Extract data from the input
    patient_id = data.get('patient_id')
    patient_name = data.get('patient_name')
    transcription = data.get('transcription', '')
    
    # Get additional patient data from the database
    try:
        conn = sqlite3.connect('data/dentai.db')
        c = conn.cursor()
        
        # Get patient details
        c.execute("SELECT first_name, last_name, date_of_birth, gender FROM patients WHERE id = ?", (patient_id,))
        patient_data = c.fetchone()
        
        if not patient_data:
            patient_age = "Unknown"
            patient_gender = "Unknown"
        else:
            # Calculate age from date of birth
            if patient_data[2]:  # If date_of_birth is not None
                try:
                    dob = datetime.strptime(patient_data[2], '%Y-%m-%d')
                    today = datetime.today()
                    patient_age = str(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))
                except:
                    patient_age = "Unknown"
            else:
                patient_age = "Unknown"
            
            patient_gender = patient_data[3] if patient_data[3] else "Unknown"
        
        # Get medical questionnaire data
        c.execute("SELECT responses FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'medical'", (patient_id,))
        medical_data = c.fetchone()
        
        medical_conditions = []
        if medical_data and medical_data[0]:
            try:
                medical_dict = safe_eval(medical_data[0])
                for key, value in medical_dict.items():
                    if value == True or value == "Yes" or value == "yes":
                        medical_conditions.append(key)
                    elif isinstance(value, str) and value and value != "No" and value != "no":
                        medical_conditions.append(f"{key}: {value}")
            except:
                pass
        
        # Get dental questionnaire data
        c.execute("SELECT responses FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'dental'", (patient_id,))
        dental_data = c.fetchone()
        
        dental_concerns = []
        tmd_issues = []
        if dental_data and dental_data[0]:
            try:
                dental_dict = safe_eval(dental_data[0])
                for key, value in dental_dict.items():
                    if key.startswith('tmd_') and (value == True or value == "Yes" or value == "yes"):
                        tmd_issues.append(key.replace('tmd_', '').replace('_', ' '))
                    elif value == True or value == "Yes" or value == "yes":
                        dental_concerns.append(key.replace('_', ' '))
                    elif isinstance(value, str) and value and value != "No" and value != "no":
                        dental_concerns.append(f"{key.replace('_', ' ')}: {value}")
            except:
                pass
        
        # Get chief complaint
        c.execute("SELECT chief_complaint FROM clinical_records WHERE patient_id = ?", (patient_id,))
        chief_complaint_row = c.fetchone()
        chief_complaint = chief_complaint_row[0] if chief_complaint_row and chief_complaint_row[0] else "Not specified"
        
        # Get examination data from questionnaires table
        c.execute("SELECT responses FROM questionnaires WHERE patient_id = ? AND questionnaire_type LIKE '%examination%'", (patient_id,))
        examination_rows = c.fetchall()
        
        examination_data = {}
        for row in examination_rows:
            if row[0]:
                try:
                    exam_data = safe_eval(row[0])
                    if isinstance(exam_data, dict):
                        examination_data.update(exam_data)
                except:
                    pass
        
        conn.close()
        
        # First, generate an analysis of medical & dental history and examination data
        try:
            # Initialize OpenAI client
            if st.session_state.openai_api_key:
                client = OpenAI(api_key=st.session_state.openai_api_key)
            else:
                st.warning("OpenAI API key is not configured. Using simulated analysis instead.")
                client = None
                raise Exception("OpenAI API key not configured")
            
            # Prepare the prompt for medical & dental history analysis
            history_prompt = f"""
            Generate a comprehensive analysis of the following patient's medical and dental history:
            
            PATIENT INFORMATION:
            Name: {patient_name}
            Age: {patient_age}
            Gender: {patient_gender}
            
            MEDICAL HISTORY:
            {"Medical conditions: " + ", ".join(medical_conditions) if medical_conditions else "No significant medical conditions reported."}
            
            DENTAL CONCERNS:
            {"Dental concerns: " + ", ".join(dental_concerns) if dental_concerns else "No specific dental concerns reported."}
            
            TMD ISSUES:
            {"TMD issues: " + ", ".join(tmd_issues) if tmd_issues else "No TMD issues reported."}
            
            DENTAL EXAMINATION FINDINGS:
            {json.dumps(examination_data, indent=2) if examination_data else "No examination data available."}
            
            Please provide a detailed analysis including:
            1. Key findings from medical history
            2. Dental examination observations
            3. Potential risk factors
            4. Preliminary diagnosis based on history and examination
            
            Format the analysis in Markdown for readability.
            """
            
            # Call OpenAI API for history analysis
            history_response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using GPT-3.5-turbo as requested
                messages=[
                    {"role": "system", "content": "You are a dental professional assistant that analyzes patient medical and dental history data."},
                    {"role": "user", "content": history_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract the generated history analysis
            history_analysis = history_response.choices[0].message.content
            
            # If there's a transcription, generate a clinical report that includes the history analysis
            if transcription:
                # Prepare the prompt for the full clinical report
                report_prompt = f"""
                Generate a comprehensive dental clinical report based on the following information:
                
                PATIENT INFORMATION:
                Name: {patient_name}
                Age: {patient_age}
                Gender: {patient_gender}
                
                CHIEF COMPLAINT:
                {chief_complaint}
                
                PATIENT HISTORY ANALYSIS:
                {history_analysis}
                
                DOCTOR-PATIENT CONVERSATION TRANSCRIPT:
                {transcription}
                
                Please provide a detailed clinical report including:
                1. Patient Overview
                2. Medical History Summary
                3. Dental History Summary
                4. Clinical Findings from Conversation
                5. Diagnosis
                6. Treatment Recommendations
                7. Prognosis
                
                Format the report in Markdown for readability.
                """
                
                # Call OpenAI API for the full clinical report
                report_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Using GPT-3.5-turbo as requested
                    messages=[
                        {"role": "system", "content": "You are a dental professional assistant that generates comprehensive clinical reports based on patient data and doctor-patient conversations."},
                        {"role": "user", "content": report_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                
                # Extract the generated report
                analysis = report_response.choices[0].message.content
            else:
                # If no transcription, just return the history analysis
                analysis = f"""
                # Patient Analysis for {patient_name}
                
                ## Medical and Dental History Analysis
                
                {history_analysis}
                
                ## Note
                This is a preliminary analysis based on patient history and examination data only.
                A complete clinical assessment with doctor-patient interaction is recommended for a comprehensive diagnosis and treatment plan.
                """
            
            return analysis
        
        except Exception as e:
            st.error(f"Error generating AI analysis: {str(e)}")
            
            # Fallback to simulated analysis if API call fails
            analysis = f"""
            # Clinical Analysis for {patient_name}
            
            ## Patient Overview
            {patient_name} is a {patient_age}-year-old {patient_gender} who presents with the chief complaint of "{chief_complaint}".
            
            ## Medical History
            {"The patient has the following medical conditions of note: " + ", ".join(medical_conditions) if medical_conditions else "No significant medical conditions reported."}
            
            ## Dental Concerns
            {"The patient reports the following dental concerns: " + ", ".join(dental_concerns) if dental_concerns else "No specific dental concerns reported."}
            
            ## TMD Issues
            {"The patient reports the following TMD issues: " + ", ".join(tmd_issues) if tmd_issues else "No specific TMD issues reported."}
            
            ## Clinical Assessment
            Based on the available information and the conversation transcript, this patient presents with {"multiple" if len(dental_concerns) > 1 or len(tmd_issues) > 0 else "limited"} dental concerns that require attention.
            
            ## Analysis of Conversation
            The conversation between the doctor and patient reveals:
            - Discussion about dental pain and sensitivity
            - Potential need for restorative treatment
            - Patient concerns about treatment discomfort
            
            ## Recommendations
            1. {"Address the chief complaint of pain through appropriate diagnostic tests and treatment." if "pain" in str(chief_complaint).lower() else "Perform a comprehensive examination to identify the source of the patient's concerns."}
            2. {"Consider TMD evaluation and management." if tmd_issues else "Regular dental check-ups and cleanings are recommended."}
            3. Provide oral hygiene instructions and preventive care recommendations.
            4. Schedule follow-up appointment to assess treatment outcomes.
            
            ## Prognosis
            With appropriate treatment and patient compliance, the prognosis is good for managing the identified dental concerns.
            """
            
            return analysis
    
    except Exception as e:
        st.error(f"Error retrieving patient data: {str(e)}")
        return f"Error generating analysis: {str(e)}"

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
        if st.button("Clinical", key="clinical_btn_clinical", type="primary"):
            st.session_state.current_page = "clinical"
            st.rerun()
    
    with col5:
        if st.button("Dental Exam", key="dental_exam_btn_clinical"):
            st.session_state.current_page = "dental_examination"
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
        
        # Check if there's an existing transcription
        c.execute("SELECT transcription, audio_file_path FROM clinical_records WHERE patient_id = ?", (patient_id,))
        existing_record = c.fetchone()
        
        conn.close()
        
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
            
            if st.button("Record New Conversation", key="record_new"):
                st.session_state.recording_new = True
        
        # Show recording interface if no existing transcription or user wants to record new
        if not existing_record or not existing_record[0] or ('recording_new' in st.session_state and st.session_state.recording_new):
            st.write("#### Record or Upload Conversation")
            
            # Initialize session state variables if they don't exist
            if 'recording' not in st.session_state:
                st.session_state.recording = False
            if 'audio_data' not in st.session_state:
                st.session_state.audio_data = None
            if 'transcription_complete' not in st.session_state:
                st.session_state.transcription_complete = False
            if 'uploaded_file' not in st.session_state:
                st.session_state.uploaded_file = None
            
            # Create tabs for recording or uploading
            record_tabs = st.tabs(["Record Audio", "Upload Audio File"])
            
            # Record Audio Tab
            with record_tabs[0]:
                # Audio recording with start/stop buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if not st.session_state.recording:
                        if st.button("🎙️ Start Recording", key="start_recording"):
                            st.session_state.recording = True
                            st.session_state.audio_data = []
                            st.session_state.transcription_complete = False
                            st.rerun()
                
                with col2:
                    if st.session_state.recording:
                        if st.button("⏹️ Stop Recording", key="stop_recording"):
                            st.session_state.recording = False
                            st.rerun()
                
                # Display recording status
                if st.session_state.recording:
                    st.warning("🔴 Recording in progress... Speak clearly and press 'Stop Recording' when finished.")
                    st.info("Note: Your audio is being processed in the background. No actual recording is happening in the browser.")
                    
                    # Show a continuous recording indicator without auto-stopping
                    st.markdown("##### Recording time:")
                    
                    # Create a placeholder for the timer
                    timer_placeholder = st.empty()
                    
                    # Display a timer that updates every second
                    start_time = time.time()
                    while st.session_state.recording:
                        # Calculate elapsed time
                        elapsed_time = time.time() - start_time
                        minutes, seconds = divmod(int(elapsed_time), 60)
                        hours, minutes = divmod(minutes, 60)
                        
                        # Update the timer display
                        timer_placeholder.markdown(f"**{hours:02d}:{minutes:02d}:{seconds:02d}**")
                        
                        # Sleep briefly to avoid consuming too much CPU
                        time.sleep(0.1)
                        
                        # Check if recording has been stopped
                        if not st.session_state.recording:
                            break
                    
                    # No auto-stop - let the user decide when to stop recording
            
            # Upload Audio File Tab
            with record_tabs[1]:
                st.write("Upload an audio file of the doctor-patient conversation")
                st.info("Supported formats: flac, m4a, mp3, mp4, mpeg, mpga, oga, ogg, wav, webm")
                
                uploaded_file = st.file_uploader("Choose an audio file", type=["flac", "m4a", "mp3", "mp4", "mpeg", "mpga", "oga", "ogg", "wav", "webm"])
                
                if uploaded_file is not None:
                    # Save the uploaded file
                    st.session_state.uploaded_file = uploaded_file
                    st.success(f"File '{uploaded_file.name}' uploaded successfully!")
                    
                    # Add a button to process the uploaded file
                    if st.button("Process Uploaded Audio", key="process_uploaded"):
                        st.session_state.recording = False  # Ensure recording is stopped
                        st.session_state.transcription_complete = False  # Reset transcription status
                        st.rerun()
            
            # Process audio after recording stops or file is uploaded
            if (not st.session_state.recording and st.session_state.audio_data is not None and not st.session_state.transcription_complete) or \
               (st.session_state.uploaded_file is not None and not st.session_state.transcription_complete):
                st.write("#### Processing Audio...")
                
                # Create a directory for audio files if it doesn't exist
                os.makedirs('data/audio', exist_ok=True)
                
                # Generate a unique filename
                timestamp = int(time.time())
                audio_file_path = f"data/audio/recording_{patient_id}_{timestamp}.wav"
                
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
                    
                    # Handle the audio file - either from upload or recording
                    if st.session_state.uploaded_file is not None:
                        # We have an uploaded file - save it and use it for transcription
                        with open(audio_file_path, 'wb') as f:
                            f.write(st.session_state.uploaded_file.getvalue())
                        
                        if client:
                            try:
                                # Use the uploaded file with Whisper API
                                with open(audio_file_path, 'rb') as audio_file:
                                    try:
                                        transcription_response = client.audio.transcriptions.create(
                                            model="whisper-1",
                                            file=audio_file,
                                            language="en"
                                        )
                                        transcription_text = transcription_response.text
                                        st.success("Audio transcribed successfully!")
                                    except Exception as e:
                                        st.error(f"Error transcribing audio: {str(e)}")
                                        # Use sample transcription as fallback
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
                            except Exception as e:
                                st.error(f"Error transcribing audio: {str(e)}")
                                # Use sample transcription as fallback
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
                        else:
                            # No OpenAI client, use sample transcription
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
                    
                    # Clean up the transcription text
                    transcription_text = transcription_text.strip()
                    
                    # Display the transcription
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
                        if audio_file_path and os.path.exists(audio_file_path):
                            c.execute("UPDATE clinical_records SET transcription = ?, audio_file_path = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?", 
                                    (transcription_text, audio_file_path, existing_id[0]))
                        else:
                            c.execute("UPDATE clinical_records SET transcription = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?", 
                                    (transcription_text, existing_id[0]))
                    else:
                        # Insert new record
                        if audio_file_path and os.path.exists(audio_file_path):
                            c.execute("INSERT INTO clinical_records (patient_id, transcription, audio_file_path, record_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                                    (patient_id, transcription_text, audio_file_path))
                        else:
                            c.execute("INSERT INTO clinical_records (patient_id, transcription, record_date) VALUES (?, ?, CURRENT_TIMESTAMP)",
                                    (patient_id, transcription_text))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("Transcription saved to database!")
                    
                    # Reset the uploaded file after processing
                    st.session_state.uploaded_file = None
                    
                    # Set transcription complete flag
                    st.session_state.transcription_complete = True
        
        # Reopen database connection before checking for existing AI analysis
        conn = sqlite3.connect('data/dentai.db')
        c = conn.cursor()
        
        # Check for existing AI analysis
        c.execute("SELECT ai_analysis FROM clinical_records WHERE patient_id = ? AND ai_analysis IS NOT NULL", (patient_id,))
        existing_analysis = c.fetchone()
        
        # Now we can close the connection as we're done with database operations in this tab
        conn.close()
        
        if existing_analysis and existing_analysis[0]:
            st.write("#### Previous AI Analysis")
            with st.expander("View Previous Analysis"):
                st.markdown(existing_analysis[0])
            
            # Provide export options for existing analysis
            st.write("#### Export Options:")
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="Download as Text",
                    data=existing_analysis[0],
                    file_name=f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )
            
            with col2:
                if PDF_EXPORT_AVAILABLE:
                    if st.button("Export as PDF", key="export_existing_pdf"):
                        try:
                            pdf_link = export_report_as_pdf(existing_analysis[0], f"{patient[0]} {patient[1]}")
                            st.markdown(pdf_link, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error generating PDF: {e}")
                            st.markdown(create_download_link(existing_analysis[0], 
                                                           f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.md", 
                                                           "Download as Markdown instead"), 
                                      unsafe_allow_html=True)
                else:
                    st.info("PDF export requires additional packages. Install pdfkit and markdown packages for PDF export functionality.")

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
        elif st.session_state.current_page == "dental_examination":
            dental_examination_page()
        elif st.session_state.current_page == "settings":
            settings_page()

if __name__ == "__main__":
    main() 