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
                            findings = eval(data['findings'])
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