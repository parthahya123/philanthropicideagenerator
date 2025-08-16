import os, json
from src.connectors.rss_sources import fetch_rss_items, DEFAULT_RSS_SOURCES
from src.connectors.arxiv_connector import search_arxiv
from src.connectors.bio_connector import search_bio_server
from src.connectors.who_gho import search_gho_indicators
from src.connectors.ghdx import fetch_gbd_dalys_latest
from src.connectors.crossref import search_crossref
from src.synthesis.idea_generator import synthesize_ideas

def ingest(topics: str, max_items=5):
    docs = []
    docs.extend(fetch_rss_items(DEFAULT_RSS_SOURCES, limit=max_items))
    if topics.strip():
        docs.extend(search_arxiv(topics, max_results=max_items))
        docs.extend(search_bio_server(topics, server="biorxiv", max_results=max_items))
        docs.extend(search_bio_server(topics, server="medrxiv", max_results=max_items))
        for kw in [t.strip() for t in topics.split(',') if t.strip()]:
            docs.extend(search_gho_indicators(kw, limit=3))
            docs.extend(search_crossref(kw, rows=3))
    docs.extend(fetch_gbd_dalys_latest())
    return docs

runs = [
    ("global health, DALYs", 5),
    ("animal welfare, WALYs", 5),
]
all_out = {}
for topics, n in runs:
    os.environ.setdefault("OPENAI_MODEL", os.environ.get("OPENAI_MODEL", "o3"))
    docs = ingest(topics, max_items=5)
    res = synthesize_ideas(topics=topics, documents=docs, num_ideas=n, show_reasoning=True, deep_research=True)
    all_out[topics] = {
        "docs_count": res.get("docs_count"),
        "ideas_count": len(res.get("ideas", [])),
        "ideas": res.get("ideas", [])
    }
print(json.dumps(all_out, indent=2))
