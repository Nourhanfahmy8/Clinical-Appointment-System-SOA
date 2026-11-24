"""Doctor & Schedule Service configuration — port 5002."""

# --- Team parameters (the only place T appears) ---
TEAM_NUMBER = 0

CLINIC_NAME       = f"MediBook-{TEAM_NUMBER}"
BOOKING_FEE       = 20 + TEAM_NUMBER          # EGP, never covered by insurance
LOYALTY_THRESHOLD = 3 + (TEAM_NUMBER % 3)     # completed visits
LOYALTY_DISCOUNT  = 0.10                      # 10%

# --- This service ---
SERVICE_NAME = "doctor"
SERVICE_PORT = 5002

# --- Database ---
DB = {
    "host": "localhost",
    "port": 3306,
    "user": "clinic_user",
    "password": "choose_a_password",
    "database": "clinic_system",
}

# --- Services this one calls ---
# none: Doctor & Schedule calls no other service
