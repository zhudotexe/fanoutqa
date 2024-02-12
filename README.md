<p align="center">
  <a href="https://fanoutqa.readthedocs.io/en/latest/?badge=latest">
    <img alt="Documentation Status" src="https://readthedocs.org/projects/fanoutqa/badge/?version=latest">
  </a>
  <a href="https://pypi.org/project/fanoutqa/">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/fanoutqa">
  </a>
</p>

# FanOutQA

Read the paper! | [Download the dataset!](/data)

FanOutQA is a high quality, multi-hop, multi-document benchmark for large language models using English Wikipedia as its
knowledge base. Compared to other question-answering benchmarks, FanOutQA requires reasoning over a greater number of
documents, with the benchmark's main focus being on the titular fan-out style of question. We present these questions
in three tasks -- closed-book, open-book, and evidence-provided -- which
measure different abilities of LLM systems.

This repository contains utilities to download and work with the dataset in Python, along with implementations of the
evaluation metrics presented in our paper. Alternatively, you can download the dev and test sets in JSON format and
generate completions to submit to us for evaluation.

## Leaderboards

TODO: move to website

## Requirements and Installation

The `fanoutqa` package requires Python 3.8+.

To work with just the data, use `pip install fanoutqa`.

To run evaluations on the dev set, use `pip install "fanoutqa[eval]"`.

## Data Format

To load the dev or test questions, simply use `fanoutqa.load_dev()` or `fanoutqa.load_test()`. This will return a list
of `DevQuestion` or `TestQuestion`, as documented below.

### Common Models

```python
Primitive = bool | int | float | str


class Evidence:
    pageid: int  # Wikipedia page ID
    revid: int  # Wikipedia revision ID of page as of dataset epoch
    title: str  # Title of page
    url: str  # Link to page
```

### Dev Set

The development set is a JSON file containing a list of DevQuestion objects:

```python
class DevQuestion:
    id: str
    question: str  # the top-level question to answer
    decomposition: list[DevSubquestion]  # human-written decomposition of the question
    answer: dict[str, Primitive] | list[Primitive] | Primitive
    categories: list[str]


class DevSubquestion:
    id: str
    question: str
    decomposition: list[DevSubquestion]
    answer: dict[str, Primitive] | list[Primitive] | Primitive  # the answer to this subquestion
    depends_on: list[str]  # the IDs of subquestions that this subquestion requires answering first
    evidence: Evidence | None  # if this is None, the question will have a decomposition
```

### Test Set

The test set contains a slightly different format, as the answers are not provided. We include links to all the evidence
used in the human-written decompositions for our Evidence Provided task.

```python
class TestQuestion:
    id: str
    question: str
    necessary_evidence: list[FinalEvidence]
    categories: list[str]
```

## Wikipedia Retrieval

TODO

## Evaluation

To evaluate a model's generation, first ensure that you have installed all the evaluation dependencies (see above).

TODO: what env vars?
TODO: what to run?
TODO: what does it return?

### Test Set Evaluation

To evaluate your model on the hidden test set, please email your generations
to [andrz@seas.upenn.edu](mailto:andrz@seas.upenn.edu) with the subject "FanOutQA Test Evaluation". Your generations
should be in the form of a JSONL file, with each line being a JSON object with the following schema for each test
question:

```json
{
  "id": "The ID of the question (see test set schema) this is a generation for.",
  "answer": "The model's generation."
}
```

In the email body, please include details about your system, including at least:
- the name of your system
- the list of authors
- a link to your paper and recommended short citation, if applicable
- whether it is a new foundation model, a fine-tune, a prompting approach, or other

