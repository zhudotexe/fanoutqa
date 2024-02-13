from dataclasses import dataclass
from typing import Optional, Union

Primitive = Union[bool, int, float, str]
AnswerType = Union[dict[str, Primitive], list[Primitive], Primitive]


@dataclass
class Evidence:
    """A reference to a Wikipedia article at a given point in time."""

    pageid: int
    """Wikipedia page ID."""

    revid: int
    """Wikipedia revision ID of page as of dataset epoch. Often referred to as ``oldid`` in Wikipedia API docs."""

    title: str
    """Title of page."""

    url: str
    """Link to page."""

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class DevSubquestion:
    """A human-written decomposition of a top-level question."""

    id: str
    """The ID of the question."""
    question: str
    """The question for the system to answer."""
    decomposition: list["DevSubquestion"]
    """A human-written decomposition of the question."""
    answer: AnswerType
    """The human-written reference answer to this subquestion."""
    depends_on: list[str]
    """The IDs of subquestions that this subquestion requires answering first."""
    evidence: Optional[Evidence]
    """The Wikipedia page used by the human annotator to answer this question.
    If this is None, the question will have a decomposition."""

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
    """The ID of the question."""
    question: str
    """The top-level question for the system to answer."""
    decomposition: list[DevSubquestion]
    """A human-written decomposition of the question."""
    answer: AnswerType
    """A human-written reference answer to the question."""
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

    @property
    def necessary_evidence(self) -> list[Evidence]:
        """A list of all the evidence used by human annotators to answer the question."""

        def walk_evidences(subqs):
            for subq in subqs:
                if subq.evidence:
                    yield subq.evidence
                yield from walk_evidences(subq.decomposition)

        return list(walk_evidences(self.decomposition))


@dataclass
class TestQuestion:
    """A top-level question in the FOQA dataset, without its decomposition or answer."""

    id: str
    """The ID of the question."""
    question: str
    """The top-level question for the system to answer."""
    necessary_evidence: list[Evidence]
    """A list of all the evidence used by human annotators to answer the question."""
    categories: list[str]

    @classmethod
    def from_dict(cls, d):
        evidence = [Evidence.from_dict(e) for e in d["necessary_evidence"]]
        return cls(
            id=d["id"],
            question=d["question"],
            necessary_evidence=evidence,
            categories=d["categories"],
        )
