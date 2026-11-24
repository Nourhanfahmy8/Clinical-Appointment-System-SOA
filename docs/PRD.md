# PRD — MediBook Clinic Appointment System

**Product Requirements Document · IS434 Service-Oriented Architecture · Team Project**

| Field | Value |
|---|---|
| Document version | 1.0 |
| Status | Draft for team review |
| Date | 24 November 2026 |
| Course | IS434 Service-Oriented Architecture |
| Weight | 15 marks of the course grade (graded out of 100) |
| Final submission | Friday 18 December 2026, 11:59 PM |
| Live discussion | Week starting Saturday 19 December 2026 |
| Repo name | `medibook-T` |
| Team number | `T = <assigned>` (expected by Thu 26 Nov 2026) |
| Owners | 6 members — one per service + one for the JSP app (see §13) |

> **How to use this document.** Every requirement has an ID (`FR-…`), an owning role, and a phase. A requirement is "done" only when its acceptance criteria pass in Postman *and* in the browser, the owner has committed it, and a buddy has reviewed it. §19 maps every graded item to its requirement IDs.

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Problem statement and goals](#2-problem-statement-and-goals)
3. [Users and personas](#3-users-and-personas)
4. [Scope](#4-scope)
5. [Architecture](#5-architecture)
6. [Team parameters and configuration](#6-team-parameters-and-configuration)
7. [Data model](#7-data-model)
8. [Cross-cutting contracts](#8-cross-cutting-contracts)
9. [Functional requirements — Doctor & Schedule](#9-functional-requirements--doctor--schedule-5002)
10. [Functional requirements — Patient](#10-functional-requirements--patient-5004)
11. [Functional requirements — Billing](#11-functional-requirements--billing-5003)
12. [Functional requirements — Appointment](#12-functional-requirements--appointment-5001)
13. [Functional requirements — Notification](#13-functional-requirements--notification-5005)
14. [Functional requirements — Web app](#14-functional-requirements--web-app-8080)
15. [Extended features F1 and F2](#15-extended-features-f1-and-f2)
16. [End-to-end flows and failure behaviour](#16-end-to-end-flows-and-failure-behaviour)
17. [Non-functional requirements](#17-non-functional-requirements)
18. [Work breakdown and ownership](#18-work-breakdown-and-ownership)
19. [Phase plan and acceptance gates](#19-phase-plan-and-acceptance-gates)
20. [Testing and QA plan](#20-testing-and-qa-plan)
21. [Deliverables and submission checklist](#21-deliverables-and-submission-checklist)
22. [Risks and mitigations](#22-risks-and-mitigations)
23. [Open decisions](#23-open-decisions)
24. [Appendix A — Configuration templates](#appendix-a--configuration-templates)
25. [Appendix B — Database DDL and seed data](#appendix-b--database-ddl-and-seed-data)
26. [Appendix C — Error catalogue](#appendix-c--error-catalogue)
27. [Appendix D — Money test vectors](#appendix-d--money-test-vectors)
28. [Appendix E — Traceability to grading](#appendix-e--traceability-to-grading)
29. [Appendix F — Glossary](#appendix-f--glossary)

---

## 1. Executive summary

**MediBook** is a booking and billing system for a private clinic. Patients register, browse doctors, pick a free time slot, book an appointment, see the price after loyalty discount and insurance coverage, receive a confirmation, and can cancel or reschedule later. Doctors use a dashboard to mark visits complete.

The system is deliberately split into **one Java JSP web application** (UI plus API gateway) and **five Python Flask microservices**, each owning its own tables and its own port. Services communicate only over REST with JSON. The project is the practical proof that a business domain can be decomposed into independently deployable services with explicit contracts and explicit failure behaviour.

**Success looks like:** a logged-in patient books a slot in a browser, sees a correct price computed with the team's own parameters, receives console EMAIL/SMS output, and sees two log rows in MySQL. Stopping any single service produces clean `503 SERVICE_UNAVAILABLE` JSON instead of a crash, and a cancelled slot can be booked again by someone else.

**Delivery shape:** three graded phases (20 / 40 / 20 marks) plus a 20-mark individual discussion. Phase 1 is foundations, Phase 2 is the booking spine, Phase 3 is the full system with compensation, cancel/complete, reschedule and the doctor dashboard.

---

## 2. Problem statement and goals

### 2.1 Problem

A private clinic books appointments by phone. Reception cannot see which slots are free, cannot quote a price consistently (loyalty + insurance + booking fee), and has no record of what each patient was told. Double-bookings happen because two receptionists can grab the same slot.

### 2.2 Goals

| ID | Goal | Measured by |
|---|---|---|
| G1 | A patient can self-serve from registration to confirmed appointment | E2E browser run in Phase 2 |
| G2 | Price is computed identically every time, from one formula | Money test vectors pass (§Appendix D) |
| G3 | A slot can never be booked twice, even under concurrent requests | Atomic `UPDATE … WHERE status='AVAILABLE'` + concurrent test |
| G4 | The domain is split so each service owns its data | No cross-service table reads; verified by code review |
| G5 | Failure of one service degrades gracefully | 503 matrix in §16.6 |
| G6 | Every member can explain any part live | Shadow pairs + dry run before 19 Dec |

### 2.3 Non-goals

- Real email/SMS delivery — messages are printed to the console and logged.
- Payment processing, refunds, or money movement of any kind.
- Authentication beyond email + password with hashed storage (no JWT, no OAuth, no refresh tokens).
- Multi-clinic tenancy, doctor logins, or role-based access control.
- Deployment beyond localhost (no Docker requirement, no cloud hosting).
- Horizontal scaling, message queues, or eventual consistency machinery.

---

## 3. Users and personas

| Persona | Needs | Touches |
|---|---|---|
| **Patient** (primary) | Register, log in, find a doctor, see free slots, know the price before confirming, cancel or reschedule | `register`, `login`, `index`, `slots`, `book`, `confirmation`, `my-appointments` |
| **Doctor** (secondary, unauthenticated in this scope) | See today's list of patients and mark visits complete | `doctor.jsp` |
| **Receptionist / demo operator** | Run the system live, demonstrate failure handling | Postman, console output, MySQL |
| **Grader** | Verify contracts, error codes, and that each member understands the system | Postman collection, README, live Q&A |

There is **no doctor login**. `doctor.jsp` is an operational page reachable by any logged-in session; this is accepted for the scope of the course project.

---

## 4. Scope

### 4.1 In scope

- 6 deployable units: 1 JSP/Servlet app on Tomcat 10, 5 Flask services.
- 1 MySQL 8 database `clinic_system` with 6 tables, each owned by exactly one service.
- 24 REST endpoints (including `/health` on all five services and F1/F2).
- 10 JSP pages and their servlets.
- A Postman collection covering every endpoint and every listed error case.
- README with members, ownership, and run instructions.

### 4.2 Out of scope

See §2.3. Also: no DELETE endpoints (the DB user has only `SELECT, INSERT, UPDATE`), no pagination, no search beyond specialty/date filters, no i18n, no accessibility audit.

### 4.3 Deliberate simplifications

The team builds **only what the brief asks for**. The following are explicitly not built, even though they are common practice:

| Not built | Rationale |
|---|---|
| Shared Python package / helper modules (`db.py`, `errors.py`, `client.py`) | The brief specifies `app.py`, `config.py`, `requirements.txt` per service |
| Service template folder | Same reason — each service is three files |
| Mock/stub server | Not required; integration happens as services land |
| Contract files, CODEOWNERS, PR templates, issue labels | Not graded — commit history is the only required evidence |
| Docker, CI, unit-test suite | Not required; Postman plus manual E2E is the specified testing approach |
| Pagination, caching, retries | Not required; one clinic, demo-scale data |

Anything not on this list but not in §4.1 should be assumed out of scope.

---

## 5. Architecture

### 5.1 Components and ports

| Component | Technology | Port | Owns tables |
|---|---|---|---|
| Web app (UI + API gateway) | Java JSP + Jakarta Servlets, Tomcat 10.x, `java.net.http.HttpClient` | 8080 | — |
| Appointment Service | Python 3.8+ / Flask | 5001 | `appointments` |
| Doctor & Schedule Service | Flask + MySQL | 5002 | `doctors`, `slots` |
| Billing Service | Flask + MySQL | 5003 | `insurance_plans`, `invoices` |
| Patient Service | Flask + MySQL | 5004 | `patients` |
| Notification Service | Flask + MySQL | 5005 | `notification_log` |
| Database | MySQL 8.0, db `clinic_system` | 3306 | — |

### 5.2 Call graph

```
Browser
  │  (HTML forms, HttpSession holds patient_id)
  ▼
JSP app :8080 ──────────► Patient :5004
  │        ──────────► Doctor & Schedule :5002
  │        ──────────► Billing :5003
  │        ──────────► Appointment :5001
  ▼
Appointment :5001 ──────► Patient, Doctor, Billing, Notification
Billing     :5003 ──────► Doctor, Patient
Patient     :5004 ──────► Billing, Appointment
Notification:5005 ──────► Appointment, Patient, Doctor (×2), Billing (CONFIRMED only)
Doctor      :5002 ──────► (no outbound calls)
```

The JSP app is the **only** component the browser talks to. JSP pages never call Flask directly; every call goes through a servlet.

### 5.3 Cycle-safety rules (important)

The call graph contains two cycles. They are safe only if these rules hold:

1. **Appointment → Notification → Appointment.** Notification calls back `GET /api/appointments/{id}`. This works **only because** the appointment row is committed *before* Notification is called (book step 5 precedes step 7). Never move the notification call before the insert.
2. **Patient → Appointment → Patient.** `GET /api/patients/{id}/appointments` calls Appointment, which in turn may call Patient. To avoid infinite recursion, **Appointment must never call `GET /api/patients/{id}/appointments`** — only `GET /api/patients/{id}`. Enforce this in review.
3. Notification must never be called from inside a transaction that is still open on the appointment row; commit first, then notify.

### 5.4 Data ownership rule

Each service runs SQL **only** on its own tables. Cross-service data is obtained by HTTP call. There are **no foreign keys across services**; cross-service IDs are plain integers verified by calling the owning service. Reading another service's table directly scores zero for that endpoint.

---

## 6. Team parameters and configuration

These values make each team's system unique. Using another team's values scores **zero** for the affected parts. They must match everywhere: code, console output, invoices, README.

| Parameter | Formula | Example `T = 7` |
|---|---|---|
| Clinic name | `MediBook-T` | `MediBook-7` |
| Booking fee (EGP, never insured) | `20 + T` | `27.00` |
| Loyalty threshold (completed visits) | `3 + (T mod 3)` | `4` |
| Loyalty discount | `10%` | `10%` |

**Implementation rule:** store `T` in exactly **one** place per deployable unit — one constant in each service's `config.py` and one key in the JSP app's `config.properties`. Derive `CLINIC_NAME`, `BOOKING_FEE` and `LOYALTY_THRESHOLD` from `T` at startup. Never re-type `27.00` or `MediBook-7` anywhere.

**Until `T` is assigned (deadline Thu 26 Nov):** set `T = 0` and build against it. Changing it later must be a one-line edit per service with no other code changes.

---

## 7. Data model

### 7.1 Ownership matrix

| Service | Tables | Notes |
|---|---|---|
| Doctor & Schedule (5002) | `doctors`, `slots` | Only service with an intra-service FK |
| Patient (5004) | `patients` | `insurance_plan_code` is a *soft* reference to Billing |
| Appointment (5001) | `appointments` | `patient_id`, `doctor_id`, `slot_id` are plain integers |
| Billing (5003) | `insurance_plans`, `invoices` | `invoices.appointment_id` is UNIQUE |
| Notification (5005) | `notification_log` | Append-only, 2 rows per send |

### 7.2 Key constraints

- `slots` has `UNIQUE (doctor_id, slot_date, start_time)` and `FOREIGN KEY (doctor_id) → doctors`.
- `patients.email` is `UNIQUE` → duplicate registration must return `409 EMAIL_EXISTS`.
- `invoices.appointment_id` is `UNIQUE` → a second invoice for the same appointment must return `409`.
- `appointments.status` is `ENUM('CONFIRMED','CANCELLED','COMPLETED')`, default `CONFIRMED`.
- `invoices.status` is `ENUM('ISSUED','CANCELLED')`, default `ISSUED`.
- No `DELETE` is used anywhere; cancellation is a status change. The app DB user has only `SELECT, INSERT, UPDATE`.

Full DDL and seed data: [Appendix B](#appendix-b--database-ddl-and-seed-data).

### 7.3 Seed data rules

- 5 doctors, 4 slots per doctor (20 slots), 3 insurance plans — inserted by SQL.
- **Patients are never inserted by SQL.** Create at least 3 via `POST /api/patients/register` so passwords are hashed: one with no insurance, one on `BASIC`, one on `GOLD`.
- Seed one patient with `completed_visits` above the loyalty threshold to demo the discount (set via `PUT /api/patients/{id}/visits` or direct SQL as admin).

---

## 8. Cross-cutting contracts

These apply to **every** service and are graded in every phase.

### 8.1 JSON conventions

| Type | Format | Example |
|---|---|---|
| Money | JSON number, 2 decimals | `150.00` |
| Date | `YYYY-MM-DD` | `2026-12-27` |
| Time | `HH:MM` | `10:30` |
| Timestamp | ISO-8601 (where a full timestamp is needed) | `2026-11-24T10:15:00` |
| Null | JSON `null`, never `"None"` or `""` | `"insurance_plan_code": null` |

Every response body is JSON. Never return HTML, never return a Python traceback, never return `None` where a value is expected.

### 8.2 Error format (one format, everywhere)

```json
{"error": {"code": "SLOT_NOT_AVAILABLE", "message": "Slot 12 is already booked"}}
```

| Status | Code | When |
|---|---|---|
| 200 / 201 | — | OK / created |
| 400 | `VALIDATION_ERROR` | Missing or invalid input |
| 401 | `INVALID_CREDENTIALS` | Wrong email **or** password |
| 404 | `NOT_FOUND` | ID does not exist |
| 409 | `SLOT_NOT_AVAILABLE` | Slot already booked |
| 409 | `EMAIL_EXISTS` | Email already registered |
| 409 | `INVALID_STATUS` | State transition not allowed |
| 503 | `SERVICE_UNAVAILABLE` | A dependency is down or timed out |

Codes are **stable identifiers**; messages are human-readable and may include the offending value. Additional codes are allowed only if they keep the same envelope.

### 8.3 Health check

Every service exposes `GET /health`:

```json
{"service": "billing", "status": "UP"}
```

`service` is the lowercase service name. `/health` must respond even if the database is unreachable (report `"status": "UP"` for liveness; do not couple it to DB state, to keep the 503 demo clean).

### 8.4 Inter-service calls

- Use `requests` with `timeout=3` on **every** call. No exceptions.
- Any connection error, timeout, or non-2xx that means "dependency broken" → return `503 SERVICE_UNAVAILABLE`.
- A dependency's `404` is **not** a 503 — translate it to your own `404` with a clear message.
- Never let an exception escape to Flask's default HTML error page. Register a global error handler that emits the §8.2 envelope.

### 8.5 Configuration

- Each service: one `config.py` holding `T`, derived parameters, DB credentials, own port, and the URLs of services it calls.
- JSP app: one `config.properties` (or one constants class) with the same values plus the five base URLs.
- No hard-coded URL, port, or credential anywhere else.

### 8.6 Security

- Passwords hashed with `werkzeug.security.generate_password_hash`; verified with `check_password_hash`.
- `password_hash` is **never** returned by any endpoint, including error messages and logs.
- All SQL is parameterized: `cursor.execute(sql, params)`. No string concatenation, no f-strings in SQL.
- Services connect as the limited `clinic_user` (SELECT/INSERT/UPDATE only).

### 8.7 MySQL driver pitfalls (all owners must handle)

| Column type | Comes back as | Must convert with |
|---|---|---|
| `DECIMAL` | `decimal.Decimal` | `float(x)` for JSON; keep `Decimal` for math |
| `TIME` | `datetime.timedelta` | `(datetime.min + x).strftime('%H:%M')` |
| `DATE` | `datetime.date` | `x.isoformat()` |
| `TIMESTAMP` | `datetime.datetime` | `x.isoformat()` |

Call `conn.commit()` after **every** `INSERT`/`UPDATE`. Close cursors and connections (use `try/finally` or a context helper).

---

## 9. Functional requirements — Doctor & Schedule (5002)

**Owner:** O2 · **Phase:** 1 · **Calls:** nothing · **Graded:** 6 marks + 3 for DB

### FR-DOC-01 `GET /api/doctors`

- **Query:** `specialty` optional (exact match, case-insensitive recommended).
- **Returns:** `200`, JSON array of doctor objects.
- **Errors:** none.
- **Doctor object:**
  ```json
  {"doctor_id": 1, "name": "Dr. Mona Khaled", "specialty": "Cardiology",
   "consultation_fee": 600.00, "room": "A-101"}
  ```
- **Acceptance:** all 5 seeded doctors; `?specialty=ENT` returns only Dr. Hany Fawzy; unknown specialty returns `[]` (not 404).

### FR-DOC-02 `GET /api/doctors/{doctor_id}`

- **Returns:** `200` + one doctor object.
- **Errors:** `404 NOT_FOUND`.

### FR-DOC-03 `GET /api/doctors/{doctor_id}/slots`

- **Query:** `date` optional (`YYYY-MM-DD`).
- **Returns:** `200`, **only `AVAILABLE` slots**, sorted by `slot_date`, then `start_time`.
- **Errors:** `404 NOT_FOUND` if the doctor does not exist. An invalid `date` format → `400 VALIDATION_ERROR`.
- **Slot object:**
  ```json
  {"slot_id": 1, "doctor_id": 1, "slot_date": "2026-12-27",
   "start_time": "10:00", "status": "AVAILABLE"}
  ```
- **Acceptance:** a booked slot disappears from this list; `?date=2026-12-27` returns only that day.

### FR-DOC-04 `GET /api/slots/{slot_id}`

- **Returns:** `200` + slot object **including** `status` (this endpoint returns any status).
- **Errors:** `404 NOT_FOUND`.

### FR-DOC-05 `PUT /api/slots/{slot_id}/reserve`

- **Effect:** slot becomes `BOOKED`.
- **Errors:** `404 NOT_FOUND` (no such slot), `409 SLOT_NOT_AVAILABLE` (already booked).
- **Hard rule — atomic reservation.** Must be a single statement:
  ```python
  cursor.execute(
      "UPDATE slots SET status='BOOKED' WHERE slot_id=%s AND status='AVAILABLE'",
      (slot_id,))
  if cursor.rowcount == 0:
      # distinguish 404 from 409 by a follow-up SELECT of the row
  ```
  Reading the status and then updating is a **bug**: two concurrent requests both read `AVAILABLE`. This is explicitly graded.
- **Acceptance:** two simultaneous Postman requests for the same slot → exactly one `200`, one `409`; slot ends `BOOKED` once.

### FR-DOC-06 `PUT /api/slots/{slot_id}/release`

- **Effect:** slot becomes `AVAILABLE`.
- **Errors:** `404 NOT_FOUND`, `409 INVALID_STATUS` (already available).
- **Acceptance:** after cancel, the slot reappears in FR-DOC-03 and can be booked again by a different patient.

### FR-DOC-07 `GET /health`

- `{"service": "doctor", "status": "UP"}`.

### FR-DOC-08 Service layout and conventions (applies to every service)

Each service is **exactly three files**, as the brief requires. No shared packages, no helper modules, no extra tooling:

```
services/<name>/
  app.py             Flask app: routes, /health, errors
  config.py          T, derived parameters, DB settings, port, peer URLs
  requirements.txt   flask, mysql-connector-python, requests, werkzeug
```

- `config.py` is the **only** place where `T` and the derived values appear (Appendix A).
- `app.py` defines its own `/health` route and one small `error()` helper that produces the §8.2 envelope — five lines inline, not a shared module.
- Outbound calls use `requests` with `timeout=3` written inline where the call happens.
- Nothing else is added to a service folder: no `db.py`, no `errors.py`, no `client.py`.

**Project structure is created once by O1** (team leader) for all five services in Phase 1, as `/health`-only stubs. Each owner then fills in only their own `app.py`.

---

## 10. Functional requirements — Patient (5004)

**Owner:** O4 · **Phase:** 1 (main) + Phase 3 (appointments proxy) · **Calls:** Billing, Appointment · **Graded:** 6 marks

### FR-PAT-01 `POST /api/patients/register`

- **Body:** `name`, `email`, `phone`, `password`, `insurance_plan_code` (optional/nullable).
- **Returns:** `201` + patient object (**no** `password_hash`):
  ```json
  {"patient_id": 3, "name": "Sara Ali", "email": "sara@example.com",
   "phone": "01098765432", "insurance_plan_code": "GOLD", "completed_visits": 0}
  ```
- **Validation (`400 VALIDATION_ERROR`):** name non-empty; email contains `@`; phone is 11 digits starting with `01` (`^01\d{9}$`); password ≥ 6 characters.
- **If `insurance_plan_code` given:** call Billing `GET /api/billing/plans/{plan_code}`. Not found → `400 VALIDATION_ERROR`. Billing down → `503 SERVICE_UNAVAILABLE`.
- **Errors:** `400`, `409 EMAIL_EXISTS`, `503`.
- **Acceptance:** duplicate email → `409`; plan `PLATINUM` → `400`; 10-digit phone → `400`; hash stored, plaintext never stored or returned.

### FR-PAT-02 `POST /api/patients/login`

- **Body:** `email`, `password`.
- **Returns:** `200` + `{"patient_id": 3, "name": "Sara Ali"}`.
- **Errors:** `400` if a field is missing; `401 INVALID_CREDENTIALS` for wrong email **or** wrong password (same code and message — do not reveal which).
- **Acceptance:** case-insensitive email recommended; response contains no hash.

### FR-PAT-03 `GET /api/patients/{patient_id}`

- **Returns:** `200` + profile (id, name, email, phone, `insurance_plan_code`, `completed_visits`).
- **Errors:** `404 NOT_FOUND`.
- **Consumers:** Billing (plan + visits), Notification (name/email/phone), Appointment (existence check).

### FR-PAT-04 `PUT /api/patients/{patient_id}/visits`

- **Effect:** `completed_visits = completed_visits + 1` in a single `UPDATE`.
- **Returns:** `200` + updated `{"patient_id": 3, "completed_visits": 6}` (or the full profile — pick one and document it).
- **Errors:** `404 NOT_FOUND`.
- **Called by:** Appointment `complete` only. **Phase 3.**
- **Acceptance:** two consecutive completes increment by exactly 2; crossing the threshold makes the next quote apply the discount.

### FR-PAT-05 `GET /api/patients/{patient_id}/appointments`

- **Returns:** `200`:
  ```json
  {"patient": {"patient_id": 3, "name": "...", "email": "...", "phone": "...",
               "insurance_plan_code": "GOLD", "completed_visits": 5},
   "appointments": [ <appointment objects, newest first> ]}
  ```
- **Behaviour:** call Appointment `GET /api/appointments?patient_id={id}` and combine.
- **Errors:** `404` if the patient does not exist (check locally first), `503` if Appointment is down.
- **Phase:** 3.

### FR-PAT-06 `GET /health`

- `{"service": "patient", "status": "UP"}`.

---

## 11. Functional requirements — Billing (5003)

**Owner:** O3 · **Phase:** 1 (`/plans`) + 2 (rest) + 3 (cancel) · **Calls:** Doctor, Patient · **Graded:** 11 marks

### FR-BIL-01 `GET /api/billing/plans/{plan_code}`

- **Returns:** `200` + `{"plan_code": "GOLD", "plan_name": "Gold Care", "coverage_percent": 80.00, "max_coverage": 500.00}`.
- **Errors:** `404 NOT_FOUND`.
- **Phase:** 1 — needed by Patient registration validation, so it must ship before Patient's plan check.

### FR-BIL-02 `POST /api/billing/quote`

- **Body:** `patient_id`, `doctor_id`. **Saves nothing.**
- **Returns:** `200`:
  ```json
  {"patient_id": 3, "doctor_id": 1, "consultation_fee": 600.00,
   "loyalty_discount": 60.00, "insurance_plan": "GOLD",
   "insurance_covered": 432.00, "booking_fee": 27.00, "total": 135.00}
  ```
  `insurance_plan` is the plan **code** or `null` when the patient has no insurance.
- **Errors:** `400 VALIDATION_ERROR`, `404 NOT_FOUND` (patient or doctor missing), `503 SERVICE_UNAVAILABLE`.
- **Calculation (exact order, `Decimal` throughout):**
  1. `fee = doctor.consultation_fee`
  2. `loyalty_discount = fee * 0.10` if `completed_visits >= LOYALTY_THRESHOLD`, else `0`
  3. `after_discount = fee - loyalty_discount`
  4. `insurance_covered = min(after_discount * coverage_percent / 100, max_coverage)`, else `0` if no plan
  5. `booking_fee = 20 + T`
  6. `total = after_discount - insurance_covered + booking_fee`
  - Quantize to `0.01` with `ROUND_HALF_UP` after each step; the cap is applied **after** the percentage.
  - `loyalty_discount` uses `>=`, not `>`.

### FR-BIL-03 `POST /api/billing/invoices`

- **Body:** `appointment_id`, `patient_id`, `doctor_id`.
- **Effect:** same calculation, persisted with `status = 'ISSUED'`.
- **Returns:** `201` + invoice object (quote fields + `invoice_id`, `status`, `created_at`).
- **Errors:** `400`, `404`, `409` if this appointment already has an invoice, `503`.
- **Acceptance:** duplicate call → `409`; invoice row matches the quote to the piastre.

### FR-BIL-04 `GET /api/billing/invoices/{appointment_id}`

- **Returns:** `200` + invoice object.
- **Errors:** `404 NOT_FOUND`.

### FR-BIL-05 `PUT /api/billing/invoices/{appointment_id}/cancel`

- **Effect:** `status = 'CANCELLED'`.
- **Returns:** `200` + updated invoice.
- **Errors:** `404`, `409 INVALID_STATUS` if already cancelled.
- **Phase:** 3.

### FR-BIL-06 `GET /health`

- `{"service": "billing", "status": "UP"}`.

---

## 12. Functional requirements — Appointment (5001)

**Owner:** O1 · **Phase:** 2 (book + GET) + 3 (cancel, complete, reschedule, F1 query) · **Calls:** Patient, Doctor, Billing, Notification · **Graded:** 12 + 4 + share of 4

### FR-APT-01 `POST /api/appointments/book`

Follows §16.1 exactly. Body: `patient_id`, `doctor_id`, `slot_id`, `reason`.

- **Returns:** `201`:
  ```json
  {"appointment_id": 15, "status": "CONFIRMED",
   "doctor": {"doctor_id": 1, "name": "Dr. Mona Khaled", "room": "A-101"},
   "slot": {"slot_id": 2, "slot_date": "2026-12-27", "start_time": "10:30"},
   "invoice": {"total": 135.00, "insurance_covered": 432.00, "booking_fee": 27.00},
   "notification": "SENT"}
  ```
  `notification` is `"SENT"` or `"FAILED"` — never an error, never `null`.
- **Errors:** `400` (missing field, non-positive ID, slot belongs to another doctor), `404` (patient/slot not found), `409 SLOT_NOT_AVAILABLE`, `503` (dependency down, after compensation).

### FR-APT-02 `GET /api/appointments/{appointment_id}`

- **Returns:** `200` + canonical appointment object.
- **Errors:** `404 NOT_FOUND`.
- **Must not** enrich or call other services (it is called back by Notification during booking — keep it fast and dependency-free).

### FR-APT-03 `GET /api/appointments`

- **Query:** `patient_id` (required today) → that patient's appointments, newest first.
- **Returns:** `200` + JSON array of canonical appointment objects.
- **Errors:** `400 VALIDATION_ERROR` if `patient_id` is missing.
- **Phase:** 2.
- **Phase 3 extension (FR-FEA-01):** also accept `doctor_id` + `date`.

### FR-APT-04 `PUT /api/appointments/{appointment_id}/cancel`

Follows §16.2.
- **Errors:** `404`, `409 INVALID_STATUS` when not `CONFIRMED`.
- **Returns:** `200` + updated appointment.
- **Phase:** 3.

### FR-APT-05 `PUT /api/appointments/{appointment_id}/complete`

Follows §16.3.
- **Errors:** `404`, `409 INVALID_STATUS` when not `CONFIRMED`.
- **Returns:** `200` + updated appointment.
- **Phase:** 3.

### FR-APT-06 Canonical appointment object

```json
{"appointment_id": 15, "patient_id": 3, "doctor_id": 1, "slot_id": 2,
 "reason": "Chest pain", "status": "CONFIRMED",
 "created_at": "2026-11-24T10:15:00", "updated_at": "2026-11-24T10:15:00"}
```

List endpoints return this shape; display enrichment (doctor name, room, slot date/time, patient name) is the **web app's** job (§14.6), except inside the book response.

### FR-APT-07 `GET /health`

- `{"service": "appointment", "status": "UP"}`.

---

## 13. Functional requirements — Notification (5005)

**Owner:** O5 · **Phase:** 2 (main) + 3 (extra types) · **Calls:** Appointment, Patient, Doctor ×2, Billing (CONFIRMED only) · **Graded:** 9 marks

### FR-NOT-01 `POST /api/notifications/send`

- **Body:** `appointment_id`, `type` ∈ {`CONFIRMED`, `CANCELLED`, `COMPLETED`, `RESCHEDULED`}.
- **Steps (exact):**
  1. Call Appointment `GET /api/appointments/{id}` → `patient_id`, `doctor_id`, `slot_id`.
  2. Call Patient `GET /api/patients/{patient_id}` → name, email, phone.
  3. Call Doctor `GET /api/doctors/{doctor_id}` (name, room) **and** `GET /api/slots/{slot_id}` (date, time) — two calls.
  4. **Only for `CONFIRMED`:** call Billing `GET /api/billing/invoices/{appointment_id}` for the total.
  5. Print EMAIL and SMS to the console; insert **2** rows into `notification_log` (`EMAIL` + `SMS`).
- **Returns:** `201` + `{"logged": 2}`.
- **Errors:** `400 VALIDATION_ERROR` (unknown type, missing field), `404 NOT_FOUND` (appointment/patient/doctor/slot missing), `503 SERVICE_UNAVAILABLE` (any dependency down).
- **Console format:**
  ```
  EMAIL TO: sara@example.com
  Subject: [MediBook-7] Appointment #15 confirmed
  Body: Dear Sara, your appointment with Dr. Mona Khaled is on 2026-12-27 at 10:30, room A-101. Amount due: 135.00 EGP.
  SMS TO: 01098765432 | MediBook-7: Appt #15 confirmed 2026-12-27 10:30. Pay 135.00 EGP.
  ```
  The clinic name `MediBook-T` **must** come from config, not a literal. For `CANCELLED`/`COMPLETED`/`RESCHEDULED`, omit the amount or state the invoice status consistently; keep the same two-line structure.
- **Acceptance:** booking prints both messages; exactly 2 rows in `notification_log` with the right `type`; `RESCHEDULED` works after F2.

### FR-NOT-02 `GET /api/notifications`

- **Query:** `patient_id` (required).
- **Returns:** `200` + array of log rows, newest first:
  ```json
  {"notification_id": 7, "appointment_id": 15, "patient_id": 3,
   "channel": "EMAIL", "type": "CONFIRMED",
   "message": "...", "sent_at": "2026-11-24T10:15:03"}
  ```
- **Errors:** `400 VALIDATION_ERROR` if `patient_id` missing.

### FR-NOT-03 `GET /health`

- `{"service": "notification", "status": "UP"}`.

---

## 14. Functional requirements — Web app (8080)

**Owner:** O6 · **Phases:** 1 (4 pages) + 2 (2 pages) + 3 (3 pages) · **Graded:** 3 + 5 + 4

### 14.1 Pages and servlets

| Page | Shows | Servlet → service | Phase |
|---|---|---|---|
| `register.jsp` | Registration form; insurance dropdown: none, `BASIC`, `GOLD`, `STAFF` | `RegisterServlet` → Patient register | 1 |
| `login.jsp` | Email + password | `LoginServlet` → Patient login, stores `patient_id` in session | 1 |
| `index.jsp` | Doctor list + specialty filter | `DoctorServlet` → Doctor `GET /api/doctors` | 1 |
| `slots.jsp` | Free slots for one doctor, grouped by date | `SlotServlet` → Doctor `.../slots` | 1 |
| `book.jsp` | Booking summary + price breakdown + reason field | `QuoteServlet` → Billing quote | 2 |
| `confirmation.jsp` | Appointment no., doctor, room, date, time, total, notification status | `BookServlet` → Appointment book | 2 |
| `my-appointments.jsp` | Patient's appointments + Cancel / Reschedule on `CONFIRMED` | `MyAppointmentsServlet` → Patient `.../appointments`; `CancelServlet` → Appointment cancel; `RescheduleServlet` → Appointment reschedule | 3 |
| `doctor.jsp` | One doctor's appointments for one date + "Mark completed" | `DoctorDashboardServlet` → Appointment `?doctor_id&date`; `CompleteServlet` → complete | 3 |
| `error.jsp` | Friendly message from the service's `error.message` | used by every servlet | 3 |

**Derived (not in the spec table, but required to work):** `LogoutServlet` (clears session) and a `HomeServlet`/redirect for `/`. Add them; they cost minutes and prevent demo embarrassment.

### 14.2 Session rules

- `patient_id` lives in `HttpSession` after login.
- Every page except `login.jsp` and `register.jsp` redirects to `login.jsp` when there is no session.
- `doctor.jsp` also requires a session (no doctor login in scope).

### 14.3 HTTP client rules

- Use `java.net.http.HttpClient` with a **connect timeout of 3 seconds** and a request timeout of 3 seconds, mirroring the Python side.
- Always set `Content-Type: application/json` and send UTF-8.
- Read the response body as UTF-8 explicitly (`BodyHandlers.ofString(StandardCharsets.UTF_8)`), otherwise Arabic/Egyptian names break.

### 14.4 JSON rules

- Build and parse JSON with **Gson** (preferred) or `org.json`. Never `String.format`/concatenation — a name like `O"Brien` breaks hand-built JSON.
- Use DTO classes or `JsonObject`; do not pass raw strings between servlets.

### 14.5 Error handling rules

- Check the HTTP status of **every** reply.
- `4xx`/`5xx` → forward to `error.jsp` with the service's `error.message`. Never show a Java stack trace.
- Connection refused / `ConnectException` / timeout → `error.jsp` with "This service is temporarily unavailable, please try again."
- Money is rendered with 2 decimals and the currency: `135.00 EGP`.

### 14.6 Enrichment policy (design decision)

Services store IDs; the web app is the presentation layer. Therefore:

- `my-appointments.jsp` and `doctor.jsp` may call Doctor (`GET /api/slots/{id}`, `GET /api/doctors/{id}`) and Patient (`GET /api/patients/{id}`) per row to display date/time/room/patient name.
- At demo scale (≤ 20 rows) this N+1 is acceptable and keeps services decoupled.
- Cache per-request where trivial (e.g. one doctor lookup reused for all rows of that doctor).
- **Exception:** the book response and F1 endpoint already enrich server-side because the spec requires it.

### FR-WEB-01 … FR-WEB-09

| ID | Requirement | Phase | Acceptance |
|---|---|---|---|
| FR-WEB-01 | Register form posts to Patient register; success → login page | 1 | New patient row exists, password hashed |
| FR-WEB-02 | Login stores `patient_id`; wrong password shows `INVALID_CREDENTIALS` message | 1 | No session on failure; session survives navigation |
| FR-WEB-03 | Doctor list with specialty filter | 1 | Filter returns the ENT doctor only |
| FR-WEB-04 | Slots page groups by date and hides booked slots | 1 | Booked slot disappears after a booking |
| FR-WEB-05 | Book page shows full price breakdown before confirming | 2 | Breakdown equals the Postman quote |
| FR-WEB-06 | Confirmation page shows all six values incl. `notification` | 2 | Matches `201` book response |
| FR-WEB-07 | My appointments: statuses + Cancel on `CONFIRMED` | 3 | Cancel → status `CANCELLED`, slot free again |
| FR-WEB-08 | Reschedule button → pick another slot for the same doctor | 3 | Old slot released, new slot booked, invoice unchanged |
| FR-WEB-09 | Doctor dashboard: date picker, patient names, Mark completed | 3 | Complete increments `completed_visits` |
| FR-WEB-10 | `error.jsp` renders service messages and the 503 message | 3 | Stop Billing → friendly message, no stack trace |

---

## 15. Extended features F1 and F2

Both are **mandatory** in Phase 3. Graded: 4 marks total.

### 15.1 F1 — Doctor dashboard

**FR-FEA-01 `GET /api/appointments?doctor_id={id}&date=YYYY-MM-DD`** — owner O1, page owner O6.

- `appointments` has no date column, so: load the doctor's appointments, call Doctor `GET /api/slots/{slot_id}` for each, keep those whose `slot_date` equals `date`.
- **Returns:** `200` + array of canonical appointment objects (enriched with `slot` if convenient).
- **Errors:** `400` if neither `patient_id` nor the `doctor_id`+`date` pair is supplied, or if `date` is malformed; `503` if Doctor is down.
- **Acceptance:** returns exactly the appointments whose slots fall on that date; a different date returns `[]`.

**FR-FEA-02 `doctor.jsp`** — owner O6.
- Doctor picker (from `GET /api/doctors`), date picker (default today), table of that day's appointments with **patient names**, and a "Mark completed" button per `CONFIRMED` row calling `PUT /complete`.
- Patient names come from Patient `GET /api/patients/{id}` per row (§14.6).

### 15.2 F2 — Reschedule

**FR-FEA-03 `PUT /api/appointments/{appointment_id}/reschedule`** — owner O1.

- **Body:** `new_slot_id`.
- **Rules:** appointment must be `CONFIRMED`; the new slot must belong to the **same doctor**; the new slot must be `AVAILABLE`.
- **Order (do not reorder):**
  1. Validate appointment exists and is `CONFIRMED` (`404` / `409 INVALID_STATUS`).
  2. `GET /api/slots/{new_slot_id}` → must exist (`404`), same `doctor_id` (`400`), `AVAILABLE`.
  3. `PUT /api/slots/{new_slot_id}/reserve` → `409 SLOT_NOT_AVAILABLE` on race.
  4. `PUT /api/slots/{old_slot_id}/release`.
  5. `UPDATE appointments SET slot_id = new_slot_id` and commit.
  6. Notification `send` with type `RESCHEDULED`. If it fails, the reschedule still succeeds — report `"notification": "FAILED"`.
- **Invoice does not change** (same doctor, same fee).
- **Compensation:** if step 5 fails after step 3, release the new slot and keep the old one. If step 4 fails after step 3, release the new slot too (log the inconsistency).
- **Returns:** `200` + updated appointment (plus `"notification"`).
- **Errors:** `400`, `404`, `409 INVALID_STATUS`, `409 SLOT_NOT_AVAILABLE`, `503`.

**FR-FEA-04 Reschedule UI** — owner O6: button on `my-appointments.jsp` → `slots.jsp?doctor_id=X&reschedule=appointment_id` → confirm → `RescheduleServlet` → back to my-appointments.

---

## 16. End-to-end flows and failure behaviour

Failure handling is **graded**. Invariants that must never break:

- Never a `BOOKED` slot without a `CONFIRMED` appointment.
- Never a `CONFIRMED` appointment without an invoice.
- Never an HTML error page or a stack trace from any service.

### 16.1 Book — `POST /api/appointments/book`

| Step | Action | On failure |
|---|---|---|
| 1 | Validate body: 4 fields present, IDs positive integers | `400` |
| 2 | `GET /api/patients/{patient_id}` | `404` if missing; `503` if Patient down |
| 3 | `GET /api/slots/{slot_id}`; check `slot.doctor_id == doctor_id` | `404` if missing; `400` if doctor mismatch; `503` if Doctor down |
| 4 | `PUT /api/slots/{slot_id}/reserve` | `409 SLOT_NOT_AVAILABLE`; `503` if Doctor down |
| 5 | `INSERT` appointment `CONFIRMED`, **commit** | `500`; must release the slot (compensation) |
| 6 | `POST /api/billing/invoices` | **Compensate:** release slot, set appointment `CANCELLED`, return `503` |
| 7 | `POST /api/notifications/send` (`CONFIRMED`) | **Booking still succeeds**: return `201` with `"notification": "FAILED"` |
| 8 | Return `201` booking response | — |

**Notes:** the appointment must be committed before step 7 because Notification calls back `GET /api/appointments/{id}`. Compensation in step 6 is the single most graded behaviour in Phase 3 — test it by stopping Billing.

### 16.2 Cancel — `PUT /api/appointments/{id}/cancel`

| Step | Action | On failure |
|---|---|---|
| 1 | Load appointment | `404`; `409 INVALID_STATUS` if not `CONFIRMED` |
| 2 | Set `CANCELLED`, commit | — |
| 3 | `PUT /api/slots/{slot_id}/release` | Log; cancellation already stands. Prefer returning `200` with a warning field over failing the user's cancel |
| 4 | `PUT /api/billing/invoices/{id}/cancel` | Log; do not fail the cancellation |
| 5 | Notification `CANCELLED` | Failure tolerated |
| 6 | Return `200` + updated appointment | — |

**Decision to record in README:** steps 3–5 are best-effort. The status change in step 2 is the source of truth. (If Billing is down, the invoice stays `ISSUED` — acceptable and explainable.)

### 16.3 Complete — `PUT /api/appointments/{id}/complete`

| Step | Action | On failure |
|---|---|---|
| 1 | Load; must be `CONFIRMED` | `404`, `409 INVALID_STATUS` |
| 2 | Set `COMPLETED`, commit | — |
| 3 | `PUT /api/patients/{patient_id}/visits` | **This is how loyalty is earned.** If Patient is down, return `503` *before* committing the status change if possible; otherwise document the inconsistency |
| 4 | Notification `COMPLETED` | Tolerated |
| 5 | Return `200` | — |

**Recommended:** call Patient **before** committing `COMPLETED`, so a Patient outage does not silently lose a visit. Document the order you choose.

### 16.4 Reschedule

See §15.2. Order is reserve-new → release-old → update → notify.

### 16.5 Compensation invariants

| Failure point | Required end state |
|---|---|
| Billing down during book | Slot `AVAILABLE`, appointment `CANCELLED`, no invoice, `503` |
| Notification down during book | Slot `BOOKED`, appointment `CONFIRMED`, invoice `ISSUED`, `201` + `"notification":"FAILED"` |
| Doctor down during book step 3/4 | No appointment, no invoice, `503` |
| Appointment insert fails after reserve | Slot released, `500` |
| Reschedule: reserve succeeds, update fails | New slot released, old slot still `BOOKED`, appointment unchanged |

### 16.6 503 matrix (demo script — memorise this)

| Stopped service | Book | Cancel | Complete | Reschedule | Patient `/appointments` | Notification `/send` | Web pages |
|---|---|---|---|---|---|---|---|
| Billing 5003 | `503` + compensation | `200` (invoice stays `ISSUED`) | `200` | `200` | `200` | `503` | quote page → 503 message |
| Doctor 5002 | `503` | `200` (release fails, logged) | `200` | `503` | `200` | `503` | index/slots → 503 message |
| Patient 5004 | `503` | `200` | `503` | `200` | `503` | `503` | login/register → 503 message |
| Appointment 5001 | n/a | n/a | n/a | n/a | `503` | `503` | my-appointments → 503 message |
| Notification 5005 | `201` + `FAILED` | `200` | `200` | `200` + `FAILED` | `200` | `503` | unaffected |

---

## 17. Non-functional requirements

| ID | Requirement | Verification |
|---|---|---|
| NFR-01 | Every inter-service call uses `timeout=3` | Grep for `requests.get`/`post`/`put` without `timeout` |
| NFR-02 | No HTML error page ever reaches a client | Stop each service, hit each endpoint |
| NFR-03 | All SQL parameterized | Code review; grep for `%` / `+` / f-strings near `execute` |
| NFR-04 | No cross-service table access | Grep each service for table names it does not own |
| NFR-05 | No hard-coded URLs/ports/credentials | Only `config.py` / `config.properties` contain them |
| NFR-06 | Passwords hashed, never returned | Register + login + profile responses |
| NFR-07 | Money 2 decimals, `Decimal` math | Test vectors in Appendix D |
| NFR-08 | Dates `YYYY-MM-DD`, times `HH:MM` | All slot/appointment payloads |
| NFR-09 | Each service starts standalone with `python app.py` and answers `/health` | Fresh terminal per service |
| NFR-10 | Concurrent reserve is safe | Two simultaneous requests → one 200, one 409 |
| NFR-11 | Every response is valid JSON | Postman "Pretty" + `jq` |
| NFR-12 | Code is explainable by its owner under questioning | Dry run with shadow partner |

---

## 18. Work breakdown and ownership

### 18.1 Primary ownership (as chosen: one owner per service + one for the JSP app)

| Role | Member | Primary component | Graded items owned | Side duties |
|---|---|---|---|---|
| **O1** | Ziad *(leader)* | Appointment Service (5001) | Book 12, cancel+complete 4, compensation+503 5, F2 endpoint, F1 query endpoint | Project structure: folders + `config.py`/`app.py` skeletons for all six units |
| **O2** | `<name>` | Doctor & Schedule (5002) | Doctor 6, DB schema+data 3 | `database/schema.sql`, `sample_data.sql`, DB user |
| **O3** | `<name>` | Billing (5003) | Billing 11 | Money test vectors |
| **O4** | `<name>` | Patient (5004) | Patient 6 | README updates, demo script, submission zip |
| **O5** | `<name>` | Notification (5005) | Notification 9 | Postman collection owner, 503 failure matrix |
| **O6** | `<name>` | JSP web app (8080) | JSP 3+5+4, F1/F2 pages | `webapp/` setup, releases |

**Why this is fair:** O1 and O6 carry the two heaviest builds; O1's extra duty is a one-off 45-minute skeleton, O6's is its own project setup. O2 carries the lightest service but owns the whole database, which is a hard dependency for everyone. O3 and O5 sit in the middle with targeted extras.

### 18.2 Shadow pairs (protects the 20-mark individual discussion)

| Pair | Covers |
|---|---|
| O1 ↔ O2 | Appointment + Doctor (tightest coupling) |
| O3 ↔ O4 | Billing + Patient (Billing calls Patient) |
| O5 ↔ O6 | Notification + JSP (both integration-heavy) |

Shadow duties: write the partner's Postman requests, review their PRs, and be able to explain their code and modify it live. Swap one small task per phase so both have commits in both components.

### 18.3 RACI for cross-cutting artifacts

| Artifact | Accountable | Contributors |
|---|---|---|
| Project structure (folders, service stubs, `config.py`, `requirements.txt`) | O1 | — |
| `database/schema.sql`, `sample_data.sql`, DB user | O2 | O3 (plans seed), O4 (patients created via API) |
| `config.properties` + HttpClient usage in the web app | O6 | — |
| Postman collection | O5 | all (one folder each) |
| README (members, ownership, run steps) | O4 | all (own section) |
| Integration test pass + 503 matrix | O5 | O1, O6 |
| Release zips + Classroom submission | O6 | — |
| Demo script + rehearsal | O4 | all |

### 18.4 Working agreements

1. **One file, one owner per phase.** No two people edit the same `app.py` in the same week.
2. **Everyone commits their own work.** The brief states that a member with no commits is questioned in the discussion.
3. **Commit messages name the part:** `feat(doctor): atomic reserve`. Keeps the history readable at a glance.
4. **`main` always runs.** Merge only when `/health` is green on all five services.
5. **Phase-boundary check-in:** confirm each phase's gate checklist (§19) is met before the Classroom submission.

---

## 19. Phase plan and acceptance gates

### 19.1 Timeline

| Phase | Window | Deadline (11:59 PM) | Marks |
|---|---|---|---|
| Team registration | — | **Thu 26 Nov 2026** | gate |
| 1 — Foundations | 22 Nov – 2 Dec | **Wed 2 Dec 2026** | 20 (3 of 15) |
| 2 — Booking | 3 – 10 Dec | **Thu 10 Dec 2026** | 40 (6 of 15) |
| 3 — Full system | 11 – 18 Dec | **Fri 18 Dec 2026** (final) | 20 (3 of 15) |
| Discussion | 19 – 24 Dec | team slot | 20 (3 of 15) |

### 19.2 Phase 1 — Foundations (deadline Wed 2 Dec)

**Build:** database + sample data; Doctor & Schedule (all endpoints); Patient (register, login, profile, visits); Billing `GET /plans`; `/health` on all 5 services; JSP `register`, `login`, `index`, `slots`.

| Owner | Tasks | Exit criteria |
|---|---|---|
| O1 | **Project structure for all six units** (folders, `config.py` with `T`, `/health`-only `app.py`, `requirements.txt`, `webapp/`, `postman/`); then FR-APT body validation + book-flow contract for §16.1 | All five `/health` respond; contract agreed by O3/O5 |
| O2 | `schema.sql`, `sample_data.sql`, limited DB user; **all** FR-DOC | All FR-DOC pass in Postman incl. `409`/`404`; concurrent reserve test passes; 20 slots seeded |
| O3 | `insurance_plans` seed rows; FR-BIL-01 | `GOLD` and `BASIC` return 200, unknown → 404 |
| O4 | FR-PAT-01…03, FR-PAT-06 | 3 patients created via API; duplicate email → 409; hash stored |
| O5 | Notification skeleton (`/health`, `config.py`); message templates using `T` | `/health` UP; template strings reviewed by O6 |
| O6 | `webapp/` project setup, `config.properties`, HttpClient usage; FR-WEB-01…04 | Register → login → doctors → slots works in the browser |

**Gate — do not submit until all true:**
- [ ] Every Phase 1 endpoint answers correctly in Postman, **including its error cases**.
- [ ] A patient can register, log in, browse doctors, and see free slots in the browser.
- [ ] `/health` returns the right JSON on all five services.
- [ ] Every error is the §8.2 envelope; no HTML error pages.
- [ ] No hard-coded URLs; no plaintext passwords; no cross-service table reads.
- [ ] All six members have commits.

### 19.3 Phase 2 — Booking (deadline Thu 10 Dec)

**Build:** Billing (quote + invoices); Appointment book + GET endpoints; Notification service; JSP `book`, `confirmation`; Postman collection.

| Owner | Tasks | Exit criteria |
|---|---|---|
| O1 | FR-APT-01 (steps 1–8, incl. compensation), FR-APT-02, FR-APT-03 | Booking returns 201 with all six keys; Billing down → 503 and slot released |
| O2 | Postman folder for Doctor/slots; concurrency + race testing support | Collection covers all FR-DOC incl. errors |
| O3 | FR-BIL-02…04 | Quote matches Appendix D vectors for the team's `T` |
| O4 | Seed 3 test patients (none/BASIC/GOLD) + one above threshold; Patient Postman folder | Loyalty and insurance both demonstrable |
| O5 | FR-NOT-01, FR-NOT-02; Postman collection assembly | Both console messages printed; exactly 2 log rows; collection importable |
| O6 | FR-WEB-05, FR-WEB-06 | Book → confirmation in the browser with the correct total |

**Gate:**
- [ ] A logged-in patient books a slot from the browser and sees the correct price.
- [ ] The invoice and the two log rows exist in MySQL.
- [ ] The EMAIL and SMS appear in the Notification console with `MediBook-T`.
- [ ] Postman collection has one request per endpoint, error cases included.
- [ ] Money matches Appendix D exactly (2 decimals).

### 19.4 Phase 3 — Full system (deadline Fri 18 Dec, final)

**Build:** cancel + complete; compensation + 503 handling; Patient `/appointments`; JSP `my-appointments`, `error`; F1 doctor dashboard; F2 reschedule; README.

| Owner | Tasks | Exit criteria |
|---|---|---|
| O1 | FR-APT-04, FR-APT-05, FR-FEA-01, FR-FEA-03; full §16.5 compensation | Every row of the §16.6 matrix behaves as specified |
| O2 | Support F1 slot lookups; DB reset script; final schema/data verification | Fresh clone + schema + seed reproduces the demo |
| O3 | FR-BIL-05; money regression after any formula change | Cancel → `CANCELLED`; duplicate cancel → 409 |
| O4 | FR-PAT-05; README; demo script; zip packaging | README lets a stranger run the system in <15 min |
| O5 | All notification types incl. `RESCHEDULED`; failure injection; final Postman | Every endpoint + error case present; 503 tests documented |
| O6 | FR-WEB-07…10, FR-FEA-02, FR-FEA-04 | Cancel, reschedule, dashboard complete all work in the browser |

**Gate (final):**
- [ ] Whole system works end to end, including dashboard and reschedule.
- [ ] Stop one service at a time: the rest still answer with clean 503s (matrix §16.6).
- [ ] A cancelled slot can be booked again.
- [ ] Reschedule releases the old slot and keeps the invoice unchanged.
- [ ] README has members + IDs, ownership map, and run steps.
- [ ] Repo is public, zips named `medibook-T-phaseN.zip`.

### 19.5 Discussion (week of 19 Dec)

- Run from Phase 3 code on one laptop; all 5 services + Tomcat + MySQL already running before the slot.
- Rehearse: book → confirmation → my-appointments → cancel → rebook → reschedule → dashboard complete.
- Each member must be able to (a) explain any file, (b) change the loyalty rule live, (c) explain what happens when a named service is down.
- **Dry run on 18 Dec:** each person explains their shadow partner's component for 10 minutes.

---

## 20. Testing and QA plan

### 20.1 Postman collection

- One folder per service, one request per endpoint, saved examples for success and each error.
- Error cases required: `400`, `401`, `404`, `409` (all three codes), `503`.
- Environment variables: `base_appointment`, `base_doctor`, `base_billing`, `base_patient`, `base_notification`, `patient_id`, `doctor_id`, `slot_id`, `appointment_id`.
- A "Happy path" folder that runs in order: register → login → doctors → slots → quote → book → invoice → notifications → cancel.
- `503` cases are documented, not scripted (they require stopping a service).

### 20.2 Manual E2E checklist

- [ ] Register with each insurance option (none, BASIC, GOLD, STAFF).
- [ ] Login failure shows the right message and keeps you logged out.
- [ ] Filter doctors by specialty; open slots for one doctor.
- [ ] Quote for: no insurance, BASIC, GOLD, STAFF (cap), below threshold, at threshold.
- [ ] Book → confirmation values match Postman.
- [ ] Two browsers book the same slot → second gets a friendly `SLOT_NOT_AVAILABLE`.
- [ ] Cancel → slot reappears → a different patient books it.
- [ ] Complete → `completed_visits` increments → next quote shows the discount.
- [ ] Reschedule → old slot free, new slot booked, total unchanged.
- [ ] Doctor dashboard shows only that date's appointments with patient names.
- [ ] Stop each service per §16.6 and confirm no stack traces.

### 20.3 Failure injection procedure

1. Note the baseline response.
2. Stop the service (`Ctrl+C` in its terminal).
3. Re-run the dependent endpoint.
4. Confirm status, code, and message.
5. Restart and confirm the data is consistent (slot released, appointment cancelled, etc.).
6. Record the result in the README/Postman description.

### 20.4 Definition of Done (per endpoint)

- [ ] Correct success status and JSON shape.
- [ ] Every listed error case returns the right status + code + message.
- [ ] Own tables only; parameterized SQL; no hard-coded URL.
- [ ] Decimal/date/time conversions handled.
- [ ] `commit()` after writes.
- [ ] Postman request + examples added.
- [ ] Owner committed it with the FR ID.
- [ ] Buddy reviewed it.
- [ ] README row updated if behaviour was decided here.

---

## 21. Deliverables and submission checklist

### 21.1 Per phase, one member submits on Google Classroom

1. Link to the team's **public** GitHub repository.
2. A `.zip` of the repository named `medibook-T-phaseN.zip`.

### 21.2 Repository structure

```
medibook-T/
  README.md                 team members + IDs, who owns what, how to run
  database/
    schema.sql
    sample_data.sql
  services/
    appointment/            app.py  config.py  requirements.txt
    doctor/                 ...
    billing/                ...
    patient/                ...
    notification/           ...
  webapp/                   the JSP/Servlet project
  postman/
    medibook-T.postman_collection.json
```

### 21.3 README required content

- Team number `T` and all four derived parameter values.
- Member names + IDs + component ownership + shadow pairs.
- Ports and how to start MySQL, the 5 services, and Tomcat.
- How to create the DB and seed it; how to create test patients.
- The Postman collection import steps.
- The 503 matrix and the compensation behaviour you implemented.
- Known limitations and decisions from §23.

---

## 22. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `T` not assigned by 26 Nov | Wrong parameters everywhere | Build with `T = 0`; single constant per unit; change once |
| Two people editing one `app.py` | Conflicts, lost work | One owner per file per phase; shadows only review |
| Non-atomic reserve | Double booking, lost 6 marks | Single `UPDATE … WHERE status='AVAILABLE'` + `rowcount`; concurrency test |
| Decimal/timedelta not converted | `jsonify` crashes → 500 | Convert in the route before returning (§8.7) |
| Cross-service FK temptation | Zero marks for the endpoint | IDs only; verify via API |
| Notification called before commit | Callback 404 during booking | Commit appointment before step 7 |
| Patient↔Appointment recursion | Infinite loop / timeout | Appointment never calls Patient `/appointments` |
| Tomcat 10 uses `jakarta.*` | Servlets won't compile | Import `jakarta.servlet.*`, not `javax.*` |
| Java client default timeout | Hangs when a service is down | Explicit 3s connect + request timeouts |
| DB user lacks `DELETE` | Cannot reset via services | No DELETE endpoints; reset as root/admin |
| Notification failure treated as booking failure | Wrong 201/503 | Notification failure → `201` + `FAILED` |
| Port already in use | Service won't start | Check ports 5001–5005, 8080, 3306 before demo |
| Uneven hours | Resentment, one person can't explain | Phase-boundary rebalance on hours, not marks |
| Discussion ambush | Lost individual marks | Shadow pairs + 18 Dec dry run |

---

## 23. Open decisions

Record the answer in the README when decided. Defaults below are recommended.

| # | Decision | Default recommendation | Owner | Due |
|---|---|---|---|---|
| D1 | Shape of `PUT /patients/{id}/visits` response | `{"patient_id":3,"completed_visits":6}` | O4 | Phase 1 |
| D2 | Order in `complete`: Patient call before or after commit | Before commit, so a Patient outage doesn't lose a visit | O1 | Phase 3 |
| D3 | Cancel with Billing down | Status change wins; log the invoice mismatch; return 200 | O1 | Phase 3 |
| D4 | Patient names in F1 | JSP calls Patient per row (§14.6) | O6 | Phase 3 |
| D5 | Appointment list enrichment | Raw canonical object; JSP enriches | O1/O6 | Phase 2 |
| D6 | Login email case sensitivity | Case-insensitive (store lowercase) | O4 | Phase 1 |
| D7 | `GET /api/appointments` when both `patient_id` and `doctor_id`+`date` given | `patient_id` wins; document it | O1 | Phase 3 |
| D8 | Money rounding mode | `Decimal` + `ROUND_HALF_UP`, quantize each step | O3 | Phase 2 |
| D9 | Reschedule when the new slot equals the old slot | `400 VALIDATION_ERROR` | O1 | Phase 3 |
| D10 | Notification message text for CANCELLED/COMPLETED/RESCHEDULED | Keep the two-line structure; omit amount unless an invoice exists | O5 | Phase 3 |

---

## Appendix A — Configuration templates

### A.1 `services/*/config.py`

```python
# Single source of truth for team parameters.
TEAM_NUMBER = 0                    # <-- set to your assigned T

# Derived — never re-type these anywhere else
CLINIC_NAME      = f"MediBook-{TEAM_NUMBER}"
BOOKING_FEE      = 20 + TEAM_NUMBER          # EGP
LOYALTY_THRESHOLD = 3 + (TEAM_NUMBER % 3)    # completed visits
LOYALTY_DISCOUNT  = 0.10                     # 10%

# Database
DB_HOST, DB_PORT = "localhost", 3306
DB_NAME          = "clinic_system"
DB_USER          = "clinic_user"
DB_PASSWORD      = "choose_a_password"

# This service
SERVICE_NAME = "billing"
SERVICE_PORT = 5003

# Peers — only the ones this service actually calls
DOCTOR_URL       = "http://localhost:5002"
PATIENT_URL      = "http://localhost:5004"
BILLING_URL      = "http://localhost:5003"
APPOINTMENT_URL  = "http://localhost:5001"
NOTIFICATION_URL = "http://localhost:5005"

HTTP_TIMEOUT = 3
```

### A.2 `webapp` `config.properties`

```properties
team.number=0
clinic.name=MediBook-0
booking.fee=20
loyalty.threshold=3
loyalty.discount=10

patient.service.url=http://localhost:5004
doctor.service.url=http://localhost:5002
billing.service.url=http://localhost:5003
appointment.service.url=http://localhost:5001
notification.service.url=http://localhost:5005

http.timeout.seconds=3
```

---

## Appendix B — Database DDL and seed data

```sql
CREATE DATABASE clinic_system;
USE clinic_system;

-- Doctor & Schedule Service
CREATE TABLE doctors (
  doctor_id        INT PRIMARY KEY AUTO_INCREMENT,
  name             VARCHAR(100) NOT NULL,
  specialty        VARCHAR(50) NOT NULL,
  consultation_fee DECIMAL(10,2) NOT NULL,
  room             VARCHAR(20)
);

CREATE TABLE slots (
  slot_id    INT PRIMARY KEY AUTO_INCREMENT,
  doctor_id  INT NOT NULL,
  slot_date  DATE NOT NULL,
  start_time TIME NOT NULL,
  status     ENUM('AVAILABLE','BOOKED') NOT NULL DEFAULT 'AVAILABLE',
  FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
  UNIQUE (doctor_id, slot_date, start_time)
);

-- Patient Service
CREATE TABLE patients (
  patient_id          INT PRIMARY KEY AUTO_INCREMENT,
  name                VARCHAR(100) NOT NULL,
  email               VARCHAR(100) NOT NULL UNIQUE,
  phone               VARCHAR(20) NOT NULL,
  password_hash       VARCHAR(255) NOT NULL,
  insurance_plan_code VARCHAR(20) NULL,
  completed_visits    INT NOT NULL DEFAULT 0,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Appointment Service
CREATE TABLE appointments (
  appointment_id INT PRIMARY KEY AUTO_INCREMENT,
  patient_id     INT NOT NULL,
  doctor_id      INT NOT NULL,
  slot_id        INT NOT NULL,
  reason         VARCHAR(255),
  status         ENUM('CONFIRMED','CANCELLED','COMPLETED') NOT NULL DEFAULT 'CONFIRMED',
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Billing Service
CREATE TABLE insurance_plans (
  plan_code        VARCHAR(20) PRIMARY KEY,
  plan_name        VARCHAR(100) NOT NULL,
  coverage_percent DECIMAL(5,2) NOT NULL,
  max_coverage     DECIMAL(10,2) NOT NULL
);

CREATE TABLE invoices (
  invoice_id        INT PRIMARY KEY AUTO_INCREMENT,
  appointment_id    INT NOT NULL UNIQUE,
  patient_id        INT NOT NULL,
  consultation_fee  DECIMAL(10,2) NOT NULL,
  loyalty_discount  DECIMAL(10,2) NOT NULL,
  insurance_covered DECIMAL(10,2) NOT NULL,
  booking_fee       DECIMAL(10,2) NOT NULL,
  total             DECIMAL(10,2) NOT NULL,
  status            ENUM('ISSUED','CANCELLED') NOT NULL DEFAULT 'ISSUED',
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notification Service
CREATE TABLE notification_log (
  notification_id INT PRIMARY KEY AUTO_INCREMENT,
  appointment_id  INT NOT NULL,
  patient_id      INT NOT NULL,
  channel         ENUM('EMAIL','SMS') NOT NULL,
  type            VARCHAR(30) NOT NULL,
  message         TEXT NOT NULL,
  sent_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

```sql
INSERT INTO doctors (name, specialty, consultation_fee, room) VALUES
('Dr. Mona Khaled', 'Cardiology',  600.00, 'A-101'),
('Dr. Hany Fawzy',  'ENT',         350.00, 'A-102'),
('Dr. Salma Adel',  'Dermatology', 400.00, 'B-201'),
('Dr. Omar Nabil',  'Pediatrics',  300.00, 'B-202'),
('Dr. Laila Samir', 'Dentistry',   250.00, 'C-301');

INSERT INTO slots (doctor_id, slot_date, start_time)
SELECT d.doctor_id, t.slot_date, t.start_time
FROM doctors d
CROSS JOIN (
  SELECT '2026-12-27' AS slot_date, '10:00:00' AS start_time
  UNION ALL SELECT '2026-12-27', '10:30:00'
  UNION ALL SELECT '2026-12-28', '11:00:00'
  UNION ALL SELECT '2026-12-28', '11:30:00'
) t;

INSERT INTO insurance_plans (plan_code, plan_name, coverage_percent, max_coverage) VALUES
('BASIC', 'Basic Health',    50.00, 200.00),
('GOLD',  'Gold Care',       80.00, 500.00),
('STAFF', 'University Staff',100.00, 300.00);

CREATE USER 'clinic_user'@'localhost' IDENTIFIED BY 'choose_a_password';
GRANT SELECT, INSERT, UPDATE ON clinic_system.* TO 'clinic_user'@'localhost';
FLUSH PRIVILEGES;
```

> Patients are created **only** through `POST /api/patients/register`.

---

## Appendix C — Error catalogue

| HTTP | Code | Trigger | Example message |
|---|---|---|---|
| 400 | `VALIDATION_ERROR` | Missing field, bad email/phone/password, non-positive ID, wrong doctor for slot, bad date format | `"Slot 12 belongs to doctor 2"` |
| 401 | `INVALID_CREDENTIALS` | Wrong email or password | `"Wrong email or password"` |
| 404 | `NOT_FOUND` | Unknown patient/doctor/slot/appointment/plan/invoice | `"Patient 99 not found"` |
| 409 | `SLOT_NOT_AVAILABLE` | Reserve a booked slot | `"Slot 12 is already booked"` |
| 409 | `EMAIL_EXISTS` | Register an existing email | `"Email sara@example.com is already registered"` |
| 409 | `INVALID_STATUS` | Cancel a cancelled appointment, release a free slot, cancel a cancelled invoice | `"Appointment 15 is CANCELLED"` |
| 503 | `SERVICE_UNAVAILABLE` | Dependency down or timed out | `"Billing service is unavailable"` |

Envelope: `{"error": {"code": "...", "message": "..."}}`.

---

## Appendix D — Money test vectors

Formula: `total = (fee − loyalty) − min((fee − loyalty) × coverage%, cap) + (20 + T)`.

### D.1 Team `T = 7` (threshold 4, fee 27.00)

| # | Doctor (fee) | Plan | Visits | Loyalty | After disc. | Covered | Booking | Total |
|---|---|---|---|---|---|---|---|---|
| 1 | Mona Khaled (600) | GOLD | 5 | 60.00 | 540.00 | 432.00 | 27.00 | **135.00** |
| 2 | Hany Fawzy (350) | BASIC | 0 | 0.00 | 350.00 | 175.00 | 27.00 | **202.00** |
| 3 | Laila Samir (250) | none | 0 | 0.00 | 250.00 | 0.00 | 27.00 | **277.00** |
| 4 | Mona Khaled (600) | STAFF | 0 | 0.00 | 600.00 | 300.00 (cap) | 27.00 | **327.00** |
| 5 | Hany Fawzy (350) | STAFF | 0 | 0.00 | 350.00 | 300.00 (cap) | 27.00 | **77.00** |
| 6 | Omar Nabil (300) | GOLD | 5 | 30.00 | 270.00 | 216.00 | 27.00 | **81.00** |
| 7 | Salma Adel (400) | GOLD | 3 | 0.00 | 400.00 | 320.00 | 27.00 | **107.00** |
| 8 | Salma Adel (400) | GOLD | 4 | 40.00 | 360.00 | 288.00 | 27.00 | **99.00** |

Rows 7–8 prove the `>=` threshold boundary: one visit short → no discount; exactly at threshold → discount.

### D.2 Re-deriving for your `T`

1. `BOOKING_FEE = 20 + T`.
2. `LOYALTY_THRESHOLD = 3 + (T % 3)`.
3. Recompute columns 6–9 with the same formula; the loyalty and coverage columns do not depend on `T`.
4. Add the new rows to Postman as assertions and to the README as the documented expected values.

**Rounding:** `Decimal`, `ROUND_HALF_UP`, quantize to `0.01` after each step; cap after percentage.

---

## Appendix E — Traceability to grading

| Phase | Graded item | Marks | Owner | Requirements | Gate test |
|---|---|---|---|---|---|
| 1 | Database schema + sample data | 3 | O2 | Appendix B | Fresh import reproduces 5 doctors / 20 slots / 3 plans |
| 1 | Doctor & Schedule incl. safe reserve | 6 | O2 | FR-DOC-01…06 | Concurrency test: one 200, one 409 |
| 1 | Patient: validation, hashing, login | 6 | O4 | FR-PAT-01…03 | Duplicate email 409; hash stored; 401 on bad password |
| 1 | `/health` + one error format | 2 | all | §8.2, §8.3 | All five `/health`; every error matches envelope |
| 1 | JSP register, login, index, slots | 3 | O6 | FR-WEB-01…04 | Browser walkthrough |
| 2 | Billing calculation + invoices | 11 | O3 | FR-BIL-02…04 | Appendix D vectors |
| 2 | Appointment book (steps 1–8) | 12 | O1 | FR-APT-01 | §16.1 + Billing-down compensation |
| 2 | Notification: 4 services, console, 2 rows | 9 | O5 | FR-NOT-01 | Console output + `notification_log` count |
| 2 | JSP book + confirmation | 5 | O6 | FR-WEB-05…06 | Browser price matches quote |
| 2 | Postman collection | 3 | O5 | §20.1 | Import + run happy path |
| 3 | Cancel + complete flows | 4 | O1 | FR-APT-04, FR-APT-05 | Slot rebookable; visits increment |
| 3 | Compensation + clean 503 | 5 | O1 | §16.5, §16.6 | Full matrix |
| 3 | JSP my-appointments + error | 4 | O6 | FR-WEB-07, FR-WEB-10 | Cancel in browser; friendly 503 |
| 3 | F1 dashboard + F2 reschedule | 4 | O1, O6 | FR-FEA-01…04 | Dashboard by date; reschedule keeps invoice |
| 3 | README + final demo | 3 | O4 | §21.3 | Stranger can run it; demo rehearsed |
| Final | Individual discussion | 20 | all | — | Shadow dry run on 18 Dec |

Project mark = (total / 100) × 0.15.

---

## Appendix F — Glossary

| Term | Meaning |
|---|---|
| **Slot** | A bookable 30-minute window for one doctor, owned by the Doctor service |
| **Reserve / release** | Atomic status flip on a slot (`AVAILABLE` ⇄ `BOOKED`) |
| **Quote** | A price calculation that saves nothing |
| **Invoice** | A persisted quote, unique per appointment |
| **Compensation** | Undoing earlier side effects when a later step fails (release slot, cancel appointment) |
| **Enrichment** | Adding display fields (doctor name, slot date) from other services at the presentation layer |
| **Shadow pair** | Two owners who must each be able to explain and modify the other's component |
| **`T`** | Team number that parameterises clinic name, booking fee and loyalty threshold |
| **503** | The only acceptable answer when a dependency is down |
| **DoD** | Definition of Done (§20.4) |
