# Heuristics Architecture for PyDI Agent Pipeline

## The Real Question

PyDI already has:
- **Schema matching**: `LabelBasedSchemaMatcher`, `InstanceBasedSchemaMatcher`, `DuplicateBasedSchemaMatcher`, `LLMBasedSchemaMatcher`
- **Normalization**: `normalize_dataframe(df, auto=True)`, `profile_dataframe()`, JSON schema integration via `load_normalization_spec()`
- **Blocking**: `EmbeddingBlocker`, `TokenBlocker`, `StandardBlocker`
- **Matching**: `RuleBasedMatcher`, `BERTMatcher`, comparators
- **Fusion**: `DataFusionEngine` with strategies

So what are we actually building? Not new algorithms - we're building **orchestration logic** that decides:
1. Which existing tools to call
2. In what order
3. With what parameters
4. How to interpret results and adjust

## Simplest Viable Approach: One Function Per Step

```
PyDI/
└── pipeline/
    ├── __init__.py
    ├── run.py              # Main entry point: run_pipeline()
    ├── schema_matching.py  # auto_match_schema()
    ├── normalization.py    # auto_normalize()
    ├── blocking.py         # auto_block()
    ├── matching.py         # auto_match()
    └── fusion.py           # auto_fuse()
```

Each file has **one main function** that:
- Takes source data + target schema + optional config
- Uses PyDI's existing modules internally
- Returns results in a standard format

```python
# schema_matching.py
def auto_match_schema(
    source_df: pd.DataFrame,
    target_schema: dict,
    method: str = "auto"  # "auto", "label", "instance", "llm"
) -> SchemaMapping:
    """
    Match source columns to target schema attributes.

    If method="auto", tries multiple approaches and picks best.
    """
    if method == "auto":
        # Try label-based first (fast, often good enough)
        label_matcher = LabelBasedSchemaMatcher()
        mapping = label_matcher.match(source_df, target_schema)

        # Check confidence - if low, try LLM
        if mapping.avg_confidence < 0.7:
            llm_matcher = LLMBasedSchemaMatcher()
            mapping = llm_matcher.match(source_df, target_schema)

        return mapping

    # ... specific method implementations
```

```python
# normalization.py
def auto_normalize(
    df: pd.DataFrame,
    schema_mapping: SchemaMapping,
    target_schema: dict
) -> pd.DataFrame:
    """
    Normalize values based on target schema requirements.

    Uses PyDI's existing normalize_dataframe with auto-detection,
    plus target schema specs for format requirements.
    """
    # Get normalization spec from target schema
    spec = load_normalization_spec(target_schema)

    # Apply schema mapping (rename columns)
    df_mapped = apply_mapping(df, schema_mapping)

    # Normalize using existing PyDI infrastructure
    result = normalize_dataframe(df_mapped, spec=spec, auto=True)

    return result.dataframe
```

```python
# run.py
def run_pipeline(
    sources: List[pd.DataFrame],
    target_schema: dict,
    config: Optional[dict] = None
) -> pd.DataFrame:
    """
    Run full integration pipeline.
    """
    config = config or {}

    # Step 1: Schema matching
    mappings = []
    for df in sources:
        mapping = auto_match_schema(df, target_schema)
        mappings.append(mapping)

    # Step 2: Normalize
    normalized = []
    for df, mapping in zip(sources, mappings):
        df_norm = auto_normalize(df, mapping, target_schema)
        normalized.append(df_norm)

    # Step 3: Block
    candidates = auto_block(normalized)

    # Step 4: Match
    correspondences = auto_match(normalized, candidates)

    # Step 5: Fuse
    result = auto_fuse(normalized, correspondences, target_schema)

    return result
```

## Why This Is Enough (For Now)

1. **Single responsibility**: Each `auto_X` function handles one step
2. **Uses existing code**: Just wraps PyDI modules, doesn't reinvent
3. **Easy to modify**: Want to try different blocking? Edit `auto_block()`
4. **No abstraction overhead**: Plain functions, plain dicts
5. **Testable**: Each function can be tested independently

## What About "Heuristics"?

The "heuristics" are just the decision logic inside each function:

```python
def auto_match_schema(...):
    # HEURISTIC 1: Try fast method first
    mapping = label_matcher.match(...)

    # HEURISTIC 2: Fall back to LLM if confidence low
    if mapping.avg_confidence < 0.7:
        mapping = llm_matcher.match(...)

    # HEURISTIC 3: Use instance-based for columns with no name match
    for col in unmatched_columns:
        instance_mapping = instance_matcher.match_column(col, ...)
        mapping.add(instance_mapping)
```

These are just if-statements and loops. No need for a `Heuristic` class.

## When Would We Need More Structure?

Add complexity only when we hit real problems:

| Problem | Solution |
|---------|----------|
| Too many heuristics in one function | Extract to helper functions in same file |
| Need to A/B test heuristics | Add a `strategy` parameter |
| Feedback loops between steps | Pass results back, add retry logic |
| Agent needs to introspect options | Add `list_available_methods()` functions |

## Concrete Next Steps

1. **Create `pipeline/` directory** with basic structure
2. **Implement `auto_match_schema()`** - wrap existing schema matchers
3. **Implement `auto_normalize()`** - wrap existing normalization
4. **Test on movies use case** - does it work end-to-end?
5. **Then add blocking/matching/fusion** as needed

## Files to Create

```
PyDI/pipeline/
├── __init__.py          # Exports run_pipeline, auto_* functions
├── run.py               # ~50 lines - orchestrates the pipeline
├── schema_matching.py   # ~80 lines - wraps schema matchers
└── normalization.py     # ~60 lines - wraps normalization
```

Total: ~200 lines to start. Add more files as we implement more steps.

## Open Questions

1. **How does target schema look?** Need to see an example to understand what info is available
2. **What should `run_pipeline` return?** Just the fused DataFrame, or also metadata/logs?
3. **How to handle errors?** Fail fast, or continue with partial results?
