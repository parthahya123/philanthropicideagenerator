import os
import subprocess
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
if "debug_raw" not in st.session_state:
    st.session_state.debug_raw = ""
if "debug_docs_count" not in st.session_state:
    st.session_state.debug_docs_count = 0


with st.sidebar:
    st.header("Configuration")
    # Allow secure, in-app API key entry without writing to disk
    if not os.getenv("OPENAI_API_KEY"):
        entered_key = st.text_input("OpenAI API Key", type="password", help="Key is stored only in memory for this session.")
        if entered_key:
            os.environ["OPENAI_API_KEY"] = entered_key.strip()
    openai_key_present = bool(os.getenv("OPENAI_API_KEY"))
    st.write("OpenAI key loaded:" + (" ✅" if openai_key_present else " ❌"))
    goal_options = [
        "Improve global health (DALYs)",
        "Reduce animal suffering (WALYs)",
        "Increase economic growth in developing countries (log income)",
        "Improve mental health (WELBY)",
        "Prevent catastrophic risks (pandemics, nuclear) (DALYs)",
        "Reduce climate risk (CO2)",
        "Custom",
    ]
    goal_choice = st.selectbox(
        "What is your goal?",
        options=goal_options,
        index=0,
        help="Choose a broad objective. The model will tailor ideas and benchmarks accordingly.",
    )
    goal_map = {
        "Improve global health (DALYs)": "global health, DALYs",
        "Reduce animal suffering (WALYs)": "animal welfare, WALYs",
        "Increase economic growth in developing countries (log income)": "economic growth, log income",
        "Improve mental health (WELBY)": "mental health, WELBY",
        "Prevent catastrophic risks (pandemics, nuclear) (DALYs)": "catastrophic risks, pandemics, nuclear, DALYs",
        "Reduce climate risk (CO2)": "climate, CO2",
    }
    details = st.text_input(
        "Add specifics (optional)",
        value="",
        help="Briefly add target geographies, mechanisms, or constraints.",
    )
    # Assemble topics string for ingestion/synthesis
    base = goal_map.get(goal_choice, "")
    topics = ", ".join([t for t in [base, details] if t.strip()])
    max_items = st.slider("Max items per source", 5, 20, 10)
    num_ideas = st.slider("Ideas to generate", 5, 40, 5)
    deep_research = st.checkbox("Deep research mode (two-step refinement, larger context)", value=True)
    st.write("Benchmarks (fixed):")
    st.json(BENCHMARKS, expanded=False)

    # Run info
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except Exception:
        branch, commit = "unknown", "unknown"
    st.caption(f"Model: {os.getenv('OPENAI_MODEL', 'unset')} | Branch: {branch} | Commit: {commit}")

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
                    result = synthesize_ideas(
                        topics=topics,
                        documents=docs,
                        num_ideas=num_ideas,
                        show_reasoning=True,
                        deep_research=deep_research,
                    )
                    if isinstance(result, dict) and "ideas" in result:
                        st.session_state.ideas = result.get("ideas", [])
                        st.session_state.debug_raw = result.get("raw", "")
                        st.session_state.debug_docs_count = result.get("docs_count", 0)
                    else:
                        st.session_state.ideas = result or []
                        st.session_state.debug_raw = ""
                        st.session_state.debug_docs_count = len(docs)
                    st.success(f"Generated {len(st.session_state.ideas)} ideas.")
                except Exception as e:
                    st.session_state.ideas = []
                    st.session_state.debug_raw = ""
                    st.session_state.debug_docs_count = 0
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
            # Use tabs instead of nested expanders (Streamlit forbids nested expanders)
            tabs = st.tabs(["BOTEC", "Chain of reasoning", "Reasoning", "Doers", "Sources"])
            with tabs[0]:
                if idea.get("botec"):
                    st.json(idea["botec"], expanded=False)
                else:
                    st.write("No BOTEC provided.")
            with tabs[1]:
                botec = idea.get("botec", {}) or {}
                if botec:
                    if botec.get("target_question"):
                        st.write(f"Target question: {botec.get('target_question')}")
                    if botec.get("decomposition"):
                        st.write("Decomposition:")
                        for comp in botec.get("decomposition", [])[:10]:
                            st.write(f"- {comp}")
                    if botec.get("anchors"):
                        st.write("Anchors:")
                        for a in botec.get("anchors", [])[:10]:
                            ref = a.get("ref") if isinstance(a, dict) else None
                            url = a.get("url") if isinstance(a, dict) else None
                            if ref and url:
                                st.markdown(f"- [{ref}]({url})")
                            elif ref:
                                st.write(f"- {ref}")
                    if botec.get("assumptions"):
                        st.write("Assumptions:")
                        for k, v in list(botec.get("assumptions", {}).items())[:10]:
                            st.write(f"- {k}: {v}")
                    if botec.get("formulas"):
                        st.write("Formulas:")
                        try:
                            st.code("\n".join(botec.get("formulas", [])[:10]))
                        except Exception:
                            st.write(botec.get("formulas"))
                    if botec.get("sensitivity"):
                        st.write("Sensitivity (top drivers):")
                        for s in botec.get("sensitivity", [])[:10]:
                            st.write(f"- {s}")
                debate = idea.get("debate", {}) or {}
                if debate:
                    st.write("Adversarial review (Roodman-style):")
                    for sec in ["criticisms", "rebuttals"]:
                        if debate.get(sec):
                            st.write(sec.capitalize() + ":")
                            for item in debate.get(sec, [])[:10]:
                                st.write(f"- {item}")
                    if debate.get("revised_assumptions"):
                        st.write("Revised assumptions:")
                        for k, v in list(debate.get("revised_assumptions", {}).items())[:10]:
                            st.write(f"- {k}: {v}")
                    if debate.get("recalc"):
                        st.write("Recalculated CE:")
                        st.json(debate.get("recalc"), expanded=False)
                    if debate.get("final_conclusion"):
                        st.write("Final conclusion:")
                        st.write(debate.get("final_conclusion"))
            with tabs[2]:
                if idea.get("reasoning"):
                    st.json(idea["reasoning"], expanded=False)
                else:
                    st.write("No extended reasoning provided.")
            with tabs[3]:
                if idea.get("doers"):
                    st.json(idea["doers"], expanded=False)
                elif idea.get("doer_archetype"):
                    st.write(idea["doer_archetype"])
                else:
                    st.write("No doers provided.")
            with tabs[4]:
                if idea.get("sources"):
                    for s in idea["sources"][:10]:
                        st.write(f"- [{s.get('title','source')}]({s.get('url')})")
                else:
                    st.write("No sources listed.")

with st.expander("Debug (last run)", expanded=False):
    st.write(f"Docs ingested: {st.session_state.get('debug_docs_count', 0)}")
    raw = st.session_state.get("debug_raw", "")
    if raw:
        st.code(raw[:1200] + ("\n..." if len(raw) > 1200 else ""))


with st.expander("Advanced: show ingested docs (from last run)", expanded=False):
    st.write("Docs are fetched automatically when generating ideas.")
    if st.session_state.ideas:
        st.write("Top source links embedded in each idea above.")


