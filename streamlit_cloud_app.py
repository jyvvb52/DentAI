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
    st.header("DentAI Workflow")
    
    # Display workflow steps
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
        ### 3. Clinical Interaction
        - Record patient conversation
        - Transcribe audio
        - AI analysis of clinical data
        """)
        if st.button("Go to Clinical Interaction", key="dash_goto_clinical"):
            st.session_state.current_page = "clinical"
            st.rerun()
    
    with col4:
        st.markdown("""
        ### 4. Reports & Analysis
        - View patient reports
        - AI-generated suggestions
        - Export clinical records
        """)
        # This would go to a reports page in a future enhancement
    
    # Display recent activity
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
            if st.button("Add New Patient", key="dash_add_patient"):
                st.session_state.current_page = "patients"
                st.rerun()
    
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
            st.info("No clinical records found. Complete a clinical interaction to generate records.")
    
    # Display system status
    st.header("System Status")
    
    # Check database status
    try:
        conn = sqlite3.connect('data/dentai.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM patients")
        patient_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM clinical_records")
        record_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM medical_questionnaires")
        questionnaire_count = c.fetchone()[0]
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Patients", patient_count)
        with col2:
            st.metric("Clinical Records", record_count)
        with col3:
            st.metric("Questionnaires", questionnaire_count)
        
        st.success("System is running normally. Database is accessible.")
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        
    # Display workflow tips
    with st.expander("Workflow Tips"):
        st.markdown("""
        ### Recommended Workflow
        
        For the best experience with DentAI, follow these steps:
        
        1. **Add a new patient** or select an existing one from Patient Management
        2. **Complete the Medical Questionnaire** to record patient's medical and dental history
        3. **Conduct a Clinical Interaction** to record and analyze the patient conversation
        4. **Review the AI Analysis** to get insights and treatment suggestions
        
        This workflow ensures that the AI has all the necessary information to provide the most accurate analysis and suggestions.
        """)

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
                except:
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
                col1, col2, col3, col4 = st.columns(4)
                
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
                    if st.button("Clinical Interaction", key="pat_list_go_clinical"):
                        st.session_state.selected_patient = selected_patient_id
                        st.session_state.current_page = "clinical"
                        st.rerun()
                
                with col4:
                    if st.button("Delete Patient", key="delete_patient_btn"):
                        st.session_state.confirm_delete = selected_patient_id
                        st.rerun()
                
                # Confirmation dialog for delete
                if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
                    patient_to_delete = st.session_state.confirm_delete
                    patient_name = f"{patients_df[patients_df['id'] == patient_to_delete]['first_name'].iloc[0]} {patients_df[patients_df['id'] == patient_to_delete]['last_name'].iloc[0]}"
                    
                    st.warning(f"Are you sure you want to delete {patient_name}? This action cannot be undone.")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Yes, Delete", key="confirm_delete_btn"):
                            try:
                                conn = sqlite3.connect('data/dentai.db')
                                c = conn.cursor()
                                
                                # Delete related records first (foreign key constraints)
                                c.execute("DELETE FROM clinical_records WHERE patient_id = ?", (patient_to_delete,))
                                c.execute("DELETE FROM medical_questionnaires WHERE patient_id = ?", (patient_to_delete,))
                                c.execute("DELETE FROM dental_history WHERE patient_id = ?", (patient_to_delete,))
                                c.execute("DELETE FROM allergies WHERE patient_id = ?", (patient_to_delete,))
                                c.execute("DELETE FROM ai_reports WHERE patient_id = ?", (patient_to_delete,))
                                
                                # Delete the patient
                                c.execute("DELETE FROM patients WHERE id = ?", (patient_to_delete,))
                                
                                conn.commit()
                                conn.close()
                                
                                st.success(f"Patient {patient_name} has been deleted.")
                                st.session_state.confirm_delete = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting patient: {str(e)}")
                    
                    with col2:
                        if st.button("Cancel", key="cancel_delete_btn"):
                            st.session_state.confirm_delete = None
                            st.rerun()
                
                # Patient detail view
                if 'patient_detail_view' in st.session_state and st.session_state.patient_detail_view and 'selected_patient' in st.session_state:
                    patient_id = st.session_state.selected_patient
                    patient_row = patients_df[patients_df['id'] == patient_id].iloc[0]
                    
                    st.write("---")
                    st.subheader(f"Patient Details: {patient_row['first_name']} {patient_row['last_name']}")
                    
                    # Get additional patient data
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check completion status
                    c.execute("SELECT COUNT(*) FROM medical_questionnaires WHERE patient_id = ?", (patient_id,))
                    has_medical = c.fetchone()[0] > 0
                    
                    c.execute("SELECT COUNT(*) FROM dental_history WHERE patient_id = ?", (patient_id,))
                    has_dental = c.fetchone()[0] > 0
                    
                    c.execute("SELECT COUNT(*) FROM allergies WHERE patient_id = ?", (patient_id,))
                    has_allergies = c.fetchone()[0] > 0
                    
                    c.execute("SELECT COUNT(*) FROM clinical_records WHERE patient_id = ?", (patient_id,))
                    clinical_count = c.fetchone()[0]
                    
                    c.execute("SELECT COUNT(*) FROM ai_reports WHERE patient_id = ?", (patient_id,))
                    report_count = c.fetchone()[0]
                    
                    conn.close()
                    
                    # Display patient information
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("#### Personal Information")
                        st.write(f"**Name:** {patient_row['first_name']} {patient_row['last_name']}")
                        st.write(f"**Date of Birth:** {patient_row['date_of_birth']}")
                        st.write(f"**Age:** {patient_row['Age']}")
                        st.write(f"**Gender:** {patient_row['gender']}")
                        st.write(f"**Phone:** {patient_row['phone']}")
                        st.write(f"**Email:** {patient_row['email']}")
                    
                    with col2:
                        st.write("#### Patient Progress")
                        st.write(f"**Medical History:** {'✅ Completed' if has_medical else '❌ Not Completed'}")
                        st.write(f"**Dental History:** {'✅ Completed' if has_dental else '❌ Not Completed'}")
                        st.write(f"**Allergies:** {'✅ Documented' if has_allergies else '❌ Not Documented'}")
                        st.write(f"**Clinical Records:** {clinical_count}")
                        st.write(f"**AI Reports:** {report_count}")
                    
                    # Action buttons for this patient
                    st.write("#### Actions")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("Complete Medical Questionnaire", key="detail_medical_btn"):
                            st.session_state.current_page = "questionnaire"
                            st.rerun()
                    
                    with col2:
                        if st.button("Start Clinical Interaction", key="detail_clinical_btn"):
                            st.session_state.current_page = "clinical"
                            st.rerun()
                    
                    with col3:
                        if st.button("Close Details", key="close_details_btn"):
                            st.session_state.patient_detail_view = False
                            st.rerun()
            else:
                st.info("No patients found. Add patients to get started.")
        except Exception as e:
            st.error(f"Error retrieving patients: {str(e)}")
            # Display sample data for demonstration
            sample_patients = {
                "ID": [1, 2, 3, 4, 5],
                "First Name": ["John", "Jane", "Robert", "Emily", "Michael"],
                "Last Name": ["Doe", "Smith", "Johnson", "Davis", "Wilson"],
                "Date of Birth": ["1978-05-12", "1991-08-23", "1965-11-15", "1996-04-02", "1982-07-19"],
                "Phone": ["555-123-4567", "555-234-5678", "555-345-6789", "555-456-7890", "555-567-8901"]
            }
            st.dataframe(pd.DataFrame(sample_patients))
    
    # Add Patient Tab
    with tab2:
        st.subheader("Add New Patient")
        with st.form("add_patient_form"):
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name*")
                last_name = st.text_input("Last Name*")
                dob = st.date_input("Date of Birth*")
                gender = st.selectbox("Gender*", ["Male", "Female", "Other", "Prefer not to say"])
            
            with col2:
                phone = st.text_input("Phone Number*")
                email = st.text_input("Email Address")
                address = st.text_area("Address")
            
            st.markdown("*Required fields")
            
            submitted = st.form_submit_button("Add Patient")
            if submitted:
                if first_name and last_name and phone:
                    try:
                        conn = sqlite3.connect('data/dentai.db')
                        c = conn.cursor()
                        c.execute(
                            "INSERT INTO patients (first_name, last_name, date_of_birth, gender, phone, email, address) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (first_name, last_name, dob, gender, phone, email, address)
                        )
                        
                        # Get the ID of the newly added patient
                        c.execute("SELECT last_insert_rowid()")
                        new_patient_id = c.fetchone()[0]
                        
                        conn.commit()
                        conn.close()
                        
                        st.success(f"Patient {first_name} {last_name} added successfully!")
                        
                        # Ask if user wants to proceed to questionnaires
                        st.write("Would you like to complete the medical questionnaire for this patient now?")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("Yes, Complete Questionnaire", key="new_patient_quest"):
                                st.session_state.selected_patient = new_patient_id
                                st.session_state.current_page = "questionnaire"
                                st.rerun()
                        
                        with col2:
                            if st.button("No, Add Another Patient", key="add_another"):
                                # Clear the form by refreshing
                                st.rerun()
                    except Exception as e:
                        st.error(f"Error adding patient: {str(e)}")
                else:
                    st.error("First name, last name, and phone number are required")
    
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
                    
                    col1, col2, col3 = st.columns(3)
                    
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
                        if st.button("Clinical Interaction", key="search_go_clinical"):
                            st.session_state.selected_patient = patient_id
                            st.session_state.current_page = "clinical"
                            st.rerun()
                else:
                    st.info("No matching patients found.")
                    
                    # Offer to add a new patient
                    if st.button("Add New Patient", key="search_add_new"):
                        # Switch to the Add Patient tab
                        st.session_state.active_tab = "Add Patient"
                        st.rerun()
            except Exception as e:
                st.error(f"Error searching patients: {str(e)}")
    
    # Patient Progress Tab
    with tab4:
        st.subheader("Patient Progress Overview")
        
        try:
            # Get all patients with their progress status
            conn = sqlite3.connect('data/dentai.db')
            
            # Get basic patient info
            patients = pd.read_sql_query(
                "SELECT id, first_name, last_name FROM patients ORDER BY last_name, first_name",
                conn
            )
            
            if not patients.empty:
                # Create progress tracking columns
                patients['Medical History'] = False
                patients['Dental History'] = False
                patients['Allergies'] = False
                patients['Clinical Records'] = 0
                patients['AI Reports'] = 0
                
                # Check medical history completion
                medical_completed = pd.read_sql_query(
                    "SELECT DISTINCT patient_id FROM medical_questionnaires",
                    conn
                )
                if not medical_completed.empty:
                    patients.loc[patients['id'].isin(medical_completed['patient_id']), 'Medical History'] = True
                
                # Check dental history completion
                dental_completed = pd.read_sql_query(
                    "SELECT DISTINCT patient_id FROM dental_history",
                    conn
                )
                if not dental_completed.empty:
                    patients.loc[patients['id'].isin(dental_completed['patient_id']), 'Dental History'] = True
                
                # Check allergies documentation
                allergies_completed = pd.read_sql_query(
                    "SELECT DISTINCT patient_id FROM allergies",
                    conn
                )
                if not allergies_completed.empty:
                    patients.loc[patients['id'].isin(allergies_completed['patient_id']), 'Allergies'] = True
                
                # Count clinical records
                clinical_records = pd.read_sql_query(
                    "SELECT patient_id, COUNT(*) as count FROM clinical_records GROUP BY patient_id",
                    conn
                )
                if not clinical_records.empty:
                    for _, row in clinical_records.iterrows():
                        patients.loc[patients['id'] == row['patient_id'], 'Clinical Records'] = row['count']
                
                # Count AI reports
                ai_reports = pd.read_sql_query(
                    "SELECT patient_id, COUNT(*) as count FROM ai_reports GROUP BY patient_id",
                    conn
                )
                if not ai_reports.empty:
                    for _, row in ai_reports.iterrows():
                        patients.loc[patients['id'] == row['patient_id'], 'AI Reports'] = row['count']
                
                conn.close()
                
                # Convert boolean columns to Yes/No for better display
                patients['Medical History'] = patients['Medical History'].map({True: '✅', False: '❌'})
                patients['Dental History'] = patients['Dental History'].map({True: '✅', False: '❌'})
                patients['Allergies'] = patients['Allergies'].map({True: '✅', False: '❌'})
                
                # Display the progress table
                st.write("This table shows the completion status of each patient's records:")
                st.dataframe(patients)
                
                # Summary statistics
                st.subheader("Summary Statistics")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    medical_complete_count = (patients['Medical History'] == '✅').sum()
                    st.metric("Medical Histories Completed", f"{medical_complete_count}/{len(patients)}")
                
                with col2:
                    dental_complete_count = (patients['Dental History'] == '✅').sum()
                    st.metric("Dental Histories Completed", f"{dental_complete_count}/{len(patients)}")
                
                with col3:
                    allergies_complete_count = (patients['Allergies'] == '✅').sum()
                    st.metric("Allergies Documented", f"{allergies_complete_count}/{len(patients)}")
                
                # Identify patients with incomplete records
                incomplete_patients = patients[
                    (patients['Medical History'] == '❌') | 
                    (patients['Dental History'] == '❌') | 
                    (patients['Allergies'] == '❌')
                ]
                
                if not incomplete_patients.empty:
                    st.subheader("Patients with Incomplete Records")
                    st.dataframe(incomplete_patients)
                    
                    # Select a patient to complete their records
                    selected_incomplete = st.selectbox(
                        "Select a patient to complete their records:",
                        incomplete_patients['id'].tolist(),
                        format_func=lambda x: f"{incomplete_patients[incomplete_patients['id'] == x]['first_name'].iloc[0]} {incomplete_patients[incomplete_patients['id'] == x]['last_name'].iloc[0]}"
                    )
                    
                    if st.button("Complete Records", key="complete_records_btn"):
                        st.session_state.selected_patient = selected_incomplete
                        st.session_state.current_page = "questionnaire"
                        st.rerun()
            else:
                st.info("No patients found in the database.")
        except Exception as e:
            st.error(f"Error retrieving patient progress: {str(e)}")

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
    
    # Check if patient has completed questionnaires
    c.execute("SELECT COUNT(*) FROM medical_questionnaires WHERE patient_id = ?", (patient_id,))
    has_medical = c.fetchone()[0] > 0
    
    c.execute("SELECT COUNT(*) FROM dental_history WHERE patient_id = ?", (patient_id,))
    has_dental = c.fetchone()[0] > 0
    
    c.execute("SELECT COUNT(*) FROM allergies WHERE patient_id = ?", (patient_id,))
    has_allergies = c.fetchone()[0] > 0
    
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
    
    # Display patient info in a card-like format with questionnaire status
    st.markdown(f"""
    <div style="background-color:#f0f2f6;padding:15px;border-radius:10px;margin-bottom:20px;">
        <h3 style="margin-top:0;">Patient: {patient[0]} {patient[1]}</h3>
        <p><strong>Age:</strong> {age} | <strong>Gender:</strong> {patient[3]}</p>
        <p>
            <span style="margin-right:15px;"><strong>Medical History:</strong> {'✅ Completed' if has_medical else '❌ Not Completed'}</span>
            <span style="margin-right:15px;"><strong>Dental History:</strong> {'✅ Completed' if has_dental else '❌ Not Completed'}</span>
            <span><strong>Allergies:</strong> {'✅ Documented' if has_allergies else '❌ Not Documented'}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show warning if questionnaires are not completed
    if not (has_medical and has_dental):
        st.warning("⚠️ Medical and/or dental history is not complete. For the best AI analysis, please complete all questionnaires.")
        if st.button("Go to Questionnaires", key="clin_goto_quest"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
    
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
                # Display data availability status
                st.write("### Available Patient Data")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Medical History", "Available" if medical_data else "Missing")
                with col2:
                    st.metric("Dental History", "Available" if dental_data else "Missing")
                with col3:
                    st.metric("Clinical Records", len(clinical_records) if not clinical_records.empty else 0)
                
                # Display warning if data is missing
                if not medical_data or not dental_data:
                    st.warning("Some patient data is missing. For the most accurate analysis, please complete all questionnaires.")
                    if st.button("Complete Missing Questionnaires", key="complete_missing_quest"):
                        st.session_state.current_page = "questionnaire"
                        st.rerun()
                
                if st.button("Generate Comprehensive Analysis", key="comp_analysis_btn"):
                    with st.spinner("Analyzing all patient data..."):
                        # Simulate AI processing time
                        time.sleep(2)
                        
                        # If we have medical data, try to parse it
                        med_health = "Unknown"
                        med_conditions = []
                        if medical_data:
                            try:
                                med_history = eval(medical_data[0])
                                med_health = med_history.get('general_health', 'Unknown')
                                conditions = med_history.get('conditions', {})
                                for condition, has_condition in conditions.items():
                                    if has_condition:
                                        med_conditions.append(condition.replace('_', ' ').title())
                            except:
                                pass
                        
                        # Generate analysis based on available data
                        st.markdown(f"""
                        # Comprehensive Health Analysis for {patient[0]} {patient[1]}
                        
                        ## Patient Overview
                        - **Age:** {age}
                        - **Gender:** {patient[3]}
                        - **General Health:** {med_health}
                        
                        ## Medical Conditions
                        {("- " + "\\n- ".join(med_conditions)) if med_conditions else "- No significant medical conditions reported"}
                        
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
                            - General Health: {med_health}
                            
                            ## Medical Conditions
                            {("- " + "\\n- ".join(med_conditions)) if med_conditions else "- No significant medical conditions reported"}
                            
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
                
                # Provide quick links to add missing data
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Complete Questionnaires", key="ai_goto_quest"):
                        st.session_state.current_page = "questionnaire"
                        st.rerun()
                with col2:
                    if st.button("Record Clinical Interaction", key="ai_goto_record"):
                        st.rerun()  # Just refresh to show the recording tab
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

def questionnaire_page():
    st.title("DentAI - Medical Questionnaire")
    
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
    
    st.header(f"Medical Questionnaire for {patient[0]} {patient[1]}")
    
    # Create tabs for different questionnaire types
    tabs = st.tabs(["Medical History", "Dental History", "Allergies", "Questionnaire Summary"])
    
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
            st.write("Do you have or have you had any of the following conditions?")
            col1, col2 = st.columns(2)
            
            with col1:
                heart_disease = st.checkbox("Heart Disease")
                high_bp = st.checkbox("High Blood Pressure")
                asthma = st.checkbox("Asthma")
                diabetes = st.checkbox("Diabetes")
                kidney_disease = st.checkbox("Kidney Disease")
            
            with col2:
                liver_disease = st.checkbox("Liver Disease")
                arthritis = st.checkbox("Arthritis")
                cancer = st.checkbox("Cancer")
                epilepsy = st.checkbox("Epilepsy")
                bleeding_disorder = st.checkbox("Bleeding Disorder")
            
            # Medications
            st.write("### Medications")
            medications = st.text_area("List all medications you are currently taking")
            
            # Allergies
            st.write("### Allergies")
            allergies = st.text_area("List all allergies")
            
            # Physician information
            st.write("### Physician Information")
            under_physician_care = st.checkbox("Are you currently under a physician's care?")
            physician_name = st.text_input("Physician's Name")
            physician_phone = st.text_input("Physician's Phone")
            
            # Submit button
            submitted = st.form_submit_button("Save Medical History")
            if submitted:
                # Prepare responses as JSON
                responses = {
                    "general_health": general_health,
                    "conditions": {
                        "heart_disease": heart_disease,
                        "high_bp": high_bp,
                        "asthma": asthma,
                        "diabetes": diabetes,
                        "kidney_disease": kidney_disease,
                        "liver_disease": liver_disease,
                        "arthritis": arthritis,
                        "cancer": cancer,
                        "epilepsy": epilepsy,
                        "bleeding_disorder": bleeding_disorder
                    },
                    "medications": medications,
                    "allergies": allergies,
                    "physician": {
                        "under_care": under_physician_care,
                        "name": physician_name,
                        "phone": physician_phone
                    }
                }
                
                # Save to database
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if a questionnaire already exists for this patient
                    c.execute("SELECT id FROM medical_questionnaires WHERE patient_id = ?", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing questionnaire
                        c.execute(
                            "UPDATE medical_questionnaires SET responses = ?, visit_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (str(responses).replace("'", "''"), existing[0])
                        )
                    else:
                        # Insert new questionnaire
                        c.execute(
                            "INSERT INTO medical_questionnaires (patient_id, reason_for_visit, responses) VALUES (?, ?, ?)",
                            (patient_id, "Regular checkup", str(responses).replace("'", "''"))
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
            last_dental_visit = st.date_input("Date of last dental visit", value=None)
            reason_for_last_visit = st.text_input("Reason for last visit")
            previous_dentist = st.text_input("Previous dentist's name")
            
            # Dental habits
            st.write("### Dental Habits")
            brushing_frequency = st.selectbox("How often do you brush your teeth?", 
                                             ["Twice daily", "Once daily", "Several times a week", "Less frequently"])
            flossing_frequency = st.selectbox("How often do you floss?", 
                                             ["Daily", "Several times a week", "Occasionally", "Rarely or never"])
            
            # Dental concerns
            st.write("### Dental Concerns")
            sensitivity = st.checkbox("Do you experience tooth sensitivity?")
            grinding_clenching = st.checkbox("Do you grind or clench your teeth?")
            orthodontic_treatment = st.checkbox("Have you had orthodontic treatment?")
            dental_concerns = st.text_area("Please describe any concerns about your dental health")
            
            # Submit button
            submitted = st.form_submit_button("Save Dental History")
            if submitted:
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if dental history already exists
                    c.execute("SELECT id FROM dental_history WHERE patient_id = ?", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing history
                        c.execute("""
                        UPDATE dental_history SET 
                            last_dental_visit = ?, 
                            reason_for_last_visit = ?, 
                            previous_dentist = ?, 
                            brushing_frequency = ?, 
                            flossing_frequency = ?, 
                            sensitivity = ?, 
                            grinding_clenching = ?, 
                            orthodontic_treatment = ?, 
                            dental_concerns = ? 
                        WHERE id = ?
                        """, (
                            last_dental_visit, 
                            reason_for_last_visit, 
                            previous_dentist, 
                            brushing_frequency, 
                            flossing_frequency, 
                            sensitivity, 
                            grinding_clenching, 
                            orthodontic_treatment, 
                            dental_concerns,
                            existing[0]
                        ))
                    else:
                        # Insert new history
                        c.execute("""
                        INSERT INTO dental_history (
                            patient_id, 
                            last_dental_visit, 
                            reason_for_last_visit, 
                            previous_dentist, 
                            brushing_frequency, 
                            flossing_frequency, 
                            sensitivity, 
                            grinding_clenching, 
                            orthodontic_treatment, 
                            dental_concerns
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            patient_id, 
                            last_dental_visit, 
                            reason_for_last_visit, 
                            previous_dentist, 
                            brushing_frequency, 
                            flossing_frequency, 
                            sensitivity, 
                            grinding_clenching, 
                            orthodontic_treatment, 
                            dental_concerns
                        ))
                    
                    conn.commit()
                    conn.close()
                    st.success("Dental history saved successfully!")
                except Exception as e:
                    st.error(f"Error saving dental history: {str(e)}")
    
    # Allergies Tab
    with tabs[2]:
        st.subheader("Allergies and Immunization")
        
        with st.form("allergies_form"):
            st.write("### Allergies")
            st.write("Do you have allergies to any of the following?")
            
            analgesics = st.checkbox("Analgesics (e.g., aspirin, ibuprofen)")
            antibiotics = st.checkbox("Antibiotics (e.g., penicillin)")
            latex = st.checkbox("Latex")
            metals = st.checkbox("Metals")
            dental_materials = st.checkbox("Dental materials")
            other_allergies = st.text_area("Other allergies (please specify)")
            
            st.write("### Immunization")
            vaccinated = st.checkbox("Are your vaccinations up to date?")
            
            # Submit button
            submitted = st.form_submit_button("Save Allergies Information")
            if submitted:
                try:
                    conn = sqlite3.connect('data/dentai.db')
                    c = conn.cursor()
                    
                    # Check if allergies record already exists
                    c.execute("SELECT id FROM allergies WHERE patient_id = ?", (patient_id,))
                    existing = c.fetchone()
                    
                    if existing:
                        # Update existing record
                        c.execute("""
                        UPDATE allergies SET 
                            analgesics = ?, 
                            antibiotics = ?, 
                            latex = ?, 
                            metals = ?, 
                            dental_materials = ?, 
                            other_allergies = ?, 
                            vaccinated = ? 
                        WHERE id = ?
                        """, (
                            analgesics, 
                            antibiotics, 
                            latex, 
                            metals, 
                            dental_materials, 
                            other_allergies, 
                            vaccinated,
                            existing[0]
                        ))
                    else:
                        # Insert new record
                        c.execute("""
                        INSERT INTO allergies (
                            patient_id, 
                            analgesics, 
                            antibiotics, 
                            latex, 
                            metals, 
                            dental_materials, 
                            other_allergies, 
                            vaccinated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            patient_id, 
                            analgesics, 
                            antibiotics, 
                            latex, 
                            metals, 
                            dental_materials, 
                            other_allergies, 
                            vaccinated
                        ))
                    
                    conn.commit()
                    conn.close()
                    st.success("Allergies information saved successfully!")
                except Exception as e:
                    st.error(f"Error saving allergies information: {str(e)}")
    
    # Questionnaire Summary Tab
    with tabs[3]:
        st.subheader("Questionnaire Summary")
        
        # Fetch all questionnaire data
        try:
            conn = sqlite3.connect('data/dentai.db')
            c = conn.cursor()
            
            # Medical history
            c.execute("SELECT responses FROM medical_questionnaires WHERE patient_id = ?", (patient_id,))
            medical_history = c.fetchone()
            
            # Dental history
            c.execute("""
            SELECT 
                last_dental_visit, 
                reason_for_last_visit, 
                previous_dentist, 
                brushing_frequency, 
                flossing_frequency, 
                sensitivity, 
                grinding_clenching, 
                orthodontic_treatment, 
                dental_concerns 
            FROM dental_history 
            WHERE patient_id = ?
            """, (patient_id,))
            dental_history = c.fetchone()
            
            # Allergies
            c.execute("""
            SELECT 
                analgesics, 
                antibiotics, 
                latex, 
                metals, 
                dental_materials, 
                other_allergies, 
                vaccinated 
            FROM allergies 
            WHERE patient_id = ?
            """, (patient_id,))
            allergies = c.fetchone()
            
            conn.close()
            
            # Display summary
            if medical_history or dental_history or allergies:
                st.write("### Patient Health Summary")
                
                # Medical history summary
                if medical_history:
                    st.write("#### Medical History")
                    try:
                        # Convert string representation of dict back to dict
                        med_history = eval(medical_history[0])
                        
                        st.write(f"General Health: {med_history.get('general_health', 'Not specified')}")
                        
                        st.write("Medical Conditions:")
                        conditions = med_history.get('conditions', {})
                        for condition, has_condition in conditions.items():
                            if has_condition:
                                st.write(f"- {condition.replace('_', ' ').title()}")
                        
                        if med_history.get('medications'):
                            st.write(f"Medications: {med_history.get('medications')}")
                        
                        if med_history.get('allergies'):
                            st.write(f"Allergies (self-reported): {med_history.get('allergies')}")
                        
                        physician = med_history.get('physician', {})
                        if physician.get('under_care'):
                            st.write(f"Under physician care: Yes")
                            st.write(f"Physician: {physician.get('name', 'Not specified')}")
                            st.write(f"Physician Phone: {physician.get('phone', 'Not specified')}")
                    except:
                        st.write("Error parsing medical history data")
                
                # Dental history summary
                if dental_history:
                    st.write("#### Dental History")
                    st.write(f"Last dental visit: {dental_history[0] if dental_history[0] else 'Not specified'}")
                    st.write(f"Reason for last visit: {dental_history[1] if dental_history[1] else 'Not specified'}")
                    st.write(f"Previous dentist: {dental_history[2] if dental_history[2] else 'Not specified'}")
                    st.write(f"Brushing frequency: {dental_history[3] if dental_history[3] else 'Not specified'}")
                    st.write(f"Flossing frequency: {dental_history[4] if dental_history[4] else 'Not specified'}")
                    
                    dental_concerns = []
                    if dental_history[5]: dental_concerns.append("Tooth sensitivity")
                    if dental_history[6]: dental_concerns.append("Grinding/clenching teeth")
                    if dental_history[7]: dental_concerns.append("Previous orthodontic treatment")
                    
                    if dental_concerns:
                        st.write("Dental concerns:")
                        for concern in dental_concerns:
                            st.write(f"- {concern}")
                    
                    if dental_history[8]:
                        st.write(f"Additional concerns: {dental_history[8]}")
                
                # Allergies summary
                if allergies:
                    st.write("#### Allergies and Immunization")
                    
                    allergy_list = []
                    if allergies[0]: allergy_list.append("Analgesics")
                    if allergies[1]: allergy_list.append("Antibiotics")
                    if allergies[2]: allergy_list.append("Latex")
                    if allergies[3]: allergy_list.append("Metals")
                    if allergies[4]: allergy_list.append("Dental materials")
                    
                    if allergy_list:
                        st.write("Allergies:")
                        for allergy in allergy_list:
                            st.write(f"- {allergy}")
                    
                    if allergies[5]:
                        st.write(f"Other allergies: {allergies[5]}")
                    
                    st.write(f"Vaccinations up to date: {'Yes' if allergies[6] else 'No'}")
                
                # Generate AI analysis
                if st.button("Generate AI Analysis", key="generate_ai_analysis"):
                    st.info("Analyzing patient data...")
                    
                    # Prepare data for analysis
                    analysis_data = {
                        "patient_name": f"{patient[0]} {patient[1]}",
                        "medical_history": medical_history[0] if medical_history else "{}",
                        "dental_history": {
                            "last_visit": dental_history[0] if dental_history else None,
                            "brushing": dental_history[3] if dental_history else None,
                            "flossing": dental_history[4] if dental_history else None,
                            "sensitivity": dental_history[5] if dental_history else False,
                            "grinding": dental_history[6] if dental_history else False,
                            "orthodontic": dental_history[7] if dental_history else False,
                            "concerns": dental_history[8] if dental_history else None
                        },
                        "allergies": {
                            "analgesics": allergies[0] if allergies else False,
                            "antibiotics": allergies[1] if allergies else False,
                            "latex": allergies[2] if allergies else False,
                            "metals": allergies[3] if allergies else False,
                            "dental_materials": allergies[4] if allergies else False,
                            "other": allergies[5] if allergies else None,
                            "vaccinated": allergies[6] if allergies else False
                        }
                    }
                    
                    # In a real app, this would call OpenAI API
                    # For now, we'll simulate an AI analysis
                    ai_analysis = f"""
                    # Health Analysis for {patient[0]} {patient[1]}
                    
                    ## Summary
                    Based on the provided questionnaire data, this patient appears to be in {med_history.get('general_health', 'unknown')} general health.
                    
                    ## Key Observations
                    - {'Patient reports tooth sensitivity, which may indicate enamel erosion, gum recession, or decay.' if dental_history and dental_history[5] else 'No tooth sensitivity reported.'}
                    - {'Patient reports grinding/clenching teeth, which may lead to tooth wear, jaw pain, or TMJ issues.' if dental_history and dental_history[6] else 'No teeth grinding/clenching reported.'}
                    - {'Patient has allergies that may impact treatment options.' if allergies and any(allergies[0:5]) else 'No significant allergies reported.'}
                    
                    ## Recommendations
                    1. {'Consider a night guard to prevent further damage from teeth grinding.' if dental_history and dental_history[6] else 'Regular dental check-ups every 6 months.'}
                    2. {'Use desensitizing toothpaste for sensitivity issues.' if dental_history and dental_history[5] else 'Continue current oral hygiene routine.'}
                    3. {'Take precautions regarding allergies during treatment.' if allergies and any(allergies[0:5]) else 'No special precautions needed regarding allergies.'}
                    4. {'Improve flossing habits for better gum health.' if dental_history and dental_history[4] in ['Occasionally', 'Rarely or never'] else 'Continue good flossing habits.'}
                    
                    ## Treatment Considerations
                    - {'Due to reported allergies, avoid materials containing: ' + ', '.join([a for i, a in enumerate(['analgesics', 'antibiotics', 'latex', 'metals', 'dental materials']) if allergies and allergies[i]]) if allergies and any(allergies[0:5]) else 'No specific material restrictions needed.'}
                    - {'Consider fluoride treatment to address sensitivity issues.' if dental_history and dental_history[5] else ''}
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
                        
                        st.success("AI analysis generated successfully!")
                        st.markdown(ai_analysis)
                    except Exception as e:
                        st.error(f"Error saving AI analysis: {str(e)}")
            else:
                st.info("No questionnaire data available. Please fill out the questionnaires.")
        except Exception as e:
            st.error(f"Error retrieving questionnaire data: {str(e)}")
            
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