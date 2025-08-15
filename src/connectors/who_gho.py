from typing import List
import requests


GHO_API = "https://ghoapi.azureedge.net/ghoapi/api/"


def search_gho_indicators(keyword: str, limit: int = 20) -> List[dict]:
    """Search WHO GHO indicators by keyword and return indicator metadata/links.
    Uses the Dimensions endpoint and filters on Code/Title.
    """
    out: List[dict] = []
    try:
        r = requests.get(GHO_API + "Indicator", timeout=20)
        if not r.ok:
            return out
        data = r.json().get("value", [])
        kw = keyword.lower()
        for item in data:
            code = (item.get("Code") or "").lower()
            title = (item.get("Title") or "").lower()
            if kw in code or kw in title:
                out.append(
                    {
                        "source": "WHO GHO",
                        "title": item.get("Title", "Indicator"),
                        "url": f"https://ghoapi.azureedge.net/ghoapi/api/Indicator?$filter=Code%20eq%20'{item.get('Code','')}'",
                        "summary": f"Indicator code: {item.get('Code','')}",
                        "published": "",
                        "type": "who_gho",
                    }
                )
                if len(out) >= limit:
                    break
    except Exception:
        pass
    return out


