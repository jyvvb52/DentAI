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
        
        if st.button("Dental Examination", key="pat_exam_btn"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
        
        if st.button("Logout", key="pat_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
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
    st.title("DentAI - Medical & Dental Questionnaire")
    
    # Add back navigation buttons at the top
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Patients", key="quest_back_btn"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    # Sidebar navigation
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}!")
        
        if st.button("Dashboard", key="quest_dash_btn"):
            st.session_state.current_page = "dashboard"
            st.rerun()
        
        if st.button("Patient Management", key="quest_patient_btn"):
            st.session_state.current_page = "patients"
            st.rerun()
        
        if st.button("Dental Examination", key="quest_exam_btn"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
        
        if st.button("Clinical Interaction", key="quest_clinical_btn"):
            st.session_state.current_page = "clinical"
            st.rerun()
        
        if st.button("Logout", key="quest_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
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
    tabs = st.tabs(["Medical History", "Dental History", "Allergies", "Medications", "Lifestyle", "Women's Health"])
    
    # Medical History Tab
    with tabs[0]:
        st.subheader("Medical History")
        
        with st.form("medical_history_form"):
            # General health
            st.write("### General Health")
            general_health = st.selectbox("How would you rate your general health?", 
                                         ["Excellent", "Good", "Fair", "Poor"])
            
            # Medical conditions
            st.write("### Medical Conditions")
            st.write("Do you have or have you ever had any of the following conditions?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                heart_disease = st.checkbox("Heart Disease")
                high_blood_pressure = st.checkbox("High Blood Pressure")
                diabetes = st.checkbox("Diabetes")
                asthma = st.checkbox("Asthma")
                epilepsy = st.checkbox("Epilepsy")
                cancer = st.checkbox("Cancer")
                arthritis = st.checkbox("Arthritis")
            
            with col2:
                kidney_disease = st.checkbox("Kidney Disease")
                liver_disease = st.checkbox("Liver Disease")
                thyroid_disorder = st.checkbox("Thyroid Disorder")
                stroke = st.checkbox("Stroke")
                mental_health_disorder = st.checkbox("Mental Health Disorder")
                blood_disorder = st.checkbox("Blood Disorder")
                other_condition = st.checkbox("Other")
            
            if other_condition:
                other_condition_details = st.text_area("Please specify other medical conditions")
            else:
                other_condition_details = ""
            
            # Hospitalizations
            st.write("### Hospitalizations and Surgeries")
            hospitalizations = st.checkbox("Have you been hospitalized or had any surgeries in the past 5 years?")
            if hospitalizations:
                hospitalization_details = st.text_area("Please provide details about hospitalizations or surgeries")
            else:
                hospitalization_details = ""
            
            # Physician information
            st.write("### Physician Information")
            physician_name = st.text_input("Primary care physician's name")
            physician_phone = st.text_input("Physician's phone number")
            last_physical = st.date_input("Date of last physical examination", value=None)
            
            # Submit button
            submitted = st.form_submit_button("Save Medical History")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "general_health": general_health,
                    "medical_conditions": {
                        "heart_disease": heart_disease,
                        "high_blood_pressure": high_blood_pressure,
                        "diabetes": diabetes,
                        "asthma": asthma,
                        "epilepsy": epilepsy,
                        "cancer": cancer,
                        "arthritis": arthritis,
                        "kidney_disease": kidney_disease,
                        "liver_disease": liver_disease,
                        "thyroid_disorder": thyroid_disorder,
                        "stroke": stroke,
                        "mental_health_disorder": mental_health_disorder,
                        "blood_disorder": blood_disorder,
                        "other": other_condition,
                        "other_details": other_condition_details
                    },
                    "hospitalizations": {
                        "has_hospitalizations": hospitalizations,
                        "details": hospitalization_details
                    },
                    "physician": {
                        "name": physician_name,
                        "phone": physician_phone,
                        "last_physical": str(last_physical) if last_physical else ""
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'medical'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses) VALUES (?, ?, ?)",
                            (patient_id, "medical", str(responses).replace("'", "''"))
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
            # Previous dental care
            st.write("### Previous Dental Care")
            last_dental_visit = st.selectbox("When was your last dental visit?", 
                                            ["Within 6 months", "6-12 months ago", "1-2 years ago", "2+ years ago", "Never"])
            
            reason_for_visit = st.text_area("Reason for your last dental visit")
            
            # Dental habits
            st.write("### Dental Habits")
            brushing_frequency = st.selectbox("How often do you brush your teeth?", 
                                             ["Twice or more daily", "Once daily", "Few times a week", "Rarely"])
            
            flossing_frequency = st.selectbox("How often do you floss?", 
                                             ["Daily", "Few times a week", "Occasionally", "Rarely", "Never"])
            
            # Dental concerns
            st.write("### Dental Concerns")
            st.write("Are you currently experiencing any of the following?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                tooth_pain = st.checkbox("Tooth Pain")
                sensitivity = st.checkbox("Sensitivity to hot/cold")
                bleeding_gums = st.checkbox("Bleeding Gums")
                bad_breath = st.checkbox("Bad Breath")
            
            with col2:
                grinding_teeth = st.checkbox("Grinding/Clenching Teeth")
                dry_mouth = st.checkbox("Dry Mouth")
                jaw_pain = st.checkbox("Jaw Pain")
                clicking_jaw = st.checkbox("Clicking/Popping Jaw")
            
            dental_concerns_other = st.text_area("Other dental concerns")
            
            # TMD (Temporomandibular Disorders) section
            st.write("### TMD Assessment")
            st.write("Please answer the following questions about jaw joint issues:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                jaw_noises = st.checkbox("Are you aware of noises in the jaw joints?")
                jaw_stiffness = st.checkbox("Do your jaws/neck regularly feel stiff, tight, or tired?")
                facial_pain = st.checkbox("Do you have pain in or about the ears, temples, cheeks, or other parts of the face?")
                headaches = st.checkbox("Do you have frequent headaches and/or neckaches?")
                previous_tmd_treatment = st.checkbox("Have you previously been treated for a jaw joint, TMJ, or TMD problem?")
            
            with col2:
                swallowing_difficulty = st.checkbox("Do you have difficulty swallowing?")
                daytime_clenching = st.checkbox("Are you aware of clenching your teeth during the day?")
                sleep_grinding = st.checkbox("Have you been told that you grind your teeth when asleep?")
                opening_difficulty = st.checkbox("Do you have difficulty opening your mouth wide?")
            
            if previous_tmd_treatment:
                tmd_treatment_details = st.text_area("Please describe previous TMD treatments (biteguard, splint, surgery, medication, etc.)")
            else:
                tmd_treatment_details = ""
            
            # Previous dental treatments
            st.write("### Previous Dental Treatments")
            st.write("Have you had any of the following dental treatments?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fillings = st.checkbox("Fillings")
                crowns = st.checkbox("Crowns/Bridges")
                root_canal = st.checkbox("Root Canal")
                extractions = st.checkbox("Extractions")
            
            with col2:
                dentures = st.checkbox("Dentures/Partials")
                implants = st.checkbox("Dental Implants")
                orthodontics = st.checkbox("Orthodontics (Braces/Aligners)")
                periodontal = st.checkbox("Periodontal (Gum) Treatment")
            
            # Cosmetic concerns
            st.write("### Cosmetic Concerns")
            st.write("Are you interested in improving any of the following?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                teeth_whitening = st.checkbox("Teeth Whitening")
                straightening = st.checkbox("Teeth Straightening")
            
            with col2:
                replace_missing = st.checkbox("Replacing Missing Teeth")
                smile_appearance = st.checkbox("Overall Smile Appearance")
            
            # Dental anxiety
            st.write("### Dental Anxiety")
            dental_anxiety = st.slider("On a scale of 1-10, how anxious are you about dental treatment?", 1, 10, 1)
            
            # Submit button
            submitted = st.form_submit_button("Save Dental History")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "previous_care": {
                        "last_visit": last_dental_visit,
                        "reason": reason_for_visit
                    },
                    "dental_habits": {
                        "brushing": brushing_frequency,
                        "flossing": flossing_frequency
                    },
                    "dental_concerns": {
                        "tooth_pain": tooth_pain,
                        "sensitivity": sensitivity,
                        "bleeding_gums": bleeding_gums,
                        "bad_breath": bad_breath,
                        "grinding_teeth": grinding_teeth,
                        "dry_mouth": dry_mouth,
                        "jaw_pain": jaw_pain,
                        "clicking_jaw": clicking_jaw,
                        "other": dental_concerns_other
                    },
                    "tmd_assessment": {
                        "jaw_noises": jaw_noises,
                        "jaw_stiffness": jaw_stiffness,
                        "facial_pain": facial_pain,
                        "headaches": headaches,
                        "previous_tmd_treatment": previous_tmd_treatment,
                        "treatment_details": tmd_treatment_details if previous_tmd_treatment else "",
                        "swallowing_difficulty": swallowing_difficulty,
                        "daytime_clenching": daytime_clenching,
                        "sleep_grinding": sleep_grinding,
                        "opening_difficulty": opening_difficulty
                    },
                    "previous_treatments": {
                        "fillings": fillings,
                        "crowns": crowns,
                        "root_canal": root_canal,
                        "extractions": extractions,
                        "dentures": dentures,
                        "implants": implants,
                        "orthodontics": orthodontics,
                        "periodontal": periodontal
                    },
                    "cosmetic_concerns": {
                        "whitening": teeth_whitening,
                        "straightening": straightening,
                        "replace_missing": replace_missing,
                        "smile_appearance": smile_appearance
                    },
                    "anxiety_level": dental_anxiety
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'dental'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses) VALUES (?, ?, ?)",
                            (patient_id, "dental", str(responses).replace("'", "''"))
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
            # Medication allergies
            st.write("### Medication Allergies")
            medication_allergies = st.checkbox("Do you have any medication allergies?")
            if medication_allergies:
                medication_allergies_list = st.text_area("Please list all medication allergies and reactions")
            else:
                medication_allergies_list = ""
            
            # Dental material allergies
            st.write("### Dental Material Allergies")
            dental_allergies = st.checkbox("Do you have any allergies to dental materials?")
            
            if dental_allergies:
                col1, col2 = st.columns(2)
                
                with col1:
                    latex_allergy = st.checkbox("Latex")
                    metals_allergy = st.checkbox("Metals (e.g., nickel)")
                
                with col2:
                    acrylics_allergy = st.checkbox("Acrylics")
                    local_anesthetic_allergy = st.checkbox("Local Anesthetics")
                
                other_dental_allergies = st.text_area("Other dental material allergies")
            else:
                latex_allergy = False
                metals_allergy = False
                acrylics_allergy = False
                local_anesthetic_allergy = False
                other_dental_allergies = ""
            
            # Food and environmental allergies
            st.write("### Food and Environmental Allergies")
            food_env_allergies = st.checkbox("Do you have any food or environmental allergies?")
            if food_env_allergies:
                food_env_allergies_list = st.text_area("Please list all food and environmental allergies")
            else:
                food_env_allergies_list = ""
            
            # Allergy symptoms
            st.write("### Allergy Symptoms")
            st.write("What symptoms do you typically experience during an allergic reaction?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                rash = st.checkbox("Rash/Hives")
                swelling = st.checkbox("Swelling")
                itching = st.checkbox("Itching")
            
            with col2:
                breathing_difficulty = st.checkbox("Difficulty Breathing")
                anaphylaxis = st.checkbox("Anaphylaxis")
                other_symptoms = st.checkbox("Other Symptoms")
            
            if other_symptoms:
                other_symptoms_details = st.text_area("Please describe other allergy symptoms")
            else:
                other_symptoms_details = ""
            
            # Emergency treatment
            st.write("### Emergency Treatment")
            epipen = st.checkbox("Do you carry an EpiPen or other emergency allergy medication?")
            
            # Submit button
            submitted = st.form_submit_button("Save Allergies Information")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "medication_allergies": {
                        "has_allergies": medication_allergies,
                        "details": medication_allergies_list
                    },
                    "dental_material_allergies": {
                        "has_allergies": dental_allergies,
                        "latex": latex_allergy,
                        "metals": metals_allergy,
                        "acrylics": acrylics_allergy,
                        "local_anesthetic": local_anesthetic_allergy,
                        "other": other_dental_allergies
                    },
                    "food_env_allergies": {
                        "has_allergies": food_env_allergies,
                        "details": food_env_allergies_list
                    },
                    "allergy_symptoms": {
                        "rash": rash,
                        "swelling": swelling,
                        "itching": itching,
                        "breathing_difficulty": breathing_difficulty,
                        "anaphylaxis": anaphylaxis,
                        "other": other_symptoms,
                        "other_details": other_symptoms_details
                    },
                    "emergency_treatment": {
                        "epipen": epipen
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'allergies'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses) VALUES (?, ?, ?)",
                            (patient_id, "allergies", str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Allergies information saved successfully!")
                except Exception as e:
                    st.error(f"Error saving allergies information: {str(e)}")
    
    # Medications Tab
    with tabs[3]:
        st.subheader("Medications")
        
        with st.form("medications_form"):
            # Current medications
            st.write("### Current Medications")
            taking_medications = st.checkbox("Are you currently taking any medications?")
            
            if taking_medications:
                st.write("Please list all medications you are currently taking, including prescription, over-the-counter, and supplements.")
                medications_list = st.text_area("Medications (include name, dosage, frequency, and reason)")
            else:
                medications_list = ""
            
            # Anticoagulants
            st.write("### Anticoagulants/Blood Thinners")
            anticoagulants = st.checkbox("Are you taking any blood thinners (e.g., Warfarin, Aspirin, Plavix)?")
            if anticoagulants:
                anticoagulants_details = st.text_area("Please provide details about blood thinners")
            else:
                anticoagulants_details = ""
            
            # Bisphosphonates
            st.write("### Bisphosphonates")
            bisphosphonates = st.checkbox("Have you ever taken bisphosphonates (e.g., Fosamax, Boniva, Actonel)?")
            if bisphosphonates:
                bisphosphonates_details = st.text_area("Please provide details about bisphosphonates")
            else:
                bisphosphonates_details = ""
            
            # Submit button
            submitted = st.form_submit_button("Save Medications Information")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "current_medications": {
                        "taking_medications": taking_medications,
                        "medications_list": medications_list
                    },
                    "anticoagulants": {
                        "taking_anticoagulants": anticoagulants,
                        "details": anticoagulants_details
                    },
                    "bisphosphonates": {
                        "taking_bisphosphonates": bisphosphonates,
                        "details": bisphosphonates_details
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'medications'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses) VALUES (?, ?, ?)",
                            (patient_id, "medications", str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Medications information saved successfully!")
                except Exception as e:
                    st.error(f"Error saving medications information: {str(e)}")
    
    # Lifestyle Tab
    with tabs[4]:
        st.subheader("Lifestyle Factors")
        
        with st.form("lifestyle_form"):
            # Tobacco use
            st.write("### Tobacco Use")
            tobacco_use = st.selectbox("Do you use tobacco products?", 
                                      ["Never", "Former user", "Current user"])
            
            if tobacco_use != "Never":
                col1, col2 = st.columns(2)
                
                with col1:
                    tobacco_type = st.multiselect("Type of tobacco", 
                                                ["Cigarettes", "Cigars", "Pipe", "Smokeless tobacco", "E-cigarettes/Vaping"])
                
                with col2:
                    if tobacco_use == "Current user":
                        tobacco_frequency = st.text_input("How often do you use tobacco?")
                        tobacco_duration = st.text_input("For how many years?")
                    else:
                        tobacco_quit = st.text_input("When did you quit?")
                        tobacco_duration = st.text_input("For how many years did you use tobacco?")
            
            # Alcohol consumption
            st.write("### Alcohol Consumption")
            alcohol_consumption = st.selectbox("Do you consume alcoholic beverages?", 
                                              ["No", "Occasionally", "Moderately", "Heavily"])
            
            if alcohol_consumption != "No":
                alcohol_frequency = st.text_input("How many drinks per week?")
            else:
                alcohol_frequency = ""
            
            # Recreational drugs
            st.write("### Recreational Drugs")
            recreational_drugs = st.checkbox("Do you use recreational drugs?")
            if recreational_drugs:
                recreational_drugs_details = st.text_area("Please provide details (this information is confidential and important for your dental care)")
            else:
                recreational_drugs_details = ""
            
            # Diet
            st.write("### Diet")
            diet_description = st.text_area("Please describe your typical diet")
            
            sugary_foods = st.slider("How often do you consume sugary foods or drinks?", 0, 10, 5, 
                                    help="0 = Never, 10 = Very frequently")
            
            # Submit button
            submitted = st.form_submit_button("Save Lifestyle Information")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "tobacco_use": {
                        "status": tobacco_use,
                        "type": tobacco_type if tobacco_use != "Never" else [],
                        "frequency": tobacco_frequency if tobacco_use == "Current user" else "",
                        "duration": tobacco_duration if tobacco_use != "Never" else "",
                        "quit_date": tobacco_quit if tobacco_use == "Former user" else ""
                    },
                    "alcohol_consumption": {
                        "status": alcohol_consumption,
                        "frequency": alcohol_frequency
                    },
                    "recreational_drugs": {
                        "uses_drugs": recreational_drugs,
                        "details": recreational_drugs_details
                    },
                    "diet": {
                        "description": diet_description,
                        "sugary_foods_frequency": sugary_foods
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'lifestyle'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses) VALUES (?, ?, ?)",
                            (patient_id, "lifestyle", str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Lifestyle information saved successfully!")
                except Exception as e:
                    st.error(f"Error saving lifestyle information: {str(e)}")
    
    # Women's Health Tab
    with tabs[5]:
        st.subheader("Women's Health")
        
        with st.form("womens_health_form"):
            # Pregnancy
            st.write("### Pregnancy")
            pregnant = st.checkbox("Are you currently pregnant?")
            if pregnant:
                due_date = st.date_input("Due date", value=None)
                trimester = st.selectbox("Trimester", ["First", "Second", "Third"])
            else:
                due_date = None
                trimester = ""
            
            planning_pregnancy = st.checkbox("Are you planning to become pregnant in the near future?")
            
            # Nursing
            st.write("### Nursing")
            nursing = st.checkbox("Are you currently nursing?")
            
            # Hormonal therapy
            st.write("### Hormonal Therapy")
            hormonal_therapy = st.checkbox("Are you currently on hormonal therapy or birth control?")
            if hormonal_therapy:
                hormonal_therapy_details = st.text_area("Please provide details about hormonal therapy")
            else:
                hormonal_therapy_details = ""
            
            # Menopause
            st.write("### Menopause")
            menopause = st.selectbox("Menopause status", 
                                    ["Not applicable", "Pre-menopausal", "Peri-menopausal", "Post-menopausal"])
            
            # Submit button
            submitted = st.form_submit_button("Save Women's Health Information")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "pregnancy": {
                        "is_pregnant": pregnant,
                        "due_date": str(due_date) if due_date else "",
                        "trimester": trimester,
                        "planning_pregnancy": planning_pregnancy
                    },
                    "nursing": {
                        "is_nursing": nursing
                    },
                    "hormonal_therapy": {
                        "on_therapy": hormonal_therapy,
                        "details": hormonal_therapy_details
                    },
                    "menopause": {
                        "status": menopause
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM questionnaires WHERE patient_id = ? AND questionnaire_type = 'womens_health'", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE questionnaires SET responses = ?, completion_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO questionnaires (patient_id, questionnaire_type, responses) VALUES (?, ?, ?)",
                            (patient_id, "womens_health", str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Women's health information saved successfully!")
                except Exception as e:
                    st.error(f"Error saving women's health information: {str(e)}")

def clinical_interaction_page():
    st.title("DentAI - Clinical Interaction")
    
    # Add back navigation buttons at the top
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back to Patients", key="clinical_back_btn"):
            st.session_state.current_page = "patients"
            st.rerun()
    
    # Sidebar navigation
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}!")
        
        if st.button("Dashboard", key="clinical_dash_btn"):
            st.session_state.current_page = "dashboard"
            st.rerun()
        
        if st.button("Patient Management", key="clinical_patient_btn"):
            st.session_state.current_page = "patients"
            st.rerun()
        
        if st.button("Medical Questionnaire", key="clinical_quest_btn"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
        
        if st.button("Dental Examination", key="clinical_exam_btn"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
        
        if st.button("Logout", key="clinical_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.rerun()
    
    # Check if a patient is selected
    if 'selected_patient' not in st.session_state:
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
    conn.close()
    
    if not patient:
        st.error("Patient not found")
        return
    
    st.header(f"Clinical Interaction for {patient[0]} {patient[1]}")
    
    # Check if questionnaires are completed
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    c.execute("SELECT questionnaire_type FROM questionnaires WHERE patient_id = ?", (patient_id,))
    completed_questionnaires = [q[0] for q in c.fetchall()]
    conn.close()
    
    # Display warnings for incomplete questionnaires
    if "medical" not in completed_questionnaires:
        st.warning("Medical history questionnaire is not completed. Some AI analysis may be limited.")
        if st.button("Complete Medical History", key="complete_medical"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
    if "dental" not in completed_questionnaires:
        st.warning("Dental history questionnaire is not completed. Some AI analysis may be limited.")
        if st.button("Complete Dental History", key="complete_dental"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
    # Check if dental examination is completed
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dental_examination WHERE patient_id = ?", (patient_id,))
    exam_count = c.fetchone()[0]
    conn.close()
    
    if exam_count == 0:
        st.warning("Dental examination has not been completed. Consider completing it for more accurate analysis.")
        if st.button("Complete Dental Examination", key="complete_exam"):
            st.session_state.current_page = "dental_examination"
            st.rerun()
    
    # Clinical interaction tabs
    tabs = st.tabs(["Chief Complaint", "AI Analysis", "Treatment Planning", "Clinical Notes"])
    
    # Chief Complaint Tab
    with tabs[0]:
        st.subheader("Chief Complaint")
        
        # Audio recording and transcription section
        st.write("### Doctor-Patient Conversation")
        st.write("Record the conversation between doctor and patient to generate an AI-powered analysis.")
        
        # Check if there's already a transcription for this patient
        conn = sqlite3.connect('data/dentai.db')
        c = conn.cursor()
        c.execute("SELECT transcription, audio_file_path FROM clinical_records WHERE patient_id = ?", (patient_id,))
        existing_record = c.fetchone()
        conn.close()
        
        if existing_record and existing_record[0]:
            st.write("#### Existing Transcription")
            st.write(existing_record[0])
            
            if existing_record[1]:
                st.write("#### Existing Audio Recording")
                st.audio(existing_record[1])
            
            if st.button("Record New Conversation", key="record_new"):
                st.session_state.recording_new = True
        
        # Show recording interface if no existing transcription or user wants to record new
        if not existing_record or not existing_record[0] or ('recording_new' in st.session_state and st.session_state.recording_new):
            st.write("#### Record Conversation")
            
            # Check if audio_recorder is available
            if AUDIO_RECORDER_AVAILABLE:
                st.write("Click 'Start Recording' to begin capturing the doctor-patient conversation.")
                # Audio recording
                audio_bytes = st.audio_recorder(pause_threshold=2.0)
            else:
                st.info("Live audio recording is not available in this environment. Please upload an audio file instead.")
                uploaded_file = st.file_uploader("Upload audio file (WAV, MP3, or M4A format)", type=["wav", "mp3", "m4a"])
                audio_bytes = None
                if uploaded_file is not None:
                    audio_bytes = uploaded_file.read()
                    st.write("#### Audio Uploaded!")
                    st.audio(audio_bytes)
            
            if audio_bytes:
                st.write("#### Audio Recorded!" if AUDIO_RECORDER_AVAILABLE else "#### Audio Uploaded!")
                st.audio(audio_bytes)
                
                # Save audio file
                audio_file_path = f"data/audio/{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)
                
                with open(audio_file_path, "wb") as f:
                    f.write(audio_bytes)
                
                st.success(f"Audio saved to {audio_file_path}")
                
                # Transcribe audio
                st.write("#### Transcribing Audio...")
                
                try:
                    # Initialize OpenAI client
                    client = OpenAI(api_key="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")
                    
                    # Create a file-like object from the audio bytes
                    audio_file = BytesIO(audio_bytes)
                    audio_file.name = "recording.wav"  # OpenAI needs a filename
                    
                    # Transcribe the audio
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                    
                    transcription_text = transcript.text
                    
                    st.write("#### Transcription:")
                    st.write(transcription_text)
                    
                    # Save transcription to database
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE clinical_records SET transcription = ?, audio_file_path = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (transcription_text, audio_file_path, existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO clinical_records (patient_id, transcription, audio_file_path) VALUES (?, ?, ?)",
                            (patient_id, transcription_text, audio_file_path)
                        )
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("Transcription saved successfully!")
                    
                    # Clear recording_new flag if it exists
                    if 'recording_new' in st.session_state:
                        del st.session_state.recording_new
                    
                    # Rerun to update the UI
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error transcribing audio: {str(e)}")
        
        with st.form("chief_complaint_form"):
            # Chief complaint
            st.write("### Patient's Main Concern")
            chief_complaint = st.text_area("What brings the patient in today? (Chief complaint)")
            
            # Pain assessment
            st.write("### Pain Assessment")
            has_pain = st.checkbox("Patient reports pain")
            
            if has_pain:
                pain_location = st.text_input("Pain location")
                pain_duration = st.selectbox("Pain duration", 
                                           ["Less than a day", "1-3 days", "4-7 days", "1-2 weeks", "2+ weeks", "Months", "Years"])
                pain_intensity = st.slider("Pain intensity (1-10)", 1, 10, 5)
                
                col1, col2 = st.columns(2)
                with col1:
                    pain_constant = st.checkbox("Constant pain")
                    pain_sharp = st.checkbox("Sharp pain")
                    pain_dull = st.checkbox("Dull/aching pain")
                
                with col2:
                    pain_triggered = st.checkbox("Triggered by stimuli")
                    if pain_triggered:
                        pain_triggers = st.multiselect("Pain triggers", 
                                                     ["Cold", "Heat", "Sweet", "Pressure/Biting", "Spontaneous"])
                    else:
                        pain_triggers = []
            else:
                pain_location = ""
                pain_duration = ""
                pain_intensity = 0
                pain_constant = False
                pain_sharp = False
                pain_dull = False
                pain_triggered = False
                pain_triggers = []
            
            # Additional concerns
            st.write("### Additional Concerns")
            additional_concerns = st.text_area("Any other concerns or symptoms the patient mentions")
            
            # Submit button
            submitted = st.form_submit_button("Save Chief Complaint")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "chief_complaint": chief_complaint,
                    "pain": {
                        "has_pain": has_pain,
                        "location": pain_location,
                        "duration": pain_duration,
                        "intensity": pain_intensity,
                        "constant": pain_constant,
                        "sharp": pain_sharp,
                        "dull": pain_dull,
                        "triggered": pain_triggered,
                        "triggers": pain_triggers
                    },
                    "additional_concerns": additional_concerns
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE clinical_records SET chief_complaint = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO clinical_records (patient_id, chief_complaint) VALUES (?, ?)",
                            (patient_id, str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Chief complaint saved successfully!")
                except Exception as e:
                    st.error(f"Error saving chief complaint: {str(e)}")
    
    # AI Analysis Tab
    with tabs[1]:
        st.subheader("AI Analysis")
        
        # Get patient data for AI analysis
        try:
            conn = sqlite3.connect('data/dentai.db')
            c = conn.cursor()
            
            # Get patient basic info
            c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
            patient_data = c.fetchone()
            
            # Get questionnaire responses
            c.execute("SELECT questionnaire_type, responses FROM questionnaires WHERE patient_id = ?", (patient_id,))
            questionnaire_data = c.fetchall()
            
            # Get dental examination data
            c.execute("SELECT exam_type, findings FROM dental_examination WHERE patient_id = ?", (patient_id,))
            examination_data = c.fetchall()
            
            # Get clinical records
            c.execute("SELECT chief_complaint FROM clinical_records WHERE patient_id = ?", (patient_id,))
            clinical_data = c.fetchone()
            
            conn.close()
            
            # Check if we have enough data for analysis
            if not questionnaire_data:
                st.warning("No questionnaire data available. Please complete at least the medical and dental questionnaires.")
            elif not clinical_data:
                st.warning("No chief complaint recorded. Please complete the Chief Complaint tab first.")
            else:
                # Prepare data for AI analysis
                analysis_data = {
                    "patient": {
                        "id": patient_id,
                        "name": f"{patient[0]} {patient[1]}",
                        "age": calculate_age(patient_data[3]) if patient_data[3] else "Unknown",
                        "gender": patient_data[4] if patient_data[4] else "Unknown"
                    },
                    "questionnaires": {q_type: safe_eval(resp) for q_type, resp in questionnaire_data},
                    "examinations": {e_type: safe_eval(findings) for e_type, findings in examination_data} if examination_data else {},
                    "clinical": safe_eval(clinical_data[0]) if clinical_data else {}
                }
                
                # Display data availability for analysis
                st.write("### Data Available for Analysis")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Questionnaires Completed", f"{len(questionnaire_data)}/6")
                    st.metric("Examination Components", f"{len(examination_data)}/4" if examination_data else "0/4")
                
                with col2:
                    st.metric("Chief Complaint", "Recorded" if clinical_data else "Missing")
                    st.metric("Data Completeness", f"{calculate_completeness(analysis_data)}%")
                
                # Generate AI analysis
                if st.button("Generate AI Analysis", key="generate_analysis"):
                    with st.spinner("Analyzing patient data..."):
                        # In a real app, this would call OpenAI API
                        # For now, we'll simulate an AI analysis
                        time.sleep(2)  # Simulate processing time
                        
                        # Generate analysis based on available data
                        analysis_text = generate_ai_analysis(analysis_data)
                        
                        # Save analysis to database
                        try:
                            conn = sqlite3.connect('data/dentai.db')
                            c = conn.cursor()
                            
                            # Check if a record already exists for this patient
                            c.execute("SELECT id FROM ai_reports WHERE patient_id = ?", (patient_id,))
                            existing = c.fetchone()
                            
                            if existing:
                                # Update existing record
                                c.execute(
                                    "UPDATE ai_reports SET report_text = ?, generated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                    (analysis_text, existing[0])
                                )
                            else:
                                # Insert new record
                                c.execute(
                                    "INSERT INTO ai_reports (patient_id, report_text) VALUES (?, ?)",
                                    (patient_id, analysis_text)
                                )
                            
                            conn.commit()
                            conn.close()
                            
                            st.success("AI analysis generated successfully!")
                            st.markdown(analysis_text)
                            
                            # Add export options
                            st.write("### Export Report")
                            export_col1, export_col2 = st.columns(2)
                            
                            with export_col1:
                                # Export as text
                                download_link = create_download_link(
                                    analysis_text,
                                    f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.md",
                                    "Download as Markdown"
                                )
                                st.markdown(download_link, unsafe_allow_html=True)
                            
                            with export_col2:
                                # Export as PDF if available
                                if PDF_EXPORT_AVAILABLE:
                                    try:
                                        pdf_link = export_report_as_pdf(analysis_text, f"{patient[0]} {patient[1]}")
                                        st.markdown(pdf_link, unsafe_allow_html=True)
                                    except Exception as e:
                                        st.error(f"Error creating PDF: {str(e)}")
                                else:
                                    st.info("PDF export is not available. Install pdfkit and markdown packages for PDF export functionality.")
                        except Exception as e:
                            st.error(f"Error saving AI analysis: {str(e)}")
                
                # Display previous analysis if available
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    c.execute("SELECT report_text, generated_at FROM ai_reports WHERE patient_id = ? ORDER BY generated_at DESC LIMIT 1", (patient_id,))
                    report = c.fetchone()
                    conn.close()
                    
                    if report:
                        with st.expander("View Previous Analysis", expanded=False):
                            st.write(f"Generated on: {report[1]}")
                            st.markdown(report[0])
                            
                            # Add export options for previous report
                            st.write("### Export Previous Report")
                            prev_export_col1, prev_export_col2 = st.columns(2)
                            
                            with prev_export_col1:
                                # Export as text
                                prev_download_link = create_download_link(
                                    report[0],
                                    f"Clinical_Report_{patient[0]}_{patient[1]}_{datetime.strptime(report[1], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d')}.md",
                                    "Download as Markdown"
                                )
                                st.markdown(prev_download_link, unsafe_allow_html=True)
                            
                            with prev_export_col2:
                                # Export as PDF if available
                                if PDF_EXPORT_AVAILABLE:
                                    try:
                                        prev_pdf_link = export_report_as_pdf(report[0], f"{patient[0]} {patient[1]}")
                                        st.markdown(prev_pdf_link, unsafe_allow_html=True)
                                    except Exception as e:
                                        st.error(f"Error creating PDF: {str(e)}")
                                else:
                                    st.info("PDF export is not available. Install pdfkit and markdown packages for PDF export functionality.")
                except Exception as e:
                    st.error(f"Error retrieving previous analysis: {str(e)}")
        except Exception as e:
            st.error(f"Error preparing data for AI analysis: {str(e)}")
    
    # Treatment Planning Tab
    with tabs[2]:
        st.subheader("Treatment Planning")
        
        with st.form("treatment_plan_form"):
            # Diagnosis
            st.write("### Diagnosis")
            diagnosis = st.text_area("Clinical diagnosis")
            
            # Treatment options
            st.write("### Treatment Options")
            st.write("Enter treatment options and recommendations:")
            
            treatment_options = st.text_area("Treatment options")
            
            # Treatment plan
            st.write("### Treatment Plan")
            st.write("Outline the treatment plan sequence:")
            
            treatment_plan = st.text_area("Treatment plan sequence")
            
            # Prognosis
            st.write("### Prognosis")
            prognosis = st.selectbox("Overall prognosis", 
                                    ["Excellent", "Good", "Fair", "Poor", "Guarded"])
            
            prognosis_notes = st.text_area("Prognosis notes")
            
            # Submit button
            submitted = st.form_submit_button("Save Treatment Plan")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "diagnosis": diagnosis,
                    "treatment_options": treatment_options,
                    "treatment_plan": treatment_plan,
                    "prognosis": {
                        "status": prognosis,
                        "notes": prognosis_notes
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE clinical_records SET treatment_plan = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO clinical_records (patient_id, treatment_plan) VALUES (?, ?)",
                            (patient_id, str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Treatment plan saved successfully!")
                except Exception as e:
                    st.error(f"Error saving treatment plan: {str(e)}")
    
    # Clinical Notes Tab
    with tabs[3]:
        st.subheader("Clinical Notes")
        
        with st.form("clinical_notes_form"):
            # Clinical notes
            st.write("### Clinical Notes")
            clinical_notes = st.text_area("Enter clinical notes", height=300)
            
            # Next appointment
            st.write("### Next Appointment")
            next_appointment_date = st.date_input("Next appointment date", value=None)
            next_appointment_notes = st.text_input("Notes for next appointment")
            
            # Submit button
            submitted = st.form_submit_button("Save Clinical Notes")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "clinical_notes": clinical_notes,
                    "next_appointment": {
                        "date": str(next_appointment_date) if next_appointment_date else "",
                        "notes": next_appointment_notes
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a record already exists for this patient
                    c.execute("SELECT id FROM clinical_records WHERE patient_id = ?", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute(
                            "UPDATE clinical_records SET clinical_notes = ?, record_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new record
                        c.execute(
                            "INSERT INTO clinical_records (patient_id, clinical_notes) VALUES (?, ?)",
                            (patient_id, str(responses).replace("'", "''"))
                        )
                    
                    conn.commit()
                    conn.close()
                    st.success("Clinical notes saved successfully!")
                except Exception as e:
                    st.error(f"Error saving clinical notes: {str(e)}")

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
    # In a real app, this would call OpenAI API
    # For now, we'll generate a simulated analysis
    
    patient_name = data["patient"]["name"]
    patient_age = data["patient"]["age"]
    patient_gender = data["patient"]["gender"]
    
    # Get chief complaint if available
    chief_complaint = data.get("clinical", {}).get("chief_complaint", "No chief complaint recorded")
    
    # Check for medical conditions
    medical_conditions = []
    if "medical" in data.get("questionnaires", {}):
        med_data = data["questionnaires"]["medical"].get("medical_conditions", {})
        for condition, has_condition in med_data.items():
            if has_condition and condition != "other" and condition != "other_details":
                medical_conditions.append(condition.replace("_", " ").title())
    
    # Check for dental concerns
    dental_concerns = []
    if "dental" in data.get("questionnaires", {}):
        dental_data = data["questionnaires"]["dental"].get("dental_concerns", {})
        for concern, has_concern in dental_data.items():
            if has_concern and concern != "other":
                dental_concerns.append(concern.replace("_", " ").title())
    
    # Check for TMD issues
    tmd_issues = []
    if "dental" in data.get("questionnaires", {}):
        tmd_data = data["questionnaires"]["dental"].get("tmd_assessment", {})
        for issue, has_issue in tmd_data.items():
            if has_issue and issue not in ["previous_tmd_treatment", "treatment_details"]:
                tmd_issues.append(issue.replace("_", " ").title())
    
    # Get transcription if available
    transcription = data.get("clinical", {}).get("transcription", "")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key="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")
        
        # Prepare the prompt for OpenAI
        prompt = f"""
        Generate a comprehensive dental clinical report based on the following information:
        
        PATIENT INFORMATION:
        Name: {patient_name}
        Age: {patient_age}
        Gender: {patient_gender}
        
        CHIEF COMPLAINT:
        {chief_complaint}
        
        MEDICAL HISTORY:
        {"Medical conditions: " + ", ".join(medical_conditions) if medical_conditions else "No significant medical conditions reported."}
        
        DENTAL CONCERNS:
        {"Dental concerns: " + ", ".join(dental_concerns) if dental_concerns else "No specific dental concerns reported."}
        
        TMD ISSUES:
        {"TMD issues: " + ", ".join(tmd_issues) if tmd_issues else "No TMD issues reported."}
        
        DENTAL EXAMINATION FINDINGS:
        {json.dumps(data.get("examinations", {}), indent=2)}
        
        DOCTOR-PATIENT CONVERSATION TRANSCRIPT:
        {transcription}
        
        Please provide a detailed clinical report including:
        1. Patient Overview
        2. Medical History Summary
        3. Dental History Summary
        4. Clinical Findings
        5. Diagnosis
        6. Treatment Recommendations
        7. Prognosis
        
        Format the report in Markdown for readability.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a dental professional assistant that generates comprehensive clinical reports based on patient data and doctor-patient conversations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract the generated report
        analysis = response.choices[0].message.content
        
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
        Based on the available information, this patient presents with {"multiple" if len(dental_concerns) > 1 or len(tmd_issues) > 0 else "limited"} dental concerns and TMD issues that require attention.
        
        ## Recommendations
        1. {"Address the chief complaint of pain through appropriate diagnostic tests and treatment." if "pain" in str(chief_complaint).lower() else "Perform a comprehensive examination to identify the source of the patient's concerns."}
        2. {"Consider the patient's medical history when planning treatment, particularly: " + ", ".join(medical_conditions[:3]) if medical_conditions else "No specific medical considerations for treatment planning."}
        3. {"Prioritize addressing: " + ", ".join(dental_concerns[:3]) if dental_concerns else "Focus on preventive care and maintenance."}
        4. {"Schedule follow-up appointments to address all identified issues." if dental_concerns or tmd_issues else "Recommend regular check-ups and preventive care."}
        
        ## Treatment Considerations
        - {"Medical consultation may be necessary before certain procedures due to: " + ", ".join(medical_conditions[:2]) if medical_conditions else "No medical contraindications for standard dental treatment."}
        - {"Consider the patient's reported dental anxiety when planning treatment approach." if "dental" in data.get("questionnaires", {}) and data["questionnaires"]["dental"].get("anxiety_level", 0) > 5 else "Patient does not report significant dental anxiety."}
        - {"Evaluate for potential medication interactions before prescribing." if "medications" in data.get("questionnaires", {}) and data["questionnaires"]["medications"].get("current_medications", {}).get("taking_medications", False) else "No medication interactions to consider."}
        - {"Consider TMD evaluation and possible occlusal guard therapy based on reported symptoms." if tmd_issues else "No TMD-specific treatment considerations needed at this time."}
        """
        
        return analysis

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

if __name__ == "__main__":
    main() 