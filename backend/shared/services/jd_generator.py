from shared.schemas.common import JDGenerateRequest, JDGenerateResponse

BIAS_TERMS = [
    "rockstar", "ninja", "guru", "young", "energetic", "native english speaker",
    "digital native", "guys", "he/she", "manpower",
]


def generate_job_description(req: JDGenerateRequest) -> JDGenerateResponse:
    skills = req.key_skills or ["Communication", "Problem solving", "Collaboration"]
    seniority_map = {
        "junior": (2, 5, "0-2 years"),
        "mid": (4, 8, "3-5 years"),
        "senior": (6, 12, "5+ years"),
        "lead": (8, 15, "8+ years"),
    }
    sal_min, sal_max, exp_label = seniority_map.get(req.seniority.lower(), seniority_map["mid"])

    description = (
        f"We are seeking a {req.seniority} {req.title} to join our {req.department} team. "
        f"You will contribute to meaningful projects, collaborate with cross-functional partners, "
        f"and help deliver high-quality outcomes. We value diverse perspectives and inclusive teamwork."
    )

    responsibilities = [
        f"Design, build, and maintain solutions as a {req.title}",
        "Collaborate with product, design, and engineering stakeholders",
        "Participate in code/design reviews and continuous improvement",
        "Mentor teammates and document best practices",
        "Contribute to hiring and team culture initiatives",
    ]

    requirements = [
        f"{exp_label} relevant experience",
        f"Proficiency in: {', '.join(skills[:5])}",
        "Strong written and verbal communication",
        "Experience working in agile, cross-functional teams",
        "Commitment to inclusive and ethical practices",
    ]

    salary_band = f"${sal_min * 10000:,} – ${sal_max * 10000:,} (region-dependent)"

    bias_warnings = []
    combined = f"{description} {' '.join(requirements)}".lower()
    for term in BIAS_TERMS:
        if term in combined:
            bias_warnings.append(f"Avoid biased term: '{term}'")

    return JDGenerateResponse(
        title=req.title,
        description=description,
        responsibilities=responsibilities,
        requirements=requirements,
        skills=skills,
        salary_band=salary_band,
        bias_warnings=bias_warnings,
    )
