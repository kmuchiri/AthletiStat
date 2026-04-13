import os
import glob
import pandas as pd

class DatasetGenerator:
    """Generates and combines track and field datasets from processed CSV files."""
    def __init__(self, mode="both"):
        """
        Initializes the dataset generator with the specific running mode.
        
        Args:
            mode (str): "seasons", "all-time", or "both". Defaults to "both".
        """
        self.mode = mode

    def generate_datasets(self, mode):
        """
        Generates and combines track and field datasets from processed CSVs for the given mode.
        
        Args:
            mode (str): "seasons" or "all-time".

        Returns:
            None
        """
        combined_dir = f"{mode}/processing/combined"
        output_dataset_dir = f"{mode}/datasets"
        os.makedirs(output_dataset_dir, exist_ok=True)

        if mode == "seasons":
            if not os.path.exists(combined_dir):
                print(f"Directory {combined_dir} does not exist.")
                return

            year_dirs = [d for d in os.listdir(combined_dir) if os.path.isdir(os.path.join(combined_dir, d))]
            for year in year_dirs:
                year_path = os.path.join(combined_dir, year)
                csv_files = [f for f in os.listdir(year_path) if f.endswith(".csv")]
                all_dataframes = []
                
                # Read files in folder
                for file in csv_files:
                    file_path = os.path.join(year_path, file)
                    try:
                        df = pd.read_csv(file_path)
                        all_dataframes.append(df)
                    except Exception as e:
                        print(f"Error reading {file}: {e}")
                        
                # Combine and save
                if all_dataframes:
                    combined_df = pd.concat(all_dataframes, ignore_index=True)
                    output_filename = os.path.join(output_dataset_dir, f"{year}_track_field_performances.csv")
                    
                    combined_df.to_csv(output_filename, index=False)
                    print(f"Success: Saved {year} data to {output_filename}")
                else:
                    print(f"No CSV files found in {year_path}")
        
        else:
            if not os.path.exists(combined_dir):
                print(f"Directory {combined_dir} does not exist.")
                return

            # List all CSV files
            csv_files = [f for f in os.listdir(combined_dir) if f.endswith(".csv")]

            # Load and concatenate
            all_dataframes = []
            for file in csv_files:
                try:
                    df = pd.read_csv(os.path.join(combined_dir, file))
                    all_dataframes.append(df)
                except Exception as e:
                    print(f"Error reading {file}: {e}")
            if all_dataframes:
                # Combine into a single DataFrame
                combined_df = pd.concat(all_dataframes, ignore_index=True)
                combined_df.drop_duplicates(inplace=True)

                # Save to a new CSV
                output_filename = os.path.join(output_dataset_dir, "top_track_field_performances_all_time.csv")
                combined_df.to_csv(output_filename, index=False)
                print(f"Combined CSV saved as {output_filename}" )
            else:
                print(f"No CSV files found in {combined_dir}")

    def combine_seasons(self):
        """
        Combines all available season datasets into a single aggregated CSV file covering all years.
        
        Returns:
            None
        """
        dataset_dir = "seasons/datasets"
        processed_dir = "seasons/processing/combined"

        if not os.path.exists(dataset_dir) or not os.path.exists(processed_dir):
            print(f"Directories {dataset_dir} or {processed_dir} do not exist.")
            return

        # List CSV files directly inside the Year folder
        csv_files = [f for f in os.listdir(dataset_dir) if f.endswith(".csv")]
        all_dataframes = []

        try:
            min_year = min(os.listdir(processed_dir))
            max_year = max(os.listdir(processed_dir))
        except ValueError:
            print(f"No directories found in {processed_dir}")
            return

        # Loop through files and read them
        for file in csv_files:
            file_path = os.path.join(dataset_dir, file)
            try:
                df = pd.read_csv(file_path)
                all_dataframes.append(df)
            except Exception as e:
                print(f"Error reading {file}: {e}")

        # Combine and Save
        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            output_filename = os.path.join(dataset_dir, f"combined_track_field_performances_{min_year}_{max_year}.csv")
            combined_df.to_csv(output_filename, index=False)
            print(f"Success: Saved data to {output_filename}")
        else:
            print(f"No CSV files found in {dataset_dir}")

    def run(self, combine=False):
        """
        Executes dataset generation for 'seasons', 'all-time', or both, optionally combining seasons.
        
        Args:
            combine (bool): Whether to combine season datasets into one. Defaults to False.

        Returns:
            None
        """
        if self.mode in ["seasons", "both"]:
            self.generate_datasets("seasons")
            
        if self.mode in ["all-time", "both"]:
            self.generate_datasets("all-time")

        if combine and self.mode in ["seasons", "both"]:
            self.combine_seasons()

class DatasetSplitter:
    """Splits unified track and field datasets into more granular subsets by event type, discipline, and gender."""
    def __init__(self, mode="both"):
        """
        Initializes the dataset splitter with the targeted dataset mode.
        
        Args:
            mode (str): "seasons", "all-time", or "both". Defaults to "both".
        """
        self.mode = mode

    def get_filename_with_years(self, base_name, df, is_seasons):
        """
        Generates a filename dynamically including the min and max year if applicable.
        
        Args:
            base_name (str): Base filename.
            df (pd.DataFrame): Dataset to process.
            is_seasons (bool): Whether the dataset is season-based.
        
        Returns:
            str: Filename appended with min-max years if applicable.
        """
        if is_seasons and "season" in df.columns:
            valid_seasons = df["season"].dropna()
            if not valid_seasons.empty:
                min_yr = int(valid_seasons.min())
                max_yr = int(valid_seasons.max())
                
                suffix = f"_{min_yr}" if min_yr == max_yr else f"_{min_yr}-{max_yr}"
                return f"{base_name}{suffix}.csv"
                
        return f"{base_name}.csv"

    def split_dataset(self, df, mode_dir, is_seasons=False):
        """
        Splits a DataFrame by event type, discipline, and gender.
        
        Args:
            df (pd.DataFrame): Dataset to split.
            mode_dir (str): Output directory mode ("seasons" or "all-time").
            is_seasons (bool): Whether the dataset is season-based.
        
        Returns:
            None
        """
        
        individual_df = df[df["type"] != "relays"]
        relay_df = df[df["type"] == "relays"].copy()

        cols_to_drop = [col for col in ["dob", "age_at_event"] if col in relay_df.columns]
        if cols_to_drop:
            relay_df = relay_df.drop(columns=cols_to_drop)

        # --- 1. Save global-level splits ---
        global_out = os.path.join(mode_dir,"datasets","split_global")
        os.makedirs(global_out, exist_ok=True)
        
        ind_filename = self.get_filename_with_years("individual_events", individual_df, is_seasons)
        individual_df.to_csv(os.path.join(global_out, ind_filename), index=False)
        
        if not relay_df.empty:
            relay_filename = self.get_filename_with_years("relay_events", relay_df, is_seasons)
            relay_df.to_csv(os.path.join(global_out, relay_filename), index=False)

        genders = df["sex"].dropna().unique()

        # --- 2. Split both datasets by gender, type, and discipline ---
        for gender in genders:
            gender_individual = individual_df[individual_df["sex"] == gender]
            gender_relay = relay_df[relay_df["sex"] == gender]

            type_output_dir = os.path.join(mode_dir,"datasets", "split_by_type", gender)
            discipline_output_dir = os.path.join(mode_dir, "datasets","split_by_discipline", gender)
            relay_output_dir = os.path.join(mode_dir, "split_by_discipline", gender, "relays")

            if not gender_individual.empty:
                os.makedirs(type_output_dir, exist_ok=True)
                for event_type, df_group in gender_individual.groupby("type"):
                    filename = self.get_filename_with_years(event_type, df_group, is_seasons)
                    filepath_type = os.path.join(type_output_dir, filename)
                    df_group.to_csv(filepath_type, index=False)

                os.makedirs(discipline_output_dir, exist_ok=True)
                for discipline, df_group in gender_individual.groupby("normalized_discipline"):
                    filename = self.get_filename_with_years(discipline, df_group, is_seasons)
                    filepath_disc = os.path.join(discipline_output_dir, filename)
                    df_group.to_csv(filepath_disc, index=False)

            if not gender_relay.empty:
                os.makedirs(relay_output_dir, exist_ok=True)
                for discipline, df_group in gender_relay.groupby("normalized_discipline"):
                    filename = self.get_filename_with_years(discipline, df_group, is_seasons)
                    filepath_relay = os.path.join(relay_output_dir, filename)
                    df_group.to_csv(filepath_relay, index=False)

        print(f"  └─ Successfully generated aggregated splits for: {mode_dir.upper()}")

    def execute_splits(self):
        """
        Locates a single combined dataset, runs the generator if missing, and splits it.
        
        Returns:
            None
        """
        
        if self.mode in ["seasons", "both"]:
            datasets_dir = os.path.join("seasons", "datasets")
            os.makedirs(datasets_dir, exist_ok=True)

            # Look for a single combined seasons file
            filepath = os.path.join(datasets_dir, "combined_track_field_performances_*.csv")
            matching_files = glob.glob(filepath)
            
            # Generates combined dataset if not found (seasons)
            if not matching_files:
                print(f"[SEASONS] Combined dataset not found at {filepath}. Running generator automatically...")
                try:
                    generator = DatasetGenerator(mode="seasons")
                    generator.run(combine=True)
                    matching_files = glob.glob(filepath) # Check again after running generator
                except Exception as e:
                    print(f"[ERROR] Generator failed to run: {e}")
                    return
            
            if matching_files:
                filepath = matching_files[0]
                print(f"\n[SEASONS] Loading {filepath} for splitting...")
                try:
                    df = pd.read_csv(filepath)
                    self.split_dataset(df, mode_dir="seasons", is_seasons=True)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
            else:
                print("[SEASONS] Still no dataset found after running generator. Is there raw data to combine?")

        if self.mode in ["all-time", "both"]:
            datasets_dir = os.path.join("all-time", "datasets")
            os.makedirs(datasets_dir, exist_ok=True)
            
            filepath = os.path.join(datasets_dir, "top_track_field_performances_all_time.csv")
            
            # Generates combined dataset if not found (all-time)
            if not os.path.exists(filepath):
                print(f"[ALL-TIME] Combined dataset not found at {filepath}. Running generator automatically...")
                try:
                    generator = DatasetGenerator(mode="all-time")
                    generator.run()
                except Exception as e:
                    print(f"[ERROR] Generator failed to run: {e}")
                    return

            if os.path.exists(filepath):
                print(f"\n[ALL-TIME] Loading {filepath} for splitting...")
                try:
                    df = pd.read_csv(filepath)
                    self.split_dataset(df, mode_dir="all-time", is_seasons=False)
                except Exception as e:
                     print(f"Error reading {filepath}: {e}")
            else:
                print("[ALL-TIME] Still no dataset found after running generator. Is there raw data to combine?")

    def run(self):
        """
        Executes dataset splitting logic based on initialized mode.

        Returns:
            None
        """
        self.execute_splits()

if __name__ == "__main__":
    splitter = DatasetSplitter(mode="seasons")
    splitter.run()
