from typing import List, Dict
import os
from tenacity import wait_exponential, stop_after_attempt  # retained import to avoid unused removal churn
from openai import OpenAI
import httpx
import re

from .botec import BENCHMARKS, DISCOUNT_SCHEDULE

# Priority sources for evidence (weighted to appear earlier in context)
PRIORITY_SOURCES = {
    "Open Philanthropy",
    "Animal Charity Evaluators",
    "Wild Animal Initiative",
    "FAOSTAT",
    "Fishcount",
}


SYSTEM_PROMPT = (
    "You are an idea generator trying to find high expected value philanthropic ideas. "
    "Follow this disciplined approach: "
    "(1) Problem sizing (goal-conditional): use domain-appropriate sources to quantify the largest contributors in native units. "
    "For global health, use GBD/IHME/WHO GHO to size DALYs by cause and region; "
    "for climate, use sources like Our World in Data (OWID), BloombergNEF, and IPCC to size tCO2e by sector/technology and marginal abatement costs; "
    "for animal welfare, use reputable sources (e.g., ACE, WAI, FAOSTAT, Fishcount) to rank suffering by taxa/production system; "
    "for income growth/poverty, use World Bank and OWID to size populations, income gaps, and elasticities; "
    "for mental health/WELBYs, use sources like GBD and peer-reviewed meta-analyses to anchor estimates. Express orders of magnitude and the top contributors only. "
    "(2) Leading and possible solutions: scan authoritative sources (peer-reviewed literature, high-quality policy analyses, reputable research orgs). "
    "(3) Cruxes: identify binding constraints on development or adoption (technical feasibility, regulatory, buyer fragmentation, CapEx/O&M, incentives, supply chain). "
    "(4) Mechanism choice: consider the full space of mechanisms and select based on the identified cruxes; avoid preselecting interventions or instruments. Where relevant, assess whether market-shaping is appropriate given market failure and buyer commitment, but do not assume it by default. "
    "(5) Ideal-solution backcasting: outline the ideal endpoint and what new science/tech or coordination would unlock it (e.g., new models, datasets, screening methods, repurposing). "
    "(6) BOTEC: provide explicit expected-value calculations in native units against the benchmark appropriate to the user's goal. "
    "Use the correct benchmark and include its definition and typical performance range with citations: DALY → GiveWell Top Charities; WALY → The Humane League (use ACE only if THL not applicable); WELBY → StrongMinds-like; log income → GiveDirectly; CO2 → frontier climate $/tCO2e. No cross-metric conversions. Discount 0% ≤ 50y, 2% thereafter. "
    "(7) Doer-first: identify 1–3 high-agency individuals when possible (via open-web signals such as Crunchbase, Wikipedia, LinkedIn, news). Be picky; filter for integrity, track record, domain qualification. Score each 1–7 on intelligence/creativity, entrepreneurial drive, track record, integrity, domain expertise; include an average and 1–2 sentence rationale with a link. If no great fit, provide a concise 2–3 sentence archetype description. "
    "(8) Adversarial review (Roodman-style): simulate a rigorous reviewer who challenges identification, external validity, publication bias, and unmodeled costs; propose alternative anchors and recompute pessimistic/optimistic CE; then produce an adjudicated CE and conclusion. "
    "Be highly specific (assets, geographies, timelines, thresholds) in reasoning, not by prespecifying interventions."
)


def _build_context(documents: List[Dict], max_chars: int = 12000) -> str:
    # Stable sort: priority sources first, then others
    def _priority(doc: Dict) -> int:
        src = (doc.get("source") or "").strip()
        return 0 if src in PRIORITY_SOURCES else 1

    ordered = sorted(documents, key=_priority)

    parts: List[str] = []
    used = 0
    for d in ordered[:50]:
        title = d.get("title", "")
        url = d.get("url", "")
        summary = d.get("summary", "")[:1000]
        s = f"- {title}\n  {summary}\n  Source: {url}\n"
        if used + len(s) > max_chars:
            break
        parts.append(s)
        used += len(s)
    return "\n".join(parts)


def _call_llm(messages: List[Dict], model: str = "gpt-4o-mini", max_tokens: int = 2000, temperature: float = 0.6) -> str:
    # Ensure message contents are strings
    safe_messages: List[Dict[str, str]] = []
    for m in messages:
        safe_messages.append({"role": str(m.get("role", "user")), "content": str(m.get("content", ""))})

    # Create an explicit httpx client without proxies to avoid environment proxy misconfig errors
    http_client = httpx.Client(timeout=60.0)
    client = OpenAI(http_client=http_client)
    models_to_try = [
        os.getenv("OPENAI_MODEL", "gpt-5"),
        "gpt-5",
        "gpt-5o",
        "o3",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-4o-mini-2024-07-18",
        "gpt-3.5-turbo-0125",
    ]
    for m in models_to_try:
        try:
            if not m:
                continue
            # Prefer JSON output
            try:
                resp = client.chat.completions.create(
                    model=m,
                    messages=safe_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
            except Exception:
                resp = client.chat.completions.create(
                    model=m,
                    messages=safe_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            content = resp.choices[0].message.content if resp and resp.choices else ""
            return content or "[]"
        except Exception:
            # Try next model
            continue
    # Final fallback
    return "[]"


def synthesize_ideas(
    topics: str,
    documents: List[Dict],
    num_ideas: int = 25,
    show_reasoning: bool = False,
    deep_research: bool = False,
):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set")

    context = _build_context(documents)
    reasoning_clause = (
        "Include a 'reasoning' object with problem_sizing, cruxes, mechanism_rationale, and verification_plan."
        if show_reasoning
        else ""
    )

    # Domain-specific guardrails (animal welfare, cause-neutral and EV-first)
    animal_clause = ""
    if any(k in (topics or "").lower() for k in ["animal", "welfare", "broiler", "fish", "shrimp", "layer", "poultry", "swine", "aquaculture"]):
        animal_clause = (
            "\nANIMAL WELFARE MODE:\n"
            "- Cause-neutral, EV-first: start by ranking the largest sources of animal suffering by scale and intensity using credible counts (e.g., FAOSTAT, Fishcount, ACE, WAI).\n"
            "- Consider a wide range of plausible mechanisms and delivery approaches appropriate to the production systems; do not preselect a single intervention ex ante. Justify the chosen mechanism from identified cruxes.\n"
            "- Compute expected value (WALY) for candidates using explicit BOTECs; select the highest-EV options.\n"
            "- Use WALY as the metric. Quantify animals improved per year and cost per animal-year improved.\n"
            "- Describe an independent, auditable verification approach suitable to the mechanism (optional but recommended).\n"
            "- Benchmarks: compare WALY/$ to The Humane League baseline; use ACE only if THL is not applicable. State the numeric delta.\n"
            "- Prioritize evidence from reputable sources (e.g., Open Philanthropy on animal welfare, Animal Charity Evaluators, Wild Animal Initiative, FAOSTAT, Fishcount).\n"
        )

    user_prompt = f"""
Generate {num_ideas} ideas. Constraints:
- 3/4 human wellbeing (incl. pandemics) and 1/4 animals.
- No cross-metric conversion. Compare to relevant benchmarks only.
- Discount: 0% up to 50y, 2% thereafter.
- Select mechanisms based on identified cruxes; avoid precommitting to specific intervention types. Justify the choice succinctly.
- Be highly specific about asset counts, geographies, timelines, and verification thresholds.
- Benchmarks mapping (must cite explicitly in BOTEC): DALY → GiveWell Top Charities; WALY → The Humane League (corporate campaigns) by default (use ACE only if THL not applicable); WELBY → StrongMinds-like references; log income → GiveDirectly; CO2 → frontier climate $/tCO2e.

Topics: {topics}

Evidence snippets (non-exhaustive):
{context}

{animal_clause}

Return a JSON object with the EXACT key name "ideas" whose value is a list of idea objects. Do not use any other top-level key. Each idea object contains:
- title
- description (single paragraph; exact template: Funding what, through what mechanism, with the expectation of having what impact at what cost, resulting in what cost-effectiveness vs benchmark.)
- instrument (free-text; keep concise)
- metric_tag (one of DALY, WALY, WELBY, log income, CO2)
- total_cost (USD range ok)
- ce_vs_benchmark (short comparison text)
- candidates (1-3 names or orgs)
- sources (list of {{title, url}})
- doers (list of {{"name","link","affiliation","scores":{{"intelligence":1-7,"drive":1-7,"track_record":1-7,"integrity":1-7,"domain_expertise":1-7}},"average_score":number,"rationale":string}}) OR, if none strong, a 'doer_archetype' string (2–3 sentences)
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

Add a 'debate' object representing the adversarial review:
- criticisms (list)
- rebuttals (list)
- revised_assumptions (object with key revisions)
- recalc {{impact_units, total_cost_usd, ce_value, ce_units}}
- final_conclusion (short paragraph)

{reasoning_clause}
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": user_prompt,
        },
    ]
    # Model/run settings
    default_model = os.getenv("OPENAI_MODEL") or ("o3" if deep_research else "gpt-4o")
    run_temperature = 0.2 if deep_research else 0.6
    max_tokens = 3000 if deep_research else 2000

    # First-pass generation
    raw = _call_llm(messages, model=default_model, max_tokens=max_tokens, temperature=run_temperature)

    # Robust JSON parsing
    clean = raw.strip()
    if clean.startswith("```"):
        match = re.search(r"```(?:json)?\n([\s\S]*?)```", clean, re.IGNORECASE)
        if match:
            clean = match.group(1).strip()

    import json
    obj = None
    try:
        obj = json.loads(clean)
    except Exception:
        # Try array extraction
        a_start = clean.find("[")
        a_end = clean.rfind("]")
        if a_start != -1 and a_end != -1 and a_end > a_start:
            try:
                obj = json.loads(clean[a_start : a_end + 1])
            except Exception:
                obj = None
        # Try object extraction
        if obj is None:
            o_start = clean.find("{")
            o_end = clean.rfind("}")
            if o_start != -1 and o_end != -1 and o_end > o_start:
                try:
                    obj = json.loads(clean[o_start : o_end + 1])
                except Exception:
                    obj = None

    ideas_list: List[Dict] = []
    if isinstance(obj, dict):
        ideas_list = obj.get("ideas", []) or []
        # Accept common alternate key names from models and map to ideas
        if not ideas_list:
            for alt in ["philanthropic_ideas", "initiatives", "recommendations", "results", "items"]:
                if isinstance(obj.get(alt), list):
                    ideas_list = obj.get(alt, []) or []
                    break
        # Last-resort: if any single top-level key contains a list of dicts, use it
        if not ideas_list:
            for k, v in obj.items():
                if isinstance(v, list) and (len(v) == 0 or isinstance(v[0], dict)):
                    ideas_list = v
                    break
    elif isinstance(obj, list):
        ideas_list = obj

    # Rescue fallback: if empty, ask for a minimal array
    if not ideas_list:
        minimal_system = "You generate concise philanthropic ideas. Return strictly JSON only."
        minimal_user = (
            f"Return a JSON array with {num_ideas} objects. Each object has keys: "
            f"title, description, instrument, metric_tag, total_cost, ce_vs_benchmark, candidates (array), "
            f"sources (array of objects with title and url). Use one-sentence descriptions with concrete numbers. Topics: {topics}."
        )
        rescue_messages = [
            {"role": "system", "content": minimal_system},
            {"role": "user", "content": minimal_user},
        ]
        raw2 = _call_llm(rescue_messages)
        clean2 = raw2.strip()
        if clean2.startswith("```"):
            m2 = re.search(r"```(?:json)?\n([\s\S]*?)```", clean2, re.IGNORECASE)
            if m2:
                clean2 = m2.group(1).strip()
        try:
            parsed2 = json.loads(clean2)
            if isinstance(parsed2, list):
                ideas_list = parsed2
            elif isinstance(parsed2, dict) and "ideas" in parsed2:
                ideas_list = parsed2.get("ideas", []) or []
        except Exception:
            ideas_list = []
        raw = raw if ideas_list else raw2  # keep the one that yielded content

    # Refine pass: enforce benchmarks, BOTEC rigor, verification, and specificity
    refined = _refine_ideas_with_rubric(topics, ideas_list[:num_ideas], deep_research=deep_research)
    # If refinement yields nothing, fall back to draft ideas rather than returning 0
    if not refined and ideas_list:
        refined = ideas_list[:num_ideas]
    # If refinement yields nothing, keep the draft ideas rather than returning empty
    if not refined and ideas_list:
        refined = ideas_list[:num_ideas]

    # Normalize and cap
    normed: List[Dict] = []
    topics_l = (topics or "").lower()
    is_animal = any(k in topics_l for k in ["animal", "welfare", "broiler", "fish", "shrimp", "layer", "poultry", "swine", "aquaculture"])
    is_global_health = any(k in topics_l for k in [
        "health", "malaria", "tb", "hiv", "pandemic", "epidemic"
    ])
    allowed_metrics = {"DALY", "WALY", "WELBY", "log income", "CO2"}
    for idea in refined[:num_ideas]:
        mt = str(idea.get("metric_tag", "")).strip()
        if mt not in allowed_metrics:
            mt = "DALY" if is_global_health else ("WALY" if is_animal else mt)
        normed.append(
            {
                "title": idea.get("title", "Idea"),
                "description": idea.get("description", ""),
                "instrument": idea.get("instrument", ""),
                "metric_tag": mt,
                "total_cost": idea.get("total_cost", ""),
                "ce_vs_benchmark": idea.get("ce_vs_benchmark", ""),
                "candidates": idea.get("candidates", []) or [],
                "sources": idea.get("sources", []) or [],
                "botec": idea.get("botec", {}),
                "reasoning": idea.get("reasoning", {}) if show_reasoning else {},
                "doers": idea.get("doers", []) or [],
                "doer_archetype": idea.get("doer_archetype", ""),
                "debate": idea.get("debate", {}),
            }
        )
    return {"ideas": normed, "raw": raw, "docs_count": len(documents)}


def _refine_ideas_with_rubric(topics: str, draft_ideas: List[Dict], deep_research: bool = False) -> List[Dict]:
    """Second-pass refinement enforcing strict rubric, benchmarks, and BOTEC rigor."""
    import json
    if not draft_ideas:
        return []
    topics_l = (topics or "").lower()
    is_animal = any(k in topics_l for k in ["animal", "welfare", "broiler", "fish", "shrimp", "layer", "poultry", "swine", "aquaculture"])
    is_global_health = any(k in topics_l for k in [
        "health", "malaria", "tb", "hiv", "pandemic", "epidemic"
    ])

    rubric = (
        "You are a meticulous editor who transforms draft philanthropic ideas into strictly structured, benchmark-anchored, high-specificity plans.\n"
        "Rules:\n"
        "- Each idea must follow the template sentence and include numeric targets, costs, and cost-effectiveness vs an explicit benchmark.\n"
        "- Metrics: DALY (vs GiveWell), WALY (vs The Humane League; use ACE only if THL N/A), WELBY (vs StrongMinds-like), log income (vs GiveDirectly), CO2 (vs frontier climate).\n"
        "- BOTEC must include target_question, decomposition, anchors (with refs/URLs), assumptions (with ranges), formulas, estimates (impact_units, total_cost_usd, ce_value, ce_units), benchmark (name, range), comparison (numeric delta), sensitivity (2–3 top drivers).\n"
        "- Include a verification plan with independently auditable criteria and named auditor types when it materially increases credibility; if omitted, briefly justify.\n"
        "- Include 1–3 doers (individuals preferred) with scores (1–7) and rationale; else a 2–3 sentence archetype.\n"
        "- Reject vague metrics (e.g., 'cases prevented'); use DALY/WALY/CO2 etc.\n"
        "- Do NOT replicate well-known benchmark programs. Ideas must be novel or meaningfully re-engineered so they are not isomorphic to these.\n"
        "- For each idea, add 'novelty_rationale' (2–3 sentences) explaining what is new (mechanism, verification, buyer config, TPP, or delivery innovation) and why this could beat benchmarks on expected value.\n"
    )
    if is_animal:
        rubric += (
            "- Animal welfare: cause-neutral, EV-first. First rank sources of suffering by scale/intensity (taxa/production systems), consider multiple mechanisms, compute EV (WALY), and select the highest-EV options.\n"
            "- WALY required; state animals improved/year and $/animal-year vs THL baseline.\n"
        )
    if is_global_health:
        rubric += (
            "- Global health: DALY required; state $/DALY vs GiveWell; focus on highest-burden causes per GBD/IHME rather than prespecified interventions.\n"
        )

    user = (
        "Refine the following draft ideas strictly to this schema. Output a JSON object with a single key 'ideas' containing the refined list.\n\n"
        f"Draft ideas JSON:\n{json.dumps(draft_ideas) }\n"
    )
    messages = [
        {"role": "system", "content": rubric},
        {"role": "user", "content": user},
    ]
    refine_model = os.getenv("OPENAI_MODEL") or ("o3" if deep_research else "gpt-4o")
    raw = _call_llm(messages, model=refine_model, max_tokens=(3000 if deep_research else 2000), temperature=0.2)
    # Parse refined
    clean = raw.strip()
    if clean.startswith("```"):
        m = re.search(r"```(?:json)?\n([\s\S]*?)```", clean, re.IGNORECASE)
        if m:
            clean = m.group(1).strip()
    try:
        obj = json.loads(clean)
        if isinstance(obj, dict) and isinstance(obj.get("ideas"), list):
            return obj.get("ideas", [])
        if isinstance(obj, list):
            return obj
    except Exception:
        return draft_ideas
    return draft_ideas


