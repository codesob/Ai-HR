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
Databases: SQLite for local/Docker MVP | Redis | Qdrant | Local/S3 uploads
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

### With Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: [http://localhost:3000](http://localhost:3000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- GraphQL MVP endpoint: [http://localhost:8000/api/v1/graphql](http://localhost:8000/api/v1/graphql)
- Notification WebSocket: `ws://localhost:8000/api/v1/ws/notifications`
- Qdrant UI: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

Demo users are seeded automatically on startup:

| Email                 | Password    | Role      |
| --------------------- | ----------- | --------- |
| `admin@aihr.demo`     | `demo12345` | Admin     |
| `recruiter@aihr.demo` | `demo12345` | Recruiter |
| `candidate@aihr.demo` | `demo12345` | Candidate |

### Local Development

The frontend can run directly on your machine:

```bash
cd frontend
npm install
npm run dev
```

For the backend, Docker Compose is the simplest local setup because the API gateway expects the service containers by name. If you want to run services manually, start each FastAPI service on its own port and override the gateway service URLs, for example:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt

# terminal 1
cd resume-parsing-svc
uvicorn app.main:app --reload --port 8011

# terminal 2
cd ../matching-engine-svc
uvicorn app.main:app --reload --port 8012

# terminal 3
cd ../api-gateway
$env:RESUME_SERVICE_URL="http://localhost:8011"
$env:MATCHING_SERVICE_URL="http://localhost:8012"
uvicorn main:app --reload --port 8000
```

By default the backend uses SQLite and seeds demo data automatically, so PostgreSQL is not required for local development. Docker Compose also includes PostgreSQL for production-like runs; switch `DATABASE_URL` to `postgresql+asyncpg://aihr:aihr-dev-password@postgres:5432/aihr` to use it.

## Architecture Coverage

Implemented now:

- REST API gateway with CORS, security headers, rate limiting, audit log writes, and MVP GraphQL query support
- JWT authentication with role-based route protection for sensitive HR operations
- FastAPI microservices for resume parsing, matching, interview scheduling, analytics, HR ops/onboarding, payroll, chatbot/RAG, and notifications
- Onboarding plans, leave requests, burnout risk scoring, payroll profile management, payslip generation, and interview workflow automation
- AI functions including resume extraction, job description generation, semantic matching, explainable scoring, and HR policy chat
- Notification/event records for applications and interview scheduling
- WebSocket notification stream endpoint for realtime UI wiring
- SQLite local default, PostgreSQL Compose option, Redis, Qdrant, and local object storage abstraction
- Docker Compose and Kubernetes manifests, with Terraform/MLOps folders reserved for production rollout

Still production-hardening work:

- Full GraphQL schema/resolvers beyond the MVP query adapter
- OAuth provider integration and MFA challenge flow
- Redis-backed distributed rate limiting instead of in-process buckets
- Real email/SMS/calendar dispatch providers
- S3 upload implementation behind the storage abstraction
- Formal GDPR/CCPA retention policies, SOC2 evidence automation, and complete audit dashboard

## Portals

| Portal     | Path         | Users                               |
| ---------- | ------------ | ----------------------------------- |
| Recruiter  | `/recruiter` | Pipeline, ranking, scheduling       |
| Candidate  | `/candidate` | Apply, track status, tests          |
| Employee   | `/employee`  | Leave, payslips, learning           |
| Admin      | `/admin`     | Analytics, compliance, AI insights  |
| HR Copilot | `/chat`      | RAG policy and recruiting assistant |

## Ethical AI

- Human-in-the-loop overrides on all AI rankings
- Explainable match breakdowns (skills, experience, gaps)
- No automated rejection without recruiter approval
- Video/emotion analysis stubs disabled by default because of legal sensitivity

## Tech Stack

- Frontend: Next.js 15, React, TypeScript, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, async SQLite/PostgreSQL-compatible settings
- AI: Sentence Transformers, Qdrant, optional OpenAI for LLM extraction
- Infra: Docker, Kubernetes-ready manifests in `k8s/`

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

