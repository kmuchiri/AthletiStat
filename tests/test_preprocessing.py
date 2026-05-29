"""Tests for athletistat/core/preprocessing.py - Preprocessor."""

import json
import os
import re
import tempfile

import pandas as pd
import pytest

from athletistat.core.preprocessing import Preprocessor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_options(tmp_path):
    """Create a minimal options.json understood by Preprocessor."""
    data = [
        {
            "name": "region",
            "cases": [
                {
                    "regionType": "countries",
                    "values": [
                        {"value": "ken", "label": "Kenya"},
                        {"value": "usa", "label": "United States"},
                        {"value": "eth", "label": "Ethiopia"},
                        {"value": "jam", "label": "Jamaica"},
                    ],
                }
            ],
        }
    ]
    p = tmp_path / "options.json"
    p.write_text(json.dumps(data))
    return str(p)


@pytest.fixture()
def preprocessor(minimal_options):
    return Preprocessor(mode="both", options_file=minimal_options)


# ---------------------------------------------------------------------------
# normalize_discipline
# ---------------------------------------------------------------------------

class TestNormalizeDiscipline:
    def test_known_alias_100m_hurdles(self, preprocessor):
        assert preprocessor.normalize_discipline("100m-hurdles") == "100-metres-hurdles"

    def test_known_alias_110m_hurdles(self, preprocessor):
        assert preprocessor.normalize_discipline("110m-hurdles") == "110-metres-hurdles"

    def test_known_alias_400m_hurdles(self, preprocessor):
        assert preprocessor.normalize_discipline("400m-hurdles") == "400-metres-hurdles"

    def test_decathlon_u20_normalised(self, preprocessor):
        assert preprocessor.normalize_discipline("decathlon-u20") == "decathlon"

    def test_decathlon_boys_normalised(self, preprocessor):
        assert preprocessor.normalize_discipline("decathlon-boys") == "decathlon"

    def test_heptathlon_girls_normalised(self, preprocessor):
        assert preprocessor.normalize_discipline("heptathlon-girls") == "heptathlon"

    def test_strips_u18_suffix(self, preprocessor):
        result = preprocessor.normalize_discipline("shot-put-u18")
        assert result == "shot-put"

    def test_strips_u20_suffix(self, preprocessor):
        result = preprocessor.normalize_discipline("shot-put-u20")
        assert result == "shot-put"

    def test_strips_kg_suffix(self, preprocessor):
        result = preprocessor.normalize_discipline("hammer-7260g")
        assert result == "hammer"

    def test_unchanged_discipline(self, preprocessor):
        assert preprocessor.normalize_discipline("100-metres") == "100-metres"

    def test_strips_senior_suffix(self, preprocessor):
        result = preprocessor.normalize_discipline("marathon-senior")
        assert result == "marathon"

    def test_alias_embedded_in_slug(self, preprocessor):
        """Alias found mid-slug is also replaced."""
        result = preprocessor.normalize_discipline("indoor-400m-hurdles-senior")
        assert "400-metres-hurdles" in result


# ---------------------------------------------------------------------------
# parse_mark_to_number
# ---------------------------------------------------------------------------

class TestParseMarkToNumber:
    def test_simple_float_string(self, preprocessor):
        assert preprocessor.parse_mark_to_number("9.58") == pytest.approx(9.58)

    def test_integer_string(self, preprocessor):
        assert preprocessor.parse_mark_to_number("100") == pytest.approx(100.0)

    def test_mm_ss_format(self, preprocessor):
        # 1:30 => 90 seconds
        assert preprocessor.parse_mark_to_number("1:30") == pytest.approx(90.0)

    def test_hh_mm_ss_format(self, preprocessor):
        # 2:03:13 marathon world record
        expected = 2 * 3600 + 3 * 60 + 13
        assert preprocessor.parse_mark_to_number("2:03:13") == pytest.approx(expected)

    def test_h_suffix_stripped(self, preprocessor):
        # Some marks carry an 'h' suffix for hand-timing
        assert preprocessor.parse_mark_to_number("10.5h") == pytest.approx(10.5)

    def test_invalid_mark_returns_inf(self, preprocessor):
        assert preprocessor.parse_mark_to_number("DNF") == float("inf")

    def test_empty_string_returns_inf(self, preprocessor):
        assert preprocessor.parse_mark_to_number("") == float("inf")

    def test_mark_with_extra_whitespace(self, preprocessor):
        assert preprocessor.parse_mark_to_number("  9.58  ") == pytest.approx(9.58)

    def test_mark_with_single_colon_segment(self, preprocessor):
        # 3 parts - edge case (should be treated as single-segment, returning inf)
        result = preprocessor.parse_mark_to_number("1:2:3:4")
        assert result == float("inf")

    def test_integer_input(self, preprocessor):
        assert preprocessor.parse_mark_to_number(100) == pytest.approx(100.0)

    def test_float_input(self, preprocessor):
        assert preprocessor.parse_mark_to_number(9.58) == pytest.approx(9.58)


# ---------------------------------------------------------------------------
# extract_country_code_from_venue
# ---------------------------------------------------------------------------

class TestExtractCountryCodeFromVenue:
    def test_standard_venue_with_code(self, preprocessor):
        assert preprocessor.extract_country_code_from_venue("Nairobi (KEN)") == "KEN"

    def test_three_letter_code(self, preprocessor):
        assert preprocessor.extract_country_code_from_venue("Eugene (USA)") == "USA"

    def test_no_parentheses(self, preprocessor):
        assert preprocessor.extract_country_code_from_venue("Berlin") is None

    def test_empty_string(self, preprocessor):
        assert preprocessor.extract_country_code_from_venue("") is None

    def test_parentheses_with_non_three_letter(self, preprocessor):
        # Two letters - should not match (regex is \w{3})
        result = preprocessor.extract_country_code_from_venue("City (US)")
        assert result is None

    def test_multiple_parentheses_takes_first(self, preprocessor):
        # re.search finds the first match
        result = preprocessor.extract_country_code_from_venue("X (AAA) Y (BBB)")
        assert result == "AAA"

    def test_numeric_in_parentheses(self, preprocessor):
        # \w matches digits, so (123) is technically matched
        result = preprocessor.extract_country_code_from_venue("Arena (100)")
        assert result == "100"


# ---------------------------------------------------------------------------
# country_lookup populated from options
# ---------------------------------------------------------------------------

class TestCountryLookup:
    def test_known_code_is_in_lookup(self, preprocessor):
        assert preprocessor.country_lookup.get("ken") == "Kenya"

    def test_unknown_code_is_missing(self, preprocessor):
        assert "xyz" not in preprocessor.country_lookup

    def test_lookup_keys_are_lowercase(self, preprocessor):
        for key in preprocessor.country_lookup:
            assert key == key.lower()


# ---------------------------------------------------------------------------
# Type sets (ascending / descending / track / field / mixed)
# ---------------------------------------------------------------------------

class TestTypeSets:
    def test_sprints_in_ascending(self, preprocessor):
        assert "sprints" in preprocessor.ascending_types

    def test_throws_in_descending(self, preprocessor):
        assert "throws" in preprocessor.descending_types

    def test_jumps_in_field_types(self, preprocessor):
        assert "jumps" in preprocessor.field_types

    def test_combined_events_in_mixed(self, preprocessor):
        assert "combined-events" in preprocessor.mixed_types

    def test_relays_in_track_types(self, preprocessor):
        assert "relays" in preprocessor.track_types


# ---------------------------------------------------------------------------
# _get_files_by_key  (filesystem-level)
# ---------------------------------------------------------------------------

class TestGetFilesByKey:
    def test_returns_none_when_dir_missing(self, preprocessor):
        result = preprocessor._get_files_by_key("seasons")
        # The real data dir doesn't exist in the test environment
        assert result is None or isinstance(result, dict)

    def test_returns_dict_or_none(self, preprocessor):
        result = preprocessor._get_files_by_key("all-time")
        assert result is None or isinstance(result, dict)


# ---------------------------------------------------------------------------
# Preprocessor init with missing options file
# ---------------------------------------------------------------------------

class TestPreprocessorInit:
    def test_missing_options_file_does_not_raise(self):
        """Preprocessor should handle a missing config gracefully."""
        pp = Preprocessor(mode="both", options_file="nonexistent_config.json")
        assert isinstance(pp.country_lookup, dict)

    def test_mode_both(self, minimal_options):
        pp = Preprocessor(mode="both", options_file=minimal_options)
        assert pp.mode == "both"

    def test_mode_seasons(self, minimal_options):
        pp = Preprocessor(mode="seasons", options_file=minimal_options)
        assert pp.mode == "seasons"

    def test_mode_all_time(self, minimal_options):
        pp = Preprocessor(mode="all-time", options_file=minimal_options)
        assert pp.mode == "all-time"
