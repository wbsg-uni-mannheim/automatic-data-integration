# Pipeline Module Design Document

## Overview

The `PyDI.pipeline` module provides end-to-end data integration by orchestrating existing PyDI components (schema matching, normalization) into a simple, automated workflow.

## Goals

1. **Simplicity**: One function call to process multiple data files
2. **Reuse**: Leverage existing PyDI modules, don't reinvent
3. **Minimal abstraction**: Plain functions, no complex class hierarchies

## Architecture

```
PyDI/pipeline/
├── __init__.py          # Exports: run_pipeline, auto_match_schema, auto_normalize
├── run.py               # Main orchestrator
├── schema_matching.py   # Wraps LLMBasedSchemaMatcher
└── normalization.py     # Wraps SchemaTranslator
```

Total code: ~200 lines

## Components

### `run_pipeline(data_dir, schema_path, chat_model, ...)`

Main entry point. Discovers data files, runs schema matching and normalization on each.

**Parameters:**
- `data_dir`: Directory containing `*.xml` and `*.csv` files
- `schema_path`: Path to `target_schema.json`
- `chat_model`: LangChain chat model for LLM-based matching
- `num_rows`: Sample rows for LLM (default: 30)
- `output_dir`: Where to write normalized CSVs (default: `data_dir/normalized/`)

**Outputs:**
- Normalized CSV files per input dataset
- `pipeline_stats.json` with transformation statistics
- `pipeline.log` (if configured in calling script)

### `auto_match_schema(source_df, target_schema, chat_model, ...)`

Wraps `LLMBasedSchemaMatcher` to match source columns to target schema.

### `auto_normalize(source_df, mapping, target_schema, ...)`

Wraps `SchemaTranslator` to rename columns and normalize values.

## Data Flow

```
Input Files (XML/CSV)
        │
        ▼
   Load with PyDI.io
        │
        ▼
   Schema Matching (LLM)
   source columns → target columns
        │
        ▼
   Normalization
   rename + transform values
        │
        ▼
   Output CSVs
```

## Usage

```python
from langchain_openai import ChatOpenAI
from PyDI.pipeline import run_pipeline

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

results = run_pipeline(
    data_dir="usecases/input/movies/data/regular",
    schema_path="usecases/input/movies/schemamatching/target_schema.json",
    chat_model=llm,
    output_dir="scripts/output/movies/regular",
)

# results = {"academy_awards": df, "actors": df, "golden_globes": df}
```

## Target Schema Format

Standard JSON Schema with PyDI extensions:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Movie Record",
  "properties": {
    "id": {"type": "string", "description": "Unique identifier"},
    "title": {"type": "string", "description": "Movie title"},
    "date": {"type": "string", "format": "date"},
    "oscar": {"type": "boolean"}
  }
}
```

The schema serves two purposes:
1. **Schema matching**: LLM sees field names and descriptions for better matching
2. **Normalization**: Types and formats define how values should be transformed

## Current Limitations

### Normalization Failures

When normalization fails (e.g., can't parse a date), the current behavior is:
- `on_failure="null"`: Set the value to null

**TODO**: Add proper error resolution for normalization failures. Options to explore:
- LLM-based value correction
- Rule-based fallbacks
- User confirmation for ambiguous cases

### Missing Columns

When a target schema column doesn't exist in a source dataset:
- The column is simply not present in the output
- This is logged as a warning but not treated as an error

**TODO**: Consider whether missing columns should be:
- Added with null values
- Flagged for user review
- Handled differently based on schema `required` field

### No Feedback Loop

The pipeline currently runs in a single pass. There's no mechanism for:
- Using fusion results to improve schema matching
- Iterative refinement based on data quality issues

This is intentional for the initial implementation. Feedback loops will be added when we implement blocking, entity matching, and fusion steps.

## Future Work

### Next Steps (Blocking & Entity Matching)

The pipeline currently handles:
1. Schema matching
2. Value normalization

To complete end-to-end integration, we need to add:
3. Blocking (candidate pair generation)
4. Entity matching (duplicate detection)
5. Data fusion (conflict resolution)

### Heuristics Layer

The current implementation uses fixed logic. Future improvements:
- Confidence-based decisions (e.g., fall back to different matcher if confidence low)
- Automatic method selection based on data characteristics
- Learning from user corrections

See `docs/heuristics_architecture.md` for the design approach.

## File Structure for Use Cases

```
usecases/input/{usecase}/
├── data/
│   └── regular/        # or other variants
│       ├── dataset1.xml
│       ├── dataset2.xml
│       └── dataset3.csv
└── schemamatching/
    └── target_schema.json
```

## Output Structure

```
scripts/output/{usecase}/regular/
├── dataset1.csv
├── dataset2.csv
├── dataset3.csv
├── pipeline_stats.json
└── pipeline.log
```

### pipeline_stats.json

```json
{
  "dataset1": {
    "rows": 4580,
    "mappings": 6,
    "transformed": 4580,
    "failed": 366
  },
  ...
}
```

- `rows`: Number of input rows
- `mappings`: Number of columns successfully mapped to target schema
- `transformed`: Number of values that were normalized
- `failed`: Number of normalization failures (set to null)
