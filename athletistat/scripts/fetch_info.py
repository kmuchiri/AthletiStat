import pathlib
import os
from prettytable import PrettyTable
from athletistat.console import success
import re
from athletistat.config import cfg

dataset_dir = cfg.paths.dataset_dir
all_time_dir = os.path.join(cfg.paths.dataset_dir, "all-time")
seasons_dir = os.path.join(cfg.paths.dataset_dir, "seasons")
info_file = cfg.paths.dataset_info_file
summary_file = cfg.paths.dataset_summary_file



class DatasetInfo:
    def __init__(self):
        self.table = PrettyTable()
        self.table.field_names = ["File Name", "File Size", "Row Count"]
        self.table.align["Row Count"] = "r"

    
    def count_rows(self,filename):
        def _make_gen(reader):
            while True:
                # Read in 1MB chunks
                b = reader(cfg.display.row_count_chunk_size)
                if not b: break
                yield b

        with open(filename, 'rb') as f:
            # Count the number of newline characters
            count = sum(buf.count(b'\n') for buf in _make_gen(f.read))
        return count - 1


    def get_file_size(self,filepath):
        size_in_bytes = os.path.getsize(filepath)
        
        # Convert to Megabytes
        size_in_mb = size_in_bytes / (1024 * 1024)
        
        if size_in_mb > 1024:
            # If it's over 1024 MB, show it in Gigabytes
            size_in_gb = size_in_mb / 1024
            return f"{size_in_gb:.2f} GB"
        else:
            return f"{size_in_mb:.2f} MB"

    def generate_info(self):
          # Process all-time datasets
        if os.path.exists(all_time_dir):
            for file in pathlib.Path(all_time_dir).glob('*.csv'):
                self.table.add_row([file.name, self.get_file_size(file), self.count_rows(file)])

        # Process seasons datasets
        if os.path.exists(seasons_dir):
            for file in pathlib.Path(seasons_dir).glob('**/*.csv'):
                self.table.add_row([file.name, self.get_file_size(file), self.count_rows(file)])
        self.table.sortby = "Row Count"
        self.table.reversesort = True

        # Save to txt file
        with open(info_file, "w") as f:
            f.write(str(self.table))
        
        success("Dataset information saved to" + info_file)

    def generate_summary(self):
         # Process all-time datasets
        if os.path.exists(all_time_dir):
            for file in pathlib.Path(all_time_dir).glob('top_track_field_performances_all_time.csv'):
                self.table.add_row([file.name, self.get_file_size(file), self.count_rows(file)])

        # Process seasons datasets
        if os.path.exists(seasons_dir):
            for file in pathlib.Path(seasons_dir).glob('combined_track_field_performances_*.csv'):
                self.table.add_row([file.name, self.get_file_size(file), self.count_rows(file)])
        self.table.sortby = "Row Count"
        self.table.reversesort = True

        # Update README.md with the generated info inside a markdown code block
        readme_path = "README.md"
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()

            start_anchor = "<!-- START_DATASET_INFO -->"
            end_anchor = "<!-- END_DATASET_INFO -->"
            
            
            pattern = re.compile(
                rf"{re.escape(start_anchor)}.*?{re.escape(end_anchor)}", re.DOTALL
            )
            replacement = f"{start_anchor}\n```text\n{str(self.table)}\n```\n{end_anchor}"
            new_readme_content = pattern.sub(replacement, readme_content)
            
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(new_readme_content)
            success("README.md dataset info updated successfully!")

       




