# AI-HR - Intelligent Workforce Operating System

An AI-powered HR platform that automates recruitment, candidate intelligence, HR operations, analytics, and policy assistance. Built from the [complete HR blueprint](docs/BLUEPRINT.md) with an MVP-first architecture.

## Architecture

### Current (MVP)
```text
Frontend (Next.js) -> API Gateway (FastAPI)
  |-- Resume Parsing Service
  |-- Matching Service (embeddings + Qdrant)
  |-- Chatbot Service (RAG)
  |-- Interview Scheduling
  |-- Analytics Service
  |-- HR Ops & Onboarding
  |-- Payroll Service
  |-- Notification Service
  |-- Authentication
  `-- Notification hooks
Databases: PostgreSQL | Redis | Qdrant | Local/S3 uploads
```

### Future (Complete HRIS)
```text
Frontend (Next.js) -> API Gateway (FastAPI)
  |-- Recruitment Services
  |   |-- Resume Parsing Service
  |   |-- Matching Service (embeddings)
  |   |-- Recruitment Service (assessments, offers)
  |
  |-- Employee Services
  |   |-- Employee Management Service (directory, hierarchy)
  |   |-- Attendance Service (time tracking)
  |   |-- Performance Service (reviews, goals)
  |
  |-- Compensation Services
  |   |-- Benefits Service (enrollment, coverage)
  |   |-- Payroll Service (batch processing, taxes)
  |   |-- Expense Service (reimbursements)
  |
  |-- HR Operations
  |   |-- Onboarding Service
  |   |-- Offboarding Service
  |   |-- Leave Management (enhanced)
  |
  |-- Support Services
  |   |-- Chatbot Service (RAG policy assistant)
  |   |-- Engagement Service (surveys, recognition)
  |   |-- Document Management (contracts, e-sig)
  |   |-- AI Insights Service (predictions, analytics)
  |
  |-- Infrastructure
  |   |-- Analytics Service (enhanced with workforce planning)
  |   |-- Notification Service
  |   |-- Compliance Service (GDPR, audit trails)
  |   |-- Authentication & RBAC
  |
Databases: PostgreSQL | Redis cache | Qdrant embeddings | S3 storage
```

## Complete HR Platform Features

### ✅ Implemented (MVP + Core)

| Feature                                | Category       | Status  |
| -------------------------------------- | -------------- | ------- |
| AI Resume Parser (PDF/DOCX/text)       | Recruitment    | ✅ Done |
| Semantic Candidate-Job Matching        | Recruitment    | ✅ Done |
| Smart Candidate Ranking                | Recruitment    | ✅ Done |
| Interactive Job Description Generator  | Recruitment    | ✅ Done |
| RAG HR Policy Assistant                | HR Operations  | ✅ Done |
| Interview Scheduling + Notifications   | Recruitment    | ✅ Done |
| Hiring Analytics Dashboard             | Analytics      | ✅ Done |
| Employee Onboarding Workflows          | Onboarding     | ✅ Done |
| Employee Leave Requests + Burnout Risk | Leave Mgmt     | ✅ Done |
| Payroll Profile and Payslip Automation | Payroll        | ✅ Done |
| Explainable match scores               | AI/ML          | ✅ Done |
| RBAC-protected HR operations           | Security       | ✅ Done |
| Rate limiting and audit logging        | Compliance     | ✅ Done |
| MVP GraphQL and WebSocket adapters     | API            | ✅ Done |
| Notification event records             | Communications | ✅ Done |

### 🔴 Phase 1: Critical Core HR (NEW - In Development)

| Feature                          | Category      | Service                             | Status     |
| -------------------------------- | ------------- | ----------------------------------- | ---------- |
| **Employee Directory & Records** | Employee Mgmt | `employee-management-svc`           | 🔴 Planned |
| **Attendance & Time Tracking**   | Time Tracking | `attendance-svc`                    | 🔴 Planned |
| **Performance Management**       | Performance   | `performance-svc`                   | 🔴 Planned |
| **Benefits Management**          | Compensation  | `benefits-svc`                      | 🔴 Planned |
| **Enhanced Payroll System**      | Payroll       | `payroll-automation-svc` (enhanced) | 🔴 Planned |
| **Advanced Leave Management**    | Leave Mgmt    | `hr-ops-onboarding-svc` (enhanced)  | 🔴 Planned |

**Phase 1 Details:**

- Employee directory with organizational hierarchy
- Clock-in/out and attendance records with overtime tracking
- 360-degree performance reviews, goal tracking, ratings
- Benefits enrollment (health, dental, 401k, life insurance, FSA/HSA)
- Batch payroll with tax calculations (federal, state, local)
- Leave approval workflows with accrual policies

### 🟡 Phase 2: Enhanced HR Operations (NEW - Planned)

| Feature                      | Category    | Service           | Status     |
| ---------------------------- | ----------- | ----------------- | ---------- |
| **Employee Offboarding**     | Lifecycle   | `offboarding-svc` | 🟡 Planned |
| **Compliance & Legal**       | Compliance  | `compliance-svc`  | 🟡 Planned |
| **Recruitment Enhancements** | Recruitment | `recruitment-svc` | 🟡 Planned |

**Phase 2 Details:**

- Exit procedures, asset recovery, separation documents
- GDPR compliance tools, data retention policies, audit trails
- Candidate assessments, background checks, offer letters

### 🔵 Phase 3: Advanced Features (NEW - Planned)

| Feature                            | Category        | Service                              | Status     |
| ---------------------------------- | --------------- | ------------------------------------ | ---------- |
| **Workforce Planning & Analytics** | Analytics       | `analytics-dashboard-svc` (enhanced) | 🔵 Planned |
| **Employee Engagement**            | Culture         | `engagement-svc`                     | 🔵 Planned |
| **Time & Expense Management**      | Finance         | `expense-svc`                        | 🔵 Planned |
| **Document Management**            | Admin           | `document-mgmt-svc`                  | 🔵 Planned |
| **Employee Self-Service Portal**   | Employee Portal | `employee-portal-svc`                | 🔵 Planned |
| **Advanced AI Insights**           | AI/ML           | `ai-insights-svc`                    | 🔵 Planned |

**Phase 3 Details:**

- Headcount forecasting, skill gap analysis, succession planning, turnover predictions
- Engagement surveys, recognition system, pulse checks
- Expense reports, travel tracking, reimbursement workflows
- Contract templates, e-signature, document versioning
- Payslip downloads, profile updates, beneficiary management
- Retention risk prediction, salary benchmarking, bias detection

## Quick Start

### With Docker (recommended)

```bash
cp .env.example .env          # set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
```

- App: [http://localhost:3000](http://localhost:3000). Click **Create your workspace** to sign up a company.
- API docs (development only): [http://localhost:8000/docs](http://localhost:8000/docs)

The `migrate` job applies database migrations before any service starts. In development it also seeds a
**Demo Company** workspace (careers page at `/careers/demo`):

| Email                 | Password    | Role      |
| --------------------- | ----------- | --------- |
| `admin@aihr.demo`     | `demo12345` | Admin     |
| `recruiter@aihr.demo` | `demo12345` | Recruiter |
| `employee@aihr.demo`  | `demo12345` | Employee  |
| `candidate@aihr.demo` | `demo12345` | Candidate |

Hot reload for backend code: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`.

### Running tests

```bash
cd backend
uv venv --python 3.14 && uv pip install -r requirements.txt -r requirements-dev.txt
pytest -q && ruff check .

cd ../frontend
npm ci && npm run lint && npm run typecheck && npm run build
```

### Dependencies

Backend pins are compiled for Python 3.14 on Linux (the container target):

```bash
cd backend
uv pip compile requirements.in --upgrade --python-version 3.14 --python-platform linux -o requirements.txt
```

`requirements-ml.txt` (torch CPU + sentence-transformers) is only installed in the resume, matching and chatbot
images. In `frontend/`, `typescript` is aliased to the TypeScript 6 API package because `typescript-eslint` does
not support TypeScript 7 yet; `npm run typecheck` uses the TypeScript 7 compiler.

## Going to Production

Set in `.env` (or your secret manager):

- `ENVIRONMENT=production`. The services then refuse to start with a weak `SECRET_KEY` or SQLite, disable
  `/docs`, turn off demo seeding and LAN CORS, and send HSTS.
- `SECRET_KEY` of 32+ random characters, a managed PostgreSQL `DATABASE_URL`, `CORS_ORIGINS`/`FRONTEND_URL`
  set to your real domain, and `NEXT_PUBLIC_API_URL` set at frontend build time.
- `STORAGE_BACKEND=s3` with `S3_BUCKET` (resumes are written with SSE-AES256).
- `SMTP_*` so invitations and interview notices are emailed.
- `TRUST_PROXY_HEADERS=true` only when running behind a load balancer that sets `X-Forwarded-For`.

Expose only the frontend and `api-gateway` publicly, behind TLS. Every service has `/health` (liveness) and
`/ready` (database check) endpoints and logs JSON to stdout, including one audit record per write request.

## Architecture Coverage

Implemented now:

- Multi-tenant workspaces: every record is scoped to an organization; company sign-up, team invites with
  expiring single-use tokens, and public per-company careers pages with candidate sign-up
- JWT auth (PyJWT, bcrypt) with role-based access; roles can't be self-assigned at sign-up
- API gateway with Redis-backed rate limiting (stricter on auth), security headers, request IDs, and
  structured audit logs
- Alembic migrations and a PostgreSQL-first Compose stack with health-gated startup
- Resume parsing with upload size limits and local or S3 storage, semantic matching, explainable ranking,
  application pipeline status, interview scheduling with email notices, leave requests with approvals,
  payroll runs and payslips, hiring analytics from live data, and a RAG HR policy assistant

Not yet built:

- Billing and plan limits (the `organizations.plan` column is in place)
- SSO/OAuth, MFA, password reset, and email verification
- Org-specific policy documents for the HR assistant (it currently uses a shared default policy set)
- Production Kubernetes manifests (`k8s/deployment.yaml` is a placeholder) and Terraform
- GDPR data export/deletion endpoints and retention policies

## Portals

| Portal     | Path         | Users                               |
| ---------- | ------------ | ----------------------------------- |
| Recruiter  | `/recruiter` | Pipeline, ranking, scheduling       |
| Candidate  | `/candidate` | Resume upload, apply, track status  |
| Employee   | `/employee`  | Leave requests/approvals, payslips  |
| Admin      | `/admin`     | Hiring analytics                    |
| Team       | `/team`      | Invite members, careers page link   |
| Careers    | `/careers/<slug>` | Public job board, candidate sign-up |
| HR Copilot | `/chat`      | RAG policy and recruiting assistant |

## Ethical AI

- Human-in-the-loop overrides on all AI rankings
- Explainable match breakdowns (skills, experience, gaps)
- No automated rejection without recruiter approval
- Video/emotion analysis stubs disabled by default because of legal sensitivity

## Tech Stack

- Frontend: Next.js 16, React 19, TypeScript 7, Tailwind CSS 4 (Node 24)
- Backend: Python 3.14, FastAPI, SQLAlchemy 2.1 (async), Alembic, PostgreSQL 18, Redis 8
- AI: Sentence Transformers (CPU torch), Qdrant 1.20, optional Groq LLM and NVIDIA reranker
- Infra: Docker multi-stage images (non-root), Docker Compose, GitHub Actions CI

## Comprehensive HR Features Map

### 🎯 RECRUITMENT & TALENT ACQUISITION
- ✅ **Resume Parsing**: Extract skills, experience, education from PDF/DOCX/TXT
- ✅ **Semantic Job Matching**: AI-powered candidate-job fit scoring with explainability
- ✅ **Candidate Ranking**: Smart ranking with match breakdowns
- ✅ **Job Description Generator**: AI-assisted JD creation
- ✅ **Interview Scheduling**: Automated scheduling with notifications
- ✅ **Hiring Analytics**: Funnel tracking, source effectiveness, time-to-hire
- 🔴 **Candidate Assessments** (Phase 2): Tests, coding challenges, skill assessments
- 🔴 **Background Checks** (Phase 2): Integration stubs for background verification
- 🔴 **Reference Checks** (Phase 2): Reference request workflows
- 🔴 **Offer Management** (Phase 2): Generate, track, and e-sign offer letters

### 👥 EMPLOYEE MANAGEMENT
- 🔴 **Employee Directory** (Phase 1): Complete employee profiles with contact info
- 🔴 **Organizational Hierarchy** (Phase 1): Department structure, reporting relationships
- 🔴 **Emergency Contacts** (Phase 1): Track emergency contact information
- 🔴 **Employee Status** (Phase 1): Active, inactive, on-leave, terminated statuses
- 🟡 **Profile Self-Service** (Phase 3): Employees update personal information

### ⏱️ ATTENDANCE & TIME TRACKING
- 🔴 **Clock In/Out** (Phase 1): Digital time tracking with timestamps
- 🔴 **Attendance Records** (Phase 1): Daily presence, absence, late tracking
- 🔴 **Overtime Management** (Phase 1): Track and report overtime hours
- 🔴 **Attendance Reports** (Phase 1): Admin reports with monthly/daily summaries
- 🔴 **Auto-Sync with Leave** (Phase 1): Link attendance to leave management

### 📊 PERFORMANCE MANAGEMENT
- 🔴 **Review Cycles** (Phase 1): Create and manage annual/quarterly review periods
- 🔴 **360-Degree Feedback** (Phase 1): Self, manager, peer, and direct report feedback
- 🔴 **Performance Ratings** (Phase 1): Rate employees on competencies and behaviors
- 🔴 **Goal Setting & Tracking** (Phase 1): Create, track, and measure employee goals
- 🔴 **Review Workflows** (Phase 1): Draft → Submit → Review → Finalize
- 🔴 **Performance History** (Phase 1): Track ratings and feedback over time

### 💰 COMPENSATION & PAYROLL
- ✅ **Payroll Profiles**: Basic salary and employment type setup
- ✅ **Payslip Generation**: Auto-generate payslips
- 🔴 **Batch Payroll Processing** (Phase 1): Run monthly/bi-weekly payroll for all employees
- 🔴 **Tax Calculations** (Phase 1): Federal, state, and local tax computation
- 🔴 **Statutory Deductions** (Phase 1): Social Security, Medicare, unemployment insurance
- 🔴 **Salary Revisions** (Phase 1): Track and apply salary increases
- 🔴 **Payroll Cycles** (Phase 1): Define pay periods (monthly, bi-weekly, weekly)
- 🔴 **Payroll Reports** (Phase 1): Reconciliation, distribution, tax reports
- 🔴 **Year-End Reporting** (Phase 1): W2s, 1099s, tax statements

### 💳 BENEFITS MANAGEMENT
- 🔴 **Benefits Catalog** (Phase 1): Health, dental, vision, 401k, FSA, HSA, life insurance
- 🔴 **Enrollment & Deenrollment** (Phase 1): Employee benefits enrollment process
- 🔴 **Coverage Tracking** (Phase 1): Track active benefits and coverage dates
- 🔴 **Eligibility Rules** (Phase 1): Define who qualifies for each benefit
- 🔴 **Deduction Calculations** (Phase 1): Compute benefit deductions from payroll
- 🔴 **Benefits Reporting** (Phase 1): Benefits usage and cost analysis

### 🗓️ LEAVE & ABSENCE MANAGEMENT
- ✅ **Leave Requests**: Basic leave request functionality
- ✅ **Leave Types**: Annual, sick, unpaid, maternity leave
- ✅ **Burnout Risk**: Predict employee burnout based on leave patterns
- 🔴 **Leave Approval Workflows** (Phase 1): Employee → Manager → HR approval
- 🔴 **Leave Balances** (Phase 1): Track available, used, and carryover leave
- 🔴 **Accrual Policies** (Phase 1): Auto-calculate monthly/yearly leave accrual
- 🔴 **Carryover Rules** (Phase 1): Define carryover limits and expiration
- 🔴 **Leave Forecasting** (Phase 1): Predict leave balance for future periods
- 🔴 **Attendance Sync** (Phase 1): Auto-link leave requests to attendance records

### 🎓 ONBOARDING & OFFBOARDING
- ✅ **Onboarding Workflows**: Task-based employee onboarding
- 🔴 **Complete Onboarding** (Phase 2): Equipment, access, training, documentation
- 🔴 **Offboarding Workflows** (Phase 2): Exit procedures, knowledge transfer, asset recovery
- 🔴 **Exit Interviews** (Phase 2): Capture exit interview data
- 🔴 **Separation Documents** (Phase 2): Generate reference, severance, and legal docs

### 📈 ANALYTICS & REPORTING
- ✅ **Hiring Analytics**: Funnel, match quality, time-to-hire metrics
- 🔴 **Workforce Planning** (Phase 3): Headcount forecasts and budgeting
- 🔴 **Skill Gap Analysis** (Phase 3): Identify skills to recruit or train
- 🔴 **Succession Planning** (Phase 3): Plan for key position replacements
- 🔴 **Turnover Analytics** (Phase 3): Predict and analyze employee turnover
- 🔴 **Diversity Metrics** (Phase 3): Track diversity and inclusion KPIs
- 🔴 **Cost Per Hire** (Phase 3): Calculate recruitment ROI
- 🔴 **Employee ROI** (Phase 3): Measure productivity and value

### 🤝 EMPLOYEE ENGAGEMENT
- 🔴 **Engagement Surveys** (Phase 3): Measure employee satisfaction and engagement
- 🔴 **Pulse Surveys** (Phase 3): Quick feedback on specific topics
- 🔴 **Recognition System** (Phase 3): Employee recognition and rewards
- 🔴 **Feedback Channels** (Phase 3): 360 feedback and peer recognition

### 💼 TALENT DEVELOPMENT
- 🔴 **Learning Catalog** (Future): Training and development courses
- 🔴 **Course Enrollment** (Future): Track employee training
- 🔴 **Certifications** (Future): Manage professional certifications
- 🔴 **Skill Development Plans** (Future): Personalized learning paths
- 🔴 **Internal Mobility** (Future): Job promotion and transfer tracking

### ✍️ DOCUMENTS & CONTRACTS
- 🔴 **Contract Templates** (Phase 3): Employment contract templates
- 🔴 **E-Signature Integration** (Phase 3): Digital signing capability
- 🔴 **Document Versioning** (Phase 3): Track document versions and history
- 🔴 **Contract Renewal** (Phase 3): Automated contract renewal tracking

### 🛡️ COMPLIANCE & LEGAL
- ✅ **RBAC**: Role-based access control for sensitive operations
- ✅ **Audit Logging**: Complete audit trail of all API operations
- ✅ **Rate Limiting**: Protection against abuse
- 🔴 **GDPR Compliance** (Phase 2): Data requests, right to be forgotten
- 🔴 **Data Retention Policies** (Phase 2): Enforce data deletion schedules
- 🔴 **Consent Management** (Phase 2): Track employee data consents
- 🔴 **Compliance Audit Trail** (Phase 2): Complete change logs and approvals
- 🔴 **Policy Version Control** (Phase 2): Track policy changes over time

### 💬 AI & CHATBOT
- ✅ **HR Policy Assistant**: RAG-based chatbot for HR policy questions
- ✅ **Match Explanations**: AI explanations for candidate-job match scores
- 🔴 **Retention Risk Prediction** (Phase 3): ML-based turnover prediction
- 🔴 **Career Recommendations** (Phase 3): AI suggestions for career development
- 🔴 **Salary Benchmarking** (Phase 3): Market-based salary recommendations
- 🔴 **Bias Detection** (Phase 3): Identify bias in recruiting decisions

### 📱 EMPLOYEE SELF-SERVICE
- 🔴 **Payslip Downloads** (Phase 3): Access and download payslips
- 🔴 **Tax Documents** (Phase 3): Download W2s, 1099s, tax statements
- 🔴 **Profile Updates** (Phase 3): Update personal information
- 🔴 **Beneficiary Management** (Phase 3): Add/update beneficiaries
- 🔴 **Bank Details** (Phase 3): Update direct deposit information
- 🔴 **Leave Balance Inquiry** (Phase 3): Check leave balance and history
- 🔴 **Benefits Info** (Phase 3): View enrolled benefits and coverage

### 💸 TIME & EXPENSE MANAGEMENT
- 🔴 **Expense Reports** (Phase 3): Submit and track expenses
- 🔴 **Travel Tracking** (Phase 3): Manage travel expenses
- 🔴 **Reimbursement Workflows** (Phase 3): Approval and payment tracking
- 🔴 **Project Time Tracking** (Phase 3): Track time spent on projects

### 🔗 INTEGRATIONS
- 🔴 **HRIS Integration** (Phase 3): Sync with other HRIS systems
- 🔴 **ATS Connection** (Phase 3): Link with applicant tracking systems
- 🔴 **Background Check API** (Phase 3): Connect to verification services
- 🔴 **Tax Software** (Phase 3): Export to accounting/tax software
- 🔴 **Calendar Integration** (Phase 3): Gmail, Outlook calendar sync
- 🔴 **Communication** (Phase 3): Slack, Teams, email integration
- 🔴 **Payroll Providers** (Phase 3): Integration with payroll services

---

## Data Models (Database Schema)

### Employee Management
```sql
employees, emergency_contacts, departments
```

### Attendance
```sql
attendance_logs, attendance_summary
```

### Performance
```sql
review_cycles, reviews, feedback, goals
```

### Compensation
```sql
salary_profiles, salary_revisions, payroll_cycles
benefit_plans, employee_benefits, benefit_eligibility
payroll_deductions
```

### Leave
```sql
leave_types, leave_balances, leave_requests
```

### Recruitment
```sql
assessments, assessment_results, offers, reference_checks
```

### Compliance
```sql
compliance_events, data_retention_policies, consent_records
```

---

## Implementation Timeline

### Phase 1 (Weeks 1-3): Critical Core
- Employee Management Service
- Attendance Service  
- Performance Management Service
- Benefits Management Service
- Enhanced Payroll (batch processing, taxes)
- Advanced Leave Management

### Phase 2 (Weeks 4-5): HR Operations
- Offboarding Service
- Compliance & Legal Service
- Recruitment Enhancements (assessments, offers)

### Phase 3 (Weeks 6-7): Advanced Features
- Workforce Planning Analytics
- Employee Engagement
- Time & Expense Management
- Document Management
- Employee Portal
- Advanced AI Insights

---

## Project Structure

```text
AI-HR/
|-- backend/
|   |-- resume-parsing-svc/        # ✅ Resume extraction
|   |-- matching-engine-svc/       # ✅ Job matching & ranking
|   |-- interview-assistant-svc/   # ✅ Interview scheduling
|   |-- analytics-dashboard-svc/   # ✅ + 🔴 Analytics & workforce planning
|   |-- hr-ops-onboarding-svc/     # ✅ + 🔴 Onboarding & advanced leave
|   |-- payroll-automation-svc/    # ✅ + 🔴 Payroll & benefits
|   |-- chatbot-rag-assistant-svc/ # ✅ HR policy chatbot
|   |-- notification-scheduling-svc/ # ✅ Notifications
|   |-- api-gateway/               # ✅ API gateway, auth, audit
|   |
|   |-- employee-management-svc/   # 🔴 Employee directory (Phase 1)
|   |-- attendance-svc/            # 🔴 Time tracking (Phase 1)
|   |-- performance-svc/           # 🔴 Reviews & goals (Phase 1)
|   |-- benefits-svc/              # 🔴 Benefits (Phase 1)
|   |-- offboarding-svc/           # 🔴 Exit procedures (Phase 2)
|   |-- compliance-svc/            # 🔴 GDPR & audit (Phase 2)
|   |-- recruitment-svc/           # 🔴 Assessments & offers (Phase 2)
|   |-- engagement-svc/            # 🔴 Surveys & recognition (Phase 3)
|   |-- expense-svc/               # 🔴 Expenses & reimbursement (Phase 3)
|   |-- document-mgmt-svc/         # 🔴 Contracts & docs (Phase 3)
|   |-- ai-insights-svc/           # 🔴 Advanced ML (Phase 3)
|   |-- employee-portal-svc/       # 🔴 Self-service (Phase 3)
|   `-- shared/                    # Common utilities, auth, models
|
|-- frontend/                      # Next.js dashboards
|   |-- src/pages/
|   |   |-- /recruiter             # ✅ Recruitment portal
|   |   |-- /candidate             # ✅ Candidate portal
|   |   |-- /employee              # ✅ Employee portal (basic)
|   |   |-- /admin                 # ✅ Analytics & admin
|   |   |-- /chat                  # ✅ HR Copilot
|   |   `-- /hr                    # 🔴 HR operations portal (Phase 1-3)
|
|-- k8s/                           # Kubernetes manifests
|-- docs/                          # Blueprint, API specs
`-- docker-compose.yml
```

---

## License

MIT

