from dataclasses import dataclass
from typing import Optional, Union

Primitive = Union[bool, int, float, str]


@dataclass
class Evidence:
    """A reference to a Wikipedia article at a given point in time."""

    pageid: int
    """Wikipedia page ID"""

    revid: int
    """Wikipedia revision ID of page as of dataset epoch"""

    title: str
    """Title of page"""

    url: str
    """Link to page"""

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class DevSubquestion:
    """A human-written decomposition of a top-level question."""

    id: str
    question: str
    decomposition: list["DevSubquestion"]
    answer: Union[dict[str, Primitive], list[Primitive], Primitive]
    """the answer to this subquestion"""

    depends_on: list[str]
    """the IDs of subquestions that this subquestion requires answering first"""

    evidence: Optional[Evidence]
    """if this is None, the question will have a decomposition"""

    @classmethod
    def from_dict(cls, d):
        decomposition = [DevSubquestion.from_dict(dc) for dc in d["decomposition"]]
        evidence = None if d["evidence"] is None else Evidence.from_dict(d["evidence"])
        return cls(
            id=d["id"],
            question=d["question"],
            decomposition=decomposition,
            answer=d["answer"],
            depends_on=d["depends_on"],
            evidence=evidence,
        )


@dataclass
class DevQuestion:
    """A top-level question in the FOQA dataset and its decomposition."""

    id: str
    question: str
    """the top-level question to answer"""
    decomposition: list[DevSubquestion]
    """human-written decomposition of the question"""
    answer: Union[dict[str, Primitive], list[Primitive], Primitive]
    categories: list[str]

    @classmethod
    def from_dict(cls, d):
        decomposition = [DevSubquestion.from_dict(dc) for dc in d["decomposition"]]
        return cls(
            id=d["id"],
            question=d["question"],
            decomposition=decomposition,
            answer=d["answer"],
            categories=d["categories"],
        )


@dataclass
class TestQuestion:
    """A top-level question in the FOQA dataset, without its decomposition or answer."""

    id: str
    question: str
    necessary_evidence: list[Evidence]
    categories: list[str]

    @classmethod
    def from_dict(cls, d):
        evidence = [Evidence.from_dict(e) for e in d["evidence"]]
        return cls(
            id=d["id"],
            question=d["question"],
            necessary_evidence=evidence,
            categories=d["categories"],
        )
