import click
from datetime import datetime
from athletistat.core.scraper import Scraper
from athletistat.core.preprocessing import Preprocessor
from athletistat.core.generator import DatasetGenerator, DatasetSplitter
from athletistat.scripts.fetch_info import DatasetInfo
from athletistat.console import cprint, header, divider, success, info, step, warn, Colors, Symbols


@click.command()
@click.option('--scraper', type=click.Choice(['seasons', 'all-time']), help='Scrape data for seasons or all-time.')
@click.option('--preprocessing', type=click.Choice(['seasons', 'all-time']), help='Preprocess scraped data.')
@click.option('--create-dataset', type=click.Choice(['seasons', 'all-time']), help='Generate datasets from preprocessed data.')
@click.option('--combine', is_flag=True, help='Combine datasets in season for all years scraped.')
@click.option('--split-dataset', type=click.Choice(['seasons', 'all-time']), help='Splits datasets according to gender, discipline, and event type.')
@click.option('--fetch-data', type=click.Choice(['seasons', 'all-time']), help='Performs --scraper, --preprocessing and --create-dataset for given mode.')
@click.option('--year', type=int, help='Year to use for seasons mode. If blank, behavior depends on the command.')
@click.option('--dataset-info', is_flag=True, help='Generates a txt file of dataset information; file name, file size, and row number')

def cli(scraper, preprocessing, create_dataset, combine, split_dataset, fetch_data, dataset_info, year):
    """AthletiStat CLI"""

    header("AthletiStat  —  Track & Field Data Pipeline")
    current_year = datetime.now().year

    if fetch_data:
        s_year = year if year else current_year
        info(f"fetch-data mode: {fetch_data.upper()}  |  year: {s_year if fetch_data == 'seasons' else 'all-time'}")
        divider()
        step(f"[1/3] Starting scraper...")
        Scraper(mode=fetch_data).run(year=s_year if fetch_data == 'seasons' else None)
        step(f"[2/3] Running preprocessing...")
        Preprocessor(mode=fetch_data).run()
        step(f"[3/3] Generating datasets...")
        DatasetGenerator(mode=fetch_data).run()
        divider()
        success("fetch-data pipeline complete.")

    if scraper:
        s_year = year if year else current_year
        info(f"Scraper mode: {scraper.upper()}  |  year: {s_year if scraper == 'seasons' else 'all-time'}")
        Scraper(mode=scraper).run(year=s_year if scraper == 'seasons' else None)

    if preprocessing:
        info(f"Preprocessing mode: {preprocessing.upper()}")
        # Note: Preprocessor currently processes all years as implemented
        Preprocessor(mode=preprocessing).run()

    if create_dataset:
        info(f"Generating dataset — mode: {create_dataset.upper()}")
        # Note: DatasetGenerator currently processes all years as implemented
        DatasetGenerator(mode=create_dataset).run()

    if combine:
        info("Combining season datasets into a single aggregated file...")
        DatasetGenerator(mode="seasons").run(combine=True)

    if split_dataset:
        info(f"Splitting dataset — mode: {split_dataset.upper()}")
        DatasetSplitter(mode=split_dataset).run()

    if dataset_info:
        info("Fetching dataset information...")
        DatasetInfo().run()