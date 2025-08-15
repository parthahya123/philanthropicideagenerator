from typing import List
import requests


def search_crossref(query: str, rows: int = 10) -> List[dict]:
    docs: List[dict] = []
    try:
        url = "https://api.crossref.org/works"
        params = {"query": query, "rows": rows, "select": "title,DOI,URL,author,issued,type"}
        r = requests.get(url, params=params, timeout=20, headers={"User-Agent": "idea-generator/0.1"})
        if not r.ok:
            return docs
        items = r.json().get("message", {}).get("items", [])
        for it in items:
            title = (it.get("title") or [""])[0]
            url = it.get("URL") or ("https://doi.org/" + it.get("DOI", ""))
            year = None
            issued = it.get("issued", {}).get("\"date-parts\"") or it.get("issued", {}).get("date-parts")
            if isinstance(issued, list) and issued and isinstance(issued[0], list) and issued[0]:
                year = issued[0][0]
            docs.append(
                {
                    "source": "Crossref",
                    "title": title,
                    "url": url,
                    "summary": "",
                    "published": str(year or ""),
                    "type": "crossref",
                }
            )
    except Exception:
        pass
    return docs


