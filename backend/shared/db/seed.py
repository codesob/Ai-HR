from sqlalchemy import select

from shared.core.security import hash_password
from shared.db.session import AsyncSessionLocal, Base, engine
from shared.models.entities import Job, User, UserRole


async def seed_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "recruiter@aihr.demo"))
        if result.scalar_one_or_none():
            return

        users = [
            User(
                email="admin@aihr.demo",
                hashed_password=hash_password("demo12345"),
                full_name="Admin User",
                role=UserRole.ADMIN,
            ),
            User(
                email="recruiter@aihr.demo",
                hashed_password=hash_password("demo12345"),
                full_name="Alex Recruiter",
                role=UserRole.RECRUITER,
            ),
            User(
                email="candidate@aihr.demo",
                hashed_password=hash_password("demo12345"),
                full_name="Jordan Candidate",
                role=UserRole.CANDIDATE,
            ),
        ]
        db.add_all(users)

        jobs = [
            Job(
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
        db.add_all(jobs)
        await db.commit()
