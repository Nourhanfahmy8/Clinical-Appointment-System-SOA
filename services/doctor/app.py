"""MediBook service skeleton — see config.py for name, port and settings."""

import mysql.connector
from mysql.connector import Error
from datetime import datetime

import logging

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

import config

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# HTTP status -> error code, for anything Flask raises itself (PRD 8.2)
HTTP_ERROR_CODES = {
    400: "VALIDATION_ERROR",
    401: "INVALID_CREDENTIALS",
    404: "NOT_FOUND",
    405: "VALIDATION_ERROR",
    409: "INVALID_STATUS",
}

def error(code, message, status):
    """The project's single error shape."""
    return jsonify({"error": {"code": code, "message": message}}), status

def get_conn():
    """Open a connection to the service's own database (config.py holds the settings)."""
    return mysql.connector.connect(**config.DB)

@app.get("/api/doctors")
def list_doctors():
    specialty = request.args.get("specialty")   # optional filter from ?specialty=ENT
    conn = get_conn()
    try:
        cur = conn.cursor()
        if specialty:
            cur.execute("SELECT doctor_id, name, specialty, consultation_fee, room "
                        "FROM doctors WHERE specialty=%s", (specialty,))
        else:
            cur.execute("SELECT doctor_id, name, specialty, consultation_fee, room "
                        "FROM doctors")
        rows = cur.fetchall()
        cur.close()
        return jsonify([
            {"doctor_id": r[0], "name": r[1], "specialty": r[2],
             "consultation_fee": float(r[3]), "room": r[4]}
            for r in rows
        ])
    finally:
        conn.close()

@app.get("/api/doctors/<doctor_id>")
def get_doctor(doctor_id):
    if not doctor_id.isdigit() or int(doctor_id) <= 0:
        return error("VALIDATION_ERROR", "doctor_id must be a positive integer", 400)

    doctor_id = int(doctor_id)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT doctor_id, name, specialty, consultation_fee, room "
                    "FROM doctors WHERE doctor_id=%s", (doctor_id,))
        r = cur.fetchone()
        cur.close()
        if r is None:
            return error("NOT_FOUND", f"Doctor {doctor_id} not found", 404)
        return jsonify({"doctor_id": r[0], "name": r[1], "specialty": r[2],
                        "consultation_fee": float(r[3]), "room": r[4]})
    finally:
        conn.close()

@app.get("/api/doctors/<doctor_id>/slots")
def doctor_slots(doctor_id):
    if not doctor_id.isdigit() or int(doctor_id) <= 0:
        return error("VALIDATION_ERROR", "doctor_id must be a positive integer", 400)
    doctor_id = int(doctor_id)

    date = request.args.get("date")          # optional, YYYY-MM-DD

    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return error("VALIDATION_ERROR", "date must be YYYY-MM-DD", 400)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT doctor_id FROM doctors WHERE doctor_id=%s", (doctor_id,))
        if cur.fetchone() is None:
            cur.close()
            return error("NOT_FOUND", f"Doctor {doctor_id} not found", 404)

        if date:
            cur.execute("SELECT slot_id, doctor_id, slot_date, start_time, status "
                        "FROM slots "
                        "WHERE doctor_id=%s AND slot_date=%s AND status='AVAILABLE' "
                        "ORDER BY slot_date, start_time",
                        (doctor_id, date))
        else:
            cur.execute("SELECT slot_id, doctor_id, slot_date, start_time, status "
                        "FROM slots "
                        "WHERE doctor_id=%s AND status='AVAILABLE' "
                        "ORDER BY slot_date, start_time",
                        (doctor_id,))
        rows = cur.fetchall()
        cur.close()
        return jsonify([
            {"slot_id": r[0], "doctor_id": r[1],
             "slot_date": r[2].isoformat(),
             "start_time": (datetime.min + r[3]).strftime("%H:%M"),
             "status": r[4]}
            for r in rows
        ])
    finally:
        conn.close()

@app.get("/api/slots/<slot_id>")
def get_slot(slot_id):
    if not slot_id.isdigit() or int(slot_id) <= 0:
        return error("VALIDATION_ERROR", "slot_id must be a positive integer", 400)
    slot_id = int(slot_id)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT slot_id, doctor_id, slot_date, start_time, status "
                    "FROM slots WHERE slot_id=%s", (slot_id,))
        r = cur.fetchone()
        cur.close()
        if r is None:
            return error("NOT_FOUND", f"Slot {slot_id} not found", 404)
        return jsonify({"slot_id": r[0], "doctor_id": r[1],
                        "slot_date": r[2].isoformat(),
                        "start_time": (datetime.min + r[3]).strftime("%H:%M"),
                        "status": r[4]})
    finally:
        conn.close()

@app.put("/api/slots/<slot_id>/reserve")
def reserve_slot(slot_id):
    if not slot_id.isdigit() or int(slot_id) <= 0:
        return error("VALIDATION_ERROR", "slot_id must be a positive integer", 400)
    slot_id = int(slot_id)

    conn = get_conn()
    try:
        cur = conn.cursor()
        # ONE statement: read + write happen atomically inside the database
        cur.execute("UPDATE slots SET status='BOOKED' "
                    "WHERE slot_id=%s AND status='AVAILABLE'", (slot_id,))
        if cur.rowcount == 0:
            # Nothing changed: either no such slot (404) or already BOOKED (409)
            cur.execute("SELECT status FROM slots WHERE slot_id=%s", (slot_id,))
            row = cur.fetchone()
            cur.close()
            if row is None:
                return error("NOT_FOUND", f"Slot {slot_id} not found", 404)
            return error("SLOT_NOT_AVAILABLE", f"Slot {slot_id} is already booked", 409)
        conn.commit()
        cur.close()
        return jsonify({"slot_id": slot_id, "status": "BOOKED"})
    finally:
        conn.close()

@app.put("/api/slots/<slot_id>/release")
def release_slot(slot_id):
    if not slot_id.isdigit() or int(slot_id) <= 0:
        return error("VALIDATION_ERROR", "slot_id must be a positive integer", 400)
    slot_id = int(slot_id)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE slots SET status='AVAILABLE' "
                    "WHERE slot_id=%s AND status='BOOKED'", (slot_id,))
        if cur.rowcount == 0:
            cur.execute("SELECT status FROM slots WHERE slot_id=%s", (slot_id,))
            row = cur.fetchone()
            cur.close()
            if row is None:
                return error("NOT_FOUND", f"Slot {slot_id} not found", 404)
            return error("INVALID_STATUS", f"Slot {slot_id} is already available", 409)
        conn.commit()
        cur.close()
        return jsonify({"slot_id": slot_id, "status": "AVAILABLE"})
    finally:
        conn.close()                

@app.get("/health")
def health():
    return jsonify({"service": config.SERVICE_NAME, "status": "UP"})

@app.errorhandler(Exception)
def handle_unexpected(exc):
    """Never answer with an HTML error page (PRD ground rule 5)."""
    if isinstance(exc, HTTPException):
        code = HTTP_ERROR_CODES.get(exc.code, "INTERNAL_ERROR")
        return error(code, exc.description, exc.code)

    app.logger.exception("unhandled error")
    return error("INTERNAL_ERROR", "Unexpected server error", 500)

if __name__ == "__main__":
    # 127.0.0.1 locally; Docker sets SERVICE_HOST=0.0.0.0 so the port is reachable.
    app.run(host=config.SERVICE_HOST, port=config.SERVICE_PORT)