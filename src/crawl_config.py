"""
Configuration for the full-site crawl architecture.

Key settings:
- No crawl depth limit (crawl entire site)
- 6-month re-crawl frequency
- 18-month data retention
"""

import os
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load .env file from project root
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


@dataclass
class CrawlConfig:
    """Configuration for Firecrawl crawl operations."""

    api_key: str

    # Crawl settings - NO LIMIT to ensure complete site capture
    # Setting limit to None or very high number captures everything
    crawl_limit: Optional[int] = None  # None = unlimited

    # Scrape options applied to each page during crawl
    scrape_formats: List[str] = field(default_factory=lambda: ["markdown", "html"])
    only_main_content: bool = False  # Capture full page for audit
    wait_for: int = 3000  # ms for JS rendering

    # Crawl behavior
    crawl_timeout: int = 600000  # 10 minutes max for entire crawl
    ignore_sitemap: bool = False  # Use sitemap if available
    allow_subdomains: bool = False  # Stay on main domain
    crawl_entire_domain: bool = True  # Follow all internal links

    # Rate limiting
    delay_between_requests: float = 1.0  # seconds
    max_retries: int = 3

    # Polling for async crawl jobs
    poll_interval: int = 5  # seconds between status checks


@dataclass
class RetentionConfig:
    """Configuration for data retention and re-crawl scheduling."""

    # Re-crawl frequency: 6 months
    recrawl_interval: timedelta = field(default_factory=lambda: timedelta(days=180))

    # Data retention: 18 months
    retention_period: timedelta = field(default_factory=lambda: timedelta(days=540))

    # Maximum crawl versions to keep per business (18 months / 6 months = 3)
    max_versions_per_business: int = 3


@dataclass
class ClassifierConfig:
    """Configuration for the page classifier LLM."""

    # Use cheap, fast model for classification
    # Options: "claude-3-haiku-20240307", "gpt-4o-mini"
    model: str = "claude-3-haiku-20240307"

    # Classification settings
    max_tokens: int = 200  # Short responses only
    temperature: float = 0.0  # Deterministic classification

    # Batching for efficiency
    batch_size: int = 10  # Classify pages in batches

    # Cost tracking (approximate)
    cost_per_1k_input_tokens: float = 0.00025  # Haiku pricing
    cost_per_1k_output_tokens: float = 0.00125


@dataclass
class MergerConfig:
    """Configuration for content merging before extraction."""

    # Priority order for page types (highest priority first)
    # Pages with higher priority are included first in merged content
    page_type_priority: List[str] = field(default_factory=lambda: [
        "pricing",      # Most important - always include
        "services",     # Service details often have prices too
        "contact",      # Need address, phone, email
        "terms",        # T&Cs, policies
        "faq",          # Often has vaccination/policy info
        "booking",      # May have deposit/cancellation info
        "about",        # Business description
        "homepage",     # Fallback overview
    ])

    # Excluded page types (never include in extraction)
    excluded_page_types: List[str] = field(default_factory=lambda: [
        "blog",         # News/articles not relevant
        "gallery",      # Just images
    ])

    # Token/size limits for merged content
    max_merged_tokens: int = 100000  # Generous limit for comprehensive extraction
    max_pages_to_merge: int = 20     # Safety limit

    # Minimum relevance score to include page
    min_relevance_score: float = 0.2


@dataclass
class ExtractionConfig:
    """Configuration for the final extraction pass."""

    # Firecrawl extraction settings
    extraction_timeout: int = 180000  # 3 minutes for comprehensive extraction

    # LLM settings for extraction
    extraction_model: str = "default"  # Use Firecrawl's default

    # Quality thresholds
    min_quality_score: int = 50
    min_prices_for_success: int = 1


def get_firecrawl_api_key() -> str:
    """Get Firecrawl API key from environment variable."""
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError(
            "FIRECRAWL_API_KEY environment variable is not set. "
            "Please set it with: export FIRECRAWL_API_KEY='fc-your-key-here'"
        )
    return api_key


def get_anthropic_api_key() -> Optional[str]:
    """Get Anthropic API key for page classification (optional)."""
    return os.environ.get("ANTHROPIC_API_KEY")


def get_crawl_config(api_key: Optional[str] = None) -> CrawlConfig:
    """Get crawl configuration."""
    if api_key is None:
        api_key = get_firecrawl_api_key()
    return CrawlConfig(api_key=api_key)


def get_retention_config() -> RetentionConfig:
    """Get retention configuration."""
    return RetentionConfig()


def get_classifier_config() -> ClassifierConfig:
    """Get classifier configuration."""
    return ClassifierConfig()


def get_merger_config() -> MergerConfig:
    """Get merger configuration."""
    return MergerConfig()


def get_extraction_config() -> ExtractionConfig:
    """Get extraction configuration."""
    return ExtractionConfig()


# Summary of the architecture
ARCHITECTURE_SUMMARY = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FULL SITE CRAWL ARCHITECTURE                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  CRAWL POLICY                                                                ║
║  ├─ Depth Limit: NONE (crawl entire site)                                    ║
║  ├─ Re-crawl Frequency: Every 6 months                                       ║
║  └─ Data Retention: 18 months (3 versions per business)                      ║
║                                                                              ║
║  PIPELINE FLOW                                                               ║
║                                                                              ║
║  1. CRAWL ──────────────────────────────────────────────────────────────────║
║     │  Firecrawl /crawl endpoint                                             ║
║     │  • No page limit                                                       ║
║     │  • Formats: markdown + HTML                                            ║
║     │  • Full page content (not just main)                                   ║
║     │                                                                        ║
║  2. STORE ──────────────────────────────────────────────────────────────────║
║     │  All pages saved to database                                           ║
║     │  • Raw markdown for extraction                                         ║
║     │  • Raw HTML for audit trail                                            ║
║     │  • Metadata (title, status, timestamp)                                 ║
║     │                                                                        ║
║  3. CLASSIFY ───────────────────────────────────────────────────────────────║
║     │  Cheap LLM (Claude Haiku) classifies each page                         ║
║     │  • Page type: pricing, contact, terms, etc.                            ║
║     │  • Relevance score: 0-1                                                ║
║     │  • ~$0.001 per page                                                    ║
║     │                                                                        ║
║  4. MERGE ──────────────────────────────────────────────────────────────────║
║     │  Combine relevant pages by priority                                    ║
║     │  • Pricing > Services > Contact > Terms > FAQ                          ║
║     │  • Exclude: Blog, Gallery                                              ║
║     │  • Respect token limits                                                ║
║     │                                                                        ║
║  5. EXTRACT ────────────────────────────────────────────────────────────────║
║     │  Single extraction call on merged content                              ║
║     │  • Business-type-specific schema                                       ║
║     │  • Comprehensive prompt                                                ║
║     │  • ~60-90 credits                                                      ║
║     │                                                                        ║
║  6. NORMALIZE ──────────────────────────────────────────────────────────────║
║        Save to structured tables                                             ║
║        • businesses, boarding_prices, etc.                                   ║
║        • Link to source crawl for audit                                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    print(ARCHITECTURE_SUMMARY)
