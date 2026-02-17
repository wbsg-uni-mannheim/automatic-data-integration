# PyDI Pipeline Documentation

This document describes the PyDI data integration pipeline, its steps, configuration options, and usage.

## Overview

The pipeline performs end-to-end data integration across multiple datasets:

1. **Schema Matching** - Align schemas across input datasets
2. **Validation & Training Set Generation** - Generate labeled pairs for model training
3. **FAISS Candidate Generation** - Create candidate pairs using embedding similarity
4. **Training Set Comparison** (optional) - Compare different training set generation strategies
5. **Matcher Optimization** - Find the best matching model and threshold
6. **Active Learning** - Augment training data with informative examples
7. **Data Fusion** - Merge matched records into a unified dataset
8. **Fusion Validation** - Generate validation sets for fusion quality assessment
9. **Test Evaluation** - Evaluate against held-out test sets

## Usage

```bash
python scripts/run_pipeline.py \
    --data-dir usecases/input/games/data \
    --schema usecases/input/games/schemamatching/target_schema.json \
    --output-dir scripts/output/games
```

### Command Line Arguments

| Argument | Description |
|----------|-------------|
| `--data-dir` | Path to directory containing input CSV/XML files |
| `--schema` | Path to target schema JSON file |
| `--output-dir` | Path to output directory for results |
| `--test-dir` | Path to directory containing held-out test sets |
| `--compare-training-sets` | Generate and compare multiple training set variants |
| `--fusion-val-generation-mode` | Fusion validation mode: `llm`, `llm_omit`, `web`, `web_omit`, `all` |
| `--fusion-use-test-set` | Filter fusion validation to entities in the test set |
| `--fusion-case` | Fusion rule selection strategy |
| `--fusion-iterations` | Number of iterations for iterative fusion case |

## Input Directory Structure

The pipeline expects a specific directory structure for input data:

```
usecases/input/{usecase}/
├── data/                          # Source datasets (CSV, XML, JSON)
│   ├── dataset1.csv
│   ├── dataset2.xml
│   └── dataset3.json
├── schemamatching/
│   └── target_schema.json         # Target schema definition
├── entitymatching/                # Optional: provided training/test sets
│   ├── {left}_2_{right}_train.csv # Provided training set
│   ├── {left}_2_{right}_test.csv  # Held-out test set
│   └── embeddings/                # Optional: pre-computed embeddings
└── fusion/
    ├── test_set.xml               # Fusion test set
    └── validation_set.xml         # Fusion validation set
```

## Training Set Comparison (Step 4)

When `--compare-training-sets` is enabled, the pipeline generates and compares multiple training set variants to find the optimal strategy.

### Generated Variants

| Variant | Description |
|---------|-------------|
| `provided` | Official/provided training set from `entitymatching/*_train.csv` (if exists) |
| `faiss_small` | Small FAISS-based set (default: 34 pos, 66 neg) |
| `faiss_large` | Large FAISS-based set (default: 200 pos, 400 neg) |
| `active` | Active learning augmented set starting from faiss_small |
| `*_plus_random` | Any above variant with 20% additional random pairs |

### Provided Training Sets

The comparison automatically loads provided/official training sets from the `entitymatching` directory if they exist. These files should be named:

- `{left_name}_2_{right_name}_train.csv` (e.g., `dbpedia_2_sales_train.csv`)
- Or with swapped order: `{right_name}_2_{left_name}_train.csv`

The file format should be:
- CSV with columns: `id1`, `id2`, `label`
- Labels: `TRUE` or `FALSE` (case-insensitive)
- Header is optional (auto-detected)

### Test Set Matching

Test files are matched to training files by name. The pipeline checks both orderings:
- `{left}_2_{right}_test.csv`
- `{right}_2_{left}_test.csv`

### Output

Comparison results are saved to:
```
{output_dir}/entity_resolution/training/training_comparison/{left}_{right}/
├── comparison_summary.csv    # Results for all variants and models
└── comparison_details.json   # Detailed metrics and best variant info
```

Example `comparison_summary.csv`:
```csv
variant,model,train_total,train_positives,train_negatives,f1,precision,recall,tokens_used
provided,logreg,500,100,400,0.85,0.88,0.82,0
provided,rf,500,100,400,0.87,0.90,0.84,0
faiss_small,logreg,100,34,66,0.72,0.75,0.70,0
faiss_large,logreg,600,200,400,0.83,0.85,0.81,0
active,xgb,615,205,410,0.89,0.91,0.87,0
```

## Configuration

Key configuration parameters in `run_pipeline.py`:

### Validation Set Generation
```python
VALIDATION_TARGET_POSITIVES = 100   # Target positive pairs
VALIDATION_TARGET_NEGATIVES = 200   # Target negative pairs
VALIDATION_K = 20                   # FAISS neighbors per query
```

### Training Set Generation
```python
TRAINING_SMALL_TARGET_POSITIVES = 34    # Small set positives
TRAINING_SMALL_TARGET_NEGATIVES = 66    # Small set negatives
TRAINING_LARGE_TARGET_POSITIVES = 200   # Large set positives
TRAINING_LARGE_TARGET_NEGATIVES = 400   # Large set negatives
```

### Training Set Comparison
```python
COMPARISON_RANDOM_SAMPLE_RATIO = 0.2    # Random pairs ratio for *_plus_random variants
```

## Final Test Evaluation

The pipeline also runs a final training data comparison in the test evaluation step (Step 8). This comparison uses the same methodology but is separate from Step 4.

Results are saved to:
```
{output_dir}/entity_resolution/test_evaluation/training_data_comparison.csv
```

This comparison includes:
- `manual` - Provided training sets (same as `provided` in Step 4)
- `auto (faiss)` - FAISS-generated training set
- `auto (augmented)` - Active learning augmented set

The test evaluation handles swapped dataset ordering automatically, so `metacritic_2_dbpedia_train.csv` will match with `dbpedia_2_metacritic_test.csv`.
