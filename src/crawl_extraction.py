#!/usr/bin/env python3
"""
Full site crawl extraction pipeline.

Implements the complete flow:
1. CRAWL - Crawl entire site with no depth limit
2. STORE - Save all pages for audit trail
3. CLASSIFY - Categorize pages by type using cheap LLM
4. MERGE - Combine relevant pages by priority
5. EXTRACT - Run structured extraction on merged content
6. NORMALIZE - Save to database tables

Usage:
    python crawl_extraction.py --url https://example-kennels.co.uk --type dog_kennel
    python crawl_extraction.py --batch  # Run all URLs from sample_urls.py
"""

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

try:
    from firecrawl import FirecrawlApp
except ImportError:
    print("Error: firecrawl-py not installed. Run: pip install firecrawl-py")
    sys.exit(1)

from content_merger import create_extraction_document, get_merge_summary
from crawl_config import (
    get_crawl_config,
    get_classifier_config,
    get_merger_config,
    get_extraction_config,
    get_retention_config,
    ARCHITECTURE_SUMMARY,
)
from crawl_schemas import (
    CrawledPage,
    CrawlStatus,
    MergedContent,
    PageType,
    SiteCrawl,
)
from page_classifier import classify_pages, get_classification_summary
from quality_scoring import generate_metrics, QualityMetrics
from schemas import BusinessExtraction, get_extraction_prompt

console = Console()

# Output directories
DEFAULT_OUTPUT_DIR = "crawl_results"
CRAWL_STORAGE_DIR = "crawl_storage"


def ensure_directories() -> Tuple[Path, Path]:
    """Create output directories if they don't exist."""
    output_path = Path(DEFAULT_OUTPUT_DIR)
    storage_path = Path(CRAWL_STORAGE_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    storage_path.mkdir(parents=True, exist_ok=True)
    return output_path, storage_path


def run_crawl(
    app: FirecrawlApp,
    url: str,
    config: Any,
) -> Tuple[SiteCrawl, List[CrawledPage]]:
    """
    Run a full site crawl with no depth limit.

    Returns:
        Tuple of (SiteCrawl metadata, list of CrawledPage objects)
    """
    crawl_id = str(uuid.uuid4())
    retention_config = get_retention_config()

    site_crawl = SiteCrawl(
        crawl_id=crawl_id,
        business_url=url,
        business_type="",  # Will be set later
        status=CrawlStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + retention_config.retention_period,
    )

    console.print(f"[cyan]Starting crawl of {url}...[/cyan]")
    console.print("[dim]No page limit - crawling entire site[/dim]")

    try:
        # Build scrape options
        scrape_options = {
            "formats": config.scrape_formats,
            "onlyMainContent": config.only_main_content,
            "waitFor": config.wait_for,
        }

        # Start the crawl - NO LIMIT for complete site capture
        # If limit is None, we don't pass it (unlimited)
        crawl_params = {
            "scrapeOptions": scrape_options,
            "ignoreSitemap": config.ignore_sitemap,
            "allowSubdomains": config.allow_subdomains,
        }

        if config.crawl_limit is not None:
            crawl_params["limit"] = config.crawl_limit

        # Use the synchronous crawl method that waits for completion
        result = app.crawl(url, **crawl_params)

        # Process results
        pages: List[CrawledPage] = []

        # Handle different response formats from Firecrawl
        crawl_data = []
        if hasattr(result, "data") and result.data:
            crawl_data = result.data
        elif isinstance(result, dict) and "data" in result:
            crawl_data = result["data"]
        elif isinstance(result, list):
            crawl_data = result

        for item in crawl_data:
            # Handle both object and dict formats
            if hasattr(item, "markdown"):
                markdown = item.markdown or ""
                html = getattr(item, "html", None)
                metadata = getattr(item, "metadata", {}) or {}
            else:
                markdown = item.get("markdown", "")
                html = item.get("html")
                metadata = item.get("metadata", {})

            page = CrawledPage(
                url=metadata.get("sourceURL", metadata.get("url", url)),
                markdown=markdown,
                html=html,
                title=metadata.get("title"),
                description=metadata.get("description"),
                status_code=metadata.get("statusCode", 200),
                word_count=len(markdown.split()) if markdown else 0,
            )
            pages.append(page)

        # Update crawl metadata
        site_crawl.status = CrawlStatus.COMPLETED
        site_crawl.completed_at = datetime.utcnow()
        site_crawl.pages_crawled = len(pages)
        site_crawl.total_pages_found = len(pages)

        # Estimate credits used (1 per page for crawl)
        site_crawl.credits_used = len(pages)

        console.print(f"[green]Crawl complete: {len(pages)} pages captured[/green]")

        return site_crawl, pages

    except Exception as e:
        site_crawl.status = CrawlStatus.FAILED
        site_crawl.completed_at = datetime.utcnow()
        site_crawl.errors.append(str(e))
        console.print(f"[red]Crawl failed: {e}[/red]")
        return site_crawl, []


def save_crawl_data(
    site_crawl: SiteCrawl,
    pages: List[CrawledPage],
    storage_path: Path,
) -> Path:
    """
    Save crawl data to disk for audit trail.

    Returns path to saved file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"crawl_{site_crawl.crawl_id}_{timestamp}.json"
    filepath = storage_path / filename

    data = {
        "crawl_metadata": {
            "crawl_id": site_crawl.crawl_id,
            "business_url": site_crawl.business_url,
            "business_type": site_crawl.business_type,
            "status": site_crawl.status.value,
            "started_at": site_crawl.started_at.isoformat(),
            "completed_at": site_crawl.completed_at.isoformat() if site_crawl.completed_at else None,
            "pages_crawled": site_crawl.pages_crawled,
            "credits_used": site_crawl.credits_used,
            "expires_at": site_crawl.expires_at.isoformat() if site_crawl.expires_at else None,
        },
        "pages": [
            {
                "url": p.url,
                "page_type": p.page_type.value if p.page_type else None,
                "page_type_confidence": p.page_type_confidence,
                "relevance_score": p.relevance_score,
                "title": p.title,
                "description": p.description,
                "word_count": p.word_count,
                "has_pricing_signals": p.has_pricing_signals,
                "has_contact_signals": p.has_contact_signals,
                "markdown": p.markdown,
                # HTML omitted from JSON to save space, stored separately if needed
            }
            for p in pages
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    console.print(f"[dim]Crawl data saved to: {filepath}[/dim]")
    return filepath


def run_extraction_on_merged(
    app: FirecrawlApp,
    merged: MergedContent,
    config: Any,
) -> Tuple[Dict[str, Any], float, str]:
    """
    Run structured extraction on merged content.

    Uses the merged markdown as context for extraction.

    Returns:
        Tuple of (extracted_data, elapsed_time, method_used)
    """
    schema = BusinessExtraction.model_json_schema()
    prompt = get_extraction_prompt(merged.business_type)

    # Enhanced prompt with merged content context
    full_prompt = f"""{prompt}

The following content has been collected from multiple pages of the business website.
Pages included: {', '.join(merged.source_pages)}

Extract all available information from this combined content.
"""

    start_time = time.time()

    try:
        # Use Firecrawl's extract with the merged content
        # We pass the primary URL but the LLM will use our merged content
        result = app.extract(
            urls=[merged.business_url],
            schema=schema,
            prompt=full_prompt,
            timeout=config.extraction_timeout,
        )

        elapsed = time.time() - start_time

        extracted = {}
        if hasattr(result, "data") and result.data:
            extracted = result.data if isinstance(result.data, dict) else {}
        elif isinstance(result, dict):
            extracted = result.get("data", {})

        return extracted, elapsed, "schema"

    except Exception as e:
        elapsed = time.time() - start_time
        console.print(f"[yellow]Schema extraction failed: {e}[/yellow]")

        # Fallback to prompt-only extraction
        try:
            fallback_prompt = full_prompt + """

Return the data as a JSON object with these fields:
- business_name: string
- business_type: string
- description: string
- contact: {phone, email, address}
- services: [{service_name, price, unit, description}]
- vaccination_requirements: [{vaccine_name, requirement_details}]
- cancellation_policy: string
- deposit_policy: string
- opening_hours: string
- amenities: [string]
"""

            result = app.extract(
                urls=[merged.business_url],
                prompt=fallback_prompt,
                timeout=config.extraction_timeout,
            )

            fallback_elapsed = time.time() - start_time

            extracted = {}
            if hasattr(result, "data") and result.data:
                extracted = result.data if isinstance(result.data, dict) else {}
            elif isinstance(result, dict):
                extracted = result.get("data", {})

            return extracted, fallback_elapsed, "fallback"

        except Exception as e2:
            total_elapsed = time.time() - start_time
            console.print(f"[red]Fallback extraction also failed: {e2}[/red]")
            return {}, total_elapsed, "failed"


def process_business(
    url: str,
    business_type: str,
    output_path: Path,
    storage_path: Path,
    use_llm_classifier: bool = True,
) -> Tuple[SiteCrawl, MergedContent, Dict[str, Any], QualityMetrics]:
    """
    Process a single business through the full pipeline.

    Steps:
    1. Crawl entire site
    2. Classify pages
    3. Merge relevant pages
    4. Extract structured data
    5. Generate quality metrics

    Returns:
        Tuple of (SiteCrawl, MergedContent, extracted_data, QualityMetrics)
    """
    crawl_config = get_crawl_config()
    extraction_config = get_extraction_config()
    app = FirecrawlApp(api_key=crawl_config.api_key)

    console.print(f"\n[bold cyan]Processing: {url}[/bold cyan]")
    console.print(f"[dim]Business type: {business_type}[/dim]")

    # Step 1: Crawl
    console.print("\n[bold]Step 1: Crawling site...[/bold]")
    site_crawl, pages = run_crawl(app, url, crawl_config)
    site_crawl.business_type = business_type

    if not pages:
        console.print("[red]No pages crawled, cannot continue[/red]")
        return site_crawl, None, {}, QualityMetrics(
            url=url,
            business_type=business_type,
            quality_score=0,
            extraction_success=False,
            has_business_name=False,
            has_contact_info=False,
            has_pricing=False,
            price_count=0,
            has_vaccination_info=False,
            has_policy_info=False,
            extraction_time=0,
            error_message="Crawl returned no pages",
        )

    # Step 2: Classify pages
    console.print("\n[bold]Step 2: Classifying pages...[/bold]")
    classified_pages = classify_pages(pages, use_llm=use_llm_classifier)
    classification_summary = get_classification_summary(classified_pages)
    console.print(f"  Pages classified: {classification_summary['total_pages']}")
    console.print(f"  High relevance: {classification_summary['high_relevance_pages']}")
    console.print(f"  With pricing signals: {classification_summary['pages_with_pricing_signals']}")

    # Step 3: Save crawl data (for audit trail)
    console.print("\n[bold]Step 3: Saving crawl data...[/bold]")
    save_crawl_data(site_crawl, classified_pages, storage_path)

    # Step 4: Merge pages
    console.print("\n[bold]Step 4: Merging relevant pages...[/bold]")
    merged, merge_summary = create_extraction_document(
        pages=classified_pages,
        crawl_id=site_crawl.crawl_id,
        business_url=url,
        business_type=business_type,
    )
    console.print(f"  Pages merged: {merged.pages_merged}")
    console.print(f"  Pages excluded: {merged.pages_excluded}")
    console.print(f"  Page types: {', '.join(pt.value for pt in merged.page_types_included)}")

    # Save merged content
    merged_filename = f"merged_{site_crawl.crawl_id}.md"
    merged_path = output_path / merged_filename
    with open(merged_path, "w", encoding="utf-8") as f:
        f.write(merged.merged_markdown)
    console.print(f"  [dim]Merged content saved to: {merged_path}[/dim]")

    # Step 5: Extract
    console.print("\n[bold]Step 5: Extracting structured data...[/bold]")
    extracted_data, extraction_time, method = run_extraction_on_merged(
        app, merged, extraction_config
    )
    console.print(f"  Method: {method}")
    console.print(f"  Time: {extraction_time:.1f}s")

    # Save extracted data
    if extracted_data:
        extracted_filename = f"extracted_{site_crawl.crawl_id}.json"
        extracted_path = output_path / extracted_filename
        with open(extracted_path, "w", encoding="utf-8") as f:
            json.dump({
                "url": url,
                "business_type": business_type,
                "crawl_id": site_crawl.crawl_id,
                "extraction_method": method,
                "pages_crawled": site_crawl.pages_crawled,
                "pages_merged": merged.pages_merged,
                "data": extracted_data,
            }, f, indent=2, default=str)
        console.print(f"  [dim]Extracted data saved to: {extracted_path}[/dim]")

    # Step 6: Generate quality metrics
    extraction_success = bool(extracted_data)
    total_time = extraction_time + (site_crawl.completed_at - site_crawl.started_at).total_seconds()

    metrics = generate_metrics(
        url=url,
        business_type=business_type,
        extraction_result=extracted_data,
        extraction_success=extraction_success,
        extraction_time=total_time,
        error_message=None if extraction_success else "Extraction failed",
    )

    # Display summary
    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"  Quality Score: {metrics.quality_score}")
    console.print(f"  Prices Found: {metrics.price_count}")
    console.print(f"  Has Contact: {metrics.has_contact_info}")
    console.print(f"  Total Time: {total_time:.1f}s")

    return site_crawl, merged, extracted_data, metrics


def display_batch_summary(
    results: List[Tuple[str, str, QualityMetrics]],
) -> None:
    """Display summary table for batch processing."""
    table = Table(title="Crawl Extraction Results")
    table.add_column("URL", style="cyan", max_width=40)
    table.add_column("Type", style="dim")
    table.add_column("Pages", justify="right")
    table.add_column("Quality", justify="right")
    table.add_column("Prices", justify="right")
    table.add_column("Status", justify="center")

    total_quality = 0
    total_prices = 0
    successful = 0

    for url, business_type, metrics in results:
        status = "[green]✓[/green]" if metrics.extraction_success else "[red]✗[/red]"
        # Note: pages_crawled would need to be passed through
        table.add_row(
            url[:40],
            business_type,
            "-",  # Would need to track pages
            str(metrics.quality_score),
            str(metrics.price_count),
            status,
        )
        total_quality += metrics.quality_score
        total_prices += metrics.price_count
        if metrics.extraction_success:
            successful += 1

    console.print(table)

    # Summary stats
    total = len(results)
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total businesses: {total}")
    console.print(f"  Successful: {successful}/{total} ({100*successful/total:.0f}%)")
    console.print(f"  Average quality: {total_quality/total:.1f}")
    console.print(f"  Total prices found: {total_prices}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Full site crawl extraction pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=ARCHITECTURE_SUMMARY,
    )
    parser.add_argument(
        "--url",
        help="URL to crawl and extract",
    )
    parser.add_argument(
        "--type",
        choices=[
            "dog_kennel", "cattery", "dog_groomer",
            "veterinary_clinic", "dog_daycare", "dog_sitter",
        ],
        help="Business type (required with --url)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run all URLs from sample_urls.py",
    )
    parser.add_argument(
        "--no-llm-classifier",
        action="store_true",
        help="Use rule-based classification only (no LLM costs)",
    )
    parser.add_argument(
        "--show-architecture",
        action="store_true",
        help="Display architecture summary and exit",
    )

    args = parser.parse_args()

    if args.show_architecture:
        console.print(ARCHITECTURE_SUMMARY)
        sys.exit(0)

    if not args.url and not args.batch:
        parser.print_help()
        console.print("\n[yellow]Specify --url or --batch[/yellow]")
        sys.exit(1)

    if args.url and not args.type:
        console.print("[red]Error: --type is required when using --url[/red]")
        sys.exit(1)

    # Create directories
    output_path, storage_path = ensure_directories()
    use_llm = not args.no_llm_classifier

    console.print("[bold cyan]Pet Care Full Site Crawl Extraction[/bold cyan]")
    console.print(f"[dim]LLM Classifier: {'enabled' if use_llm else 'disabled (rule-based only)'}[/dim]")
    console.print()

    if args.url:
        # Single URL mode
        try:
            site_crawl, merged, extracted, metrics = process_business(
                url=args.url,
                business_type=args.type,
                output_path=output_path,
                storage_path=storage_path,
                use_llm_classifier=use_llm,
            )

            if metrics.extraction_success:
                console.print("\n[green]Extraction completed successfully![/green]")
                sys.exit(0)
            else:
                console.print("\n[yellow]Extraction completed with issues[/yellow]")
                sys.exit(1)

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            sys.exit(1)

    elif args.batch:
        # Batch mode - process all URLs
        try:
            from sample_urls import get_all_urls
            test_urls = get_all_urls()
        except ImportError:
            console.print("[red]Error: sample_urls.py not found[/red]")
            sys.exit(1)

        console.print(f"Processing {len(test_urls)} URLs...")

        results = []
        for test_url in test_urls:
            try:
                site_crawl, merged, extracted, metrics = process_business(
                    url=test_url.url,
                    business_type=test_url.business_type,
                    output_path=output_path,
                    storage_path=storage_path,
                    use_llm_classifier=use_llm,
                )
                results.append((test_url.url, test_url.business_type, metrics))

                # Rate limiting between businesses
                time.sleep(2)

            except Exception as e:
                console.print(f"[red]Error processing {test_url.url}: {e}[/red]")
                # Create failed metrics
                results.append((
                    test_url.url,
                    test_url.business_type,
                    QualityMetrics(
                        url=test_url.url,
                        business_type=test_url.business_type,
                        quality_score=0,
                        extraction_success=False,
                        has_business_name=False,
                        has_contact_info=False,
                        has_pricing=False,
                        price_count=0,
                        has_vaccination_info=False,
                        has_policy_info=False,
                        extraction_time=0,
                        error_message=str(e),
                    ),
                ))

        display_batch_summary(results)

        # Save batch summary
        summary_path = output_path / "batch_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_urls": len(results),
                "results": [
                    {
                        "url": url,
                        "business_type": bt,
                        "quality_score": m.quality_score,
                        "success": m.extraction_success,
                        "prices": m.price_count,
                    }
                    for url, bt, m in results
                ],
            }, f, indent=2)
        console.print(f"\nBatch summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
