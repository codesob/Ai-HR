"""AI-powered insights dashboard for HR analytics."""

import logging
from datetime import datetime
from shared.services.ai_llm import get_llm

logger = logging.getLogger(__name__)


async def generate_dashboard_insights(
    hiring_metrics: dict,
    employee_metrics: dict,
    performance_data: dict | None = None,
) -> dict:
    """
    Generate comprehensive AI insights for HR dashboard.

    Args:
        hiring_metrics: Hiring pipeline metrics
        employee_metrics: Employee-related metrics
        performance_data: Optional performance data

    Returns:
        Comprehensive dashboard insights
    """
    llm = await get_llm()
    
    system = """You are an expert HR strategist. Analyze hiring and employee metrics 
to provide strategic insights and actionable recommendations."""
    
    hiring_str = ", ".join([f"{k}: {v}" for k, v in hiring_metrics.items()])
    employee_str = ", ".join([f"{k}: {v}" for k, v in employee_metrics.items()])
    
    prompt = f"""
HR Metrics Summary:

Hiring Pipeline:
{hiring_str}

Employee Metrics:
{employee_str}

Provide:
1. Overall HR health assessment
2. Key achievements (2-3)
3. Areas for improvement (2-3)
4. Strategic recommendations (2-3)
5. 30-day action items (top 3)
"""

    try:
        insights = await llm.generate(prompt, system, max_tokens=400)
    except Exception as e:
        logger.warning(f"Dashboard insights failed: {e}")
        insights = "Dashboard analysis in progress. Review individual metrics for detailed insights."

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "metrics": {
            "hiring": hiring_metrics,
            "employee": employee_metrics,
        },
        "executive_summary": insights,
        "health_status": calculate_health_status(hiring_metrics, employee_metrics),
    }


async def get_hiring_dashboard(
    total_applications: int,
    pending_interviews: int,
    recent_hires: int,
    average_time_to_hire: float,
    acceptance_rate: float,
) -> dict:
    """
    Generate hiring-focused dashboard insights.

    Args:
        total_applications: Total applications received
        pending_interviews: Pending interview count
        recent_hires: Recent hires count
        average_time_to_hire: Average days to hire
        acceptance_rate: Offer acceptance rate

    Returns:
        Hiring dashboard data
    """
    llm = await get_llm()
    
    # Calculate metrics
    interview_rate = (pending_interviews / total_applications * 100) if total_applications > 0 else 0
    efficiency_score = calculate_hiring_efficiency(
        total_applications, pending_interviews, recent_hires, average_time_to_hire
    )

    system = """You are a talent acquisition expert. Provide insights on hiring effectiveness."""
    
    prompt = f"""
Hiring Funnel:
- Applications: {total_applications}
- Interview Rate: {interview_rate:.1f}%
- Recent Hires: {recent_hires}
- Avg Time to Hire: {average_time_to_hire:.0f} days
- Offer Acceptance Rate: {acceptance_rate:.1%}
- Efficiency Score: {efficiency_score:.1f}/10

Provide brief assessment and recommendations.
"""

    try:
        assessment = await llm.generate(prompt, system, max_tokens=200)
    except Exception as e:
        logger.warning(f"Hiring assessment failed: {e}")
        assessment = f"Hiring pipeline shows {efficiency_score:.1f}/10 efficiency. Interview rate: {interview_rate:.1f}%."

    return {
        "section": "Hiring Pipeline",
        "metrics": {
            "total_applications": total_applications,
            "pending_interviews": pending_interviews,
            "interview_rate_percent": round(interview_rate, 1),
            "recent_hires": recent_hires,
            "average_time_to_hire_days": round(average_time_to_hire, 0),
            "acceptance_rate": round(acceptance_rate, 3),
            "efficiency_score": round(efficiency_score, 1),
        },
        "status": "Healthy" if efficiency_score >= 7 else "Moderate" if efficiency_score >= 5 else "Needs Improvement",
        "ai_assessment": assessment,
    }


async def get_employee_dashboard(
    total_employees: int,
    recent_onboardings: int,
    retention_rate: float,
    avg_tenure_months: float,
    active_development_plans: int,
) -> dict:
    """
    Generate employee-focused dashboard insights.

    Args:
        total_employees: Total active employees
        recent_onboardings: Recent onboarding count
        retention_rate: Employee retention rate
        avg_tenure_months: Average tenure in months
        active_development_plans: Active development plans count

    Returns:
        Employee dashboard data
    """
    llm = await get_llm()
    
    onboarding_rate = (recent_onboardings / max(1, total_employees)) * 100

    system = """You are an HR strategy expert. Assess employee engagement and retention trends."""
    
    prompt = f"""
Employee Metrics:
- Total Employees: {total_employees}
- New Hires (recent): {recent_onboardings}
- Retention Rate: {retention_rate:.1%}
- Avg Tenure: {avg_tenure_months:.1f} months
- Development Plans Active: {active_development_plans}

Assess employee health and provide recommendations.
"""

    try:
        assessment = await llm.generate(prompt, system, max_tokens=200)
    except Exception as e:
        logger.warning(f"Employee assessment failed: {e}")
        assessment = f"Employee retention at {retention_rate:.1%}. {active_development_plans} development plans active."

    return {
        "section": "Employee Health",
        "metrics": {
            "total_employees": total_employees,
            "recent_onboardings": recent_onboardings,
            "onboarding_rate_percent": round(onboarding_rate, 1),
            "retention_rate": round(retention_rate, 3),
            "average_tenure_months": round(avg_tenure_months, 1),
            "active_development_plans": active_development_plans,
        },
        "status": "Healthy" if retention_rate > 0.95 else "Good" if retention_rate > 0.90 else "Needs Attention",
        "ai_assessment": assessment,
    }


async def predict_hiring_needs(
    current_headcount: int,
    planned_growth_percent: float,
    recent_attrition_rate: float,
    average_time_to_hire_days: float,
) -> dict:
    """
    Predict future hiring needs using AI analysis.

    Args:
        current_headcount: Current employee count
        planned_growth_percent: Planned growth percentage
        recent_attrition_rate: Recent attrition rate
        average_time_to_hire_days: Average hiring timeline

    Returns:
        Hiring needs forecast
    """
    llm = await get_llm()
    
    # Calculate predicted needs
    growth_hires = int(current_headcount * (planned_growth_percent / 100))
    attrition_replacement = int(current_headcount * recent_attrition_rate)
    total_needed = growth_hires + attrition_replacement
    recruitment_lead_time = int(average_time_to_hire_days / 30)  # months

    system = """You are an HR planning expert. Forecast hiring needs based on growth and attrition."""
    
    prompt = f"""
Hiring Forecast:
- Current Headcount: {current_headcount}
- Growth Target: +{planned_growth_percent:.0f}%
- Attrition Rate: {recent_attrition_rate:.1%}
- Total Hires Needed: {total_needed}
- Lead Time: {recruitment_lead_time} months

Provide recruitment strategy and timeline recommendations.
"""

    try:
        forecast = await llm.generate(prompt, system, max_tokens=250)
    except Exception as e:
        logger.warning(f"Hiring forecast failed: {e}")
        forecast = f"Plan to hire {total_needed} employees. Begin recruitment {recruitment_lead_time} months in advance."

    return {
        "forecast_period": "12 months",
        "current_headcount": current_headcount,
        "hiring_needs": {
            "growth_hires": growth_hires,
            "attrition_replacement": attrition_replacement,
            "total_needed": total_needed,
        },
        "recruitment_timeline": {
            "months_lead_time": recruitment_lead_time,
            "start_recruitment": f"Month {max(1, recruitment_lead_time - 1)}",
            "expected_completion": f"Month {12 if total_needed <= 10 else 12}",
        },
        "ai_forecast": forecast,
    }


# Helper functions

def calculate_health_status(hiring: dict, employee: dict) -> str:
    """Calculate overall HR health status."""
    hiring_efficiency = hiring.get("efficiency_score", 5) / 10
    retention = employee.get("retention_rate", 0.85)
    
    composite = (hiring_efficiency * 0.4) + (retention * 0.6)
    
    if composite >= 0.8:
        return "Excellent"
    elif composite >= 0.65:
        return "Good"
    elif composite >= 0.5:
        return "Needs Improvement"
    else:
        return "Critical"


def calculate_hiring_efficiency(
    applications: int,
    interviews: int,
    hires: int,
    time_to_hire: float,
) -> float:
    """Calculate hiring efficiency score."""
    # Normalize metrics (all 0-10)
    interview_rate = min(10, (interviews / max(1, applications)) * 20)  # Goal: >50%
    hire_rate = min(10, (hires / max(1, interviews)) * 10)  # Goal: >33%
    speed = min(10, 30 / time_to_hire)  # Goal: 30 days
    
    # Weighted average
    efficiency = (interview_rate * 0.3) + (hire_rate * 0.4) + (speed * 0.3)
    return min(10, efficiency)
