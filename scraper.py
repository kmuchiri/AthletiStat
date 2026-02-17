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
	status_forcelist=(439, 500, 502, 503, 504),
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