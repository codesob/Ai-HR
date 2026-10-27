"""AI-powered predictive hiring analytics."""

import logging
from datetime import datetime, timedelta, timezone
from shared.services.ai_llm import generate_hiring_insights, get_llm

logger = logging.getLogger(__name__)


def _naive_utc(value: datetime | str) -> datetime:
    """Parse ISO strings and convert aware datetimes to naive UTC so they compare with utcnow()."""
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


async def analyze_hiring_pipeline(
    applications: list[dict],
    interviews: list[dict],
    hires: list[dict],
) -> dict:
    """
    Analyze hiring pipeline with AI insights.

    Args:
        applications: List of applications
        interviews: List of interviews
        hires: List of completed hires

    Returns:
        Pipeline analysis with predictions
    """
    now = datetime.utcnow()
    last_30_days = now - timedelta(days=30)

    recent_hires = len([h for h in hires if _naive_utc(h.get("created_at", now)) > last_30_days])
    total_applications = len(applications)
    pending_interviews = len([i for i in interviews if i.get("status") == "scheduled"])
    conversion_rate = (recent_hires / total_applications * 100) if total_applications > 0 else 0

    # Only verified metrics go to the LLM: open positions and time-to-hire aren't known here.
    try:
        insights = await generate_hiring_insights(recent_hires_count=recent_hires)
        ai_insights = insights.get("insights", "")
    except Exception as e:
        logger.warning(f"AI insights generation failed: {e}")
        ai_insights = f"Pipeline shows {conversion_rate:.1f}% conversion rate. {recent_hires} hires in last 30 days."

    return {
        "metrics": {
            "total_applications": total_applications,
            "recent_hires": recent_hires,
            "pending_interviews": pending_interviews,
            "conversion_rate": round(conversion_rate, 1),
        },
        "health_status": "Healthy" if conversion_rate > 10 else "Moderate" if conversion_rate > 5 else "Needs Improvement",
        "ai_insights": ai_insights,
        "timestamp": now.isoformat(),
    }


async def predict_time_to_hire(
    job_posting_date: str,
    num_applications: int,
    avg_interview_score: float,
) -> dict:
    """
    Predict time to hire using historical patterns.

    Args:
        job_posting_date: When job was posted
        num_applications: Number of applications received
        avg_interview_score: Average interview score so far

    Returns:
        Time to hire prediction
    """
    posting_date = _naive_utc(job_posting_date)
    days_open = (datetime.utcnow() - posting_date).days
    
    # ML-based estimation
    base_days = 21
    app_factor = max(0, (num_applications - 10) * 0.5)
    quality_factor = (avg_interview_score / 10 - 0.5) * -5  # Better candidates = faster
    
    predicted_days = base_days + app_factor + quality_factor
    predicted_days = max(5, min(60, predicted_days))  # Bound between 5-60 days

    return {
        "current_days_open": days_open,
        "predicted_total_days": round(predicted_days),
        "predicted_remaining_days": max(0, round(predicted_days - days_open)),
        "confidence": "High" if num_applications >= 20 else "Moderate" if num_applications >= 10 else "Low",
        "recommendation": "On track" if days_open <= predicted_days else "Behind schedule - consider widening candidate pool",
    }


async def candidate_quality_score(
    match_score: float,
    interview_score: float,
    experience_years: float,
    required_experience: float,
    skills_match_percent: float,
) -> dict:
    """
    Calculate AI-powered candidate quality score.

    Args:
        match_score: Initial match score (0-1)
        interview_score: Interview composite score (0-10)
        experience_years: Candidate's experience
        required_experience: Required experience for role
        skills_match_percent: % of required skills matched

    Returns:
        Quality score and grade
    """
    llm = await get_llm()
    
    # Normalize scores
    match_normalized = match_score  # 0-1
    interview_normalized = interview_score / 10  # Convert to 0-1
    experience_normalized = min(1.0, experience_years / required_experience) if required_experience > 0 else 1.0
    skills_normalized = skills_match_percent / 100  # Convert percent to 0-1

    # Weighted composite
    weights = [0.25, 0.35, 0.20, 0.20]
    composite = sum([
        match_normalized * weights[0],
        interview_normalized * weights[1],
        experience_normalized * weights[2],
        skills_normalized * weights[3],
    ])

    # Grade
    if composite >= 0.85:
        grade = "A"
        tier = "Top Tier"
    elif composite >= 0.70:
        grade = "B"
        tier = "Strong"
    elif composite >= 0.55:
        grade = "C"
        tier = "Viable"
    else:
        grade = "D"
        tier = "Needs Development"

    system = "You are a talent quality assessment expert. Provide hiring recommendation based on quality metrics."
    prompt = f"""
Candidate Quality Assessment:
- Match Score: {match_score:.1%}
- Interview Score: {interview_score:.1f}/10
- Experience: {experience_years:.1f} years (required: {required_experience:.1f})
- Skills Match: {skills_match_percent:.1f}%
- Overall Quality Score: {composite:.1%} ({grade})

Provide a one-sentence hiring recommendation.
"""

    try:
        recommendation = await llm.generate(prompt, system, max_tokens=50)
    except Exception as e:
        logger.warning(f"Quality assessment failed: {e}")
        recommendation = f"{tier} candidate. Quality tier: {grade}."

    return {
        "quality_score": round(composite, 2),
        "grade": grade,
        "tier": tier,
        "components": {
            "match_score": round(match_normalized, 2),
            "interview_score": round(interview_normalized, 2),
            "experience_fit": round(experience_normalized, 2),
            "skills_fit": round(skills_normalized, 2),
        },
        "recommendation": recommendation,
    }


async def hiring_trend_analysis(
    historical_data: list[dict],
) -> dict:
    """
    Analyze hiring trends and predict future needs.

    Args:
        historical_data: Historical hiring records with timestamps

    Returns:
        Trend analysis and predictions
    """
    if not historical_data:
        return {
            "trend": "Insufficient data",
            "monthly_average": 0,
            "prediction_q_next": "Increase data collection for predictions",
        }

    # Group by month and calculate averages
    monthly_hires = {}
    for record in historical_data:
        date = _naive_utc(record.get("created_at", datetime.utcnow().isoformat()))
        month_key = date.strftime("%Y-%m")
        monthly_hires[month_key] = monthly_hires.get(month_key, 0) + 1

    recent_months = sorted(monthly_hires.keys())[-3:]
    recent_values = [monthly_hires[m] for m in recent_months]
    average = sum(recent_values) / len(recent_values) if recent_values else 0

    # Calculate trend
    if len(recent_values) >= 2:
        trend = "Increasing" if recent_values[-1] > recent_values[0] else "Decreasing" if recent_values[-1] < recent_values[0] else "Stable"
    else:
        trend = "Insufficient data"

    return {
        "trend": trend,
        "monthly_average": round(average, 1),
        "recent_hires": recent_values,
        "recent_months": recent_months,
        "next_quarter_prediction": round(average * 3.2),  # 3-4 months
        "recommendation": "Maintain current recruitment pace" if average >= 3 else "Increase recruiting efforts",
    }
