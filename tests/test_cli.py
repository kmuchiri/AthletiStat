"""Tests for the CLI entry point (athletistat/cli/cli.py)."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from athletistat.cli.cli import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _runner():
    return CliRunner()


def _patch_all():
    """Context-manager that silences all real side-effects in the CLI."""
    return (
        patch("athletistat.cli.cli.Scraper"),
        patch("athletistat.cli.cli.Preprocessor"),
        patch("athletistat.cli.cli.DatasetGenerator"),
        patch("athletistat.cli.cli.DatasetSplitter"),
        patch("athletistat.cli.cli.DatasetInfo"),
    )


# ---------------------------------------------------------------------------
# Basic invocation
# ---------------------------------------------------------------------------

class TestCliInvocation:
    def test_no_args_exits_zero(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper"), \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator"), \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            result = runner.invoke(cli, [])
        assert result.exit_code == 0

    def test_help_exits_zero(self):
        result = _runner().invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_help_mentions_scraper(self):
        result = _runner().invoke(cli, ["--help"])
        assert "scraper" in result.output.lower()


# ---------------------------------------------------------------------------
# --scraper flag
# ---------------------------------------------------------------------------

class TestScraperFlag:
    def test_scraper_seasons_instantiates_scraper(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper") as mock_scraper, \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator"), \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_scraper.return_value = mock_instance
            runner.invoke(cli, ["--scraper", "seasons"])
            mock_scraper.assert_called_once_with(mode="seasons")
            mock_instance.run.assert_called_once()

    def test_scraper_all_time_instantiates_scraper(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper") as mock_scraper, \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator"), \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_scraper.return_value = mock_instance
            runner.invoke(cli, ["--scraper", "all-time"])
            mock_scraper.assert_called_with(mode="all-time")

    def test_scraper_invalid_choice_exits_nonzero(self):
        result = _runner().invoke(cli, ["--scraper", "invalid"])
        assert result.exit_code != 0

    def test_scraper_seasons_with_year_passes_year(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper") as mock_scraper, \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator"), \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_scraper.return_value = mock_instance
            runner.invoke(cli, ["--scraper", "seasons", "--year", "2021"])
            mock_instance.run.assert_called_once_with(year=2021)


# ---------------------------------------------------------------------------
# --preprocessing flag
# ---------------------------------------------------------------------------

class TestPreprocessingFlag:
    def test_preprocessing_seasons_instantiates_preprocessor(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper"), \
             patch("athletistat.cli.cli.Preprocessor") as mock_pp, \
             patch("athletistat.cli.cli.DatasetGenerator"), \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_pp.return_value = mock_instance
            runner.invoke(cli, ["--preprocessing", "seasons"])
            mock_pp.assert_called_once_with(mode="seasons")
            mock_instance.run.assert_called_once()

    def test_preprocessing_all_time(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper"), \
             patch("athletistat.cli.cli.Preprocessor") as mock_pp, \
             patch("athletistat.cli.cli.DatasetGenerator"), \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_pp.return_value = mock_instance
            runner.invoke(cli, ["--preprocessing", "all-time"])
            mock_pp.assert_called_with(mode="all-time")


# ---------------------------------------------------------------------------
# --create-dataset flag
# ---------------------------------------------------------------------------

class TestCreateDatasetFlag:
    def test_create_dataset_seasons_instantiates_generator(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper"), \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator") as mock_gen, \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_gen.return_value = mock_instance
            runner.invoke(cli, ["--create-dataset", "seasons"])
            mock_gen.assert_called_once_with(mode="seasons")
            mock_instance.run.assert_called_once()

    def test_create_dataset_all_time(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper"), \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator") as mock_gen, \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_gen.return_value = mock_instance
            runner.invoke(cli, ["--create-dataset", "all-time"])
            mock_gen.assert_called_with(mode="all-time")


# ---------------------------------------------------------------------------
# --combine flag
# ---------------------------------------------------------------------------

class TestCombineFlag:
    def test_combine_calls_generator_run_with_combine(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper"), \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator") as mock_gen, \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_gen.return_value = mock_instance
            runner.invoke(cli, ["--combine"])
            mock_gen.assert_called_with(mode="seasons")
            mock_instance.run.assert_called_once_with(combine=True)


# ---------------------------------------------------------------------------
# --split-dataset flag
# ---------------------------------------------------------------------------

class TestSplitDatasetFlag:
    def test_split_dataset_seasons_instantiates_splitter(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper"), \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator"), \
             patch("athletistat.cli.cli.DatasetSplitter") as mock_split, \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_split.return_value = mock_instance
            runner.invoke(cli, ["--split-dataset", "seasons"])
            mock_split.assert_called_once_with(mode="seasons")
            mock_instance.run.assert_called_once()

    def test_split_dataset_all_time(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper"), \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator"), \
             patch("athletistat.cli.cli.DatasetSplitter") as mock_split, \
             patch("athletistat.cli.cli.DatasetInfo"):
            mock_instance = MagicMock()
            mock_split.return_value = mock_instance
            runner.invoke(cli, ["--split-dataset", "all-time"])
            mock_split.assert_called_with(mode="all-time")


# ---------------------------------------------------------------------------
# --dataset-info flag
# ---------------------------------------------------------------------------

class TestDatasetInfoFlag:
    def test_dataset_info_instantiates_and_runs(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper"), \
             patch("athletistat.cli.cli.Preprocessor"), \
             patch("athletistat.cli.cli.DatasetGenerator"), \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo") as mock_di:
            mock_instance = MagicMock()
            mock_di.return_value = mock_instance
            runner.invoke(cli, ["--dataset-info"])
            mock_di.assert_called_once_with()
            mock_instance.run.assert_called_once()


# ---------------------------------------------------------------------------
# --fetch-data flag (full pipeline)
# ---------------------------------------------------------------------------

class TestFetchDataFlag:
    def test_fetch_data_seasons_runs_all_three_steps(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper") as mock_scraper, \
             patch("athletistat.cli.cli.Preprocessor") as mock_pp, \
             patch("athletistat.cli.cli.DatasetGenerator") as mock_gen, \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            for m in (mock_scraper, mock_pp, mock_gen):
                m.return_value = MagicMock()
            runner.invoke(cli, ["--fetch-data", "seasons", "--year", "2022"])
            mock_scraper.assert_called_once_with(mode="seasons")
            mock_pp.assert_called_once_with(mode="seasons")
            mock_gen.assert_called_once_with(mode="seasons")

    def test_fetch_data_all_time_runs_all_three_steps(self):
        runner = _runner()
        with patch("athletistat.cli.cli.Scraper") as mock_scraper, \
             patch("athletistat.cli.cli.Preprocessor") as mock_pp, \
             patch("athletistat.cli.cli.DatasetGenerator") as mock_gen, \
             patch("athletistat.cli.cli.DatasetSplitter"), \
             patch("athletistat.cli.cli.DatasetInfo"):
            for m in (mock_scraper, mock_pp, mock_gen):
                m.return_value = MagicMock()
            runner.invoke(cli, ["--fetch-data", "all-time"])
            mock_scraper.assert_called_with(mode="all-time")
            mock_pp.assert_called_with(mode="all-time")
            mock_gen.assert_called_with(mode="all-time")
