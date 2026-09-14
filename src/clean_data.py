"""
clean_data.py
=============
Cleaning pipeline for the Social Engine / Data Vortex hackathon dataset.

Pipeline stages (in order):
  1. load        — read raw data without coercing types
  2. validate    — assert schema expectations, log surprises
  3. placeholders — replace sentinel/placeholder strings with NaN
  4. missing     — impute or flag remaining missing values (per-column strategy)
  5. standardize — enforce uniform formats: dates, casing, units, categories
  6. deduplicate — remove exact and near-duplicate rows, log every drop
  7. export      — write cleaned CSV to data/cleaned/ and flush the change log

DEPRECATED CLI: This is a single-file cleaner when run directly. Use src/run_cleaning.py 
as the main entry point which uses this file as a utility library.

Run
---
    python src/clean_data.py [--input PATH] [--output PATH]

All decisions are logged to docs/decisions.md (updated in-place).
All transformations are appended to docs/change_log.csv.
"""

import argparse
import glob
import logging
import os
import sys
import textwrap
from datetime import datetime

import re

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Configuration — paths are relative so the repo is portable
# ---------------------------------------------------------------------------
RAW_GLOB = os.path.join("data", "raw", "*.*")
DEFAULT_OUTPUT = os.path.join("data", "cleaned", "cleaned_dataset.csv")
CHANGE_LOG_PATH = os.path.join("docs", "change_log.csv")
DECISIONS_PATH = os.path.join("docs", "decisions.md")

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Change-log helper
# ---------------------------------------------------------------------------
_CHANGE_LOG_ROWS: list[dict] = []


def _record(stage: str, column: str, method: str, rows_affected: int, detail: str) -> None:
    """
    Appends one entry to the in-memory change log.

    Parameters
    ----------
    stage : str
        Pipeline stage name (e.g. 'missing', 'standardize').
    column : str
        Column affected, or 'ALL' for row-level operations.
    method : str
        Short name of the transformation applied.
    rows_affected : int
        Number of cells/rows changed.
    detail : str
        Human-readable description of what was done.

    Returns
    -------
    None
    """
    _CHANGE_LOG_ROWS.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stage": stage,
        "column": column,
        "method": method,
        "rows_affected": rows_affected,
        "detail": detail,
    })
    log.info("[%s | %s] %s — %d rows affected", stage, column, method, rows_affected)


def _flush_change_log() -> None:
    """Writes accumulated change-log rows to CHANGE_LOG_PATH (CSV, append-safe)."""
    os.makedirs(os.path.dirname(CHANGE_LOG_PATH), exist_ok=True)
    new_df = pd.DataFrame(_CHANGE_LOG_ROWS)
    if os.path.exists(CHANGE_LOG_PATH):
        existing = pd.read_csv(CHANGE_LOG_PATH)
        new_df = pd.concat([existing, new_df], ignore_index=True)
    new_df.to_csv(CHANGE_LOG_PATH, index=False)
    log.info("Change log written → %s", CHANGE_LOG_PATH)


# ---------------------------------------------------------------------------
# Stage 1 — Load
# ---------------------------------------------------------------------------
def load_raw(filepath: str) -> pd.DataFrame:
    """
    Reads the raw dataset without coercing types so corruption is visible.

    Parameters
    ----------
    filepath : str
        Path to a CSV or JSON file.

    Returns
    -------
    pd.DataFrame
        All columns read as string/object dtype.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(filepath, dtype=str, keep_default_na=False)
    elif ext == ".json":
        df = pd.read_json(filepath, dtype=False)
        df = df.astype(str).replace("nan", "")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    log.info("Loaded: %s  (%d rows × %d cols)", filepath, *df.shape)
    _record("load", "ALL", "read_file", df.shape[0], f"Loaded {filepath}: {df.shape[0]} rows, {df.shape[1]} cols")
    return df


# ---------------------------------------------------------------------------
# Stage 2 — Validate
# ---------------------------------------------------------------------------
def validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Asserts basic schema expectations and logs any surprises.
    Does NOT modify the DataFrame — purely observational.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to validate.

    Returns
    -------
    pd.DataFrame
        Unchanged DataFrame (pass-through).
    """
    dup_count = df.duplicated().sum()
    _record("validate", "ALL", "check_duplicates", int(dup_count),
            f"Found {dup_count} exact duplicate rows before cleaning")

    for col in df.columns:
        null_n = df[col].replace("", np.nan).isna().sum()
        if null_n > 0:
            pct = null_n / len(df) * 100
            _record("validate", col, "check_missing", int(null_n),
                    f"{null_n} nulls ({pct:.1f}%) detected before imputation")

    log.info("Validation complete — %d cols checked", df.shape[1])
    return df


# ---------------------------------------------------------------------------
# Stage 3 — Replace placeholder strings with NaN
# ---------------------------------------------------------------------------
PLACEHOLDER_VALUES = {
    "", "n/a", "na", "n.a.", "none", "null", "nan", "?", "-", "–",
    "unknown", "missing", "not available", "tbd", "#n/a", "nil",
}


def replace_placeholders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replaces common sentinel/placeholder strings with proper NaN.

    Justification: These strings are data-entry artifacts, not real values.
    Standardising them to NaN ensures downstream imputation logic works
    uniformly regardless of how the original entry was made.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame (all object dtypes).

    Returns
    -------
    pd.DataFrame
        DataFrame with placeholders converted to np.nan.
    """
    before_null = df.isna().sum().sum()
    df = df.replace(
        to_replace=r"^\s*(" + "|".join(re.escape(v) for v in PLACEHOLDER_VALUES) + r")\s*$",
        value=np.nan,
        regex=True,
    )
    after_null = df.isna().sum().sum()
    new_nulls = int(after_null - before_null)
    _record("placeholders", "ALL", "replace_placeholder_strings", new_nulls,
            f"Converted {new_nulls} placeholder strings to NaN across all columns")
    return df


# ---------------------------------------------------------------------------
# Stage 4 — Handle missing values (column-by-column strategy)
# ---------------------------------------------------------------------------
def handle_missing(df: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    """
    Applies per-column imputation or flagging strategies.

    Strategy is determined by column role:
      - Numeric columns  → median imputation (robust to outliers)
      - Categorical/text → mode imputation only if mode frequency ≥ 30%,
                           otherwise leave null and flag with a sentinel column
      - Date columns     → left null; flagged for downstream review
      - ID / key columns → left null; logged

    Justification for median (not mean) on numerics:
      Median is resistant to the skewed distributions and outliers that
      commonly appear in corrupted datasets.  Mean would propagate outlier
      bias into imputed values.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame post-placeholder replacement.
    config : dict, optional
        Override strategy per column: {col_name: 'median'|'mode'|'drop'|'flag'}.

    Returns
    -------
    pd.DataFrame
        DataFrame with missing values handled.
    """
    config = config or {}

    for col in df.columns:
        null_mask = df[col].isna()
        n_null = null_mask.sum()
        if n_null == 0:
            continue

        strategy = config.get(col)

        # --- attempt numeric coercion to decide strategy
        numeric_test = pd.to_numeric(df[col], errors="coerce")
        is_numeric = (numeric_test.notna().sum() / max(df[col].notna().sum(), 1)) > 0.7

        if strategy == "drop":
            before_len = len(df)
            df = df[~null_mask].copy()
            _record("missing", col, "drop_null_rows", before_len - len(df),
                    f"Dropped {before_len - len(df)} rows with null in '{col}' (explicit config)")

        elif strategy == "flag":
            df[f"{col}_was_null"] = null_mask.astype(int)
            _record("missing", col, "flag_null", int(n_null),
                    f"Added '{col}_was_null' indicator column; values left null")

        elif is_numeric or strategy == "median":
            numeric_col = numeric_test.copy()
            med = numeric_col.median()
            df.loc[null_mask, col] = str(med)
            _record("missing", col, "median_impute", int(n_null),
                    f"Imputed {n_null} nulls with median={med:.4g} — chosen because column is numeric and median is outlier-robust")

        else:
            # Categorical / text
            mode_result = df[col].mode(dropna=True)
            if len(mode_result) > 0:
                mode_val = mode_result.iloc[0]
                mode_freq = (df[col] == mode_val).sum() / df[col].notna().sum()
                if mode_freq >= 0.30:
                    df.loc[null_mask, col] = mode_val
                    _record("missing", col, "mode_impute", int(n_null),
                            f"Imputed {n_null} nulls with mode='{mode_val}' (freq={mode_freq:.1%}) — "
                            "chosen because dominant category makes mode meaningful")
                else:
                    df[f"{col}_was_null"] = null_mask.astype(int)
                    _record("missing", col, "flag_null_low_mode", int(n_null),
                            f"Left {n_null} nulls; mode freq {mode_freq:.1%} < 30% threshold — "
                            "imputing would introduce significant fabrication risk")
            else:
                _record("missing", col, "no_imputation", int(n_null),
                        f"Left {n_null} nulls — no mode available, cannot impute without fabricating")

    return df


# ---------------------------------------------------------------------------
# Stage 5 — Standardise formats
# ---------------------------------------------------------------------------


def _standardise_dates(series: pd.Series, col: str) -> pd.Series:
    """
    Coerces a column to ISO 8601 date format (YYYY-MM-DD).

    Tries multiple common input formats and falls back to pd.to_datetime
    with infer_datetime_format as a last resort.

    Parameters
    ----------
    series : pd.Series
        Date-like column (object dtype).
    col : str
        Column name (for logging).

    Returns
    -------
    pd.Series
        Dates as 'YYYY-MM-DD' strings; unparseable values become NaN.
    """
    FORMATS = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
        "%d %B %Y", "%B %d, %Y", "%Y/%m/%d",
    ]
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=False)
    for fmt in FORMATS:
        mask = parsed.isna() & series.notna()
        if mask.any():
            attempt = pd.to_datetime(series[mask], format=fmt, errors="coerce")
            parsed[mask] = attempt

    converted = parsed.notna().sum()
    _record("standardize", col, "date_to_iso8601", int(converted),
            f"Converted {converted} date values to YYYY-MM-DD ISO 8601")
    return parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), other=np.nan)


def _standardise_text_casing(series: pd.Series, col: str) -> pd.Series:
    """
    Strips whitespace and applies title-case to text columns.

    Title-case is preferred for names/labels; lower-case applied for
    identifiers and category codes.

    Parameters
    ----------
    series : pd.Series
    col : str

    Returns
    -------
    pd.Series
    """
    cleaned = series.str.strip()
    if any(kw in col.lower() for kw in ("name", "city", "country", "region", "title")):
        result = cleaned.str.title()
    else:
        result = cleaned.str.lower()
    changed = (result != cleaned).sum()
    _record("standardize", col, "normalise_casing", int(changed),
            f"Normalised casing for {changed} values in '{col}'")
    return result


def _standardise_numeric(series: pd.Series, col: str) -> pd.Series:
    """
    Strips non-numeric characters (currency symbols, commas, units) and coerces to float.

    Parameters
    ----------
    series : pd.Series
    col : str

    Returns
    -------
    pd.Series
        Float dtype series.
    """
    stripped = series.astype(str).str.replace(r"[,$€£%\s]", "", regex=True)
    coerced = pd.to_numeric(stripped, errors="coerce")
    converted = coerced.notna().sum()
    _record("standardize", col, "coerce_numeric", int(converted),
            f"Coerced {converted} values to numeric in '{col}', removing currency/unit symbols")
    return coerced


def standardise(df: pd.DataFrame, date_cols: list | None = None,
                numeric_cols: list | None = None, text_cols: list | None = None) -> pd.DataFrame:
    """
    Enforces uniform formats across date, numeric, and text columns.

    Column lists are auto-detected if not provided:
      - Date cols: columns whose name contains 'date', 'time', 'dob', 'year'
      - Numeric cols: columns with > 70% numeric values
      - Text cols: remaining object columns

    Parameters
    ----------
    df : pd.DataFrame
    date_cols : list of str, optional
    numeric_cols : list of str, optional
    text_cols : list of str, optional

    Returns
    -------
    pd.DataFrame
    """
    DATE_KEYWORDS = ("date", "time", "dob", "year", "month", "day")
    NUMERIC_KEYWORDS = ("age", "salary", "income", "amount", "price", "score", "count", "num", "qty")

    if date_cols is None:
        date_cols = [c for c in df.columns if any(kw in c.lower() for kw in DATE_KEYWORDS)]
    if numeric_cols is None:
        numeric_cols = [
            c for c in df.columns
            if c not in date_cols
            and pd.to_numeric(df[c], errors="coerce").notna().sum() / max(df[c].notna().sum(), 1) > 0.70
        ] + [c for c in df.columns if any(kw in c.lower() for kw in NUMERIC_KEYWORDS) and c not in date_cols]
        numeric_cols = list(dict.fromkeys(numeric_cols))  # dedupe, preserve order
    if text_cols is None:
        text_cols = [c for c in df.select_dtypes(include="object").columns
                     if c not in date_cols and c not in numeric_cols]

    for col in date_cols:
        if col in df.columns:
            df[col] = _standardise_dates(df[col].astype(str).replace("nan", np.nan), col)

    for col in numeric_cols:
        if col in df.columns:
            df[col] = _standardise_numeric(df[col], col)

    for col in text_cols:
        if col in df.columns and df[col].dtype == object:
            df[col] = _standardise_text_casing(df[col].astype(str).replace("nan", np.nan), col)

    return df


# ---------------------------------------------------------------------------
# Stage 6 — Deduplicate
# ---------------------------------------------------------------------------
def deduplicate(df: pd.DataFrame, subset: list | None = None) -> pd.DataFrame:
    """
    Removes exact duplicate rows, logging every drop.

    'Exact' means all selected columns are identical.
    Keeps the first occurrence to preserve original record order.

    Parameters
    ----------
    df : pd.DataFrame
    subset : list of str, optional
        Columns to consider for duplication check.
        If None, all columns are used.

    Returns
    -------
    pd.DataFrame
        DataFrame with duplicates removed.
    """
    before = len(df)
    df = df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)
    dropped = before - len(df)
    _record("deduplicate", "ALL", "drop_exact_duplicates", dropped,
            f"Removed {dropped} exact duplicate rows (kept first occurrence); "
            f"{len(df)} rows remain")
    return df


# ---------------------------------------------------------------------------
# Stage 7 — Export
# ---------------------------------------------------------------------------
def export(df: pd.DataFrame, output_path: str) -> None:
    """
    Writes the cleaned DataFrame to a CSV file.

    Parameters
    ----------
    df : pd.DataFrame
        Fully cleaned DataFrame.
    output_path : str
        Destination path.

    Returns
    -------
    None
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    _record("export", "ALL", "write_csv", len(df),
            f"Exported {len(df)} rows × {df.shape[1]} cols → {output_path}")
    log.info("Cleaned dataset saved → %s", output_path)


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------
def run_pipeline(input_path: str | None = None, output_path: str = DEFAULT_OUTPUT) -> pd.DataFrame:
    """
    Executes the full cleaning pipeline in order:
      load → validate → placeholders → missing → standardise → deduplicate → export.

    Parameters
    ----------
    input_path : str, optional
        Path to the raw data file.  Auto-detected from data/raw/ if None.
    output_path : str
        Destination for the cleaned CSV.

    Returns
    -------
    pd.DataFrame
        Final cleaned DataFrame.
    """
    if input_path is None:
        matches = [p for p in glob.glob(RAW_GLOB) if p.lower().endswith((".csv", ".json"))]
        if not matches:
            raise FileNotFoundError("No CSV/JSON found in data/raw/")
        input_path = matches[0]

    df = load_raw(input_path)
    df = validate(df)
    df = replace_placeholders(df)
    df = handle_missing(df)
    df = standardise(df)
    df = deduplicate(df)
    export(df, output_path)
    _flush_change_log()
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """Parses CLI arguments and invokes run_pipeline."""
    parser = argparse.ArgumentParser(description="Clean the Social Engine dataset.")
    parser.add_argument("--input", default=None, help="Path to raw data file (auto-detected if omitted).")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV path.")
    args = parser.parse_args()
    run_pipeline(input_path=args.input, output_path=args.output)


if __name__ == "__main__":
    main()
