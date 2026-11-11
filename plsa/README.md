# Modeling Beyond Keywords: Probabilistic Latent Semantic Analysis (PLSA)

**Group 12 | Information Retrieval | BITS Pilani**

This repository contains our course project on implementing
**Probabilistic Latent Semantic Analysis (PLSA)** and studying its use
in document retrieval. We compare PLSA-based retrieval with **TF-IDF /
Vector Space Model (VSM)** and **Latent Semantic Indexing (LSI)** using
the 20 Newsgroups dataset.

The project looks at two related questions: how well can PLSA discover
latent topics in a collection of documents, and how useful are those
topics when retrieving documents for different kinds of queries?

> **Project note:** Results vary across the full 20-category corpus and
> the smaller six-category experiment. The README describes the
> experiments and evaluation approach; use the latest notebook outputs
> for any reported numerical results.

## Table of Contents

-   [Project Motivation](#project-motivation)
-   [Project Goals](#project-goals)
-   [Dataset](#dataset)
-   [Text Preprocessing](#text-preprocessing)
-   [PLSA Model](#plsa-model)
-   [Training with EM](#training-with-em)
-   [Document Retrieval Methods](#document-retrieval-methods)
-   [Query Design and Evaluation](#query-design-and-evaluation)
-   [Topic-Mixture Experiment](#topic-mixture-experiment)
-   [Model-Order Study](#model-order-study)
-   [Runtime and Memory Profiling](#runtime-and-memory-profiling)
-   [Metrics](#metrics)
-   [Experimental Design and
    Reproducibility](#experimental-design-and-reproducibility)
-   [Repository Structure](#repository-structure)
-   [Installation and Setup](#installation-and-setup)
-   [Running the Notebooks](#running-the-notebooks)
-   [How to Interpret the Results](#how-to-interpret-the-results)
-   [Limitations](#limitations)
-   [Team](#team)
-   [Reference](#reference)

## Project Motivation

Traditional keyword-based retrieval methods work well when the words in
a query closely match the words used in relevant documents. However, a
relevant document may discuss the same idea using different terminology.
This project explores whether latent topic representations can provide a
useful alternative or complement to direct word matching.

PLSA is a probabilistic topic model. It represents each document as a
mixture of topics and each topic as a probability distribution over
words. We use this representation to investigate topic structure and to
retrieve documents for queries.

The project does not assume that PLSA must outperform conventional
methods. Instead, we compare the methods experimentally and examine
where their strengths and weaknesses appear.

## Project Goals

The main goals are to:

1.  Implement PLSA using the Expectation--Maximization (EM) algorithm.
2.  Learn document-topic and topic-word probability distributions from
    document word counts.
3.  Inspect the most representative words associated with learned
    topics.
4.  Compare PLSA retrieval with TF-IDF and LSI.
5.  Evaluate different query styles: direct keywords, paraphrases, and
    related domain terms.
6.  Study how changing the number of latent topics, `K`, affects
    training and topic separation.
7.  Create synthetic documents from two source categories and examine
    the topic mixtures inferred by PLSA.
8.  Measure the runtime and memory used during model training and
    inference.

## Dataset

The experiments use the **20 Newsgroups** text dataset, available
through sklearn.datasets.fetch_20newsgroups(subset="all")

Two corpus settings are explored:

### Full 20-category corpus

The baseline experiment uses the original newsgroup categories. This
setting includes a broad range of subjects, some of which are closely
related. It provides a more challenging test of whether PLSA can learn
useful topic representations across a diverse collection.

### Six-category subset

A separate experiment retains six categories with more distinct subject
matter, including:

-   `comp.graphics`
-   `misc.forsale`
-   `rec.sport.baseball`
-   `sci.med`
-   `sci.space`
-   `talk.politics.guns`

The purpose of this smaller experiment is to investigate topic discovery
and query-based retrieval in a corpus where the selected categories are
easier to distinguish. This is a diagnostic setup, not evidence that six
is the ideal number of topics.

**Important distinction:** the number of dataset categories and the
number of latent PLSA topics (`K`) are different. PLSA may split a
category across topics or learn a topic that contains words from
multiple categories.

## Text Preprocessing

Text is cleaned and converted into numerical word-count representations
before fitting PLSA.

The preprocessing pipeline includes:

1.  **Text cleanup:** dataset headers, footers, and quoted text are
    removed where configured.
2.  **Tokenization and normalization:** spaCy processes each document.
3.  **Filtering:** spaces, punctuation, numbers, non-alphabetic tokens,
    and stop words are removed.
4.  **Lemmatization:** words are converted to their base forms; for
    example, related inflected forms can share one representation.
5.  **Vocabulary construction:** `CountVectorizer` builds the vocabulary
    from training documents only, with settings such as
    `max_features=3000`, `min_df=3`, and `max_df=0.90` in the
    six-category validation experiment.
6.  **Document-term matrix:** each document is represented by word
    counts over the selected vocabulary.

In the validation-based six-category experiment, the data is split into
**60% training, 20% validation, and 20% test** sets using stratification
to preserve category proportions. The vocabulary and models are fitted
using training data, validation data is used to choose settings and the
held-out test set is reserved for final evaluation.

Splits differ by study; vectorizer settings and preprocessing implementations are shared.
Comparisons should therefore be made within the same experiment setup
rather than by directly combining results from different notebooks.

## PLSA Model

PLSA explains the words in a document through a mixture of latent topics.
For document $d$, word $w$, and topic $z$:

$$
P(w \mid d) = \sum_{z=1}^{K} P(w \mid z)P(z \mid d)
$$
The model learns two distributions:

-   **Document-topic distribution**, `P(z | d)`: how strongly each topic
    is associated with a document.
-   **Topic-word distribution**, `P(w | z)`: how strongly each word is
    associated with a topic.

Each distribution is probabilistic, so its values are non-negative and
normalized to sum to one along the appropriate dimension.

The model is unsupervised. It learns these distributions from word
counts without using the category labels as training targets.

## Training with EM

PLSA is trained using the **Expectation--Maximization (EM)** algorithm.

### E-step

For each observed document-word pair, the model estimates the
responsibility of each topic: the probability that a topic accounts for
that word in that document.

### M-step

The model uses the expected topic assignments and observed word counts
to update the document-topic and topic-word distributions.

These steps repeat until the improvement in training log-likelihood
becomes smaller than the chosen tolerance or the maximum number of
iterations is reached.

Because the result can depend on initialization, the experiments may fit
several initializations and compare their training log-likelihoods. The
highest training likelihood indicates the best fit among those runs on
the training data; it does **not** guarantee the best held-out retrieval
performance.

## Document Retrieval Methods

The project compares three main approaches.

### 1. TF-IDF / Vector Space Model

TF-IDF assigns higher weight to words that are informative for a
document and lower weight to words that occur frequently across the
collection. Documents and queries are represented as weighted vectors,
and similarity scores are used to rank candidate documents.

This method is a useful lexical baseline, especially when query words
overlap with relevant document words.

### 2. Latent Semantic Indexing (LSI)

LSI applies truncated Singular Value Decomposition (SVD) to a TF-IDF
matrix to obtain a lower-dimensional representation. Documents and
queries can then be compared in this reduced space.

LSI uses a geometric low-rank representation rather than PLSA's
normalized probability distributions.

### 3. PLSA-based retrieval

PLSA represents documents through their inferred topic mixtures. The
experiments explore two scoring approaches:

-   **Cosine similarity:** compares topic-space representations using
    cosine similarity.
-   **Query likelihood:** scores documents according to how likely the
    query is under the document's topic representation, with background
    smoothing where configured.

Where a PLSA + TF-IDF hybrid is included, it is reported as a separate
method. Hybrid results should not be described as results from pure
PLSA.

## Query Design and Evaluation

The six-category validation study uses a fixed set of queries, with
three query styles for each category:

-   **Direct keywords:** terms closely associated with the target
    category.
-   **Paraphrases:** a different wording of the same general information
    need.
-   **Related terms:** domain vocabulary that may be associated with the
    target category without repeating the exact query wording.

This setup helps examine whether retrieval performance changes with
query wording.

The query vocabulary analysis checks which preprocessed query terms
occur in the vocabulary built from training documents. It records
vocabulary coverage and out-of-vocabulary terms. Per-query evaluation
then connects that coverage with retrieval metrics, helping identify
cases where missing vocabulary may affect retrieval.

For validation-based model selection, the validation set is used to
select settings such as PLSA topic count and query-likelihood background
smoothing. After the settings are fixed, the final comparison is
performed on held-out test documents.

The same queries, candidate documents, and relevance labels should be
used for all methods within a given experiment.

## Topic-Mixture Experiment

To study how PLSA represents documents that combine subjects, the
experiment creates artificial documents by sampling word tokens from
source documents in two categories:

-   `rec.sport.baseball`
-   `talk.politics.guns`

The source-word ratio is varied, and PLSA's folding-in procedure
estimates the topic mixture for each artificial document. The inferred
probabilities are compared with the known source-word proportions.

The experiment identifies baseball-associated and politics-associated
topics by examining the average topic distributions of training
documents from those source categories.

**Interpretation caution:** the source-word ratio is not expected to
match the inferred topic probability exactly. A learned topic may cover
only part of a category, or may contain words associated with both
categories. The experiment checks whether a mixture signal appears; it
does not establish perfect recovery of the original proportions.

## Model-Order Study

The model-order study compares different values of `K`, the number of
latent topics. It records training log-likelihood and the number of
iterations needed for convergence, and allows inspection of how the
learned topics change as `K` varies.

A larger `K` does not necessarily produce more meaningful topics or
better retrieval. Training likelihood is useful for studying model fit
and convergence, but retrieval quality must be assessed separately on
held-out documents.

The six dataset categories do not require `K=6`; category count and
latent topic count are separate choices.

## Runtime and Memory Profiling

The project includes resource profiling to measure the computational
cost of PLSA.

### Training profiling

The training profile records measurements for a PLSA fit, including
runtime and memory use, along with the configured topic count, number of
iterations completed, and final training log-likelihood.

### Inference profiling

The inference profile measures the resources required to infer topic
mixtures for held-out test documents using both the cosine-based and
query-likelihood PLSA models. It records runtime and memory measurements
for the inference operation.

These measurements help compare the cost of training and applying the
model. They depend on the hardware, Python environment, dataset size,
and model configuration, so reported values should include the settings
under which they were measured.

## Metrics

The project uses ranking metrics to compare retrieval methods.

  Metric                              Meaning
  -----------------------------------------------------------------------
  **Precision@10**                    Of the top 10 retrieved documents,
                                      how many are relevant?

  **Recall@10**                       Of all relevant documents in the
                                      evaluated collection, how many
                                      appear in the top 10?

  **AP@10**                           Rewards ranking relevant documents
                                      near the top for one query.

  **MAP@10**                          Average AP@10 across the query set.

  **MRR**                             Measures how high the first
                                      relevant result appears.

  **NDCG@10**                         Measures ranking quality while
                                      giving more importance to
                                      higher-ranked results.


In these experiments, relevance is generally determined from category
labels. A retrieved document is treated as relevant when its category
matches the target category for the query. These labels provide a
convenient and consistent proxy, but they are not the same as human
judgments of whether a document truly answers a query.

Metric values should only be compared directly when the corpus, split,
query set, candidate pool, relevance definition, and metric
implementation are consistent.

## Experimental Design and Reproducibility

For a fair comparison:

-   Fit the vocabulary and retrieval models using training documents
    only.
-   Use validation data for hyperparameter selection when a validation
    split is available.
-   Keep the held-out test set separate until the final evaluation.
-   Use the same queries, relevance labels, and candidate documents for
    methods being compared.
-   Set and report random seeds for experiments that involve random
    initialization or sampling.
-   Record the topic count, iteration settings, preprocessing
    configuration, and scoring method alongside results.
-   Keep results from the full 20-category and six-category experiments
    clearly separated.

No single method is assumed to be best in advance. The conclusions
should follow from the measured results for each experimental setup.

## Repository Structure

All six notebooks import the **same PLSA implementation** from `src/plsa_model.py`.
They create separate fitted instances for different K values, seeds and bootstrap
samples. Dataset, preprocessing and metric implementations are shared too;
experimental choices remain explicit in each notebook and `src/config.py`.

```text
Result.py                 # Run experiments or build the combined results report
src/
  config.py               # Corpus profiles, queries and vectorizer settings
  dataset.py              # One 20 Newsgroups loader and supergroup mapping
  preprocessing.py        # Cached spaCy pipeline, splits and training vocabulary
  plsa_model.py           # Single PLSA EM, fold-in and restart implementation
  retrieval.py            # TF-IDF/LSI fitting and query-likelihood scoring
  metrics.py              # Precision, recall, F1, AP, NDCG and reciprocal rank
  experiments.py          # Synthetic mixtures and ensemble rank aggregation
  profiling.py            # Runtime and sampled process memory
  results.py              # CSV export, provenance and report generation
*.ipynb                   # Study-specific orchestration, plots and explanation
requirements.txt          # Runtime dependencies
requirements-dev.txt      # Test dependencies
tests/                   # Numerical and notebook integration checks
```

| Notebook | Corpus / relevance | Train / validation / test |
| --- | --- | --- |
| `PLSA_Baseline.ipynb` | All 20 categories | 75 / 0 / 25 |
| `PLSA_Retrieval_Scoring_Investigation.ipynb` | Six original categories | 75 / 0 / 25 |
| `Six_Category_Experiment.ipynb` | All 20 categories mapped to six supergroups | 80 / 0 / 20 |
| `Bagging_Experiment.ipynb` | Same six supergroups | 80 / 0 / 20 |
| `Retrieval_Validation_Query_Study.ipynb` | Six original categories | 60 / 20 / 20 |
| `All20_K_Study.ipynb` | All 20 categories | 60 / 20 / 20 |

The legacy `Six_Category_Experiment` filename refers to **six supergroups**,
not the smaller six-category corpus. Compare methods within each study; scores
from different evaluation settings are not a common leaderboard.

## Installation and Setup

Use Python 3.10 or newer. In this repository, first run `cd plsa`; run all
commands and open notebooks from that directory:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

The first dataset load may download 20 Newsgroups through scikit-learn; its
cache lives in `.cache/sklearn/`. All notebooks remove headers, footers and
quoted text through the same loader. The raw `20news-bydate/` folder from the
original repository is not required or included here; scikit-learn downloads
and caches the dataset when needed.

To open notebooks interactively, install JupyterLab (`pip install jupyterlab`)
and launch it from this directory. In Colab, clone the entire repository,
change into its directory, and install these same requirements; uploading a
notebook alone is insufficient because it imports `src`.

## Running the Notebooks

Run any notebook's cells in order through the final export cell. Its result
folder contains CSV tables and `manifest.json` with split sizes, settings,
package versions and source hashes. Old execution outputs were cleared during
the shared-code refactor; explicitly marked historical interpretations need
verification against a new run.

Use the requested **`Result.py`** file for a single entry point:

```bash
python Result.py --run all
# Or execute just one experiment:
python Result.py --run PLSA_Baseline
# Rebuild the report from completed runs without retraining:
python Result.py
```

`results/Result.md` explains the entire workflow and displays each study's
retrieval summary, with links to all its exported tables (per-query retrieval,
K/beta studies, mixtures, convergence, topic words, coverage, and resource
measurements where that notebook produces them). `results/summary.csv` collects
the summaries with an experiment column. Executed notebooks are saved in
`results/executed_notebooks/` when launched through `Result.py`.

Missing studies are marked **not run yet**; scores are never hard-coded. Source
hashes flag when the current code differs from an exported run. Every successful
run gets a unique directory; `latest.json` points to the most recent completed
export. Full execution fits many models and can require substantial time and
memory. `--timeout` controls the per-cell time limit (default: 7200 seconds).

AP is a per-query metric; its average across queries is MAP. Some legacy
supergroup detail tables label per-query AP as `MAP@10`; `Result.py` reports the
macro average correctly. The original `MRR` column is truncated at 10 and is
labeled `MRR@10` in the combined report. Ties retain the original NumPy argsort
ordering. Candidate eligibility and smoothing floors retain each study's
original choices; filtering an empty processed text differs from filtering a
zero vector after vocabulary selection.

### Verification

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m tests.smoke_notebooks
```

The integration check executes every code cell using the real loader and spaCy
pipeline, sampled to 15 documents per original category and at most three EM
iterations per fit/fold-in. It writes separately to `results-smoke/` and marks
outputs **smoke**. These numbers verify wiring, not retrieval performance; full
research scores require running the original budgets with `Result.py --run all`.

## How to Interpret the Results

-   **PLSA topics are not category labels.** A topic can contain words
    from several categories, and a category can be represented by
    several topics.
-   **Training fit and retrieval are different.** A higher training
    log-likelihood does not guarantee better ranking on unseen
    documents.
-   **Query wording matters.** Direct keywords, paraphrases, and related
    terms can produce different retrieval outcomes.
-   **Vocabulary coverage matters.** Query terms absent from the
    training vocabulary cannot contribute to retrieval in the same way
    as known terms.
-   **Methods have different strengths.** TF-IDF can be effective for
    exact lexical overlap; LSI and PLSA use different kinds of
    lower-dimensional representations.
-   **Resource measurements are contextual.** Runtime and memory numbers
    should be interpreted alongside the model configuration and machine
    used.
-   **Use measured evidence.** Avoid general claims that one method is
    always superior; report what happens in each tested setting.

## Limitations

1.  The scoring and validation studies use a six-category subset, so
    their findings may not generalize to all 20 categories. The six-supergroup
    and bagging studies retain all 20 original categories.
2.  PLSA learns topics without category labels, and the learned topics
    may not correspond exactly to the dataset categories.
3.  The query set is limited, and category membership is only an
    approximate measure of query relevance.
4.  In the synthetic mixture experiment, source-word proportions are not
    guaranteed to equal the topic probabilities inferred by PLSA.
5.  Selecting a model using training log-likelihood alone does not
    guarantee the best retrieval performance.
6.  Runtime and memory measurements depend on the execution environment
    and model settings.
7.  More queries and human-judged relevance labels would provide a
    stronger evaluation of retrieval quality.

## Team

**Group 12 --- Information Retrieval**

1. Nookala Gayathri Sreeja (2025H1030232P)
2. Shubhangi Tyagi (2025H1030059P)
3. Khush Siddharth Bothra (2026H1120139P)
4. Animesh Singh (2026H1120144P)


## Reference

Thomas Hofmann. "Probabilistic Latent Semantic Analysis." *Proceedings
of the Fifteenth Conference on Uncertainty in Artificial Intelligence
(UAI)*, 1999.


**Course project:** Information Retrieval\
**Project title:** Modeling Beyond Keywords: Probabilistic Latent
Semantic Analysis (PLSA)\
**Group:** 12\
**Repository URL:** https://github.com/Animesh2609/Tendering

**Source project:** https://github.com/Animesh2609/Probablisitic-Latent-Semantic-Analysis
