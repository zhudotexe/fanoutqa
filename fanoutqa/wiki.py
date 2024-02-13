"""Utils for working with Wikipedia"""

import functools
import logging
import urllib.parse

import httpx

from .models import Evidence
from .utils import CACHE_DIR, DATASET_EPOCH, markdownify

USER_AGENT = "fanoutqa/1.0.0 (andrz@seas.upenn.edu)"
WIKI_CACHE_DIR = CACHE_DIR / "wikicache"
WIKI_CACHE_DIR.mkdir(exist_ok=True, parents=True)

log = logging.getLogger(__name__)
wikipedia = httpx.Client(
    base_url="https://en.wikipedia.org/w/api.php", headers={"User-Agent": USER_AGENT}, follow_redirects=True
)


class LazyEvidence(Evidence):
    """A subclass of Evidence without a known revision ID; lazily loads it when needed."""

    def __init__(self, title: str, pageid: int, url: str = None):
        self.title = title
        self.pageid = pageid
        self._url = url

    @property
    def url(self):
        if self._url is not None:
            return self._url
        encoded_title = urllib.parse.quote(self.title)
        return f"https://en.wikipedia.org/wiki/{encoded_title}"

    @functools.cached_property
    def revid(self):
        resp = wikipedia.get(
            "",
            params={
                "format": "json",
                "action": "query",
                "prop": "revisions",
                "rvprop": "ids|timestamp",
                "rvlimit": 1,
                "pageids": self.pageid,
                "rvstart": DATASET_EPOCH.isoformat(),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        page = data["query"]["pages"][str(self.pageid)]
        return page["revisions"][0]["revid"]


@functools.lru_cache()
def wiki_search(query: str, results=10) -> list[Evidence]:
    """Return a list of Evidence documents given the search query."""
    # get the list of articles that match the query
    resp = wikipedia.get(
        "", params={"format": "json", "action": "query", "list": "search", "srsearch": query, "srlimit": results}
    )
    resp.raise_for_status()
    data = resp.json()

    # and return a LazyEvidence for each
    return [LazyEvidence(title=d["title"], pageid=d["pageid"]) for d in data["query"]["search"]]


def wiki_content(doc: Evidence) -> str:
    """Get the page content in markdown, including tables and infoboxes, appropriate for displaying to an LLM."""
    # get the cached content, if available
    cache_filename = WIKI_CACHE_DIR / f"{doc.pageid}-dated.md"
    if cache_filename.exists():
        return cache_filename.read_text()

    # otherwise retrieve it from Wikipedia
    resp = wikipedia.get("", params={"format": "json", "action": "parse", "oldid": doc.revid, "prop": "text"})
    resp.raise_for_status()
    data = resp.json()
    try:
        html = data["parse"]["text"]["*"]
    except KeyError:
        log.warning(f"Could not find dated revision of {doc.title} - maybe the page did not exist yet?")
        html = ""

    # MD it, cache it, and return
    text = markdownify(html)
    cache_filename.write_text(text)
    return text
