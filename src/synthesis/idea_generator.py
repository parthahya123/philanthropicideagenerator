from typing import List, Dict
import os
from tenacity import retry, wait_exponential, stop_after_attempt
from openai import OpenAI

from .botec import BENCHMARKS, DISCOUNT_SCHEDULE


SYSTEM_PROMPT = (
    "You are an idea generator optimizing for the wellbeing of all sentient beings. "
    "Follow this reasoning pipeline per topic: "
    "(1) Problem sizing: quantify the biggest problems (orders of magnitude, e.g., animals affected, DALYs, tCO2e). "
    "(2) Leading solutions: scan authoritative sources (e.g., WAI, Open Phil, RP, DCP, peer-reviewed). "
    "(3) Cruxes: identify the binding constraints on development/adoption (technical, regulatory, buyer fragmentation, CapEx, ops). "
    "(4) Mechanism design: propose specific levers (AMCs, prizes, milestones, purchase guarantees, pooled procurement, verification). "
    "(5) Ideal-solution backcasting: consider what would make the problem go away; scan literature for enabling tech and what's newly possible. "
    "(6) Verification: define binary, independent measures of success. "
    "(7) Light BOTEC: native metric CE vs benchmark; no cross-metric conversions; 0% discount ≤50y, 2% thereafter. "
    "Return concise ideas in the exact format requested by the user."
)


def _build_context(documents: List[Dict], max_chars: int = 12000) -> str:
    parts: List[str] = []
    used = 0
    for d in documents[:50]:
        title = d.get("title", "")
        url = d.get("url", "")
        summary = d.get("summary", "")[:1000]
        s = f"- {title}\n  {summary}\n  Source: {url}\n"
        if used + len(s) > max_chars:
            break
        parts.append(s)
        used += len(s)
    return "\n".join(parts)


@retry(wait=wait_exponential(min=1, max=5), stop=stop_after_attempt(2))
def _call_llm(messages: List[Dict], model: str = "gpt-4o-mini", max_tokens: int = 2000) -> str:
    # Ensure message contents are strings
    safe_messages = []
    for m in messages:
        safe_messages.append({"role": m.get("role", "user"), "content": str(m.get("content", ""))})

    client = OpenAI()
    last_exc = None
    for m in [model, "gpt-4o", "gpt-4o-mini-2024-07-18", "gpt-3.5-turbo-0125"]:
        try:
            resp = client.chat.completions.create(
                model=m,
                messages=safe_messages,
                temperature=0.6,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:  # capture and try fallback models
            last_exc = exc
            continue
    # Fallback to empty JSON list to avoid crashing the app; upstream will handle gracefully
    return "[]"


def synthesize_ideas(topics: str, documents: List[Dict], num_ideas: int = 25) -> List[Dict]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set")

    context = _build_context(documents)
    user_prompt = f"""
Generate {num_ideas} ideas. Constraints:
- 3/4 human wellbeing (incl. pandemics) and 1/4 animals.
- No cross-metric conversion. Compare to relevant benchmarks only.
- Discount: 0% up to 50y, 2% thereafter.
- Prefer market-shaping mechanisms where appropriate (AMCs, prizes, milestones, purchase guarantees).

Topics: {topics}

Evidence snippets (non-exhaustive):
{context}

Return JSON list with objects containing:
- title
- description (single paragraph in the exact template)
- instrument (e.g., AMC, prize, milestone, purchase guarantee, direct grant)
- metric_tag (one of DALY, WALY, WELBY, log income, CO2)
- total_cost (USD range ok)
- ce_vs_benchmark (short comparison text)
- candidates (1-3 names or orgs)
- sources (list of {{title, url}})
Ensure novelty by addressing adoption barriers/cruxes with a concrete mechanism.
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": user_prompt,
        },
    ]
    raw = _call_llm(messages)

    # Try to parse JSON; if fails, wrap best-effort
    ideas: List[Dict] = []
    import json

    try:
        ideas = json.loads(raw)
    except Exception:
        # Fallback: attempt to extract JSON substring
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                ideas = json.loads(raw[start : end + 1])
            except Exception:
                ideas = []
    if not isinstance(ideas, list):
        ideas = []

    # Normalize and cap
    normed: List[Dict] = []
    for idea in ideas[:num_ideas]:
        normed.append(
            {
                "title": idea.get("title", "Idea"),
                "description": idea.get("description", ""),
                "instrument": idea.get("instrument", ""),
                "metric_tag": idea.get("metric_tag", ""),
                "total_cost": idea.get("total_cost", ""),
                "ce_vs_benchmark": idea.get("ce_vs_benchmark", ""),
                "candidates": idea.get("candidates", []) or [],
                "sources": idea.get("sources", []) or [],
            }
        )
    return normed


