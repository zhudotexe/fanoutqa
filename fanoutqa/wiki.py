"""Utils for working with Wikipedia"""

import functools
import logging
import os
import urllib.parse
from xml.etree import ElementTree

import httpx
import pywikibot

from .models import Evidence
from .utils import CACHE_DIR, DATASET_EPOCH, markdownify

WIKI_CACHE_DIR = CACHE_DIR / "wikicache"
WIKI_CACHE_DIR.mkdir(exist_ok=True, parents=True)
PWB_CACHE_DIR = CACHE_DIR / "pywikibot"
pywikibot.config.base_dir = str(PWB_CACHE_DIR.resolve())
KIWIX_CACHE_DIR = CACHE_DIR / "kiwix"

FANOUTQA_WIKIPEDIA_TYPE = os.getenv("FANOUTQA_WIKIPEDIA_TYPE")
FANOUTQA_KIWIX_BASE = os.getenv("FANOUTQA_KIWIX_BASE")
FANOUTQA_KIWIX_ZIMNAME = os.getenv("FANOUTQA_KIWIX_ZIMNAME")

log = logging.getLogger(__name__)
_site = pywikibot.Site("en", "wikipedia")


# ==== impl ====
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


def _wiki_search_live(query: str, results=10) -> list[Evidence]:
    """Return a list of Evidence documents given the search query."""
    # get the list of articles that match the query
    # and return a LazyEvidence for each
    return [LazyEvidence(title=page.title(), pageid=page.pageid) for page in _site.search(query, total=results)]


def _wiki_content_live(doc: Evidence):
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


def _wiki_search_kiwix(query: str, results: int = 10) -> list[Evidence]:
    params = urllib.urlencode(
        {"pattern": query, "start": 0, "pageLength": results, "books.name": FANOUTQA_KIWIX_ZIMNAME}
    )
    resp = httpx.get(f"{FANOUTQA_KIWIX_BASE}/search?{params}")
    resp.raise_for_status()
    resp.read()
    text = resp.text

    # Kiwix returns an OpenSearch Atom feed
    root = ElementTree.fromstring(text)
    # Handle feeds with or without the Atom namespace
    ns_prefix = ""
    if root.tag.startswith("{"):
        ns_uri = root.tag[1 : root.tag.index("}")]
        ns_prefix = f"{{{ns_uri}}}"

    entries = []
    for entry in root.findall(f"{ns_prefix}entry"):
        title_el = entry.find(f"{ns_prefix}title")
        link_el = entry.find(f"{ns_prefix}link")
        if title_el is None or link_el is None:
            continue
        title = title_el.text or ""
        href = link_el.get("href", "")
        entries.append(Evidence(pageid=0, revid=0, title=title, url=href))
    return entries


def _wiki_content_kiwix(doc: Evidence) -> str:
    """Get the page content in markdown, including tables and infoboxes, appropriate for displaying to an LLM."""
    # Use the href as the cache key (strip leading slash, replace slashes with dashes)
    cache_name = doc.url.lstrip("/").replace("/", "-")
    cache_filename = KIWIX_CACHE_DIR / f"{cache_name}.md"
    if cache_filename.exists():
        try:
            return cache_filename.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            pass

    resp = httpx.get(f"{FANOUTQA_KIWIX_BASE}{doc.url}")
    if resp.status_code == 404:
        return "This page does not exist."
    resp.raise_for_status()
    resp.read()

    text = markdownify(resp.text)
    cache_filename.write_text(text, encoding="utf-8")
    return text


# ==== entrypoint ====
@functools.lru_cache()
def wiki_search(query: str, results=10) -> list[Evidence]:
    """Return a list of Evidence documents given the search query."""
    if FANOUTQA_WIKIPEDIA_TYPE == "kiwix":
        return _wiki_search_kiwix(query, results)
    return _wiki_search_live(query, results)


def wiki_content(doc: Evidence) -> str:
    """Get the page content in markdown, including tables and infoboxes, appropriate for displaying to an LLM."""
    if FANOUTQA_WIKIPEDIA_TYPE == "kiwix":
        return _wiki_content_kiwix(doc)
    return _wiki_content_live(doc)
