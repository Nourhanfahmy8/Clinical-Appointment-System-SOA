# MediBook-T — Clinic Appointment System

Service-Oriented Architecture team project for **IS434**.

A booking and billing system for a private clinic: one Java JSP web application (UI + API
gateway) and five Python Flask microservices. Each service owns its tables and runs on its own
port; services talk only over REST with JSON.

> **Status:** planning. Structure and requirements are in place; application code is being
> written phase by phase.
>
> Full specification: [`docs/PRD.md`](docs/PRD.md)

---

## Team parameters

Set by the team number `T`, registered on Google Classroom (deadline **Thu 26 Nov 2026**).

| Parameter | Formula | Current (`T = 0`) | Example (`T = 7`) |
|---|---|---|---|
| Clinic name | `MediBook-T` | `MediBook-0` | `MediBook-7` |
| Booking fee (EGP, never insured) | `20 + T` | `20.00` | `27.00` |
| Loyalty threshold (completed visits) | `3 + (T mod 3)` | `3` | `4` |
| Loyalty discount | `10%` | `10%` | `10%` |

`T` appears in exactly one place per unit — one constant in each `config.py` and one key in the
web app's `config.properties`. Everything else is derived. Using another team's values scores zero.

---

## Team and ownership

| Role | Member | ID | Owns |
|---|---|---|---|
| O1 | Ziad *(leader)* | `<id>` | Appointment Service (5001) + project structure |
| O2 | `<name>` | `<id>` | Doctor & Schedule Service (5002) + database |
| O3 | `<name>` | `<id>` | Billing Service (5003) |
| O4 | `<name>` | `<id>` | Patient Service (5004) + README |
| O5 | `<name>` | `<id>` | Notification Service (5005) + Postman collection |
| O6 | `<name>` | `<id>` | JSP web app (8080) |

---

## Components

| Component | Technology | Port | Owns tables |
|---|---|---|---|
| Web app (UI + API gateway) | Java JSP + Jakarta Servlets, Tomcat 10.x | 8080 | — |
| Appointment Service | Python 3.8+ / Flask | 5001 | `appointments` |
| Doctor & Schedule Service | Flask + MySQL | 5002 | `doctors`, `slots` |
| Billing Service | Flask + MySQL | 5003 | `insurance_plans`, `invoices` |
| Patient Service | Flask + MySQL | 5004 | `patients` |
| Notification Service | Flask + MySQL | 5005 | `notification_log` |
| Database | MySQL 8.0, db `clinic_system` | 3306 | — |

Each service folder contains exactly three files: `app.py`, `config.py`, `requirements.txt`.

---

## Repository layout

```
medibook-T/
├── README.md
├── Dockerfile                  one image for all five services
├── docker-compose.yml          MySQL + the five services
├── docs/PRD.md
├── database/
│   ├── schema.sql
│   └── sample_data.sql
├── docker/
│   └── initdb/03-grant.sql     Docker-only DB user grant
├── services/
│   ├── appointment/
│   ├── doctor/
│   ├── billing/
│   ├── patient/
│   └── notification/
├── webapp/
└── postman/
    └── medibook-T.postman_collection.json
```

---

## How to run

### Prerequisites

MySQL 8.0 · Python 3.8+ · JDK 17+ and Tomcat 10.x · Postman

### 1. Database

```bash
mysql -u root -p < database/schema.sql
mysql -u root -p < database/sample_data.sql
```

Creates `clinic_system`, the six tables, the limited `clinic_user` account, 5 doctors, 20 slots
and 3 insurance plans.

Patients are **never inserted with SQL** — register them through the API so passwords are hashed:

```bash
curl -X POST http://localhost:5004/api/patients/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Sara Ali","email":"sara@example.com","phone":"01098765432",
       "password":"secret123","insurance_plan_code":"GOLD"}'
```

Create at least three patients: no insurance, `BASIC`, and `GOLD` — plus one with
`completed_visits` above the loyalty threshold.

### 2. Services

One terminal per service:

```bash
cd services/appointment  && pip install -r requirements.txt && python app.py   # :5001
cd services/doctor       && pip install -r requirements.txt && python app.py   # :5002
cd services/billing      && pip install -r requirements.txt && python app.py   # :5003
cd services/patient      && pip install -r requirements.txt && python app.py   # :5004
cd services/notification && pip install -r requirements.txt && python app.py   # :5005
```

Check each one:

```bash
curl http://localhost:5001/health   # {"service": "appointment", "status": "UP"}
curl http://localhost:5002/health   # {"service": "doctor",      "status": "UP"}
curl http://localhost:5003/health   # {"service": "billing",     "status": "UP"}
curl http://localhost:5004/health   # {"service": "patient",     "status": "UP"}
curl http://localhost:5005/health   # {"service": "notification","status": "UP"}
```

### 3. Web app

Open `webapp/` in NetBeans/IntelliJ/Eclipse, deploy to Tomcat 10.x, browse to
<http://localhost:8080/>.

### 4. Postman

Import `postman/medibook-T.postman_collection.json` and set `base_appointment`, `base_doctor`,
`base_billing`, `base_patient`, `base_notification`.

### 5. Docker (optional)

The manual steps above are the primary way to run the project. Docker is a convenience that
starts MySQL and all five services with one command:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f appointment
```

Services listen on the same ports (5001–5005), so Postman and the web app work unchanged.
Reset the database with `docker compose down -v`.

How it fits together:

- `Dockerfile` is one image definition for all five services; compose passes `SERVICE_DIR`.
- `config.py` reads `DB_HOST`, `SERVICE_HOST` and the peer URLs from environment variables.
  The defaults are the local values, so `python app.py` still works without Docker.
- `docker/initdb/03-grant.sql` adds `clinic_user@'%'`, because a container connects from a
  different host than `localhost`. Privileges are unchanged: `SELECT, INSERT, UPDATE`.
- MySQL runs `schema.sql`, then `sample_data.sql`, then the grant. Those first two are
  placeholders until O2 fills them in.
- The web app is not in the compose file yet; it needs the JSP project from O6.

---

## Ground rules

1. A service runs SQL only on its own tables; other data comes over HTTP.
2. JSON everywhere — money 2 decimals, dates `YYYY-MM-DD`, times `HH:MM`.
3. One error format: `{"error": {"code": "...", "message": "..."}}` with the correct status.
4. `GET /health` on every service.
5. Inter-service calls use `timeout=3`; a dead dependency returns `503`, never an HTML error page.
6. No URLs, ports or credentials outside `config.py` / `config.properties`.
7. Parameterized SQL only.
8. Passwords hashed, never returned.

---

## Phases

| Phase | Window | Deadline | Scope |
|---|---|---|---|
| 1 — Foundations | 22 Nov – 2 Dec | Wed 2 Dec | Database, Doctor, Patient, Billing plans, `/health`, JSP register/login/index/slots |
| 2 — Booking | 3 – 10 Dec | Thu 10 Dec | Billing quote + invoices, Appointment book, Notification, JSP book/confirmation, Postman |
| 3 — Full system | 11 – 18 Dec | Fri 18 Dec | Cancel/complete, compensation + 503, my-appointments/error, doctor dashboard, reschedule |
| Discussion | 19 – 24 Dec | team slot | Live demo + individual questions |

Every phase is submitted as a public repo link plus `medibook-T-phaseN.zip`.

Acceptance gates, the 503 matrix, and all design decisions are in
[`docs/PRD.md`](docs/PRD.md) §16, §19 and §23.
