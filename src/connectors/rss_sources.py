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
    "Our World in Data": "https://ourworldindata.org/feed",
    "IHME": "https://www.healthdata.org/rss.xml",
    "Wild Animal Initiative": "https://www.wildanimalinitiative.org/blog?format=rss",
    "Matt Clancy (New Things Under the Sun)": "https://www.newthingsunderthesun.com/rss.xml",
    "Michael Nielsen": "https://michaelnielsen.org/feed/",
    "Lauren Policy": "https://www.laurenpolicy.com/feed",
    "Sarah Constantin": "https://sarahconstantin.substack.com/feed",
    "Jacob Trefethen": "https://jacobtrefethen.substack.com/feed",
    "Statecraft": "https://statecraft.pub/feed",
    "Asimov Press": "https://asimovpress.substack.com/feed",
    "The Great Gender Divergence": "https://greatgenderdivergence.substack.com/feed",
    "Devon Zuegel": "https://devonzuegel.com/feed.xml",
    "Sam Rodrigues": "https://samrod.substack.com/feed",
    "Lant Pritchett": "https://lantpritchett.substack.com/feed",
    "Gwern": "https://www.gwern.net/atom.xml",
    "Animal Charity Evaluators": "https://animalcharityevaluators.org/blog/feed/",
    "Marginal Revolution": "https://marginalrevolution.com/feed",
    "Ben Reinhardt": "https://benreinhardt.substack.com/feed",
    "Congression Research Service (EveryCRSReport)": "https://www.everycrsreport.com/rss/current.xml",
    "Council of Economic Advisers": "https://www.whitehouse.gov/cea/feed/",
    "eryney": "https://substack.com/feed/@eryney",
    "Abhishaik Mahajan": "https://substack.com/feed/@abhishaikemahajan",
    "Global Developments (Oliver Kim)": "https://www.global-developments.org/feed",
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


