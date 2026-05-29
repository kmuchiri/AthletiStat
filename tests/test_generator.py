"""Tests for athletistat/core/generator.py — DatasetGenerator and DatasetSplitter."""

import os
import json
import pytest
import pandas as pd

from unittest.mock import patch, MagicMock
from athletistat.core.generator import DatasetGenerator, DatasetSplitter


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_df(**extra_cols):
    """Return a minimal track-and-field DataFrame."""
    data = {
        "rank": [1, 2, 3],
        "mark": ["9.58", "9.69", "9.72"],
        "wind": ["0.9", "0.0", "0.2"],
        "competitor": ["Bolt U", "Gatlin J", "Blake Y"],
        "dob": ["21 Aug 1986", "10 Feb 1982", "26 Dec 1989"],
        "nationality": ["JAM", "USA", "JAM"],
        "position": ["1", "1", "1"],
        "venue": ["Berlin (GER)", "London (GBR)", "Lausanne (SUI)"],
        "date": ["16 Aug 2009", "05 Aug 2017", "25 Aug 2011"],
        "result_score": ["1244", "1200", "1198"],
        "discipline": ["100-metres", "100-metres", "100-metres"],
        "type": ["sprints", "sprints", "sprints"],
        "sex": ["male", "male", "male"],
        "age_cat": ["senior", "senior", "senior"],
        "normalized_discipline": ["100-metres", "100-metres", "100-metres"],
        "mark_numeric": [9.58, 9.69, 9.72],
        "nat_full": ["Jamaica", "United States", "Jamaica"],
        "track_field": ["track", "track", "track"],
        "season": [2009, 2017, 2011],
    }
    data.update(extra_cols)
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# DatasetGenerator.generate_datasets — seasons
# ---------------------------------------------------------------------------

class TestDatasetGeneratorSeasons:
    def test_seasons_dir_not_found_returns_early(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = DatasetGenerator(mode="seasons")
        # combined dir doesn't exist — should not raise
        gen.generate_datasets("seasons")

    def test_seasons_csv_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        year = "2024"
        year_dir = tmp_path / "data" / "processing" / "combined" / "seasons" / year
        year_dir.mkdir(parents=True)
        df = _make_df()
        df.to_csv(year_dir / "male_sprints_100-metres.csv", index=False)

        gen = DatasetGenerator(mode="seasons")
        gen.generate_datasets("seasons")

        out = tmp_path / "data" / "datasets" / "seasons" / f"{year}_track_field_performances.csv"
        assert out.exists()

    def test_seasons_combined_df_has_all_rows(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        year = "2023"
        year_dir = tmp_path / "data" / "processing" / "combined" / "seasons" / year
        year_dir.mkdir(parents=True)
        df1 = _make_df()
        df2 = _make_df()
        df1.to_csv(year_dir / "male_sprints_100-metres.csv", index=False)
        df2.to_csv(year_dir / "female_sprints_100-metres.csv", index=False)

        gen = DatasetGenerator(mode="seasons")
        gen.generate_datasets("seasons")

        out = tmp_path / "data" / "datasets" / "seasons" / f"{year}_track_field_performances.csv"
        combined = pd.read_csv(out)
        assert len(combined) == len(df1) + len(df2)


# ---------------------------------------------------------------------------
# DatasetGenerator.generate_datasets — all-time
# ---------------------------------------------------------------------------

class TestDatasetGeneratorAllTime:
    def test_all_time_dir_not_found_returns_early(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = DatasetGenerator(mode="all-time")
        gen.generate_datasets("all-time")  # should not raise

    def test_all_time_csv_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        combined_dir = tmp_path / "data" / "processing" / "combined" / "all-time"
        combined_dir.mkdir(parents=True)
        _make_df().to_csv(combined_dir / "male_sprints_100-metres.csv", index=False)

        gen = DatasetGenerator(mode="all-time")
        gen.generate_datasets("all-time")

        out = tmp_path / "data" / "datasets" / "all-time" / "top_track_field_performances_all_time.csv"
        assert out.exists()

    def test_all_time_deduplication(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        combined_dir = tmp_path / "data" / "processing" / "combined" / "all-time"
        combined_dir.mkdir(parents=True)
        df = _make_df()
        # Write same file twice → two identical copies → deduplicated output
        df.to_csv(combined_dir / "file_a.csv", index=False)
        df.to_csv(combined_dir / "file_b.csv", index=False)

        gen = DatasetGenerator(mode="all-time")
        gen.generate_datasets("all-time")

        out = pd.read_csv(tmp_path / "data" / "datasets" / "all-time" / "top_track_field_performances_all_time.csv")
        assert len(out) == len(df)  # duplicates removed


# ---------------------------------------------------------------------------
# DatasetGenerator.combine_seasons
# ---------------------------------------------------------------------------

class TestCombineSeasons:
    def test_combine_seasons_no_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = DatasetGenerator(mode="seasons")
        gen.combine_seasons()  # should not raise

    def test_combine_seasons_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        seasons_dir = tmp_path / "data" / "datasets" / "seasons"
        seasons_dir.mkdir(parents=True)
        _make_df().to_csv(seasons_dir / "2022_track_field_performances.csv", index=False)
        _make_df().to_csv(seasons_dir / "2023_track_field_performances.csv", index=False)

        gen = DatasetGenerator(mode="seasons")
        gen.combine_seasons()

        combined = list(seasons_dir.glob("combined_track_field_performances_*.csv"))
        assert len(combined) == 1

    def test_combine_seasons_year_range_in_filename(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        seasons_dir = tmp_path / "data" / "datasets" / "seasons"
        seasons_dir.mkdir(parents=True)
        _make_df().to_csv(seasons_dir / "2020_track_field_performances.csv", index=False)
        _make_df().to_csv(seasons_dir / "2024_track_field_performances.csv", index=False)

        gen = DatasetGenerator(mode="seasons")
        gen.combine_seasons()

        combined = list(seasons_dir.glob("combined_track_field_performances_2020_2024.csv"))
        assert len(combined) == 1


# ---------------------------------------------------------------------------
# DatasetGenerator.run dispatch
# ---------------------------------------------------------------------------

class TestDatasetGeneratorRun:
    def test_run_seasons_calls_generate_datasets_seasons(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = DatasetGenerator(mode="seasons")
        with patch.object(gen, "generate_datasets") as mock_gen:
            gen.run()
            mock_gen.assert_called_once_with("seasons")

    def test_run_all_time_calls_generate_datasets_all_time(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = DatasetGenerator(mode="all-time")
        with patch.object(gen, "generate_datasets") as mock_gen:
            gen.run()
            mock_gen.assert_called_once_with("all-time")

    def test_run_both_calls_generate_datasets_twice(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = DatasetGenerator(mode="both")
        with patch.object(gen, "generate_datasets") as mock_gen, \
             patch.object(gen, "combine_seasons"):
            gen.run()
            assert mock_gen.call_count == 2

    def test_run_with_combine_calls_combine_seasons(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = DatasetGenerator(mode="seasons")
        with patch.object(gen, "generate_datasets"), \
             patch.object(gen, "combine_seasons") as mock_combine:
            gen.run(combine=True)
            mock_combine.assert_called_once()


# ---------------------------------------------------------------------------
# DatasetSplitter.get_filename_with_years
# ---------------------------------------------------------------------------

class TestGetFilenameWithYears:
    @pytest.fixture()
    def splitter(self):
        return DatasetSplitter(mode="both")

    def test_seasons_with_single_year(self, splitter):
        df = _make_df(season=[2022, 2022, 2022])
        result = splitter.get_filename_with_years("sprints", df, is_seasons=True)
        assert result == "sprints_2022.csv"

    def test_seasons_with_year_range(self, splitter):
        df = _make_df(season=[2018, 2019, 2022])
        result = splitter.get_filename_with_years("sprints", df, is_seasons=True)
        assert result == "sprints_2018-2022.csv"

    def test_not_seasons_returns_base_csv(self, splitter):
        df = _make_df()
        result = splitter.get_filename_with_years("sprints", df, is_seasons=False)
        assert result == "sprints.csv"

    def test_seasons_no_season_column(self, splitter):
        df = _make_df()
        df = df.drop(columns=["season"])
        result = splitter.get_filename_with_years("sprints", df, is_seasons=True)
        assert result == "sprints.csv"

    def test_seasons_all_nan_season(self, splitter):
        df = _make_df(season=[float("nan"), float("nan"), float("nan")])
        result = splitter.get_filename_with_years("sprints", df, is_seasons=True)
        assert result == "sprints.csv"


# ---------------------------------------------------------------------------
# DatasetSplitter.split_dataset
# ---------------------------------------------------------------------------

class TestSplitDataset:
    @pytest.fixture()
    def splitter(self):
        return DatasetSplitter(mode="both")

    def test_creates_global_individual_csv(self, splitter, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        df = _make_df()
        splitter.split_dataset(df, mode_dir=str(tmp_path / "out"), is_seasons=False)

        global_out = tmp_path / "out" / "split_global"
        assert any(f.name.startswith("individual_events") for f in global_out.iterdir())

    def test_relays_separated_from_individual(self, splitter, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        relay_row = {
            "rank": 1, "mark": "37.10", "wind": "0.0", "competitor": "Team JAM",
            "dob": None, "nationality": "JAM", "position": "1",
            "venue": "Beijing (CHN)", "date": "22 Aug 2008", "result_score": "1000",
            "discipline": "4x100-metres-relay", "type": "relays", "sex": "male",
            "age_cat": "senior", "normalized_discipline": "4x100-metres-relay",
            "mark_numeric": 37.10, "nat_full": "Jamaica", "track_field": "track",
            "season": 2008,
        }
        df = pd.concat([_make_df(), pd.DataFrame([relay_row])], ignore_index=True)
        splitter.split_dataset(df, mode_dir=str(tmp_path / "out"), is_seasons=False)

        global_out = tmp_path / "out" / "split_global"
        relay_files = [f for f in global_out.iterdir() if f.name.startswith("relay_events")]
        assert len(relay_files) == 1

    def test_split_by_type_creates_dir(self, splitter, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        df = _make_df()
        splitter.split_dataset(df, mode_dir=str(tmp_path / "out"), is_seasons=False)

        type_dir = tmp_path / "out" / "split_by_type" / "male"
        assert type_dir.exists()
        assert any(type_dir.iterdir())

    def test_split_by_discipline_creates_dir(self, splitter, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        df = _make_df()
        splitter.split_dataset(df, mode_dir=str(tmp_path / "out"), is_seasons=False)

        disc_dir = tmp_path / "out" / "split_by_discipline" / "male"
        assert disc_dir.exists()
        assert any(disc_dir.iterdir())

    def test_relay_dob_column_dropped(self, splitter, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        relay_row = {
            "rank": 1, "mark": "37.10", "wind": "0.0", "competitor": "Team JAM",
            "dob": "21 Aug 1986", "nationality": "JAM", "position": "1",
            "venue": "Beijing (CHN)", "date": "22 Aug 2008", "result_score": "1000",
            "discipline": "4x100-metres-relay", "type": "relays", "sex": "male",
            "age_cat": "senior", "normalized_discipline": "4x100-metres-relay",
            "mark_numeric": 37.10, "nat_full": "Jamaica", "track_field": "track",
            "season": 2008, "age_at_event": 21,
        }
        df = pd.DataFrame([relay_row])
        splitter.split_dataset(df, mode_dir=str(tmp_path / "out"), is_seasons=False)

        global_out = tmp_path / "out" / "split_global"
        relay_file = next(f for f in global_out.iterdir() if f.name.startswith("relay_events"))
        relay_df = pd.read_csv(relay_file)
        assert "dob" not in relay_df.columns
        assert "age_at_event" not in relay_df.columns


# ---------------------------------------------------------------------------
# DatasetSplitter.run dispatch
# ---------------------------------------------------------------------------

class TestDatasetSplitterRun:
    def test_run_calls_execute_splits(self):
        splitter = DatasetSplitter(mode="seasons")
        with patch.object(splitter, "execute_splits") as mock_exec:
            splitter.run()
            mock_exec.assert_called_once()
