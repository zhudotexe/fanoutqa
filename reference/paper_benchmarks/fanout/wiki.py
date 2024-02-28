"""Utils for working with Wikipedia"""

import datetime
import json
import logging
import re

import mediawiki
from bs4 import BeautifulSoup
from mediawiki import MediaWiki, MediaWikiPage

from fanout.config import CACHE_DIR
from fanout.norm import normalize
from fanout.utils import markdownify

USER_AGENT = "fanoutqa/bench (andrz@seas.upenn.edu) pymediawiki/0.7.4"
DATASET_EPOCH = datetime.datetime(year=2023, month=11, day=20, tzinfo=datetime.timezone.utc)

log = logging.getLogger(__name__)
wikipedia = MediaWiki(user_agent=USER_AGENT)


# ==== classes ====
class DatedPage(MediaWikiPage):
    """To query contents as of the right date, we override some of the request params"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dated_html = False

    def get_dated_html(self):
        """Get the page content as of the dataset epoch."""
        cache_filename = CACHE_DIR / f"{self.pageid}-dated.html"
        if self._dated_html is False:
            if cache_filename.exists():
                self._dated_html = cache_filename.read_text()
            else:
                self._dated_html = ""
                query_params = {
                    "prop": "revisions",
                    "rvprop": "content",
                    "rvlimit": 1,
                    "rvparse": "",
                    "titles": self.title,
                    # added here
                    "rvstart": DATASET_EPOCH.isoformat(),
                }
                request = self.mediawiki.wiki_request(query_params)
                page = request["query"]["pages"][self.pageid]
                try:
                    self._dated_html = page["revisions"][0]["*"]
                except KeyError:
                    log.warning(f"Could not find dated revision of {self.title} - maybe the page did not exist yet?")
                    pass
                cache_filename.write_text(self._dated_html)
        return self._dated_html

    def get_dated_revid(self):
        query_params = {
            "prop": "revisions",
            "rvprop": "ids",
            "rvlimit": 1,
            "rvparse": "",
            "titles": self.title,
            # added here
            "rvstart": DATASET_EPOCH.isoformat(),
        }
        request = self.mediawiki.wiki_request(query_params)
        page = request["query"]["pages"][self.pageid]
        return page["revisions"][0]["revid"]

    def get_backlinks(self):
        """Cached version of page.backlinks"""
        cache_filename = CACHE_DIR / f"{self.pageid}-backlinks.json"
        if cache_filename.exists():
            with open(cache_filename) as f:
                return json.load(f)
        backlinks = self.backlinks
        with open(cache_filename, "w") as f:
            json.dump(backlinks, f)
        return backlinks


class WikiError(Exception):
    pass


# ==== main ====
def get_wikipedia_page_by_id(pageid):
    try:
        return DatedPage(wikipedia, pageid=pageid, redirect=True, preload=False)
    except (mediawiki.PageError, mediawiki.DisambiguationError) as e:
        log.exception("Got PageError:")
        raise WikiError(repr(e)) from e


def get_page_all_text(pageid: int, norm=True, remove_citations_and_notes=False) -> str:
    """
    Render the page HTML **as of the dataset epoch** and retrieve all visible text (including tables and infoboxes),
    without markup.
    """
    if norm:
        cache_filename = CACHE_DIR / f"{pageid}-dated-norm.txt"
    else:
        cache_filename = CACHE_DIR / f"{pageid}-dated.txt"

    if cache_filename.exists():
        text = cache_filename.read_text()
    else:
        page = get_wikipedia_page_by_id(pageid)
        html = page.get_dated_html()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        if norm:
            text = normalize(text)
        cache_filename.write_text(text)

    if remove_citations_and_notes:
        text = re.sub(r"\s\[ (((note\s+)?\d+)|edit) ]\s", " ", text)
    return text


def get_page_markdown(pageid: int):
    """Get the page content in markdown, including tables and infoboxes, appropriate for displaying to an LLM"""
    cache_filename = CACHE_DIR / f"{pageid}-dated.md"

    if cache_filename.exists():
        return cache_filename.read_text()

    page = get_wikipedia_page_by_id(pageid)
    html = page.get_dated_html()
    text = markdownify(html)
    cache_filename.write_text(text)
    return text
