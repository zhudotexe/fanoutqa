"""Utils for working with Wikipedia"""

import functools
import logging
import urllib.parse

import pywikibot

from .models import Evidence
from .utils import CACHE_DIR, DATASET_EPOCH, markdownify

WIKI_CACHE_DIR = CACHE_DIR / "wikicache"
WIKI_CACHE_DIR.mkdir(exist_ok=True, parents=True)
PWB_CACHE_DIR = CACHE_DIR / "pywikibot"
pywikibot.config.base_dir = str(PWB_CACHE_DIR.resolve())

log = logging.getLogger(__name__)
_site = pywikibot.Site("en", "wikipedia")


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
        req = _site.simple_request(
            action="query",
            prop="revisions",
            rvprop="ids|timestamp",
            rvlimit=1,
            pageids=self.pageid,
            rvstart=DATASET_EPOCH.isoformat(),
        )
        data = req.submit()
        page = data["query"]["pages"][str(self.pageid)]
        try:
            return page["revisions"][0]["revid"]
        except KeyError:
            return None


@functools.lru_cache()
def wiki_search(query: str, results=10) -> list[Evidence]:
    """Return a list of Evidence documents given the search query."""
    # get the list of articles that match the query
    # and return a LazyEvidence for each
    return [LazyEvidence(title=page.title(), pageid=page.pageid) for page in _site.search(query, total=results)]


def wiki_content(doc: Evidence) -> str:
    """Get the page content in markdown, including tables and infoboxes, appropriate for displaying to an LLM."""
    # get the cached content, if available
    cache_filename = WIKI_CACHE_DIR / f"{doc.pageid}-dated.md"
    if cache_filename.exists():
        try:
            return cache_filename.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            pass

    # otherwise retrieve it from Wikipedia
    req = _site.simple_request(action="parse", oldid=doc.revid, prop="text")
    data = req.submit()
    try:
        html = data["parse"]["text"]["*"]
    except KeyError:
        log.warning(f"Could not find dated revision of {doc.title} - maybe the page did not exist yet?")
        html = ""

    # MD it, cache it, and return
    text = markdownify(html)
    cache_filename.write_text(text, encoding="utf-8")
    return text
