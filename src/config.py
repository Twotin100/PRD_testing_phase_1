"""
Configuration and environment setup for the Pet Care Data Extraction POC.

This module handles Firecrawl API configuration and provides default settings
for the extraction pipeline as specified in the PRD.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class FirecrawlConfig:
    """Configuration for Firecrawl API."""

    api_key: str

    # Pass 1: Content Capture settings
    capture_wait_for: int = 3000  # ms for JS rendering
    capture_timeout: int = 60000  # ms
    capture_only_main_content: bool = False  # Capture everything

    # Pass 2: Structured Extraction settings
    extraction_timeout: int = 120000  # ms

    # Rate limiting
    delay_between_requests: float = 1.0  # seconds
    max_retries: int = 2


def get_firecrawl_api_key() -> str:
    """Get Firecrawl API key from environment variable.

    Returns:
        The API key string.

    Raises:
        ValueError: If FIRECRAWL_API_KEY is not set.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError(
            "FIRECRAWL_API_KEY environment variable is not set. "
            "Please set it with: export FIRECRAWL_API_KEY='fc-your-key-here'"
        )
    return api_key


def get_config(api_key: Optional[str] = None) -> FirecrawlConfig:
    """Get Firecrawl configuration.

    Args:
        api_key: Optional API key. If not provided, reads from environment.

    Returns:
        FirecrawlConfig instance.
    """
    if api_key is None:
        api_key = get_firecrawl_api_key()
    return FirecrawlConfig(api_key=api_key)


# Business types supported by the POC
BUSINESS_TYPES = [
    "dog_kennel",
    "cattery",
    "dog_groomer",
    "veterinary_clinic",
    "dog_daycare",
    "dog_sitter",
]


# Output directory for extraction results
DEFAULT_OUTPUT_DIR = "extraction_results"
