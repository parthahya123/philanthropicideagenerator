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


load_dotenv()

st.set_page_config(page_title="Idea Generator MVP", layout="wide")
st.title("Idea Generator MVP")
st.caption("Generates philanthropic ideas from reputable sources and synthesizes light BOTECs.")


if "docs" not in st.session_state:
    st.session_state.docs = []
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
        help="Used for arXiv/bioRxiv queries and LLM focus",
    )
    max_items = st.slider("Max items per source", 5, 20, 10)
    num_ideas = st.slider("Ideas to generate", 10, 40, 25)
    st.write("Benchmarks (fixed):")
    st.json(BENCHMARKS, expanded=False)

st.subheader("Sources")
col1, col2 = st.columns(2)
with col1:
    selected_rss = st.multiselect(
        "RSS sources",
        options=list(DEFAULT_RSS_SOURCES.keys()),
        default=[
            "Open Philanthropy",
            "Rethink Priorities",
            "Astral Codex Ten",
            "CGD",
            "EA Forum",
            "Brian Potter",
            "Slow Boring",
        ],
    )
with col2:
    use_arxiv = st.checkbox("Include arXiv", value=True)
    use_biorxiv = st.checkbox("Include bioRxiv", value=True)
    use_medrxiv = st.checkbox("Include medRxiv", value=True)
    use_who_gho = st.checkbox("Include WHO GHO indicators", value=False)


def ingest() -> List[Dict]:
    docs: List[Dict] = []
    # RSS
    if selected_rss:
        rss_docs = fetch_rss_items({k: DEFAULT_RSS_SOURCES[k] for k in selected_rss}, limit=max_items)
        docs.extend(rss_docs)
    # arXiv
    if use_arxiv and topics.strip():
        docs.extend(search_arxiv(topics, max_results=max_items))
    # bioRxiv / medRxiv
    if topics.strip():
        if use_biorxiv:
            docs.extend(search_bio_server(topics, server="biorxiv", max_results=max_items))
        if use_medrxiv:
            docs.extend(search_bio_server(topics, server="medrxiv", max_results=max_items))
    # WHO GHO
    if use_who_gho and topics.strip():
        for kw in [t.strip() for t in topics.split(",") if t.strip()]:
            docs.extend(search_gho_indicators(kw, limit=5))
    return docs


with st.expander("Ingested documents", expanded=False):
    st.write("No documents yet. Click 'Ingest sources' below.")


ingest_col, gen_col, export_col = st.columns([1, 1, 1])
with ingest_col:
    if st.button("Ingest sources"):
        with st.spinner("Fetching sources..."):
            st.session_state.docs = ingest()
        st.success(f"Fetched {len(st.session_state.docs)} documents.")
with gen_col:
    if st.button("Generate ideas"):
        if not os.getenv("OPENAI_API_KEY"):
            st.error("Missing OPENAI_API_KEY. Set it in your environment or .env file.")
        elif not st.session_state.docs:
            st.warning("No documents ingested. Click 'Ingest sources' first.")
        else:
            with st.spinner("Synthesizing ideas with BOTECs..."):
                st.session_state.ideas = synthesize_ideas(
                    topics=topics,
                    documents=st.session_state.docs,
                    num_ideas=num_ideas,
                )
            st.success(f"Generated {len(st.session_state.ideas)} ideas.")
with export_col:
    if st.session_state.ideas:
        ideas_json = json.dumps(st.session_state.ideas, indent=2)
        st.download_button("Download JSON", data=ideas_json, file_name="ideas.json", mime="application/json")


st.subheader("Ideas")
if not st.session_state.ideas:
    st.info("No ideas yet. Ingest sources, then generate ideas.")
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


