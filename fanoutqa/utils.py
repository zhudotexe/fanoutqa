import datetime
import json
import os
from itertools import islice
from pathlib import Path
from typing import TypeAlias, Union

from markdownify import MarkdownConverter

from .models import DevQuestion, TestQuestion

AnyPath: TypeAlias = Union[str, bytes, os.PathLike]
PKG_ROOT = Path(__file__).parent
CACHE_DIR = Path("~/.cache/fanoutqa")
CACHE_DIR.mkdir(exist_ok=True, parents=True)
DATASET_EPOCH = datetime.datetime(year=2023, month=11, day=20, tzinfo=datetime.timezone.utc)
"""The day before which to get revisions from Wikipedia, to ensure that the contents of pages don't change over time."""


def load_dev(fp: AnyPath = None) -> list[DevQuestion]:
    """Load all questions from the development set.

    :param fp: The path to load the questions from (defaults to bundled FOQA).
    """
    if fp is None:
        fp = PKG_ROOT / "data/fanout-final-dev.json"

    with open(fp) as f:
        data = json.load(f)
    return [DevQuestion.from_dict(d) for d in data]


def load_test(fp: AnyPath = None) -> list[TestQuestion]:
    """Load all questions from the test set.

    :param fp: The path to load the questions from (defaults to bundled FOQA).
    """
    if fp is None:
        fp = PKG_ROOT / "data/fanout-final-test.json"

    with open(fp) as f:
        data = json.load(f)
    return [TestQuestion.from_dict(d) for d in data]


def batched(iterable, n):
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


# markdown
# We make some minor adjustments to markdownify's default style to make it look a little bit nicer
def discard(*_):
    return ""


class MDConverter(MarkdownConverter):
    def convert_img(self, el, text, convert_as_inline):
        alt = el.attrs.get("alt", None) or ""
        return f"![{alt}](image)"

    def convert_a(self, el, text, convert_as_inline):
        return text

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def convert_div(self, el, text, convert_as_inline):
        content = text.strip()
        if not content:
            return ""
        return f"{content}\n"

    # sometimes these appear inline and are just annoying
    convert_script = discard
    convert_style = discard


def markdownify(html: str):
    return MDConverter(heading_style="atx").convert(html)
