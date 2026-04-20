import pathlib
import os
from prettytable import PrettyTable

dataset_dir = "./data/datasets"
all_time_dir = os.path.join(dataset_dir,"all-time")
seasons_dir = os.path.join(dataset_dir, "seasons")
info_file = os.path.join(dataset_dir, "dataset_info.txt")


class DatasetInfo:
    def __init__(self):
        self.table = PrettyTable()
        self.table.field_names = ["File Name", "File Size", "Row Count"]
        self.table.align["Row Count"] = "r"

    
    def count_rows(self,filename):
        def _make_gen(reader):
            while True:
                b = reader(1024 * 1024) # Read in 1MB chunks
                if not b: break
                yield b

        with open(filename, 'rb') as f:
            # Count the number of newline characters
            count = sum(buf.count(b'\n') for buf in _make_gen(f.read))
        return count - 1


    def get_file_size(self,filepath):
        size_in_bytes = os.path.getsize(filepath)
        
        # Convert to Megabytes (1 MB = 1024 * 1024 bytes)
        size_in_mb = size_in_bytes / (1024 * 1024)
        
        if size_in_mb > 1024:
            # If it's over 1024 MB, show it in Gigabytes
            size_in_gb = size_in_mb / 1024
            return f"{size_in_gb:.2f} GB"
        else:
            return f"{size_in_mb:.2f} MB"

    def run(self):
        
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
        
        print("Dataset information saved to dataset_info.txt")



