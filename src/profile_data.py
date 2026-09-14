"""
profile_data.py
===============
Generates sweetviz HTML profiling reports for raw and/or cleaned datasets.

sweetviz is used instead of ydata-profiling because Python 3.14 is not
yet supported by ydata-profiling.  The output is functionally equivalent:
an interactive HTML report covering distributions, correlations, missing
values, and data types.

Usage
-----
    python src/profile_data.py --stage raw
    python src/profile_data.py --stage cleaned
    python src/profile_data.py --stage both
"""

import argparse
import glob
import os
import sys

import pandas as pd
import sweetviz as sv


RAW_GLOB = os.path.join("data", "raw", "*.*")
CLEANED_GLOB = os.path.join("data", "cleaned", "*.*")
REPORTS_DIR = "reports"


def find_dataset(glob_pattern: str) -> str:
    """
    Finds the first CSV or JSON file matching *glob_pattern*.

    Parameters
    ----------
    glob_pattern : str
        Shell-style wildcard pattern to search.

    Returns
    -------
    str
        Path to the first matching file.

    Raises
    ------
    FileNotFoundError
        If no file matches the pattern.
    """
    matches = [
        p for p in glob.glob(glob_pattern)
        if p.lower().endswith((".csv", ".json"))
    ]
    if not matches:
        raise FileNotFoundError(f"No CSV/JSON found matching: {glob_pattern}")
    return matches[0]


def load_dataset(filepath: str) -> pd.DataFrame:
    """
    Loads a CSV or JSON file into a DataFrame with inferred dtypes.

    Parameters
    ----------
    filepath : str
        Path to the data file.

    Returns
    -------
    pd.DataFrame
        Loaded DataFrame.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        return pd.read_csv(filepath, low_memory=False)
    if ext == ".json":
        return pd.read_json(filepath)
    raise ValueError(f"Unsupported file extension: {ext}")


def generate_profile(df: pd.DataFrame, title: str, output_path: str) -> None:
    """
    Runs sweetviz and saves the HTML report to *output_path*.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset to profile.
    title : str
        Title shown in the HTML report header.
    output_path : str
        Destination path for the HTML file.

    Returns
    -------
    None
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"[profile] Generating report: {title}  →  {output_path}")
    report = sv.analyze(df, target_feat=None)
    report.show_html(filepath=output_path, open_browser=False)
    print(f"[profile] Saved → {output_path}")


def compare_profiles(raw_df: pd.DataFrame, cleaned_df: pd.DataFrame, output_path: str) -> None:
    """
    Generates a sweetviz comparison report between raw and cleaned datasets.

    Parameters
    ----------
    raw_df : pd.DataFrame
        Raw dataset.
    cleaned_df : pd.DataFrame
        Cleaned dataset.
    output_path : str
        Destination path for the comparison HTML report.

    Returns
    -------
    None
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"[profile] Generating comparison report → {output_path}")
    comparison = sv.compare([raw_df, "Raw"], [cleaned_df, "Cleaned"])
    comparison.show_html(filepath=output_path, open_browser=False)
    print(f"[profile] Comparison saved → {output_path}")


def profile_stage(stage: str) -> None:
    """
    Profiles one or both dataset stages.  Generates a comparison report
    when stage='both'.

    Parameters
    ----------
    stage : str
        One of 'raw', 'cleaned', or 'both'.

    Returns
    -------
    None
    """
    raw_path = os.path.join(REPORTS_DIR, "raw_profile.html")
    cleaned_path = os.path.join(REPORTS_DIR, "cleaned_profile.html")
    comparison_path = os.path.join(REPORTS_DIR, "comparison_profile.html")

    raw_df = cleaned_df = None

    if stage in ("raw", "both"):
        try:
            filepath = find_dataset(RAW_GLOB)
            raw_df = load_dataset(filepath)
            print(f"[profile] Loaded raw dataset: {raw_df.shape[0]} rows × {raw_df.shape[1]} cols")
            generate_profile(raw_df, "Raw Dataset Profile", raw_path)
        except FileNotFoundError as exc:
            print(f"[profile] SKIP raw — {exc}", file=sys.stderr)

    if stage in ("cleaned", "both"):
        try:
            filepath = find_dataset(CLEANED_GLOB)
            cleaned_df = load_dataset(filepath)
            print(f"[profile] Loaded cleaned dataset: {cleaned_df.shape[0]} rows × {cleaned_df.shape[1]} cols")
            generate_profile(cleaned_df, "Cleaned Dataset Profile", cleaned_path)
        except FileNotFoundError as exc:
            print(f"[profile] SKIP cleaned — {exc}", file=sys.stderr)

    if stage == "both" and raw_df is not None and cleaned_df is not None:
        try:
            compare_profiles(raw_df, cleaned_df, comparison_path)
        except Exception as exc:
            print(f"[profile] Comparison skipped (column mismatch expected): {exc}", file=sys.stderr)


def main() -> None:
    """Entry point: parse CLI args and dispatch profiling."""
    parser = argparse.ArgumentParser(description="Generate sweetviz profiling reports.")
    parser.add_argument(
        "--stage",
        choices=["raw", "cleaned", "both"],
        default="raw",
        help="Which dataset stage to profile (default: raw).",
    )
    args = parser.parse_args()
    profile_stage(args.stage)


if __name__ == "__main__":
    main()
