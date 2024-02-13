import json
import os
from pathlib import Path
from typing import TypeAlias, Union

from .models import DevQuestion, TestQuestion

AnyPath: TypeAlias = Union[str, bytes, os.PathLike]
PKG_ROOT = Path(__file__).parent


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
