from typing import List
import arxiv


def search_arxiv(query: str, max_results: int = 10) -> List[dict]:
    docs: List[dict] = []
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )
        for result in arxiv.Client().results(search):
            docs.append(
                {
                    "source": "arXiv",
                    "title": result.title,
                    "url": result.entry_id,
                    "summary": result.summary,
                    "published": result.published.strftime("%Y-%m-%d"),
                    "type": "arxiv",
                }
            )
    except Exception:
        pass
    return docs


