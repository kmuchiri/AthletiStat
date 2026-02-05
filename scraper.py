# Imports

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

today = datetime.now().strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%Y-%m-%d %H%M%S")

log_dir = os.path.join("logs",today)
os.makedirs(log_dir,exist_ok=True)

print (current_time)

session = requests.Session()
retries = Retry(
	total = 5
	backoff_factor = 1
	status_forcelist=(439, 500, 502, 503, 504),
	allowed_methods=("GET", "HEAD", "OPTIONS"),
)

