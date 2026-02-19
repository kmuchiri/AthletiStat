import os
import re
import argparse
import pandas as pd
from collections import defaultdict
import json

# --- CONFIGURATION ---
try:
    with open("options.json", "r") as f:
        options_data = json.load(f)
except FileNotFoundError:
    print("Error: 'options.json' not found. Ensure it is in the root directory.")
    exit(1)

# Define sort order by event type
ascending_types = {"sprints", "middlelong", "hurdles", "relays", "road-running", "race-walks"}
descending_types = {"throws", "jumps", "combined-events"}

track_types = {"sprints", "middlelong", "hurdles", "relays", "road-running", "race-walks"}
field_types = {"throws", "jumps"}
mixed_types = {"combined-events"} 

# Custom name normalization
manual_aliases = {
    "100m-hurdles": "100-metres-hurdles",
    "110m-hurdles": "110-metres-hurdles",
    "400m-hurdles": "400-metres-hurdles",
    "decathlon-u20": "decathlon",
    "decathlon-boys": "decathlon",
    "heptathlon-girls": "heptathlon",
}

# --- COUNTRY LOOKUP ---
country_lookup = {}
for item in options_data:
    if item.get("name") != "region":
        continue

    for case in item.get("cases", []):
        if case.get("regionType") != "countries":
            continue

        for country in case.get("values", []):
            code = country.get("value")
            label = country.get("label")

            if code and label:
                country_lookup[code] = label

# --- HELPER FUNCTIONS ---
def parse_mark(mark):
    mark = str(mark).strip().lower().replace("h", "")
    try:
        if ":" in mark:
            minutes, seconds = mark.split(":")
            return int(minutes) * 60 + float(seconds)
        return float(mark)
    except:
        return float("inf")

def normalize_discipline(discipline_slug):
    if discipline_slug in manual_aliases:
        return manual_aliases[discipline_slug]
    for alias, standard in manual_aliases.items():
        if alias in discipline_slug:
            discipline_slug = discipline_slug.replace(alias, standard)
    discipline_slug = re.sub(r"[-_](\d+(kg|g|cm)|u18|u20|senior|girls|boys)$", "", discipline_slug)
    return discipline_slug

def parse_mark_to_number(mark):
    mark = str(mark).strip().lower().replace("h", "")
    try:
        if ":" in mark:
            parts = mark.split(":")
            parts = [float(p) for p in parts]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:  # M:S
                return parts[0] * 60 + parts[1]
            else:
                return float("inf")
        return float(mark)
    except:
        return float("inf")

def extract_country_code_from_venue(venue):
    match = re.search(r"\((\w{3})\)", str(venue))
    return match.group(1) if match else None

# --- CORE PREPROCESSING LOGIC ---
def process_data(mode):
    files_by_key = defaultdict(list)
    
    # Dynamically set root directories based on mode
    if mode == "seasons":
        input_root = os.path.join("seasons", "processing", "output")
        output_root = os.path.join("seasons", "processing", "combined")
        
        if not os.path.exists(input_root):
            print(f"[{mode.upper()}] Input directory not found: {input_root}")
            return
            
        # Target only numeric folders (years)
        target_dirs = [d for d in os.listdir(input_root) if os.path.isdir(os.path.join(input_root, d)) and d.isdigit()]
        
    elif mode == "all-time":
        input_root = os.path.join("all-time", "processing", "output")
        output_root = os.path.join("all-time", "processing", "combined")
        
        # Accommodate if the scraper nested it under an extra 'all-time' folder
        if os.path.exists(os.path.join(input_root, "all-time")):
            input_root = os.path.join(input_root, "all-time")
            
        if not os.path.exists(input_root):
            print(f"[{mode.upper()}] Input directory not found: {input_root}")
            return
            
        # Use a dot to represent the current directory for the inner loop
        target_dirs = ["."] 
    else:
        return

    if not target_dirs:
        print(f"[{mode.upper()}] No target data directories found in {input_root}.")
        return
        
    print(f"[{mode.upper()}] Scanning files in: {input_root}")

    # Map files to their base groupings
    for dir_name in target_dirs:
        dir_path = os.path.join(input_root, dir_name)
        
        # Determine the label for output (the year, or "all-time")
        out_label = dir_name if mode == "seasons" else "all-time"
        
        # Loop through Genders inside the directory
        for gender in os.listdir(dir_path):
            gender_path = os.path.join(dir_path, gender)
            
            if not os.path.isdir(gender_path):
                continue
                
            for file in os.listdir(gender_path):
                if file.endswith(".csv"):
                    # Split filename to extract parts
                    parts = file.replace(".csv", "").split("_")
                    if len(parts) >= 4:
                        type_slug = parts[1]
                        discipline_slug = "_".join(parts[2:-1]) 
                        base_discipline = normalize_discipline(discipline_slug)
                        
                        key = (out_label, gender, type_slug, base_discipline)
                        files_by_key[key].append(os.path.join(gender_path, file))

    # 3. Combine, Process, and Save Data
    for (out_label, gender, type_slug, discipline_key), file_list in files_by_key.items():
        
        # Combine files
        df = pd.concat([pd.read_csv(f) for f in file_list], ignore_index=True)

        df["normalized_discipline"] = discipline_key

        # Track/Field classification
        if type_slug in field_types:
            df["track_field"] = "field"
        elif type_slug in track_types:
            df["track_field"] = "track"
        elif type_slug in mixed_types:
            df["track_field"] = "mixed"
        else:
            df["track_field"] = "unknown"

        if "mark" not in df.columns:
            print(f"[{out_label}] Skipping {discipline_key} — missing 'Mark'")
            continue

        # Sorting
        sort_ascending = type_slug in ascending_types
        df["mark_numeric"] = df["mark"].apply(parse_mark_to_number)
        df = df.sort_values("mark_numeric", ascending=sort_ascending).reset_index(drop=True)
        
        # Processing Country & Venue
        df["nat_full"] = (
            df["nationality"]
            .str.lower()
            .map(country_lookup)
            .fillna("Unknown")
        )

        if "venue" in df.columns:
            df["venue_country"] = (
                df["venue"]
                .apply(extract_country_code_from_venue).str.lower()
                .map(country_lookup)
                .fillna("Unknown")
            )

        # Processing Dates
        for col in ["dob", "date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="%d %b %Y", errors="coerce")

        if "dob" in df.columns and "date" in df.columns:
            df["age_at_event"] = (df["date"] - df["dob"]).dt.days // 365

        if "date" in df.columns:
            df["season"] = df["date"].dt.year
        
        # Output processed files
        target_dir = os.path.join(output_root, out_label)
        os.makedirs(target_dir, exist_ok=True)
        
        output_filename = f"{type_slug}_{gender}_{discipline_key}.csv"
        output_path = os.path.join(target_dir, output_filename)
        
        df.to_csv(output_path, index=False)
        print(f"[{mode.upper()}] Saved: {output_path}")

# --- MAIN CLI EXECUTION ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="World Athletics Data Preprocessor")
    
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["seasons", "all-time", "both"], 
        default="both", 
        help="Choose the preprocessing mode: 'seasons', 'all-time', or 'both'."
    )
    
    args = parser.parse_args()

    if args.mode in ["seasons", "both"]:
        process_data("seasons")
        
    if args.mode in ["all-time", "both"]:
        process_data("all-time")