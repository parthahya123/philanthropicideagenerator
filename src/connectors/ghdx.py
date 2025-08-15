from typing import List, Dict, Optional
import json
import base64
import requests


GHDX_DOWNLOAD = "https://ghdx.healthdata.org/gbd-results-tool/download.csv"


def _encode_params(params: Dict) -> str:
    raw = json.dumps(params, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def fetch_gbd_dalys_latest(candidates_years: Optional[List[int]] = None) -> List[Dict]:
    """Attempt to fetch a simple Global DALYs CSV for the latest available year.
    Returns a list with one 'document' entry containing the CSV URL and metadata if successful.
    """
    if candidates_years is None:
        # Known public GBD full releases: 2019, 2021 (updates vary by domain)
        candidates_years = [2021, 2019]

    for y in candidates_years:
        params = {
            "measure": ["DALYs"],
            "metric": ["Number"],
            "location": ["Global"],
            "age": ["All Ages"],
            "sex": ["Both"],
            "cause": ["All causes"],
            "year": [str(y)],
        }
        enc = _encode_params(params)
        url = f"{GHDX_DOWNLOAD}?params={enc}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.ok and len(resp.content) > 100:  # crude sanity check
                return [
                    {
                        "source": "GHDx GBD",
                        "title": f"GBD Global DALYs (Number), {y}",
                        "url": url,
                        "summary": "Global DALYs across all causes, all ages, both sexes (CSV).",
                        "published": str(y),
                        "type": "ghdx_gbd",
                    }
                ]
        except Exception:
            continue
    return []


