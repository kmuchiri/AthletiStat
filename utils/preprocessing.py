import os
import re
import pandas as pd
from collections import defaultdict
import json

class Preprocessor:
    """Handles data preprocessing, cleaning, and normalization for raw track and field dataset files."""
    def __init__(self, mode="both", options_file="utils/athletistat-options.json"):
        """
        Initializes the Preprocessor with running mode and loads regional configuration data.

        Args:
            mode (str): "both", "seasons", or "all-time". Defaults to "both".
            options_file (str): Path to the config file. Defaults to "utils/athletistat-options.json".
        """
        self.mode = mode
        
        # Load configs
        try:
            with open(options_file, "r") as f:
                options_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: '{options_file}' not found. Ensure it is in the root directory.")
            options_data = []

        self.ascending_types = {"sprints", "middlelong", "hurdles", "relays", "road-running", "race-walks"}
        self.descending_types = {"throws", "jumps", "combined-events"}

        self.track_types = {"sprints", "middlelong", "hurdles", "relays", "road-running", "race-walks"}
        self.field_types = {"throws", "jumps"}
        self.mixed_types = {"combined-events"} 

        self.manual_aliases = {
            "100m-hurdles": "100-metres-hurdles",
            "110m-hurdles": "110-metres-hurdles",
            "400m-hurdles": "400-metres-hurdles",
            "decathlon-u20": "decathlon",
            "decathlon-boys": "decathlon",
            "heptathlon-girls": "heptathlon",
        }

        self.country_lookup = {}
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
                        self.country_lookup[code] = label

    def normalize_discipline(self, discipline_slug):
        """
        Normalizes discipline slugs by mapping known aliases and stripping age/weight suffixes.

        Args:
            discipline_slug (str): The unnormalized discipline slug.

        Returns:
            str: The normalized discipline string.
        """
        if discipline_slug in self.manual_aliases:
            return self.manual_aliases[discipline_slug]
        for alias, standard in self.manual_aliases.items():
            if alias in discipline_slug:
                discipline_slug = discipline_slug.replace(alias, standard)
        discipline_slug = re.sub(r"[-_](\d+(kg|g|cm)|u18|u20|senior|girls|boys)$", "", discipline_slug)
        return discipline_slug

    def parse_mark_to_number(self, mark):
        """
        Converts a mark string (e.g., "M:S" or "H:M:S") into a numeric total seconds or float representation.

        Args:
            mark (str or int or float): The mark to be parsed.

        Returns:
            float: Parsed numeric representation in seconds or direct value. Returns float("inf") on failure.
        """
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

    def extract_country_code_from_venue(self, venue):
        """
        Extracts three-letter country codes from venue strings using regex.

        Args:
            venue (str): Venue name, optionally containing a country code in parentheses.

        Returns:
            str or None: The three-letter country code, or None if not found.
        """
        match = re.search(r"\((\w{3})\)", str(venue))
        return match.group(1) if match else None

    def _get_files_by_key(self, current_mode):
        """
        Scans the output directory and groups CSV files by year, gender, type, and discipline.

        Args:
            current_mode (str): Execution mode ("seasons" or "all-time").

        Returns:
            dict or None: Grouped file paths, or None if directory doesn't exist.
        """
        files_by_key = defaultdict(list)
        
        input_root = os.path.join("data","processing", "output", current_mode)
        if not os.path.exists(input_root):
            print(f"[{current_mode.upper()}] Input directory not found: {input_root}")
            return None

        print(f"[{current_mode.upper()}] Scanning files in: {input_root}")

        if current_mode == "seasons":
            years = [d for d in os.listdir(input_root) if os.path.isdir(os.path.join(input_root, d)) and d.isdigit()]
            for year in years:
                for gender in ["male", "female"]:
                    gender_path = os.path.join(input_root, year, gender)
                    if not os.path.exists(gender_path):
                        continue
                        
                    for file in os.listdir(gender_path):
                        if file.endswith(".csv"):
                            parts = file.replace(".csv", "").split("_")
                            if len(parts) >= 4:
                                type_slug = parts[1]
                                discipline_slug = "_".join(parts[2:-1]) 
                                base_discipline = self.normalize_discipline(discipline_slug)
                                
                                key = (year, gender, type_slug, base_discipline)
                                files_by_key[key].append(os.path.join(gender_path, file))

        elif current_mode == "all-time":
            base_dir = input_root
            for gender in os.listdir(base_dir):
                gender_path = os.path.join(base_dir, gender)
                if not os.path.isdir(gender_path):
                    continue
                
                for file in os.listdir(gender_path):
                    if file.endswith(".csv"):
                        parts = file.replace(".csv", "").split("_")
                        if len(parts) >= 3:
                            type_slug = parts[0]
                            discipline_slug = "_".join(parts[1:-1]) 
                            base_discipline = self.normalize_discipline(discipline_slug)
                            
                            key = (None, gender, type_slug, base_discipline)
                            files_by_key[key].append(os.path.join(gender_path, file))

        return files_by_key

    def process_data(self, current_mode):
        """
        Processes and combines scraped CSV files, normalizing disciplines, parsing marks, and augmenting demographics.

        Args:
            current_mode (str): The mode being processed ("seasons" or "all-time").

        Returns:
            None: Writes the combined files to disk.
        """
        files_by_key = self._get_files_by_key(current_mode)
        if files_by_key is None:
            return

        output_root = os.path.join("data","processing", "combined", current_mode)

        for (out_label, gender, type_slug, discipline_key), file_list in files_by_key.items():
            df = pd.concat([pd.read_csv(f) for f in file_list], ignore_index=True)

            df["normalized_discipline"] = discipline_key

            if type_slug in self.field_types:
                df["track_field"] = "field"
            elif type_slug in self.track_types:
                df["track_field"] = "track"
            elif type_slug in self.mixed_types:
                df["track_field"] = "mixed"
            else:
                df["track_field"] = "unknown"

            if "mark" not in df.columns:
                print(f"[Skipping] {discipline_key} — missing 'Mark'")
                continue

            sort_ascending = type_slug in self.ascending_types
            df["mark_numeric"] = df["mark"].apply(self.parse_mark_to_number)
            df = df.sort_values("mark_numeric", ascending=sort_ascending).reset_index(drop=True)
            
            df["nat_full"] = (
                df["nationality"]
                .str.lower()
                .map(self.country_lookup)
                .fillna("Unknown")
            )

            if "venue" in df.columns:
                df["venue_country"] = (
                    df["venue"]
                    .apply(self.extract_country_code_from_venue).str.lower()
                    .map(self.country_lookup)
                    .fillna("Unknown")
                )

            for col in ["dob", "date"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], format="%d %b %Y", errors="coerce")

            if "dob" in df.columns and "date" in df.columns:
                df["age_at_event"] = (df["date"] - df["dob"]).dt.days // 365

            if "date" in df.columns:
                df["season"] = df["date"].dt.year
            
            if current_mode == "seasons":
                target_dir = os.path.join(output_root, str(out_label))
            else:
                target_dir = os.path.join(output_root)
                
            os.makedirs(target_dir, exist_ok=True)

            prefix = f"{out_label}_" if current_mode == "seasons" else ""
            output_filename = f"{prefix}{gender}_{type_slug}_{discipline_key}.csv"
            output_path = os.path.join(target_dir, output_filename)
            
            df.to_csv(output_path, index=False)
            print(f"[{current_mode.upper()}] Saved: {output_path}")

    def run(self):
        """
        Executes the full data processing pipeline for 'seasons', 'all-time', or both based on the selected mode.

        Returns:
            None
        """
        if self.mode in ["seasons", "both"]:
            self.process_data("seasons")
            
        if self.mode in ["all-time", "both"]:
            self.process_data("all-time")

if __name__ == "__main__":
    preprocessor = Preprocessor(mode="seasons")
    preprocessor.run()