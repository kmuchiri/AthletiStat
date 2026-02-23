import os
import glob
import argparse
import pandas as pd
import numpy as np
import subprocess

def get_filename_with_years(base_name, df, is_seasons):
    """Generates a filename dynamically including the min and max year if applicable."""
    if is_seasons and "season" in df.columns:
        valid_seasons = df["season"].dropna()
        if not valid_seasons.empty:
            min_yr = int(valid_seasons.min())
            max_yr = int(valid_seasons.max())
            
            suffix = f"_{min_yr}" if min_yr == max_yr else f"_{min_yr}-{max_yr}"
            return f"{base_name}{suffix}.csv"
            
    return f"{base_name}.csv"

def split_dataset(df, mode_dir, is_seasons=False):
    """Splits a DataFrame by event type, discipline, and gender."""
    
    individual_df = df[df["type"] != "relays"]
    relay_df = df[df["type"] == "relays"].copy()

    cols_to_drop = [col for col in ["dob", "age_at_event"] if col in relay_df.columns]
    if cols_to_drop:
        relay_df = relay_df.drop(columns=cols_to_drop)

    # --- 1. Save global-level splits ---
    global_out = os.path.join(mode_dir,"datasets","split_global")
    os.makedirs(global_out, exist_ok=True)
    
    ind_filename = get_filename_with_years("individual_events", individual_df, is_seasons)
    individual_df.to_csv(os.path.join(global_out, ind_filename), index=False)
    
    if not relay_df.empty:
        relay_filename = get_filename_with_years("relay_events", relay_df, is_seasons)
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
                filename = get_filename_with_years(event_type, df_group, is_seasons)
                filepath_type = os.path.join(type_output_dir, filename)
                df_group.to_csv(filepath_type, index=False)

            os.makedirs(discipline_output_dir, exist_ok=True)
            for discipline, df_group in gender_individual.groupby("normalized_discipline"):
                filename = get_filename_with_years(discipline, df_group, is_seasons)
                filepath_disc = os.path.join(discipline_output_dir, filename)
                df_group.to_csv(filepath_disc, index=False)

        if not gender_relay.empty:
            os.makedirs(relay_output_dir, exist_ok=True)
            for discipline, df_group in gender_relay.groupby("normalized_discipline"):
                filename = get_filename_with_years(discipline, df_group, is_seasons)
                filepath_relay = os.path.join(relay_output_dir, filename)
                df_group.to_csv(filepath_relay, index=False)

    print(f"  └─ Successfully generated aggregated splits for: {mode_dir.upper()}")

def execute_splits(mode):
    """Locates a single combined dataset, runs the generator if missing, and splits it."""
    
    if mode in ["seasons", "both"]:
        datasets_dir = os.path.join("seasons", "datasets")
        os.makedirs(datasets_dir, exist_ok=True)

        
        
        # Look for a single combined seasons file
        filepath = os.path.join(datasets_dir, "combined_track_field_performances_*.csv")
        matching_file = glob.glob(filepath)
        
        # --- CONDITIONAL GENERATOR TRIGGER ---
        if not matching_file:
            print(f"[SEASONS] Combined dataset not found at {filepath}. Running generator automatically...")
            try:
                subprocess.run(["python", "utils/generator.py", "-c"], check=True)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Generator failed to run: {e}")
                return
            except FileNotFoundError:
                print("[ERROR] Could not find 'utils/generator.py'. Ensure the path is correct.")
                return
        
        if matching_file:
            filepath = matching_file[0]
            print(f"\n[SEASONS] Loading {filepath} for splitting...")
            try:
                df = pd.read_csv(filepath)
                split_dataset(df, mode_dir="seasons", is_seasons=True)
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
        else:
            print("[SEASONS] Still no dataset found after running generator. Is there raw data to combine?")

    if mode in ["all-time", "both"]:
        datasets_dir = os.path.join("all-time", "datasets")
        os.makedirs(datasets_dir, exist_ok=True)
        
        filepath = os.path.join(datasets_dir, "top_track_field_performances_all_time.csv")
        
        # --- CONDITIONAL GENERATOR TRIGGER ---
        if not os.path.exists(filepath):
            print(f"[ALL-TIME] Combined dataset not found at {filepath}. Running generator automatically...")
            try:
                subprocess.run(["python", "utils/generator.py", "-c", "--mode", "all-time"], check=True)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Generator failed to run: {e}")
                return
            except FileNotFoundError:
                print("[ERROR] Could not find 'utils/generator.py'. Ensure the path is correct.")
                return

        if os.path.exists(filepath):
            print(f"\n[ALL-TIME] Loading {filepath} for splitting...")
            try:
                df = pd.read_csv(filepath)
                split_dataset(df, mode_dir="all-time", is_seasons=False)
            except Exception as e:
                 print(f"Error reading {filepath}: {e}")
        else:
            print("[ALL-TIME] Still no dataset found after running generator. Is there raw data to combine?")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AthletiStat Dataset Splitter")
    
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["seasons", "all-time", "both"], 
        default="both", 
        help="Choose the splitting mode: 'seasons', 'all-time', or 'both'."
    )
    
    args = parser.parse_args()

    # Execute the splitter
    execute_splits(args.mode)