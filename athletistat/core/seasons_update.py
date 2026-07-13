import os
import glob
import pandas as pd
from datetime import datetime
from athletistat.console import cprint, header, divider, success, warn, error, info, step, Colors, Symbols


class SeasonsUpdate:
    """Updates the combined seasons dataset by removing and replacing data for a given year.

    Workflow:
        1. (Optional) Run the full data pipeline — scrape, preprocess, generate — for the
           target year so that a fresh per-year dataset exists.
        2. Load the current combined seasons CSV.
        3. Drop all rows whose ``season`` column matches the target year.
        4. Append the rows from the per-year dataset for the target year.
        5. Save the updated combined CSV.
    """

    DATASET_DIR = "data/datasets/seasons"

    def __init__(self, year: int | None = None, generate: bool = True):
        """
        Initializes the SeasonsUpdate instance.

        Args:
            year (int | None): The year to update. Defaults to the current year.
            generate (bool): If True, run the full pipeline (scrape → preprocess →
                generate) before replacing. If False, assume the per-year dataset
                already exists on disk.
        """
        self.year = year if year is not None else datetime.now().year
        self.generate = generate

        # Resolve the combined file (glob pattern covers any year-range suffix)
        self.combined_file = self._find_combined_file()
        self.year_file = os.path.join(
            self.DATASET_DIR, f"{self.year}_track_field_performances.csv"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_combined_file(self) -> str | None:
        """Locates the combined seasons CSV file.

        Returns:
            str | None: Absolute or relative path to the combined file, or None.
        """
        pattern = os.path.join(self.DATASET_DIR, "combined_track_field_performances_*.csv")
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
        return None

    def _run_pipeline(self):
        """Runs scraper → preprocessor → generator for the target year.

        Returns:
            bool: True if the pipeline completed without raising.
        """
        from athletistat.core.scraper import Scraper
        from athletistat.core.preprocessing import Preprocessor
        from athletistat.core.generator import DatasetGenerator

        step(f"[1/3] Scraping data for {self.year}...")
        Scraper(mode="seasons").run(year=self.year)

        step(f"[2/3] Preprocessing data...")
        Preprocessor(mode="seasons").run()

        step(f"[3/3] Generating per-year dataset...")
        DatasetGenerator(mode="seasons").run()

        return True

    def _load_csv(self, filepath: str) -> pd.DataFrame | None:
        """Safely loads a CSV file into a DataFrame.

        Args:
            filepath (str): Path to the CSV.

        Returns:
            pd.DataFrame | None: The loaded DataFrame, or None on failure.
        """
        try:
            df = pd.read_csv(filepath)
            return df
        except FileNotFoundError:
            error(f"File not found: {filepath}")
            return None
        except Exception as e:
            error(f"Error reading {filepath}: {e}")
            return None

    def _delete_year_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """Removes all rows for ``self.year`` from the DataFrame.

        Args:
            df (pd.DataFrame): The combined dataset.

        Returns:
            pd.DataFrame: Filtered DataFrame without the target year's rows.
        """
        if "season" not in df.columns:
            warn("'season' column not found in combined dataset — cannot filter by year.")
            return df

        before = len(df)
        df = df[df["season"] != self.year].reset_index(drop=True)
        removed = before - len(df)
        info(f"Removed {removed:,} rows for season {self.year} (was {before:,}, now {len(df):,}).")
        return df

    def _append_year_data(self, combined_df: pd.DataFrame, year_df: pd.DataFrame) -> pd.DataFrame:
        """Appends the new year data to the combined DataFrame.

        Args:
            combined_df (pd.DataFrame): The combined dataset (year already removed).
            year_df (pd.DataFrame): The fresh per-year dataset.

        Returns:
            pd.DataFrame: Merged DataFrame.
        """
        merged = pd.concat([combined_df, year_df], ignore_index=True)
        info(f"Appended {len(year_df):,} rows for {self.year} → combined total: {len(merged):,}.")
        return merged

    def _save_combined(self, df: pd.DataFrame):
        """Saves the updated combined dataset, updating the filename year range.

        Args:
            df (pd.DataFrame): The final combined DataFrame.
        """
        if "season" in df.columns:
            valid = df["season"].dropna()
            if not valid.empty:
                min_yr = int(valid.min())
                max_yr = int(valid.max())
            else:
                min_yr = max_yr = self.year
        else:
            min_yr = max_yr = self.year

        output_filename = os.path.join(
            self.DATASET_DIR,
            f"combined_track_field_performances_{min_yr}_{max_yr}.csv",
        )

        # Remove old combined file if it differs from the new name
        if self.combined_file and self.combined_file != output_filename and os.path.exists(self.combined_file):
            os.remove(self.combined_file)
            info(f"Removed old combined file: {self.combined_file}")

        df.to_csv(output_filename, index=False)
        self.combined_file = output_filename
        success(f"Saved updated combined dataset → {output_filename}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self):
        """Executes the full seasons-update workflow.

        Steps:
            1. Optionally generate fresh data for the target year.
            2. Load the combined dataset.
            3. Remove all rows for the target year.
            4. Load the per-year dataset and append it.
            5. Save the updated combined CSV.
        """
        header(f"Seasons Update  —  {self.year}")

        # Step 1: Optionally run the pipeline
        if self.generate:
            info(f"Generating fresh data for {self.year} (full pipeline)...")
            divider()
            try:
                self._run_pipeline()
            except Exception as e:
                error(f"Pipeline failed: {e}")
                return
            divider()
        else:
            info(f"Skipping generation — expecting existing dataset for {self.year}.")

        # Step 2: Load combined dataset
        if self.combined_file is None:
            error(
                "No combined seasons dataset found. "
                "Run the full pipeline first with: --create-dataset seasons --combine"
            )
            return

        info(f"Loading combined dataset: {self.combined_file}")
        combined_df = self._load_csv(self.combined_file)
        if combined_df is None:
            return

        rows_before = len(combined_df)

        # Step 3: Remove target year
        combined_df = self._delete_year_records(combined_df)

        # Step 4: Load and append year dataset
        if not os.path.exists(self.year_file):
            error(f"Per-year dataset not found: {self.year_file}")
            return

        info(f"Loading year dataset: {self.year_file}")
        year_df = self._load_csv(self.year_file)
        if year_df is None:
            return

        combined_df = self._append_year_data(combined_df, year_df)

        rows_after = len(combined_df)
        delta = rows_after - rows_before
        delta_str = f"+{delta:,}" if delta >= 0 else f"{delta:,}"

        # Step 5: Save
        self._save_combined(combined_df)

        divider()
        info(f"Rows before: {rows_before:,}  |  Rows after: {rows_after:,}  |  Δ {delta_str}")
        success(f"Seasons update for {self.year} complete!")