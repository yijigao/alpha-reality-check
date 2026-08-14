"""CSV ingestion and explicit data validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .models import AuditError, LoadedTrades, PolicyConfig

OPTIONAL_FIELDS = (
    "symbol",
    "stage",
    "fees",
    "slippage",
    "regime",
    "side",
    "strategy_id",
)
ALLOWED_STAGES = {"backtest", "paper", "live"}


def _utc_text(value: pd.Timestamp) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _validate_numeric(frame: pd.DataFrame, field: str) -> None:
    converted = pd.to_numeric(frame[field], errors="coerce")
    invalid = converted.isna() | ~np.isfinite(converted.to_numpy(dtype=float))
    if bool(invalid.any()):
        rows = [int(index) + 2 for index in frame.index[invalid][:10]]
        raise AuditError(f"INVALID_{field.upper()} at CSV rows {rows}")
    frame[field] = converted.astype(float)


def load_csv(path: Path, config: PolicyConfig) -> LoadedTrades:
    if not path.is_file():
        raise AuditError(f"INPUT_NOT_FOUND: {path.name}")
    try:
        raw = pd.read_csv(path, encoding="utf-8")
    except (UnicodeDecodeError, pd.errors.ParserError, OSError) as exc:
        raise AuditError(f"INVALID_CSV: {exc}") from exc

    mapped = config.columns.as_dict()
    required_sources = [mapped["exit_time"], mapped["pnl"]]
    missing_required = [name for name in required_sources if name not in raw.columns]
    if missing_required:
        raise AuditError(f"MISSING_REQUIRED_COLUMNS: {missing_required}")
    duplicate_mapping = len(set(mapped.values())) != len(mapped.values())
    if duplicate_mapping:
        raise AuditError("COLUMN_MAPPING_VALUES_MUST_BE_UNIQUE")
    if len(raw) < 2:
        raise AuditError("INSUFFICIENT_TRADES: at least two trades are required")
    duplicate_count = int(raw.duplicated(keep=False).sum())
    if duplicate_count:
        raise AuditError(f"DUPLICATE_ROWS: {duplicate_count} rows are duplicated")

    selected: dict[str, Any] = {
        logical: raw[source]
        for logical, source in mapped.items()
        if source in raw.columns
    }
    frame = pd.DataFrame(selected)
    timestamps = pd.to_datetime(
        frame["exit_time"], errors="coerce", utc=True, format="mixed"
    )
    invalid_time = timestamps.isna()
    if bool(invalid_time.any()):
        rows = [int(index) + 2 for index in frame.index[invalid_time][:10]]
        raise AuditError(f"INVALID_EXIT_TIME at CSV rows {rows}")
    frame["exit_time"] = timestamps
    _validate_numeric(frame, "pnl")
    for field in ("fees", "slippage"):
        if field in frame.columns:
            _validate_numeric(frame, field)

    warnings: list[str] = []
    for field in OPTIONAL_FIELDS:
        if field not in frame.columns:
            warnings.append(f"{field.upper()}_ANALYSIS_NOT_AVAILABLE")

    for field in ("symbol", "stage", "regime", "side", "strategy_id"):
        if field not in frame.columns:
            continue
        text = frame[field].astype("string").str.strip()
        missing = text.isna() | (text == "")
        if bool(missing.any()):
            warnings.append(
                f"{field.upper()}_MISSING_FOR_{int(missing.sum())}_TRADES; "
                "THOSE_TRADES_ARE_EXCLUDED_FROM_THIS_DIMENSION_ONLY"
            )
            text = text.mask(missing)
        frame[field] = text

    if "stage" in frame.columns:
        frame["stage"] = frame["stage"].str.lower()
        invalid_stage = frame["stage"].notna() & ~frame["stage"].isin(ALLOWED_STAGES)
        if bool(invalid_stage.any()):
            values = sorted(
                str(value) for value in frame.loc[invalid_stage, "stage"].unique()
            )
            raise AuditError(f"INVALID_STAGE_VALUES: {values}")

    frame["_source_order"] = np.arange(len(frame), dtype=int)
    frame = frame.sort_values(["exit_time", "_source_order"], kind="stable")
    frame = frame.drop(columns=["_source_order"]).reset_index(drop=True)
    input_summary = {
        "source_name": path.name,
        "trade_count": int(len(frame)),
        "columns_present": sorted(str(column) for column in frame.columns),
        "first_exit_time": _utc_text(frame["exit_time"].iloc[0]),
        "last_exit_time": _utc_text(frame["exit_time"].iloc[-1]),
        "duplicate_rows": 0,
    }
    return LoadedTrades(frame=frame, warnings=warnings, input_summary=input_summary)
