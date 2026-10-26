"""AI-powered interview scoring and evaluation service."""

import logging
from datetime import datetime
from shared.services.ai_llm import (
    generate_interview_score_explanation,
    get_llm,
)

logger = logging.getLogger(__name__)


async def score_interview(
    interview_id: int,
    candidate_name: str,
    job_title: str,
    technical_assessment: str,
    communication_assessment: str,
    interviewer_notes: str,
    performance_metrics: dict | None = None,
) -> dict:
    """
    Score interview using AI analysis.

    Args:
        interview_id: Interview ID
        candidate_name: Candidate name
        job_title: Target job title
        technical_assessment: Technical skills evaluation
        communication_assessment: Communication ability evaluation
        interviewer_notes: Interviewer's notes
        performance_metrics: Optional metrics dict with scores

    Returns:
        Interview score and AI explanation
    """
    metrics = performance_metrics or {}
    tech_score = metrics.get("technical", 7.0)
    comm_score = metrics.get("communication", 7.0)
    problem_solving = metrics.get("problem_solving", 7.0)
    culture_fit = metrics.get("culture_fit", 7.0)

    # Calculate composite score
    composite = (tech_score * 0.35 + comm_score * 0.25 + problem_solving * 0.25 + culture_fit * 0.15)
    
    # Get AI explanation
    try:
        ai_analysis = await generate_interview_score_explanation(
            candidate_name,
            f"Technical: {technical_assessment}. Communication: {communication_assessment}. Notes: {interviewer_notes}",
            tech_score,
            comm_score,
        )
        explanation = ai_analysis.get("explanation", "")
    except Exception as e:
        logger.warning(f"AI explanation failed: {e}")
        explanation = f"Candidate {candidate_name} interviewed for {job_title}. Technical skills: {tech_score}/10, Communication: {comm_score}/10."

    return {
        "interview_id": interview_id,
        "candidate_name": candidate_name,
        "job_title": job_title,
        "scores": {
            "technical": round(tech_score, 1),
            "communication": round(comm_score, 1),
            "problem_solving": round(problem_solving, 1),
            "culture_fit": round(culture_fit, 1),
            "composite": round(composite, 1),
        },
        "recommendation": "Proceed to next round" if composite >= 7.0 else ("Hold for feedback" if composite >= 6.0 else "Consider alternative candidates"),
        "ai_analysis": explanation,
        "scored_at": datetime.utcnow().isoformat(),
    }


async def get_interview_insights(
    interviews: list[dict],
) -> dict:
    """
    Get AI insights from multiple interviews.

    Args:
        interviews: List of interview records

    Returns:
        Aggregated insights and recommendations
    """
    if not interviews:
        return {
            "total_interviews": 0,
            "insights": "No interviews to analyze yet.",
        }

    avg_technical = sum(i.get("scores", {}).get("technical", 0) for i in interviews) / len(interviews)
    avg_communication = sum(i.get("scores", {}).get("communication", 0) for i in interviews) / len(interviews)
    avg_composite = sum(i.get("scores", {}).get("composite", 0) for i in interviews) / len(interviews)

    insights = f"""
Interview Analysis Summary:
- Total Interviews: {len(interviews)}
- Average Technical Score: {avg_technical:.1f}/10
- Average Communication Score: {avg_communication:.1f}/10
- Average Composite Score: {avg_composite:.1f}/10

Trend: {('Improving' if len(interviews) > 3 and avg_composite > 7.5 else 'Stable' if avg_composite >= 7.0 else 'Needs Improvement')}

Key Observation: {'Strong candidate pipeline' if avg_composite >= 7.5 else 'Good mix of candidates' if avg_composite >= 7.0 else 'Review interview criteria and screening process'}
"""

    return {
        "total_interviews": len(interviews),
        "average_scores": {
            "technical": round(avg_technical, 1),
            "communication": round(avg_communication, 1),
            "composite": round(avg_composite, 1),
        },
        "insights": insights.strip(),
    }


async def predict_hire_success(
    candidate_profile: dict,
    team_context: dict | None = None,
) -> dict:
    """
    Predict likelihood of hire success using AI.

    Args:
        candidate_profile: Candidate info (scores, skills, experience)
        team_context: Optional team dynamics info

    Returns:
        Success prediction and recommendations
    """
    llm = await get_llm()
    
    scores = candidate_profile.get("scores", {})
    composite = scores.get("composite", 0)
    
    # AI prediction factors
    factors = {
        "Technical Alignment": scores.get("technical", 0) / 10,
        "Communication": scores.get("communication", 0) / 10,
        "Problem Solving": scores.get("problem_solving", 0) / 10,
        "Culture Fit": scores.get("culture_fit", 0) / 10,
        "Experience Match": candidate_profile.get("experience_match", 0.7),
    }

    weights = [0.30, 0.15, 0.20, 0.20, 0.15]
    success_probability = sum(v * w for v, w in zip(factors.values(), weights, strict=True))
    
    system = """You are an expert HR prediction model. Assess likelihood of successful hire."""
    
    prompt = f"""
Candidate Success Prediction:
- Composite Interview Score: {composite:.1f}/10
- Technical Skills: {scores.get('technical', 0):.1f}/10
- Communication: {scores.get('communication', 0):.1f}/10
- Problem Solving: {scores.get('problem_solving', 0):.1f}/10
- Culture Fit: {scores.get('culture_fit', 0):.1f}/10
- Success Probability: {success_probability:.1%}

Provide a prediction of success within 6 months with reasoning.
"""

    try:
        ai_assessment = await llm.generate(prompt, system, max_tokens=200)
    except Exception as e:
        logger.warning(f"AI prediction failed: {e}")
        ai_assessment = f"Candidate shows {'strong' if success_probability > 0.75 else 'moderate' if success_probability > 0.5 else 'developing'} potential for success."

    return {
        "success_probability": round(success_probability, 2),
        "confidence_level": "High" if success_probability > 0.8 else "Moderate" if success_probability > 0.6 else "Low",
        "key_factors": factors,
        "ai_assessment": ai_assessment,
        "recommendation": "Strong hire" if success_probability > 0.8 else ("Promising candidate" if success_probability > 0.65 else "Needs further evaluation"),
    }
