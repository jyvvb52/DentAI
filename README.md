# DentAI - Dental AI Assistant

DentAI is a prototype web application designed to help dentists manage patient records.

## Features

- User authentication (signup/login)
- Invitation code system for controlled user registration
- Patient management
- Chronological patient record tracking
- Simple and intuitive interface
- Patient questionnaire system
- Record editing capabilities
- Comprehensive medical questionnaire

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:

```bash
streamlit run DentAI.py
```

2. Open your web browser and navigate to the URL displayed in the terminal (typically http://localhost:8501)

3. Log in with the default admin account:
   - Username: admin
   - Password: admin123

4. Generate invitation codes to allow new users to register

5. Share the invitation codes with dentists who need access to the system

6. New users can register using the invitation code

7. Start managing your patients and their records!

## Project Structure

- `DentAI.py`: Main application file
- `data/dentai.db`: SQLite database (created automatically on first run)
- `requirements.txt`: List of required Python packages

## Invitation Code System

DentAI uses an invitation code system to control user registration:

1. **Admin Access**
   - The system creates a default admin user on first run
   - Admin credentials: username: `admin`, password: `admin123`
   - It's recommended to change the admin password after first login using the "Change Password" option in the sidebar
   - Only the administrator can generate new invitation codes

2. **Managing Invitation Codes**
   - Only administrators can generate new invitation codes from the "Manage Invitation Codes" page
   - Each code can be used only once
   - The system tracks which codes have been used and by whom
   - Regular users can view their own invitation code usage history

3. **User Registration**
   - New users must provide a valid invitation code to register
   - Once used, an invitation code cannot be used again
   - This ensures that only authorized individuals can access the system
   - Contact the administrator to obtain an invitation code

## Patient Questionnaire

The current implementation includes a simple questionnaire with one question:
- "What brings you here today?"

This can be expanded in the future to include a more comprehensive set of questions.

## Medical Questionnaire

The medical questionnaire includes seven main sections:

1. **Travel & Health Screening**
   - Travel history outside the US
   - Travel to specific African countries
   - Contact with sick individuals
   - Current symptoms
   - Automatic alert system for potential health risks

2. **Vital Signs**
   - Blood pressure
   - Pulse & rhythm
   - Height and weight
   - BMI calculation
   - Temperature
   - Respiration

3. **Physician Information**
   - Current physician details
   - Medical history
   - Previous physician visits
   - Purpose of last medical visit

4. **Allergies**
   - Analgesics or pain medications
   - Antibiotics (e.g., Penicillin, Erythromycin)
   - Latex or rubber products
   - Metals
   - Dental materials (e.g., resins, nickel, amalgam)
   - Other allergies
   - Vaccination status

5. **Hospitalization History**
   - Past hospitalizations
   - Surgical history
   - Reactions to anesthetics or medications
   - Blood transfusions
   - Current medications
   - Tobacco use
   - Cancer and treatment history
   - Injuries and other medical conditions

6. **Clinical Conditions**
   - Impaired hearing or sight
   - Contact lenses
   - Language and mental function
   - Sleep patterns and disorders
   - Sleep apnea screening

7. **Female Patient Information**
   - Pregnancy status
   - Nursing status
   - Birth control usage

## Future Enhancements

- Integration with LLM-powered AI for clinical decision support
- Image analysis for dental X-rays and scans
- Treatment planning assistance
- Patient communication tools
- Appointment scheduling
- Comprehensive patient questionnaires
- Medical history tracking

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Email Settings

To configure your email settings in the Settings page, follow these steps:

1. Click on "Settings" in the sidebar navigation menu
2. In the Settings page, you'll see an "Email Settings" section with a form
3. Fill in the following details:

For Gmail:
```
Sender Email: your.email@gmail.com
SMTP Server: smtp.gmail.com
SMTP Port: 587
SMTP Username: your.email@gmail.com
SMTP Password: [your app password]
```

For Outlook/Office 365:
```
Sender Email: your.email@outlook.com
SMTP Server: smtp.office365.com
SMTP Port: 587
SMTP Username: your.email@outlook.com
SMTP Password: your email password
```

For school email (like .edu addresses), Google Workspace (formerly G Suite) School Email:
```
Sender Email: your.name@school.edu
SMTP Server: smtp.gmail.com
SMTP Port: 587
SMTP Username: your.name@school.edu
SMTP Password: [your app password]
```

For school email (like .edu addresses), Microsoft 365 School Email:
```
Sender Email: your.name@school.edu
SMTP Server: smtp.office365.com
SMTP Port: 587
SMTP Username: your.name@school.edu
SMTP Password: your school email password
```

For Other School Email Systems:
You'll need to check with your school's IT department for the correct SMTP settings. Common configurations include:
```
Sender Email: your.name@school.edu
MTP Server: mail.school.edu
SMTP Port: 587 (or 465 for SSL)
SMTP Username: your.name@school.edu
SMTP Password: your school email password


Important notes:
1. If you're using Gmail:
   - You need to enable 2-factor authentication
   - Generate an "App Password":
     1. Go to your Google Account settings
     2. Security
     3. 2-Step Verification
     4. App passwords
     5. Generate a new app password for "Mail"
     6. Use this generated password in the SMTP Password field

2. After filling in the details:
   - Click "Save Email Settings"
   - You should see a success message

3. Once configured, you can go back to the clinical interaction page and try sending the email again.