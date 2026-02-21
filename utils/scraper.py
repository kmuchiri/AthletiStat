'''
IMPORTS
'''
import os
import json
import time
import glob
import threading
import argparse
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

# --- GLOBALS & SETUP ---
today = datetime.now().strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%Y-%m-%d_%H%M%S")
current_year = int(datetime.now().strftime("%Y"))

# Threading lock for safe file writing
lock = threading.Lock()

# Configure requests session with built-in retries
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("GET", "HEAD", "OPTIONS"),
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)

'''
CONFIG
'''
# --- URL TEMPLATES ---
BASE_URL_ALL_TIME = (
    "https://worldathletics.org/records/all-time-toplists/{type_slug}/{discipline_slug}/all/{gender}/{age_category}"
    "?regionType=world&page={page}&bestResultsOnly=false&firstDay=1900-01-01&lastDay={today}&maxResultsByCountry=all&ageCategory={age_category}"
)

BASE_URL_SEASONS = (
    "https://worldathletics.org/records/toplists/{type_slug}/{discipline_slug}/all/{gender}/{age_category}/{year}"
    "?regionType=world&timing=all&windReading=all&page={page}&bestResultsOnly=false&maxResultsByCountry=all&ageCategory={age_category}"
)

# --- CONFIG LOADER ---
def load_mappings(config_file="modules/00-options.json"):
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

# --- HELPER: BUILD JOBS ---
def build_jobs(mappings, mode, year):
    jobs = []
    for (gender, age_category), discipline_list in mappings.items():
        if mode == "seasons":
            output_dir = os.path.join(f"{mode}/processing/output/{year}/", gender)
        else:
            output_dir = os.path.join(f"{mode}/processing/output/", gender)
            
        for discipline_slug, type_slug in discipline_list:
            jobs.append((gender, age_category, discipline_slug, type_slug, output_dir, mode, year))
    return jobs

'''
SCRAPER
'''
# --- SCRAPER ---
def scrape_event(gender, age_category, discipline_slug, type_slug, output_dir, mode="seasons", year=None):
    page = 1
    data = []
    
    log_dir = os.path.join(f"logs/{mode}", today)
    os.makedirs(log_dir, exist_ok=True)

    while True:
        if mode == "seasons":
            url = BASE_URL_SEASONS.format(
                type_slug=type_slug, discipline_slug=discipline_slug,
                gender=gender, age_category=age_category, page=page, year=year
            )
        else:
            url = BASE_URL_ALL_TIME.format(
                type_slug=type_slug, discipline_slug=discipline_slug,
                gender=gender, age_category=age_category, page=page, today=today
            )
        
        headers = {"User-Agent": "Mozilla/5.0"}
        
        try:
            response = session.get(url, headers=headers, timeout=(5, 30), verify=True)
            response.raise_for_status()
        except Exception as e:
            with lock:
                with open(os.path.join(log_dir, f"scrape_errors_{current_time}.log"), "a") as log_file:
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
        prefix = f"{year}_" if mode == "seasons" else ""
        filename = f"{prefix}{type_slug}_{discipline_slug}_{age_category}.csv".replace(" ", "_").replace("/", "-")
        filepath = os.path.join(output_dir, filename)
        
        df = pd.DataFrame(data)
        with lock:
            df.to_csv(filepath, index=False)
            print(f"Saved {filepath}")

    return True # Returns True when complete

# --- MULTITHREADING ---
def run_scraper(mappings, mode="seasons", max_workers=10, year=None):
    jobs = []
    completed_years = [] 
    print(f"Starting {mode.upper()} scrape using {max_workers} workers...")
    start_time = time.time()

    queue_file = None
    completed_file = "seasons/completed_seasons.json"
    
    log_dir = os.path.join(f"logs/{mode}", today)
    os.makedirs(log_dir, exist_ok=True)

    # Evaluate Job Logic Based on Year and Mode
    if mode == "seasons":
        if year != current_year:
            queue_file = f"{mode}/queues/queue_seasons_{year}.json"
            
            # Historical Year Logic
            if os.path.exists(completed_file):
                with open(completed_file, "r") as f:
                    completed_years = json.load(f)
            
            if year in completed_years:
                print(f"Data for the year {year} is already completely retrieved. Skipping scrape.")
                return 

            if os.path.exists(queue_file) and os.path.getsize(queue_file) > 0:
                with open(queue_file, "r") as f:
                    jobs = [tuple(job) for job in json.load(f)] 
                print(f"Resuming {len(jobs)} incomplete jobs from {queue_file}...")
            else:
                jobs = build_jobs(mappings, mode, year)
                with open(queue_file, "w") as f:
                    json.dump(jobs, f)
                print(f"Created new queue with {len(jobs)} jobs for historical year {year}.")
        else:
            # No queue for current year
            jobs = build_jobs(mappings, mode, year)
            print(f"Current year ({year}) detected. Running {len(jobs)} jobs from scratch (no queue).")
            
    elif mode == "all-time":
        queue_file = f"{mode}/queues/queue_all_time_{today}.json"
        
        # Clean up all-time queues from previous days
        for old_queue in glob.glob(f"{mode}/queue/queue_all_time_*.json"):
            if old_queue != queue_file:
                os.remove(old_queue)
                print(f"Removed outdated queue file: {old_queue}")
                
        # Resume today's queue if it exists
        if os.path.exists(queue_file) and os.path.getsize(queue_file) > 0:
            with open(queue_file, "r") as f:
                jobs = [tuple(job) for job in json.load(f)] 
            print(f"Resuming {len(jobs)} incomplete jobs from {queue_file}...")
        else:
            jobs = build_jobs(mappings, mode, year)
            with open(queue_file, "w") as f:
                json.dump(jobs, f)
            print(f"Created new queue with {len(jobs)} jobs for all-time ({today}).")


    # Execute Jobs
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {executor.submit(scrape_event, *job): job for job in jobs}
        
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                success = future.result()
                
                # Queue Management on Success (For historical seasons or all-time)
                if success:
                    if (mode == "seasons" and year != current_year) or (mode == "all-time"):
                        jobs.remove(job)
                        with open(queue_file, "w") as f:
                            json.dump(jobs, f)
                        
            except Exception as e:
                with lock:
                    with open(os.path.join(log_dir, f"scrape_errors_{current_time}.log"), "a") as log_file:
                        log_file.write(f"UNCAUGHT ERROR in job {job}: {repr(e)}\n")

    # Final Cleanup & Logging
    if (mode == "seasons" and year != current_year) or (mode == "all-time"):
        if not jobs:
            print(f"All jobs for {mode} completed successfully! Updating logs.")
            if os.path.exists(queue_file):
                os.remove(queue_file)
            
            # Record completed seasons
            if mode == "seasons" and year not in completed_years:
                completed_years.append(year)
                with open(completed_file, "w") as f:
                    json.dump(completed_years, f)
        else:
            print(f"Scrape paused or encountered errors. {len(jobs)} jobs remaining in queue.")

    end_time = time.time()
    total_time = end_time - start_time
    print("-" * 38)
    print(f"{mode.capitalize()} scraping finished in {total_time:.1f} seconds ({total_time / 60:.2f} minutes)\n")

'''
MAIN EXECUTION WITH ARGPARSE
'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AthletiStat: Athletics Data Web Scraper")
    
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["seasons", "all-time", "both"], 
        default="seasons", 
        help="Choose the scraping mode: 'seasons', 'all-time', or 'both'."
    )
    parser.add_argument(
        "--year", 
        type=int, 
        default=current_year, 
        help="Specify the year to scrape for 'seasons' mode (defaults to current year)."
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=12, 
        help="Maximum number of parallel threads to use (default: 12)."
    )

    args = parser.parse_args()

    # Load configuration
    try:
        discipline_mappings = load_mappings("utils/00-options.json")
    except FileNotFoundError:
        print("Error: 'utils/options.json' not found. Please ensure the file is in the correct directory.")
        exit(1)

    # Execute based on arguments
    if args.mode in ["seasons", "both"]:
        run_scraper(discipline_mappings, mode="seasons", max_workers=args.workers, year=args.year)
        
    if args.mode in ["all-time", "both"]:
        run_scraper(discipline_mappings, mode="all-time", max_workers=args.workers)

    