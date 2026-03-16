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

class AllTimeScraper:
    BASE_URL = (
        "https://worldathletics.org/records/all-time-toplists/{type_slug}/{discipline_slug}/all/{gender}/{age_category}"
        "?regionType=world&page={page}&bestResultsOnly=false&firstDay=1900-01-01&lastDay={today}&maxResultsByCountry=all&ageCategory={age_category}"
    )

    def __init__(self, mappings=None, options_file="utils/options.json"):
        if mappings is not None:
            self.mappings = mappings
        else:
            self.mappings = self.load_mappings(options_file)
            
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.current_time = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        
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

    @staticmethod
    def load_mappings(config_file="utils/options.json"):
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

    def build_jobs(self):
        jobs = []
        for (gender, age_category), discipline_list in self.mappings.items():
            output_dir = os.path.join("all-time/processing/output/", gender)
            for discipline_slug, type_slug in discipline_list:
                jobs.append((gender, age_category, discipline_slug, type_slug, output_dir))
        return jobs

    def scrape_event(self, gender, age_category, discipline_slug, type_slug, output_dir):
        page = 1
        data = []
        
        log_dir = os.path.join("logs/all-time", self.today)
        os.makedirs(log_dir, exist_ok=True)

        while True:
            url = self.BASE_URL.format(
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
                return False # CRITICAL: Must return False so the queue doesn't remove the job

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
            time.sleep(1.5) # Do not give too low of a value, will overwhelm server.

        # Save to CSV
        if data:
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{type_slug}_{discipline_slug}_{age_category}.csv".replace(" ", "_").replace("/", "-")
            filepath = os.path.join(output_dir, filename)
            
            df = pd.DataFrame(data)
            with self.lock:
                df.to_csv(filepath, index=False)
                print(f"Saved {filepath}")

        return True # Returns True when complete

    def run(self, max_workers=10):
        jobs = []
        print(f"Starting ALL-TIME scrape using {max_workers} workers...")
        start_time = time.time()

        queue_file = f"all-time/queues/queue_all_time_{self.today}.json"
        
        log_dir = os.path.join("logs/all-time", self.today)
        os.makedirs(log_dir, exist_ok=True)

        # Clean up all-time queues from previous days
        os.makedirs(os.path.dirname(queue_file), exist_ok=True)
        for old_queue in glob.glob("all-time/queues/queue_all_time_*.json"):
            if old_queue != queue_file:
                try:
                    os.remove(old_queue)
                    print(f"Removed outdated queue file: {old_queue}")
                except OSError:
                    pass
                
        # Resume today's queue if it exists
        if os.path.exists(queue_file) and os.path.getsize(queue_file) > 0:
            with open(queue_file, "r") as f:
                jobs = [tuple(job) for job in json.load(f)] 
            print(f"Resuming {len(jobs)} incomplete jobs from {queue_file}...")
        else:
            jobs = self.build_jobs()
            with open(queue_file, "w") as f:
                json.dump(jobs, f)
            print(f"Created new queue with {len(jobs)} jobs for all-time ({self.today}).")

        # Execute Jobs
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_job = {executor.submit(self.scrape_event, *job): job for job in jobs}
            
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    success = future.result()
                    
                    # Queue Management on Success
                    if success:
                        jobs.remove(job)
                        with open(queue_file, "w") as f:
                            json.dump(jobs, f)
                        
                except Exception as e:
                    with self.lock:
                        with open(os.path.join(log_dir, f"scrape_errors_{self.current_time}.log"), "a") as log_file:
                            log_file.write(f"UNCAUGHT ERROR in job {job}: {repr(e)}\n")

        # Final Cleanup & Logging
        if not jobs:
            print(f"All jobs for all-time completed successfully! Updating logs.")
            if os.path.exists(queue_file):
                os.remove(queue_file)
        else:
            print(f"Scrape paused or encountered errors. {len(jobs)} jobs remaining in queue.")

        end_time = time.time()
        total_time = end_time - start_time
        print("-" * 38)
        print(f"All-time scraping finished in {total_time:.1f} seconds ({total_time / 60:.2f} minutes)\n")

if __name__ == "__main__":
    # Example usage:
    scraper = AllTimeScraper()
    # Runs the all-time scrape with default max_workers
    # scraper.run(max_workers=10)
