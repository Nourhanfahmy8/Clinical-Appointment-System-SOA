"""Billing Service configuration — port 5003."""

# --- Team parameters (the only place T appears) ---
TEAM_NUMBER = 0

CLINIC_NAME       = f"MediBook-{TEAM_NUMBER}"
BOOKING_FEE       = 20 + TEAM_NUMBER          # EGP, never covered by insurance
LOYALTY_THRESHOLD = 3 + (TEAM_NUMBER % 3)     # completed visits
LOYALTY_DISCOUNT  = 0.10                      # 10%

# --- This service ---
SERVICE_NAME = "billing"
SERVICE_PORT = 5003

# --- Database ---
DB = {
    "host": "localhost",
    "port": 3306,
    "user": "clinic_user",
    "password": "choose_a_password",
    "database": "clinic_system",
}

# --- Services this one calls (timeout 3s, PRD 8.4) ---
DOCTOR_URL  = "http://localhost:5002"
PATIENT_URL = "http://localhost:5004"

HTTP_TIMEOUT = 3
