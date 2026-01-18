#!/usr/bin/env python3
"""
Quick test script for validating Firecrawl API connectivity and basic extraction.

Usage:
    python quick_test.py <url> <business_type>

Example:
    python quick_test.py "https://example-kennels.co.uk" dog_kennel
"""

import argparse
import json
import sys
import time
from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax

try:
    from firecrawl import FirecrawlApp
except ImportError:
    print("Error: firecrawl-py not installed. Run: pip install firecrawl-py")
    sys.exit(1)

from config import BUSINESS_TYPES, get_config
from schemas import BusinessExtraction, get_extraction_prompt

console = Console()


def test_api_connectivity(app: FirecrawlApp) -> bool:
    """Test if the Firecrawl API is accessible."""
    console.print("[cyan]Testing API connectivity...[/cyan]")
    try:
        # Try a simple scrape to verify API key works
        result = app.scrape(
            "https://example.com",
            formats=["markdown"],
            timeout=10000,
        )
        if result and hasattr(result, "markdown"):
            console.print("[green]API connectivity: OK[/green]")
            return True
        else:
            console.print("[red]API connectivity: Failed (unexpected response)[/red]")
            return False
    except Exception as e:
        console.print(f"[red]API connectivity: Failed ({e})[/red]")
        return False


def run_pass1_capture(app: FirecrawlApp, url: str, config: Any) -> Dict[str, Any]:
    """Run Pass 1: Content Capture."""
    console.print(f"\n[cyan]Pass 1: Content Capture[/cyan]")
    console.print(f"  URL: {url}")

    start_time = time.time()

    result = app.scrape(
        url,
        formats=["markdown", "html"],
        wait_for=config.capture_wait_for,
        timeout=config.capture_timeout,
        only_main_content=config.capture_only_main_content,
    )

    elapsed = time.time() - start_time

    # Extract content
    markdown_content = getattr(result, "markdown", "") or ""
    html_content = getattr(result, "html", "") or ""
    metadata = getattr(result, "metadata", {}) or {}

    console.print(f"  [green]Capture completed in {elapsed:.1f}s[/green]")
    console.print(f"  Markdown length: {len(markdown_content):,} chars")
    console.print(f"  HTML length: {len(html_content):,} chars")
    console.print(f"  Title: {metadata.get('title', 'N/A') if isinstance(metadata, dict) else 'N/A'}")

    return {
        "markdown": markdown_content,
        "html": html_content,
        "metadata": metadata,
        "capture_time": elapsed,
    }


def run_pass2_extraction(
    app: FirecrawlApp, url: str, business_type: str, config: Any
) -> Dict[str, Any]:
    """Run Pass 2: Structured Extraction."""
    console.print(f"\n[cyan]Pass 2: Structured Extraction[/cyan]")
    console.print(f"  Business type: {business_type}")

    # Get schema and prompt
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

        # Extract data from result
        extracted_data = {}
        if hasattr(result, "data") and result.data:
            extracted_data = result.data if isinstance(result.data, dict) else {}
        elif isinstance(result, dict):
            extracted_data = result.get("data", {})

        console.print(f"  [green]Extraction completed in {elapsed:.1f}s[/green]")

        return {
            "success": True,
            "data": extracted_data,
            "extraction_time": elapsed,
            "error": None,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        console.print(f"  [red]Extraction failed: {e}[/red]")

        return {
            "success": False,
            "data": {},
            "extraction_time": elapsed,
            "error": str(e),
        }


def display_results(
    pass1_result: Dict[str, Any],
    pass2_result: Dict[str, Any],
    business_type: str,
) -> None:
    """Display extraction results in a formatted way."""
    console.print("\n")
    console.print(Panel.fit("[bold]Extraction Results[/bold]", style="cyan"))

    # Pass 1 summary
    console.print("\n[bold]Pass 1 Summary:[/bold]")
    console.print(f"  Markdown: {len(pass1_result['markdown']):,} chars")
    console.print(f"  HTML: {len(pass1_result['html']):,} chars")
    console.print(f"  Time: {pass1_result['capture_time']:.1f}s")

    # Pass 2 summary
    console.print("\n[bold]Pass 2 Summary:[/bold]")
    if pass2_result["success"]:
        console.print("  [green]Status: Success[/green]")
        console.print(f"  Time: {pass2_result['extraction_time']:.1f}s")

        # Display extracted data
        data = pass2_result["data"]
        console.print(f"\n[bold]Extracted Data:[/bold]")
        console.print(f"  Business Name: {data.get('business_name', 'N/A')}")
        console.print(f"  Business Type: {data.get('business_type', business_type)}")

        # Contact info
        contact = data.get("contact", {})
        if contact:
            console.print(f"  Phone: {contact.get('phone', 'N/A')}")
            console.print(f"  Email: {contact.get('email', 'N/A')}")

        # Services/Pricing
        services = data.get("services", [])
        if services:
            console.print(f"\n  [bold]Services ({len(services)} found):[/bold]")
            for svc in services[:5]:  # Show first 5
                name = svc.get("service_name", "Unknown")
                price = svc.get("price", "N/A")
                unit = svc.get("unit", "")
                console.print(f"    - {name}: {price} {unit}")
            if len(services) > 5:
                console.print(f"    ... and {len(services) - 5} more")
        else:
            console.print("  [yellow]No pricing data found[/yellow]")

        # Full JSON
        console.print("\n[bold]Full Extracted JSON:[/bold]")
        json_str = json.dumps(data, indent=2, default=str)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
        console.print(syntax)

    else:
        console.print(f"  [red]Status: Failed[/red]")
        console.print(f"  Error: {pass2_result['error']}")


def main():
    """Main entry point for quick test."""
    parser = argparse.ArgumentParser(
        description="Quick test for Firecrawl extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Business types: {', '.join(BUSINESS_TYPES)}

Example:
    python quick_test.py "https://example-kennels.co.uk" dog_kennel
""",
    )
    parser.add_argument("url", help="URL to test")
    parser.add_argument(
        "business_type",
        choices=BUSINESS_TYPES,
        help="Type of pet care business",
    )
    parser.add_argument(
        "--skip-connectivity",
        action="store_true",
        help="Skip API connectivity test",
    )

    args = parser.parse_args()

    console.print(Panel.fit("[bold cyan]Pet Care Data Extraction - Quick Test[/bold cyan]"))

    try:
        # Get configuration
        config = get_config()
        console.print(f"[green]API key loaded successfully[/green]")

        # Initialize Firecrawl
        app = FirecrawlApp(api_key=config.api_key)

        # Test connectivity
        if not args.skip_connectivity:
            if not test_api_connectivity(app):
                console.print("[red]Aborting due to connectivity issues[/red]")
                sys.exit(1)

        # Run Pass 1: Content Capture
        pass1_result = run_pass1_capture(app, args.url, config)

        # Run Pass 2: Structured Extraction
        pass2_result = run_pass2_extraction(app, args.url, args.business_type, config)

        # Display results
        display_results(pass1_result, pass2_result, args.business_type)

        # Summary
        total_time = pass1_result["capture_time"] + pass2_result["extraction_time"]
        console.print(f"\n[cyan]Total extraction time: {total_time:.1f}s[/cyan]")

        if pass2_result["success"]:
            console.print("[green]Quick test completed successfully![/green]")
            sys.exit(0)
        else:
            console.print("[yellow]Quick test completed with extraction errors[/yellow]")
            sys.exit(1)

    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
