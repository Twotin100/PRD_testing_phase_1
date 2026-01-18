"""
Quality scoring system for extraction results.

Implements the automated quality scoring algorithm from PRD Section 5.3.

Quality Score (0-100) Components:
- Extraction succeeds: 20 points
- Business name found: 10 points
- Contact info found: 10 points (email OR phone OR address)
- Has pricing data: 30 points (at least 1 price found)
- Multiple prices (bonus): +2 per price, max 20 bonus points
- Vaccination info found: 5 points
- Policy info found: 5 points (cancellation OR deposit)

Success Targets (from PRD Section 7.1):
- Overall success rate: >90% (min 80%)
- Quality score average: >65 (min 50)
- Pricing data found: >75% (min 60%)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class QualityMetrics:
    """Metrics from quality scoring."""

    url: str
    business_type: str
    quality_score: int
    extraction_success: bool
    has_business_name: bool
    has_contact_info: bool
    has_pricing: bool
    price_count: int
    has_vaccination_info: bool
    has_policy_info: bool
    extraction_time: float
    error_message: Optional[str] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "business_type": self.business_type,
            "quality_score": self.quality_score,
            "extraction_success": self.extraction_success,
            "has_business_name": self.has_business_name,
            "has_contact_info": self.has_contact_info,
            "has_pricing": self.has_pricing,
            "price_count": self.price_count,
            "has_vaccination_info": self.has_vaccination_info,
            "has_policy_info": self.has_policy_info,
            "extraction_time": self.extraction_time,
            "error_message": self.error_message,
            "timestamp": self.timestamp or datetime.now().isoformat(),
        }


def calculate_quality_score(
    extraction_result: Dict[str, Any],
    extraction_success: bool = True,
) -> int:
    """
    Calculate quality score based on PRD Section 5.3 algorithm.

    Args:
        extraction_result: The extracted data dictionary.
        extraction_success: Whether extraction completed without errors.

    Returns:
        Quality score from 0-100.
    """
    score = 0

    # Extraction succeeds: 20 points
    if extraction_success:
        score += 20

    # Business name found: 10 points
    business_name = extraction_result.get("business_name", "")
    if business_name and isinstance(business_name, str) and business_name.strip():
        score += 10

    # Contact info found: 10 points (email OR phone OR address)
    contact = extraction_result.get("contact", {}) or {}
    has_contact = (
        bool(contact.get("email"))
        or bool(contact.get("phone"))
        or bool(contact.get("address"))
    )
    if has_contact:
        score += 10

    # Has pricing data: 30 points (at least 1 price found)
    services = extraction_result.get("services", []) or []
    prices_found = 0
    for service in services:
        if service.get("price") is not None or service.get("price_text"):
            prices_found += 1

    if prices_found > 0:
        score += 30

    # Multiple prices (bonus): +2 per price, max 20 bonus points
    if prices_found > 1:
        bonus = min((prices_found - 1) * 2, 20)
        score += bonus

    # Vaccination info found: 5 points
    vaccinations = extraction_result.get("vaccination_requirements", []) or []
    if vaccinations and len(vaccinations) > 0:
        score += 5

    # Policy info found: 5 points (cancellation OR deposit)
    has_cancellation = bool(extraction_result.get("cancellation_policy"))
    has_deposit = bool(extraction_result.get("deposit_policy"))
    if has_cancellation or has_deposit:
        score += 5

    return min(score, 100)  # Cap at 100


def generate_metrics(
    url: str,
    business_type: str,
    extraction_result: Dict[str, Any],
    extraction_success: bool,
    extraction_time: float,
    error_message: Optional[str] = None,
) -> QualityMetrics:
    """
    Generate quality metrics for an extraction.

    Args:
        url: The URL that was extracted.
        business_type: Type of business.
        extraction_result: The extracted data dictionary.
        extraction_success: Whether extraction completed without errors.
        extraction_time: Time taken for extraction in seconds.
        error_message: Error message if extraction failed.

    Returns:
        QualityMetrics instance.
    """
    # Calculate component values
    business_name = extraction_result.get("business_name", "")
    has_business_name = bool(
        business_name and isinstance(business_name, str) and business_name.strip()
    )

    contact = extraction_result.get("contact", {}) or {}
    has_contact_info = (
        bool(contact.get("email"))
        or bool(contact.get("phone"))
        or bool(contact.get("address"))
    )

    services = extraction_result.get("services", []) or []
    price_count = sum(
        1
        for service in services
        if service.get("price") is not None or service.get("price_text")
    )
    has_pricing = price_count > 0

    vaccinations = extraction_result.get("vaccination_requirements", []) or []
    has_vaccination_info = len(vaccinations) > 0

    has_cancellation = bool(extraction_result.get("cancellation_policy"))
    has_deposit = bool(extraction_result.get("deposit_policy"))
    has_policy_info = has_cancellation or has_deposit

    quality_score = calculate_quality_score(extraction_result, extraction_success)

    return QualityMetrics(
        url=url,
        business_type=business_type,
        quality_score=quality_score,
        extraction_success=extraction_success,
        has_business_name=has_business_name,
        has_contact_info=has_contact_info,
        has_pricing=has_pricing,
        price_count=price_count,
        has_vaccination_info=has_vaccination_info,
        has_policy_info=has_policy_info,
        extraction_time=extraction_time,
        error_message=error_message,
        timestamp=datetime.now().isoformat(),
    )


@dataclass
class AggregateStats:
    """Aggregate statistics for a set of extractions."""

    total_urls: int
    successful_extractions: int
    success_rate: float
    average_quality_score: float
    urls_with_pricing: int
    pricing_rate: float
    average_extraction_time: float
    total_prices_found: int


def aggregate_scores(metrics_list: List[QualityMetrics]) -> AggregateStats:
    """
    Calculate aggregate statistics from a list of metrics.

    Args:
        metrics_list: List of QualityMetrics instances.

    Returns:
        AggregateStats instance with summary statistics.
    """
    if not metrics_list:
        return AggregateStats(
            total_urls=0,
            successful_extractions=0,
            success_rate=0.0,
            average_quality_score=0.0,
            urls_with_pricing=0,
            pricing_rate=0.0,
            average_extraction_time=0.0,
            total_prices_found=0,
        )

    total = len(metrics_list)
    successful = sum(1 for m in metrics_list if m.extraction_success)
    with_pricing = sum(1 for m in metrics_list if m.has_pricing)
    total_prices = sum(m.price_count for m in metrics_list)
    total_score = sum(m.quality_score for m in metrics_list)
    total_time = sum(m.extraction_time for m in metrics_list)

    return AggregateStats(
        total_urls=total,
        successful_extractions=successful,
        success_rate=(successful / total * 100) if total > 0 else 0.0,
        average_quality_score=total_score / total if total > 0 else 0.0,
        urls_with_pricing=with_pricing,
        pricing_rate=(with_pricing / total * 100) if total > 0 else 0.0,
        average_extraction_time=total_time / total if total > 0 else 0.0,
        total_prices_found=total_prices,
    )


def aggregate_by_business_type(
    metrics_list: List[QualityMetrics],
) -> Dict[str, AggregateStats]:
    """
    Calculate aggregate statistics grouped by business type.

    Args:
        metrics_list: List of QualityMetrics instances.

    Returns:
        Dictionary mapping business type to AggregateStats.
    """
    by_type: Dict[str, List[QualityMetrics]] = {}
    for m in metrics_list:
        if m.business_type not in by_type:
            by_type[m.business_type] = []
        by_type[m.business_type].append(m)

    return {btype: aggregate_scores(metrics) for btype, metrics in by_type.items()}


def check_success_targets(stats: AggregateStats) -> Dict[str, Dict[str, Any]]:
    """
    Check if extraction results meet success targets from PRD Section 7.1.

    Args:
        stats: Aggregate statistics.

    Returns:
        Dictionary with pass/fail status for each target.
    """
    return {
        "success_rate": {
            "target": 90.0,
            "minimum": 80.0,
            "actual": stats.success_rate,
            "meets_target": stats.success_rate >= 90.0,
            "meets_minimum": stats.success_rate >= 80.0,
        },
        "quality_score": {
            "target": 65.0,
            "minimum": 50.0,
            "actual": stats.average_quality_score,
            "meets_target": stats.average_quality_score >= 65.0,
            "meets_minimum": stats.average_quality_score >= 50.0,
        },
        "pricing_rate": {
            "target": 75.0,
            "minimum": 60.0,
            "actual": stats.pricing_rate,
            "meets_target": stats.pricing_rate >= 75.0,
            "meets_minimum": stats.pricing_rate >= 60.0,
        },
    }


def format_quality_report(
    stats: AggregateStats, by_type: Optional[Dict[str, AggregateStats]] = None
) -> str:
    """
    Format a quality report as a string.

    Args:
        stats: Overall aggregate statistics.
        by_type: Optional per-business-type statistics.

    Returns:
        Formatted report string.
    """
    lines = [
        "QUALITY SCORE REPORT",
        "=" * 50,
        "",
        "Overall Statistics:",
        f"  Total URLs: {stats.total_urls}",
        f"  Successful: {stats.successful_extractions} ({stats.success_rate:.1f}%)",
        f"  Average Quality Score: {stats.average_quality_score:.1f}",
        f"  URLs with Pricing: {stats.urls_with_pricing} ({stats.pricing_rate:.1f}%)",
        f"  Total Prices Found: {stats.total_prices_found}",
        f"  Average Extraction Time: {stats.average_extraction_time:.1f}s",
        "",
    ]

    # Add success target check
    targets = check_success_targets(stats)
    lines.extend(
        [
            "Success Target Assessment:",
        ]
    )
    for metric, values in targets.items():
        status = (
            "PASS"
            if values["meets_target"]
            else ("MINIMUM" if values["meets_minimum"] else "FAIL")
        )
        lines.append(
            f"  {metric}: {values['actual']:.1f} "
            f"(target: {values['target']}, min: {values['minimum']}) [{status}]"
        )
    lines.append("")

    # Add per-type breakdown if available
    if by_type:
        lines.extend(
            [
                "By Business Type:",
                "  ┌──────────────────┬────────┬─────────┬───────────┬────────────┐",
                "  │ Type             │ Tested │ Success │ Avg Score │ Has Prices │",
                "  ├──────────────────┼────────┼─────────┼───────────┼────────────┤",
            ]
        )
        for btype, type_stats in sorted(by_type.items()):
            lines.append(
                f"  │ {btype:<16} │ {type_stats.total_urls:>6} │ "
                f"{type_stats.success_rate:>6.1f}% │ "
                f"{type_stats.average_quality_score:>9.1f} │ "
                f"{type_stats.pricing_rate:>9.1f}% │"
            )
        lines.append(
            "  └──────────────────┴────────┴─────────┴───────────┴────────────┘"
        )

    return "\n".join(lines)
