#!/usr/bin/env python3
"""
Full test extraction pipeline for the Pet Care Data Extraction POC.

Implements the two-pass extraction strategy from PRD Section 5.1:
- Pass 1: Content Capture (markdown, HTML)
- Pass 2: Structured Extraction (JSON with schema)
- Fallback: Prompt-only extraction if schema fails

Usage:
    python test_extraction.py                    # Run all URLs
    python test_extraction.py --type dog_kennel  # Run specific type
    python test_extraction.py --url <url> --type dog_kennel  # Single URL
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

try:
    from firecrawl import FirecrawlApp
except ImportError:
    print("Error: firecrawl-py not installed. Run: pip install firecrawl-py")
    sys.exit(1)

from config import DEFAULT_OUTPUT_DIR, get_config
from quality_scoring import (
    QualityMetrics,
    aggregate_by_business_type,
    aggregate_scores,
    format_quality_report,
    generate_metrics,
)
from sample_urls import TestURL, get_all_urls, get_urls_by_type
from schemas import BusinessExtraction, get_extraction_prompt

console = Console()


def ensure_output_dir(output_dir: str) -> Path:
    """Create output directory if it doesn't exist."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_filename(url: str, business_type: str, suffix: str) -> str:
    """Generate a filename from URL and business type."""
    # Extract domain from URL
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").replace(".", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{business_type}_{domain}_{timestamp}_{suffix}"


def run_pass1(
    app: FirecrawlApp,
    url: str,
    config: Any,
) -> Tuple[Dict[str, Any], float]:
    """
    Run Pass 1: Content Capture.

    Returns:
        Tuple of (result_dict, elapsed_time)
    """
    start_time = time.time()

    try:
        result = app.scrape(
            url,
            formats=["markdown", "html"],
            wait_for=config.capture_wait_for,
            timeout=config.capture_timeout,
            only_main_content=config.capture_only_main_content,
        )

        elapsed = time.time() - start_time

        return {
            "success": True,
            "markdown": getattr(result, "markdown", "") or "",
            "html": getattr(result, "html", "") or "",
            "metadata": getattr(result, "metadata", {}) or {},
            "error": None,
        }, elapsed

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "markdown": "",
            "html": "",
            "metadata": {},
            "error": str(e),
        }, elapsed


def run_pass2(
    app: FirecrawlApp,
    url: str,
    business_type: str,
    config: Any,
) -> Tuple[Dict[str, Any], float]:
    """
    Run Pass 2: Structured Extraction with schema.

    Returns:
        Tuple of (result_dict, elapsed_time)
    """
    schema = BusinessExtraction.model_json_schema()
    prompt = get_extraction_prompt(business_type)

    start_time = time.time()

    try:
        result = app.extract(
            urls=[url],
            schema=schema,
            prompt=prompt,
            timeout=config.extraction_timeout,
        )

        elapsed = time.time() - start_time
        # Extract returns a list of results, get first one
        extracted = {}
        if hasattr(result, "data") and result.data:
            extracted = result.data if isinstance(result.data, dict) else {}
        elif isinstance(result, dict):
            extracted = result.get("data", {})

        return {
            "success": True,
            "data": extracted,
            "method": "schema",
            "error": None,
        }, elapsed

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "data": {},
            "method": "schema",
            "error": str(e),
        }, elapsed


def run_fallback_extraction(
    app: FirecrawlApp,
    url: str,
    business_type: str,
    config: Any,
) -> Tuple[Dict[str, Any], float]:
    """
    Run fallback: Prompt-only extraction without schema.

    Returns:
        Tuple of (result_dict, elapsed_time)
    """
    prompt = get_extraction_prompt(business_type) + """

Return the data as a JSON object with these fields:
- business_name: string
- business_type: string
- contact: {phone, email, address}
- services: [{service_name, price, unit, description}]
- vaccination_requirements: [{vaccine_name, requirement_details}]
- cancellation_policy: string
- deposit_policy: string
- amenities: [string]
- opening_hours: string
"""

    start_time = time.time()

    try:
        result = app.extract(
            urls=[url],
            prompt=prompt,
            timeout=config.extraction_timeout,
        )

        elapsed = time.time() - start_time
        extracted = {}
        if hasattr(result, "data") and result.data:
            extracted = result.data if isinstance(result.data, dict) else {}
        elif isinstance(result, dict):
            extracted = result.get("data", {})

        return {
            "success": True,
            "data": extracted,
            "method": "fallback",
            "error": None,
        }, elapsed

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "data": {},
            "method": "fallback",
            "error": str(e),
        }, elapsed


def extract_with_fallback(
    app: FirecrawlApp,
    url: str,
    business_type: str,
    config: Any,
) -> Tuple[Dict[str, Any], float, str]:
    """
    Full extraction pipeline with fallback.

    Returns:
        Tuple of (extracted_data, total_time, method_used)
    """
    # Try schema-based extraction first
    result, elapsed = run_pass2(app, url, business_type, config)

    if result["success"]:
        return result["data"], elapsed, "schema"

    # Fallback to prompt-only if schema fails
    fallback_result, fallback_elapsed = run_fallback_extraction(
        app, url, business_type, config
    )

    total_time = elapsed + fallback_elapsed

    if fallback_result["success"]:
        return fallback_result["data"], total_time, "fallback"

    # Both failed
    return {}, total_time, "failed"


def process_url(
    app: FirecrawlApp,
    test_url: TestURL,
    config: Any,
    output_dir: Path,
) -> QualityMetrics:
    """
    Process a single URL through the full extraction pipeline.

    Returns:
        QualityMetrics for the extraction.
    """
    url = test_url.url
    business_type = test_url.business_type

    total_time = 0.0
    error_message = None

    # Pass 1: Content Capture
    pass1_result, pass1_time = run_pass1(app, url, config)
    total_time += pass1_time

    # Save markdown if successful
    if pass1_result["success"] and pass1_result["markdown"]:
        md_filename = generate_filename(url, business_type, "markdown.md")
        md_path = output_dir / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(pass1_result["markdown"])

    # Pass 2: Structured Extraction (with fallback)
    extracted_data, pass2_time, method = extract_with_fallback(
        app, url, business_type, config
    )
    total_time += pass2_time

    extraction_success = bool(extracted_data)

    if not extraction_success:
        error_message = f"Extraction failed (Pass 1: {pass1_result.get('error', 'OK')}, Pass 2: failed)"

    # Save extracted data
    if extracted_data:
        json_filename = generate_filename(url, business_type, "extracted.json")
        json_path = output_dir / json_filename
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "url": url,
                    "business_type": business_type,
                    "extraction_method": method,
                    "data": extracted_data,
                    "pass1_success": pass1_result["success"],
                    "metadata": pass1_result.get("metadata", {}),
                },
                f,
                indent=2,
                default=str,
            )

    # Generate quality metrics
    metrics = generate_metrics(
        url=url,
        business_type=business_type,
        extraction_result=extracted_data,
        extraction_success=extraction_success,
        extraction_time=total_time,
        error_message=error_message,
    )

    # Save metrics
    metrics_filename = generate_filename(url, business_type, "metrics.json")
    metrics_path = output_dir / metrics_filename
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics.to_dict(), f, indent=2)

    return metrics


def run_extraction_batch(
    urls: List[TestURL],
    output_dir: str = DEFAULT_OUTPUT_DIR,
    delay: float = 1.0,
) -> List[QualityMetrics]:
    """
    Run extraction on a batch of URLs.

    Args:
        urls: List of TestURL objects to process.
        output_dir: Directory to save results.
        delay: Delay between requests in seconds.

    Returns:
        List of QualityMetrics for all processed URLs.
    """
    config = get_config()
    app = FirecrawlApp(api_key=config.api_key)
    output_path = ensure_output_dir(output_dir)

    all_metrics: List[QualityMetrics] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting...", total=len(urls))

        for i, test_url in enumerate(urls):
            progress.update(
                task,
                description=f"[cyan]Processing {test_url.url[:50]}...[/cyan]",
            )

            try:
                metrics = process_url(app, test_url, config, output_path)
                all_metrics.append(metrics)

                # Display result
                status = (
                    "[green]OK[/green]"
                    if metrics.extraction_success
                    else "[red]FAIL[/red]"
                )
                console.print(
                    f"  {i+1}/{len(urls)} {status} "
                    f"Score: {metrics.quality_score} "
                    f"Prices: {metrics.price_count} "
                    f"Time: {metrics.extraction_time:.1f}s"
                )

            except Exception as e:
                console.print(f"  {i+1}/{len(urls)} [red]ERROR: {e}[/red]")
                # Create failed metrics
                all_metrics.append(
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
                    )
                )

            progress.update(task, advance=1)

            # Delay between requests
            if i < len(urls) - 1:
                time.sleep(delay)

    return all_metrics


def display_summary(metrics_list: List[QualityMetrics]) -> None:
    """Display summary statistics."""
    stats = aggregate_scores(metrics_list)
    by_type = aggregate_by_business_type(metrics_list)

    console.print("\n")
    report = format_quality_report(stats, by_type)
    console.print(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run pet care data extraction tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--type",
        choices=[
            "dog_kennel",
            "cattery",
            "dog_groomer",
            "veterinary_clinic",
            "dog_daycare",
            "dog_sitter",
        ],
        help="Run only URLs of this business type",
    )
    parser.add_argument(
        "--url",
        help="Test a single URL (requires --type)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    console.print("\n[bold cyan]Pet Care Data Extraction - Full Test Suite[/bold cyan]\n")

    # Determine which URLs to process
    if args.url:
        if not args.type:
            console.print("[red]Error: --url requires --type[/red]")
            sys.exit(1)
        urls = [
            TestURL(
                url=args.url,
                business_type=args.type,
                complexity="unknown",
                notes="Manual test",
            )
        ]
    elif args.type:
        urls = get_urls_by_type(args.type)
    else:
        urls = get_all_urls()

    console.print(f"URLs to process: {len(urls)}")
    console.print(f"Output directory: {args.output}")
    console.print("")

    try:
        # Run extraction
        metrics = run_extraction_batch(urls, args.output, args.delay)

        # Display summary
        display_summary(metrics)

        # Save summary
        output_path = Path(args.output)
        summary_path = output_path / "extraction_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "total_urls": len(metrics),
                    "metrics": [m.to_dict() for m in metrics],
                },
                f,
                indent=2,
            )
        console.print(f"\nSummary saved to: {summary_path}")

        # Exit with appropriate code
        stats = aggregate_scores(metrics)
        if stats.success_rate >= 80 and stats.average_quality_score >= 50:
            console.print("\n[green]Tests completed successfully![/green]")
            sys.exit(0)
        else:
            console.print("\n[yellow]Tests completed with issues.[/yellow]")
            sys.exit(1)

    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
