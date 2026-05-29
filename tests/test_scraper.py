"""Tests for athletistat/core/scraper.py — Scraper."""

import json
import os
import threading

import pytest
import requests

from unittest.mock import MagicMock, patch, mock_open, call
from athletistat.core.scraper import Scraper


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_options(tmp_path):
    """Writes a minimal options.json and returns its path."""
    data = [
        {
            "name": "disciplineCode",
            "cases": [
                {
                    "gender": "male",
                    "ageCategory": "senior",
                    "values": [
                        {
                            "disciplineNameUrlSlug": "100-metres",
                            "typeNameUrlSlug": "sprints",
                        },
                        {
                            "disciplineNameUrlSlug": "shot-put",
                            "typeNameUrlSlug": "throws",
                        },
                    ],
                },
                {
                    "gender": "female",
                    "ageCategory": "senior",
                    "values": [
                        {
                            "disciplineNameUrlSlug": "100-metres",
                            "typeNameUrlSlug": "sprints",
                        },
                    ],
                },
            ],
        }
    ]
    p = tmp_path / "options.json"
    p.write_text(json.dumps(data))
    return str(p)


@pytest.fixture()
def scraper(minimal_options, tmp_path, monkeypatch):
    """Return a Scraper instance with patched paths so tests don't write to real dirs."""
    monkeypatch.chdir(tmp_path)
    return Scraper(mode="both", options_file=minimal_options)


# ---------------------------------------------------------------------------
# _load_mappings
# ---------------------------------------------------------------------------

class TestLoadMappings:
    def test_male_senior_disciplines_loaded(self, scraper):
        key = ("male", "senior")
        assert key in scraper.mappings

    def test_female_senior_disciplines_loaded(self, scraper):
        key = ("female", "senior")
        assert key in scraper.mappings

    def test_discipline_tuples_are_strings(self, scraper):
        for key, values in scraper.mappings.items():
            for slug, type_slug in values:
                assert isinstance(slug, str)
                assert isinstance(type_slug, str)

    def test_correct_discipline_count_male(self, scraper):
        assert len(scraper.mappings[("male", "senior")]) == 2

    def test_correct_discipline_count_female(self, scraper):
        assert len(scraper.mappings[("female", "senior")]) == 1

    def test_entries_without_slugs_are_skipped(self, tmp_path, monkeypatch):
        """Values missing required keys are omitted from mappings."""
        data = [
            {
                "name": "disciplineCode",
                "cases": [
                    {
                        "gender": "male",
                        "ageCategory": "senior",
                        "values": [
                            {"noSlugHere": "value"},  # should be skipped
                            {"disciplineNameUrlSlug": "200-metres", "typeNameUrlSlug": "sprints"},
                        ],
                    }
                ],
            }
        ]
        p = tmp_path / "opts.json"
        p.write_text(json.dumps(data))
        monkeypatch.chdir(tmp_path)
        s = Scraper(mode="seasons", options_file=str(p))
        assert len(s.mappings[("male", "senior")]) == 1


# ---------------------------------------------------------------------------
# build_jobs
# ---------------------------------------------------------------------------

class TestBuildJobs:
    def test_build_jobs_seasons_returns_list(self, scraper):
        jobs = scraper.build_jobs("seasons", year=2024)
        assert isinstance(jobs, list)
        assert len(jobs) > 0

    def test_build_jobs_all_time_returns_list(self, scraper):
        jobs = scraper.build_jobs("all-time")
        assert isinstance(jobs, list)
        assert len(jobs) > 0

    def test_job_tuple_length(self, scraper):
        jobs = scraper.build_jobs("seasons", year=2024)
        for job in jobs:
            # (gender, age_category, discipline_slug, type_slug, output_dir, mode, year)
            assert len(job) == 7

    def test_job_mode_field(self, scraper):
        jobs = scraper.build_jobs("seasons", year=2023)
        for _, _, _, _, _, mode, _ in jobs:
            assert mode == "seasons"

    def test_job_year_field(self, scraper):
        jobs = scraper.build_jobs("seasons", year=2021)
        for _, _, _, _, _, _, year in jobs:
            assert year == 2021

    def test_all_time_jobs_year_is_none(self, scraper):
        jobs = scraper.build_jobs("all-time")
        for _, _, _, _, _, _, year in jobs:
            assert year is None

    def test_output_dir_created(self, scraper, tmp_path):
        scraper.build_jobs("seasons", year=2024)
        # At least one output dir under data/processing/output/seasons/2024 should exist
        base = tmp_path / "data" / "processing" / "output" / "seasons" / "2024"
        assert base.exists()

    def test_all_time_output_dir_created(self, scraper, tmp_path):
        scraper.build_jobs("all-time")
        base = tmp_path / "data" / "processing" / "output" / "all-time"
        assert base.exists()


# ---------------------------------------------------------------------------
# _get_queue_info
# ---------------------------------------------------------------------------

class TestGetQueueInfo:
    def test_seasons_queue_path_contains_year(self, scraper):
        path = scraper._get_queue_info("seasons", year=2020)
        assert "2020" in path

    def test_all_time_queue_path_contains_today(self, scraper):
        path = scraper._get_queue_info("all-time")
        assert scraper.today in path

    def test_seasons_queue_dir_created(self, scraper, tmp_path):
        scraper._get_queue_info("seasons", year=2020)
        assert (tmp_path / "queues" / "seasons").exists()

    def test_all_time_queue_dir_created(self, scraper, tmp_path):
        scraper._get_queue_info("all-time")
        assert (tmp_path / "queues" / "all-time").exists()


# ---------------------------------------------------------------------------
# scrape_event
# ---------------------------------------------------------------------------

def _make_html_table(rows):
    """Build a minimal records-table HTML page."""
    row_html = ""
    for row in rows:
        tds = "".join(f"<td>{cell}</td>" for cell in row)
        row_html += f"<tr>{tds}</tr>"
    return f"""
    <html><body>
    <table class="records-table">
      <tbody>{row_html}</tbody>
    </table>
    </body></html>
    """


def _make_response(html, status=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _row(rank="1", mark="9.58", wind="0.0", competitor="Bolt U", dob="21 Aug 1986",
         nat="JAM", pos="1", extra="", venue="Berlin (GER)", date="16 Aug 2009", score="1244"):
    """Return 11 TD cells for a valid athlete row."""
    return [rank, mark, wind, competitor, dob, nat, pos, extra, venue, date, score]


class TestScrapeEvent:
    def _make_scraper(self, minimal_options, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        return Scraper(mode="seasons", options_file=minimal_options)

    def test_returns_true_on_success(self, minimal_options, tmp_path, monkeypatch):
        s = self._make_scraper(minimal_options, tmp_path, monkeypatch)
        # First call returns one-row page, second call returns empty (no table)
        response1 = _make_response(_make_html_table([_row()]))
        response2 = _make_response("<html></html>")
        s.session.get = MagicMock(side_effect=[response1, response2])

        result = s.scrape_event(
            "male", "senior", "100-metres", "sprints",
            str(tmp_path / "out"), mode="seasons", year=2024
        )
        assert result is True

    def test_returns_false_on_request_error(self, minimal_options, tmp_path, monkeypatch):
        s = self._make_scraper(minimal_options, tmp_path, monkeypatch)
        s.session.get = MagicMock(side_effect=requests.exceptions.ConnectionError("err"))

        result = s.scrape_event(
            "male", "senior", "100-metres", "sprints",
            str(tmp_path / "out"), mode="seasons", year=2024
        )
        assert result is False

    def test_csv_saved_when_data_collected(self, minimal_options, tmp_path, monkeypatch):
        s = self._make_scraper(minimal_options, tmp_path, monkeypatch)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        response1 = _make_response(_make_html_table([_row()]))
        response2 = _make_response("<html></html>")
        s.session.get = MagicMock(side_effect=[response1, response2])

        s.scrape_event(
            "male", "senior", "100-metres", "sprints",
            str(out_dir), mode="seasons", year=2024
        )

        csv_files = list(out_dir.glob("*.csv"))
        assert len(csv_files) == 1

    def test_no_csv_saved_when_no_data(self, minimal_options, tmp_path, monkeypatch):
        s = self._make_scraper(minimal_options, tmp_path, monkeypatch)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        response = _make_response("<html></html>")
        s.session.get = MagicMock(return_value=response)

        s.scrape_event(
            "male", "senior", "100-metres", "sprints",
            str(out_dir), mode="seasons", year=2024
        )

        csv_files = list(out_dir.glob("*.csv"))
        assert len(csv_files) == 0

    def test_rows_with_fewer_than_11_cols_skipped(self, minimal_options, tmp_path, monkeypatch):
        s = self._make_scraper(minimal_options, tmp_path, monkeypatch)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        short_row = ["1", "9.58"]  # only 2 cols — must be skipped
        response1 = _make_response(_make_html_table([short_row, _row()]))
        response2 = _make_response("<html></html>")
        s.session.get = MagicMock(side_effect=[response1, response2])

        s.scrape_event(
            "male", "senior", "100-metres", "sprints",
            str(out_dir), mode="seasons", year=2024
        )

        import pandas as pd
        csv_file = next(out_dir.glob("*.csv"))
        df = pd.read_csv(csv_file)
        # Only the valid _row() should be recorded
        assert len(df) == 1

    def test_error_is_logged(self, minimal_options, tmp_path, monkeypatch):
        s = self._make_scraper(minimal_options, tmp_path, monkeypatch)
        s.session.get = MagicMock(side_effect=requests.exceptions.Timeout("timed out"))

        s.scrape_event(
            "male", "senior", "100-metres", "sprints",
            str(tmp_path / "out"), mode="seasons", year=2024
        )

        log_dir = tmp_path / "logs" / "seasons" / s.today
        log_files = list(log_dir.glob("scrape_errors_*.log"))
        assert len(log_files) == 1
        assert "FAILED" in log_files[0].read_text()

    def test_all_time_url_used_when_mode_is_all_time(self, minimal_options, tmp_path, monkeypatch):
        s = self._make_scraper(minimal_options, tmp_path, monkeypatch)
        responses = [_make_response(_make_html_table([_row()])), _make_response("<html></html>")]
        s.session.get = MagicMock(side_effect=responses)

        s.scrape_event(
            "male", "senior", "100-metres", "sprints",
            str(tmp_path / "out"), mode="all-time", year=None
        )

        called_url = s.session.get.call_args_list[0][0][0]
        assert "all-time-toplists" in called_url

    def test_seasons_url_used_when_mode_is_seasons(self, minimal_options, tmp_path, monkeypatch):
        s = self._make_scraper(minimal_options, tmp_path, monkeypatch)
        responses = [_make_response("<html></html>")]
        s.session.get = MagicMock(side_effect=responses)

        s.scrape_event(
            "male", "senior", "100-metres", "sprints",
            str(tmp_path / "out"), mode="seasons", year=2024
        )

        called_url = s.session.get.call_args_list[0][0][0]
        assert "toplists" in called_url
        assert "2024" in called_url


# ---------------------------------------------------------------------------
# Scraper.run dispatch
# ---------------------------------------------------------------------------

class TestScraperRun:
    def test_run_seasons_only(self, minimal_options, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s = Scraper(mode="seasons", options_file=minimal_options)
        with patch.object(s, "run_scraper") as mock_run:
            s.run(max_workers=1, year=2024)
            mock_run.assert_called_once_with("seasons", max_workers=1, year=2024)

    def test_run_all_time_only(self, minimal_options, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s = Scraper(mode="all-time", options_file=minimal_options)
        with patch.object(s, "run_scraper") as mock_run:
            s.run(max_workers=1)
            mock_run.assert_called_once_with("all-time", max_workers=1)

    def test_run_both_calls_scraper_twice(self, minimal_options, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s = Scraper(mode="both", options_file=minimal_options)
        with patch.object(s, "run_scraper") as mock_run:
            s.run(max_workers=1, year=2024)
            assert mock_run.call_count == 2

    def test_run_defaults_year_to_current(self, minimal_options, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s = Scraper(mode="seasons", options_file=minimal_options)
        with patch.object(s, "run_scraper") as mock_run:
            s.run(max_workers=1)  # year=None by default
            _, kwargs = mock_run.call_args
            assert kwargs["year"] == s.current_year
