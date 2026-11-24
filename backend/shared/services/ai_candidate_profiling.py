"""AI-powered candidate profiling and insights."""

import logging
from shared.services.ai_llm import generate_candidate_insights, get_llm

logger = logging.getLogger(__name__)


async def profile_candidate(
    candidate_id: str,
    name: str,
    email: str,
    skills: list[str],
    experience_years: float,
    education: str,
    previous_roles: list[str],
    target_role: str,
    match_score: float,
    interview_scores: dict | None = None,
) -> dict:
    """
    Create AI-powered candidate profile with insights.

    Args:
        candidate_id: Unique candidate ID
        name: Candidate name
        email: Email address
        skills: List of skills
        experience_years: Total years of experience
        education: Education background
        previous_roles: List of previous roles
        target_role: Target position
        match_score: Job match score (0-1)
        interview_scores: Optional interview scores dict

    Returns:
        Comprehensive candidate profile with AI insights
    """
    interviews = interview_scores or {}
    
    try:
        insights = await generate_candidate_insights(
            name=name,
            skills=skills,
            experience_years=experience_years,
            match_score=match_score,
            job_title=target_role,
        )
        ai_insights = insights.get("insights", "")
    except Exception as e:
        logger.warning(f"Candidate insights generation failed: {e}")
        ai_insights = f"Candidate with {experience_years:.1f} years experience targeting {target_role}. Match score: {match_score:.1%}."

    # Skill assessment
    skill_level = categorize_experience_level(experience_years)
    
    # Strengths and gaps
    strengths = extract_strengths(skills, experience_years)
    gaps = identify_skill_gaps(skills, target_role)

    return {
        "candidate_id": candidate_id,
        "name": name,
        "email": email,
        "profile": {
            "experience_level": skill_level,
            "total_experience_years": experience_years,
            "education": education,
            "previous_roles": previous_roles,
            "current_skills": skills,
            "skill_count": len(skills),
        },
        "job_fit": {
            "target_role": target_role,
            "match_score": round(match_score, 2),
            "interview_scores": interviews,
            "composite_score": round(calculate_composite_score(match_score, interviews), 2),
        },
        "assessment": {
            "key_strengths": strengths,
            "skill_gaps": gaps,
            "growth_potential": assess_growth_potential(experience_years, len(skills)),
            "retention_risk": assess_retention_risk(experience_years, skill_level),
        },
        "ai_insights": ai_insights,
        "readiness_score": calculate_readiness(match_score, interviews),
    }


async def generate_hiring_recommendation_for_candidate(
    candidate_profile: dict,
    other_candidates: list[dict] | None = None,
) -> dict:
    """
    Generate detailed hiring recommendation for a candidate.

    Args:
        candidate_profile: Candidate profile dict
        other_candidates: Optional list of other candidates for comparison

    Returns:
        Detailed hiring recommendation
    """
    llm = await get_llm()
    
    name = candidate_profile.get("name", "Candidate")
    match = candidate_profile.get("job_fit", {}).get("match_score", 0)
    composite = candidate_profile.get("job_fit", {}).get("composite_score", 0)
    strengths = candidate_profile.get("assessment", {}).get("key_strengths", [])
    gaps = candidate_profile.get("assessment", {}).get("skill_gaps", [])
    
    system = """You are a senior talent acquisition expert. Provide actionable, data-driven 
hiring recommendations with clear rationale."""
    
    prompt = f"""
Candidate: {name}
Match Score: {match:.1%}
Composite Assessment: {composite:.2f}
Key Strengths: {', '.join(strengths[:3])}
Skill Gaps: {', '.join(gaps[:2]) if gaps else 'None identified'}

Provide hiring recommendation including:
1. Final recommendation (Hire/Further Discussion/Hold/Decline)
2. Risk assessment (if any)
3. Onboarding focus areas
4. Career development path
"""

    try:
        recommendation = await llm.generate(prompt, system=system, max_tokens=300)
    except Exception as e:
        logger.warning(f"Recommendation generation failed: {e}")
        recommendation = f"Based on assessment: {name} shows {'strong' if composite > 0.75 else 'moderate' if composite > 0.5 else 'developing'} readiness."

    recommendation_level = determine_recommendation_level(match, composite, gaps)
    
    return {
        "candidate_name": name,
        "recommendation_level": recommendation_level,
        "match_score": round(match, 2),
        "composite_score": round(composite, 2),
        "detailed_recommendation": recommendation,
        "decision": "Proceed" if composite > 0.7 else "Further Discussion" if composite > 0.5 else "Hold",
    }


# Helper functions

def categorize_experience_level(years: float) -> str:
    """Categorize experience level."""
    if years < 2:
        return "Entry-Level"
    elif years < 5:
        return "Mid-Level"
    elif years < 10:
        return "Senior"
    else:
        return "Principal/Lead"


def extract_strengths(skills: list[str], experience_years: float) -> list[str]:
    """Extract key strengths from skills and experience."""
    strengths = []
    
    if experience_years >= 10:
        strengths.append("Extensive Industry Experience")
    if experience_years >= 5:
        strengths.append("Proven Track Record")
    
    technical_skills = [s for s in skills if any(tech in s.lower() for tech in 
                        ["python", "java", "sql", "aws", "cloud", "data", "ml"])]
    if technical_skills:
        strengths.append(f"Strong Technical Foundation ({len(technical_skills)} tech skills)")
    
    soft_skills = [s for s in skills if any(soft in s.lower() for soft in
                   ["leadership", "communication", "management", "agile"])]
    if soft_skills:
        strengths.append("Leadership & Communication Skills")
    
    return strengths[:3] if strengths else ["Technical Competence"]


def identify_skill_gaps(current_skills: list[str], target_role: str) -> list[str]:
    """Identify potential skill gaps."""
    gaps = []
    
    # Common required skills for different roles
    role_requirements = {
        "senior": ["leadership", "mentoring", "strategic thinking"],
        "lead": ["team management", "architecture", "decision making"],
        "engineer": ["coding", "testing", "debugging"],
        "manager": ["people management", "communication", "planning"],
        "analyst": ["data analysis", "visualization", "reporting"],
    }
    
    role_lower = target_role.lower()
    required = []
    for role_key, skills_list in role_requirements.items():
        if role_key in role_lower:
            required = skills_list
            break
    
    current_lower = [s.lower() for s in current_skills]
    for skill in required:
        if not any(skill in s for s in current_lower):
            gaps.append(skill.title())
    
    return gaps[:2]


def assess_growth_potential(experience_years: float, skill_count: int) -> str:
    """Assess candidate growth potential."""
    if experience_years < 2 and skill_count >= 5:
        return "High - Quick learner with solid foundation"
    elif experience_years >= 5 and skill_count >= 8:
        return "High - Ready for advancement"
    elif experience_years < 5 or skill_count < 5:
        return "Moderate - Needs development"
    else:
        return "Depends on motivation and mentorship"


def assess_retention_risk(experience_years: float, level: str) -> str:
    """Assess retention risk."""
    if level in ["Senior", "Principal/Lead"] and experience_years >= 10:
        return "Moderate-High - May seek new challenges"
    elif experience_years < 2:
        return "Moderate - Early career may explore options"
    else:
        return "Low-Moderate"


def calculate_composite_score(match_score: float, interview_scores: dict) -> float:
    """Calculate composite score from match and interview."""
    interview_avg = sum(interview_scores.values()) / len(interview_scores) / 10 if interview_scores else 0.5
    
    return (match_score * 0.4) + (interview_avg * 0.6)


def calculate_readiness(match_score: float, interview_scores: dict) -> dict:
    """Calculate overall readiness score."""
    composite = calculate_composite_score(match_score, interview_scores)
    
    if composite >= 0.8:
        readiness = "Ready Now"
        confidence = "Very High"
    elif composite >= 0.7:
        readiness = "Ready Soon"
        confidence = "High"
    elif composite >= 0.6:
        readiness = "With Support"
        confidence = "Moderate"
    else:
        readiness = "Not Ready"
        confidence = "Low"
    
    return {
        "readiness": readiness,
        "confidence": confidence,
        "score": round(composite, 2),
    }


def determine_recommendation_level(match_score: float, composite: float, gaps: list[str]) -> str:
    """Determine recommendation level."""
    if composite >= 0.8 and len(gaps) <= 1:
        return "Strong Hire"
    elif composite >= 0.7:
        return "Good Fit"
    elif composite >= 0.6 and len(gaps) <= 2:
        return "Promising"
    elif composite >= 0.5:
        return "Potential"
    else:
        return "Not Recommended"
