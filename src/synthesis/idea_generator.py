from typing import List, Dict
import os
from tenacity import wait_exponential, stop_after_attempt  # retained import to avoid unused removal churn
from openai import OpenAI
import httpx

from .botec import BENCHMARKS, DISCOUNT_SCHEDULE


SYSTEM_PROMPT = (
    "You are an idea generator optimizing for the wellbeing of all sentient beings. "
    "Follow this disciplined approach: "
    "(1) Problem sizing: quantify the largest problems (orders of magnitude: animals affected, DALYs, WELBY, log-income, tCO2e). "
    "(2) Leading and possible solutions: scan authoritative sources (e.g., Wild Animal Initiative, Open Philanthropy, Rethink Priorities, Disease Control Priorities, peer-reviewed meta-analyses). "
    "(3) Cruxes: identify binding constraints on development or adoption (technical feasibility, regulatory, buyer fragmentation, CapEx/O&M, incentives, supply chain). "
    "(4) Mechanism choice: select mechanisms based on the crux (corporate commitments/campaigns, regulation/enforcement, direct/pooled procurement and delivery, standards/verification, concessionary finance, policy advocacy, or market-shaping such as AMCs/prizes/milestones/purchase guarantees). Do not default to market-shaping. "
    "(5) Ideal-solution backcasting: outline the ideal endpoint and what new science/tech or coordination would unlock it (e.g., new models, datasets, screening methods, repurposing). "
    "(6) Verification: define binary, independently auditable success metrics. "
    "(7) BOTEC: provide explicit expected-value calculations in native units vs an explicit benchmark. No cross-metric conversions. Discount 0% ≤ 50y, 2% thereafter. "
    "Be highly specific (assets, geographies, timelines, thresholds), like the brick kiln zig-zag retrofit example."
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


def _call_llm(messages: List[Dict], model: str = "gpt-4o-mini", max_tokens: int = 1200) -> str:
    # Ensure message contents are strings
    safe_messages: List[Dict[str, str]] = []
    for m in messages:
        safe_messages.append({"role": str(m.get("role", "user")), "content": str(m.get("content", ""))})

    # Create an explicit httpx client without proxies to avoid environment proxy misconfig errors
    http_client = httpx.Client(timeout=60.0)
    client = OpenAI(http_client=http_client)
    models_to_try = [
        os.getenv("OPENAI_MODEL", model),
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4o-mini-2024-07-18",
        "gpt-3.5-turbo-0125",
    ]
    for m in models_to_try:
        try:
            if not m:
                continue
            resp = client.chat.completions.create(
                model=m,
                messages=safe_messages,
                temperature=0.6,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content if resp and resp.choices else ""
            return content or "[]"
        except Exception:
            # Try next model
            continue
    # Final fallback
    return "[]"


def synthesize_ideas(topics: str, documents: List[Dict], num_ideas: int = 25, show_reasoning: bool = False) -> List[Dict]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set")

    context = _build_context(documents)
    reasoning_clause = (
        "Include a 'reasoning' object with problem_sizing, cruxes, mechanism_rationale, and verification_plan."
        if show_reasoning
        else ""
    )

    user_prompt = f"""
Generate {num_ideas} ideas. Constraints:
- 3/4 human wellbeing (incl. pandemics) and 1/4 animals.
- No cross-metric conversion. Compare to relevant benchmarks only.
- Discount: 0% up to 50y, 2% thereafter.
- Choose mechanisms per crux; consider corporate commitments/campaigns, regulation/enforcement, direct/pooled procurement and delivery, standards/verification, concessionary finance, policy advocacy, and market-shaping (AMCs/prizes/milestones/purchase guarantees) only when appropriate. Do not default to market-shaping.
- Be highly specific about asset counts, geographies, timelines, and verification thresholds.

Topics: {topics}

Evidence snippets (non-exhaustive):
{context}

Return JSON list with objects containing:
- title
- description (single paragraph; exact template: Funding what, through what mechanism, with the expectation of having what impact at what cost, resulting in what cost-effectiveness vs benchmark.)
- instrument (e.g., AMC, prize, milestone, purchase guarantee, direct grant)
- metric_tag (one of DALY, WALY, WELBY, log income, CO2)
- total_cost (USD range ok)
- ce_vs_benchmark (short comparison text)
- candidates (1-3 names or orgs)
- sources (list of {{title, url}})
Ensure novelty by addressing adoption barriers/cruxes with a concrete mechanism.

Also include a 'botec' object with the following fields:
- target_question (units)
- decomposition (list of components)
- anchors (list of {{ref, url}})
- assumptions (object with key: value ranges)
- formulas (list of strings showing explicit relationships)
- estimates {{impact_units, total_cost_usd, ce_value, ce_units}}
- benchmark {{name, range}}
- comparison (e.g., "better by 2–5x", "worse by ~30%")
- sensitivity (top 2–3 drivers and how a 2x change shifts CE)

{reasoning_clause}
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
                "botec": idea.get("botec", {}),
                "reasoning": idea.get("reasoning", {}) if show_reasoning else {},
            }
        )
    return normed


