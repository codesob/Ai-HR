"""Tool-calling client for any OpenAI-compatible chat API (Groq by default)."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

import httpx

from shared.core.config import get_settings

logger = logging.getLogger(__name__)


class AgentLLMError(RuntimeError):
    """The model isn't configured or the call failed."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    # The assistant message exactly as it goes back into the conversation.
    message: dict = field(default_factory=dict)


MAX_RATE_LIMIT_RETRIES = 3


def _retry_after(res: httpx.Response) -> float:
    """Seconds to wait after a 429, from the Retry-After header or the provider's message; capped."""
    try:
        wait = float(res.headers.get("retry-after", ""))
    except ValueError:
        found = re.search(r"try again in ([\d.]+)s", res.text)
        wait = float(found.group(1)) if found else 5.0
    return min(max(wait, 1.0), 20.0)


def configured() -> bool:
    s = get_settings()
    return bool(s.agent_llm_api_key or s.groq_api_key)


async def complete(messages: list[dict], tools: list[dict]) -> LLMReply:
    s = get_settings()
    api_key = s.agent_llm_api_key or s.groq_api_key
    if not api_key:
        raise AgentLLMError("The HR agent needs a language model. Set GROQ_API_KEY (or AGENT_LLM_API_KEY).")

    body: dict = {
        "model": s.agent_llm_model or s.groq_model,
        "messages": messages,
        "temperature": 0.2,
        # Counts against per-minute token limits even when unused, so keep it modest.
        "max_tokens": 800,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
                res = await client.post(
                    f"{s.agent_llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=body,
                )
                if res.status_code != 429 or attempt == MAX_RATE_LIMIT_RETRIES:
                    break
                await asyncio.sleep(_retry_after(res))
        res.raise_for_status()
        msg = res.json()["choices"][0]["message"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        detail = exc.response.text[:300] if isinstance(exc, httpx.HTTPStatusError) else str(exc)
        logger.warning("Agent model call failed: %s", detail)
        raise AgentLLMError("The language model didn't respond. Try again in a moment.") from exc

    calls = []
    for c in msg.get("tool_calls") or []:
        try:
            args = json.loads(c["function"].get("arguments") or "{}")
        except ValueError:
            args = {"_invalid_json": c["function"].get("arguments")}
        calls.append(ToolCall(id=c["id"], name=c["function"]["name"], arguments=args if isinstance(args, dict) else {}))

    message = {"role": "assistant", "content": msg.get("content") or ""}
    if msg.get("tool_calls"):
        message["tool_calls"] = msg["tool_calls"]
    return LLMReply(content=msg.get("content") or "", tool_calls=calls, message=message)
