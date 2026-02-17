# Pipeline Prompts

This directory contains all LLM prompts used in the unsupervised data integration pipeline. Prompts are organized by pipeline step. Template variables are shown as `{variable_name}`.

## Directory Structure

- `schema_matching/` - Prompts for aligning source schemas to a target schema
- `normalization/` - Prompts for mapping categorical values to standardized taxonomies
- `entity_matching/` - Prompts for entity resolution (matching, blocking column selection)
- `data_fusion/` - Prompts for conflict resolution strategy selection and validation set generation

## Model

All prompts are designed for GPT-5.2 (OpenAI) via the LangChain interface.
