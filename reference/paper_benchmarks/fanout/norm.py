import logging
import re
from decimal import Decimal

import ftfy
import spacy

log = logging.getLogger(__name__)
nlp = spacy.load("en_core_web_sm")


def normalize(text, remove_stopwords=False):
    """
    - ftfy
    - normalize numbers
    - lemmatize
    - remove stopwords (optional)
    - remove punctuation
    - remove redundant whitespace
    """
    text = str(text).lower()
    text = ftfy.fix_text(text)
    text = normalize_numbers(text)
    text = lemmatize(text, remove_stopwords=remove_stopwords)
    text = remove_punct(text)
    text = normalize_whitespace(text)
    return text


def normalize_numbers(text: str, do_text_sub=False):
    """Use regex to normalize numbers like 5.2 billion, and numbers with commas"""
    # numbers with commas
    comma_sub_text = re.sub(r"(\d+,)+\d+(\.\d+)?", lambda m: m[0].replace(",", ""), text)

    if not do_text_sub:
        return comma_sub_text

    # numbers with text
    def number_text_sub(match: re.Match):
        n = Decimal(match[1])  # for precision
        muls = match[2].strip()
        for mul in muls.split():
            match mul.lower():
                case "thousand":
                    n *= 1_000
                case "million":
                    n *= 1_000_000
                case "billion":
                    n *= 1_000_000_000
                case "trillion":
                    n *= 1_000_000_000_000
        return str(n.normalize())

    textual_number_sub_text = re.sub(
        r"(\d+(?:\.\d+)?)((?:\s*(?:thousand|million|billion|trillion))+)",
        number_text_sub,
        comma_sub_text,
        flags=re.IGNORECASE,
    )

    return textual_number_sub_text


def lemmatize(text: str, remove_stopwords=False):
    """Return a normalized string with each word replaced by its lemmatized version."""
    doc = nlp(text)
    if remove_stopwords:
        return " ".join(tok.lemma_ for tok in doc if not tok.is_stop)
    return " ".join(tok.lemma_ for tok in doc)


def remove_punct(text: str):
    """Remove all punctuation from the string."""
    return re.sub(r"[,.?!:;]", "", text)


def normalize_whitespace(text: str):
    """Replace all whitespace with a single space."""
    return re.sub(r"\s+", " ", text)
