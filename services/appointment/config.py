"""Appointment Service configuration — port 5001."""

import os


def env(name, default):
    """Environment override for Docker; local defaults otherwise."""
    return os.environ.get(name, default)


# --- Team parameters (the only place T appears) ---
TEAM_NUMBER = 0

CLINIC_NAME       = f"MediBook-{TEAM_NUMBER}"
BOOKING_FEE       = 20 + TEAM_NUMBER          # EGP, never covered by insurance
LOYALTY_THRESHOLD = 3 + (TEAM_NUMBER % 3)     # completed visits
LOYALTY_DISCOUNT  = 0.10                      # 10%

# --- This service ---
SERVICE_NAME = "appointment"
SERVICE_PORT = int(env("SERVICE_PORT", 5001))
SERVICE_HOST = env("SERVICE_HOST", "127.0.0.1")

# --- Database ---
DB = {
    "host": env("DB_HOST", "localhost"),
    "port": int(env("DB_PORT", 3306)),
    "user": env("DB_USER", "clinic_user"),
    "password": env("DB_PASSWORD", "choose_a_password"),
    "database": env("DB_NAME", "clinic_system"),
}

# --- Services this one calls (timeout 3s, PRD 8.4) ---
PATIENT_URL      = env("PATIENT_URL", "http://localhost:5004")
DOCTOR_URL       = env("DOCTOR_URL", "http://localhost:5002")
BILLING_URL      = env("BILLING_URL", "http://localhost:5003")
NOTIFICATION_URL = env("NOTIFICATION_URL", "http://localhost:5005")

HTTP_TIMEOUT = 3
