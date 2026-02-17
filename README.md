# Automatic End-to-End Data Integration using Large Language Models

This repository contains the code, case study data, and pipeline outputs for the paper:

> **Automatic End-to-End Data Integration using Large Language Models**
> Aaron Steiner, Christian Bizer
> Data and Web Science Group, University of Mannheim
> Beyond SQL Workshop 2026 at ICDE

## Abstract

Designing data integration pipelines requires substantial manual effort from data engineers who must configure pipeline components and label training data for each integration task. This paper investigates the potential of LLMs to fully automate end-to-end data integration pipelines. We present three case studies covering the integration of heterogeneous data sources describing music releases, video games, and companies. For each pipeline step -- schema matching, value normalization, entity matching, and data fusion -- we compare the performance achieved using GPT-5.2 against the performance achieved by graduate-level data engineers who manually configured the pipeline and labeled training data.

## Pipeline

The automated pipeline covers four steps:

1. **Schema Matching** -- LLM-based single-prompt approach that receives source column names with sample values and the target schema as a JSON Schema document. Achieves perfect F1 (1.00) across all three case studies.

2. **Value Normalization** -- Hybrid approach combining code-based normalizers for standard data formats (dates, units, phone numbers, etc.) with LLM-based taxonomy mapping for categorical attributes (genres, platforms, industry codes).

3. **Entity Matching** -- LLM-labeled training data generation using FAISS-based candidate selection and active learning augmentation. Trains traditional ML matchers (XGBoost, random forests, logistic regression) achieving an average F1 of 0.937, competitive with human-labeled baselines (0.916).

4. **Data Fusion** -- LLM-generated validation sets using well-known entities to automatically select among candidate fusion heuristics per attribute. RAG-augmented variant achieves 0.773 average accuracy.

## Case Studies

| Use Case | Sources | Records | Target Attributes |
|----------|---------|---------|-------------------|
| Music | MusicBrainz, Last.fm, Discogs | 37,255 | 8 (name, artist, date, country, label, genre, tracks, duration) |
| Games | DBpedia, Metacritic, Sales | 74,951 | 12 (name, releaseYear, developer, genres, publisher, platform, ...) |
| Companies | Forbes, DBpedia, FullContact | 14,016 | 10 (name, website, founded, country, city, industry, assets, revenue, founders) |

## Repository Structure

```
├── PyDI/                   # PyDI framework (core library)
├── scripts/                # Pipeline execution scripts
│   ├── run_pipeline.py     # Main pipeline entry point
│   └── output/             # Pipeline run outputs and metrics
├── usecases/               # Case study data and workflows
│   ├── input/              # Source datasets, schemas, training/test sets
│   │   ├── music/
│   │   ├── games/
│   │   └── companies/
│   ├── music_workflow.ipynb
│   ├── games_workflow.ipynb
│   └── companies_workflow.ipynb
├── docs/                   # Documentation and tutorials
├── prompts/                # LLM prompt templates
└── tests/                  # Test suite
```

## Usage

### Installation

```bash
pip install -r requirements_clean.txt
```

### Running the Pipeline

```bash
python scripts/run_pipeline.py \
    --data-dir usecases/input/games/data \
    --schema usecases/input/games/schemamatching/target_schema.json \
    --output-dir scripts/output/games
```

See [Pipeline Documentation](docs/pipeline.md) for all configuration options.

### Use Case Notebooks

Interactive notebooks for each case study are available in `usecases/`:

| Notebook | Description |
|----------|-------------|
| [Music Workflow](usecases/music_workflow.ipynb) | Integrating MusicBrainz, Last.fm, and Discogs |
| [Games Workflow](usecases/games_workflow.ipynb) | Integrating DBpedia, Metacritic, and Sales data |
| [Companies Workflow](usecases/companies_workflow.ipynb) | Integrating Forbes, DBpedia, and FullContact |

## Key Results

**Entity Matching** (F1 on held-out test sets):

| Use Case | Dataset Pair | Human Config | Human Labels | LLM Labels |
|----------|-------------|----------|----------------|-------|
| Games | DBpedia--Metacritic | .930 | .826 | .849 |
| Games | DBpedia--Sales | .927 | .839 | .979 |
| Companies | DBpedia--Forbes | .857 | .954 | .939 |
| Companies | Forbes--FullContact | .870 | .898 | .897 |
| Music | Discogs--MusicBrainz | .800 | .991 | .990 |
| Music | Last.fm--MusicBrainz | .977 | .988 | .968 |
| **Average** | | **.894** | **.916** | **.937** |

**Data Fusion** (test accuracy):

| Use Case | Human Config | Human Val. Set | LLM Val. Set | LLM + RAG |
|----------|----------|----------------|-------|-------|
| Games | .832 | .866 | .866 | .866 |
| Companies | .803 | .861 | .709 | .744 |
| Music | .766 | .721 | .708 | .708 |
| **Average** | **.800** | **.816** | **.761** | **.773** |

**Cost**: The total LLM usage cost is approximately $27 across all three use cases (~$9 per use case), using GPT-5.2 at February 2026 pricing. The LLM pipeline runs unattended in approximately 2 hours per use case, compared to 19+ person-hours for the human baseline.

## Built With

This project uses the [PyDI](https://github.com/wbsg-uni-mannheim/PyDI) (Python Data Integration) framework for all pipeline components.

## Contact

- Aaron Steiner -- aaron.steiner@uni-mannheim.de
- Christian Bizer -- christian.bizer@uni-mannheim.de

[Data and Web Science Group](https://www.uni-mannheim.de/dws/), University of Mannheim
