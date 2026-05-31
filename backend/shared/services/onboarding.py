DEFAULT_ONBOARDING_TASKS = [
    {"id": "doc-1", "title": "Submit signed offer letter", "category": "documents", "completed": False},
    {"id": "doc-2", "title": "Complete ID verification", "category": "compliance", "completed": False},
    {"id": "it-1", "title": "IT account provisioning (email, SSO)", "category": "it", "completed": False},
    {"id": "it-2", "title": "Equipment request (laptop, accessories)", "category": "it", "completed": False},
    {"id": "hr-1", "title": "Acknowledge employee handbook", "category": "policy", "completed": False},
    {"id": "hr-2", "title": "Benefits enrollment", "category": "hr", "completed": False},
    {"id": "sec-1", "title": "Security & data privacy training", "category": "training", "completed": False},
    {"id": "team-1", "title": "Meet your onboarding buddy", "category": "culture", "completed": False},
]


def create_onboarding_plan(employee_name: str, role: str) -> list[dict]:
    tasks = [dict(t) for t in DEFAULT_ONBOARDING_TASKS]
    tasks.append({
        "id": "role-1",
        "title": f"Role-specific orientation: {role}",
        "category": "training",
        "completed": False,
    })
    return tasks
