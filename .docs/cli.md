# CLI

--scraper (options: seasons, all-time)
- seasons
    - year: int (if blank scrape current year)

--preprocessing (options: seasons, all-time)
- seasons
    - year: int (if blank preprocess all years)


--create-dataset (options: seasons, all-time)
- seasons
    - year: int (if blank generate datasets for all years)


--combine
- combines datasets in season for all years scraped

--split-dataset(options: seasons, all-time)
- splits datasets according to gender, discipline, and event type


--fetch-data(options: seasons, all-time)
- performs --scraper, --preprocessing and --create-dataset for given mode