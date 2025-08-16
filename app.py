import os
import json
import time
from typing import List, Dict

import streamlit as st
from dotenv import load_dotenv

from src.connectors.rss_sources import fetch_rss_items, DEFAULT_RSS_SOURCES
from src.connectors.arxiv_connector import search_arxiv
from src.connectors.bio_connector import search_bio_server
from src.synthesis.idea_generator import synthesize_ideas
from src.synthesis.botec import BENCHMARKS
from src.connectors.who_gho import search_gho_indicators
from src.connectors.ghdx import fetch_gbd_dalys_latest
from src.connectors.crossref import search_crossref


load_dotenv()

st.set_page_config(page_title="Idea Generator MVP", layout="wide")
st.title("Idea Generator MVP")
st.caption("Generates philanthropic ideas from reputable sources and synthesizes light BOTECs.")


if "ideas" not in st.session_state:
    st.session_state.ideas = []


with st.sidebar:
    st.header("Configuration")
    # Allow secure, in-app API key entry without writing to disk
    if not os.getenv("OPENAI_API_KEY"):
        entered_key = st.text_input("OpenAI API Key", type="password", help="Key is stored only in memory for this session.")
        if entered_key:
            os.environ["OPENAI_API_KEY"] = entered_key.strip()
    openai_key_present = bool(os.getenv("OPENAI_API_KEY"))
    st.write("OpenAI key loaded:" + (" ✅" if openai_key_present else " ❌"))
    topics = st.text_input(
        "Topics (comma-separated)",
        value="statins, broiler welfare, respirators, clean indoor air, lead exposure, e-cooking, GLP-1, TB preventive therapy",
        help="Used for API queries and LLM focus",
    )
    max_items = st.slider("Max items per source", 5, 20, 10)
    num_ideas = st.slider("Ideas to generate", 5, 40, 5)
    st.write("Benchmarks (fixed):")
    st.json(BENCHMARKS, expanded=False)

st.subheader("Sources used (auto-selected)")
st.caption("The app chooses reputable sources automatically; no selection needed.")
st.write(", ".join(sorted(DEFAULT_RSS_SOURCES.keys() | set(["arXiv", "bioRxiv", "medRxiv", "WHO GHO", "GHDx GBD", "Crossref"]))))


def ingest() -> List[Dict]:
    docs: List[Dict] = []
    # RSS
    rss_docs = fetch_rss_items(DEFAULT_RSS_SOURCES, limit=max_items)
    docs.extend(rss_docs)
    # arXiv
    if topics.strip():
        docs.extend(search_arxiv(topics, max_results=max_items))
    # bioRxiv / medRxiv
    if topics.strip():
        docs.extend(search_bio_server(topics, server="biorxiv", max_results=max_items))
        docs.extend(search_bio_server(topics, server="medrxiv", max_results=max_items))
    # WHO GHO
    if topics.strip():
        for kw in [t.strip() for t in topics.split(",") if t.strip()]:
            docs.extend(search_gho_indicators(kw, limit=5))
    # GHDx GBD
    docs.extend(fetch_gbd_dalys_latest())
    # Crossref
    if topics.strip():
        for kw in [t.strip() for t in topics.split(",") if t.strip()]:
            docs.extend(search_crossref(kw, rows=5))
    return docs


gen_col, export_col = st.columns([1, 1])
with gen_col:
    if st.button("Generate ideas", type="primary"):
        if not os.getenv("OPENAI_API_KEY"):
            st.error("Missing OPENAI_API_KEY. Set it in the sidebar or your environment.")
        else:
            with st.spinner("Fetching sources and synthesizing ideas..."):
                try:
                    docs = ingest()
                    st.session_state.ideas = synthesize_ideas(
                        topics=topics,
                        documents=docs,
                        num_ideas=num_ideas,
                    )
                    st.success(f"Generated {len(st.session_state.ideas)} ideas.")
                except Exception as e:
                    st.session_state.ideas = []
                    st.error(f"Generation failed: {e}")
with export_col:
    if st.session_state.ideas:
        ideas_json = json.dumps(st.session_state.ideas, indent=2)
        st.download_button("Download JSON", data=ideas_json, file_name="ideas.json", mime="application/json")


st.subheader("Ideas")
if not st.session_state.ideas:
    st.info("No ideas yet. Click 'Generate ideas'.")
else:
    for idx, idea in enumerate(st.session_state.ideas, 1):
        with st.expander(f"{idx}. {idea.get('title', 'Idea')}", expanded=False):
            st.markdown(idea.get("description", ""))
            meta_cols = st.columns(4)
            meta_cols[0].write(f"Metric: {idea.get('metric_tag', 'n/a')}")
            meta_cols[1].write(f"Instrument: {idea.get('instrument', 'n/a')}")
            meta_cols[2].write(f"CE vs benchmark: {idea.get('ce_vs_benchmark', 'n/a')}")
            meta_cols[3].write(f"Total cost: {idea.get('total_cost', 'n/a')}")
            if idea.get("candidates"):
                st.write("Candidates:")
                st.write(", ".join(idea["candidates"]))
            if idea.get("sources"):
                st.write("Evidence sources:")
                for s in idea["sources"][:5]:
                    st.write(f"- [{s.get('title','source')}]({s.get('url')})")

with st.expander("Advanced: show ingested docs (from last run)", expanded=False):
    st.write("Docs are fetched automatically when generating ideas.")
    if st.session_state.ideas:
        st.write("Top source links embedded in each idea above.")


