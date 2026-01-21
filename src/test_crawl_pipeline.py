#!/usr/bin/env python3
"""
Test script for the full site crawl pipeline.

This validates the pipeline components work together correctly
without requiring API calls. Run with actual APIs using:

    python crawl_extraction.py --url <url> --type <type>

For unit tests of individual components, this script uses mock data.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from typing import List

from crawl_schemas import CrawledPage, PageType, SiteCrawl, CrawlStatus
from page_classifier import classify_pages, get_classification_summary
from content_merger import create_extraction_document, merge_pages
from crawl_config import get_merger_config, ARCHITECTURE_SUMMARY
from retention_manager import RetentionManager, print_retention_report


def create_mock_pages() -> List[CrawledPage]:
    """Create mock crawled pages for testing."""
    return [
        CrawledPage(
            url="https://example-kennels.co.uk/",
            markdown="""
# Welcome to Example Kennels

We are a family-run dog boarding facility in the heart of the countryside.
Our kennels have been caring for dogs since 1985.

## Why Choose Us?
- Individual heated kennels
- Large exercise paddocks
- 24-hour supervision
- Webcam access for owners

Contact us today to book your dog's stay!
            """,
            title="Example Kennels - Quality Dog Boarding",
            description="Family-run dog boarding kennels in countryside setting",
            word_count=60,
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/prices/",
            markdown="""
# Our Boarding Prices

All prices are per night and include daily walks, fresh bedding, and meals.

## Dog Boarding Rates

| Size | Price per Night |
|------|-----------------|
| Small dogs (under 10kg) | £25 |
| Medium dogs (10-25kg) | £28 |
| Large dogs (25-40kg) | £32 |
| Giant breeds (40kg+) | £38 |

### Discounts Available

- **Second dog (sharing):** 10% discount
- **Stays over 14 nights:** 5% discount
- **Regular customers:** Loyalty card available

### Additional Charges

- Bank holiday surcharge: £5 per night
- Christmas period (23 Dec - 2 Jan): £8 per night
- Single night stays: £3 surcharge

## Day Care

- Full day (7am-6pm): £22
- Half day (up to 5 hours): £15

All prices include VAT.
            """,
            title="Prices - Example Kennels",
            description="View our competitive boarding rates",
            word_count=120,
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/contact/",
            markdown="""
# Contact Us

## Address
Example Kennels
123 Farm Lane
Countryside Village
AB1 2CD

## Phone
01234 567890

## Email
info@example-kennels.co.uk

## Opening Hours
- Monday to Saturday: 8:00am - 6:00pm
- Sunday: 9:00am - 5:00pm
- Bank Holidays: 10:00am - 4:00pm

## Find Us
We are located 2 miles from Junction 5 of the M1.
Free parking available on site.
            """,
            title="Contact - Example Kennels",
            description="Get in touch or visit us",
            word_count=70,
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/requirements/",
            markdown="""
# Booking Requirements

## Vaccinations

All dogs staying with us must have up-to-date vaccinations for:

1. **Distemper** - Annual booster required
2. **Parvovirus** - Annual booster required
3. **Leptospirosis** - Annual booster required
4. **Kennel Cough (Bordetella)** - Must be given at least 2 weeks before boarding

Please bring your vaccination card when dropping off your dog.

## Cancellation Policy

- More than 14 days notice: Full refund
- 7-14 days notice: 50% refund
- Less than 7 days notice: No refund

A non-refundable deposit of £25 is required to secure your booking.

## What to Bring

- Your dog's usual food (we can provide if needed)
- Favourite toy or blanket
- Any medications with clear instructions
- Vaccination card
            """,
            title="Requirements - Example Kennels",
            description="What you need to know before booking",
            word_count=140,
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/blog/summer-tips/",
            markdown="""
# Summer Safety Tips for Dogs

With summer approaching, here are some tips to keep your dog safe in the heat...

[Blog content about summer dog care - not relevant for extraction]
            """,
            title="Summer Safety Tips - Example Kennels Blog",
            description="Keep your dog safe this summer",
            word_count=200,
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/gallery/",
            markdown="""
# Photo Gallery

[Image: Happy dogs in our exercise paddock]
[Image: Our heated kennels]
[Image: Feeding time]
            """,
            title="Gallery - Example Kennels",
            description="See our facilities",
            word_count=20,
        ),
    ]


def test_page_classification():
    """Test the page classifier."""
    print("\n" + "=" * 60)
    print("TEST: Page Classification")
    print("=" * 60)

    pages = create_mock_pages()
    print(f"\nInput: {len(pages)} pages")

    # Classify without LLM (rule-based only)
    classified = classify_pages(pages, use_llm=False)

    print("\nClassification Results:")
    print("-" * 60)
    for page in classified:
        print(f"  {page.url}")
        print(f"    Type: {page.page_type.value}")
        print(f"    Confidence: {page.page_type_confidence:.2f}")
        print(f"    Relevance: {page.relevance_score:.2f}")
        print(f"    Pricing signals: {page.has_pricing_signals}")
        print()

    summary = get_classification_summary(classified)
    print("Summary:")
    print(f"  Total pages: {summary['total_pages']}")
    print(f"  High relevance: {summary['high_relevance_pages']}")
    print(f"  With pricing signals: {summary['pages_with_pricing_signals']}")
    print(f"  Type distribution: {summary['type_distribution']}")

    # Assertions
    pricing_page = next(p for p in classified if "prices" in p.url)
    assert pricing_page.page_type == PageType.PRICING, "Pricing page should be classified as PRICING"
    assert pricing_page.relevance_score >= 0.7, "Pricing page should have high relevance"

    contact_page = next(p for p in classified if "contact" in p.url)
    assert contact_page.page_type == PageType.CONTACT, "Contact page should be classified as CONTACT"

    blog_page = next(p for p in classified if "blog" in p.url)
    assert blog_page.page_type == PageType.BLOG, "Blog page should be classified as BLOG"
    assert blog_page.relevance_score < 0.3, "Blog should have low relevance"

    print("\n✓ All classification tests passed!")
    return classified


def test_content_merger(classified_pages: List[CrawledPage]):
    """Test the content merger."""
    print("\n" + "=" * 60)
    print("TEST: Content Merger")
    print("=" * 60)

    merged, summary = create_extraction_document(
        pages=classified_pages,
        crawl_id="test-crawl-123",
        business_url="https://example-kennels.co.uk",
        business_type="dog_kennel",
    )

    print(summary)

    # Assertions
    assert merged.pages_merged > 0, "Should merge at least one page"
    assert merged.pages_excluded > 0, "Should exclude some pages (blog, gallery)"
    assert PageType.PRICING in merged.page_types_included, "Should include pricing page"
    assert PageType.BLOG not in merged.page_types_included, "Should exclude blog"
    assert PageType.GALLERY not in merged.page_types_included, "Should exclude gallery"

    # Check pricing page is first (highest priority)
    assert "PRICING PAGE" in merged.merged_markdown[:2000], "Pricing should appear early in merged content"

    # Check merged content has pricing data
    assert "£25" in merged.merged_markdown, "Should include price data"
    assert "01234 567890" in merged.merged_markdown, "Should include contact info"
    assert "Kennel Cough" in merged.merged_markdown, "Should include vaccination requirements"

    print("\n✓ All merger tests passed!")
    return merged


def test_retention_manager():
    """Test the retention manager."""
    print("\n" + "=" * 60)
    print("TEST: Retention Manager")
    print("=" * 60)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = RetentionManager(storage_dir=tmpdir)

        # Register a business
        business_id = manager.register_business(
            "https://example-kennels.co.uk",
            "dog_kennel",
            "Example Kennels"
        )
        print(f"\nRegistered business: {business_id}")

        # Simulate multiple crawls
        for i in range(4):  # 4 crawls, should only keep 3
            crawl_file = Path(tmpdir) / f"crawl_{i}.json"
            crawl_file.write_text('{"test": "data"}')

            record = manager.register_crawl(
                crawl_id=f"crawl-{i}",
                business_url="https://example-kennels.co.uk",
                business_type="dog_kennel",
                crawl_file_path=str(crawl_file),
                pages_crawled=10 + i,
                credits_used=50,
            )
            print(f"  Registered crawl version {record['version']}")

        # Check max versions enforced
        history = manager.get_crawl_history("https://example-kennels.co.uk")
        assert len(history) == 3, f"Should only keep 3 versions, got {len(history)}"

        # Check versions are correct (oldest deleted)
        versions = [c["version"] for c in history]
        assert versions == [2, 3, 4], f"Should keep versions 2,3,4 but got {versions}"

        # Check latest crawl
        latest = manager.get_latest_crawl("https://example-kennels.co.uk")
        assert latest["version"] == 4, "Latest should be version 4"

        # Check retention stats
        stats = manager.get_retention_stats()
        print(f"\nRetention Stats:")
        print(f"  Total businesses: {stats['total_businesses']}")
        print(f"  Total crawls: {stats['total_crawls']}")
        print(f"  Retention period: {stats['retention_period_days']} days")

        assert stats["total_businesses"] == 1
        assert stats["total_crawls"] == 3
        assert stats["retention_period_days"] == 540  # 18 months
        assert stats["recrawl_interval_days"] == 180  # 6 months

        print("\n✓ All retention manager tests passed!")


def test_full_pipeline_mock():
    """Test the full pipeline with mock data (no API calls)."""
    print("\n" + "=" * 60)
    print("TEST: Full Pipeline (Mock)")
    print("=" * 60)

    # Step 1: Create mock crawl result
    pages = create_mock_pages()
    print(f"\n1. Crawl: {len(pages)} pages captured")

    # Step 2: Classify pages
    classified = classify_pages(pages, use_llm=False)
    classification = get_classification_summary(classified)
    print(f"2. Classify: {classification['high_relevance_pages']} high-relevance pages")

    # Step 3: Merge content
    merged, _ = create_extraction_document(
        pages=classified,
        crawl_id="mock-123",
        business_url="https://example-kennels.co.uk",
        business_type="dog_kennel",
    )
    print(f"3. Merge: {merged.pages_merged} pages merged, {merged.pages_excluded} excluded")

    # Step 4: Verify merged content quality
    word_count = len(merged.merged_markdown.split())
    print(f"4. Merged content: ~{word_count} words")

    # Check all expected data is present
    expected_data = [
        ("£25", "Small dog price"),
        ("£28", "Medium dog price"),
        ("£32", "Large dog price"),
        ("01234 567890", "Phone number"),
        ("AB1 2CD", "Postcode"),
        ("Kennel Cough", "Vaccination requirement"),
        ("14 days notice", "Cancellation policy"),
        ("£25", "Deposit amount"),
        ("8:00am - 6:00pm", "Opening hours"),
    ]

    print("\n5. Data presence check:")
    all_present = True
    for data, description in expected_data:
        present = data in merged.merged_markdown
        status = "✓" if present else "✗"
        print(f"   {status} {description}: {data}")
        if not present:
            all_present = False

    assert all_present, "Some expected data missing from merged content"

    print("\n✓ Full pipeline mock test passed!")


def main():
    """Run all tests."""
    print(ARCHITECTURE_SUMMARY)

    print("\n" + "#" * 60)
    print("# CRAWL PIPELINE TESTS")
    print("#" * 60)

    # Run tests
    classified = test_page_classification()
    test_content_merger(classified)
    test_retention_manager()
    test_full_pipeline_mock()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    print("""
Next steps:
1. Set your API keys:
   export FIRECRAWL_API_KEY="fc-your-key"
   export ANTHROPIC_API_KEY="sk-ant-your-key"  # Optional, for LLM classifier

2. Test with a real URL:
   python crawl_extraction.py --url https://example.co.uk --type dog_kennel

3. Run batch extraction:
   python crawl_extraction.py --batch
""")


if __name__ == "__main__":
    main()
