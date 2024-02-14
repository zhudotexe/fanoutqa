# FanOutQA

![PyPI](https://img.shields.io/pypi/v/fanoutqa)

Read the paper! | [Download the dataset!](https://github.com/zhudotexe/fanoutqa/tree/main/fanoutqa/data)

FanOutQA is a high quality, multi-hop, multi-document benchmark for large language models using English Wikipedia as its
knowledge base. Compared to other question-answering benchmarks, FanOutQA requires reasoning over a greater number of
documents, with the benchmark's main focus being on the titular fan-out style of question. We present these questions
in three tasks -- closed-book, open-book, and evidence-provided -- which measure different abilities of LLM systems.

This repository contains utilities to download and work with the dataset in Python, along with implementations of the
evaluation metrics presented in our paper. Alternatively, you can download the dev and test sets in JSON format and
generate completions to submit to us for evaluation.

To view the leaderboards and more documentation about how to use this dataset, check out our website
at <https://fanoutqa.com>!

## Requirements and Installation

The `fanoutqa` package requires Python 3.8+.

To work with just the data, use `pip install fanoutqa`.
Use `pip install "fanoutqa[all]"` and read the following section to include a baseline retriever and evaluation metrics.

### Optional

To include a baseline BM25-based retriever, use `pip install "fanoutqa[retrieval]"`.

To run evaluations on the dev set, you will need to run a couple more steps:

```shell
pip install "fanoutqa[eval]"
python -m spacy download en_core_web_sm
pip install "bleurt @ git+https://github.com/google-research/bleurt.git@master"
wget https://storage.googleapis.com/bleurt-oss-21/BLEURT-20.zip
unzip BLEURT-20.zip
rm BLEURT-20.zip
```

## Quickstart

1. Use `fanoutqa.load_dev()` or `fanoutqa.load_test()` to load the dataset.
2. Run your generations.
    1. Use `fanoutqa.wiki_search(title)` and `fanoutqa.wiki_content(evidence)` to retrieve the contents of
       Wikipedia pages for the Open Book and Evidence Provided settings.
3. Evaluate your generations with `fanoutqa.eval.evaluate(dev_questions, answers)` (see below for the schema).

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
    necessary_evidence: list[Evidence]
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
    necessary_evidence: list[Evidence]
    categories: list[str]
```

## Wikipedia Retrieval

To retrieve the contents of Wikipedia pages used as evidence, this package queries Wikipedia's Revisions API. There
are two main functions to interface with Wikipedia:

- `wiki_search(query)` returns a list of Evidence (Wikipedia pages that best match the query)
- `wiki_content(evidence)` takes an Evidence and returns its content (as of the dataset epoch) as Markdown.

To save on time waiting for requests and computation power (both locally and on Wikipedia's end), this package
aggressively caches retrieved Wikipedia pages. By default, this cache is located in `~/.cache/fanoutqa/wikicache`.
We provide many cached pages (~9GB) you can prepopulate this cache with, by using the following commands:

```shell
mkdir -p ~/.cache/fanoutqa
wget -O ~/.cache/fanoutqa/wikicache.tar.gz https://datasets.mechanus.zhu.codes/fanoutqa/wikicache.tar.gz 
tar -xzf ~/.cache/fanoutqa/wikicache.tar.gz
```

## Evaluation

To evaluate a model's generation, first ensure that you have installed all the evaluation dependencies (see above).

To use the GPT-as-judge metric, you will need to provide your OpenAI API key. We intentionally do not read
the `OPENAI_API_KEY` environment variable by default to prevent accidentally spending money; you must set the
`FANOUTQA_OPENAI_API_KEY` environment variable instead. You can use `export FANOUTQA_OPENAI_API_KEY=$OPENAI_API_KEY` to
quickly copy it over.

You should record your model/system's outputs as a list of dicts with the following schema:

```json
{
  "id": "The ID of the question (see test set schema) this is a generation for.",
  "answer": "The model's generation."
}
```

Finally, to evaluate your generations on the dev set,
call `fanoutqa.eval.evaluate(dev_questions, answers, llm_cache_key="your-model-key")`. This will run all of the metrics
and return an `EvaluationScore` object, which has attributes matching the following structure:

```json
{
  "acc": {
    "loose": 0,
    "strict": 0
  },
  "rouge": {
    "rouge1": {
      "precision": 0,
      "recall": 0,
      "fscore": 0
    },
    "rouge2": {
      "precision": 0,
      "recall": 0,
      "fscore": 0
    },
    "rougeL": {
      "precision": 0,
      "recall": 0,
      "fscore": 0
    }
  },
  "bleurt": 0,
  "gpt": 0
}
```

(to access this in this dictionary form, use `dataclasses.asdict()`.)

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

## Additional Resources

Although this package queries live Wikipedia and uses the Revisions API to get page content as of the dataset epoch,
we also provide a snapshot of English Wikipedia as of Nov 20, 2023. You can download this
snapshot [here](https://datasets.mechanus.zhu.codes/fanoutqa/enwiki-20231120-pages-articles-multistream.xml.bz2) (23G)
and its
index [here](https://datasets.mechanus.zhu.codes/fanoutqa/enwiki-20231120-pages-articles-multistream-index.txt.bz2).