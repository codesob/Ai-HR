"""Demo tenant for local development. Never runs in production unless SEED_DEMO_DATA=true."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from shared.core.security import hash_password
from shared.db.session import AsyncSessionLocal
from shared.services.onboarding import create_onboarding_plan

DEMO_ORG_SLUG = "demo"
DEMO_ORG_NAME = "Halcyon Robotics"
DEMO_PASSWORD = "demo12345"

# (title, department, description, requirements, skills, min_years, salary_min, salary_max, status)
JOBS = [
    ("Senior ML Engineer", "Engineering",
     "Build and deploy ML systems including RAG pipelines and ranking models for our robot fleet.",
     "5+ years Python, PyTorch, production ML experience.",
     ["Python", "PyTorch", "RAG", "FastAPI", "Docker"], 5, 140000, 190000, "open"),
    ("Full Stack Developer", "Engineering",
     "Develop Next.js and FastAPI features for our fleet operations console.",
     "3+ years React and backend API development.",
     ["React", "Next.js", "TypeScript", "FastAPI", "PostgreSQL"], 3, 100000, 140000, "open"),
    ("HR Operations Specialist", "People",
     "Automate onboarding, compliance, and employee lifecycle workflows.",
     "HRIS experience and process optimization skills.",
     ["HRIS", "Compliance", "Onboarding", "Communication"], 2, 70000, 95000, "open"),
    ("Product Designer", "Product",
     "Own end-to-end design for operator-facing tools, from research to shipped UI.",
     "Portfolio of shipped B2B product work; strong Figma and prototyping skills.",
     ["Figma", "User Research", "Prototyping", "Design Systems"], 3, 95000, 130000, "open"),
    ("Field Robotics Technician", "Operations",
     "Install, maintain and troubleshoot autonomous robots at customer warehouses.",
     "Hands-on electromechanical experience; travel up to 40%.",
     ["Electronics", "Troubleshooting", "PLC", "Customer Service"], 2, 60000, 80000, "closed"),
]

# name, email local part, skills, years, education, summary, certifications
CANDIDATES = [
    ("Priya Natarajan", "priya", ["Python", "PyTorch", "RAG", "FastAPI", "Docker", "Kubernetes"], 7,
     "MSc Computer Science, University of Toronto",
     "ML engineer who shipped retrieval and ranking systems serving 2M daily queries.", ["AWS ML Specialty"]),
    ("Marcus Okafor", "marcus", ["Python", "PyTorch", "TensorFlow", "Docker"], 4,
     "BEng Electrical Engineering, Imperial College London",
     "Computer vision engineer working on perception models for warehouse robots.", []),
    ("Elena Petrova", "elena", ["Python", "RAG", "FastAPI", "LangChain"], 3,
     "BSc Mathematics, ETH Zurich",
     "Applied scientist building LLM-powered search and question answering.", []),
    ("Diego Alvarez", "diego", ["React", "Next.js", "TypeScript", "FastAPI", "PostgreSQL", "Tailwind"], 5,
     "BSc Software Engineering, UNAM",
     "Full stack engineer who led the rebuild of a logistics dashboard used by 300 operators.", []),
    ("Hannah Kim", "hannah", ["React", "TypeScript", "Node.js", "GraphQL"], 3,
     "BA Computer Science, UC Berkeley",
     "Frontend-leaning engineer focused on accessible, data-dense interfaces.", []),
    ("Tomás Ribeiro", "tomas", ["Java", "Spring", "PostgreSQL", "React"], 2,
     "BSc Information Systems, University of Lisbon",
     "Backend developer moving into full stack product work.", []),
    ("Aisha Bello", "aisha", ["HRIS", "Compliance", "Onboarding", "Communication", "Workday"], 4,
     "BA Human Resource Management, University of Lagos",
     "People operations generalist who automated onboarding for a 400-person company.", ["SHRM-CP"]),
    ("Liam O'Connor", "liam", ["Recruiting", "Communication", "Excel"], 1,
     "BA Psychology, Trinity College Dublin",
     "Recruiting coordinator interested in HR operations.", []),
    ("Mei Chen", "mei", ["Figma", "User Research", "Prototyping", "Design Systems", "Accessibility"], 6,
     "BFA Interaction Design, RISD",
     "Product designer who built the design system for an industrial IoT platform.", []),
    ("Noah Fischer", "noah", ["Figma", "Illustration", "Branding"], 2,
     "BA Communication Design, HTW Berlin",
     "Brand and visual designer exploring product design.", []),
    ("Sofia Rossi", "sofia", ["Python", "FastAPI", "PostgreSQL", "Docker", "React"], 6,
     "MSc Computer Engineering, Politecnico di Milano",
     "Platform engineer comfortable across the stack, from APIs to deployment.", ["CKA"]),
    ("Kwame Mensah", "kwame", ["Electronics", "Troubleshooting", "PLC", "Customer Service"], 5,
     "HND Electrical Engineering, Kumasi Technical University",
     "Field service technician for automated conveyor and sorting systems.", []),
]

# candidate email, job index, status, source, days ago applied, days from applying to hire
APPLICATIONS = [
    ("priya", 0, "interview", "referral", 12, None),
    ("marcus", 0, "screening", "linkedin", 6, None),
    ("elena", 0, "applied", "careers_page", 2, None),
    ("sofia", 0, "assessment", "careers_page", 9, None),
    ("diego", 1, "offer", "linkedin", 21, None),
    ("hannah", 1, "interview", "careers_page", 10, None),
    ("tomas", 1, "rejected", "job_board", 25, None),
    ("sofia", 1, "screening", "careers_page", 9, None),
    ("aisha", 2, "hired", "referral", 48, 19),
    ("liam", 2, "rejected", "careers_page", 30, None),
    ("mei", 3, "interview", "linkedin", 8, None),
    ("noah", 3, "applied", "careers_page", 1, None),
    ("kwame", 4, "hired", "job_board", 70, 24),
]

# name, email local part, role, annual base
STAFF = [
    ("Admin User", "admin", "admin", 150000),
    ("Alex Recruiter", "recruiter", "recruiter", 98000),
    ("Sam Employee", "employee", "employee", 112000),
    ("Grace Liu", "grace", "employee", 135000),
    ("Ravi Shah", "ravi", "employee", 121000),
]

# staff email, leave type, start offset in days from today, length in days, status, reason
LEAVE = [
    ("employee", "annual", 14, 5, "pending", "Family trip"),
    ("employee", "sick", -20, 2, "approved", "Flu"),
    ("grace", "annual", 30, 10, "pending", "Wedding and honeymoon"),
    ("ravi", "annual", -45, 3, "approved", "Long weekend"),
    ("ravi", "unpaid", 60, 15, "pending", "Sabbatical project"),
]


async def seed_demo_data() -> None:
    """Idempotent and safe when several workers or services run it at the same time."""
    try:
        await _seed()
    except IntegrityError:
        # Another process inserted the demo org first; its transaction owns the seed.
        pass


async def _seed() -> None:
    from shared.models.entities import Organization

    async with AsyncSessionLocal() as db:
        org = (await db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG))).scalar_one_or_none()
        if org is None:
            org = Organization(name=DEMO_ORG_NAME, slug=DEMO_ORG_SLUG, plan="trial")
            db.add(org)
            await db.flush()
            await _seed_core(db, org.id)
        elif org.name == "Demo Company":
            org.name = DEMO_ORG_NAME
        if not await _has_showcase(db, org.id):
            await _seed_showcase(db, org.id)
        await db.commit()


async def _seed_core(db, org_id: int) -> None:
    from shared.models.entities import Job, User, UserRole

    password = hash_password(DEMO_PASSWORD)
    db.add_all([
        User(organization_id=org_id, email=f"{local}@aihr.demo", hashed_password=password,
             full_name=name, role=UserRole(role))
        for name, local, role, _ in STAFF
    ])
    db.add(User(organization_id=org_id, email="candidate@aihr.demo", hashed_password=password,
                full_name="Jordan Candidate", role=UserRole.CANDIDATE))
    db.add_all([
        Job(organization_id=org_id, title=t, department=d, description=desc, requirements=req,
            required_skills=skills, min_experience_years=years, salary_min=lo, salary_max=hi, status=status)
        for t, d, desc, req, skills, years, lo, hi, status in JOBS
    ])
    await db.flush()


async def _has_showcase(db, org_id: int) -> bool:
    from shared.models.entities import Application

    count = (await db.execute(
        select(func.count()).select_from(Application).where(Application.organization_id == org_id)
    )).scalar()
    return bool(count)


async def _seed_showcase(db, org_id: int) -> None:
    """Candidates across the whole pipeline plus HR records, so every screen has something real to show.

    Match scores are left empty: the matching engine scores them with the real model when it starts.
    """
    from shared.models.entities import (
        Application, ApplicationStatus, CandidateProfile, Interview, Job, OnboardingTask, User, UserRole,
    )
    from shared.models.leave import LeaveRequest, LeaveStatus, LeaveType
    from shared.models.payroll import SalaryProfile

    now = datetime.now(timezone.utc)
    today = date.today()
    password = hash_password(DEMO_PASSWORD)

    users = {u.email: u for u in (await db.execute(select(User).where(User.organization_id == org_id))).scalars()}
    # Workspaces seeded before the showcase existed only have the original staff and jobs.
    for name, local, role, _ in STAFF:
        if f"{local}@aihr.demo" not in users:
            users[f"{local}@aihr.demo"] = User(organization_id=org_id, email=f"{local}@aihr.demo",
                                                hashed_password=password, full_name=name, role=UserRole(role))
            db.add(users[f"{local}@aihr.demo"])
    jobs_by_title = {j.title: j for j in (await db.execute(select(Job).where(Job.organization_id == org_id))).scalars()}
    for t, d, desc, req, skills, years, lo, hi, status in JOBS:
        if t not in jobs_by_title:
            jobs_by_title[t] = Job(organization_id=org_id, title=t, department=d, description=desc, requirements=req,
                                   required_skills=skills, min_experience_years=years, salary_min=lo, salary_max=hi,
                                   status=status)
            db.add(jobs_by_title[t])
    jobs = [jobs_by_title[spec[0]] for spec in JOBS]

    candidates: dict[str, User] = {}
    for name, local, skills, years, education, summary, certs in CANDIDATES:
        user = User(organization_id=org_id, email=f"{local}@candidates.aihr.demo", hashed_password=password,
                    full_name=name, role=UserRole.CANDIDATE, created_at=now - timedelta(days=75))
        db.add(user)
        candidates[local] = user
    await db.flush()

    for name, local, skills, years, education, summary, certs in CANDIDATES:
        parsed = {"name": name, "email": candidates[local].email, "skills": skills, "experience_years": years,
                  "education": education, "certifications": certs, "summary": summary}
        db.add(CandidateProfile(
            organization_id=org_id, user_id=candidates[local].id, parsed_data=parsed, skills=skills,
            experience_years=years, education=education,
            resume_text=f"{name}\n{summary}\nSkills: {', '.join(skills)}\n{years} years experience\n{education}",
        ))

    recruiter_email = "recruiter@aihr.demo"
    for local, job_idx, status, source, days_ago, days_to_hire in APPLICATIONS:
        applied_at = now - timedelta(days=days_ago)
        app = Application(
            organization_id=org_id, job_id=jobs[job_idx].id, candidate_id=candidates[local].id,
            status=ApplicationStatus(status), source=source, created_at=applied_at,
            hired_at=applied_at + timedelta(days=days_to_hire) if days_to_hire else None,
        )
        db.add(app)
        await db.flush()
        if status == "interview":
            db.add(Interview(
                organization_id=org_id, application_id=app.id, interviewer_email=recruiter_email,
                scheduled_at=(now + timedelta(days=2 + job_idx)).replace(hour=15, minute=0, second=0, microsecond=0),
                meeting_link="https://meet.example.com/halcyon-interview", status="scheduled",
            ))
        if status in ("offer", "hired"):
            db.add(Interview(
                organization_id=org_id, application_id=app.id, interviewer_email=recruiter_email,
                scheduled_at=applied_at + timedelta(days=7), status="completed",
                notes="Strong systems thinking; clear communicator. Recommend moving forward.",
            ))
        if status == "hired":
            name = candidates[local].full_name
            tasks = create_onboarding_plan(name, jobs[job_idx].title)
            # The earlier hire is further along, so the onboarding view shows real progress.
            for task in tasks[: 7 if days_ago > 60 else 3]:
                task["completed"] = True
            db.add(OnboardingTask(organization_id=org_id, employee_name=name,
                                  employee_email=candidates[local].email, role=jobs[job_idx].title, tasks=tasks,
                                  status="in_progress"))

    for _, local, _, annual_base in STAFF:
        db.add(SalaryProfile(organization_id=org_id, user_id=users[f"{local}@aihr.demo"].id, annual_base=annual_base))

    reviewer = users["admin@aihr.demo"]
    for local, leave_type, start, length, status, reason in LEAVE:
        db.add(LeaveRequest(
            organization_id=org_id, user_id=users[f"{local}@aihr.demo"].id, leave_type=LeaveType(leave_type),
            start_date=today + timedelta(days=start), end_date=today + timedelta(days=start + length - 1),
            status=LeaveStatus(status), reason=reason,
            reviewed_by_id=reviewer.id if status != "pending" else None,
        ))
