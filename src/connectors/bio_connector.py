from typing import List
import requests


def search_bio_server(query: str, server: str = "biorxiv", max_results: int = 10) -> List[dict]:
    """Search bioRxiv/medRxiv API by simple query string across recent timeframe.
    server: 'biorxiv' or 'medrxiv'
    """
    docs: List[dict] = []
    base = "https://api.biorxiv.org/details"
    try:
        # Use 'any' endpoint for simple query; fallback to latest if query fails
        url = f"{base}/{server}/2023-01-01/3000-01-01/{query.replace(' ', '%20')}"
        resp = requests.get(url, timeout=20)
        if resp.ok:
            data = resp.json()
            for item in data.get("collection", [])[:max_results]:
                docs.append(
                    {
                        "source": server,
                        "title": item.get("title", ""),
                        "url": f"https://www.biorxiv.org/content/{item.get('doi','')}",
                        "summary": item.get("abstract", ""),
                        "published": item.get("date", ""),
                        "type": server,
                    }
                )
    except Exception:
        pass
    return docs


