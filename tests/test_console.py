"""Tests for athletistat/console.py — terminal styling utilities."""

import pytest
from unittest.mock import patch
from io import StringIO

from athletistat.console import (
    Colors, Symbols,
    cprint, header, divider,
    success, warn, error, info, step,
)


# ---------------------------------------------------------------------------
# Colors & Symbols
# ---------------------------------------------------------------------------

class TestColors:
    def test_reset_is_ansi(self):
        assert Colors.RESET == "\033[0m"

    def test_bold_is_ansi(self):
        assert Colors.BOLD == "\033[1m"

    def test_all_foreground_colors_are_strings(self):
        for attr in ("RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE"):
            assert isinstance(getattr(Colors, attr), str)

    def test_bright_variants_exist(self):
        for attr in ("BRIGHT_RED", "BRIGHT_GREEN", "BRIGHT_YELLOW",
                     "BRIGHT_BLUE", "BRIGHT_MAGENTA", "BRIGHT_CYAN", "BRIGHT_WHITE"):
            assert hasattr(Colors, attr)


class TestSymbols:
    def test_ok_symbol(self):
        assert Symbols.OK == "✔"

    def test_fail_symbol(self):
        assert Symbols.FAIL == "✖"

    def test_warn_symbol(self):
        assert Symbols.WARN == "⚠"

    def test_all_symbols_are_non_empty_strings(self):
        for attr in ("OK", "FAIL", "WARN", "INFO", "ARROW", "BULLET",
                     "ROCKET", "CLOCK", "SKIP", "SAVE", "SEARCH", "GEAR", "MERGE"):
            val = getattr(Symbols, attr)
            assert isinstance(val, str) and val


# ---------------------------------------------------------------------------
# cprint
# ---------------------------------------------------------------------------

class TestCprint:
    def _capture(self, *args, **kwargs):
        with patch("builtins.print") as mock_print:
            cprint(*args, **kwargs)
            return mock_print.call_args[0][0]

    def test_plain_message_contains_text(self):
        output = self._capture("Hello")
        assert "Hello" in output

    def test_output_ends_with_reset(self):
        output = self._capture("Test", color=Colors.GREEN)
        assert output.endswith(Colors.RESET)

    def test_bold_flag_injects_bold_code(self):
        output = self._capture("Bold", bold=True)
        assert Colors.BOLD in output

    def test_dim_flag_injects_dim_code(self):
        output = self._capture("Dim", dim=True)
        assert Colors.DIM in output

    def test_prefix_is_prepended(self):
        output = self._capture("Msg", prefix=Symbols.OK)
        assert Symbols.OK in output
        assert "Msg" in output

    def test_color_code_is_in_output(self):
        output = self._capture("Colored", color=Colors.CYAN)
        assert Colors.CYAN in output

    def test_no_prefix_no_space_artifact(self):
        """Without a prefix the message should not start with a leading space."""
        output = self._capture("NoPrefix")
        content = output.replace(Colors.RESET, "").lstrip("\033[0m\033[1m\033[2m")
        assert not content.startswith(" ")


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    def _capture(self, fn, *args, **kwargs):
        with patch("builtins.print") as mock_print:
            fn(*args, **kwargs)
            return mock_print.call_args[0][0]

    def test_success_contains_ok_symbol(self):
        out = self._capture(success, "Done")
        assert Symbols.OK in out

    def test_success_contains_message(self):
        out = self._capture(success, "Done")
        assert "Done" in out

    def test_warn_contains_warn_symbol(self):
        out = self._capture(warn, "Careful")
        assert Symbols.WARN in out

    def test_error_contains_fail_symbol(self):
        out = self._capture(error, "Boom")
        assert Symbols.FAIL in out

    def test_info_contains_message(self):
        out = self._capture(info, "FYI")
        assert "FYI" in out

    def test_step_contains_arrow_symbol(self):
        out = self._capture(step, "Step 1")
        assert Symbols.ARROW in out

    def test_header_prints_three_lines(self):
        with patch("builtins.print") as mock_print:
            header("My Title")
            assert mock_print.call_count == 3

    def test_divider_prints_once(self):
        with patch("builtins.print") as mock_print:
            divider()
            assert mock_print.call_count == 1

    def test_success_with_detail_prints_twice(self):
        with patch("builtins.print") as mock_print:
            success("Done", detail="All good")
            assert mock_print.call_count == 2
