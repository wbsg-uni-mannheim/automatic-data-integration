"""Utilities for running the WDC Schema Matching Benchmark (WDC SMB).

The helper functions in this module connect :class:`LLMBasedSchemaMatcher`
to the official benchmark splits (SOTAB-SM and T2D-SM) and report precision,
recall, and F1 scores via :class:`SchemaMappingEvaluator`.

Benchmark data must only be used for evaluation, never for model training.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple, TYPE_CHECKING

import pandas as pd

from .evaluation import SchemaMappingEvaluator
from .llm_based import LLMBasedSchemaMatcher

if TYPE_CHECKING:  # pragma: no cover - optional dependency for type checking
    from langchain_core.language_models.chat_models import BaseChatModel


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class WDCSMBPair:  # pragma: no cover - simple container
    """Container describing one benchmark table pair."""

    pair_id: str
    source_df: pd.DataFrame
    target_df: pd.DataFrame
    evaluation: pd.DataFrame


@dataclass
class WDCBenchmarkConfig:
    """Configuration specifying which benchmark variant to evaluate."""

    dataset_root: Path
    task: str  # "sotab", "t2d-sm-wh", "t2d-sm-nh"
    split: str  # "train", "valid", "test"
    max_pairs: Optional[int] = None

    def normalized_task(self) -> str:
        lookup = {
            "sotab": "sotab",
            "sotab-sm": "sotab",
            "sotab_sm": "sotab",
            "t2d": "t2d-sm-wh",
            "t2d-sm": "t2d-sm-wh",
            "t2d_sm_wh": "t2d-sm-wh",
            "t2d-sm-wh": "t2d-sm-wh",
            "t2d-sm-nh": "t2d-sm-nh",
            "t2d_sm_nh": "t2d-sm-nh",
        }
        key = self.task.lower().strip()
        if key not in lookup:
            raise ValueError(
                f"Unsupported task '{self.task}'. Choose from 'sotab', 't2d-sm-wh', or 't2d-sm-nh'."
            )
        return lookup[key]

    def normalized_split(self) -> str:
        lookup = {
            "train": "train",
            "training": "train",
            "valid": "valid",
            "validation": "valid",
            "dev": "valid",
            "test": "test",
        }
        key = self.split.lower().strip()
        if key not in lookup:
            raise ValueError(
                f"Unsupported split '{self.split}'. Choose from 'train', 'valid', or 'test'."
            )
        return lookup[key]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_wdc_smb_benchmark(
    matcher: LLMBasedSchemaMatcher,
    config: WDCBenchmarkConfig,
    *,
    complete: bool = False,
) -> dict:
    """Run the matcher across the requested benchmark split.

    Parameters
    ----------
    matcher : LLMBasedSchemaMatcher
        Instantiated matcher ready to call ``match``.
    config : WDCBenchmarkConfig
        Benchmark configuration (dataset root, task variant, split).
    complete : bool, optional
        If True, treat the provided correspondences as exhaustive negatives
        during evaluation.

    Returns
    -------
    dict
        Dictionary containing overall metrics, a per-pair DataFrame, and the
        concatenated prediction/evaluation frames.
    """

    pairs = list(_iter_pairs(config))
    if not pairs:
        raise RuntimeError(
            "No table pairs found. Check that dataset_root points to an extracted WDC SMB split."
        )

    all_predictions: List[pd.DataFrame] = []
    all_evaluations: List[pd.DataFrame] = []
    per_pair_records: List[dict] = []

    for idx, pair in enumerate(pairs, start=1):
        logger.info("[%d/%d] Matching %s", idx, len(pairs), pair.pair_id)

        predictions = matcher.match(pair.source_df, pair.target_df)
        predictions = _ensure_mapping_frame(predictions, pair.source_df, pair.target_df).copy()
        predictions["pair_id"] = pair.pair_id

        evaluation_df = pair.evaluation.copy()
        evaluation_df["pair_id"] = pair.pair_id

        metrics = SchemaMappingEvaluator.evaluate(predictions, evaluation_df, complete=complete)

        per_pair_records.append(
            {
                "pair_id": pair.pair_id,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "matched": metrics["matched"],
                "correct": metrics["correct"],
                "positives": metrics["correct_total"],
                "negatives": len(evaluation_df) - metrics["correct_total"],
            }
        )

        all_predictions.append(predictions)
        all_evaluations.append(evaluation_df)

    predictions_df = _concat_schema_mappings(all_predictions)
    evaluation_df = _concat_schema_mappings(all_evaluations, require_score=False)

    overall_metrics = SchemaMappingEvaluator.evaluate(predictions_df, evaluation_df, complete=complete)

    return {
        "overall": overall_metrics,
        "per_pair": pd.DataFrame(per_pair_records),
        "predictions": predictions_df,
        "evaluation": evaluation_df,
    }


# ---------------------------------------------------------------------------
# Dataset iteration helpers
# ---------------------------------------------------------------------------


def _iter_pairs(config: WDCBenchmarkConfig) -> Iterator[WDCSMBPair]:
    normalized_task = config.normalized_task()
    normalized_split = config.normalized_split()

    dataset_root = config.dataset_root
    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset root '{dataset_root}' does not exist.")

    if normalized_task == "sotab":
        yield from _iter_sotab_pairs(dataset_root, normalized_split, config.max_pairs)
    elif normalized_task in {"t2d-sm-wh", "t2d-sm-nh"}:
        yield from _iter_t2d_pairs(dataset_root, normalized_split, normalized_task, config.max_pairs)
    else:  # pragma: no cover - guarded by normalized_task
        raise ValueError(f"Unsupported task '{normalized_task}'.")


def _iter_sotab_pairs(root: Path, split: str, max_pairs: Optional[int]) -> Iterator[WDCSMBPair]:
    split_dir = root / split
    table_dir = split_dir / "tables"

    correspondences_path = _find_correspondence_file(split_dir)
    correspondences = pd.read_csv(correspondences_path)

    unique_pairs = (
        correspondences[["table_name_left", "table_name_right"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    for idx, row in unique_pairs.iterrows():
        if max_pairs is not None and idx >= max_pairs:
            break

        left_name = str(row["table_name_left"])
        right_name = str(row["table_name_right"])

        left_df = _load_table(table_dir, left_name)
        right_df = _load_table(table_dir, right_name)

        pair_corr = correspondences[
            (correspondences["table_name_left"] == left_name)
            & (correspondences["table_name_right"] == right_name)
        ]

        evaluation = _build_indexed_evaluation(
            left_df,
            right_df,
            pair_corr,
            left_index_col="column_index_left",
            right_index_col="column_index_right",
            label_col="label",
        )

        pair_id = f"{left_df.attrs['dataset_name']} → {right_df.attrs['dataset_name']}"

        yield WDCSMBPair(pair_id=pair_id, source_df=left_df, target_df=right_df, evaluation=evaluation)


def _iter_t2d_pairs(
    root: Path,
    split: str,
    variant: str,
    max_pairs: Optional[int],
) -> Iterator[WDCSMBPair]:
    split_dir = root / split

    web_dir_candidates = [split_dir / "webtables", split_dir / "web_tables"]
    dbpedia_dir_candidates = [split_dir / "dbpedia_tables", split_dir / "dbpedia"]

    web_dir = _pick_existing_dir(web_dir_candidates)
    dbpedia_dir = _pick_existing_dir(dbpedia_dir_candidates)

    correspondences_path = _find_correspondence_file(split_dir)
    correspondences = pd.read_csv(correspondences_path)

    unique_tables = correspondences["table_name"].drop_duplicates().reset_index(drop=True)

    for idx, table_name in unique_tables.items():
        if max_pairs is not None and idx >= max_pairs:
            break

        table_name = str(table_name)
        web_df = _load_table(web_dir, table_name, dataset_suffix="::web")
        dbpedia_df = _load_table(dbpedia_dir, table_name, dataset_suffix="::dbpedia")

        pair_corr = correspondences[correspondences["table_name"] == table_name]

        evaluation = _build_indexed_evaluation(
            web_df,
            dbpedia_df,
            pair_corr,
            left_index_col="column_index_left",
            right_index_col="column_index_right",
            label_col="label",
        )

        variant_label = "T2D-SM-WH" if variant == "t2d-sm-wh" else "T2D-SM-NH"
        pair_id = f"{variant_label}:{table_name}"

        yield WDCSMBPair(pair_id=pair_id, source_df=web_df, target_df=dbpedia_df, evaluation=evaluation)


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _find_correspondence_file(split_dir: Path) -> Path:
    candidates = sorted(split_dir.glob("*correspondence*.csv"))
    if not candidates:
        raise FileNotFoundError(
            f"No correspondence CSV found in {split_dir}. Expected filename containing 'correspondence'."
        )
    if len(candidates) > 1:
        logger.warning(
            "Multiple correspondence files found in %s. Using %s.", split_dir, candidates[0]
        )
    return candidates[0]


def _pick_existing_dir(candidates: Sequence[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "None of the expected table directories exist. Tried: " + ", ".join(str(c) for c in candidates)
    )


def _load_table(directory: Path, table_name: str, dataset_suffix: str = "") -> pd.DataFrame:
    path = _locate_table_file(directory, table_name)

    if str(path).endswith((".json", ".jsonl", ".json.gz", ".jsonl.gz")):
        df = _read_json_lines(path)
    elif str(path).endswith(".csv"):
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported table format: {path.suffix}")

    df.columns = [str(col) for col in df.columns]

    dataset_name = f"{Path(table_name).stem}{dataset_suffix}"
    _attach_metadata(df, dataset_name, path)

    return df


def _locate_table_file(directory: Path, table_name: str) -> Path:
    if not directory.exists():
        raise FileNotFoundError(f"Table directory '{directory}' does not exist.")

    stem = Path(table_name).stem
    candidates = list(directory.glob(f"{stem}*"))

    for candidate in candidates:
        if _has_supported_suffix(candidate):
            logger.debug("Resolved table '%s' to %s", table_name, candidate)
            return candidate

    raise FileNotFoundError(
        f"Unable to locate table '{table_name}' in {directory}. Tried pattern '{stem}*'."
    )


def _has_supported_suffix(path: Path) -> bool:
    supported_suffixes = (".json", ".jsonl", ".json.gz", ".jsonl.gz", ".csv")
    return str(path).endswith(supported_suffixes)


def _read_json_lines(path: Path) -> pd.DataFrame:
    """Safely load line-delimited JSON without relying on pandas' C engine."""

    import gzip
    import json

    open_kwargs = {"mode": "rt", "encoding": "utf-8"}
    if str(path).endswith((".json.gz", ".jsonl.gz")):
        open_fn = gzip.open
    else:
        open_fn = open

    records: List[dict] = []
    with open_fn(path, **open_kwargs) as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSON line in %s", path)
                continue

    return pd.DataFrame(records)


def _attach_metadata(df: pd.DataFrame, dataset_name: str, source_path: Path) -> None:
    df.attrs["dataset_name"] = dataset_name
    provenance = {
        "source_path": str(source_path),
        "reader": "wdc_smb_loader",
    }
    if source_path.exists():
        provenance["file_size_bytes"] = source_path.stat().st_size
    df.attrs["provenance"] = provenance


def _build_indexed_evaluation(
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    correspondences: pd.DataFrame,
    *,
    left_index_col: str,
    right_index_col: str,
    label_col: str,
) -> pd.DataFrame:
    source_columns = list(source_df.columns)
    target_columns = list(target_df.columns)

    records = []
    for record in correspondences.itertuples(index=False):
        left_idx = getattr(record, left_index_col)
        right_idx = getattr(record, right_index_col)
        label_value = getattr(record, label_col)

        left_name = _column_from_index(source_columns, left_idx)
        right_name = _column_from_index(target_columns, right_idx)

        records.append(
            {
                "source_dataset": source_df.attrs["dataset_name"],
                "source_column": left_name,
                "target_dataset": target_df.attrs["dataset_name"],
                "target_column": right_name,
                "label": _to_bool(label_value),
            }
        )

    return pd.DataFrame(records)


def _column_from_index(columns: Sequence[str], index_value) -> str:
    try:
        idx = int(index_value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - guards malformed data
        raise ValueError(f"Column index '{index_value}' is not an integer.") from exc

    if idx < 0 or idx >= len(columns):
        raise IndexError(f"Column index {idx} out of bounds for {len(columns)} columns.")

    return str(columns[idx])


def _to_bool(value) -> bool:
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in {"1", "true", "t", "yes"}:
            return True
        if norm in {"0", "false", "f", "no"}:
            return False
    return bool(value)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _ensure_mapping_frame(
    frame: pd.DataFrame,
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
) -> pd.DataFrame:
    required_columns = ["source_dataset", "source_column", "target_dataset", "target_column", "score"]
    if frame is None or frame.empty:
        frame = pd.DataFrame(columns=required_columns)
    else:
        missing = [col for col in required_columns if col not in frame.columns]
        for col in missing:
            frame[col] = 1.0 if col == "score" else None

    frame.loc[:, "source_dataset"] = frame["source_dataset"].fillna(source_df.attrs.get("dataset_name"))
    frame.loc[:, "target_dataset"] = frame["target_dataset"].fillna(target_df.attrs.get("dataset_name"))

    frame.loc[:, "source_column"] = frame["source_column"].astype(str)
    frame.loc[:, "target_column"] = frame["target_column"].astype(str)

    return frame


def _concat_schema_mappings(frames: Iterable[pd.DataFrame], require_score: bool = True) -> pd.DataFrame:
    frames = list(frames)
    if not frames:
        columns = ["source_dataset", "source_column", "target_dataset", "target_column"]
        if require_score:
            columns.append("score")
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Command line interface
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate LLMBasedSchemaMatcher on WDC SMB.")
    parser.add_argument("--dataset-root", required=True, type=Path, help="Path to the extracted benchmark subset (e.g. SOTAB_SM_V500).")
    parser.add_argument("--task", required=True, help="Benchmark variant: 'sotab', 't2d-sm-wh', or 't2d-sm-nh'.")
    parser.add_argument("--split", default="test", help="Split to evaluate: train, valid, or test.")
    parser.add_argument("--max-pairs", type=int, default=None, help="Optional limit on number of table pairs to evaluate.")
    parser.add_argument("--complete", action="store_true", help="Treat evaluation sets as exhaustive negatives when computing metrics.")
    parser.add_argument("--openai-model", help="OpenAI chat model name (requires langchain-openai).")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the chat model.")
    parser.add_argument("--num-rows", type=int, default=5, help="Number of sample rows sent to the LLM.")
    parser.add_argument("--max-retries", type=int, default=1, help="Maximum number of retries for the LLM call.")
    parser.add_argument("--debug-artifacts", action="store_true", help="Enable LLMBasedSchemaMatcher debug artifact logging.")
    parser.add_argument("--log-level", default="INFO", help="Python logging level (e.g. INFO, DEBUG).")

    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    if not args.openai_model:
        parser.error("--openai-model is required for the CLI. For alternative providers, import run_wdc_smb_benchmark programmatically.")

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - triggered at runtime when dependency missing
        parser.error("langchain-openai is required when using --openai-model. Install with 'pip install langchain-openai'.")

    chat_model: BaseChatModel = ChatOpenAI(model=args.openai_model, temperature=args.temperature)

    matcher = LLMBasedSchemaMatcher(
        chat_model=chat_model,
        num_rows=args.num_rows,
        temperature=args.temperature,
        max_retries=args.max_retries,
        debug=args.debug_artifacts,
    )

    config = WDCBenchmarkConfig(
        dataset_root=args.dataset_root,
        task=args.task,
        split=args.split,
        max_pairs=args.max_pairs,
    )

    result = run_wdc_smb_benchmark(
        matcher,
        config,
        complete=args.complete,
    )

    overall = result["overall"]
    print(json.dumps({k: overall[k] for k in ["precision", "recall", "f1"]}, indent=2))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
