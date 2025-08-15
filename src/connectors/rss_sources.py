from typing import Dict, List
import feedparser


DEFAULT_RSS_SOURCES: Dict[str, str] = {
    "Open Philanthropy": "https://www.openphilanthropy.org/feed/",
    "Rethink Priorities": "https://rethinkpriorities.org/blog?format=rss",
    "Astral Codex Ten": "https://astralcodexten.substack.com/feed",
    "Dwarkesh Patel": "https://www.dwarkeshpatel.com/rss/",
    "Brian Potter": "https://www.construction-physics.com/feed",
    "Slow Boring": "https://www.slowboring.com/feed",
    "CGD": "https://www.cgdev.org/rss.xml",
    "EA Forum": "https://forum.effectivealtruism.org/posts.rss",
    "Lewis Bollard": "https://www.lewisbollard.com/feed",
    "Asterisk Magazine": "https://asteriskmag.com/feed.xml",
}


def fetch_rss_items(sources: Dict[str, str], limit: int = 10) -> List[dict]:
    docs: List[dict] = []
    for name, url in sources.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                docs.append(
                    {
                        "source": name,
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": entry.get("summary", ""),
                        "published": entry.get("published", ""),
                        "type": "rss",
                    }
                )
        except Exception:
            continue
    return docs


