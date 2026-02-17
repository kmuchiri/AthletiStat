'''
IMPORTS
'''
import os
import json
import time
from datetime import datetime

#	scraping
import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPAdapter

import urllib3 
from urllib3.util.retry import Retry
from urllib3.exceotions import InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

#Time and date
today = datetime.now().strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%Y-%m-%d %H%M%S")
#Directories
log_dir = os.path.join("logs",today)
os.makedirs(log_dir,exist_ok=True)

print (current_time)

'''
SESSIONS
'''

session = requests.Session()
retries = Retry(
	total = 5,
	backoff_factor = 1,
	status_forcelist=(429, 500, 502, 503, 504),
	allowed_methods=("GET", "HEAD", "OPTIONS"),
)
session.mount("https://", HTTPAdapter(max_retries=retries))
session.mount("http://", HTTPAdapter(max_retries=retries))

with open ("options.json","r") as f:
	options_data = json.load(f)

discpline_mappings = {}
for entry in options_data:
	if entry.get("name") == "discplineCode":
		for case in entry.get("cases",[]):
			key = (case.get("gender"), case.get(ageCategory))
			values = case.get("values",[])
			discpline_mappings[key] = [
				(v["disciplineNameUrlSlug"], v["typeNameUrlSlug"])
				for v in values if "disciplineNameUrlSlug" in v and "typeNameUrlSlug" in v
			]
year = int(datetime.now().strftime("%Y"))

#Base URL (All-time)
BASE_URL = (
    "https://worldathletics.org/records/all-time-toplists/{type_slug}/{discipline_slug}/all/{gender}/{age_category}"
    "?regionType=world&page={page}&bestResultsOnly=false&firstDay=1900-01-01&lastDay={today}&maxResultsByCountry=all&ageCategory={age_category}"
)


#Base URL (Seasons)
BASE_URL_SEASONS = ("https://worldathletics.org/records/toplists/{type_slug}/{discipline_slug}/all/{gender}/{age_category}/{year}?regionType=world&timing=all&windReading=all&page={page}&bestResultsOnly=false&maxResultsByCountry=all&ageCategory={age_category}")

'''
SCRAPER
'''
def scrape_event_seasons(gender,age_category,discipline_slug,type_slug,output_dir,year, max_retries=5):
    page = 1
    data = []
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    while True:
        url = BASE_URL.format(
            type_slug=type_slug,
            discipline_slug=discipline_slug,
            gender=gender,
            age_category=age_category,
            page=page,
            year=year
        )

        headers = {"User-Agent": "Mozilla/5.0"}
        success = False
        for attempt in range(max_retries):
            try:
                response = session.get(url, headers=headers, timeout=(5, 30), verify=True)
                response.raise_for_status()
                success = True
                break
            except Exception as e:
                time.sleep(1.5 ** attempt)  # exponential backoff
                if attempt == max_retries - 1:
                    with lock:
                        with open(os.path.join(log_dir, f"scrape_errors_{timestamp}.log"), "a") as log_file:
                            log_file.write(f"FAILED: {url} | {repr(e)}\n")
                    return


        if not success:
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find("table", class_="records-table")
		
        #Checks if there is a table, then checks for rows
        if not table:
            break
        rows = table.find("tbody").find_all("tr")
        if not rows:
            break

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 11:
                continue
            data.append({
                
                "rank": cols[0].text.strip(),
                "mark": cols[1].text.strip(),
                "wind":cols[2].text.strip(),
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
        time.sleep(2)
    

    #save to csv
    if data: 
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{year}_{type_slug}_{discipline_slug}_{age_category}.csv".replace(" ", "_").replace("/", "-")
        filepath = os.path.join(output_dir, filename)
        with lock:
            pd.DataFrame(data).to_csv(filepath, index=False)
            print(f" Saved {filepath}")

def scrape_event_alltime(gender, age_category, discipline_slug, type_slug, output_dir, today, max_retries=5):
    page = 1
    data = []
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    while True:
        url = BASE_URL.format(
            type_slug=type_slug,
            discipline_slug=discipline_slug,
            gender=gender,
            age_category=age_category,
            page=page,
            today=today
        )

        headers = {"User-Agent": "Mozilla/5.0"}
        success = False
        for attempt in range(max_retries):
            try:
                response = session.get(url, headers=headers, timeout=(5, 30), verify=True)
                response.raise_for_status()
                success = True
                break
            except Exception as e:
                time.sleep(2 ** attempt)  # exponential backoff
                if attempt == max_retries - 1:
                    with lock:
                        with open(os.path.join(log_dir, f"scrape_errors_{timestamp}.log"), "a") as log_file:
                            log_file.write(f"FAILED: {url} | {repr(e)}\n")
                    return


        if not success:
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find("table", class_="records-table")
        if not table:
            break

        rows = table.find("tbody").find_all("tr")
        if not rows:
            break

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 11:
                continue
            data.append({
                
                "rank": cols[0].text.strip(),
                "mark": cols[1].text.strip(),
                "wind":cols[2].text.strip(),
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
        time.sleep(0.2) #Brief pause

    # Save to CSV
    if data:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{type_slug}_{discipline_slug}_{age_category}.csv".replace(" ", "_").replace("/", "-")
        filepath = os.path.join(output_dir, filename)
        with lock:
            pd.DataFrame(data).to_csv(filepath, index=False)
            print(f" Saved {filepath}")

'''
MULTITHREADING
'''
def get_scrape_jobs_seasons(year):
    jobs = []
    for (gender, age_category), discipline_list in discipline_mappings.items():
        output_dir = os.path.join(f"processing/output/{year}/", gender)
        os.makedirs(output_dir,exist_ok=True)
        for discipline_slug, type_slug in discipline_list:
            jobs.append((gender, age_category, discipline_slug, type_slug, output_dir,year))
    return jobs

def run_multithreaded_scrape_seasons(max_workers=10,year=2025):
    jobs = get_scrape_jobs(year)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {executor.submit(scrape_event, *job): job for job in jobs}
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                future.result()
            except Exception as e:
                with lock:
                    with open(os.path.join(log_dir, f"scrape_errors_{current_time}.log"), "a") as log_file:
                        log_file.write(f"UNCAUGHT ERROR in job {job}: {repr(e)}\n")
def get_scrape_jobs_alltime():
    jobs = []
    for (gender, age_category), discipline_list in discipline_mappings.items():
        output_dir = os.path.join("processing/output", gender)
        for discipline_slug, type_slug in discipline_list:
            jobs.append((gender, age_category, discipline_slug, type_slug, output_dir,today))
    return jobs

def run_multithreaded_scrape_alltime(max_workers=30): 
    jobs = get_scrape_jobs()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {executor.submit(scrape_event, *job): job for job in jobs}
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                future.result()
            except Exception as e:
                with lock:
                    with open(os.path.join(log_dir, f"scrape_errors_{current_time}.log"), "a") as log_file:
                        log_file.write(f"UNCAUGHT ERROR in job {job}: {repr(e)}\n")

'''
RUN SEASONS
'''
def run_season():
	print("Running Seasons Scrape")
	start_time = time.time()
	run_multithreaded_scrape_seasons(max_workers=30,year=2025)
	end_time = time.time()

'''
RUN ALLTIME
'''
def run_alltime():
	start_time = time.time()
	run_multithreaded_scrape_alltime(max_workers=30)
	end_time = time.time()
	print("-------------------------------------- ")
	total_time = int(end_time - start_time)
	time_min = total_time / 60
	print(f" Scraping completed in {total_time:.2f} seconds")
	print(f" Scraping completed in {time_min:.2f} minutes")
	print(" ")