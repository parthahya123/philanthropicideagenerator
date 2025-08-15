## Idea Generator MVP

An MVP that ingests reputable sources (RSS/APIs), extracts key claims, and synthesizes philanthropic ideas with light BOTECs in your preferred template:

"Funding what, through what mechanism, with the expectation of having what impact at what cost, resulting in what cost-effectiveness vs benchmark."

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
- Select sources and topics.
- Click Ingest to fetch ~10 recent items/source.
- Click Generate Ideas to synthesize a 25-idea shortlist.
- Export to CSV/Markdown.

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


