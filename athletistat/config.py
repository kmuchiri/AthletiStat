"""
config.py - Centralized configuration loader for AthletiStat.

Reads settings from ``athletistat/config.toml`` and exposes them as typed,
frozen dataclasses. Falls back to built-in defaults when the file is missing
or a key is omitted.

Usage:
    from athletistat.config import cfg

    cfg.scraper.max_workers      # 10
    cfg.paths.dataset_dir        # "data/datasets"
    cfg.display.progress_bar_width  # 30
"""

import os
import tomllib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScraperConfig:
    """Scraper-related tunables."""
    max_workers: int = 10
    connect_timeout: int = 5
    read_timeout: int = 30
    retry_total: int = 5
    retry_backoff_factor: int = 1
    retry_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)
    page_delay: float = 1.5
    user_agent: str = "Mozilla/5.0"
    verify_ssl: bool = True


@dataclass(frozen=True)
class PathsConfig:
    """Directory and file path defaults."""
    options_file: str = "athletistat/options.json"
    scraper_output: str = "data/processing/output"
    queue_dir: str = "queues"
    log_dir: str = "logs"
    combined_dir: str = "data/processing/combined"
    dataset_dir: str = "data/datasets"
    dataset_info_file: str = "data/datasets/dataset_info.txt"
    dataset_summary_file: str = "data/datasets/dataset_summary.txt"


@dataclass(frozen=True)
class DisplayConfig:
    """Display and UI tunables."""
    progress_bar_width: int = 30
    row_count_chunk_size: int = 1048576  # 1 MB


@dataclass(frozen=True)
class Config:
    """Top-level configuration container."""
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)


def _load_config() -> Config:
    """Load configuration from ``config.toml`` next to this file.

    Returns:
        Config: Populated configuration object.
    """
    config_path = os.path.join(os.path.dirname(__file__), "config.toml")

    if not os.path.exists(config_path):
        return Config()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    scraper_data = data.get("scraper", {})
    # TOML arrays → immutable tuple for the dataclass
    if "retry_status_codes" in scraper_data:
        scraper_data["retry_status_codes"] = tuple(scraper_data["retry_status_codes"])

    return Config(
        scraper=ScraperConfig(**scraper_data),
        paths=PathsConfig(**data.get("paths", {})),
        display=DisplayConfig(**data.get("display", {})),
    )


cfg = _load_config()
