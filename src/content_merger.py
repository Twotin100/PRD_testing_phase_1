"""
Content merger for combining relevant pages before extraction.

Merges pages by priority order to create a comprehensive document
for the final extraction pass. Respects token limits while maximizing
information coverage.

Priority order:
1. Pricing pages (most important)
2. Services pages
3. Contact pages
4. Terms/policies pages
5. FAQ pages
6. Booking pages
7. About pages
8. Homepage (fallback)

Excludes: Blog, Gallery (not relevant for business data extraction)
"""

from datetime import datetime
from typing import List, Optional, Tuple

from crawl_config import get_merger_config, MergerConfig
from crawl_schemas import CrawledPage, MergedContent, PageType


# Approximate tokens per word (conservative estimate)
TOKENS_PER_WORD = 1.3


def estimate_tokens(text: str) -> int:
    """Estimate token count from text."""
    word_count = len(text.split())
    return int(word_count * TOKENS_PER_WORD)


def get_page_priority(page: CrawledPage, config: MergerConfig) -> int:
    """
    Get priority rank for a page (lower = higher priority).
    Returns a large number for excluded pages.
    """
    page_type_str = page.page_type.value if page.page_type else "other"

    # Check if excluded
    if page_type_str in config.excluded_page_types:
        return 999

    # Get priority from config
    try:
        return config.page_type_priority.index(page_type_str)
    except ValueError:
        # Not in priority list, put at end
        return len(config.page_type_priority)


def sort_pages_by_priority(
    pages: List[CrawledPage],
    config: Optional[MergerConfig] = None,
) -> List[CrawledPage]:
    """
    Sort pages by extraction priority.

    Primary sort: Page type priority (pricing first)
    Secondary sort: Relevance score (higher first)
    Tertiary sort: Has pricing signals (True first)
    """
    if config is None:
        config = get_merger_config()

    def sort_key(page: CrawledPage) -> Tuple[int, float, bool]:
        priority = get_page_priority(page, config)
        # Negate relevance so higher values sort first
        relevance = -page.relevance_score
        # Negate so True (1) sorts before False (0)
        has_pricing = not page.has_pricing_signals
        return (priority, relevance, has_pricing)

    return sorted(pages, key=sort_key)


def filter_relevant_pages(
    pages: List[CrawledPage],
    config: Optional[MergerConfig] = None,
) -> List[CrawledPage]:
    """
    Filter out irrelevant pages based on config.

    Removes:
    - Pages with excluded types (blog, gallery)
    - Pages below minimum relevance threshold
    - Empty pages
    """
    if config is None:
        config = get_merger_config()

    relevant = []
    for page in pages:
        page_type_str = page.page_type.value if page.page_type else "other"

        # Skip excluded types
        if page_type_str in config.excluded_page_types:
            continue

        # Skip low relevance pages
        if page.relevance_score < config.min_relevance_score:
            continue

        # Skip empty pages
        if not page.markdown or page.word_count < 50:
            continue

        relevant.append(page)

    return relevant


def format_page_for_merge(page: CrawledPage) -> str:
    """
    Format a single page for inclusion in merged content.

    Adds clear section headers to help the extraction LLM understand
    the structure and source of different content.
    """
    page_type_label = page.page_type.value.upper() if page.page_type else "PAGE"
    title = page.title or "Untitled"

    header = f"""
================================================================================
{page_type_label} PAGE: {title}
Source URL: {page.url}
================================================================================

"""
    return header + page.markdown


def merge_pages(
    pages: List[CrawledPage],
    crawl_id: str,
    business_url: str,
    business_type: str,
    config: Optional[MergerConfig] = None,
) -> MergedContent:
    """
    Merge relevant pages into a single document for extraction.

    Strategy:
    1. Filter out irrelevant pages (blog, gallery, low relevance)
    2. Sort by priority (pricing > services > contact > terms > ...)
    3. Add pages until token limit reached
    4. Always include at least the highest priority page

    Args:
        pages: All crawled pages from a site
        crawl_id: Identifier for this crawl
        business_url: Starting URL of the business
        business_type: Type of pet care business
        config: Merger configuration (optional)

    Returns:
        MergedContent with combined markdown and metadata
    """
    if config is None:
        config = get_merger_config()

    # Filter and sort pages
    relevant_pages = filter_relevant_pages(pages, config)
    sorted_pages = sort_pages_by_priority(relevant_pages, config)

    # Track what we're including
    merged_parts: List[str] = []
    source_urls: List[str] = []
    page_types_included: List[PageType] = []
    total_tokens = 0
    pages_merged = 0

    # Add header with context for the extraction LLM
    header = f"""
################################################################################
#  BUSINESS DATA EXTRACTION DOCUMENT
#  Business Type: {business_type}
#  Primary URL: {business_url}
#  Pages Included: (see below)
#  Crawl ID: {crawl_id}
################################################################################

INSTRUCTIONS FOR EXTRACTION:
This document contains merged content from multiple pages of a pet care business
website. Extract all relevant business information including:
- Business name and description
- Contact details (phone, email, address)
- All services and their prices
- Vaccination requirements
- Policies (cancellation, deposit, drop-off/pick-up)
- Opening hours
- Amenities and special features

The pages are ordered by relevance, with pricing information first.

================================================================================
BEGIN WEBSITE CONTENT
================================================================================
"""
    merged_parts.append(header)
    total_tokens += estimate_tokens(header)

    # Add pages in priority order
    for page in sorted_pages:
        # Check page limit
        if pages_merged >= config.max_pages_to_merge:
            break

        # Format page content
        page_content = format_page_for_merge(page)
        page_tokens = estimate_tokens(page_content)

        # Check token limit (but always include at least one page)
        if total_tokens + page_tokens > config.max_merged_tokens and pages_merged > 0:
            break

        # Add page
        merged_parts.append(page_content)
        source_urls.append(page.url)
        if page.page_type and page.page_type not in page_types_included:
            page_types_included.append(page.page_type)
        total_tokens += page_tokens
        pages_merged += 1

    # Add footer
    footer = f"""

================================================================================
END WEBSITE CONTENT
================================================================================

Total pages included: {pages_merged}
Page types: {', '.join(pt.value for pt in page_types_included)}
"""
    merged_parts.append(footer)

    # Calculate stats
    pages_excluded = len(pages) - pages_merged

    return MergedContent(
        crawl_id=crawl_id,
        business_url=business_url,
        business_type=business_type,
        merged_markdown="\n".join(merged_parts),
        source_pages=source_urls,
        page_types_included=page_types_included,
        total_word_count=total_tokens // TOKENS_PER_WORD,
        pages_merged=pages_merged,
        pages_excluded=pages_excluded,
        merged_at=datetime.utcnow(),
    )


def get_merge_summary(merged: MergedContent) -> str:
    """Get a human-readable summary of the merge operation."""
    page_types_str = ", ".join(pt.value for pt in merged.page_types_included)

    return f"""
Merge Summary
=============
Business URL: {merged.business_url}
Business Type: {merged.business_type}
Crawl ID: {merged.crawl_id}

Pages merged: {merged.pages_merged}
Pages excluded: {merged.pages_excluded}
Total words: ~{merged.total_word_count:,}

Page types included: {page_types_str}

Source pages:
{chr(10).join(f'  - {url}' for url in merged.source_pages)}
"""


def create_extraction_document(
    pages: List[CrawledPage],
    crawl_id: str,
    business_url: str,
    business_type: str,
    config: Optional[MergerConfig] = None,
) -> Tuple[MergedContent, str]:
    """
    High-level function to create an extraction-ready document.

    Returns:
        Tuple of (MergedContent, summary_string)
    """
    merged = merge_pages(
        pages=pages,
        crawl_id=crawl_id,
        business_url=business_url,
        business_type=business_type,
        config=config,
    )
    summary = get_merge_summary(merged)

    return merged, summary


if __name__ == "__main__":
    # Example usage
    from crawl_schemas import PageType

    # Create test pages
    test_pages = [
        CrawledPage(
            url="https://example-kennels.co.uk/",
            page_type=PageType.HOMEPAGE,
            relevance_score=0.6,
            markdown="Welcome to Example Kennels. Quality dog boarding since 1990.",
            title="Example Kennels",
            word_count=50,
            has_pricing_signals=False,
            has_contact_signals=False,
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/prices",
            page_type=PageType.PRICING,
            relevance_score=1.0,
            markdown="""
# Our Prices

All prices are per night and include:
- Individual kennel
- Daily walks
- Fresh bedding

| Dog Size | Price |
|----------|-------|
| Small (under 10kg) | £25 |
| Medium (10-25kg) | £28 |
| Large (25-40kg) | £32 |
| Giant (40kg+) | £38 |

**Multi-dog discount:** 10% off second dog sharing same kennel.

**Bank holiday surcharge:** £5 per night.
""",
            title="Prices - Example Kennels",
            word_count=80,
            has_pricing_signals=True,
            has_contact_signals=False,
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/contact",
            page_type=PageType.CONTACT,
            relevance_score=0.85,
            markdown="""
# Contact Us

**Address:** 123 Farm Lane, Countryside, AB1 2CD

**Phone:** 01234 567890

**Email:** info@example-kennels.co.uk

**Opening Hours:**
- Monday to Saturday: 8am - 6pm
- Sunday: 9am - 5pm
- Bank Holidays: 10am - 4pm
""",
            title="Contact - Example Kennels",
            word_count=60,
            has_pricing_signals=False,
            has_contact_signals=True,
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/blog/summer-tips",
            page_type=PageType.BLOG,
            relevance_score=0.1,
            markdown="Blog post about summer dog care tips...",
            title="Summer Tips Blog",
            word_count=500,
            has_pricing_signals=False,
            has_contact_signals=False,
        ),
    ]

    merged, summary = create_extraction_document(
        pages=test_pages,
        crawl_id="test-123",
        business_url="https://example-kennels.co.uk",
        business_type="dog_kennel",
    )

    print(summary)
    print("\n" + "=" * 80)
    print("MERGED DOCUMENT PREVIEW (first 2000 chars):")
    print("=" * 80)
    print(merged.merged_markdown[:2000])
