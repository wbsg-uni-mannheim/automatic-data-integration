# Pipeline

The `PyDI.pipeline` module automates the complete data integration workflow. It chains together schema matching, normalization, entity resolution (blocking + matching), and data fusion into a single configurable pipeline.

## Table of Contents

- [Pipeline Overview](#pipeline-overview)
- [Step 1: Schema Matching](#step-1-schema-matching)
- [Step 2: Normalization](#step-2-normalization)
- [Step 3: Entity Resolution](#step-3-entity-resolution)
  - [Blocking](#blocking)
  - [Matching](#matching)
- [Step 4: Data Fusion](#step-4-data-fusion)
- [Optimization Strategy](#optimization-strategy)


## Pipeline Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Schema Matching │ -> │  Normalization  │ -> │Entity Resolution│ -> │   Data Fusion   │
│   (LLM-based)   │    │  (type-aware)   │    │ Blocking+Matching│   │(conflict resolve)│
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Input:** Multiple source datasets (CSV, XML) + target schema (JSON Schema)

**Output:** Single fused dataset with resolved entities and conflicts


## Step 1: Schema Matching

Maps source columns to target schema columns using LLM.

```python
from PyDI.pipeline import auto_match_schema

mapping = auto_match_schema(
    source_df=df,
    target_schema=target_schema,
    chat_model=llm,
    num_rows=30  # sample rows shown to LLM
)
```

**What happens:**
1. LLM receives source column names + sample values + target schema properties
2. LLM returns source → target column mappings
3. Mappings cached to `{output_dir}/mappings/{name}_mapping.csv`


## Step 2: Normalization

Translates source data to match target schema types and formats.

```python
from PyDI.pipeline import auto_normalize

normalized_df, stats = auto_normalize(
    source_df=df,
    mapping=mapping,
    target_schema=target_schema,
    on_failure="keep"  # or "null" or "raise"
)
```

**What happens:**
1. Applies column renaming from schema mapping
2. Converts data types (string → date, string → number, etc.)
3. Validates against JSON Schema constraints


## Step 3: Entity Resolution

Identifies records across datasets that describe the same real-world entity. Split into two phases: blocking and matching.

### Blocking

Blocking reduces the O(n×m) comparison space by generating candidate pairs.

#### Default Blockers

| Blocker | Description | Parameters |
|---------|-------------|------------|
| **TokenBlocker (default)** | Pairs records sharing tokens (words) | `min_token_len=3`, `min_overlap=2` |
| **TokenBlocker (5-gram)** | Pairs records sharing character 5-grams | `ngram_size=5`, `ngram_type="character"` |
| **SortedNeighbourhoodBlocker** | Pairs nearby records in sorted order | `window=3` or `window=5` |
| **EmbeddingBlocker** | Pairs semantically similar records | `threshold`, `top_k=30` |

#### TokenBlocker

Tokenizes text into words and pairs records with shared tokens.

```
Record A: "The Dark Knight" → tokens: ["the", "dark", "knight"]
Record B: "Dark Knight Rises" → tokens: ["dark", "knight", "rises"]
Shared tokens: ["dark", "knight"] → candidate pair (if min_overlap=2 is met)
```

Default settings:
- `min_token_len=3`: Ignores short tokens like "a", "of", "the"
- `min_overlap=2`: Requires at least 2 shared tokens (filters stopword-only matches)

#### SortedNeighbourhoodBlocker

Sorts all records by a key column, then pairs records within a sliding window.

```
Sorted: [A, B, C, D, E, F, G]
         └──┬──┘
         window=3: pairs within {A, B, C}
            └──┬──┘
            window=3: pairs within {B, C, D}
               └──┬──┘
               ...
```

Good for catching typos and small variations where sort order is preserved.

#### EmbeddingBlocker

Uses sentence embeddings to find semantically similar pairs.

```python
blocker = EmbeddingBlocker(
    df_left, df_right,
    text_cols=["title", "description"],
    model="sentence-transformers/all-MiniLM-L6-v2",
    threshold=0.5,
    top_k=30
)
```

Optional but useful for semantic similarity that tokens miss.

#### Blocking Optimization

The optimizer tests multiple blocker configurations and selects the best one:

```python
from PyDI.pipeline import optimize_blocking

result = optimize_blocking(
    df_left, df_right,
    validation_set=val_set,
    chat_model=llm,
    min_pair_completeness=0.97  # require 97% recall
)

best_spec = result["best_spec"]
```

**Optimization strategy:**
1. Test multiple blocker types and parameters
2. Filter configurations with pair completeness < 97% (too many missed matches)
3. Among valid configurations, pick highest reduction ratio (fewest candidates)


### Matching

Matching scores candidate pairs and classifies as match/non-match.

#### Available Matchers

| Matcher | Description | Use Case |
|---------|-------------|----------|
| **RuleBasedMatcher** | Weighted similarity functions | Known domain rules, quick setup |
| **MLBasedMatcher** | Trained classifier on features | When training data is available |
| **LLMBasedMatcher** | LLM-based semantic matching | Complex cases, no training data |

#### RuleBasedMatcher

Combines comparators (similarity functions) with manual weights.

```python
from PyDI.entitymatching import RuleBasedMatcher, StringComparator

comparators = [
    StringComparator("title", similarity_function="jaro_winkler"),
    StringComparator("director", similarity_function="jaccard"),
]

matcher = RuleBasedMatcher()
correspondences = matcher.match(
    df_left, df_right,
    candidates=blocker,
    comparators=comparators,
    weights=[0.6, 0.4],
    threshold=0.7
)
```

#### MLBasedMatcher

Trains a classifier on labeled pairs to learn optimal feature weights.

```python
from PyDI.entitymatching import MLBasedMatcher, FeatureExtractor
from sklearn.ensemble import RandomForestClassifier

extractor = FeatureExtractor(comparators)
clf = RandomForestClassifier()
clf.fit(X_train, y_train)

matcher = MLBasedMatcher(extractor)
correspondences = matcher.match(
    df_left, df_right,
    candidates=blocker,
    trained_classifier=clf
)
```

#### Matching Optimization

Tests multiple matcher configurations:

```python
from PyDI.pipeline import optimize_matching

result = optimize_matching(
    df_left, df_right,
    validation_set=val_set,
    include_rule_based=True,
    include_ml_based=True,
    training_set=train_set
)

best = result["best"]  # highest F1 configuration
```

**What gets tested:**
- RuleBasedMatcher with different similarity functions (jaro_winkler, jaccard, etc.)
- MLBasedMatcher with different classifiers (LogisticRegression, RandomForest)
- Multiple thresholds (0.0 to 1.0 in steps of 0.05)


## Step 4: Data Fusion

Merges matched records into a single consolidated dataset, resolving conflicts.

```python
from PyDI.datafusion import DataFusion

fusion = DataFusion(
    correspondences=correspondences,
    datasets={"actors": df_actors, "awards": df_awards},
    fusion_rules=fusion_rules
)

fused_df = fusion.fuse()
```

See [Data Fusion](DataFusion.md) for conflict resolution strategies.


## Optimization Strategy

The pipeline optimization follows a two-phase approach:

### Phase 1: Blocking Optimization

**Goal:** Maximize reduction ratio while maintaining high recall

| Metric | Target | Description |
|--------|--------|-------------|
| Pair Completeness | ≥ 97% | Recall - don't miss true matches |
| Reduction Ratio | Maximize | Fewer candidates = faster matching |

### Phase 2: Matching Optimization

**Goal:** Maximize F1 score on validation set

| Metric | Description |
|--------|-------------|
| F1 | Harmonic mean of precision and recall |
| Precision | True matches / predicted matches |
| Recall | True matches found / all true matches |

The pipeline saves all optimization results to CSV files for analysis and reproducibility.
