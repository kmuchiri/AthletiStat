import click
from datetime import datetime
from core.scraper import Scraper
from core.preprocessing import Preprocessor
from core.generator import DatasetGenerator, DatasetSplitter
from scripts.fetch_info import fetch_info


@click.command()
@click.option('--scraper', type=click.Choice(['seasons', 'all-time']), help='Scrape data for seasons or all-time.')
@click.option('--preprocessing', type=click.Choice(['seasons', 'all-time']), help='Preprocess scraped data.')
@click.option('--create-dataset', type=click.Choice(['seasons', 'all-time']), help='Generate datasets from preprocessed data.')
@click.option('--combine', is_flag=True, help='Combine datasets in season for all years scraped.')
@click.option('--split-dataset', type=click.Choice(['seasons', 'all-time']), help='Splits datasets according to gender, discipline, and event type.')
@click.option('--fetch-data', type=click.Choice(['seasons', 'all-time']), help='Performs --scraper, --preprocessing and --create-dataset for given mode.')
@click.option('--year', type=int, help='Year to use for seasons mode. If blank, behavior depends on the command.')
@click.option('--get-dataset-info', is_flag=True, help='Generates a txt file of dataset information; file name, file size, and row number')
def cli(scraper, preprocessing, create_dataset, combine, split_dataset, fetch_data, year, fetch_info):
    """AthletiStat CLI"""
    
    current_year = datetime.now().year

    if fetch_data:
        click.echo(f"Running fetch-data for {fetch_data}...")
        s_year = year if year else current_year
        Scraper(mode=fetch_data).run(year=s_year if fetch_data == 'seasons' else None)
        Preprocessor(mode=fetch_data).run()
        DatasetGenerator(mode=fetch_data).run()
    
    if scraper:
        click.echo(f"Running scraper for {scraper}...")
        s_year = year if year else current_year
        Scraper(mode=scraper).run(year=s_year if scraper == 'seasons' else None)
        
    if preprocessing:
        click.echo(f"Running preprocessing for {preprocessing}...")
        # Note: Preprocessor currently processes all years as implemented
        Preprocessor(mode=preprocessing).run()

    if create_dataset:
        click.echo(f"Creating dataset for {create_dataset}...")
        # Note: DatasetGenerator currently processes all years as implemented
        DatasetGenerator(mode=create_dataset).run()
        
    if combine:
        click.echo("Combining datasets...")
        DatasetGenerator(mode="seasons").run(combine=True)
        
    if split_dataset:
        click.echo(f"Splitting dataset for {split_dataset}...")
        DatasetSplitter(mode=split_dataset).run()

    if fetch_info:
        click.echo("Fetching dataset information...")
        fetch_info().run()