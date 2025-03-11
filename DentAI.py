import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime, date, timedelta
import random
import string
import pandas as pd
import time
import wave
import pyaudio
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Initialize session state variables if they don't exist
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'username' not in st.session_state:
    st.session_state.username = ""

if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"

if 'remember_login' not in st.session_state:
    st.session_state.remember_login = False

if 'remembered_username' not in st.session_state:
    st.session_state.remembered_username = None

def recreate_users_table():
    """Create the users table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT UNIQUE NOT NULL,
                     password TEXT NOT NULL,
                     full_name TEXT NOT NULL,
                     email TEXT UNIQUE NOT NULL,
                     is_admin BOOLEAN DEFAULT 0)''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating users table: {e}")
    finally:
        conn.close()

def recreate_invitation_codes_table():
    """Create the invitation codes table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS invitation_codes
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     code TEXT UNIQUE NOT NULL,
                     created_by INTEGER,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     used BOOLEAN DEFAULT 0,
                     used_by INTEGER,
                     used_at TIMESTAMP,
                     FOREIGN KEY (created_by) REFERENCES users (id),
                     FOREIGN KEY (used_by) REFERENCES users (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating invitation codes table: {e}")
    finally:
        conn.close()

def recreate_patients_table():
    """Create the patients table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS patients
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     dentist_id INTEGER NOT NULL,
                     first_name TEXT NOT NULL,
                     last_name TEXT NOT NULL,
                     gender TEXT,
                     date_of_birth DATE,
                     contact_number TEXT,
                     email TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (dentist_id) REFERENCES users (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating patients table: {e}")
    finally:
        conn.close()

def recreate_records_table():
    """Create the records table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS records
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL,
                     visit_date DATE NOT NULL,
                     chief_complaint TEXT,
                     diagnosis TEXT,
                     treatment TEXT,
                     notes TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating records table: {e}")
    finally:
        conn.close()

def recreate_questionnaires_table():
    """Create the questionnaires table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS questionnaires
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL,
                     visit_date DATE NOT NULL,
                     reason_for_visit TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating questionnaires table: {e}")
    finally:
        conn.close()

def recreate_travel_questionnaires_table():
    """Create the travel questionnaires table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS travel_questionnaires
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL,
                     traveled_outside_us BOOLEAN DEFAULT 0,
                     traveled_africa BOOLEAN DEFAULT 0,
                     close_contact_sick BOOLEAN DEFAULT 0,
                     has_symptoms BOOLEAN DEFAULT 0,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating travel questionnaires table: {e}")
    finally:
        conn.close()

def recreate_vital_signs_table():
    """Create the vital signs table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS vital_signs
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL,
                     blood_pressure TEXT,
                     pulse_rhythm TEXT,
                     height_inches REAL,
                     weight_pounds REAL,
                     neck_circumference REAL,
                     bmi REAL,
                     temperature REAL,
                     respiration TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating vital signs table: {e}")
    finally:
        conn.close()

def recreate_physician_info_table():
    """Create the physician info table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS physician_info
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL,
                     under_physician_care BOOLEAN DEFAULT 0,
                     physician_name TEXT,
                     physician_address TEXT,
                     physician_phone TEXT,
                     other_physicians BOOLEAN DEFAULT 0,
                     other_physicians_details TEXT,
                     last_visit_date DATE,
                     last_visit_purpose TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating physician info table: {e}")
    finally:
        conn.close()

def recreate_allergies_table():
    """Create the allergies table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS allergies
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL,
                     analgesics TEXT,
                     antibiotics TEXT,
                     latex TEXT,
                     metals TEXT,
                     dental_materials TEXT,
                     other_allergies TEXT,
                     vaccinated BOOLEAN DEFAULT 0,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating allergies table: {e}")
    finally:
        conn.close()

def recreate_hospitalization_history_table():
    """Create the hospitalization history table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS hospitalization_history
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL,
                     condition TEXT,
                     date TEXT,
                     treatment TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating hospitalization history table: {e}")
    finally:
        conn.close()

def recreate_tmd_history_table():
    """Create the TMD history table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS tmd_history
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL,
                     has_tmd BOOLEAN DEFAULT 0,
                     symptoms TEXT,
                     diagnosis_date DATE,
                     treatment TEXT,
                     current_status TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients (id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating TMD history table: {e}")
    finally:
        conn.close()

def recreate_clinical_conversations_table():
    """Create the clinical conversations table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS clinical_conversations
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL,
                     conversation_text TEXT,
                     audio_file_path TEXT,
                     ai_analysis TEXT,
                     clinical_record TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     end_time TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients(id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating clinical_conversations table: {e}")
    finally:
        conn.close()

def recreate_current_ai_analysis_table():
    """Create the current AI analysis table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS current_ai_analysis
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     patient_id INTEGER NOT NULL UNIQUE,
                     analysis_text TEXT,
                     generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (patient_id) REFERENCES patients(id))''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating current_ai_analysis table: {e}")
    finally:
        conn.close()

# Database setup
def init_db():
    """Initialize the database and create all necessary tables"""
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Recreate all tables
    recreate_users_table()
    recreate_invitation_codes_table()
    recreate_patients_table()
    recreate_records_table()
    recreate_questionnaires_table()
    recreate_travel_questionnaires_table()
    recreate_vital_signs_table()
    recreate_physician_info_table()
    recreate_allergies_table()
    recreate_hospitalization_history_table()
    recreate_clinical_sickness_table()
    recreate_female_patient_info_table()
    recreate_special_needs_table()
    recreate_dental_history_table()
    recreate_tmd_history_table()
    recreate_ai_reports_table()
    recreate_clinical_conversations_table()
    recreate_current_ai_analysis_table()  # Add this line
    
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        # Create users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL
            )
        """)
        
        # Create invitation_codes table
        c.execute("""
            CREATE TABLE IF NOT EXISTS invitation_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                created_by INTEGER,
                used_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (used_by) REFERENCES users(id)
            )
        """)
        
        # Create patients table
        c.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dentist_id INTEGER NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                gender TEXT NOT NULL,
                date_of_birth DATE NOT NULL,
                contact_number TEXT,
                email TEXT,
                FOREIGN KEY (dentist_id) REFERENCES users(id)
            )
        """)
        
        # Create records table
        c.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                visit_date DATE NOT NULL,
                chief_complaint TEXT,
                diagnosis TEXT,
                treatment TEXT,
                notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        conn.commit()
        
        # Recreate tables that need special handling
        recreate_clinical_sickness_table()
        recreate_female_patient_info_table()
        recreate_special_needs_table()
        recreate_dental_history_table()  # Add this line
        
    except sqlite3.Error as e:
        print("Error initializing database:", e)
    finally:
        conn.close()

def recreate_dental_history_table():
    """Recreate the dental_history table"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        # Check if table exists with correct schema
        c.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='dental_history'
        """)
        current_schema = c.fetchone()
        
        # Define expected schema
        expected_schema = """CREATE TABLE dental_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                chief_complaint TEXT,
                present_complaint_history TEXT,
                first_dental_experience_age INTEGER,
                fears_dental_treatment BOOLEAN,
                recent_dental_xrays BOOLEAN,
                prior_treatment_reasons TEXT,
                treatment_complications BOOLEAN,
                oral_hygiene_methods TEXT,
                bleeding_gums BOOLEAN,
                oral_piercings BOOLEAN,
                family_tooth_loss_history BOOLEAN,
                chews_ice BOOLEAN,
                dry_mouth BOOLEAN,
                dry_mouth_eating_problems BOOLEAN,
                dry_mouth_taste_changes BOOLEAN,
                tooth_loss_reasons TEXT,
                anesthetic_problems BOOLEAN,
                removable_prosthesis_experience TEXT,
                prosthesis_fit_function TEXT,
                specialty_care TEXT,
                recurrent_ulcers BOOLEAN,
                facial_injuries BOOLEAN,
                FOREIGN KEY (patient_id) REFERENCES patients(id))"""
        
        # Only recreate if table doesn't exist or schema is wrong
        if not current_schema:
            print("Debug - Creating dental_history table as it doesn't exist")
            c.execute(expected_schema)
            conn.commit()
            print("Dental history table created successfully")
            return True
            
        return True
    except sqlite3.Error as e:
        print("Error handling dental history table:", e)
        return False
    finally:
        conn.close()

# Hash password for security
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# User authentication functions
def create_user(username, password, full_name, email, invitation_code):
    # First, verify the invitation code
    code_id = verify_invitation_code(invitation_code)
    if not code_id:
        return False, "Invalid or already used invitation code"
    
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    hashed_password = hash_password(password)
    
    try:
        c.execute(
            "INSERT INTO users (username, password, full_name, email) VALUES (?, ?, ?, ?)",
            (username, hashed_password, full_name, email)
        )
        conn.commit()
        
        # Get the user ID of the newly created user
        user_id = get_user_id(username)
        
        # Mark the invitation code as used
        mark_invitation_code_used(code_id, user_id)
        
        success = True, "Account created successfully"
    except sqlite3.IntegrityError:
        success = False, "Username already exists"
    
    conn.close()
    return success

def verify_user(username, password):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    hashed_password = hash_password(password)
    
    c.execute(
        "SELECT id, username FROM users WHERE username = ? AND password = ?",
        (username, hashed_password)
    )
    
    user = c.fetchone()
    conn.close()
    
    return user

def get_user_id(username):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    
    conn.close()
    
    if result:
        return result[0]
    return None

def is_admin(username):
    """Check if the user is an administrator (admin user)"""
    return username == "admin"

def update_password(username, current_password, new_password):
    """Update a user's password after verifying the current password"""
    # First verify the current password
    user = verify_user(username, current_password)
    if not user:
        return False, "Current password is incorrect"
    
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    hashed_password = hash_password(new_password)
    
    try:
        c.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed_password, username)
        )
        conn.commit()
        success = True, "Password updated successfully"
    except sqlite3.Error:
        success = False, "An error occurred while updating the password"
    
    conn.close()
    return success

def generate_invitation_code(created_by=None):
    """Generate a new invitation code and store it in the database"""
    
    # Get the username from the session state
    username = st.session_state.username
    
    # Check if the user is an admin
    if not is_admin(username):
        return None  # Return None if not an admin
    
    # Generate a random 8-character code
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        c.execute(
            "INSERT INTO invitation_codes (code, created_by) VALUES (?, ?)",
            (code, created_by)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # In the unlikely event of a duplicate code, try again
        conn.close()
        return generate_invitation_code(created_by)
    
    conn.close()
    return code

def verify_invitation_code(code):
    """Verify if an invitation code is valid (exists and not used)"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    c.execute("SELECT id, is_used FROM invitation_codes WHERE code = ?", (code,))
    result = c.fetchone()
    
    conn.close()
    
    if result and not result[1]:  # If code exists and is not used
        return result[0]  # Return the code ID
    return None

def mark_invitation_code_used(code_id, user_id):
    """Mark an invitation code as used by a specific user"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute(
        "UPDATE invitation_codes SET is_used = 1, used_by = ?, used_at = ? WHERE id = ?",
        (user_id, current_time, code_id)
    )
    conn.commit()
    
    conn.close()
    return True

def get_invitation_codes(created_by=None):
    """Get all invitation codes, optionally filtered by creator"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    if created_by:
        c.execute("""
            SELECT ic.id, ic.code, ic.is_used, u.username, ic.created_at, ic.used_at 
            FROM invitation_codes ic
            LEFT JOIN users u ON ic.used_by = u.id
            WHERE ic.created_by = ?
            ORDER BY ic.created_at DESC
        """, (created_by,))
    else:
        c.execute("""
            SELECT ic.id, ic.code, ic.is_used, u.username, ic.created_at, ic.used_at 
            FROM invitation_codes ic
            LEFT JOIN users u ON ic.used_by = u.id
            ORDER BY ic.created_at DESC
        """)
    
    results = c.fetchall()
    conn.close()
    
    codes = []
    for row in results:
        codes.append({
            'id': row[0],
            'code': row[1],
            'is_used': bool(row[2]),
            'used_by': row[3],
            'created_at': row[4],
            'used_at': row[5]
        })
    
    return codes

# Patient management functions
def add_patient(dentist_id, first_name, last_name, gender, date_of_birth, contact_number, email):
    """Add a new patient to the database"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO patients 
            (dentist_id, first_name, last_name, gender, date_of_birth, contact_number, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dentist_id, first_name, last_name, gender, date_of_birth, contact_number, email))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print("Error adding patient:", e)
        return False
    finally:
        conn.close()

def get_patients(dentist_id):
    """Get all patients for a dentist"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT id, first_name, last_name, gender, date_of_birth, contact_number, email 
        FROM patients 
        WHERE dentist_id = ? 
        ORDER BY last_name, first_name
    """, (dentist_id,))
    
    patients = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return patients

def get_patient(patient_id):
    """Get a specific patient's information"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT id, first_name, last_name, gender, date_of_birth, contact_number, email 
        FROM patients 
        WHERE id = ?
    """, (patient_id,))
    
    result = c.fetchone()
    patient = dict(result) if result else None
    conn.close()
    
    return patient

def update_patient(patient_id, first_name, last_name, gender, date_of_birth, contact_number, email):
    """Update patient information"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        c.execute("""
            UPDATE patients 
            SET first_name = ?, last_name = ?, gender = ?, 
                date_of_birth = ?, contact_number = ?, email = ?
            WHERE id = ?
        """, (first_name, last_name, gender, date_of_birth, 
              contact_number, email, patient_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print("Error updating patient:", e)
        return False
    finally:
        conn.close()

# Record management functions
def add_record(patient_id, visit_date, chief_complaint, diagnosis, treatment, notes):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    c.execute(
        "INSERT INTO records (patient_id, visit_date, chief_complaint, diagnosis, treatment, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (patient_id, visit_date, chief_complaint, diagnosis, treatment, notes)
    )
    
    record_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return record_id

def update_record(record_id, chief_complaint, diagnosis, treatment, notes):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    c.execute(
        "UPDATE records SET chief_complaint = ?, diagnosis = ?, treatment = ?, notes = ? WHERE id = ?",
        (chief_complaint, diagnosis, treatment, notes, record_id)
    )
    
    conn.commit()
    conn.close()

def get_records(patient_id):
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute(
        "SELECT * FROM records WHERE patient_id = ? ORDER BY visit_date DESC",
        (patient_id,)
    )
    
    records = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return records

def get_record(record_id):
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM records WHERE id = ?", (record_id,))
    
    record = dict(c.fetchone())
    conn.close()
    
    return record

# Questionnaire functions
def add_questionnaire(patient_id, visit_date, reason_for_visit):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    c.execute(
        "INSERT INTO questionnaires (patient_id, visit_date, reason_for_visit) VALUES (?, ?, ?)",
        (patient_id, visit_date, reason_for_visit)
    )
    
    conn.commit()
    conn.close()

def get_questionnaire(patient_id, visit_date):
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute(
        "SELECT * FROM questionnaires WHERE patient_id = ? AND visit_date = ? ORDER BY created_at DESC LIMIT 1",
        (patient_id, visit_date)
    )
    
    result = c.fetchone()
    questionnaire = dict(result) if result else None
    conn.close()
    
    
    return questionnaire

# Medical questionnaire functions
def save_travel_questionnaire(patient_id, traveled_outside_us, traveled_africa, close_contact_sick, has_symptoms):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    # Check if a record already exists for this patient
    c.execute("SELECT id FROM travel_questionnaire WHERE patient_id = ?", (patient_id,))
    existing = c.fetchone()
    
    if existing:
        # Update existing record
        c.execute(
            """UPDATE travel_questionnaire 
               SET traveled_outside_us = ?, traveled_africa = ?, close_contact_sick = ?, has_symptoms = ? 
               WHERE patient_id = ?""",
            (traveled_outside_us, traveled_africa, close_contact_sick, has_symptoms, patient_id)
        )
    else:
        # Insert new record
        c.execute(
            """INSERT INTO travel_questionnaire 
               (patient_id, traveled_outside_us, traveled_africa, close_contact_sick, has_symptoms) 
               VALUES (?, ?, ?, ?, ?)""",
            (patient_id, traveled_outside_us, traveled_africa, close_contact_sick, has_symptoms)
        )
    
    conn.commit()
    conn.close()

def get_travel_questionnaire(patient_id):
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM travel_questionnaire WHERE patient_id = ?", (patient_id,))
    
    result = c.fetchone()
    info = dict(result) if result else None
    conn.close()
    
    return info

# Alias for backward compatibility
def get_travel_health_data(patient_id):
    return get_travel_questionnaire(patient_id)

def save_vital_signs(patient_id, blood_pressure, pulse_rhythm, height_inches, weight_pounds, 
                    neck_circumference, bmi, temperature, respiration):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    # Check if a record already exists for this patient
    c.execute("SELECT id FROM vital_signs WHERE patient_id = ?", (patient_id,))
    existing = c.fetchone()
    
    if existing:
        # Update existing record
        c.execute(
            """UPDATE vital_signs 
               SET blood_pressure = ?, pulse_rhythm = ?, height_inches = ?, weight_pounds = ?,
               neck_circumference = ?, bmi = ?, temperature = ?, respiration = ?
               WHERE patient_id = ?""",
            (blood_pressure, pulse_rhythm, height_inches, weight_pounds, 
             neck_circumference, bmi, temperature, respiration, patient_id)
        )
    else:
        # Insert new record
        c.execute(
            """INSERT INTO vital_signs 
               (patient_id, blood_pressure, pulse_rhythm, height_inches, weight_pounds, 
               neck_circumference, bmi, temperature, respiration) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, blood_pressure, pulse_rhythm, height_inches, weight_pounds, 
             neck_circumference, bmi, temperature, respiration)
        )
    
    conn.commit()
    conn.close()

def get_vital_signs(patient_id):
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM vital_signs WHERE patient_id = ?", (patient_id,))
    
    result = c.fetchone()
    vital_signs = dict(result) if result else None
    conn.close()
    
    return vital_signs

def save_physician_info(patient_id, under_physician_care, physician_name, physician_address, 
                       physician_phone, other_physicians, other_physicians_details, 
                       last_visit_date, last_visit_purpose):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    # Check if a record already exists for this patient
    c.execute("SELECT id FROM physician_info WHERE patient_id = ?", (patient_id,))
    existing = c.fetchone()
    
    if existing:
        # Update existing record
        c.execute(
            """UPDATE physician_info 
               SET under_physician_care = ?, physician_name = ?, physician_address = ?, 
               physician_phone = ?, other_physicians = ?, other_physicians_details = ?,
               last_visit_date = ?, last_visit_purpose = ?
               WHERE patient_id = ?""",
            (under_physician_care, physician_name, physician_address, physician_phone, 
             other_physicians, other_physicians_details, last_visit_date, last_visit_purpose, patient_id)
        )
    else:
        # Insert new record
        c.execute(
            """INSERT INTO physician_info 
               (patient_id, under_physician_care, physician_name, physician_address, 
               physician_phone, other_physicians, other_physicians_details, 
               last_visit_date, last_visit_purpose) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, under_physician_care, physician_name, physician_address, 
             physician_phone, other_physicians, other_physicians_details, 
             last_visit_date, last_visit_purpose)
        )
    
    conn.commit()
    conn.close()

def get_physician_info(patient_id):
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM physician_info WHERE patient_id = ?", (patient_id,))
    
    result = c.fetchone()
    physician_info = dict(result) if result else None
    conn.close()
    
    return physician_info

def medical_questionnaire_page(patient_id):
    st.title("Medical Questionnaire")
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("Back to Patient Records", on_click=navigate_to, args=("patient_records",))
    with col2:
        if st.button("Dental Questionnaire"):
            st.session_state.current_page = "dental_questionnaire"
            st.rerun()
    
    # Get patient info
    patient_info = get_patient(patient_id)
    
    # Initialize summary dictionary
    summary = {}
    
    if patient_info:
        st.write(f"Patient: {patient_info['first_name']} {patient_info['last_name']}")
        
        # Sidebar for navigation
        with st.sidebar:
            st.title("Navigation")
            st.button("Dashboard", on_click=navigate_to, args=("dashboard",))
            st.button("Back to Records", on_click=navigate_to, args=("patient_records",))
            
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.current_page = "login"
                st.rerun()
        
        # Get existing data for each section
        travel_health_data = get_travel_health_data(patient_id)
        vital_signs_data = get_vital_signs(patient_id)
        physician_data = get_physician_info(patient_id)
        allergies_data = get_allergies(patient_id)
        hospitalization_data = get_hospitalization_history(patient_id)
        clinical_sickness_data = get_clinical_sickness(patient_id)
        female_patient_data = get_female_patient_info(patient_id)
        special_needs_data = get_special_needs(patient_id)
        
        # Create tabs for different sections of the questionnaire
        tabs = st.tabs([
            "Travel & Health", 
            "Vital Signs", 
            "Physician Information", 
            "Allergies", 
            "Hospitalization History",
            "Clinical Conditions",
            "Female Patients",
            "Special Needs"
        ])
        
        # Travel & Health tab
        with tabs[0]:
            st.header("Travel & Health Screening")
            st.markdown("""
            **Important**: If the answer is "YES" to all of these questions, place a mask on the patient, 
            inform the supervising faculty member, isolate the patient in a private room with the door closed, 
            if possible, IMMEDIATELY call Health Department.
            """)
            
            with st.form("travel_form"):
                # Default values from database if available
                traveled_outside_us = st.radio(
                    "Have you traveled outside of the United States within the last month?",
                    options=["No", "Yes"],
                    index=1 if travel_health_data and travel_health_data.get('traveled_outside_us') else 0
                )
                
                traveled_africa = st.radio(
                    "Have you traveled within or between the African countries of Liberia, Sierra Leone, or Guinea within the last month?",
                    options=["No", "Yes"],
                    index=1 if travel_health_data and travel_health_data.get('traveled_africa') else 0
                )
                
                close_contact_sick = st.radio(
                    "Have you been in close contact with anyone you believed to be sick, regardless of why you believed they were sick?",
                    options=["No", "Yes"],
                    index=1 if travel_health_data and travel_health_data.get('close_contact_sick') else 0
                )
                
                has_symptoms = st.radio(
                    "Do you have fever, headache, weakness, muscle pain, vomiting, diarrhea, or stomach pain, or unexplained bleeding or bruising?",
                    options=["No", "Yes"],
                    index=1 if travel_health_data and travel_health_data.get('has_symptoms') else 0
                )
                
                submit_travel = st.form_submit_button("Save Travel & Health Information")
                
                if submit_travel:
                    # Convert "Yes"/"No" to boolean
                    traveled_outside_us_bool = traveled_outside_us == "Yes"
                    traveled_africa_bool = traveled_africa == "Yes"
                    close_contact_sick_bool = close_contact_sick == "Yes"
                    has_symptoms_bool = has_symptoms == "Yes"
                    
                    save_travel_questionnaire(
                        patient_id, 
                        traveled_outside_us_bool, 
                        traveled_africa_bool, 
                        close_contact_sick_bool, 
                        has_symptoms_bool
                    )
                    
                    st.success("Travel & Health information saved successfully!")
                    
                    # Check if all answers are "Yes" and show warning
                    if traveled_outside_us_bool and traveled_africa_bool and close_contact_sick_bool and has_symptoms_bool:
                        st.error("""
                        ⚠️ ALERT: All questions answered YES. 
                        Please place a mask on the patient, inform the supervising faculty member, 
                        isolate the patient in a private room with the door closed, and 
                        IMMEDIATELY call the Health Department.
                        """)
        
        # Vital Signs tab
        with tabs[1]:
            st.header("Vital Signs")
            st.info("This information can be filled out later if not available now.")
            
            with st.form("vital_signs_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    blood_pressure = st.text_input(
                        "Blood Pressure",
                        value=vital_signs_data.get('blood_pressure', '') if vital_signs_data else ''
                    )
                    
                    pulse_rhythm = st.text_input(
                        "Pulse & Rhythm",
                        value=vital_signs_data.get('pulse_rhythm', '') if vital_signs_data else ''
                    )
                    
                    height_inches = st.number_input(
                        "Height (inches)",
                        min_value=0.0,
                        max_value=120.0,
                        value=float(vital_signs_data.get('height_inches', 0)) if vital_signs_data and vital_signs_data.get('height_inches') else 0.0,
                        step=0.1
                    )
                    
                    weight_pounds = st.number_input(
                        "Weight (pounds)",
                        min_value=0.0,
                        max_value=1000.0,
                        value=float(vital_signs_data.get('weight_pounds', 0)) if vital_signs_data and vital_signs_data.get('weight_pounds') else 0.0,
                        step=0.1
                    )
                
                with col2:
                    neck_circumference = st.number_input(
                        "Neck Circumference",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(vital_signs_data.get('neck_circumference', 0)) if vital_signs_data and vital_signs_data.get('neck_circumference') else 0.0,
                        step=0.1
                    )
                    
                    bmi = st.number_input(
                        "BMI",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(vital_signs_data.get('bmi', 0)) if vital_signs_data and vital_signs_data.get('bmi') else 0.0,
                        step=0.1
                    )
                    
                    temperature = st.number_input(
                        "Temperature",
                        min_value=0.0,
                        max_value=120.0,
                        value=float(vital_signs_data.get('temperature', 0)) if vital_signs_data and vital_signs_data.get('temperature') else 0.0,
                        step=0.1
                    )
                    
                    
                    respiration = st.text_input(
                        "Respiration",
                        value=vital_signs_data.get('respiration', '') if vital_signs_data else ''
                    )
                
                submit_vital_signs = st.form_submit_button("Save Vital Signs")
                
                if submit_vital_signs:
                    save_vital_signs(
                        patient_id,
                        blood_pressure,
                        pulse_rhythm,
                        height_inches,
                        weight_pounds,
                        neck_circumference,
                        bmi,
                        temperature,
                        respiration
                    )
                    
                    st.success("Vital signs saved successfully!")
        
        # Physician Information tab
        with tabs[2]:
            st.header("Physician Information")
            st.info("This information can be filled out later if not available now.")
            
            with st.form("physician_form"):
                under_physician_care = st.radio(
                    "Are you under a physician's care at present?",
                    options=["No", "Yes"],
                    index=1 if physician_data and physician_data.get('under_physician_care') else 0
                )
                
                physician_name = st.text_input(
                    "What is this physician's name?",
                    value=physician_data.get('physician_name', '') if physician_data else ''
                )
                
                physician_address = st.text_area(
                    "What is this physician's address?",
                    value=physician_data.get('physician_address', '') if physician_data else ''
                )
                
                physician_phone = st.text_input(
                    "What is this physician's telephone number?",
                    value=physician_data.get('physician_phone', '') if physician_data else ''
                )
                
                other_physicians = st.radio(
                    "Have you been to other physicians during the last two years?",
                    options=["No", "Yes"],
                    index=1 if physician_data and physician_data.get('other_physicians') else 0
                )
                
                other_physicians_details = st.text_area(
                    "What are these physicians' names, addresses, and telephone numbers?",
                    value=physician_data.get('other_physicians_details', '') if physician_data else ''
                )
                
                last_visit_date = st.date_input(
                    "When was your last visit to a physician or medical provider?",
                    value=datetime.strptime(physician_data.get('last_visit_date', '2023-01-01'), '%Y-%m-%d').date() if physician_data and physician_data.get('last_visit_date') else date.today(),
                    min_value=date(1900, 1, 1),
                    max_value=date.today()
                )
                
                last_visit_purpose = st.text_area(
                    "What was the purpose of the visit?",
                    value=physician_data.get('last_visit_purpose', '') if physician_data else ''
                )
                
                submit_physician = st.form_submit_button("Save Physician Information")
                
                if submit_physician:
                    # Convert "Yes"/"No" to boolean
                    under_physician_care_bool = under_physician_care == "Yes"
                    other_physicians_bool = other_physicians == "Yes"
                    
                    save_physician_info(
                        patient_id,
                        under_physician_care_bool,
                        physician_name,
                        physician_address,
                        physician_phone,
                        other_physicians_bool,
                        other_physicians_details,
                        last_visit_date,
                        last_visit_purpose
                    )
                    
                    st.success("Physician information saved successfully!")
        
        # Allergies tab
        with tabs[3]:
            st.header("Allergies")
            
            with st.form("allergies_form"):
                st.subheader("Do you have any of the following allergies:")
                
                analgesics = st.radio(
                    "Analgesics or pain medications?",
                    options=["No", "Yes"],
                    index=1 if allergies_data and allergies_data.get('analgesics') else 0
                )
                
                antibiotics = st.radio(
                    "Antibiotics, for example Penicillin or Erythromycin?",
                    options=["No", "Yes"],
                    index=1 if allergies_data and allergies_data.get('antibiotics') else 0
                )
                
                latex = st.radio(
                    "Latex or rubber products?",
                    options=["No", "Yes"],
                    index=1 if allergies_data and allergies_data.get('latex') else 0
                )
                
                metals = st.radio(
                    "Metals?",
                    options=["No", "Yes"],
                    index=1 if allergies_data and allergies_data.get('metals') else 0
                )
                
                dental_materials = st.radio(
                    "Any dental materials? (For example: resins, nickel, amalgam etc.)",
                    options=["No", "Yes"],
                    index=1 if allergies_data and allergies_data.get('dental_materials') else 0
                )
                
                other_allergies = st.text_area(
                    "Other allergy not listed above, e.g. shell fish?",
                    value=allergies_data.get('other_allergies', '') if allergies_data else ''
                )
                
                vaccinated = st.radio(
                    "Have you been vaccinated?",
                    options=["No", "Yes"],
                    index=1 if allergies_data and allergies_data.get('vaccinated') else 0
                )
                
                submit_allergies = st.form_submit_button("Save Allergies Information")
                
                if submit_allergies:
                    # Convert "Yes"/"No" to boolean
                    analgesics_bool = analgesics == "Yes"
                    antibiotics_bool = antibiotics == "Yes"
                    latex_bool = latex == "Yes"
                    metals_bool = metals == "Yes"
                    dental_materials_bool = dental_materials == "Yes"
                    vaccinated_bool = vaccinated == "Yes"
                    
                    save_allergies(
                        patient_id,
                        analgesics_bool,
                        antibiotics_bool,
                        latex_bool,
                        metals_bool,
                        dental_materials_bool,
                        other_allergies,
                        vaccinated_bool
                    )
                    
                    st.success("Allergies information saved successfully!")
        
        # Hospitalization History tab
        with tabs[4]:
            st.header("Hospitalization History")
            
            with st.form("hospitalization_form"):
                st.subheader("Hospitalization and past surgery information")
                
                been_hospitalized = st.radio(
                    "Have you ever been a hospitalized?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('been_hospitalized') else 0
                )
                
                had_surgery = st.radio(
                    "Have you ever had surgery, including eye surgery?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('had_surgery') else 0
                )
                
                bad_reaction_anesthetic = st.radio(
                    "Did you have a bad result or a peculiar reaction to a general anesthetic, medicines, or injections?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('bad_reaction_anesthetic') else 0
                )
                
                blood_transfusion = st.radio(
                    "Have you ever received a blood transfusion or blood products, e.g. plasma?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('blood_transfusion') else 0
                )
                
                st.subheader("Drugs or medications you are taking")
                
                regular_medications = st.radio(
                    "Are you taking taking any medications or drugs on a regular basis?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('regular_medications') else 0
                )
                
                herbs_otc_medications = st.radio(
                    "Are you taking any herbs and/or over-the-counter medications?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('herbs_otc_medications') else 0
                )
                
                blood_thinner = st.radio(
                    "Are you taking blood thinner or anticoagulant therapy medication?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('blood_thinner') else 0
                )
                
                aspirin_regularly = st.radio(
                    "Do you take aspirin on a daily or regular basis?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('aspirin_regularly') else 0
                )
                
                steroid_medication = st.radio(
                    "Have you ever received or taken steroid medication such as cortisone or body building steroids?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('steroid_medication') else 0
                )
                
                tobacco_use = st.radio(
                    "Does the patient currently use any form of tobacco?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('tobacco_use') else 0
                )
                
                medications_details = st.text_area(
                    "Please list all medications you are currently taking:",
                    value=hospitalization_data.get('medications_details', 'None')
                )
                
                st.subheader("Have you been treated for, or received any of, the following conditions?")
                
                cancer = st.radio(
                    "Cancer?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('cancer') else 0
                )
                
                radiation_treatment = st.radio(
                    "Radiation treatment or therapy?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('radiation_treatment') else 0
                )
                
                chemotherapy = st.radio(
                    "Chemotherapy?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('chemotherapy') else 0
                )
                
                face_jaw_injury = st.radio(
                    "An injury to your face or jaws?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('face_jaw_injury') else 0
                )
                
                osteoporosis_treatment = st.radio(
                    "Treatment for osteoporosis?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('osteoporosis_treatment') else 0
                )
                
                drug_alcohol_treatment = st.radio(
                    "Treatment for drug or alcohol dependency?",
                    options=["No", "Yes"],
                    index=1 if hospitalization_data and hospitalization_data.get('drug_alcohol_treatment') else 0
                )
                
                submit_hospitalization = st.form_submit_button("Save Hospitalization History")
                
                if submit_hospitalization:
                    # Convert all "Yes"/"No" to boolean and create data dictionary
                    data = {
                        'been_hospitalized': been_hospitalized == "Yes",
                        'had_surgery': had_surgery == "Yes",
                        'bad_reaction_anesthetic': bad_reaction_anesthetic == "Yes",
                        'blood_transfusion': blood_transfusion == "Yes",
                        'regular_medications': regular_medications == "Yes",
                        'herbs_otc_medications': herbs_otc_medications == "Yes",
                        'blood_thinner': blood_thinner == "Yes",
                        'aspirin_regularly': aspirin_regularly == "Yes",
                        'steroid_medication': steroid_medication == "Yes",
                        'tobacco_use': tobacco_use == "Yes",
                        'cancer': cancer == "Yes",
                        'radiation_treatment': radiation_treatment == "Yes",
                        'chemotherapy': chemotherapy == "Yes",
                        'face_jaw_injury': face_jaw_injury == "Yes",
                        'osteoporosis_treatment': osteoporosis_treatment == "Yes",
                        'drug_alcohol_treatment': drug_alcohol_treatment == "Yes",
                        'medications_details': medications_details
                    }
                    
                    save_hospitalization_history(patient_id, data)
                    st.success("Hospitalization history saved successfully!")
        
        # Clinical Conditions tab
        with tabs[5]:
            st.header("Clinical Conditions")
            
            # Get existing data if available
            clinical_data = get_clinical_sickness(patient_id)
            
            with st.form("clinical_conditions_form"):
                st.subheader("Heart and Circulation")
                
                heart_disease = st.radio(
                    "Heart Disease?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('heart_disease') == 'Yes' else 0
                )
                
                heart_surgery = st.radio(
                    "Heart Surgery?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('heart_surgery') == 'Yes' else 0
                )
                
                heart_attack = st.radio(
                    "Heart Attack?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('heart_attack') == 'Yes' else 0
                )
                
                chest_pain = st.radio(
                    "Chest Pain?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('chest_pain') == 'Yes' else 0
                )
                
                shortness_of_breath = st.radio(
                    "Shortness of Breath?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('shortness_of_breath') == 'Yes' else 0
                )
                
                heart_murmur = st.radio(
                    "Heart Murmur?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('heart_murmur') == 'Yes' else 0
                )
                
                high_blood_pressure = st.radio(
                    "High Blood Pressure?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('high_blood_pressure') == 'Yes' else 0
                )
                
                heart_defect = st.radio(
                    "Heart Defect?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('heart_defect') == 'Yes' else 0
                )
                
                rheumatic_fever = st.radio(
                    "Rheumatic Fever?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('rheumatic_fever') == 'Yes' else 0
                )
                
                st.subheader("Joints and Muscles")
                
                arthritis = st.radio(
                    "Arthritis?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('arthritis') == 'Yes' else 0
                )
                
                artificial_joint = st.radio(
                    "Artificial Joint?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('artificial_joint') == 'Yes' else 0
                )
                
                st.subheader("Digestive System")
                
                stomach_problems = st.radio(
                    "Stomach Problems?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('stomach_problems') == 'Yes' else 0
                )
                
                kidney_disease = st.radio(
                    "Kidney Disease?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('kidney_disease') == 'Yes' else 0
                )
                
                st.subheader("Respiratory System")
                
                tuberculosis = st.radio(
                    "Tuberculosis?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('tuberculosis') == 'Yes' else 0
                )
                
                persistent_cough = st.radio(
                    "Persistent Cough?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('persistent_cough') == 'Yes' else 0
                )
                
                asthma = st.radio(
                    "Asthma?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('asthma') == 'Yes' else 0
                )
                
                breathing_problems = st.radio(
                    "Breathing Problems?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('breathing_problems') == 'Yes' else 0
                )
                
                sinus_problems = st.radio(
                    "Sinus Problems?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('sinus_problems') == 'Yes' else 0
                )
                
                st.subheader("Endocrine System")
                
                diabetes = st.radio(
                    "Diabetes?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('diabetes') == 'Yes' else 0
                )
                
                thyroid_disease = st.radio(
                    "Thyroid Disease?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('thyroid_disease') == 'Yes' else 0
                )
                
                st.subheader("Other Conditions")
                
                liver_disease = st.radio(
                    "Liver Disease?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('liver_disease') == 'Yes' else 0
                )
                
                hepatitis = st.radio(
                    "Hepatitis?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('hepatitis') == 'Yes' else 0
                )
                
                aids_hiv = st.radio(
                    "AIDS/HIV?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('aids_hiv') == 'Yes' else 0
                )
                
                sexually_transmitted = st.radio(
                    "Sexually Transmitted Disease?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('sexually_transmitted') == 'Yes' else 0
                )
                
                epilepsy = st.radio(
                    "Epilepsy?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('epilepsy') == 'Yes' else 0
                )
                
                fainting = st.radio(
                    "Fainting?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('fainting') == 'Yes' else 0
                )
                
                neurological_disorders = st.radio(
                    "Neurological Disorders?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('neurological_disorders') == 'Yes' else 0
                )
                
                bleeding_problems = st.radio(
                    "Bleeding Problems?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('bleeding_problems') == 'Yes' else 0
                )
                
                anemia = st.radio(
                    "Anemia?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('anemia') == 'Yes' else 0
                )
                
                blood_disease = st.radio(
                    "Blood Disease?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('blood_disease') == 'Yes' else 0
                )
                
                head_injury = st.radio(
                    "Head Injury?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('head_injury') == 'Yes' else 0
                )
                
                eating_disorder = st.radio(
                    "Eating Disorder?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('eating_disorder') == 'Yes' else 0
                )
                
                mental_health_treatment = st.radio(
                    "Mental Health Treatment?",
                    options=["No", "Yes"],
                    index=1 if clinical_data and clinical_data.get('mental_health_treatment') == 'Yes' else 0
                )
                
                details = st.text_area(
                    "Additional Details:",
                    value=clinical_data.get('details', '') if clinical_data else ''
                )
                
                submit_clinical = st.form_submit_button("Save Clinical Conditions")
                
                if submit_clinical:
                    data = {
                        'heart_disease': heart_disease,
                        'heart_surgery': heart_surgery,
                        'heart_attack': heart_attack,
                        'chest_pain': chest_pain,
                        'shortness_of_breath': shortness_of_breath,
                        'heart_murmur': heart_murmur,
                        'high_blood_pressure': high_blood_pressure,
                        'heart_defect': heart_defect,
                        'rheumatic_fever': rheumatic_fever,
                        'arthritis': arthritis,
                        'artificial_joint': artificial_joint,
                        'stomach_problems': stomach_problems,
                        'kidney_disease': kidney_disease,
                        'tuberculosis': tuberculosis,
                        'persistent_cough': persistent_cough,
                        'asthma': asthma,
                        'breathing_problems': breathing_problems,
                        'sinus_problems': sinus_problems,
                        'diabetes': diabetes,
                        'thyroid_disease': thyroid_disease,
                        'liver_disease': liver_disease,
                        'hepatitis': hepatitis,
                        'aids_hiv': aids_hiv,
                        'sexually_transmitted': sexually_transmitted,
                        'epilepsy': epilepsy,
                        'fainting': fainting,
                        'neurological_disorders': neurological_disorders,
                        'bleeding_problems': bleeding_problems,
                        'anemia': anemia,
                        'blood_disease': blood_disease,
                        'head_injury': head_injury,
                        'eating_disorder': eating_disorder,
                        'mental_health_treatment': mental_health_treatment,
                        'details': details
                    }
                    
                    try:
                        save_clinical_sickness(patient_id, data)
                        st.success("Clinical conditions saved successfully!")
                    except Exception as e:
                        st.error(f"Error saving clinical conditions: {str(e)}")
            
            # Display summary after the form
            print("Debug - Clinical data in summary:", clinical_data)
            if clinical_data:
                # Filter out only the "Yes" conditions to make the summary more readable
                yes_conditions = {k: v for k, v in clinical_data.items() 
                                if k not in ['id', 'patient_id', 'created_at', 'details'] and v == 'Yes'}
                
                if yes_conditions:
                    summary['Clinical Conditions'] = {
                        k.replace('_', ' ').title(): v for k, v in yes_conditions.items()
                    }
                    if clinical_data.get('details'):
                        summary['Clinical Conditions']['Additional Details'] = clinical_data['details']
                else:
                    summary['Clinical Conditions'] = 'No active clinical conditions'
            else:
                summary['Clinical Conditions'] = 'No clinical conditions recorded'
        
        # Female Patients tab
        with tabs[6]:
            st.header("Female Patient Information")
            
            # Get existing data if available
            female_patient_data = get_female_patient_info(patient_id)
            
            with st.form("female_patient_form"):
                # Initialize form data with safe defaults
                female_data = {
                    'is_pregnant': female_patient_data.get('is_pregnant', 'No') if female_patient_data else 'No',
                    'pregnancy_week': female_patient_data.get('pregnancy_week', 1) if female_patient_data else 1,
                    'expected_delivery_date': female_patient_data.get('expected_delivery_date', '') if female_patient_data else '',
                    'obstetrician_name': female_patient_data.get('obstetrician_name', '') if female_patient_data else '',
                    'obstetrician_phone': female_patient_data.get('obstetrician_phone', '') if female_patient_data else '',
                    'taking_birth_control': female_patient_data.get('taking_birth_control', 'No') if female_patient_data else 'No',
                    'is_nursing': female_patient_data.get('is_nursing', 'No') if female_patient_data else 'No',
                    'menopause': female_patient_data.get('menopause', 'No') if female_patient_data else 'No',
                    'menopause_age': female_patient_data.get('menopause_age', 45) if female_patient_data else 45,
                    'hormone_replacement': female_patient_data.get('hormone_replacement', 'No') if female_patient_data else 'No',
                    'menstrual_problems': female_patient_data.get('menstrual_problems', 'No') if female_patient_data else 'No',
                    'gynecological_problems': female_patient_data.get('gynecological_problems', 'No') if female_patient_data else 'No',
                    'last_menstrual_date': female_patient_data.get('last_menstrual_date', date.today().strftime('%Y-%m-%d')) if female_patient_data else date.today().strftime('%Y-%m-%d'),
                    'details': female_patient_data.get('details', '') if female_patient_data else ''
                }
                
                # Pregnancy status
                is_pregnant = st.radio(
                    "Are you pregnant?",
                    options=["No", "Yes", "Unsure"],
                    index=["No", "Yes", "Unsure"].index(female_data['is_pregnant'])
                )
                female_data['is_pregnant'] = is_pregnant
                
                # Show pregnancy-specific fields if pregnant
                if is_pregnant == "Yes":
                    col1, col2 = st.columns(2)
                    with col1:
                        pregnancy_week = st.number_input(
                            "How many weeks pregnant are you?",
                            min_value=1,
                            max_value=45,
                            value=int(female_data['pregnancy_week'])
                        )
                        female_data['pregnancy_week'] = pregnancy_week
                    
                    with col2:
                        expected_delivery_date = st.date_input(
                            "Expected delivery date",
                            value=datetime.strptime(female_data['expected_delivery_date'], '%Y-%m-%d').date() if female_data['expected_delivery_date'] else date.today()
                        )
                        female_data['expected_delivery_date'] = expected_delivery_date.strftime('%Y-%m-%d')
                    
                    obstetrician_name = st.text_input(
                        "Obstetrician's name",
                        value=female_data['obstetrician_name']
                    )
                    female_data['obstetrician_name'] = obstetrician_name
                    
                    obstetrician_phone = st.text_input(
                        "Obstetrician's phone",
                        value=female_data['obstetrician_phone']
                    )
                    female_data['obstetrician_phone'] = obstetrician_phone
                
                # Nursing status
                is_nursing = st.radio(
                    "Are you nursing?",
                    options=["No", "Yes"],
                    index=1 if female_data['is_nursing'] == 'Yes' else 0
                )
                female_data['is_nursing'] = is_nursing
                
                # Birth control status
                taking_birth_control = st.radio(
                    "Are you taking birth control pills?",
                    options=["No", "Yes"],
                    index=1 if female_data['taking_birth_control'] == 'Yes' else 0
                )
                female_data['taking_birth_control'] = taking_birth_control
                
                # Hormone replacement status
                hormone_replacement = st.radio(
                    "Are you taking hormone replacement?",
                    options=["No", "Yes"],
                    index=1 if female_data['hormone_replacement'] == 'Yes' else 0
                )
                female_data['hormone_replacement'] = hormone_replacement
                
                # Menopause status
                menopause = st.radio(
                    "Have you reached menopause?",
                    options=["No", "Yes"],
                    index=1 if female_data['menopause'] == 'Yes' else 0
                )
                female_data['menopause'] = menopause
                
                # Show menopause-specific fields if applicable
                if menopause == "Yes":
                    menopause_age = st.number_input(
                        "At what age did you reach menopause?",
                        min_value=30,
                        max_value=65,
                        value=max(30, int(female_data['menopause_age']))
                    )
                    female_data['menopause_age'] = menopause_age
                else:
                    female_data['menopause_age'] = None  # Use NULL in database when not in menopause
                
                # Menstrual problems
                menstrual_problems = st.radio(
                    "Do you have any menstrual problems?",
                    options=["No", "Yes"],
                    index=1 if female_data['menstrual_problems'] == 'Yes' else 0
                )
                female_data['menstrual_problems'] = menstrual_problems
                
                # Gynecological problems
                gynecological_problems = st.radio(
                    "Do you have any gynecological problems?",
                    options=["No", "Yes"],
                    index=1 if female_data['gynecological_problems'] == 'Yes' else 0
                )
                female_data['gynecological_problems'] = gynecological_problems
                
                # Last menstrual date
                last_menstrual_date = st.date_input(
                    "Date of last menstrual period",
                    value=datetime.strptime(female_data['last_menstrual_date'], '%Y-%m-%d').date()
                )
                female_data['last_menstrual_date'] = last_menstrual_date.strftime('%Y-%m-%d')
                
                # Additional details
                details = st.text_area(
                    "Any other details about your health?",
                    value=female_data['details']
                )
                female_data['details'] = details
                
                # Submit button
                submit_female = st.form_submit_button("Save Female Patient Information")
                
                if submit_female:
                    try:
                        save_female_patient_info(patient_id, female_data)
                        st.success("✅ Female patient information saved successfully!")
                        time.sleep(1)  # Give user time to see the success message
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving female patient information: {str(e)}")
        
        # Special Needs tab
        with tabs[7]:
            st.header("Special Needs")
            
            with st.form("special_needs_form"):
                st.subheader("Sensory and Communication")
                impaired_hearing = st.radio(
                    "Impaired Hearing?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('impaired_hearing') == 'Yes' else 0
                )
                
                impaired_sight = st.radio(
                    "Impaired Sight?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('impaired_sight') == 'Yes' else 0
                )
                
                contact_lenses = st.radio(
                    "Contact Lenses?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('contact_lenses') == 'Yes' else 0
                )
                
                impaired_language = st.radio(
                    "Impaired Language?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('impaired_language') == 'Yes' else 0
                )
                
                impaired_mental_function = st.radio(
                    "Impaired Mental Function?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('impaired_mental_function') == 'Yes' else 0
                )
                
                st.subheader("Sleep Patterns")
                snores = st.radio(
                    "Snores?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('snores') == 'Yes' else 0
                )
                
                wakes_choking = st.radio(
                    "Wakes up choking?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('wakes_choking') == 'Yes' else 0
                )
                
                wakes_frequently = st.radio(
                    "Wakes up frequently?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('wakes_frequently') == 'Yes' else 0
                )
                
                daytime_tiredness = st.radio(
                    "Experiences daytime tiredness?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('daytime_tiredness') == 'Yes' else 0
                )
                
                falls_asleep_daytime = st.radio(
                    "Falls asleep during daytime?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('falls_asleep_daytime') == 'Yes' else 0
                )
                
                sleep_apnea_diagnosis = st.radio(
                    "Sleep Apnea Diagnosis?",
                    options=["No", "Yes"],
                    index=1 if special_needs_data and special_needs_data.get('sleep_apnea_diagnosis') == 'Yes' else 0
                )
                
                details = st.text_area(
                    "Additional Details:",
                    value=special_needs_data.get('details', '') if special_needs_data else ''
                )
                
                submit_special_needs = st.form_submit_button("Save Special Needs")
                
                if submit_special_needs:
                    data = {
                        'impaired_hearing': impaired_hearing == "Yes",
                        'impaired_sight': impaired_sight == "Yes",
                        'contact_lenses': contact_lenses == "Yes",
                        'impaired_language': impaired_language == "Yes",
                        'impaired_mental_function': impaired_mental_function == "Yes",
                        'snores': snores == "Yes",
                        'wakes_choking': wakes_choking == "Yes",
                        'wakes_frequently': wakes_frequently == "Yes",
                        'daytime_tiredness': daytime_tiredness == "Yes",
                        'falls_asleep_daytime': falls_asleep_daytime == "Yes",
                        'sleep_apnea_diagnosis': sleep_apnea_diagnosis == "Yes",
                        'details': details
                    }
                    
                    save_special_needs(patient_id, data)
                    st.success("Special needs information saved successfully!")

def manage_invitation_codes_page():
    st.title("Manage Invitation Codes")
    
    user_id = get_user_id(st.session_state.username)
    
    # Button to generate a new invitation code
    if st.button("Generate New Invitation Code"):
        code = generate_invitation_code(user_id)
        if code:
            st.success(f"New invitation code generated: {code}")
            st.info("Share this code with someone you want to invite to use DentAI.")
        else:
            st.error("You don't have permission to generate invitation codes. Only administrators can generate codes.")
    
    # Display existing invitation codes
    st.header("Your Invitation Codes")
    
    # For non-admin users, only show the codes they've used
    if is_admin(st.session_state.username):
        codes = get_invitation_codes(None)  # Get all codes for admin
    else:
        codes = get_invitation_codes(user_id)  # Get only codes created by this user
    
    if codes:
        code_data = []
        for code in codes:
            status = "Used" if code['is_used'] else "Available"
            used_by = code['used_by'] if code['used_by'] else "N/A"
            used_at = code['used_at'] if code['used_at'] else "N/A"
            
            code_data.append({
                "Code": code['code'],
                "Status": status,
                "Used By": used_by,
                "Created At": code['created_at'],
                "Used At": used_at
            })
        
        df = pd.DataFrame(code_data)
        st.dataframe(df)
    else:
        if is_admin(st.session_state.username):
            st.info("No invitation codes have been generated yet.")
        else:
            st.info("You don't have access to generate invitation codes. Please contact the administrator.")
    
    # Button to go back to dashboard
    if st.button("Back to Dashboard"):
        st.session_state.current_page = "dashboard"
        st.rerun()

def change_password_page():
    st.title("Change Password")
    
    st.write("Use this form to change your password. You'll need to enter your current password for verification.")
    
    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    
    if st.button("Change Password"):
        if current_password and new_password and confirm_password:
            if new_password == confirm_password:
                if len(new_password) >= 6:  # Basic password strength check
                    success, message = update_password(st.session_state.username, current_password, new_password)
                    if success:
                        st.success(message)
                        st.info("Please use your new password the next time you log in.")
                    else:
                        st.error(message)
                else:
                    st.error("New password must be at least 6 characters long")
            else:
                st.error("New passwords do not match")
        else:
            st.warning("Please fill in all fields")
    
    # Button to go back to dashboard
    if st.button("Back to Dashboard"):
        st.session_state.current_page = "dashboard"
        st.rerun()

# Navigation functions
def navigate_to(page):
    """Navigate to a specific page by updating the session state"""
    st.session_state.current_page = page

def navigate_to_manage_invitation_codes():
    """Navigate to the manage invitation codes page"""
    st.session_state.current_page = "manage_invitation_codes"

def navigate_to_change_password():
    """Navigate to the change password page"""
    st.session_state.current_page = "change_password"

def get_cookie_manager():
    """Get or create cookie manager"""
    if 'cookie_manager' not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager()
    return st.session_state.cookie_manager

def set_login_cookie(username):
    """Set login cookie with 30-day expiration"""
    cookie_manager = get_cookie_manager()
    expiry = (datetime.now() + timedelta(days=30)).timestamp()
    cookie_manager.set('dentai_user', username, expires_at=expiry)

def check_login_cookie():
    """Check if valid login cookie exists"""
    cookie_manager = get_cookie_manager()
    username = cookie_manager.get('dentai_user')
    if username:
        st.session_state.logged_in = True
        st.session_state.username = username
        return True
    return False

def clear_login_cookie():
    """Clear login cookie"""
    cookie_manager = get_cookie_manager()
    cookie_manager.delete('dentai_user')

def save_persistent_login(username):
    """Save login information to a file"""
    try:
        os.makedirs('data/auth', exist_ok=True)
        with open('data/auth/persistent_login.txt', 'w') as f:
            f.write(username)
        return True
    except Exception as e:
        print(f"Error saving persistent login: {e}")
        return False

def load_persistent_login():
    """Load login information from file"""
    try:
        if os.path.exists('data/auth/persistent_login.txt'):
            with open('data/auth/persistent_login.txt', 'r') as f:
                username = f.read().strip()
                if username:
                    return username
    except Exception as e:
        print(f"Error loading persistent login: {e}")
    return None

def clear_persistent_login():
    """Clear persistent login information"""
    try:
        if os.path.exists('data/auth/persistent_login.txt'):
            os.remove('data/auth/persistent_login.txt')
    except Exception as e:
        print(f"Error clearing persistent login: {e}")

def login_page():
    """Display login page"""
    st.title("Welcome to DentAI")
    
    # Check for persistent login
    if not st.session_state.get('logged_in', False):
        saved_username = load_persistent_login()
        if saved_username:
            st.session_state.logged_in = True
            st.session_state.username = saved_username
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    # Initialize session state for forgot password flow
    if 'forgot_password_state' not in st.session_state:
        st.session_state.forgot_password_state = "initial"
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    # Login tab
    with tab1:
        if st.session_state.forgot_password_state == "initial":
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                remember_me = st.checkbox("Keep me logged in")
                col1, col2 = st.columns(2)
                with col1:
                    submit = st.form_submit_button("Login", use_container_width=True)
                with col2:
                    forgot_password = st.form_submit_button("Forgot Password?", use_container_width=True)
            
            if submit and username and password:
                if verify_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    if remember_me:
                        save_persistent_login(username)
                    st.session_state.current_page = "dashboard"
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            
            elif forgot_password:
                st.session_state.forgot_password_state = "request_reset"
                st.session_state.reset_username = username if username else ""
                st.rerun()
        
        elif st.session_state.forgot_password_state == "request_reset":
            st.subheader("Password Reset")
            with st.form("reset_request_form"):
                username = st.text_input("Username", value=st.session_state.get('reset_username', ''))
                col1, col2 = st.columns(2)
                with col1:
                    submit_reset = st.form_submit_button("Send Reset Code", use_container_width=True)
                with col2:
                    cancel = st.form_submit_button("Back to Login", use_container_width=True)
            
            if submit_reset and username:
                success, message = create_password_reset_token(username)
                if success:
                    st.success(message)
                    st.session_state.forgot_password_state = "enter_code"
                    st.session_state.reset_username = username
                    st.rerun()
                else:
                    st.error(message)
            
            if cancel:
                st.session_state.forgot_password_state = "initial"
                st.rerun()
        
        elif st.session_state.forgot_password_state == "enter_code":
            st.subheader("Enter Reset Code")
            with st.form("reset_code_form"):
                reset_code = st.text_input("Enter the reset code from your email")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                col1, col2 = st.columns(2)
                with col1:
                    submit_code = st.form_submit_button("Reset Password", use_container_width=True)
                with col2:
                    cancel = st.form_submit_button("Back to Login", use_container_width=True)
            
            if submit_code:
                if not reset_code or not new_password or not confirm_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = reset_password_with_token(
                        st.session_state.reset_username,
                        reset_code,
                        new_password
                    )
                    if success:
                        st.success(message)
                        st.session_state.forgot_password_state = "initial"
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(message)
            
            if cancel:
                st.session_state.forgot_password_state = "initial"
                st.rerun()
    
    # Registration tab
    with tab2:
        with st.form("registration_form"):
            new_username = st.text_input("Username", key="reg_username")
            new_password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password")
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            invitation_code = st.text_input("Invitation Code")
            
            register = st.form_submit_button("Register", use_container_width=True)
            
            if register:
                if new_username and new_password and confirm_password and full_name and email and invitation_code:
                    if new_password == confirm_password:
                        success, message = create_user(new_username, new_password, full_name, email, invitation_code)
                        if success:
                            st.success(message)
                            st.info("Please login with your new account")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Passwords do not match")
                else:
                    st.error("Please fill in all fields")

def get_medical_questionnaire_summary(patient_id):
    """Get a summary of all medical questionnaire information for a patient"""
    summary = {}
    
    # Get travel history
    travel_data = get_travel_questionnaire(patient_id)
    if travel_data:
        summary['Travel History'] = {
            'Traveled outside US': 'Yes' if travel_data.get('traveled_outside_us') else 'No',
            'Traveled to Africa': 'Yes' if travel_data.get('traveled_africa') else 'No',
            'Close contact with sick individuals': 'Yes' if travel_data.get('close_contact_sick') else 'No',
            'Has symptoms': 'Yes' if travel_data.get('has_symptoms') else 'No'
        }
    else:
        summary['Travel History'] = 'No travel history recorded'
    
    # Get vital signs
    vital_signs = get_vital_signs(patient_id)
    if vital_signs:
        summary['Vital Signs'] = {
            'Blood Pressure': vital_signs.get('blood_pressure', 'Not recorded'),
            'Pulse & Rhythm': vital_signs.get('pulse_rhythm', 'Not recorded'),
            'BMI': vital_signs.get('bmi', 'Not recorded'),
            'Temperature': vital_signs.get('temperature', 'Not recorded')
        }
    else:
        summary['Vital Signs'] = 'No vital signs recorded'
    
    # Get physician information
    physician_info = get_physician_info(patient_id)
    if physician_info:
        summary['Physician Information'] = {
            'Under physician care': 'Yes' if physician_info.get('under_physician_care') else 'No',
            'Physician name': physician_info.get('physician_name', 'Not specified'),
            'Last visit date': physician_info.get('last_visit_date', 'Not recorded'),
            'Last visit purpose': physician_info.get('last_visit_purpose', 'Not specified')
        }
    else:
        summary['Physician Information'] = 'No physician information recorded'
    
    # Get allergies
    allergies = get_allergies(patient_id)
    if allergies:
        summary['Allergies'] = {
            'Analgesics': 'Yes' if allergies.get('analgesics') else 'No',
            'Antibiotics': 'Yes' if allergies.get('antibiotics') else 'No',
            'Latex': 'Yes' if allergies.get('latex') else 'No',
            'Metals': 'Yes' if allergies.get('metals') else 'No',
            'Dental materials': 'Yes' if allergies.get('dental_materials') else 'No',
            'Other allergies': allergies.get('other_allergies', 'None'),
            'Vaccinated': 'Yes' if allergies.get('vaccinated') else 'No'
        }
    else:
        summary['Allergies'] = 'No allergies recorded'
    
    # Get hospitalization history
    hospitalization = get_hospitalization_history(patient_id)
    if hospitalization:
        summary['Hospitalization History'] = {
            'Been Hospitalized': 'Yes' if hospitalization.get('been_hospitalized') else 'No',
            'Had Surgery': 'Yes' if hospitalization.get('had_surgery') else 'No',
            'Bad Reaction to Anesthetic': 'Yes' if hospitalization.get('bad_reaction_anesthetic') else 'No',
            'Blood Transfusion': 'Yes' if hospitalization.get('blood_transfusion') else 'No',
            'Regular Medications': 'Yes' if hospitalization.get('regular_medications') else 'No',
            'Herbs/OTC Medications': 'Yes' if hospitalization.get('herbs_otc_medications') else 'No',
            'Blood Thinner': 'Yes' if hospitalization.get('blood_thinner') else 'No',
            'Aspirin Regularly': 'Yes' if hospitalization.get('aspirin_regularly') else 'No',
            'Steroid Medication': 'Yes' if hospitalization.get('steroid_medication') else 'No',
            'Tobacco Use': 'Yes' if hospitalization.get('tobacco_use') else 'No',
            'Cancer': 'Yes' if hospitalization.get('cancer') else 'No',
            'Radiation Treatment': 'Yes' if hospitalization.get('radiation_treatment') else 'No',
            'Chemotherapy': 'Yes' if hospitalization.get('chemotherapy') else 'No',
            'Face/Jaw Injury': 'Yes' if hospitalization.get('face_jaw_injury') else 'No',
            'Osteoporosis Treatment': 'Yes' if hospitalization.get('osteoporosis_treatment') else 'No',
            'Drug/Alcohol Treatment': 'Yes' if hospitalization.get('drug_alcohol_treatment') else 'No',
            'Medications Details': hospitalization.get('medications_details', 'None')
        }
    else:
        summary['Hospitalization History'] = 'No hospitalization history recorded'
    
    # Get clinical conditions
    clinical_data = get_clinical_sickness(patient_id)
    print("Debug - Clinical data in summary:", clinical_data)
    if clinical_data:
        # Filter out only the "Yes" conditions to make the summary more readable
        yes_conditions = {k: v for k, v in clinical_data.items() 
                        if k not in ['id', 'patient_id', 'created_at', 'details'] and v == 'Yes'}
        
        if yes_conditions:
            summary['Clinical Conditions'] = {
                k.replace('_', ' ').title(): v for k, v in yes_conditions.items()
            }
            if clinical_data.get('details'):
                summary['Clinical Conditions']['Additional Details'] = clinical_data['details']
        else:
            summary['Clinical Conditions'] = 'No active clinical conditions'
    else:
        summary['Clinical Conditions'] = 'No clinical conditions recorded'
    
    # Get female patient information
    female_data = get_female_patient_info(patient_id)
    if female_data:
        summary['Female Patient Information'] = {
            'Pregnant': female_data.get('is_pregnant', 'No'),
            'Nursing': female_data.get('is_nursing', 'No'),
            'Taking Birth Control': female_data.get('taking_birth_control', 'No'),
            'Menopause': female_data.get('menopause', 'No'),
            'Hormone Replacement': female_data.get('hormone_replacement', 'No'),
            'Menstrual Problems': female_data.get('menstrual_problems', 'No'),
            'Gynecological Problems': female_data.get('gynecological_problems', 'No')
        }
        
        # Add pregnancy details if pregnant
        if female_data.get('is_pregnant') == 'Yes':
            summary['Female Patient Information'].update({
                'Pregnancy Week': female_data.get('pregnancy_week', ''),
                'Expected Delivery Date': female_data.get('expected_delivery_date', ''),
                'Obstetrician Name': female_data.get('obstetrician_name', ''),
                'Obstetrician Phone': female_data.get('obstetrician_phone', '')
            })
        
        # Add menopause age if in menopause
        if female_data.get('menopause') == 'Yes':
            summary['Female Patient Information']['Menopause Age'] = female_data.get('menopause_age', '')
        
        # Add last menstrual date
        if female_data.get('last_menstrual_date'):
            summary['Female Patient Information']['Last Menstrual Date'] = female_data.get('last_menstrual_date')
        
        # Add any additional details
        if female_data.get('details'):
            summary['Female Patient Information']['Additional Details'] = female_data.get('details')
    else:
        summary['Female Patient Information'] = 'No female patient information recorded'
    
    # Get special needs information
    special_needs_data = get_special_needs(patient_id)
    print("Debug - Special needs data in summary:", special_needs_data)
    if special_needs_data:
        # Filter out only the "Yes" conditions to make the summary more readable
        yes_conditions = {k: v for k, v in special_needs_data.items() 
                        if k not in ['id', 'patient_id', 'created_at', 'details'] 
                        and v == 'Yes'}
        
        if yes_conditions:
            # Organize conditions by category
            summary['Special Needs'] = {}
            
            # Sensory and Communication conditions
            sensory_fields = {
                'impaired_hearing': 'Impaired Hearing',
                'impaired_sight': 'Impaired Sight',
                'contact_lenses': 'Contact Lenses',
                'impaired_language': 'Impaired Language',
                'impaired_mental_function': 'Impaired Mental Function'
            }
            
            sensory_conditions = {
                sensory_fields[k]: 'Yes' for k, v in yes_conditions.items() 
                if k in sensory_fields
            }
            if sensory_conditions:
                summary['Special Needs']['Sensory and Communication'] = sensory_conditions
            
            # Sleep Pattern conditions
            sleep_fields = {
                'snores': 'Snores',
                'wakes_choking': 'Wakes Up Choking',
                'wakes_frequently': 'Wakes Up Frequently',
                'daytime_tiredness': 'Daytime Tiredness',
                'falls_asleep_daytime': 'Falls Asleep During Daytime',
                'sleep_apnea_diagnosis': 'Sleep Apnea Diagnosis'
            }
            
            sleep_conditions = {
                sleep_fields[k]: 'Yes' for k, v in yes_conditions.items() 
                if k in sleep_fields
            }
            if sleep_conditions:
                summary['Special Needs']['Sleep Patterns'] = sleep_conditions
            
            # Add additional details if any
            if special_needs_data.get('details'):
                summary['Special Needs']['Additional Details'] = special_needs_data['details']
            
            if not sensory_conditions and not sleep_conditions:
                summary['Special Needs'] = 'No active special needs'
        else:
            summary['Special Needs'] = 'No active special needs'
    else:
        summary['Special Needs'] = 'No special needs recorded'
    
    # Get dental history
    dental_data = get_dental_history(patient_id)
    if dental_data:
        summary['Dental History'] = {
            'Chief Complaint': dental_data.get('chief_complaint', 'Not specified'),
            'Present Complaint History': dental_data.get('present_complaint_history', 'Not specified'),
            'First Dental Experience Age': dental_data.get('first_dental_experience_age', 'Not specified'),
            'Fears Dental Treatment': 'Yes' if dental_data.get('fears_dental_treatment') else 'No',
            'Recent Dental X-rays': 'Yes' if dental_data.get('recent_dental_xrays') else 'No',
            'Prior Treatment Reasons': dental_data.get('prior_treatment_reasons', 'Not specified'),
            'Treatment Complications': 'Yes' if dental_data.get('treatment_complications') else 'No',
            'Oral Hygiene Methods': dental_data.get('oral_hygiene_methods', 'Not specified'),
            'Bleeding Gums': 'Yes' if dental_data.get('bleeding_gums') else 'No',
            'Oral Piercings': 'Yes' if dental_data.get('oral_piercings') else 'No',
            'Family Tooth Loss History': 'Yes' if dental_data.get('family_tooth_loss_history') else 'No',
            'Chews Ice': 'Yes' if dental_data.get('chews_ice') else 'No',
            'Dry Mouth': 'Yes' if dental_data.get('dry_mouth') else 'No',
            'Dry Mouth Eating Problems': 'Yes' if dental_data.get('dry_mouth_eating_problems') else 'No',
            'Dry Mouth Taste Changes': 'Yes' if dental_data.get('dry_mouth_taste_changes') else 'No',
            'Tooth Loss Reasons': dental_data.get('tooth_loss_reasons', 'Not specified'),
            'Anesthetic Problems': 'Yes' if dental_data.get('anesthetic_problems') else 'No',
            'Removable Prosthesis Experience': dental_data.get('removable_prosthesis_experience', 'Not specified'),
            'Prosthesis Fit Function': dental_data.get('prosthesis_fit_function', 'Not specified'),
            'Specialty Care': dental_data.get('specialty_care', 'Not specified'),
            'Recurrent Ulcers': 'Yes' if dental_data.get('recurrent_ulcers') else 'No',
            'Facial Injuries': 'Yes' if dental_data.get('facial_injuries') else 'No'
        }
    else:
        summary['Dental History'] = 'No dental history recorded'
    
    # Get TMD history
    tmd_data = get_tmd_history(patient_id)
    if tmd_data:
        summary['TMD History'] = {
            'Jaw Noises': 'Yes' if tmd_data.get('jaw_noises') else 'No',
            'Jaw/Neck Stiffness': 'Yes' if tmd_data.get('jaw_neck_stiffness') else 'No',
            'Facial Pain': 'Yes' if tmd_data.get('facial_pain') else 'No',
            'Frequent Headaches': 'Yes' if tmd_data.get('frequent_headaches') else 'No',
            'Previous TMD Treatment': 'Yes' if tmd_data.get('previous_tmd_treatment') else 'No',
            'Swallowing Difficulty': 'Yes' if tmd_data.get('swallowing_difficulty') else 'No',
            'Daytime Clenching': 'Yes' if tmd_data.get('daytime_clenching') else 'No',
            'Sleep Teeth Grinding': 'Yes' if tmd_data.get('sleep_teeth_grinding') else 'No',
            'Mouth Opening Difficulty': 'Yes' if tmd_data.get('mouth_opening_difficulty') else 'No'
        }
        if tmd_data.get('treatment_details'):
            summary['TMD History']['Treatment Details'] = tmd_data['treatment_details']
    else:
        summary['TMD History'] = 'No TMD history recorded'
    
    return summary

def patient_records_page():
    """Display patient records and medical history"""
    st.title("Patient Records")
    
    # Top navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        st.button("Back to Dashboard", key="back_to_dashboard", on_click=navigate_to, args=("dashboard",))
    with col2:
        st.button("Add New Record", key="add_new_record", on_click=navigate_to, args=("add_record",))
    
    if "selected_patient" in st.session_state:
        patient_id = st.session_state.selected_patient
        patient = get_patient(patient_id)
        
        if patient:
            st.header(f"{patient['first_name']} {patient['last_name']}'s Records")
            
            # Patient questionnaires and examination navigation
            st.subheader("Patient Forms")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.button("Medical Questionnaire", key="medical_quest_btn", 
                         on_click=navigate_to, args=("medical_questionnaire",))
            with col2:
                st.button("Dental Questionnaire", key="dental_quest_btn",
                         on_click=navigate_to, args=("dental_questionnaire",))
            with col3:
                st.button("Dental Examination", key="dental_exam_btn",
                         on_click=navigate_to, args=("dental_exam",))
            
            # Patient Information section
            st.subheader("Patient Information")
            
            # Initialize edit mode in session state if not present
            if 'edit_patient_info' not in st.session_state:
                st.session_state.edit_patient_info = False
            
            # Toggle edit mode
            if not st.session_state.edit_patient_info:
                if st.button("✏️ Edit Patient Information", key="edit_patient_btn"):
                    st.session_state.edit_patient_info = True
                    st.rerun()
            
            if st.session_state.edit_patient_info:
                # Create form for editing
                with st.form(key="edit_patient_form"):
                    st.write("Edit Patient Information")
                    first_name = st.text_input("First Name", value=patient['first_name'])
                    last_name = st.text_input("Last Name", value=patient['last_name'])
                    
                    
                    # Handle gender selection with all possible values
                    gender_options = ["Male", "Female", "Other", "Not Specified"]
                    current_gender = patient['gender'] if patient['gender'] in gender_options else "Not Specified"
                    gender = st.selectbox("Gender", gender_options, index=gender_options.index(current_gender))
                    
                    # Handle date of birth
                    try:
                        dob = datetime.strptime(patient['date_of_birth'], '%Y-%m-%d').date()
                    except:
                        dob = date.today()
                    date_of_birth = st.date_input("Date of Birth", value=dob)
                    
                    contact_number = st.text_input("Contact Number", value=patient['contact_number'] or "")
                    email = st.text_input("Email", value=patient['email'] or "")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        submit = st.form_submit_button("Save Changes")
                    with col2:
                        cancel = st.form_submit_button("Cancel")
                    
                    if submit:
                        success = update_patient(
                            patient_id, 
                            first_name, 
                            last_name, 
                            gender,
                            date_of_birth.strftime('%Y-%m-%d'),
                            contact_number, 
                            email
                        )
                        if success:
                            st.success("✅ Patient information updated successfully!")
                            st.session_state.edit_patient_info = False
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Failed to update patient information. Please try again.")
                    
                    if cancel:
                        st.session_state.edit_patient_info = False
                        st.rerun()
            else:
                # Display current information
                st.write(f"First Name: {patient['first_name']}")
                st.write(f"Last Name: {patient['last_name']}")
                st.write(f"Gender: {patient['gender']}")
                st.write(f"Date of Birth: {patient['date_of_birth']}")
                st.write(f"Contact Number: {patient['contact_number'] or 'Not provided'}")
                st.write(f"Email: {patient['email'] or 'Not provided'}")
            
            # Display medical questionnaire summary
            st.subheader("Medical History Summary")
            summary = get_medical_questionnaire_summary(patient_id)
            
            if summary:
                for category, items in summary.items():
                    with st.expander(category):
                        if isinstance(items, dict):
                            for sub_category, sub_item in items.items():
                                st.write(f"{sub_category}: {sub_item}")
                        else:
                            st.write(items)
            else:
                st.info("No medical questionnaire data available. Please complete the medical questionnaire.")
            
            # Display dental examination summary
            st.subheader("Dental Examination Summary")
            dental_summary = get_dental_exam_summary(patient_id)
            
            if dental_summary:
                for category, items in dental_summary.items():
                    with st.expander(category):
                        if isinstance(items, dict):
                            for sub_category, sub_item in items.items():
                                st.write(f"{sub_category}: {sub_item}")
                        else:
                            st.write(items)
            else:
                st.info("No dental examination data available. Please complete the dental examination.")
            
            # AI Analysis Section
            st.subheader("AI Analysis")
            
            # Display current AI analysis if it exists
            current_analysis, generated_at = get_current_ai_analysis(patient_id)
            if current_analysis:
                st.markdown("### Current AI Analysis")
                st.markdown(f"*Generated on: {generated_at}*")
                st.markdown(current_analysis)
            
            # Create two columns for the buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🤖 Generate New AI Analysis", key="generate_new_analysis_btn"):
                    with st.spinner("Generating AI analysis..."):
                        analysis = analyze_patient_data(patient_id)
                        if save_current_ai_analysis(patient_id, analysis):
                            st.success("✅ Analysis generated successfully!")
                        st.markdown(analysis)
                        
                        # Add save button
                        if st.button("💾 Save as Report", key="save_current_analysis_btn"):
                            if save_ai_report(patient_id, analysis):
                                st.success("✅ Report saved successfully!")
                                st.experimental_rerun()
                            else:
                                st.error("❌ Failed to save report. Please try again.")
    
            with col2:
                if st.button("🎤 Start Clinical Interaction", key="start_clinical_interaction_btn"):
                    st.session_state.current_page = "clinical_interaction"
                    st.rerun()
            
            # Get the latest AI report
            latest_report, report_date = get_latest_ai_report(patient_id)
            
            if latest_report:
                st.markdown("### Latest Saved AI Report")
                st.markdown(f"Generated on: {report_date}")
                st.markdown(latest_report)
                
                # Add a button to view all reports
                if st.button("View All Reports", key="view_all_reports_btn"):
                    st.markdown("### All AI Analysis Reports")
                    reports = get_all_ai_reports(patient_id)
                    for report_text, report_date in reports:
                        st.markdown(f"**Generated on: {report_date}**")
                        st.markdown(report_text)
                        st.markdown("---")
            
            # Create a container for the AI analysis section
            ai_container = st.container()
            
            # Add the generate analysis button
            if st.button("🤖 Generate New AI Analysis"):
                # Create a placeholder for the analysis
                analysis_placeholder = st.empty()
                stop_button_placeholder = st.empty()
                
                # Add a stop button
                if stop_button_placeholder.button("⏹️ Stop Generation"):
                    st.session_state.stop_ai_generation = True
                    stop_button_placeholder.empty()
                
                # Generate the analysis
                with st.spinner("Generating AI analysis..."):
                    analysis = analyze_patient_data(patient_id)
                    if not st.session_state.get('stop_ai_generation', False):
                        # Store the analysis in session state
                        st.session_state.current_analysis = analysis
                        analysis_placeholder.markdown(analysis)
                        
                        # Add save button
                        if st.button("💾 Save Report"):
                            with st.spinner("Saving report..."):
                                if save_ai_report(patient_id, analysis):
                                    st.success("✅ Report saved successfully!")
                                    # Store success state
                                    st.session_state.save_success = True
                                    st.session_state.save_success_time = time.time()
                                else:
                                    st.error("❌ Failed to save report. Please try again.")
                
                # Reset the stop flag
                st.session_state.stop_ai_generation = False
            
            # Show success message if report was just saved
            if st.session_state.get('save_success', False):
                if time.time() - st.session_state.save_success_time < 3:  # Show for 3 seconds
                    st.success("✅ Report saved successfully!")
                else:
                    st.session_state.save_success = False
            
            # Display the current analysis if it exists
            if 'current_analysis' in st.session_state:
                st.markdown("### Current Analysis")
                st.markdown(st.session_state.current_analysis)
            
            # Display dental records
            st.subheader("Dental Records")
            records = get_records(patient_id)
            
            if records:
                for record in records:
                    with st.expander(f"Visit Date: {record['visit_date']}"):
                        st.write(f"Chief Complaint: {record['chief_complaint']}")
                        st.write(f"Diagnosis: {record['diagnosis']}")
                        st.write(f"Treatment: {record['treatment']}")
                        if record['notes']:
                            st.write(f"Notes: {record['notes']}")
                        st.button("Edit Record", key=f"edit_record_{record['id']}", 
                                on_click=lambda: st.session_state.update({'selected_record': record['id']}))
            else:
                st.info("No dental records available yet.")
    else:
        st.warning("Please select a patient from the dashboard first.")

def edit_record_page():
    st.title("Edit Record")
    
    if 'selected_record' not in st.session_state:
        st.error("No record selected")
        st.button("Back to Patient Records", on_click=navigate_to, args=("patient_records",))
        return
    
    record = get_record(st.session_state.selected_record)
    patient_info = get_patient(st.session_state.selected_patient)
    
    if record and patient_info:
        st.write(f"Patient: {patient_info['first_name']} {patient_info['last_name']}")
        st.write(f"Visit Date: {record['visit_date']}")
        
        # Sidebar for navigation
        with st.sidebar:
            st.title("Navigation")
            st.button("Back to Records", on_click=navigate_to, args=("patient_records",))
            
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.current_page = "login"
                st.rerun()
        
        # Edit form
        with st.form("edit_record_form"):
            chief_complaint = st.text_area("Chief Complaint", value=record['chief_complaint'])
            diagnosis = st.text_area("Diagnosis", value=record['diagnosis'])
            treatment = st.text_area("Treatment", value=record['treatment'])
            notes = st.text_area("Notes", value=record['notes'])
            
            submit_button = st.form_submit_button("Update Record")
            
            if submit_button:
                update_record(
                    st.session_state.selected_record,
                    chief_complaint,
                    diagnosis,
                    treatment,
                    notes
                )
                st.success("Record updated successfully!")
                st.session_state.current_page = "patient_records"
                st.rerun()
    else:
        st.error("Record or patient not found")
        st.button("Back to Patient Records", on_click=navigate_to, args=("patient_records",))

# Main app logic
def main():
    """Main application function"""
    # Initialize database
    init_db()
    
    # Set page config
    st.set_page_config(
        page_title="DentAI - Dental AI Assistant",
        page_icon="🦷",
        layout="wide"
    )
    
    # Check for remembered login
    if not st.session_state.get('logged_in', False) and st.session_state.get('remember_login', False):
        remembered_username = st.session_state.get('remembered_username')
        if remembered_username:
            st.session_state.logged_in = True
            st.session_state.username = remembered_username
    
    # Display appropriate page based on session state
    if not st.session_state.get('logged_in', False):
        login_page()
    else:
        if st.session_state.current_page == "dashboard":
            dashboard_page()
        elif st.session_state.current_page == "add_patient":
            add_patient_page()
        elif st.session_state.current_page == "patient_records":
            patient_records_page()
        elif st.session_state.current_page == "edit_record":
            edit_record_page()
        elif st.session_state.current_page == "medical_questionnaire":
            medical_questionnaire_page(st.session_state.selected_patient)
        elif st.session_state.current_page == "dental_questionnaire":
            dental_questionnaire_page(st.session_state.selected_patient)
        elif st.session_state.current_page == "dental_exam":
            dental_exam_page(st.session_state.selected_patient)
        elif st.session_state.current_page == "clinical_interaction":  # Add this line
            clinical_interaction_page(st.session_state.selected_patient)  # Add this line
        elif st.session_state.current_page == "manage_invitation_codes":
            manage_invitation_codes_page()
        elif st.session_state.current_page == "change_password":
            change_password_page()
        elif st.session_state.current_page == "settings":
            settings_page()

def dashboard_page():
    """Display dashboard page"""
    # Get the full name of the logged-in user and extract last name
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    c.execute("SELECT full_name FROM users WHERE username = ?", (st.session_state.username,))
    result = c.fetchone()
    conn.close()
    
    if result:
        last_name = result[0].split()[-1]  # Get the last word of the full name
        st.title(f"Welcome, Dr. {last_name}")
    else:
        st.title("Welcome")
    
    # Sidebar for navigation
    with st.sidebar:
        st.title("Navigation")
        st.button("Dashboard", on_click=navigate_to, args=("dashboard",))
        st.button("Add Patient", on_click=navigate_to, args=("add_patient",))
        
        # Only show invitation code management for admin users
        if is_admin(st.session_state.username):
            st.button("Manage Invitation Codes", on_click=navigate_to_manage_invitation_codes)
        
        st.button("Settings", on_click=navigate_to, args=("settings",))
        st.button("Change Password", on_click=navigate_to_change_password)
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            clear_persistent_login()
            st.rerun()
    
    # Main content
    st.header("Your Patients")
    
    # Get dentist's patients
    dentist_id = get_user_id(st.session_state.username)
    patients = get_patients(dentist_id)
    
    if patients:
        # Create a DataFrame for better display
        df = pd.DataFrame(patients)
        df = df[['id', 'first_name', 'last_name', 'gender', 'date_of_birth', 'contact_number', 'email']]
        df.columns = ['ID', 'First Name', 'Last Name', 'Gender', 'Date of Birth', 'Contact Number', 'Email']
        
        # Display patients in a table
        st.dataframe(df)
        
        # Patient selection
        patient_options = [f"{p['first_name']} {p['last_name']} (ID: {p['id']})" for p in patients]
        selected_patient = st.selectbox("Select a patient to view records", [""] + patient_options)
        
        if selected_patient:
            patient_id = int(selected_patient.split("ID: ")[1].rstrip(")"))
            st.session_state.selected_patient = patient_id
            st.button("View Patient Records", on_click=navigate_to, args=("patient_records",))
    else:
        st.info("You haven't added any patients yet. Click 'Add Patient' to get started.")

def get_allergies(patient_id):
    """Get allergies information for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM allergies WHERE patient_id = ?", (patient_id,))
    
    result = c.fetchone()
    info = dict(result) if result else None
    conn.close()
    
    return info

def save_allergies(patient_id, analgesics, antibiotics, latex, metals, dental_materials, other_allergies, vaccinated):
    """Save allergies information for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    # Check if a record already exists for this patient
    c.execute("SELECT id FROM allergies WHERE patient_id = ?", (patient_id,))
    existing = c.fetchone()
    
    if existing:
        # Update existing record
        c.execute("""
            UPDATE allergies 
            SET analgesics = ?, antibiotics = ?, latex = ?, metals = ?, 
                dental_materials = ?, other_allergies = ?, vaccinated = ?
            WHERE patient_id = ?
        """, (analgesics, antibiotics, latex, metals, dental_materials, 
              other_allergies, vaccinated, patient_id))
    else:
        # Insert new record
        c.execute("""
            INSERT INTO allergies 
            (patient_id, analgesics, antibiotics, latex, metals, 
             dental_materials, other_allergies, vaccinated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, analgesics, antibiotics, latex, metals, 
              dental_materials, other_allergies, vaccinated))
    
    conn.commit()
    conn.close()
    return True

def get_hospitalization_history(patient_id):
    """Get hospitalization history for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM hospitalization_history WHERE patient_id = ?", (patient_id,))
    
    result = c.fetchone()
    info = dict(result) if result else None
    conn.close()
    
    return info

def save_hospitalization_history(patient_id, data):
    """Save hospitalization history for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    # Check if a record already exists for this patient
    c.execute("SELECT id FROM hospitalization_history WHERE patient_id = ?", (patient_id,))
    existing = c.fetchone()
    
    if existing:
        # Update existing record
        c.execute("""
            UPDATE hospitalization_history 
            SET been_hospitalized = ?, had_surgery = ?, bad_reaction_anesthetic = ?,
                blood_transfusion = ?, regular_medications = ?, herbs_otc_medications = ?,
                blood_thinner = ?, aspirin_regularly = ?, steroid_medication = ?,
                tobacco_use = ?, cancer = ?, radiation_treatment = ?, chemotherapy = ?,
                face_jaw_injury = ?, osteoporosis_treatment = ?, drug_alcohol_treatment = ?,
                medications_details = ?
            WHERE patient_id = ?
        """, (
            data['been_hospitalized'], data['had_surgery'], data['bad_reaction_anesthetic'],
            data['blood_transfusion'], data['regular_medications'], data['herbs_otc_medications'],
            data['blood_thinner'], data['aspirin_regularly'], data['steroid_medication'],
            data['tobacco_use'], data['cancer'], data['radiation_treatment'], data['chemotherapy'],
            data['face_jaw_injury'], data['osteoporosis_treatment'], data['drug_alcohol_treatment'],
            data['medications_details'], patient_id
        ))
    else:
        # Insert new record
        c.execute("""
            INSERT INTO hospitalization_history 
            (patient_id, been_hospitalized, had_surgery, bad_reaction_anesthetic,
             blood_transfusion, regular_medications, herbs_otc_medications,
             blood_thinner, aspirin_regularly, steroid_medication,
             tobacco_use, cancer, radiation_treatment, chemotherapy,
             face_jaw_injury, osteoporosis_treatment, drug_alcohol_treatment,
             medications_details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            data['been_hospitalized'], data['had_surgery'], data['bad_reaction_anesthetic'],
            data['blood_transfusion'], data['regular_medications'], data['herbs_otc_medications'],
            data['blood_thinner'], data['aspirin_regularly'], data['steroid_medication'],
            data['tobacco_use'], data['cancer'], data['radiation_treatment'], data['chemotherapy'],
            data['face_jaw_injury'], data['osteoporosis_treatment'], data['drug_alcohol_treatment'],
            data['medications_details']
        ))
    
    conn.commit()
    conn.close()
    return True

def get_clinical_sickness(patient_id):
    """Get clinical sickness data for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        # Debug: Print the SQL query
        query = "SELECT * FROM clinical_sickness WHERE patient_id = ?"
        print(f"Debug - SQL Query: {query}")
        print(f"Debug - Parameters: patient_id = {patient_id}")
        
        c.execute(query, (patient_id,))
        
        result = c.fetchone()
        print("Debug - Raw SQL result:", result)
        
        if result:
            # Convert to dictionary
            info = dict(result)
            print("Debug - Initial dict:", info)
            
            # Convert boolean values to Yes/No strings
            boolean_fields = [
                'heart_disease', 'heart_surgery', 'heart_attack', 
                'chest_pain', 'shortness_of_breath', 'heart_murmur',
                'high_blood_pressure', 'heart_defect', 'rheumatic_fever',
                'arthritis', 'artificial_joint', 'stomach_problems',
                'kidney_disease', 'tuberculosis', 'persistent_cough',
                'asthma', 'breathing_problems', 'sinus_problems',
                'diabetes', 'thyroid_disease', 'liver_disease',
                'hepatitis', 'aids_hiv', 'sexually_transmitted',
                'epilepsy', 'fainting', 'neurological_disorders',
                'bleeding_problems', 'anemia', 'blood_disease',
                'head_injury', 'eating_disorder', 'mental_health_treatment'
            ]
            
            for field in boolean_fields:
                if field in info:
                    info[field] = "Yes" if info[field] == 1 else "No"
            
            print("Debug - Processed dict with Yes/No values:", info)
        else:
            info = None
            print("Debug - No data found for patient_id:", patient_id)
        
        return info
    except sqlite3.Error as e:
        print("SQL error in get_clinical_sickness:", e)
        return None
    finally:
        conn.close()

def save_clinical_sickness(patient_id, data):
    """Save clinical sickness data for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    # Debug: Print the data being saved
    print("Debug - Saving clinical sickness data for patient_id:", patient_id)
    print("Debug - Data received:", data)
    
    # Convert string values to boolean
    boolean_fields = [
        'heart_disease', 'heart_surgery', 'heart_attack', 
        'chest_pain', 'shortness_of_breath', 'heart_murmur',
        'high_blood_pressure', 'heart_defect', 'rheumatic_fever',
        'arthritis', 'artificial_joint', 'stomach_problems',
        'kidney_disease', 'tuberculosis', 'persistent_cough',
        'asthma', 'breathing_problems', 'sinus_problems',
        'diabetes', 'thyroid_disease', 'liver_disease',
        'hepatitis', 'aids_hiv', 'sexually_transmitted',
        'epilepsy', 'fainting', 'neurological_disorders',
        'bleeding_problems', 'anemia', 'blood_disease',
        'head_injury', 'eating_disorder', 'mental_health_treatment'
    ]
    
    processed_data = {}
    for field in boolean_fields:
        value = data.get(field, 'No')
        processed_data[field] = 1 if value == 'Yes' else 0
    
    processed_data['details'] = data.get('details', '')
    
    print("Debug - Processed data:", processed_data)
    
    try:
        # Check if a record already exists for this patient
        c.execute("SELECT id FROM clinical_sickness WHERE patient_id = ?", (patient_id,))
        existing = c.fetchone()
        
        if existing:
            print("Debug - Updating existing record")
            # Update existing record
            update_query = """
                UPDATE clinical_sickness 
                SET heart_disease = ?, heart_surgery = ?, heart_attack = ?, 
                    chest_pain = ?, shortness_of_breath = ?, heart_murmur = ?,
                    high_blood_pressure = ?, heart_defect = ?, rheumatic_fever = ?,
                    arthritis = ?, artificial_joint = ?, stomach_problems = ?,
                    kidney_disease = ?, tuberculosis = ?, persistent_cough = ?,
                    asthma = ?, breathing_problems = ?, sinus_problems = ?,
                    diabetes = ?, thyroid_disease = ?, liver_disease = ?,
                    hepatitis = ?, aids_hiv = ?, sexually_transmitted = ?,
                    epilepsy = ?, fainting = ?, neurological_disorders = ?,
                    bleeding_problems = ?, anemia = ?, blood_disease = ?,
                    head_injury = ?, eating_disorder = ?, mental_health_treatment = ?,
                    details = ?
                WHERE patient_id = ?
            """
            params = tuple([processed_data[field] for field in boolean_fields] + 
                         [processed_data['details'], patient_id])
            print("Debug - Update query:", update_query)
            print("Debug - Update params:", params)
            c.execute(update_query, params)
        else:
            print("Debug - Inserting new record")
            # Insert new record
            insert_query = """
                INSERT INTO clinical_sickness 
                (patient_id, heart_disease, heart_surgery, heart_attack,
                 chest_pain, shortness_of_breath, heart_murmur,
                 high_blood_pressure, heart_defect, rheumatic_fever,
                 arthritis, artificial_joint, stomach_problems,
                 kidney_disease, tuberculosis, persistent_cough,
                 asthma, breathing_problems, sinus_problems,
                 diabetes, thyroid_disease, liver_disease,
                 hepatitis, aids_hiv, sexually_transmitted,
                 epilepsy, fainting, neurological_disorders,
                 bleeding_problems, anemia, blood_disease,
                 head_injury, eating_disorder, mental_health_treatment,
                 details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = tuple([patient_id] + [processed_data[field] for field in boolean_fields] + 
                         [processed_data['details']])
            print("Debug - Insert query:", insert_query)
            print("Debug - Insert params:", params)
            c.execute(insert_query, params)
        
        conn.commit()
        print("Debug - Changes committed successfully")
        
        # Verify the save
        c.execute("SELECT * FROM clinical_sickness WHERE patient_id = ?", (patient_id,))
        saved_data = c.fetchone()
        print("Debug - Saved data verification:", saved_data)
        
        return True
    except sqlite3.Error as e:
        print("SQL error in save_clinical_sickness:", e)
        return False
    finally:
        conn.close()

def get_vital_signs(patient_id):
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM vital_signs WHERE patient_id = ?", (patient_id,))
    
    result = c.fetchone()
    vital_signs = dict(result) if result else None
    conn.close()
    
    return vital_signs

def save_physician_info(patient_id, under_physician_care, physician_name, physician_address, 
                       physician_phone, other_physicians, other_physicians_details, 
                       last_visit_date, last_visit_purpose):
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    # Check if a record already exists for this patient
    c.execute("SELECT id FROM physician_info WHERE patient_id = ?", (patient_id,))
    existing = c.fetchone()
    
    if existing:
        # Update existing record
        c.execute(
            """UPDATE physician_info 
               SET under_physician_care = ?, physician_name = ?, physician_address = ?, 
               physician_phone = ?, other_physicians = ?, other_physicians_details = ?,
               last_visit_date = ?, last_visit_purpose = ?
               WHERE patient_id = ?""",
            (under_physician_care, physician_name, physician_address, physician_phone, 
             other_physicians, other_physicians_details, last_visit_date, last_visit_purpose, patient_id)
        )
    else:
        # Insert new record
        c.execute(
            """INSERT INTO physician_info 
               (patient_id, under_physician_care, physician_name, physician_address, 
               physician_phone, other_physicians, other_physicians_details, 
               last_visit_date, last_visit_purpose) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, under_physician_care, physician_name, physician_address, 
             physician_phone, other_physicians, other_physicians_details, 
             last_visit_date, last_visit_purpose)
        )
    
    conn.commit()
    conn.close()

def get_physician_info(patient_id):
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM physician_info WHERE patient_id = ?", (patient_id,))
    
    result = c.fetchone()
    physician_info = dict(result) if result else None
    conn.close()
    
    return physician_info

def get_female_patient_info(patient_id):
    """Get female patient specific health information"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT is_pregnant, pregnancy_week, expected_delivery_date,
               obstetrician_name, obstetrician_phone, taking_birth_control,
               is_nursing, menopause, menopause_age, hormone_replacement,
               menstrual_problems, gynecological_problems,
               last_menstrual_date, details
        FROM female_patient_info 
        WHERE patient_id = ?
    """, (patient_id,))
    
    result = c.fetchone()
    info = dict(result) if result else None
    conn.close()
    
    return info

def save_female_patient_info(patient_id, data):
    """Save female patient specific health information"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    # Check if a record already exists for this patient
    c.execute("SELECT id FROM female_patient_info WHERE patient_id = ?", (patient_id,))
    existing = c.fetchone()
    
    if existing:
        # Update existing record
        c.execute("""
            UPDATE female_patient_info 
            SET is_pregnant = ?, pregnancy_week = ?, expected_delivery_date = ?,
                obstetrician_name = ?, obstetrician_phone = ?, taking_birth_control = ?,
                is_nursing = ?, menopause = ?, menopause_age = ?, hormone_replacement = ?,
                menstrual_problems = ?, gynecological_problems = ?,
                last_menstrual_date = ?, details = ?
            WHERE patient_id = ?
        """, (
            data['is_pregnant'], 
            data.get('pregnancy_week', 0),
            data.get('expected_delivery_date', ''),
            data.get('obstetrician_name', ''),
            data.get('obstetrician_phone', ''),
            data['taking_birth_control'],
            data['is_nursing'],
            data['menopause'],
            data.get('menopause_age', 0),
            data['hormone_replacement'],
            data['menstrual_problems'],
            data['gynecological_problems'],
            data['last_menstrual_date'],
            data.get('details', ''),
            patient_id
        ))
    else:
        # Insert new record
        c.execute("""
            INSERT INTO female_patient_info 
            (patient_id, is_pregnant, pregnancy_week, expected_delivery_date,
             obstetrician_name, obstetrician_phone, taking_birth_control,
             is_nursing, menopause, menopause_age, hormone_replacement,
             menstrual_problems, gynecological_problems,
             last_menstrual_date, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            data['is_pregnant'],
            data.get('pregnancy_week', 0),
            data.get('expected_delivery_date', ''),
            data.get('obstetrician_name', ''),
            data.get('obstetrician_phone', ''),
            data['taking_birth_control'],
            data['is_nursing'],
            data['menopause'],
            data.get('menopause_age', 0),
            data['hormone_replacement'],
            data['menstrual_problems'],
            data['gynecological_problems'],
            data['last_menstrual_date'],
            data.get('details', '')
        ))
    
    conn.commit()
    conn.close()
    return True

def get_special_needs(patient_id):
    """Get special needs information for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        print(f"Debug - Getting special needs data for patient_id: {patient_id}")
        query = "SELECT * FROM special_needs WHERE patient_id = ?"
        print(f"Debug - SQL Query: {query}")
        print(f"Debug - Parameters: patient_id = {patient_id}")
        
        c.execute(query, (patient_id,))
        
        result = c.fetchone()
        print("Debug - Raw SQL result:", result)
        
        if result:
            # Convert to dictionary
            info = dict(result)
            print("Debug - Initial dict:", info)
            
            # Convert boolean values to Yes/No strings
            boolean_fields = [
                'impaired_hearing', 'impaired_sight', 'contact_lenses',
                'impaired_language', 'impaired_mental_function',
                'snores', 'wakes_choking', 'wakes_frequently',
                'daytime_tiredness', 'falls_asleep_daytime',
                'sleep_apnea_diagnosis'
            ]
            
            for field in boolean_fields:
                if field in info:
                    info[field] = "Yes" if info[field] == 1 else "No"
            
            print("Debug - Processed dict with Yes/No values:", info)
            return info
        else:
            print("Debug - No special needs data found for patient_id:", patient_id)
            return None
            
    except sqlite3.Error as e:
        print("Debug - SQL error in get_special_needs:", e)
        return None
    finally:
        conn.close()

def save_special_needs(patient_id, data):
    """Save special needs data for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    print("Debug - Saving special needs data:", data)
    
    try:
        # Convert boolean values to integers for SQLite
        boolean_fields = [
            'impaired_hearing', 'impaired_sight', 'contact_lenses',
            'impaired_language', 'impaired_mental_function',
            'snores', 'wakes_choking', 'wakes_frequently',
            'daytime_tiredness', 'falls_asleep_daytime',
            'sleep_apnea_diagnosis'
        ]
        
        # Convert True/False to 1/0 for SQLite
        for field in boolean_fields:
            if field in data:
                data[field] = 1 if data[field] else 0
        
        print("Debug - Converted data for SQLite:", data)
        
        # Check if a record already exists for this patient
        c.execute("SELECT id FROM special_needs WHERE patient_id = ?", (patient_id,))
        existing = c.fetchone()
        
        if existing:
            # Update existing record
            c.execute("""
                UPDATE special_needs 
                SET impaired_hearing = ?, impaired_sight = ?, contact_lenses = ?,
                    impaired_language = ?, impaired_mental_function = ?,
                    snores = ?, wakes_choking = ?, wakes_frequently = ?,
                    daytime_tiredness = ?, falls_asleep_daytime = ?,
                    sleep_apnea_diagnosis = ?, details = ?
                WHERE patient_id = ?
            """, (
                data['impaired_hearing'], data['impaired_sight'], data['contact_lenses'],
                data['impaired_language'], data['impaired_mental_function'],
                data['snores'], data['wakes_choking'], data['wakes_frequently'],
                data['daytime_tiredness'], data['falls_asleep_daytime'],
                data['sleep_apnea_diagnosis'], data['details'], patient_id
            ))
            print("Debug - Updated existing record")
        else:
            # Insert new record
            c.execute("""
                INSERT INTO special_needs 
                (patient_id, impaired_hearing, impaired_sight, contact_lenses,
                 impaired_language, impaired_mental_function,
                 snores, wakes_choking, wakes_frequently,
                 daytime_tiredness, falls_asleep_daytime,
                 sleep_apnea_diagnosis, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                data['impaired_hearing'], data['impaired_sight'], data['contact_lenses'],
                data['impaired_language'], data['impaired_mental_function'],
                data['snores'], data['wakes_choking'], data['wakes_frequently'],
                data['daytime_tiredness'], data['falls_asleep_daytime'],
                data['sleep_apnea_diagnosis'], data['details']
            ))
            print("Debug - Inserted new record")
        
        conn.commit()
        print("Debug - Successfully saved special needs data")
        return True
    except sqlite3.Error as e:
        print("Debug - Error saving special needs data:", e)
        return False
    finally:
        conn.close()

def recreate_clinical_sickness_table():
    """Create the clinical_sickness table if it doesn't exist"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        print("Debug - Checking if clinical_sickness table exists")
        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clinical_sickness'")
        if not c.fetchone():
            print("Debug - Creating new clinical_sickness table")
            # Create table with all required columns
            c.execute('''
            CREATE TABLE clinical_sickness (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                heart_disease BOOLEAN DEFAULT 0,
                heart_surgery BOOLEAN DEFAULT 0,
                heart_attack BOOLEAN DEFAULT 0,
                chest_pain BOOLEAN DEFAULT 0,
                shortness_of_breath BOOLEAN DEFAULT 0,
                heart_murmur BOOLEAN DEFAULT 0,
                high_blood_pressure BOOLEAN DEFAULT 0,
                heart_defect BOOLEAN DEFAULT 0,
                rheumatic_fever BOOLEAN DEFAULT 0,
                arthritis BOOLEAN DEFAULT 0,
                artificial_joint BOOLEAN DEFAULT 0,
                stomach_problems BOOLEAN DEFAULT 0,
                kidney_disease BOOLEAN DEFAULT 0,
                tuberculosis BOOLEAN DEFAULT 0,
                persistent_cough BOOLEAN DEFAULT 0,
                asthma BOOLEAN DEFAULT 0,
                breathing_problems BOOLEAN DEFAULT 0,
                sinus_problems BOOLEAN DEFAULT 0,
                diabetes BOOLEAN DEFAULT 0,
                thyroid_disease BOOLEAN DEFAULT 0,
                liver_disease BOOLEAN DEFAULT 0,
                hepatitis BOOLEAN DEFAULT 0,
                aids_hiv BOOLEAN DEFAULT 0,
                sexually_transmitted BOOLEAN DEFAULT 0,
                epilepsy BOOLEAN DEFAULT 0,
                fainting BOOLEAN DEFAULT 0,
                neurological_disorders BOOLEAN DEFAULT 0,
                bleeding_problems BOOLEAN DEFAULT 0,
                anemia BOOLEAN DEFAULT 0,
                blood_disease BOOLEAN DEFAULT 0,
                head_injury BOOLEAN DEFAULT 0,
                eating_disorder BOOLEAN DEFAULT 0,
                mental_health_treatment BOOLEAN DEFAULT 0,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id)
            )
            ''')
            print("Debug - Table created successfully")
        else:
            print("Debug - Table already exists")
        
        conn.commit()
    except sqlite3.Error as e:
        print("SQL error in recreate_clinical_sickness_table:", e)
    finally:
        conn.close()

def recreate_female_patient_info_table():
    """Create the female_patient_info table if it doesn't exist"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        print("Debug - Checking if female_patient_info table exists")
        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='female_patient_info'")
        if not c.fetchone():
            print("Debug - Creating new female_patient_info table")
            # Create table with all required columns
            c.execute('''
            CREATE TABLE female_patient_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                is_pregnant TEXT,
                pregnancy_week INTEGER,
                expected_delivery_date TEXT,
                obstetrician_name TEXT,
                obstetrician_phone TEXT,
                is_nursing TEXT,
                taking_birth_control TEXT,
                menopause TEXT,
                menopause_age INTEGER,
                hormone_replacement TEXT,
                menstrual_problems TEXT,
                gynecological_problems TEXT,
                last_menstrual_date TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id)
            )
            ''')
            print("Debug - Table created successfully")
        else:
            print("Debug - Table already exists")
        
        conn.commit()
    except sqlite3.Error as e:
        print("SQL error in recreate_female_patient_info_table:", e)
    finally:
        conn.close()

def recreate_special_needs_table():
    """Create the special_needs table if it doesn't exist"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        print("Debug - Checking if special_needs table exists")
        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='special_needs'")
        if not c.fetchone():
            print("Debug - Creating new special_needs table")
            # Create table with all required columns
            c.execute('''
                CREATE TABLE special_needs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    impaired_hearing BOOLEAN DEFAULT 0,
                    impaired_sight BOOLEAN DEFAULT 0,
                    contact_lenses BOOLEAN DEFAULT 0,
                    impaired_language BOOLEAN DEFAULT 0,
                    impaired_mental_function BOOLEAN DEFAULT 0,
                    snores BOOLEAN DEFAULT 0,
                    wakes_choking BOOLEAN DEFAULT 0,
                    wakes_frequently BOOLEAN DEFAULT 0,
                    daytime_tiredness BOOLEAN DEFAULT 0,
                    falls_asleep_daytime BOOLEAN DEFAULT 0,
                    sleep_apnea_diagnosis BOOLEAN DEFAULT 0,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients (id)
                )
            ''')
            print("Debug - Table created successfully")
        else:
            print("Debug - Table already exists")
        
        conn.commit()
    except sqlite3.Error as e:
        print("SQL error in recreate_special_needs_table:", e)
    finally:
        conn.close()

def add_patient_page():
    st.title("Add New Patient")
    
    # Back button
    st.button("Back to Dashboard", on_click=navigate_to, args=("dashboard",))
    
    # Input form
    with st.form("add_patient_form"):
        first_name = st.text_input("First Name*")
        last_name = st.text_input("Last Name*")
        gender = st.selectbox("Gender*", ["Not Specified", "Male", "Female", "Other"])
        date_of_birth = st.date_input("Date of Birth*")
        contact_number = st.text_input("Contact Number")
        email = st.text_input("Email")
        
        st.markdown("*Required fields")
        submitted = st.form_submit_button("Add Patient")
        
        if submitted:
            if first_name and last_name and date_of_birth:
                dentist_id = get_user_id(st.session_state.username)
                if add_patient(dentist_id, first_name, last_name, gender, date_of_birth, contact_number, email):
                    st.success("Patient added successfully!")
                    st.button("Return to Dashboard", on_click=navigate_to, args=("dashboard",))
                else:
                    st.error("Error adding patient. Please try again.")
            else:
                st.error("Please fill in all required fields.")

def get_dental_history(patient_id):
    """Get dental history for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        print("Debug - Getting dental history for patient_id:", patient_id)
        c.execute("SELECT * FROM dental_history WHERE patient_id = ?", (patient_id,))
        result = c.fetchone()
        print("Debug - Raw SQL result:", result)
        info = dict(result) if result else None
        print("Debug - Processed dental history data:", info)
        return info
    except sqlite3.Error as e:
        print("Error getting dental history:", e)
        return None
    finally:
        conn.close()

def save_dental_history(patient_id, data):
    """Save dental history for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        print("Debug - Saving dental history for patient_id:", patient_id)
        print("Debug - Data to save:", data)
        # Check if a record already exists
        c.execute("SELECT id FROM dental_history WHERE patient_id = ?", (patient_id,))
        existing = c.fetchone()
        print("Debug - Existing record:", existing)
        
        if existing:
            print("Debug - Updating existing record")
            # Update existing record
            c.execute("""
                UPDATE dental_history 
                SET chief_complaint = ?, present_complaint_history = ?,
                    first_dental_experience_age = ?, fears_dental_treatment = ?,
                    recent_dental_xrays = ?, prior_treatment_reasons = ?,
                    treatment_complications = ?, oral_hygiene_methods = ?,
                    bleeding_gums = ?, oral_piercings = ?,
                    family_tooth_loss_history = ?, chews_ice = ?,
                    dry_mouth = ?, dry_mouth_eating_problems = ?,
                    dry_mouth_taste_changes = ?, tooth_loss_reasons = ?,
                    anesthetic_problems = ?, removable_prosthesis_experience = ?,
                    prosthesis_fit_function = ?, specialty_care = ?,
                    recurrent_ulcers = ?, facial_injuries = ?
                WHERE patient_id = ?
            """, (
                data.get('chief_complaint', ''),
                data.get('present_complaint_history', ''),
                data.get('first_dental_experience_age', 0),
                data.get('fears_dental_treatment', False),
                data.get('recent_dental_xrays', False),
                data.get('prior_treatment_reasons', ''),
                data.get('treatment_complications', False),
                data.get('oral_hygiene_methods', ''),
                data.get('bleeding_gums', False),
                data.get('oral_piercings', False),
                data.get('family_tooth_loss_history', False),
                data.get('chews_ice', False),
                data.get('dry_mouth', False),
                data.get('dry_mouth_eating_problems', False),
                data.get('dry_mouth_taste_changes', False),
                data.get('tooth_loss_reasons', ''),
                data.get('anesthetic_problems', False),
                data.get('removable_prosthesis_experience', ''),
                data.get('prosthesis_fit_function', ''),
                data.get('specialty_care', ''),
                data.get('recurrent_ulcers', False),
                data.get('facial_injuries', False),
                patient_id
            ))
        else:
            print("Debug - Inserting new record")
            # Insert new record
            c.execute("""
                INSERT INTO dental_history 
                (patient_id, chief_complaint, present_complaint_history,
                 first_dental_experience_age, fears_dental_treatment,
                 recent_dental_xrays, prior_treatment_reasons,
                 treatment_complications, oral_hygiene_methods,
                 bleeding_gums, oral_piercings,
                 family_tooth_loss_history, chews_ice,
                 dry_mouth, dry_mouth_eating_problems,
                 dry_mouth_taste_changes, tooth_loss_reasons,
                 anesthetic_problems, removable_prosthesis_experience,
                 prosthesis_fit_function, specialty_care,
                 recurrent_ulcers, facial_injuries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                data.get('chief_complaint', ''),
                data.get('present_complaint_history', ''),
                data.get('first_dental_experience_age', 0),
                data.get('fears_dental_treatment', False),
                data.get('recent_dental_xrays', False),
                data.get('prior_treatment_reasons', ''),
                data.get('treatment_complications', False),
                data.get('oral_hygiene_methods', ''),
                data.get('bleeding_gums', False),
                data.get('oral_piercings', False),
                data.get('family_tooth_loss_history', False),
                data.get('chews_ice', False),
                data.get('dry_mouth', False),
                data.get('dry_mouth_eating_problems', False),
                data.get('dry_mouth_taste_changes', False),
                data.get('tooth_loss_reasons', ''),
                data.get('anesthetic_problems', False),
                data.get('removable_prosthesis_experience', ''),
                data.get('prosthesis_fit_function', ''),
                data.get('specialty_care', ''),
                data.get('recurrent_ulcers', False),
                data.get('facial_injuries', False)
            ))
        
        conn.commit()
        print("Debug - Successfully saved dental history")
        return True
    except sqlite3.Error as e:
        print("Error saving dental history:", e)
        print("Debug - SQL Error details:", str(e))
        return False
    finally:
        conn.close()

def get_tmd_history(patient_id):
    """Get TMD history for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        c.execute("SELECT * FROM tmd_history WHERE patient_id = ?", (patient_id,))
        result = c.fetchone()
        info = dict(result) if result else None
        return info
    except sqlite3.Error as e:
        print("Error getting TMD history:", e)
        return None
    finally:
        conn.close()

def save_tmd_history(patient_id, data):
    """Save TMD history for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        # Check if a record already exists
        c.execute("SELECT id FROM tmd_history WHERE patient_id = ?", (patient_id,))
        existing = c.fetchone()
        
        if existing:
            # Update existing record
            c.execute("""
                UPDATE tmd_history 
                SET jaw_noises = ?, jaw_neck_stiffness = ?,
                    facial_pain = ?, frequent_headaches = ?,
                    previous_tmd_treatment = ?, swallowing_difficulty = ?,
                    daytime_clenching = ?, sleep_teeth_grinding = ?,
                    mouth_opening_difficulty = ?, treatment_details = ?
                WHERE patient_id = ?
            """, (
                data.get('jaw_noises', False),
                data.get('jaw_neck_stiffness', False),
                data.get('facial_pain', False),
                data.get('frequent_headaches', False),
                data.get('previous_tmd_treatment', False),
                data.get('swallowing_difficulty', False),
                data.get('daytime_clenching', False),
                data.get('sleep_teeth_grinding', False),
                data.get('mouth_opening_difficulty', False),
                data.get('treatment_details', ''),
                patient_id
            ))
        else:
            # Insert new record
            c.execute("""
                INSERT INTO tmd_history 
                (patient_id, jaw_noises, jaw_neck_stiffness,
                 facial_pain, frequent_headaches,
                 previous_tmd_treatment, swallowing_difficulty,
                 daytime_clenching, sleep_teeth_grinding,
                 mouth_opening_difficulty, treatment_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                data.get('jaw_noises', False),
                data.get('jaw_neck_stiffness', False),
                data.get('facial_pain', False),
                data.get('frequent_headaches', False),
                data.get('previous_tmd_treatment', False),
                data.get('swallowing_difficulty', False),
                data.get('daytime_clenching', False),
                data.get('sleep_teeth_grinding', False),
                data.get('mouth_opening_difficulty', False),
                data.get('treatment_details', '')
            ))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print("Error saving TMD history:", e)
        return False
    finally:
        conn.close()

def dental_questionnaire_page(patient_id):
    """Display dental questionnaire page"""
    st.title("Dental Questionnaire")
    
    # Back button
    st.button("Back to Medical Questionnaire", on_click=navigate_to, args=("medical_questionnaire",))
    
    # Get existing data
    dental_data = get_dental_history(patient_id)
    tmd_data = get_tmd_history(patient_id)
    
    # Create tabs
    dental_tab, tmd_tab = st.tabs(["Dental History", "TMD History"])
    
    # Container for success messages
    message_placeholder = st.empty()
    
    with dental_tab:
        with st.form("dental_history_form"):
            st.subheader("Dental History")
            
            chief_complaint = st.text_area(
                "Chief Complaint",
                value=dental_data.get('chief_complaint', '') if dental_data else ''
            )
            
            present_complaint_history = st.text_area(
                "History of Present Complaint",
                value=dental_data.get('present_complaint_history', '') if dental_data else ''
            )
            
            first_dental_experience_age = st.number_input(
                "Age of 1st dental experience",
                min_value=0,
                value=dental_data.get('first_dental_experience_age', 0) if dental_data else 0
            )
            
            fears_dental_treatment = st.radio(
                "Do you fear dental treatment?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('fears_dental_treatment') else 0
            )
            
            recent_dental_xrays = st.radio(
                "Have you had dental x-rays within the last year?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('recent_dental_xrays') else 0
            )
            
            prior_treatment_reasons = st.text_area(
                "Reasons for prior dental treatment",
                value=dental_data.get('prior_treatment_reasons', '') if dental_data else ''
            )
            
            treatment_complications = st.radio(
                "Have you ever had any complications to previous dental treatment?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('treatment_complications') else 0
            )
            
            oral_hygiene_methods = st.text_area(
                "Frequency and methods of oral hygiene",
                value=dental_data.get('oral_hygiene_methods', '') if dental_data else ''
            )
            
            bleeding_gums = st.radio(
                "Do your gums bleed when you brush your teeth?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('bleeding_gums') else 0
            )
            
            oral_piercings = st.radio(
                "Do you have or have you had any oral piercings?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('oral_piercings') else 0
            )
            
            family_tooth_loss_history = st.radio(
                "Do other family members have a history of early tooth loss?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('family_tooth_loss_history') else 0
            )
            
            chews_ice = st.radio(
                "Do you chew ice?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('chews_ice') else 0
            )
            
            dry_mouth = st.radio(
                "Is your mouth often dry?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('dry_mouth') else 0
            )
            
            dry_mouth_eating_problems = st.radio(
                "Do you have problems eating, swallowing, or talking because of dry mouth?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('dry_mouth_eating_problems') else 0
            )
            
            dry_mouth_taste_changes = st.radio(
                "Have you noticed taste changes or mouth soreness because of dry mouth?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('dry_mouth_taste_changes') else 0
            )
            
            tooth_loss_reasons = st.text_area(
                "Reasons for tooth loss (if applicable)",
                value=dental_data.get('tooth_loss_reasons', '') if dental_data else ''
            )
            
            anesthetic_problems = st.radio(
                "Have you ever had a problem with a dental injection of local anesthetic?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('anesthetic_problems') else 0
            )
            
            removable_prosthesis_experience = st.text_area(
                "Removable prosthesis experience (if applicable)",
                value=dental_data.get('removable_prosthesis_experience', '') if dental_data else ''
            )
            
            prosthesis_fit_function = st.text_area(
                "Please describe fit and function of prosthesis",
                value=dental_data.get('prosthesis_fit_function', '') if dental_data else ''
            )
            
            specialty_care = st.text_area(
                "Specialty care/Reconstruction",
                value=dental_data.get('specialty_care', '') if dental_data else ''
            )
            
            recurrent_ulcers = st.radio(
                "Recurrent oral ulcers",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('recurrent_ulcers') else 0
            )
            
            facial_injuries = st.radio(
                "Past injuries to face, jaw, or teeth?",
                options=["No", "Yes"],
                index=1 if dental_data and dental_data.get('facial_injuries') else 0
            )
            
            if st.form_submit_button("Save Dental History"):
                data = {
                    'chief_complaint': chief_complaint,
                    'present_complaint_history': present_complaint_history,
                    'first_dental_experience_age': first_dental_experience_age,
                    'fears_dental_treatment': fears_dental_treatment == "Yes",
                    'recent_dental_xrays': recent_dental_xrays == "Yes",
                    'prior_treatment_reasons': prior_treatment_reasons,
                    'treatment_complications': treatment_complications == "Yes",
                    'oral_hygiene_methods': oral_hygiene_methods,
                    'bleeding_gums': bleeding_gums == "Yes",
                    'oral_piercings': oral_piercings == "Yes",
                    'family_tooth_loss_history': family_tooth_loss_history == "Yes",
                    'chews_ice': chews_ice == "Yes",
                    'dry_mouth': dry_mouth == "Yes",
                    'dry_mouth_eating_problems': dry_mouth_eating_problems == "Yes",
                    'dry_mouth_taste_changes': dry_mouth_taste_changes == "Yes",
                    'tooth_loss_reasons': tooth_loss_reasons,
                    'anesthetic_problems': anesthetic_problems == "Yes",
                    'removable_prosthesis_experience': removable_prosthesis_experience,
                    'prosthesis_fit_function': prosthesis_fit_function,
                    'specialty_care': specialty_care,
                    'recurrent_ulcers': recurrent_ulcers == "Yes",
                    'facial_injuries': facial_injuries == "Yes"
                }
                
                if save_dental_history(patient_id, data):
                    message_placeholder.success("✅ Dental history saved successfully! Your information has been updated.")
                    time.sleep(1)  # Give user time to see the message
                    st.rerun()
                else:
                    message_placeholder.error("❌ Error saving dental history. Please try again.")
    
    with tmd_tab:
        with st.form("tmd_history_form"):
            st.subheader("TMD History")
            
            jaw_noises = st.radio(
                "Are you aware of noises in the jaw joints?",
                options=["No", "Yes"],
                index=1 if tmd_data and tmd_data.get('jaw_noises') else 0
            )
            
            jaw_neck_stiffness = st.radio(
                "Do your jaws/neck regularly feel stiff, tight, or tired?",
                options=["No", "Yes"],
                index=1 if tmd_data and tmd_data.get('jaw_neck_stiffness') else 0
            )
            
            facial_pain = st.radio(
                "Do you have pain in or about the ears, temples, cheeks, or other parts of the face?",
                options=["No", "Yes"],
                index=1 if tmd_data and tmd_data.get('facial_pain') else 0
            )
            
            frequent_headaches = st.radio(
                "Do you have frequent headaches and/or neckaches?",
                options=["No", "Yes"],
                index=1 if tmd_data and tmd_data.get('frequent_headaches') else 0
            )
            
            previous_tmd_treatment = st.radio(
                "Have you previously been treated for a jaw-joint, TMJ, or TMD problem?",
                options=["No", "Yes"],
                index=1 if tmd_data and tmd_data.get('previous_tmd_treatment') else 0
            )
            
            swallowing_difficulty = st.radio(
                "Do you have difficulty swallowing?",
                options=["No", "Yes"],
                index=1 if tmd_data and tmd_data.get('swallowing_difficulty') else 0
            )
            
            daytime_clenching = st.radio(
                "Are you aware of clenching your teeth during the day?",
                options=["No", "Yes"],
                index=1 if tmd_data and tmd_data.get('daytime_clenching') else 0
            )
            
            sleep_teeth_grinding = st.radio(
                "Have you been told that you grind your teeth when asleep?",
                options=["No", "Yes"],
                index=1 if tmd_data and tmd_data.get('sleep_teeth_grinding') else 0
            )
            
            mouth_opening_difficulty = st.radio(
                "Do you have difficulty opening your mouth wide?",
                options=["No", "Yes"],
                index=1 if tmd_data and tmd_data.get('mouth_opening_difficulty') else 0
            )
            
            treatment_details = st.text_area(
                "If you've had TMD treatment, please describe (biteguard, splint, surgery, medication, etc.)",
                value=tmd_data.get('treatment_details', '') if tmd_data else ''
            )
            
            if st.form_submit_button("Save TMD History"):
                data = {
                    'jaw_noises': jaw_noises == "Yes",
                    'jaw_neck_stiffness': jaw_neck_stiffness == "Yes",
                    'facial_pain': facial_pain == "Yes",
                    'frequent_headaches': frequent_headaches == "Yes",
                    'previous_tmd_treatment': previous_tmd_treatment == "Yes",
                    'swallowing_difficulty': swallowing_difficulty == "Yes",
                    'daytime_clenching': daytime_clenching == "Yes",
                    'sleep_teeth_grinding': sleep_teeth_grinding == "Yes",
                    'mouth_opening_difficulty': mouth_opening_difficulty == "Yes",
                    'treatment_details': treatment_details
                }
                
                if save_tmd_history(patient_id, data):
                    message_placeholder.success("✅ TMD history saved successfully! Your information has been updated.")
                    time.sleep(1)  # Give user time to see the message
                    st.rerun()
                else:
                    message_placeholder.error("❌ Error saving TMD history. Please try again.")

def dental_exam_page(patient_id):
    """Display and handle the dental examination form"""
    st.title("Dental Examination")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        st.button("Back to Patient Records", key="back_to_records_btn", 
                 on_click=navigate_to, args=("patient_records",))
    with col2:
        st.button("Back to Dashboard", key="back_to_dash_btn",
                 on_click=navigate_to, args=("dashboard",))
    
    # Get patient info
    patient = get_patient(patient_id)
    if patient:
        st.header(f"Dental Examination for {patient['first_name']} {patient['last_name']}")
    
    # Get existing exam data if available
    exam_data = get_dental_exam(patient_id)
    
    # Create a placeholder for messages
    message_placeholder = st.empty()
    
    with st.form("dental_exam_form"):
        # Exam date
        exam_date = st.date_input(
            "Examination Date",
            value=datetime.strptime(exam_data.get('exam_date', date.today().strftime('%Y-%m-%d')), '%Y-%m-%d').date() if exam_data else date.today()
        )
        
        # General Appraisal
        st.subheader("General Appraisal")
        stature = st.text_input("Stature", value=exam_data.get('stature', '') if exam_data else '')
        gait = st.text_input("Gait", value=exam_data.get('gait', '') if exam_data else '')
        posture = st.text_input("Posture", value=exam_data.get('posture', '') if exam_data else '')
        
        # Neurological Examination
        st.subheader("Neurological Examination")
        col1, col2 = st.columns(2)
        with col1:
            trigeminal_nerve = st.checkbox("Trigeminal nerve abnormal", 
                value=exam_data.get('trigeminal_nerve', False) if exam_data else False)
        with col2:
            facial_nerve = st.checkbox("Facial nerve abnormal",
                value=exam_data.get('facial_nerve', False) if exam_data else False)
        
        # Upper Extremities
        st.subheader("Upper Extremities")
        col1, col2 = st.columns(2)
        with col1:
            arms_abnormal = st.checkbox("Arms abnormal",
                value=exam_data.get('arms_abnormal', False) if exam_data else False)
        with col2:
            hands_fingers_abnormal = st.checkbox("Hands & Fingers abnormal",
                value=exam_data.get('hands_fingers_abnormal', False) if exam_data else False)
        
        # Neck Examination
        st.subheader("Neck Examination")
        col1, col2 = st.columns(2)
        with col1:
            neck_muscles_abnormal = st.checkbox("Muscles abnormal",
                value=exam_data.get('neck_muscles_abnormal', False) if exam_data else False)
            thyroid_abnormal = st.checkbox("Thyroid Gland abnormal",
                value=exam_data.get('thyroid_abnormal', False) if exam_data else False)
            trachea_abnormal = st.checkbox("Trachea abnormal",
                value=exam_data.get('trachea_abnormal', False) if exam_data else False)
        with col2:
            carotid_abnormal = st.checkbox("Carotid Artery abnormal",
                value=exam_data.get('carotid_abnormal', False) if exam_data else False)
            lymph_nodes_abnormal = st.checkbox("Head & Neck Lymph Nodes abnormal",
                value=exam_data.get('lymph_nodes_abnormal', False) if exam_data else False)
        
        # Extra-oral Head Examination
        st.subheader("Extra-oral Head Examination")
        col1, col2 = st.columns(2)
        with col1:
            face_abnormal = st.checkbox("Face abnormal",
                value=exam_data.get('face_abnormal', False) if exam_data else False)
            skin_abnormal = st.checkbox("Skin abnormal",
                value=exam_data.get('skin_abnormal', False) if exam_data else False)
            scars_abnormal = st.checkbox("Scars abnormal",
                value=exam_data.get('scars_abnormal', False) if exam_data else False)
            hair_abnormal = st.checkbox("Hair abnormal",
                value=exam_data.get('hair_abnormal', False) if exam_data else False)
        with col2:
            eyes_abnormal = st.checkbox("Eyes abnormal",
                value=exam_data.get('eyes_abnormal', False) if exam_data else False)
            salivary_glands_abnormal = st.checkbox("Salivary Glands abnormal",
                value=exam_data.get('salivary_glands_abnormal', False) if exam_data else False)
            masticatory_muscles_abnormal = st.checkbox("Masticatory muscles abnormal",
                value=exam_data.get('masticatory_muscles_abnormal', False) if exam_data else False)
        
        # Intra-oral soft tissue
        st.subheader("Intra-oral Soft Tissue")
        col1, col2 = st.columns(2)
        with col1:
            lips_labial_mucosa_abnormal = st.checkbox("Lips and Labial Mucosa abnormal",
                value=exam_data.get('lips_labial_mucosa_abnormal', False) if exam_data else False)
            buccal_mucosa_abnormal = st.checkbox("Buccal Mucosa abnormal",
                value=exam_data.get('buccal_mucosa_abnormal', False) if exam_data else False)
            gingiva_abnormal = st.checkbox("Gingiva abnormal",
                value=exam_data.get('gingiva_abnormal', False) if exam_data else False)
            alveolar_process_abnormal = st.checkbox("Alveolar Process abnormal",
                value=exam_data.get('alveolar_process_abnormal', False) if exam_data else False)
            edentulous_ridges_abnormal = st.checkbox("Edentulous ridges abnormal",
                value=exam_data.get('edentulous_ridges_abnormal', False) if exam_data else False)
            floor_of_mouth_abnormal = st.checkbox("Floor of the Mouth abnormal",
                value=exam_data.get('floor_of_mouth_abnormal', False) if exam_data else False)
        with col2:
            soft_palate_abnormal = st.checkbox("Soft Palate abnormal",
                value=exam_data.get('soft_palate_abnormal', False) if exam_data else False)
            oropharynx_abnormal = st.checkbox("Oropharynx abnormal",
                value=exam_data.get('oropharynx_abnormal', False) if exam_data else False)
            hard_palate_abnormal = st.checkbox("Hard Palate abnormal",
                value=exam_data.get('hard_palate_abnormal', False) if exam_data else False)
            mucobuccal_fold_abnormal = st.checkbox("Mucobuccal Fold abnormal",
                value=exam_data.get('mucobuccal_fold_abnormal', False) if exam_data else False)
            tongue_abnormal = st.checkbox("Tongue abnormal",
                value=exam_data.get('tongue_abnormal', False) if exam_data else False)
            uvula_abnormal = st.checkbox("Uvula abnormal",
                value=exam_data.get('uvula_abnormal', False) if exam_data else False)
        
        # Tooth Examination
        st.subheader("Tooth Examination")
        col1, col2 = st.columns(2)
        with col1:
            developmental_abnormal = st.checkbox("Developmental abnormal",
                value=exam_data.get('developmental_abnormal', False) if exam_data else False)
            size_abnormal = st.checkbox("Size abnormal",
                value=exam_data.get('size_abnormal', False) if exam_data else False)
            color_abnormal = st.checkbox("Color abnormal",
                value=exam_data.get('color_abnormal', False) if exam_data else False)
            shape_abnormal = st.checkbox("Shape abnormal",
                value=exam_data.get('shape_abnormal', False) if exam_data else False)
            number_abnormal = st.checkbox("Number abnormal",
                value=exam_data.get('number_abnormal', False) if exam_data else False)
        with col2:
            hypoplasia_present = st.checkbox("Hypoplasia present",
                value=exam_data.get('hypoplasia_present', False) if exam_data else False)
            hypomaturation_present = st.checkbox("Hypomaturation present",
                value=exam_data.get('hypomaturation_present', False) if exam_data else False)
            intrinsic_stain_present = st.checkbox("Intrinsic Stain present",
                value=exam_data.get('intrinsic_stain_present', False) if exam_data else False)
            abrasion_present = st.checkbox("Abrasion/abfraction present",
                value=exam_data.get('abrasion_present', False) if exam_data else False)
            attrition_present = st.checkbox("Attrition/bruxism present",
                value=exam_data.get('attrition_present', False) if exam_data else False)
        
        # Tooth Environmental Conditions
        st.subheader("Tooth Environmental Conditions")
        col1, col2 = st.columns(2)
        with col1:
            saliva_quality_abnormal = st.checkbox("Quality of saliva abnormal",
                value=exam_data.get('saliva_quality_abnormal', False) if exam_data else False)
            erosion_present = st.checkbox("Erosion present",
                value=exam_data.get('erosion_present', False) if exam_data else False)
        with col2:
            extrinsic_stains_present = st.checkbox("Extrinsic stains present",
                value=exam_data.get('extrinsic_stains_present', False) if exam_data else False)
            decalcification_present = st.checkbox("Decalcification present",
                value=exam_data.get('decalcification_present', False) if exam_data else False)
        
        # Orthodontic Examination
        st.subheader("Orthodontic Examination")
        col1, col2 = st.columns(2)
        with col1:
            teeth_out_of_line = st.checkbox("Teeth out of line",
                value=exam_data.get('teeth_out_of_line', False) if exam_data else False)
            midline_deviation = st.checkbox("Midline deviation",
                value=exam_data.get('midline_deviation', False) if exam_data else False)
            teeth_rotated = st.checkbox("Teeth rotated abnormally",
                value=exam_data.get('teeth_rotated', False) if exam_data else False)
            teeth_tipped = st.checkbox("Teeth tipped abnormally",
                value=exam_data.get('teeth_tipped', False) if exam_data else False)
            spaces_between_teeth = st.checkbox("Spaces between teeth",
                value=exam_data.get('spaces_between_teeth', False) if exam_data else False)
            teeth_crowded = st.checkbox("Teeth crowded",
                value=exam_data.get('teeth_crowded', False) if exam_data else False)
        with col2:
            angle_class = st.selectbox("Angle Class",
                options=["Class I", "Class II", "Class III"],
                index=["Class I", "Class II", "Class III"].index(exam_data.get('angle_class', "Class I")) if exam_data and exam_data.get('angle_class') else 0)
            malocclusion_present = st.checkbox("Malocclusion present",
                value=exam_data.get('malocclusion_present', False) if exam_data else False)
            class_ii_occlusion = st.checkbox("Class II occlusion",
                value=exam_data.get('class_ii_occlusion', False) if exam_data else False)
            class_iii_occlusion = st.checkbox("Class III occlusion",
                value=exam_data.get('class_iii_occlusion', False) if exam_data else False)
            posterior_crossbite = st.checkbox("Posterior cross-bite",
                value=exam_data.get('posterior_crossbite', False) if exam_data else False)
            anterior_posterior_crossbite = st.checkbox("Anterior and/or posterior cross-bite",
                value=exam_data.get('anterior_posterior_crossbite', False) if exam_data else False)
            overbite_present = st.checkbox("Overbite present",
                value=exam_data.get('overbite_present', False) if exam_data else False)
            open_bite_present = st.checkbox("Open bite present",
                value=exam_data.get('open_bite_present', False) if exam_data else False)
        
        # Additional Notes
        st.subheader("Additional Notes")
        notes = st.text_area("Notes", value=exam_data.get('notes', '') if exam_data else '')
        
        # Submit button with a clear label
        submit = st.form_submit_button("💾 Save Dental Examination")
        
        if submit:
            # Prepare data for saving
            data = {
                'exam_date': exam_date.strftime('%Y-%m-%d'),
                'stature': stature,
                'gait': gait,
                'posture': posture,
                'trigeminal_nerve': trigeminal_nerve,
                'facial_nerve': facial_nerve,
                'arms_abnormal': arms_abnormal,
                'hands_fingers_abnormal': hands_fingers_abnormal,
                'neck_muscles_abnormal': neck_muscles_abnormal,
                'thyroid_abnormal': thyroid_abnormal,
                'trachea_abnormal': trachea_abnormal,
                'carotid_abnormal': carotid_abnormal,
                'lymph_nodes_abnormal': lymph_nodes_abnormal,
                'face_abnormal': face_abnormal,
                'skin_abnormal': skin_abnormal,
                'scars_abnormal': scars_abnormal,
                'hair_abnormal': hair_abnormal,
                'eyes_abnormal': eyes_abnormal,
                'salivary_glands_abnormal': salivary_glands_abnormal,
                'masticatory_muscles_abnormal': masticatory_muscles_abnormal,
                'lips_labial_mucosa_abnormal': lips_labial_mucosa_abnormal,
                'buccal_mucosa_abnormal': buccal_mucosa_abnormal,
                'gingiva_abnormal': gingiva_abnormal,
                'alveolar_process_abnormal': alveolar_process_abnormal,
                'edentulous_ridges_abnormal': edentulous_ridges_abnormal,
                'floor_of_mouth_abnormal': floor_of_mouth_abnormal,
                'soft_palate_abnormal': soft_palate_abnormal,
                'oropharynx_abnormal': oropharynx_abnormal,
                'hard_palate_abnormal': hard_palate_abnormal,
                'mucobuccal_fold_abnormal': mucobuccal_fold_abnormal,
                'tongue_abnormal': tongue_abnormal,
                'uvula_abnormal': uvula_abnormal,
                'developmental_abnormal': developmental_abnormal,
                'size_abnormal': size_abnormal,
                'color_abnormal': color_abnormal,
                'shape_abnormal': shape_abnormal,
                'number_abnormal': number_abnormal,
                'hypoplasia_present': hypoplasia_present,
                'hypomaturation_present': hypomaturation_present,
                'intrinsic_stain_present': intrinsic_stain_present,
                'abrasion_present': abrasion_present,
                'attrition_present': attrition_present,
                'saliva_quality_abnormal': saliva_quality_abnormal,
                'erosion_present': erosion_present,
                'extrinsic_stains_present': extrinsic_stains_present,
                'decalcification_present': decalcification_present,
                'teeth_out_of_line': teeth_out_of_line,
                'midline_deviation': midline_deviation,
                'teeth_rotated': teeth_rotated,
                'teeth_tipped': teeth_tipped,
                'spaces_between_teeth': spaces_between_teeth,
                'teeth_crowded': teeth_crowded,
                'angle_class': angle_class,
                'malocclusion_present': malocclusion_present,
                'class_ii_occlusion': class_ii_occlusion,
                'class_iii_occlusion': class_iii_occlusion,
                'posterior_crossbite': posterior_crossbite,
                'anterior_posterior_crossbite': anterior_posterior_crossbite,
                'overbite_present': overbite_present,
                'open_bite_present': open_bite_present,
                'notes': notes
            }
            
            try:
                if save_dental_exam(patient_id, data):
                    st.success("✅ Dental examination saved successfully!")
                    # Add a short delay to show the success message
                    time.sleep(1)
                    # Navigate back to patient records
                    st.session_state.current_page = "patient_records"
                    st.rerun()
                else:
                    st.error("❌ Error saving dental examination. Please try again.")
            except Exception as e:
                st.error(f"❌ Error saving dental examination: {str(e)}")
                print(f"Debug - Save error: {str(e)}")  # For debugging

def recreate_dental_exam_table():
    """Create the dental examination table if it doesn't exist"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        # Check if table exists
        c.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='dental_exam'
        """)
        current_schema = c.fetchone()
        
        # Define expected schema
        expected_schema = """CREATE TABLE dental_exam (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            exam_date DATE NOT NULL,
            
            -- General Appraisal
            stature TEXT,
            gait TEXT,
            posture TEXT,
            
            -- Neurological Examination
            trigeminal_nerve BOOLEAN,
            facial_nerve BOOLEAN,
            
            -- Upper Extremities
            arms_abnormal BOOLEAN,
            hands_fingers_abnormal BOOLEAN,
            
            -- Neck Examination
            neck_muscles_abnormal BOOLEAN,
            thyroid_abnormal BOOLEAN,
            trachea_abnormal BOOLEAN,
            carotid_abnormal BOOLEAN,
            lymph_nodes_abnormal BOOLEAN,
            
            -- Extra-oral Head Examination
            face_abnormal BOOLEAN,
            skin_abnormal BOOLEAN,
            scars_abnormal BOOLEAN,
            hair_abnormal BOOLEAN,
            eyes_abnormal BOOLEAN,
            salivary_glands_abnormal BOOLEAN,
            masticatory_muscles_abnormal BOOLEAN,
            
            -- Intra-oral soft tissue
            lips_labial_mucosa_abnormal BOOLEAN,
            buccal_mucosa_abnormal BOOLEAN,
            gingiva_abnormal BOOLEAN,
            alveolar_process_abnormal BOOLEAN,
            edentulous_ridges_abnormal BOOLEAN,
            floor_of_mouth_abnormal BOOLEAN,
            soft_palate_abnormal BOOLEAN,
            oropharynx_abnormal BOOLEAN,
            hard_palate_abnormal BOOLEAN,
            mucobuccal_fold_abnormal BOOLEAN,
            tongue_abnormal BOOLEAN,
            uvula_abnormal BOOLEAN,
            
            -- Tooth Examination
            developmental_abnormal BOOLEAN,
            size_abnormal BOOLEAN,
            color_abnormal BOOLEAN,
            shape_abnormal BOOLEAN,
            number_abnormal BOOLEAN,
            hypoplasia_present BOOLEAN,
            hypomaturation_present BOOLEAN,
            intrinsic_stain_present BOOLEAN,
            abrasion_present BOOLEAN,
            attrition_present BOOLEAN,
            
            -- Tooth Environmental Conditions
            saliva_quality_abnormal BOOLEAN,
            erosion_present BOOLEAN,
            extrinsic_stains_present BOOLEAN,
            decalcification_present BOOLEAN,
            
            -- Orthodontic Examination
            teeth_out_of_line BOOLEAN,
            midline_deviation BOOLEAN,
            teeth_rotated BOOLEAN,
            teeth_tipped BOOLEAN,
            spaces_between_teeth BOOLEAN,
            teeth_crowded BOOLEAN,
            angle_class TEXT,
            malocclusion_present BOOLEAN,
            class_ii_occlusion BOOLEAN,
            class_iii_occlusion BOOLEAN,
            posterior_crossbite BOOLEAN,
            anterior_posterior_crossbite BOOLEAN,
            overbite_present BOOLEAN,
            open_bite_present BOOLEAN,
            
            -- Additional Notes
            notes TEXT,
            
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )"""
        
        # Only recreate if table doesn't exist
        if not current_schema:
            print("Creating dental_exam table as it doesn't exist")
            c.execute(expected_schema)
            conn.commit()
            print("Dental examination table created successfully")
            return True
            
        return True
    except sqlite3.Error as e:
        print("Error handling dental exam table:", e)
        return False
    finally:
        conn.close()

def save_dental_exam(patient_id, data):
    """Save dental examination data for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    c = conn.cursor()
    
    try:
        # Check if a record already exists for this patient and date
        c.execute("""
            SELECT id FROM dental_exam 
            WHERE patient_id = ? AND exam_date = ?
        """, (patient_id, data['exam_date']))
        existing = c.fetchone()
        
        # Convert boolean values to integers for SQLite
        processed_data = {}
        for key, value in data.items():
            if isinstance(value, bool):
                processed_data[key] = 1 if value else 0
            else:
                processed_data[key] = value
        
        if existing:
            # Update existing record
            placeholders = ', '.join(f'{k} = ?' for k in processed_data.keys())
            values = list(processed_data.values()) + [patient_id, data['exam_date']]
            
            query = f"""
                UPDATE dental_exam 
                SET {placeholders}
                WHERE patient_id = ? AND exam_date = ?
            """
            print(f"Debug - Update query: {query}")  # Debug print
            c.execute(query, values)
        else:
            # Insert new record
            columns = ', '.join(['patient_id'] + list(processed_data.keys()))
            placeholders = ', '.join(['?'] * (len(processed_data) + 1))
            values = [patient_id] + list(processed_data.values())
            
            query = f"""
                INSERT INTO dental_exam 
                ({columns})
                VALUES ({placeholders})
            """
            print(f"Debug - Insert query: {query}")  # Debug print
            c.execute(query, values)
        
        conn.commit()
        print("Debug - Save successful")  # Debug print
        return True
    except sqlite3.Error as e:
        print(f"Error saving dental exam: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error saving dental exam: {str(e)}")
        return False
    finally:
        conn.close()

def get_dental_exam(patient_id, exam_date=None):
    """Get dental examination data for a patient"""
    conn = sqlite3.connect('data/dentai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        if exam_date:
            c.execute("""
                SELECT * FROM dental_exam 
                WHERE patient_id = ? AND exam_date = ?
                ORDER BY exam_date DESC
            """, (patient_id, exam_date))
        else:
            c.execute("""
                SELECT * FROM dental_exam 
                WHERE patient_id = ?
                ORDER BY exam_date DESC
            """, (patient_id,))
        
        result = c.fetchone()
        exam_data = dict(result) if result else None
        return exam_data
    finally:
        conn.close()

def get_dental_exam_summary(patient_id):
    """Get a summary of dental examinations for a patient"""
    exam_data = get_dental_exam(patient_id)
    if not exam_data:
        return None
        
    summary = {
        "General Appraisal": {
            "Stature": exam_data['stature'] or "Not specified",
            "Gait": exam_data['gait'] or "Not specified",
            "Posture": exam_data['posture'] or "Not specified"
        },
        "Neurological Examination": {
            "Trigeminal nerve": "Abnormal" if exam_data['trigeminal_nerve'] == 1 else "Normal",
            "Facial nerve": "Abnormal" if exam_data['facial_nerve'] == 1 else "Normal"
        },
        "Upper Extremities": {
            "Arms": "Abnormal" if exam_data['arms_abnormal'] == 1 else "Normal",
            "Hands & Fingers": "Abnormal" if exam_data['hands_fingers_abnormal'] == 1 else "Normal"
        },
        "Neck Examination": {
            "Muscles": "Abnormal" if exam_data['neck_muscles_abnormal'] == 1 else "Normal",
            "Thyroid Gland": "Abnormal" if exam_data['thyroid_abnormal'] == 1 else "Normal",
            "Trachea": "Abnormal" if exam_data['trachea_abnormal'] == 1 else "Normal",
            "Carotid Artery": "Abnormal" if exam_data['carotid_abnormal'] == 1 else "Normal",
            "Lymph Nodes": "Abnormal" if exam_data['lymph_nodes_abnormal'] == 1 else "Normal"
        },
        "Extra-oral Head Examination": {
            "Face": "Abnormal" if exam_data['face_abnormal'] == 1 else "Normal",
            "Skin": "Abnormal" if exam_data['skin_abnormal'] == 1 else "Normal",
            "Scars": "Abnormal" if exam_data['scars_abnormal'] == 1 else "Normal",
            "Hair": "Abnormal" if exam_data['hair_abnormal'] == 1 else "Normal",
            "Eyes": "Abnormal" if exam_data['eyes_abnormal'] == 1 else "Normal",
            "Salivary Glands": "Abnormal" if exam_data['salivary_glands_abnormal'] == 1 else "Normal",
            "Masticatory Muscles": "Abnormal" if exam_data['masticatory_muscles_abnormal'] == 1 else "Normal"
        },
        "Intra-oral Soft Tissue": {
            "Lips and Labial Mucosa": "Abnormal" if exam_data['lips_labial_mucosa_abnormal'] == 1 else "Normal",
            "Buccal Mucosa": "Abnormal" if exam_data['buccal_mucosa_abnormal'] == 1 else "Normal",
            "Gingiva": "Abnormal" if exam_data['gingiva_abnormal'] == 1 else "Normal",
            "Alveolar Process": "Abnormal" if exam_data['alveolar_process_abnormal'] == 1 else "Normal",
            "Edentulous ridges": "Abnormal" if exam_data['edentulous_ridges_abnormal'] == 1 else "Normal",
            "Floor of the Mouth": "Abnormal" if exam_data['floor_of_mouth_abnormal'] == 1 else "Normal",
            "Soft Palate": "Abnormal" if exam_data['soft_palate_abnormal'] == 1 else "Normal",
            "Oropharynx": "Abnormal" if exam_data['oropharynx_abnormal'] == 1 else "Normal",
            "Hard Palate": "Abnormal" if exam_data['hard_palate_abnormal'] == 1 else "Normal",
            "Mucobuccal Fold": "Abnormal" if exam_data['mucobuccal_fold_abnormal'] == 1 else "Normal",
            "Tongue": "Abnormal" if exam_data['tongue_abnormal'] == 1 else "Normal",
            "Uvula": "Abnormal" if exam_data['uvula_abnormal'] == 1 else "Normal"
        },
        "Tooth Examination": {
            "Developmental": "Abnormal" if exam_data['developmental_abnormal'] == 1 else "Normal",
            "Size": "Abnormal" if exam_data['size_abnormal'] == 1 else "Normal",
            "Color": "Abnormal" if exam_data['color_abnormal'] == 1 else "Normal",
            "Shape": "Abnormal" if exam_data['shape_abnormal'] == 1 else "Normal",
            "Number": "Abnormal" if exam_data['number_abnormal'] == 1 else "Normal",
            "Hypoplasia": "Present" if exam_data['hypoplasia_present'] == 1 else "Not Present",
            "Hypomaturation": "Present" if exam_data['hypomaturation_present'] == 1 else "Not Present",
            "Intrinsic Stain": "Present" if exam_data['intrinsic_stain_present'] == 1 else "Not Present",
            "Abrasion/abfraction": "Present" if exam_data['abrasion_present'] == 1 else "Not Present",
            "Attrition/bruxism": "Present" if exam_data['attrition_present'] == 1 else "Not Present"
        },
        "Tooth Environmental Conditions": {
            "Quality of saliva": "Abnormal" if exam_data['saliva_quality_abnormal'] == 1 else "Normal",
            "Erosion": "Present" if exam_data['erosion_present'] == 1 else "Not Present",
            "Extrinsic stains": "Present" if exam_data['extrinsic_stains_present'] == 1 else "Not Present",
            "Decalcification": "Present" if exam_data['decalcification_present'] == 1 else "Not Present"
        },
        "Orthodontic Examination": {
            "Teeth out of line": "Yes" if exam_data['teeth_out_of_line'] == 1 else "No",
            "Midline deviation": "Yes" if exam_data['midline_deviation'] == 1 else "No",
            "Teeth rotated": "Yes" if exam_data['teeth_rotated'] == 1 else "No",
            "Teeth tipped": "Yes" if exam_data['teeth_tipped'] == 1 else "No",
            "Spaces between teeth": "Yes" if exam_data['spaces_between_teeth'] == 1 else "No",
            "Teeth crowded": "Yes" if exam_data['teeth_crowded'] == 1 else "No",
            "Angle Class": exam_data['angle_class'],
            "Malocclusion": "Present" if exam_data['malocclusion_present'] == 1 else "Not Present",
            "Class II occlusion": "Yes" if exam_data['class_ii_occlusion'] == 1 else "No",
            "Class III occlusion": "Yes" if exam_data['class_iii_occlusion'] == 1 else "No",
            "Posterior cross-bite": "Yes" if exam_data['posterior_crossbite'] == 1 else "No",
            "Anterior/Posterior cross-bite": "Yes" if exam_data['anterior_posterior_crossbite'] == 1 else "No",
            "Overbite": "Present" if exam_data['overbite_present'] == 1 else "Not Present",
            "Open bite": "Present" if exam_data['open_bite_present'] == 1 else "Not Present"
        }
    }
    
    if exam_data.get('notes'):
        summary["Additional Notes"] = exam_data['notes']
    
    return summary

def analyze_patient_data(patient_id):
    """Analyze patient data using OpenAI's API"""
    if not st.session_state.openai_api_key:
        return "Please set your OpenAI API key in the settings page."
    
    try:
        # Get patient information
        patient = get_patient(patient_id)
        if not patient:
            return "Patient not found."
        
        # Get medical history summary
        medical_summary = get_medical_questionnaire_summary(patient_id)
        
        # Get dental examination summary
        dental_summary = get_dental_exam_summary(patient_id)
        
        # Calculate age
        age = calculate_age(patient['date_of_birth'])
        
        # Prepare the prompt
        prompt = f"""Analyze the following patient data and provide a comprehensive dental health assessment:

Patient Information:
- Name: {patient['first_name']} {patient['last_name']}
- Age: {age}
- Gender: {patient['gender']}

Medical History Summary:
{medical_summary}

Dental Examination Summary:
{dental_summary}

Please provide a detailed analysis including:
1. Key findings from medical history
2. Dental examination observations
3. Potential risk factors
4. Recommendations for treatment
5. Follow-up suggestions

Format the response in a clear, professional manner suitable for dental records."""

        # Initialize OpenAI client
        client = OpenAI(api_key=st.session_state.openai_api_key)
        
        # Generate analysis using GPT-3.5-turbo
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional dental AI assistant. Provide clear, concise, and accurate dental health assessments."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        return f"Error generating analysis: {str(e)}"

def calculate_age(date_of_birth):
    """Calculate age from date of birth"""
    try:
        dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except:
        return "Unknown"

def settings_page():
    """Settings page for the application"""
    st.title("Settings")
    
    # Add Back to Dashboard button
    if st.button("⬅️ Back to Dashboard", key="settings_back_btn"):
        st.session_state.current_page = "dashboard"
        st.rerun()
    
    st.markdown("---")  # Add a separator line
    
    # Email Settings
    st.subheader("Email Settings")
    
    # Initialize email settings in session state if not present
    if 'email_settings' not in st.session_state:
        st.session_state.email_settings = {
            'sender_email': '',
            'smtp_server': '',
            'smtp_port': '',
            'smtp_username': '',
            'smtp_password': ''
        }
    
    # Email configuration form
    with st.form("email_settings_form"):
        st.write("Configure email settings for sending clinical records")
        sender_email = st.text_input("Sender Email", value=st.session_state.email_settings['sender_email'])
        smtp_server = st.text_input("SMTP Server", value=st.session_state.email_settings['smtp_server'])
        smtp_port = st.text_input("SMTP Port", value=st.session_state.email_settings['smtp_port'])
        smtp_username = st.text_input("SMTP Username", value=st.session_state.email_settings['smtp_username'])
        smtp_password = st.text_input("SMTP Password", type="password", value=st.session_state.email_settings['smtp_password'])
        
        submitted = st.form_submit_button("Save Email Settings")
        
        if submitted:
            st.session_state.email_settings = {
                'sender_email': sender_email,
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'smtp_username': smtp_username,
                'smtp_password': smtp_password
            }
            st.success("Email settings saved successfully!")

def get_latest_ai_report(patient_id):
    """Get the most recent AI report for a patient"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''SELECT report_text, generated_date 
                    FROM ai_reports 
                    WHERE patient_id = ? 
                    ORDER BY generated_date DESC 
                    LIMIT 1''', (patient_id,))
        result = c.fetchone()
        if result:
            return result[0], result[1]
        return None, None
    except sqlite3.Error as e:
        print(f"Error retrieving AI report: {e}")
        return None, None
    finally:
        conn.close()

def get_all_ai_reports(patient_id):
    """Get all AI reports for a patient"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''SELECT report_text, generated_date 
                    FROM ai_reports 
                    WHERE patient_id = ? 
                    ORDER BY generated_date DESC''', (patient_id,))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"Error retrieving AI reports: {e}")
        return []
    finally:
        conn.close()

def recreate_ai_reports_table():
    """Create the AI reports table if it doesn't exist"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_reports'")
        if c.fetchone() is None:
            c.execute('''CREATE TABLE ai_reports
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         patient_id INTEGER NOT NULL,
                         report_text TEXT NOT NULL,
                         generated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (patient_id) REFERENCES patients (id))''')
            conn.commit()
            print("AI reports table created successfully")
        else:
            print("AI reports table already exists")
    except sqlite3.Error as e:
        print(f"Error creating AI reports table: {e}")
    finally:
        conn.close()

def save_ai_report(patient_id, report_text):
    """Save an AI-generated report to the database"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        # First verify the patient exists
        c.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
        if not c.fetchone():
            print(f"Error: Patient with ID {patient_id} not found")
            return False
            
        c.execute('''INSERT INTO ai_reports (patient_id, report_text)
                    VALUES (?, ?)''', (patient_id, report_text))
        conn.commit()
        print(f"Successfully saved AI report for patient {patient_id}")
        return True
    except sqlite3.Error as e:
        print(f"Error saving AI report: {e}")
        return False
    finally:
        conn.close()

def save_clinical_conversation(patient_id, conversation_text, audio_file_path, ai_analysis, clinical_record):
    """Save a clinical conversation and its analysis"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO clinical_conversations 
                    (patient_id, conversation_text, audio_file_path, ai_analysis, clinical_record, end_time)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                 (patient_id, conversation_text, audio_file_path, ai_analysis, clinical_record))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error saving clinical conversation: {e}")
        return False
    finally:
        conn.close()

def get_clinical_conversations(patient_id):
    """Get all clinical conversations for a patient"""
    conn = sqlite3.connect('data/dental.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        c.execute('''SELECT * FROM clinical_conversations 
                    WHERE patient_id = ? 
                    ORDER BY created_at DESC''', (patient_id,))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"Error getting clinical conversations: {e}")
        return []
    finally:
        conn.close()

def analyze_clinical_conversation(conversation_text, patient_id):
    """Analyze the clinical conversation using GPT-3.5-turbo"""
    if not st.session_state.openai_api_key:
        return "Please set your OpenAI API key in the settings page."
    
    try:
        # Get patient information and previous analysis
        patient = get_patient(patient_id)
        latest_report, _ = get_latest_ai_report(patient_id)
        medical_summary = get_medical_questionnaire_summary(patient_id)
        dental_summary = get_dental_exam_summary(patient_id)
        
        # Prepare the prompt
        prompt = f"""Analyze the following clinical conversation and create a comprehensive clinical record:

Patient Information:
- Name: {patient['first_name']} {patient['last_name']}
- Age: {calculate_age(patient['date_of_birth'])}
- Gender: {patient['gender']}

Previous Medical History:
{medical_summary}

Previous Dental Examination:
{dental_summary}

Previous AI Analysis:
{latest_report if latest_report else 'No previous analysis available.'}

Clinical Conversation:
{conversation_text}

Please provide a detailed clinical record including:
1. Chief Complaint
2. Clinical Findings
3. Diagnosis
4. Treatment Plan
5. Follow-up Recommendations
6. Special Considerations
7. Additional Notes

Format the response in a clear, professional manner suitable for dental records."""

        # Initialize OpenAI client
        client = OpenAI(api_key=st.session_state.openai_api_key)
        
        # Generate analysis using GPT-3.5-turbo
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional dental AI assistant. Create detailed, accurate clinical records based on patient conversations and medical history."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error in clinical conversation analysis: {e}")
        return f"Error generating clinical record: {str(e)}"

def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI's Whisper API"""
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcription
    except Exception as e:
        print(f"Error in audio transcription: {e}")
        return None

def record_audio_chunk(filename, duration=10):
    """Record audio in chunks"""
    CHUNK = 1024
    FORMAT = pyaudio.paInt16  # Changed from paFloat32 to paInt16 for compatibility
    CHANNELS = 1
    RATE = 16000
    
    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
        
        frames = []
        start_time = time.time()
        
        while st.session_state.is_recording and (time.time() - start_time) < duration:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            except IOError as e:
                print(f"Warning: Audio buffer overflow - {e}")
                continue
        
        stream.stop_stream()
        stream.close()
        
        # Save the audio file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return filename
    
    except Exception as e:
        print(f"Error recording audio: {e}")
        return None
    finally:
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

def clinical_interaction_page(patient_id):
    """Page for real-time clinical interaction with AI"""
    st.title("AI Clinical Interaction")
    
    # Get patient information
    patient = get_patient(patient_id)
    if not patient:
        st.error("Patient not found.")
        if st.button("⬅️ Back to Patient Records"):
            st.session_state.current_page = "patient_records"
            st.rerun()
        return
    
    # Top navigation bar
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Back to Records"):
            st.session_state.current_page = "patient_records"
            st.rerun()
    with col2:
        st.header(f"{patient['first_name']} {patient['last_name']}")
    with col3:
        if st.button("🏠 Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.markdown("---")
    
    # Initialize session state
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'conversation_text' not in st.session_state:
        st.session_state.conversation_text = ""
    if 'audio_chunks' not in st.session_state:
        st.session_state.audio_chunks = []
    if 'current_analysis' not in st.session_state:
        st.session_state.current_analysis = None
    
    # Main interaction area
    interaction_container = st.container()
    with interaction_container:
        # Status indicator
        if st.session_state.is_recording:
            st.markdown("""
                <style>
                .recording-status {
                    color: red;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 5px;
                    animation: pulse 1.5s infinite;
                }
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.5; }
                    100% { opacity: 1; }
                }
                </style>
                <div class="recording-status">🎤 Recording in Progress...</div>
                """, unsafe_allow_html=True)
        
        # Control buttons
        col1, col2 = st.columns(2)
        with col1:
            if not st.session_state.is_recording:
                if st.button("🎤 Start Audio Interaction", use_container_width=True):
                    st.session_state.is_recording = True
                    st.session_state.conversation_text = ""
                    st.session_state.audio_chunks = []
                    st.session_state.current_analysis = None
                    st.rerun()
        with col2:
            if st.session_state.is_recording:
                if st.button("⏹️ Stop Interaction", use_container_width=True):
                    st.session_state.is_recording = False
                    st.success("Recording stopped. Processing conversation...")
                    
                    # Combine all audio chunks
                    if st.session_state.audio_chunks:
                        final_audio_path = f"data/audio/final_{patient_id}_{int(time.time())}.wav"
                        if combine_audio_files(st.session_state.audio_chunks, final_audio_path):
                            # Clean up chunks
                            for chunk in st.session_state.audio_chunks:
                                try:
                                    os.remove(chunk)
                                except:
                                    pass
                            st.session_state.audio_chunks = []
                            
                            # Transcribe final audio
                            final_transcription = transcribe_audio(final_audio_path)
                            if final_transcription:
                                st.session_state.conversation_text = final_transcription
                    
                    st.rerun()
    
    # Live transcription display
    if st.session_state.is_recording:
        st.markdown("### Live Transcription")
        transcription_placeholder = st.empty()
        
        # Create audio directory if it doesn't exist
        os.makedirs('data/audio', exist_ok=True)
        
        # Record and transcribe
        chunk_filename = f"data/audio/chunk_{patient_id}_{int(time.time())}.wav"
        if record_audio_chunk(chunk_filename):
            # Transcribe the chunk
            transcription = transcribe_audio(chunk_filename)
            if transcription:
                st.session_state.conversation_text += " " + transcription
                st.session_state.audio_chunks.append(chunk_filename)
                transcription_placeholder.markdown(st.session_state.conversation_text)
        
        # Rerun to continue recording
        time.sleep(0.1)  # Small delay to prevent too frequent updates
        st.rerun()
    
    # Analysis and save options
    if not st.session_state.is_recording and st.session_state.conversation_text:
        st.markdown("### Conversation Analysis")
        
        if not st.session_state.current_analysis:
            with st.spinner("Analyzing conversation..."):
                st.session_state.current_analysis = analyze_clinical_conversation(
                    st.session_state.conversation_text,
                    patient_id
                )
        
        if st.session_state.current_analysis:
            st.markdown(st.session_state.current_analysis)
            
            # Save options
            st.markdown("### Save Options")
            save_col1, save_col2, save_col3 = st.columns(3)
            
            with save_col1:
                if st.button("💾 Save Clinical Record", use_container_width=True):
                    final_audio_path = f"data/audio/final_{patient_id}_{int(time.time())}.wav"
                    if save_clinical_conversation(
                        patient_id,
                        st.session_state.conversation_text,
                        final_audio_path,
                        "",
                        st.session_state.current_analysis
                    ):
                        st.success("✅ Clinical record saved successfully!")
                        # Clean up audio chunks
                        for chunk in st.session_state.audio_chunks:
                            try:
                                os.remove(chunk)
                            except:
                                pass
                        st.session_state.audio_chunks = []
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to save clinical record.")
            
            with save_col2:
                if st.button("📥 Export as Text", use_container_width=True):
                    try:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"data/exports/clinical_record_{patient_id}_{timestamp}.txt"
                        os.makedirs('data/exports', exist_ok=True)
                        with open(filename, 'w') as f:
                            f.write(f"Clinical Record for {patient['first_name']} {patient['last_name']}\n")
                            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                            f.write("Conversation Transcript:\n")
                            f.write(st.session_state.conversation_text)
                            f.write("\n\nAI Analysis:\n")
                            f.write(st.session_state.current_analysis)
                        st.success(f"✅ Exported to {filename}")
                    except Exception as e:
                        st.error(f"Failed to export: {str(e)}")
            
            with save_col3:
                if st.button("📋 Copy to Clipboard", use_container_width=True):
                    try:
                        st.write("Content copied to clipboard!")
                        st.info("Copy feature coming soon!")
                    except:
                        st.error("Failed to copy to clipboard.")
            
            # Add Email Delivery Option
            st.markdown("### Email Delivery")
            with st.form("email_delivery_form"):
                recipient_email = st.text_input("Recipient Email Address")
                include_transcription = st.checkbox("Include Audio Transcription", value=True)
                
                if st.form_submit_button("📧 Send Clinical Record"):
                    if recipient_email:
                        success, message = send_clinical_record_email(
                            recipient_email,
                            f"{patient['first_name']} {patient['last_name']}",
                            st.session_state.current_analysis,
                            st.session_state.conversation_text if include_transcription else None
                        )
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Please enter a recipient email address.")
        
        # Add Transcription Display and Export Section
        st.markdown("### Audio Transcription")
        st.markdown("#### Raw Transcription")
        st.text_area("Transcription", st.session_state.conversation_text, height=200)
        
        # Export transcription options
        trans_col1, trans_col2 = st.columns(2)
        with trans_col1:
            if st.button("📝 Export Transcription", key="export_transcription_btn", use_container_width=True):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"data/exports/{timestamp}_{patient['last_name']}_{patient['first_name']}_transcription.txt"
                    os.makedirs('data/exports', exist_ok=True)
                    with open(filename, 'w') as f:
                        f.write(f"Audio Transcription for {patient['first_name']} {patient['last_name']}\n")
                        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write("Transcription:\n")
                        f.write(st.session_state.conversation_text)
                    st.success(f"✅ Transcription exported to {filename}")
                except Exception as e:
                    st.error(f"Failed to export transcription: {str(e)}")
        
        with trans_col2:
            if st.button("📋 Copy Transcription", key="copy_transcription_btn", use_container_width=True):
                try:
                    st.write("Transcription copied to clipboard!")
                    st.info("Copy feature coming soon!")
                except:
                    st.error("Failed to copy transcription.")
    
    # Display previous clinical conversations
    st.markdown("---")
    st.markdown("### Previous Clinical Records")
    conversations = get_clinical_conversations(patient_id)
    
    if conversations:
        for conv in conversations:
            with st.expander(f"Clinical Record from {conv['created_at']}"):
                st.markdown(conv['clinical_record'])
                
                # Export options for previous records
                exp_col1, exp_col2 = st.columns(2)
                with exp_col1:
                    if st.button("📥 Export as PDF", key=f"pdf_{conv['id']}", use_container_width=True):
                        st.info("PDF export feature coming soon!")
                with exp_col2:
                    if st.button("📋 Copy to Clipboard", key=f"copy_{conv['id']}", use_container_width=True):
                        st.info("Copy feature coming soon!")
    else:
        st.info("No previous clinical records available.")

def save_current_ai_analysis(patient_id, analysis_text):
    """Save or update the current AI analysis for a patient"""
    conn = sqlite3.connect('data/dental.db')
    c = conn.cursor()
    
    try:
        # Use REPLACE to either insert new or update existing
        c.execute('''REPLACE INTO current_ai_analysis 
                    (patient_id, analysis_text, generated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)''',
                 (patient_id, analysis_text))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error saving current AI analysis: {e}")
        return False
    finally:
        conn.close()

def get_current_ai_analysis(patient_id):
    """Get the current AI analysis for a patient"""
    conn = sqlite3.connect('data/dental.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        c.execute('''SELECT analysis_text, generated_at 
                    FROM current_ai_analysis 
                    WHERE patient_id = ?''', (patient_id,))
        result = c.fetchone()
        if result:
            return result['analysis_text'], result['generated_at']
        return None, None
    except sqlite3.Error as e:
        print(f"Error getting current AI analysis: {e}")
        return None, None
    finally:
        conn.close()

def send_clinical_record_email(recipient_email, patient_name, clinical_record, transcription=None):
    """Send clinical record via email"""
    try:
        # Get sender email from settings
        sender_email = st.session_state.get('email_settings', {}).get('sender_email')
        smtp_server = st.session_state.get('email_settings', {}).get('smtp_server')
        smtp_port = st.session_state.get('email_settings', {}).get('smtp_port')
        smtp_username = st.session_state.get('email_settings', {}).get('smtp_username')
        smtp_password = st.session_state.get('email_settings', {}).get('smtp_password')
        
        if not all([sender_email, smtp_server, smtp_port, smtp_username, smtp_password]):
            return False, "Email settings not configured. Please configure email settings first."
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Clinical Record for {patient_name}"
        
        # Add body
        body = f"""
Dear Doctor,

Please find attached the clinical record for patient {patient_name}.

Best regards,
DentAI System
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Add clinical record as attachment
        clinical_record_attachment = MIMEApplication(clinical_record)
        clinical_record_attachment.add_header('Content-Disposition', 'attachment', 
                                            filename=f"clinical_record_{patient_name.replace(' ', '_')}.txt")
        msg.attach(clinical_record_attachment)
        
        # Add transcription if available
        if transcription:
            transcription_attachment = MIMEApplication(transcription)
            transcription_attachment.add_header('Content-Disposition', 'attachment', 
                                              filename=f"transcription_{patient_name.replace(' ', '_')}.txt")
            msg.attach(transcription_attachment)
        
        # Send email
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        return True, "Email sent successfully!"
    
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Start the application
    main()
 