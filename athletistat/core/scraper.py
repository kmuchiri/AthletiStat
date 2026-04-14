import os
import json
import time
import glob
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable insecure request warnings
urllib3.disable_warnings(InsecureRequestWarning)

class Scraper:
    """Scrapes track and field records from the World Athletics website."""
    BASE_URL_ALL_TIME = (
        "https://worldathletics.org/records/all-time-toplists/{type_slug}/{discipline_slug}/all/{gender}/{age_category}"
        "?regionType=world&page={page}&bestResultsOnly=false&firstDay=1900-01-01&lastDay={today}&maxResultsByCountry=all&ageCategory={age_category}"
    )

    BASE_URL_SEASONS = (
        "https://worldathletics.org/records/toplists/{type_slug}/{discipline_slug}/all/{gender}/{age_category}/{year}"
        "?regionType=world&timing=all&windReading=all&page={page}&bestResultsOnly=false&maxResultsByCountry=all&ageCategory={age_category}"
    )

    def __init__(self, mode="both", options_file="athletistat/options.json"):
        """
        Initializes the scraper, configures request retry sessions, and loads configurations.

        Args:
            mode (str): "both", "seasons", or "all-time". Defaults to "both".
            options_file (str): Path to config file. Defaults to "athletistat/options.json".
        """
        self.mode = mode
        self.options_file = options_file
        self.mappings = self._load_mappings(self.options_file)
            
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.current_time = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.current_year = int(datetime.now().strftime("%Y"))
        
        # Threading lock for safe file writing
        self.lock = threading.Lock()
        
        # Configure requests session with built-in retries
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD", "OPTIONS"),
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _load_mappings(self, config_file):
        """
        Parses the provided configuration file to extract mappings between discipline code slugs.

        Args:
            config_file (str): Path to config file.

        Returns:
            dict: Parsed discipline mappings.
        """
        with open(config_file, "r") as f:
            options_data = json.load(f)

        mappings = {}
        for entry in options_data:
            if entry.get("name") == "disciplineCode": 
                for case in entry.get("cases", []):
                    key = (case.get("gender"), case.get("ageCategory")) 
                    values = case.get("values", [])
                    mappings[key] = [
                        (v["disciplineNameUrlSlug"], v["typeNameUrlSlug"])
                        for v in values if "disciplineNameUrlSlug" in v and "typeNameUrlSlug" in v
                    ]
        return mappings

    def build_jobs(self, mode, year=None):
        """
        Constructs a list of scraping jobs containing URL parameters for targeted disciplines.

        Args:
            mode (str): "seasons" or "all-time".
            year (int or None): Target year (for "seasons" mode).

        Returns:
            list: List of scrape jobs.
        """
        jobs = []
        for (gender, age_category), discipline_list in self.mappings.items():
            if mode == "seasons":
                output_dir = os.path.join(f"data/processing/output/{mode}/{year}/", gender)
            
            else:
                output_dir = os.path.join(f"data/processing/output/{mode}", gender)
            
            os.makedirs(output_dir, exist_ok=True)    
            for discipline_slug, type_slug in discipline_list:
                jobs.append((gender, age_category, discipline_slug, type_slug, output_dir, mode, year))
        return jobs

    def scrape_event(self, gender, age_category, discipline_slug, type_slug, output_dir, mode="seasons", year=None):
        """
        Scrapes individual event record tables from World Athletics, parsing rows into tabular data and saving as a CSV.

        Args:
            gender (str): male or female.
            age_category (str): senior, u20, u18.
            discipline_slug (str): WA discipline slug.
            type_slug (str): WA type slug (e.g., track, jumps).
            output_dir (str): Save directory for CSVs.
            mode (str): "seasons" or "all-time". Defaults to "seasons".
            year (int or None): Target year (for "seasons" mode). Defaults to None.

        Returns:
            bool: True if completed, False if error.
        """
        page = 1
        data = []

        
        log_dir = os.path.join(f"logs/{mode}", self.today)
        os.makedirs(log_dir, exist_ok=True)

        while True:
            if mode == "seasons":
                url = self.BASE_URL_SEASONS.format(
                    type_slug=type_slug, discipline_slug=discipline_slug,
                    gender=gender, age_category=age_category, page=page, year=year
                )
            else:
                url = self.BASE_URL_ALL_TIME.format(
                    type_slug=type_slug, discipline_slug=discipline_slug,
                    gender=gender, age_category=age_category, page=page, today=self.today
                )
            
            headers = {"User-Agent": "Mozilla/5.0"}
            
            try:
                response = self.session.get(url, headers=headers, timeout=(5, 30), verify=True)
                response.raise_for_status()
            except Exception as e:
                with self.lock:
                    with open(os.path.join(log_dir, f"scrape_errors_{self.current_time}.log"), "a") as log_file:
                        log_file.write(f"FAILED: {url} | {repr(e)}\n")
                # Must return False so the queue doesn't remove the job
                return False 

            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find("table", class_="records-table")
            
            if not table:
                break
                
            rows = table.find("tbody").find_all("tr") if table.find("tbody") else []
            if not rows:
                break

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 11:
                    continue
                    
                data.append({
                    "rank": cols[0].text.strip(),
                    "mark": cols[1].text.strip(),
                    "wind": cols[2].text.strip(),
                    "competitor": cols[3].text.strip(),
                    "dob": cols[4].text.strip(),
                    "nationality": cols[5].text.strip(),
                    "position": cols[6].text.strip(),
                    "venue": cols[8].text.strip(),
                    "date": cols[9].text.strip(),
                    "result_score": cols[10].text.strip(),
                    "discipline": discipline_slug,
                    "type": type_slug,
                    "sex": gender,
                    "age_cat": age_category
                })

            page += 1
            # Do not give too low of a value, will overwhelm server.
            time.sleep(1.5) 

        # Save to CSV
        if data:
            os.makedirs(output_dir, exist_ok=True)
            prefix = f"{year}_" if mode == "seasons" else ""
            filename = f"{prefix}{type_slug}_{discipline_slug}_{age_category}.csv".replace(" ", "_").replace("/", "-")
            filepath = os.path.join(output_dir, filename)
            
            df = pd.DataFrame(data)
            with self.lock:
                df.to_csv(filepath, index=False)
                print(f"Saved {filepath}")

        return True # Returns True when complete

    def _get_queue_info(self, mode, year=None):
        """
        Determines the queue file path specific to the scraper mode and target year.

        Args:
            mode (str): "seasons" or "all-time".
            year (int or None): Target year.

        Returns:
            str: Path to the queue JSON file.
        """
        queue_dir = f"queues/{mode}"
        os.makedirs(queue_dir, exist_ok=True)
        if mode == "seasons":
            return f"{queue_dir}/queue_seasons_{year}.json"
        else:
            return f"{queue_dir}/queue_all_time_{self.today}.json"

    def _manage_queues_and_jobs(self, mode, year=None):
        """
        Manages saved scrape job queues to enable resuming partial scrapes and caching completed years.

        Args:
            mode (str): "seasons" or "all-time".
            year (int or None): Target year.
        
        Returns:
            tuple: (jobs list, queue_file path, completed_years list).
        """

        queue_dir = f"queues/{mode}"
        os.makedirs(queue_dir, exist_ok=True)
        queue_file = self._get_queue_info(mode, year)
        jobs = []

        if mode == "seasons":
            completed_file = f"{queue_dir}/completed_seasons.json"
            completed_years = []
            
            if year != self.current_year:
                if os.path.exists(completed_file):
                    with open(completed_file, "r") as f:
                        completed_years = json.load(f)
                
                if year in completed_years:
                    print(f"Data for the year {year} is already completely retrieved. Skipping scrape.")
                    return None, queue_file, completed_years

                os.makedirs(os.path.dirname(queue_file), exist_ok=True)
                if os.path.exists(queue_file) and os.path.getsize(queue_file) > 0:
                    with open(queue_file, "r") as f:
                        jobs = [tuple(job) for job in json.load(f)] 
                    print(f"Resuming {len(jobs)} incomplete jobs from {queue_file}...")
                else:
                    jobs = self.build_jobs(mode, year)
                    with open(queue_file, "w") as f:
                        json.dump(jobs, f)
                    print(f"Created new queue with {len(jobs)} jobs for historical year {year}.")
            else:
                jobs = self.build_jobs(mode, year)
                print(f"Current year ({year}) detected. Running {len(jobs)} jobs from scratch (no queue).")
            
            return jobs, queue_file, completed_years

        elif mode == "all-time":
            os.makedirs(os.path.dirname(queue_file), exist_ok=True)
            for old_queue in glob.glob(f"{queue_dir}/queue_all_time_*.json"):
                if old_queue != queue_file:
                    try:
                        os.remove(old_queue)
                        print(f"Removed outdated queue file: {old_queue}")
                    except OSError:
                        pass
                    
            if os.path.exists(queue_file) and os.path.getsize(queue_file) > 0:
                with open(queue_file, "r") as f:
                    jobs = [tuple(job) for job in json.load(f)] 
                print(f"Resuming {len(jobs)} incomplete jobs from {queue_file}...")
            else:
                jobs = self.build_jobs(mode)
                with open(queue_file, "w") as f:
                    json.dump(jobs, f)
                print(f"Created new queue with {len(jobs)} jobs for all-time ({self.today}).")
                
            return jobs, queue_file, []

    def run_scraper(self, mode, max_workers=10, year=None):
        """
        Executes the scraper for a given mode processing the compiled jobs concurrently utilizing a threadpool.

        Args:
            mode (str): "seasons" or "all-time".
            max_workers (int): Number of threads. Defaults to 10.
            year (int or None): Target year.

        Returns:
            None
        """
        print(f"Starting {mode.upper()} scrape using {max_workers} workers...")
        start_time = time.time()
        
        log_dir = os.path.join(f"logs/{mode}", self.today)
        os.makedirs(log_dir, exist_ok=True)

        info = self._manage_queues_and_jobs(mode, year)
        if info is None or info[0] is None:
            return  # Skipped
        jobs, queue_file, completed_years = info

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_job = {executor.submit(self.scrape_event, *job): job for job in jobs}
            
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    success = future.result()
                    
                    if success:
                        if (mode == "seasons" and year != self.current_year) or (mode == "all-time"):
                            jobs.remove(job)
                            with open(queue_file, "w") as f:
                                json.dump(jobs, f)
                            
                except Exception as e:
                    with self.lock:
                        with open(os.path.join(log_dir, f"scrape_errors_{self.current_time}.log"), "a") as log_file:
                            log_file.write(f"UNCAUGHT ERROR in job {job}: {repr(e)}\n")

        # Final Cleanup & Logging
        if (mode == "seasons" and year != self.current_year) or (mode == "all-time"):
            if not jobs:
                print(f"All jobs for {mode} completed successfully! Updating logs.")
                if os.path.exists(queue_file):
                    os.remove(queue_file)
                
                if mode == "seasons" and year not in completed_years:
                    completed_years.append(year)
                    completed_file = f"queues/seasons/completed_seasons.json"
                    os.makedirs(os.path.dirname(completed_file), exist_ok=True)
                    with open(completed_file, "w") as f:
                        json.dump(completed_years, f)
            else:
                print(f"Scrape paused or encountered errors. {len(jobs)} jobs remaining in queue.")

        end_time = time.time()
        total_time = end_time - start_time
        print("-" * 38)
        print(f"{mode.capitalize()} scraping finished in {total_time:.1f} seconds ({total_time / 60:.2f} minutes)\n")

    def run(self, max_workers=10, year=None):
        """
        Wrapper that runs the scraper across designated modes utilizing max configured workers.

        Args:
            max_workers (int): Number of threads. Defaults to 10.
            year (int or None): Target year.

        Returns:
            None
        """
        if year is None:
            year = self.current_year

        if self.mode in ["seasons", "both"]:
            self.run_scraper("seasons", max_workers=max_workers, year=year)
            
        if self.mode in ["all-time", "both"]:
            self.run_scraper("all-time", max_workers=max_workers)

if __name__ == "__main__":
    scraper = Scraper(mode="seasons")
    scraper.run(max_workers=12)