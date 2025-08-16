## Idea Generator MVP

An MVP that ingests reputable sources (RSS/APIs), extracts key claims, and synthesizes benchmark‑anchored philanthropic ideas with BOTECs (Back‑Of‑The‑Envelope Calculations) using your template:

"Funding what, through what mechanism, with the expectation of having what impact at what cost, resulting in what cost‑effectiveness vs benchmark."

### How it works (high‑level)
- Ingestion: pulls from whitelisted sources (Open Phil, Rethink Priorities, EA Forum, CGD, OWID, IHME/WHO GHO/GHDx, Wild Animal Initiative, ACE, selected Substacks) via RSS/APIs.
- Evidence extraction: builds a compact context of titles/summaries/links (priority: Open Phil/ACE/WAI/WHO/IHME/FAOSTAT/Fishcount).
- Synthesis: generates ideas with a strict rubric (cause‑neutral, EV‑first; correct metric→benchmark mapping; verification; novelty rationale; doers; Roodman‑style critique).
- Refinement: a second pass enforces the schema, fills missing BOTEC/doers/reasoning from the ingested evidence only, normalizes benchmarks, and rejects “benchmark clones.”
- Output: ideas are displayed in tabs (BOTEC, Chain of reasoning, Reasoning, Doers, Sources) and downloadable as JSON; you can also export CSV/MD with the provided eval tooling.

Benchmarks (no cross‑metric conversion):
- DALY → GiveWell Top Charities
- WALY → The Humane League (ACE only if THL not applicable)
- WELBY → StrongMinds‑like references
- log income → GiveDirectly
- CO2 → frontier climate $/tCO2e

### Quick start

1) Prereqs
- Python 3.11+ (you have 3.12)
- Streamlit
- OpenAI API key

2) Setup
```
cd /Users/parthahya/idea-generator
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=YOUR_KEY_HERE
```

3) Run
```
streamlit run app.py
```

4) Use
- Choose your goal (e.g., "Improve global health (DALYs)", "Reduce animal suffering (WALYs)") and optionally add specifics (geographies/mechanisms).
- Click Generate ideas — the app auto‑ingests sources and synthesizes.
- Deep research mode: toggle in the sidebar for a two‑pass, higher‑rigor run (uses o3, larger token budget, lower temperature).
- Inspect ideas in tabs (BOTEC, Chain of reasoning, Reasoning, Doers, Sources) and export JSON.

### Eval tooling (optional)
Run generic deep‑research evaluations and capture outputs (JSON):
```
source .venv/bin/activate
export OPENAI_MODEL=o3
python tools_run_eval.py | tee /tmp/eval_run_generic.json
```

### Docker (optional, easiest portable run)
Build and run with Docker:
```
docker build -t idea-generator .
docker run -it --rm -p 8501:8501 -e OPENAI_API_KEY=YOUR_KEY idea-generator
```
Open http://localhost:8501

### What the model enforces
- Cause‑neutral, EV‑first selection (no “benchmark clones”).
- Correct metric→benchmark mapping (DALY→GiveWell, WALY→THL, WELBY→StrongMinds‑like, log income→GiveDirectly, CO2→frontier climate).
- Required fields: BOTEC (assumptions, formulas, anchors, sensitivity), verification plan (independent, pass/fail), doers (named/scored) or a detailed archetype (no score), novelty rationale, ≥2 citations from ingested sources.
- Plain but precise language (define acronyms once; minimal jargon).

### Sources (initial)
- RSS/APIs: Open Philanthropy, Rethink Priorities, Astral Codex Ten, Dwarkesh Patel, Brian Potter, Slow Boring, CGD, EA Forum, Lewis Bollard, Asterisk, Our World in Data, IHME, Wild Animal Initiative, Matt Clancy, Michael Nielsen, Lauren Policy, Sarah Constantin, Jacob Trefethen, Statecraft, Asimov Press, Great Gender Divergence, Devon Zuegel, Sam Rodrigues, Lant Pritchett, Gwern, Animal Charity Evaluators, Marginal Revolution, Ben Reinhardt, EveryCRSReport (CRS), CEA feed, eryney, Abhishaik Mahajan, Global Developments (Oliver Kim).
- Data: WHO GHO (OData), GHDx (GBD results), Crossref/Unpaywall, arXiv, bioRxiv/medRxiv.

### Notes
- Only uses whitelisted/public sources via RSS/APIs; respects robots.txt.
- Outputs are benchmark‑anchored and verifiable; no cross‑metric conversions.

### Sources (initial)
- RSS: Open Philanthropy, Rethink Priorities, ACX, Dwarkesh, Brian Potter, Slow Boring, CGD, EA Forum, Lewis Bollard, Statecraft, Asterisk, etc.
- arXiv: query by topics.
- bioRxiv/medRxiv: recent preprints by topic.
- WHO GHO: optional indicators.

### Benchmarks
- DALY: GiveWell top-charity range.
- Log income: GiveDirectly.
- WELBY: StrongMinds-like references.
- WALY: Humane League/ACE ranges.
- CO2: frontier climate $/tCO2e.

Configured in code with editable defaults (see `src/synthesis/botec.py`).

### GitHub
Initialize and push:
```
cd /Users/parthahya/idea-generator
git init
git add .
git commit -m "feat: MVP idea generator (Streamlit, sources, synthesis, BOTEC)"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

Or install GitHub CLI and I can automate repo creation.

### Notes
- Only pulls from whitelisted, public sources using RSS/APIs. No scraping.
- Respects source ToS and fair use. Stores only metadata and snippets locally.
- This is an MVP; connectors are modular and easy to extend.


