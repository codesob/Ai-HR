"""AI-powered personalized onboarding service."""

import logging
from datetime import datetime
from shared.services.ai_llm import generate_onboarding_plan, get_llm

logger = logging.getLogger(__name__)


async def create_onboarding_plan(
    employee_id: str,
    name: str,
    role: str,
    department: str,
    skills: list[str],
    experience_level: str,
    team_members: list[str] | None = None,
    manager_id: str | None = None,
) -> dict:
    """
    Create personalized AI-driven onboarding plan.

    Args:
        employee_id: Employee ID
        name: Employee name
        role: Job role
        department: Department
        skills: Key skills
        experience_level: Experience level (Entry/Mid/Senior/Principal)
        team_members: List of team member names
        manager_id: Manager employee ID

    Returns:
        Personalized onboarding plan
    """
    team_size = len(team_members) if team_members else 0
    
    try:
        plan = await generate_onboarding_plan(
            candidate_name=name,
            role=role,
            skills=skills,
            team_size=team_size,
        )
        ai_plan = plan.get("onboarding_plan", "")
    except Exception as e:
        logger.warning(f"Onboarding plan generation failed: {e}")
        ai_plan = generate_default_plan(name, role, experience_level)

    # Generate phase-specific tasks
    week1_tasks = generate_week1_tasks(role, department)
    month1_goals = generate_month1_goals(role, experience_level, skills)
    month2_3_goals = generate_month2_3_goals(role, skills)

    # Suggest mentor/buddy
    mentor_suggestion = suggest_mentor(experience_level, team_members)

    # Success metrics
    metrics = define_success_metrics(role, experience_level)

    return {
        "employee_id": employee_id,
        "employee_name": name,
        "onboarding": {
            "role": role,
            "department": department,
            "experience_level": experience_level,
            "start_date": datetime.utcnow().isoformat(),
            "expected_ramp_up_days": 90,
        },
        "week_1": {
            "focus": "Integration & Familiarization",
            "tasks": week1_tasks,
            "milestones": ["Complete HR onboarding", "Meet team members", "Understand role scope"],
        },
        "month_1": {
            "focus": "Capability Building",
            "goals": month1_goals,
            "check_in": "Weekly with manager",
        },
        "month_2_3": {
            "focus": "Productivity & Contribution",
            "goals": month2_3_goals,
            "check_in": "Bi-weekly with manager",
        },
        "mentorship": {
            "mentor_suggestion": mentor_suggestion,
            "buddy_assignment": team_members[0] if team_members else "TBD",
            "frequency": "2-3 times per week for first month",
        },
        "success_metrics": metrics,
        "ai_personalized_plan": ai_plan,
        "timeline": {
            "30_days": "Productivity checkpoint",
            "60_days": "Skill assessment",
            "90_days": "Full capability review",
        },
    }


async def generate_onboarding_checklist(
    role: str,
    department: str,
    team_size: int,
) -> dict:
    """
    Generate detailed onboarding checklist.

    Args:
        role: Job role
        department: Department
        team_size: Team size

    Returns:
        Comprehensive onboarding checklist
    """
    llm = await get_llm()
    
    system = """You are an expert in employee onboarding. Create a detailed, practical checklist 
for successful new hire integration."""
    
    prompt = f"""
Create onboarding checklist for:
- Role: {role}
- Department: {department}
- Team Size: {team_size}

Include items for:
1. Pre-arrival (2-3 items)
2. Day 1 (4-5 items)
3. Week 1 (5-6 items)
4. Month 1 (4-5 items)
5. Ongoing (systems, culture, etc.)

Format as actionable checklist items.
"""

    try:
        checklist = await llm.generate(prompt, system, max_tokens=400)
    except Exception as e:
        logger.warning(f"Checklist generation failed: {e}")
        checklist = generate_default_checklist(role)

    return {
        "role": role,
        "department": department,
        "created_at": datetime.utcnow().isoformat(),
        "checklist": checklist,
    }


async def track_onboarding_progress(
    employee_id: str,
    start_date: str,
    completed_tasks: list[str],
    manager_notes: str | None = None,
) -> dict:
    """
    Track and analyze onboarding progress.

    Args:
        employee_id: Employee ID
        start_date: Onboarding start date
        completed_tasks: List of completed task IDs
        manager_notes: Optional manager notes

    Returns:
        Progress report with AI insights
    """
    start = datetime.fromisoformat(start_date)
    days_in = (datetime.utcnow() - start).days
    
    progress_percent = min(100, (days_in / 90) * 100)
    completion_rate = (len(completed_tasks) / 30) * 100 if completed_tasks else 0

    llm = await get_llm()
    
    system = """You are an HR analytics expert. Assess new hire onboarding progress and provide recommendations."""
    
    prompt = f"""
Onboarding Progress Report:
- Days into onboarding: {days_in}
- Expected duration: 90 days
- Progress: {progress_percent:.1f}%
- Tasks completed: {len(completed_tasks)}/30
- Completion rate: {completion_rate:.1f}%
- Manager notes: {manager_notes or 'None'}

Provide assessment and recommendations.
"""

    try:
        assessment = await llm.generate(prompt, system, max_tokens=250)
    except Exception as e:
        logger.warning(f"Progress assessment failed: {e}")
        assessment = f"Progress on track. {len(completed_tasks)} tasks completed."

    status = "On Track" if completion_rate >= 70 else "Slightly Behind" if completion_rate >= 50 else "Needs Support"

    return {
        "employee_id": employee_id,
        "days_in_onboarding": days_in,
        "progress": {
            "percent_complete": round(progress_percent, 1),
            "task_completion_rate": round(completion_rate, 1),
            "tasks_completed": len(completed_tasks),
            "status": status,
        },
        "assessment": assessment,
        "recommendation": "Maintain current pace" if status == "On Track" else "Schedule check-in with employee",
    }


# Helper functions

def generate_week1_tasks(role: str, department: str) -> list[dict]:
    """Generate Week 1 onboarding tasks."""
    return [
        {"task": "Complete HR paperwork and benefits enrollment", "owner": "HR", "priority": "High"},
        {"task": "IT setup - laptop, email, access", "owner": "IT", "priority": "High"},
        {"task": "Office tour and workspace setup", "owner": "Manager", "priority": "Medium"},
        {"task": "Team introduction meeting", "owner": "Manager", "priority": "High"},
        {"task": "Department orientation", "owner": "Department Head", "priority": "Medium"},
        {"task": f"Role overview and expectations for {role}", "owner": "Manager", "priority": "High"},
    ]


def generate_month1_goals(role: str, experience_level: str, skills: list[str]) -> list[str]:
    """Generate Month 1 goals based on role and experience."""
    goals = [
        f"Understand {role} role responsibilities and expectations",
        "Build relationships with team members",
        "Complete required training and certifications",
    ]
    
    if experience_level in ["Entry-Level", "Mid-Level"]:
        goals.append("Shadow senior team member on key tasks")
    
    if any(s.lower() in ["python", "java", "coding"] for s in skills):
        goals.append("Set up development environment and run first code")
    
    return goals


def generate_month2_3_goals(role: str, skills: list[str]) -> list[str]:
    """Generate Month 2-3 goals."""
    return [
        "Contribute to first project or initiative",
        "Demonstrate understanding of key processes",
        "Provide feedback on onboarding experience",
        "Establish regular 1:1 rhythm with manager",
    ]


def suggest_mentor(experience_level: str, team_members: list[str] | None) -> str:
    """Suggest a mentor based on experience level."""
    if not team_members:
        return "To be assigned by manager"
    
    if experience_level in ["Entry-Level", "Mid-Level"]:
        return f"Recommend senior team member mentor (suggested: {team_members[0]})"
    else:
        return "Peer mentoring/collaboration recommended"


def define_success_metrics(role: str, experience_level: str) -> list[str]:
    """Define success metrics for onboarding."""
    metrics = [
        "Completes all mandatory training",
        "Establishes productive working relationships",
        "Demonstrates role competency",
    ]
    
    if experience_level in ["Entry-Level"]:
        metrics.append("Asks clarifying questions and seeks feedback")
    else:
        metrics.append("Contributes ideas and improvements")
    
    return metrics


def generate_default_plan(name: str, role: str, experience_level: str) -> str:
    """Generate default onboarding plan when AI is unavailable."""
    return f"""
90-Day Onboarding Plan for {name}

Week 1: Foundation & Integration
- Complete HR and IT setup
- Team introductions
- Role overview and expectations

Weeks 2-4: Learning & Capability Building  
- Deep dive into role responsibilities
- Learn key systems and processes
- Build working relationships

Weeks 5-8: Productivity & Contribution
- Take ownership of first tasks
- Contribute to team projects
- Demonstrate role competency

Weeks 9-12: Mastery & Independence
- Work independently on assigned tasks
- Complete role-specific training
- 90-day review and feedback

Success Metrics:
✓ All training completed
✓ Role competency demonstrated
✓ Positive team feedback
✓ Manager confidence in independence
"""


def generate_default_checklist(role: str) -> str:
    """Generate default checklist when AI is unavailable."""
    return f"""
Onboarding Checklist for {role}

PRE-ARRIVAL:
☐ Workspace prepared
☐ Equipment ordered
☐ Access provisioned

DAY 1:
☐ Welcome meeting
☐ IT setup
☐ HR orientation
☐ Office tour
☐ Team introductions

WEEK 1:
☐ Role orientation
☐ Systems training
☐ Process overview
☐ Manager 1:1
☐ Team lunch/meeting

MONTH 1:
☐ Complete required training
☐ First project assignment
☐ Competency assessment
☐ 30-day check-in

ONGOING:
☐ Regular 1:1 meetings
☐ Feedback collection
☐ Progress monitoring
☐ 60 & 90-day reviews
"""
