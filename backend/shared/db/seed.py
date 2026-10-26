"""Demo tenant for local development. Never runs in production unless SEED_DEMO_DATA=true."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from shared.core.security import hash_password
from shared.db.session import AsyncSessionLocal

DEMO_ORG_SLUG = "demo"
DEMO_PASSWORD = "demo12345"


async def seed_demo_data() -> None:
    """Idempotent and safe when several workers or services run it at the same time."""
    try:
        await _seed()
    except IntegrityError:
        # Another process inserted the demo org first; its transaction owns the seed.
        pass


async def _seed() -> None:
    from shared.models.entities import Job, Organization, User, UserRole

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG))
        if result.scalar_one_or_none():
            return

        org = Organization(name="Demo Company", slug=DEMO_ORG_SLUG, plan="trial")
        db.add(org)
        await db.flush()

        password = hash_password(DEMO_PASSWORD)
        db.add_all(
            [
                User(organization_id=org.id, email="admin@aihr.demo", hashed_password=password,
                     full_name="Admin User", role=UserRole.ADMIN),
                User(organization_id=org.id, email="recruiter@aihr.demo", hashed_password=password,
                     full_name="Alex Recruiter", role=UserRole.RECRUITER),
                User(organization_id=org.id, email="employee@aihr.demo", hashed_password=password,
                     full_name="Sam Employee", role=UserRole.EMPLOYEE),
                User(organization_id=org.id, email="candidate@aihr.demo", hashed_password=password,
                     full_name="Jordan Candidate", role=UserRole.CANDIDATE),
            ]
        )
        db.add_all(
            [
                Job(
                    organization_id=org.id,
                    title="Senior ML Engineer",
                    department="Engineering",
                    description="Build and deploy ML systems including RAG pipelines and ranking models.",
                    requirements="5+ years Python, PyTorch, production ML experience.",
                    required_skills=["Python", "PyTorch", "RAG", "FastAPI", "Docker"],
                    min_experience_years=5,
                    salary_min=140000,
                    salary_max=190000,
                ),
                Job(
                    organization_id=org.id,
                    title="Full Stack Developer",
                    department="Engineering",
                    description="Develop Next.js and FastAPI features for our HR platform.",
                    requirements="3+ years React and backend API development.",
                    required_skills=["React", "Next.js", "TypeScript", "FastAPI", "PostgreSQL"],
                    min_experience_years=3,
                    salary_min=100000,
                    salary_max=140000,
                ),
                Job(
                    organization_id=org.id,
                    title="HR Operations Specialist",
                    department="People",
                    description="Automate onboarding, compliance, and employee lifecycle workflows.",
                    requirements="HRIS experience and process optimization skills.",
                    required_skills=["HRIS", "Compliance", "Onboarding", "Communication"],
                    min_experience_years=2,
                    salary_min=70000,
                    salary_max=95000,
                ),
            ]
        )
        await db.commit()
