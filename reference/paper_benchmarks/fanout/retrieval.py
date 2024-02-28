from collections import namedtuple
from typing import Iterable

import numpy as np
from rank_bm25 import BM25Plus

from fanout.norm import normalize
from fanout.wiki import get_page_markdown

RetrievalResult = namedtuple("RetrievalResult", "title content")


class Corpus:
    """A corpus of wiki docs. Indexes the docs on creation, normalizing the text beforehand with lemmatization."""

    def __init__(self, documents: list[dict], doc_len: int):
        """
        :param documents: The list of evidences to index
        :param doc_len: The maximum length, in characters, of each chunk
        """
        self.documents = []
        normalized_corpus = []
        for doc in documents:
            title = doc["title"]
            content = get_page_markdown(doc["pageid"])
            for chunk in chunk_text(content, max_chunk_size=doc_len):
                self.documents.append(RetrievalResult(title, chunk))
                normalized_corpus.append(self.tokenize(chunk))

        self.index = BM25Plus(normalized_corpus)

    def tokenize(self, text: str):
        """Split the text into words, lemmatize, remove stopwords."""
        return normalize(text).split(" ")

    def best(self, q) -> Iterable[RetrievalResult]:
        """Yield the best matching fragments to the given query."""
        tok_q = self.tokenize(q)
        scores = self.index.get_scores(tok_q)
        idxs = np.argsort(scores)[::-1]
        for idx in idxs:
            yield self.documents[idx]


def chunk_text(text, max_chunk_size=1024, chunk_on=("\n\n", "\n", ". ", ", ", " "), chunker_i=0):
    """
    Recursively chunks *text* into a list of str, with each element no longer than *max_chunk_size*.
    Prefers splitting on the elements of *chunk_on*, in order.
    """

    if len(text) <= max_chunk_size:  # the chunk is small enough
        return [text]
    if chunker_i >= len(chunk_on):  # we have no more preferred chunk_on characters
        # optimization: instead of merging a thousand characters, just use list slicing
        return [text[:max_chunk_size], *chunk_text(text[max_chunk_size:], max_chunk_size, chunk_on, chunker_i + 1)]

    # split on the current character
    chunks = []
    split_char = chunk_on[chunker_i]
    for chunk in text.split(split_char):
        chunk = f"{chunk}{split_char}"
        if len(chunk) > max_chunk_size:  # this chunk needs to be split more, recurse
            chunks.extend(chunk_text(chunk, max_chunk_size, chunk_on, chunker_i + 1))
        elif chunks and len(chunk) + len(chunks[-1]) <= max_chunk_size:  # this chunk can be merged
            chunks[-1] += chunk
        else:
            chunks.append(chunk)

    # if the last chunk is just the split_char, yeet it
    if chunks[-1] == split_char:
        chunks.pop()

    # remove extra split_char from last chunk
    chunks[-1] = chunks[-1][: -len(split_char)]
    return chunks
