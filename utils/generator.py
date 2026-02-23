import os
import pandas as pd
import argparse

def generate_datasets(mode):
    combined_dir = f"{mode}/processing/combined"
    output_dataset_dir = f"{mode}/datasets"
    os.makedirs(output_dataset_dir, exist_ok=True)

    if mode == "seasons":
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
            combined_df.drop_duplicates()

            # Save to a new CSV
            output_filename = os.path.join(output_dataset_dir,"top_track_field_performances_all_time.csv",)
            combined_df.to_csv(output_filename, index=False)
            print(f"Combined CSV saved as {output_filename}" )
        else:
            print(f"No CSV files found in {combined_dir}")

def combine_seasons():
    dataset_dir = "seasons/datasets"
    processed_dir = "seasons/processing/combined"

    # List CSV files directly inside the Year folder
    csv_files = [f for f in os.listdir(dataset_dir) if f.endswith(".csv")]
    all_dataframes = []

    min_year = min(os.listdir(processed_dir))
    max_year = max(os.listdir(processed_dir))

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AthletiStat Dataset Generator")
    parser.add_argument(
        '-m',
        "--mode", 
        type=str, 
        choices=["seasons", "all-time", "both"], 
        default="both", 
        help="Choose the dataset generator mode: 'seasons', 'all-time', or 'both'."
    )
    parser.add_argument(
        '-c',
        "--combine",
        action='store_true',
        default=False,
        dest='combine',
        required=False,
        help = "Combines all season datasets into one"
    )
    
    args = parser.parse_args()

    if args.mode in ["seasons", "both"]:
        generate_datasets("seasons")
        combine_seasons()
        
    if args.mode in ["all-time", "both"]:
        generate_datasets("all-time")

    if args.combine:
        combine_seasons()


