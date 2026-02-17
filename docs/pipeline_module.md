# PyDI Pipeline Module

The `PyDI.pipeline` module provides end-to-end data integration capabilities, automating schema matching, normalization, and entity resolution tasks.

## Quick Start

```python
from PyDI.pipeline import run_pipeline

# Process all data files in a directory
results = run_pipeline(
    data_dir="usecases/input/movies/data",
    schema_path="usecases/input/movies/schemamatching/target_schema.json",
    chat_model=llm
)
```

## Module Structure

```
PyDI/pipeline/
├── __init__.py           # Public API exports
├── run.py                # Main pipeline runner
├── schema_matching.py    # LLM-based schema matching
├── normalization.py      # Data normalization/translation
├── entity_resolution.py  # Blocking and candidate generation
└── optimization.py       # Blocking parameter optimization
```

## Core Components

### 1. Pipeline Runner (`run.py`)

The main entry point for batch processing data files.

#### `run_pipeline()`

Processes all data files in a directory through schema matching and normalization.

```python
run_pipeline(
    data_dir: str | Path,      # Directory containing *.xml, *.csv files
    schema_path: str | Path,   # Path to target_schema.json
    chat_model,                # LangChain chat model
    num_rows: int = 30,        # Sample rows for LLM
    output_dir: str | Path = None,  # Output directory (default: data_dir/normalized)
    force_rematch: bool = False     # Regenerate cached mappings
) -> Dict[str, pd.DataFrame]
```

**Features:**
- Caches schema mappings to `{output_dir}/mappings/{name}_mapping.csv`
- Caches normalized data to `{output_dir}/{name}.csv`
- Writes statistics to `{output_dir}/pipeline_stats.json`
- On subsequent runs, loads from cache unless `force_rematch=True`

#### `discover_files()`

Discovers data files and schema in a structured input directory.

```python
discover_files(input_dir: Path) -> Dict[str, List[Path]]
```

**Expected directory structure:**
```
input_dir/
├── data/                    # Source data files
│   ├── *.xml
│   └── *.csv
└── schemamatching/
    └── target_schema.json   # Target schema definition
```

---

### 2. Schema Matching (`schema_matching.py`)

Uses LLM to automatically map source columns to target schema columns.

#### `auto_match_schema()`

```python
auto_match_schema(
    source_df: pd.DataFrame,   # Source dataset
    target_schema: dict,       # JSON Schema with "properties"
    chat_model,                # LangChain chat model
    num_rows: int = 10         # Sample rows to show LLM
) -> SchemaMapping
```

**Returns:** A `SchemaMapping` DataFrame with source-to-target column mappings.

---

### 3. Normalization (`normalization.py`)

Translates and normalizes source data to match target schema types and formats.

#### `auto_normalize()`

```python
auto_normalize(
    source_df: pd.DataFrame,
    mapping: SchemaMapping,
    target_schema: dict,
    on_failure: str = "keep"   # "keep", "null", or "raise"
) -> tuple[pd.DataFrame, TransformResult]
```

**Returns:** Tuple of (normalized DataFrame, transform statistics).

**Failure handling options:**
- `"keep"` - Keep original value on failure
- `"null"` - Set to null on failure
- `"raise"` - Raise exception on failure

---

### 4. Entity Resolution (`entity_resolution.py`)

Generates candidate pairs for entity matching using multiple blocking strategies.

#### `select_dataset_pairs()`

Selects which dataset pairs need entity resolution based on size.

```python
select_dataset_pairs(datasets: Dict[str, pd.DataFrame]) -> List[Tuple[str, str]]
```

**Strategy:** Connects the largest dataset to all others. For datasets A (largest), B, C:
- A ↔ B
- A ↔ C
- B ↔ C is inferred transitively through A

#### `select_blocking_columns()`

Uses LLM to select good blocking columns (content columns, not IDs).

```python
select_blocking_columns(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    chat_model,
    id_column: str = "id"
) -> List[str]
```

**Selection criteria:**
- Content columns (names, titles, descriptions)
- Values that overlap between datasets
- Not too sparse
- Excludes ID columns

#### `generate_candidates_multi_blocker()`

Generates candidate pairs using multiple blocking strategies.

```python
generate_candidates_multi_blocker(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    blocking_columns: List[str],
    id_column: str = "id",
    max_candidates_per_blocker: int = 1000,
    similarity_threshold: float = 0.3,
    use_embedding_blocker: bool = False,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    embedding_top_k: int = 30,
    # ... additional embedding parameters
) -> pd.DataFrame
```

**Blocking strategies used:**
1. **TokenBlocker** - Default tokenizer
2. **TokenBlocker** - Character 4-grams
3. **SortedNeighbourhoodBlocker** - Window size 3 (first column only)
4. **EmbeddingBlocker** - Semantic similarity (optional)

**Filtering:** Candidates are filtered by Jaccard similarity threshold before being returned.

#### `label_candidates_with_llm()`

Labels candidate pairs using LLM for creating validation sets.

```python
label_candidates_with_llm(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    candidates: pd.DataFrame,
    chat_model,
    id_column: str = "id",
    fields: List[str] = None,
    sample_size: int = 100
) -> pd.DataFrame
```

**Sampling strategy:** Uses "middle-out" sampling - alternates between high and low similarity candidates to get a balanced validation set.

#### `generate_validation_set()`

High-level function that generates a complete validation set.

```python
generate_validation_set(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    chat_model,
    id_column: str = "id",
    target_size: int = 100,
    target_positives: int = 30,
    similarity_threshold: float = 0.3
) -> pd.DataFrame
```

**Steps:**
1. Selects blocking columns using LLM
2. Generates candidates using multiple blockers
3. Labels candidates with LLM
4. Balances positive/negative examples

---

### 5. Optimization (`optimization.py`)

Optimizes blocking parameters using validation sets.

**Optimization Strategy:**
- Prioritize **high reduction ratio** (fewer candidates)
- While maintaining **pair completeness ≥ 97%** (recall)
- Among valid configurations, pick the one with highest reduction ratio

#### `load_or_generate_validation_set()`

Loads validation set from cache or generates if not exists.

```python
load_or_generate_validation_set(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    left_name: str,
    right_name: str,
    chat_model,
    output_dir: Path,
    id_column: str = "id",
    target_size: int = 100,
    target_positives: int = 30,
    similarity_threshold: float = 0.3,
    force_regenerate: bool = False
) -> pd.DataFrame
```

**Caching:** Saves to `{output_dir}/validation_{left_name}_{right_name}.csv`

#### `optimize_blocking()`

Finds optimal blocking parameters by testing multiple similarity thresholds.

```python
optimize_blocking(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    validation_set: pd.DataFrame,
    chat_model,
    id_column: str = "id",
    similarity_thresholds: List[float] = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    max_candidates: int = 1000,
    min_pair_completeness: float = 0.97,
    out_dir: Path = None,
    use_embedding_blocker: bool = False,
    # ... additional embedding parameters
) -> Dict
```

**Returns:**
```python
{
    "best": {...},              # Best configuration metrics
    "all_results": [...],       # All tested configurations
    "blocking_columns": [...],  # Selected blocking columns
    "min_pair_completeness": 0.97
}
```

#### `evaluate_blocker_types()`

Evaluates individual blocker types to understand their contribution.

```python
evaluate_blocker_types(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    validation_set: pd.DataFrame,
    blocking_column: str,
    id_column: str = "id",
    similarity_threshold: float = 0.3,
    min_pair_completeness: float = 0.97,
    out_dir: Path = None,
    include_embedding: bool = False,
    # ... additional embedding parameters
) -> List[Dict]
```

**Blocker types tested:**
- TokenBlocker (default)
- TokenBlocker (4-gram character)
- SortedNeighbourhoodBlocker (window=3)
- SortedNeighbourhoodBlocker (window=5)
- EmbeddingBlocker (optional)

---

## Key Metrics

| Metric | Description |
|--------|-------------|
| **Pair Completeness** | Recall - percentage of true matches found by blocking |
| **Pair Quality** | Precision - percentage of candidates that are true matches |
| **Reduction Ratio** | `1 - (candidates / total_possible_pairs)` |

---

## Usage Examples

### Full Pipeline

```python
from PyDI.pipeline import run_pipeline
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

results = run_pipeline(
    data_dir="usecases/input/movies/data",
    schema_path="usecases/input/movies/schemamatching/target_schema.json",
    chat_model=llm,
    num_rows=30,
    output_dir="output/movies"
)
```

### Individual Functions

```python
from PyDI.pipeline import auto_match_schema, auto_normalize
import pandas as pd

# Load your data
source_df = pd.read_csv("data.csv")
target_schema = {"properties": {...}}

# Step 1: Match schema
mapping = auto_match_schema(source_df, target_schema, chat_model=llm)

# Step 2: Normalize
normalized_df, stats = auto_normalize(source_df, mapping, target_schema)
```

### Entity Resolution

```python
from PyDI.pipeline import (
    select_dataset_pairs,
    generate_validation_set,
    optimize_blocking
)

# Select pairs to match
datasets = {"actors": df_actors, "awards": df_awards, "movies": df_movies}
pairs = select_dataset_pairs(datasets)

# Generate validation set
val_set = generate_validation_set(
    df_left=datasets["actors"],
    df_right=datasets["awards"],
    chat_model=llm,
    target_size=100,
    target_positives=30
)

# Optimize blocking parameters
best_config = optimize_blocking(
    df_left=datasets["actors"],
    df_right=datasets["awards"],
    validation_set=val_set,
    chat_model=llm,
    min_pair_completeness=0.97
)
```

---

## Public API

All public functions are exported from `PyDI.pipeline`:

```python
from PyDI.pipeline import (
    # Main pipeline
    run_pipeline,
    discover_files,

    # Schema matching
    auto_match_schema,

    # Normalization
    auto_normalize,

    # Entity resolution
    select_dataset_pairs,
    select_blocking_columns,
    generate_candidates_multi_blocker,
    label_candidates_with_llm,
    generate_validation_set,

    # Optimization
    load_or_generate_validation_set,
    optimize_blocking,
    evaluate_blocker_types,
)
```
