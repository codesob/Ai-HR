"""Free LLM service using Groq API (free tier with fast inference)."""

import httpx
import logging
from typing import Optional

from shared.core.config import get_settings

logger = logging.getLogger(__name__)


class AILLMService:
    """AI LLM service using free APIs (Groq, Hugging Face, etc)."""

    def __init__(self):
        self.settings = get_settings()
        self.groq_api_key = self.settings.groq_api_key
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client

    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate text using LLM.

        Args:
            prompt: User prompt
            system: System prompt/context
            max_tokens: Maximum tokens to generate
            temperature: Creativity (0.0-1.0)

        Returns:
            Generated text response
        """
        if not self.groq_api_key:
            logger.warning("Groq API key not configured. Returning template response.")
            return self._fallback_response(prompt)

        try:
            client = await self._get_client()

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = await client.post(
                self.groq_endpoint,
                json={
                    "model": self.settings.groq_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.error("Error generating with LLM: %s", type(e).__name__)
            return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        """Never fabricate an assessment when the model is unavailable; say so explicitly."""
        return (
            "AI analysis is currently unavailable. This result was produced by rule-based scoring only "
            "and should be reviewed by a person."
        )


# Global LLM instance
_llm_instance: Optional[AILLMService] = None


async def get_llm() -> AILLMService:
    """Get or create LLM service instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = AILLMService()
    return _llm_instance


async def generate_interview_score_explanation(
    candidate_name: str,
    performance_notes: str,
    technical_score: float,
    communication_score: float,
) -> dict:
    """Generate AI-powered interview score explanation."""
    llm = await get_llm()

    system = """You are an expert HR interviewer. Provide a concise, professional 
interview evaluation explaining the scores and recommendations."""

    prompt = f"""
Candidate: {candidate_name}
Performance Notes: {performance_notes}
Technical Score: {technical_score}/10
Communication Score: {communication_score}/10

Provide:
1. Brief evaluation summary (2 sentences)
2. Key strengths (2-3 points)
3. Areas for development (1-2 points)
4. Recommendation (Hire/Next Round/Further Review)
"""

    response = await llm.generate(prompt, system, max_tokens=300)
    return {"explanation": response}


async def generate_candidate_insights(
    name: str,
    skills: list[str],
    experience_years: float,
    match_score: float,
    job_title: str,
) -> dict:
    """Generate AI-powered candidate insights and recommendations."""
    llm = await get_llm()

    system = """You are an expert recruiter. Provide insightful analysis about candidates 
and hiring recommendations based on their profile."""

    prompt = f"""
Candidate Profile:
- Name: {name}
- Target Role: {job_title}
- Years of Experience: {experience_years}
- Key Skills: {', '.join(skills)}
- Match Score: {match_score:.1%}

Provide:
1. Fit assessment (1 sentence)
2. Why this candidate is strong (2 points)
3. Growth potential (1 point)
4. Interview focus areas (2-3 areas)
5. Risk factors (if any)
"""

    response = await llm.generate(prompt, system, max_tokens=400)
    return {"insights": response}


async def generate_hiring_recommendation(
    top_candidates: list[dict],
    job_description: str,
) -> dict:
    """Generate AI recommendation on top candidates."""
    llm = await get_llm()

    system = """You are a senior HR strategy advisor. Recommend the best candidate 
based on comprehensive analysis and company needs."""

    candidates_text = "\n".join([
        f"- {c['name']}: Match {c.get('match_score', 0):.1%}, Skills: {', '.join(c.get('skills', [])[:3])}"
        for c in top_candidates[:5]
    ])

    prompt = f"""
Job: {job_description[:200]}

Top Candidates:
{candidates_text}

Provide:
1. Top recommendation with reasons (2-3 sentences)
2. Alternative candidates (if any)
3. Risk mitigation for top pick
4. Next steps
5. Team integration advice
"""

    response = await llm.generate(prompt, system, max_tokens=500)
    return {"recommendation": response}


async def generate_onboarding_plan(
    candidate_name: str,
    role: str,
    skills: list[str],
    team_size: int,
) -> dict:
    """Generate personalized onboarding plan."""
    llm = await get_llm()

    system = """You are an expert in employee onboarding. Create personalized, 
practical onboarding plans that ensure successful integration."""

    prompt = f"""
New Hire Onboarding Plan:
- Employee: {candidate_name}
- Role: {role}
- Key Skills: {', '.join(skills)}
- Team Size: {team_size}

Create a 90-day onboarding plan with:
1. Week 1 priorities (3 items)
2. Month 1 goals (3-4 items)
3. Month 2-3 integration (2-3 items)
4. Mentorship pairing recommendation
5. Success metrics
"""

    response = await llm.generate(prompt, system, max_tokens=600)
    return {"onboarding_plan": response}


async def generate_hiring_insights(
    recent_hires_count: int,
    open_positions: int,
    avg_time_to_hire: float,
) -> dict:
    """Generate strategic hiring insights."""
    llm = await get_llm()

    system = """You are a data-driven HR analytics expert. Provide actionable 
insights to improve hiring effectiveness."""

    prompt = f"""
Current Hiring Metrics:
- Recent Hires (last 30 days): {recent_hires_count}
- Open Positions: {open_positions}
- Average Time to Hire: {avg_time_to_hire:.0f} days

Provide insights on:
1. Hiring velocity assessment
2. Bottleneck analysis (if any)
3. Optimization recommendations (2-3 quick wins)
4. Process improvements
5. Talent pipeline recommendations
"""

    response = await llm.generate(prompt, system, max_tokens=500)
    return {"insights": response}
