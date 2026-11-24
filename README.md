# MediBook-T — Clinic Appointment System

Service-Oriented Architecture team project for **IS434**.

A booking and billing system for a private clinic, built as **one Java JSP web application**
(UI + API gateway) and **five Python Flask microservices**. Each service owns its own tables and
runs on its own port. Services talk to each other only over REST with JSON.

> **Project status:** planning. The requirements are finalised; application code is not committed
> yet. The authoritative specification is [`docs/PRD.md`](docs/PRD.md).

---

## Team parameters

Set by the team number `T`, which is registered on Google Classroom (deadline **Thu 26 Nov 2026**).

| Parameter | Formula | Current value (`T = 0`) | Example (`T = 7`) |
|---|---|---|---|
| Clinic name | `MediBook-T` | `MediBook-0` | `MediBook-7` |
| Booking fee (EGP, never insured) | `20 + T` | `20.00` | `27.00` |
| Loyalty threshold (completed visits) | `3 + (T mod 3)` | `3` | `4` |
| Loyalty discount | `10%` | `10%` | `10%` |

**`T` is stored in exactly one place per deployable unit** — one constant in each service's
`config.py` and one key in the web app's `config.properties`. Every other value is derived at
startup. When the real team number arrives, change `TEAM_NUMBER` in those six files and nothing else.

> A submission that uses another team's values scores zero for the affected parts.

---

## Team and ownership

| Role | Member | Student ID | Owns | Shadow partner |
|---|---|---|---|---|
| O1 | _<name>_ | _<id>_ | Appointment Service (5001) | O2 |
| O2 | _<name>_ | _<id>_ | Doctor & Schedule Service (5002) + database | O1 |
| O3 | _<name>_ | _<id>_ | Billing Service (5003) | O4 |
| O4 | _<name>_ | _<id>_ | Patient Service (5004) + README | O3 |
| O5 | _<name>_ | _<id>_ | Notification Service (5005) + Postman | O6 |
| O6 | _<name>_ | _<id>_ | JSP web app (8080) + releases | O5 |

**Shadow partners** exist because 20 of the 100 marks are an individual discussion where any member
may be asked to explain or modify any part of the system. Each pair reviews the other's pull
requests and must be able to explain the other's code.

Full requirement-to-owner mapping: [`docs/PRD.md` §18](docs/PRD.md#18-work-breakdown-and-ownership).

---

## Architecture

| Component | Technology | Port | Owns tables |
|---|---|---|---|
| Web app (UI + API gateway) | Java JSP + Jakarta Servlets, Tomcat 10.x | 8080 | — |
| Appointment Service | Python 3.8+ / Flask | 5001 | `appointments` |
| Doctor & Schedule Service | Flask + MySQL | 5002 | `doctors`, `slots` |
| Billing Service | Flask + MySQL | 5003 | `insurance_plans`, `invoices` |
| Patient Service | Flask + MySQL | 5004 | `patients` |
| Notification Service | Flask + MySQL | 5005 | `notification_log` |
| Database | MySQL 8.0, db `clinic_system` | 3306 | — |

```
Browser ──► JSP app :8080 ──► Patient :5004, Doctor :5002, Billing :5003, Appointment :5001
            Appointment :5001 ──► Patient, Doctor, Billing, Notification
            Billing :5003     ──► Doctor, Patient
            Patient :5004     ──► Billing, Appointment
            Notification :5005 ──► Appointment, Patient, Doctor (×2), Billing (CONFIRMED only)
            Doctor :5002      ──► (no outbound calls)
```

**Ground rules** (graded in every phase):

1. Each service runs SQL only on its own tables. Cross-service data is fetched over HTTP.
2. JSON everywhere. Money has 2 decimals, dates are `YYYY-MM-DD`, times are `HH:MM`.
3. One error format: `{"error": {"code": "...", "message": "..."}}`.
4. `GET /health` on every service.
5. Inter-service calls use `requests` with `timeout=3`; a dead dependency returns `503`.
6. No hard-coded URLs, ports or credentials outside `config.py` / `config.properties`.
7. Parameterized SQL only.
8. Passwords are hashed with `werkzeug` and never returned by any endpoint.

---

## Repository layout

```
medibook-T/
├── README.md                    this file
├── docs/
│   └── PRD.md                   full product requirements document
├── database/
│   ├── schema.sql               tables, ownership, limited DB user
│   └── sample_data.sql          doctors, slots, insurance plans
├── services/
│   ├── appointment/             app.py  config.py  requirements.txt
│   ├── doctor/
│   ├── billing/
│   ├── patient/
│   └── notification/
├── webapp/                      JSP/Servlet project (Tomcat)
└── postman/
    └── medibook-T.postman_collection.json
```

---

## Running the system

### Prerequisites

- MySQL 8.0
- Python 3.8+
- JDK 17+ and Apache Tomcat 10.x (NetBeans, IntelliJ or Eclipse)
- Postman

### 1. Database

```bash
mysql -u root -p < database/schema.sql
mysql -u root -p < database/sample_data.sql
```

This creates `clinic_system`, the six tables, the limited `clinic_user` account, 5 doctors,
20 slots and 3 insurance plans.

**Do not insert patients with SQL.** Register them through the API so passwords are hashed:

```bash
curl -X POST http://localhost:5004/api/patients/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Sara Ali","email":"sara@example.com","phone":"01098765432","password":"secret123","insurance_plan_code":"GOLD"}'
```

Create at least three test patients: one with no insurance, one on `BASIC`, one on `GOLD`.
Create one with `completed_visits` above the loyalty threshold to demonstrate the discount.

### 2. Services

Each service runs in its own terminal:

```bash
cd services/doctor     && pip install -r requirements.txt && python app.py   # :5002
cd services/billing    && pip install -r requirements.txt && python app.py   # :5003
cd services/patient    && pip install -r requirements.txt && python app.py   # :5004
cd services/appointment && pip install -r requirements.txt && python app.py  # :5001
cd services/notification && pip install -r requirements.txt && python app.py # :5005
```

Verify each one:

```bash
curl http://localhost:5001/health   # {"service": "appointment", "status": "UP"}
curl http://localhost:5002/health   # {"service": "doctor", "status": "UP"}
curl http://localhost:5003/health   # {"service": "billing", "status": "UP"}
curl http://localhost:5004/health   # {"service": "patient", "status": "UP"}
curl http://localhost:5005/health   # {"service": "notification", "status": "UP"}
```

### 3. Web app

Open the `webapp/` project in NetBeans/IntelliJ/Eclipse, point it at Tomcat 10.x, and deploy.
Then browse to <http://localhost:8080/>.

### 4. Postman

Import `postman/medibook-T.postman_collection.json` and select the environment containing
`base_appointment`, `base_doctor`, `base_billing`, `base_patient`, `base_notification`.
Run the "Happy path" folder in order.

---

## Failure behaviour

**Compensation.** A booking never leaves a slot `BOOKED` with no appointment, and never leaves an
appointment with no invoice. If the Billing call fails during booking, the slot is released, the
appointment is set `CANCELLED`, and the caller gets `503`.

**Notification is best-effort.** If Notification is down, booking still returns `201` with
`"notification": "FAILED"`.

**503 matrix.** Stop one service at a time and verify:

| Stopped service | Book | Cancel | Complete | Reschedule | Patient `/appointments` | Notification `/send` | Web pages |
|---|---|---|---|---|---|---|---|
| Billing 5003 | `503` + compensation | `200` (invoice stays `ISSUED`) | `200` | `200` | `200` | `503` | quote page shows 503 message |
| Doctor 5002 | `503` | `200` (release logged) | `200` | `503` | `200` | `503` | index/slots show 503 message |
| Patient 5004 | `503` | `200` | `503` | `200` | `503` | `503` | login/register show 503 message |
| Appointment 5001 | n/a | n/a | n/a | n/a | `503` | `503` | my-appointments shows 503 message |
| Notification 5005 | `201` + `FAILED` | `200` | `200` | `200` + `FAILED` | `200` | `503` | unaffected |

No service ever returns an HTML error page or a stack trace.

---

## Implementation decisions

These points are unspecified in the assignment brief. The team's chosen answers are recorded here
and in [`docs/PRD.md` §23](docs/PRD.md#23-open-decisions).

| # | Decision | Status |
|---|---|---|
| D1 | `PUT /patients/{id}/visits` returns `{"patient_id", "completed_visits"}` | proposed |
| D2 | `complete` calls Patient before committing the `COMPLETED` status | proposed |
| D3 | Cancel with Billing down still returns `200`; the invoice mismatch is logged | proposed |
| D4 | The web app resolves patient names for the doctor dashboard (one call per row) | proposed |
| D5 | Appointment list endpoints return raw IDs; the web app enriches for display | proposed |
| D6 | Email matching on login and registration is case-insensitive | proposed |
| D7 | `GET /api/appointments` prefers `patient_id` when both filters are supplied | proposed |
| D8 | Money uses `Decimal` with `ROUND_HALF_UP`, quantized after each step | proposed |
| D9 | Rescheduling to the same slot returns `400` | proposed |
| D10 | CANCELLED/COMPLETED/RESCHEDULED messages keep the two-line EMAIL/SMS structure | proposed |

---

## Known limitations

- Email and SMS are simulated: messages are printed to the console and logged to `notification_log`,
  nothing is actually sent.
- `doctor.jsp` has no doctor login; it is reachable by any logged-in patient session. Accepted for
  this project's scope.
- No payment processing, refunds, or money movement.
- No pagination; list endpoints return every matching row.
- The database user has only `SELECT`, `INSERT`, `UPDATE` — there are no DELETE endpoints and
  cancellation is a status change.
- Runs on localhost only; no containerisation or cloud deployment.

---

## Phases

| Phase | Window | Deadline (11:59 PM) | Marks | Scope |
|---|---|---|---|---|
| 1 — Foundations | 22 Nov – 2 Dec | Wed 2 Dec 2026 | 20 | Database, Doctor & Schedule, Patient, Billing plans, `/health`, JSP register/login/index/slots |
| 2 — Booking | 3 – 10 Dec | Thu 10 Dec 2026 | 40 | Billing quote + invoices, Appointment book, Notification, JSP book/confirmation, Postman |
| 3 — Full system | 11 – 18 Dec | Fri 18 Dec 2026 | 20 | Cancel/complete, compensation + 503, my-appointments/error, doctor dashboard, reschedule, README |
| Discussion | 19 – 24 Dec | team slot | 20 | Live demo and individual questions |

Each phase is submitted on Google Classroom as a public repo link plus `medibook-T-phaseN.zip`.

---

## Contributing

1. Pick a GitHub issue (one per endpoint, tagged with its requirement ID, e.g. `FR-DOC-05`).
2. Work only on files your role owns for that phase.
3. Commit with the requirement ID: `feat(doctor): FR-DOC-05 atomic reserve`.
4. Open a pull request; your shadow partner reviews it.
5. Merge only when all five `/health` endpoints are green.

`main` must always run.
