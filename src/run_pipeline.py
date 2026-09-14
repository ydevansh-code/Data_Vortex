"""
run_pipeline.py
===============
Single-command entry point that runs the full Social Engine pipeline:

    Step 1: Profile raw data     (ydata-profiling → reports/raw_profile.html)
    Step 2: Clean data           (src/clean_data.py → data/cleaned/)
    Step 3: Profile cleaned data (ydata-profiling → reports/cleaned_profile.html)

Usage
-----
    python src/run_pipeline.py
    python src/run_pipeline.py --skip-profile   # skip ydata-profiling (faster)
"""

import argparse
import subprocess
import sys


def run(cmd: list, label: str) -> None:
    """
    Runs a subprocess command, streaming output to stdout.

    Parameters
    ----------
    cmd : list of str
        Command and arguments to execute.
    label : str
        Human-readable step label for logging.

    Returns
    -------
    None

    Raises
    ------
    SystemExit
        If the subprocess exits with a non-zero code.
    """
    print(f"\n{'='*60}")
    print(f"  STEP: {label}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"[ERROR] '{label}' failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    """Orchestrates the full cleaning + profiling pipeline."""
    parser = argparse.ArgumentParser(description="Run the full Data Vortex pipeline.")
    parser.add_argument("--skip-profile", action="store_true",
                        help="Skip ydata-profiling reports (use when profiling is slow).")
    args = parser.parse_args()

    python = sys.executable

    if not args.skip_profile:
        run([python, "src/profile_data.py", "--stage", "raw"], "Raw data profiling")

    run([python, "src/run_cleaning.py"], "Data cleaning pipeline")

    if not args.skip_profile:
        run([python, "src/profile_data.py", "--stage", "cleaned"], "Cleaned data profiling")

    print("\n[pipeline] All steps complete.")
    print("  Raw profile    → reports/raw_profile.html")
    print("  Cleaned data   → data/cleaned/users_clean.csv, posts_clean.json, merged_summary.csv")
    print("  Cleaned profile→ reports/cleaned_profile.html")
    print("  Change log     → docs/change_log.csv")


if __name__ == "__main__":
    main()
