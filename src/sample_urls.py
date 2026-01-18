"""
URL collection and sample management for the Pet Care Data Extraction POC.

This module contains the test URLs organized by business type as specified
in PRD Section 6 - Test Cases & Sample Selection.

Sample Distribution (40 total URLs):
- Dog Kennels: 6
- Catteries: 5
- Dog Groomers: 8 (highest pricing complexity)
- Veterinary Clinics: 10 (most complex structure)
- Dog Daycare: 6
- Dog Sitters: 5

Selection Criteria per Type:
- 2-3 Professional websites with clear pricing
- 2-3 Basic websites with some pricing
- 1-2 Complex pricing (tables, tiers)
- 1 Edge case (prose pricing, PDF links)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class TestURL:
    """A test URL with metadata."""

    url: str
    business_type: str
    complexity: str  # "easy", "medium", "hard"
    notes: str
    expected_features: Optional[List[str]] = None


# Test URLs organized by business type
# NOTE: Replace placeholder URLs with real UK pet care business URLs
TEST_URLS: Dict[str, List[TestURL]] = {
    "dog_kennel": [
        TestURL(
            url="https://example-kennels.co.uk/prices",
            business_type="dog_kennel",
            complexity="easy",
            notes="Professional site with clear pricing table",
            expected_features=["price_table", "vaccination_info"],
        ),
        TestURL(
            url="https://happy-hounds-boarding.co.uk",
            business_type="dog_kennel",
            complexity="easy",
            notes="Simple pricing, per-night rates",
            expected_features=["price_list"],
        ),
        TestURL(
            url="https://luxury-dog-hotel.co.uk/rates",
            business_type="dog_kennel",
            complexity="medium",
            notes="Multiple room types, size-based pricing",
            expected_features=["tiered_pricing", "amenities"],
        ),
        TestURL(
            url="https://country-kennels.co.uk",
            business_type="dog_kennel",
            complexity="medium",
            notes="Multi-dog discounts, seasonal rates",
            expected_features=["multi_dog_discount", "seasonal"],
        ),
        TestURL(
            url="https://farm-boarding.co.uk/info",
            business_type="dog_kennel",
            complexity="hard",
            notes="Prices in prose text, less structured",
            expected_features=["prose_pricing"],
        ),
        TestURL(
            url="https://premium-kennels.co.uk",
            business_type="dog_kennel",
            complexity="hard",
            notes="Complex pricing with many add-ons",
            expected_features=["complex_pricing", "addons"],
        ),
    ],
    "cattery": [
        TestURL(
            url="https://whiskers-cattery.co.uk/prices",
            business_type="cattery",
            complexity="easy",
            notes="Clear pricing table for cat boarding",
            expected_features=["price_table"],
        ),
        TestURL(
            url="https://purrfect-stay.co.uk",
            business_type="cattery",
            complexity="easy",
            notes="Simple per-night rates",
            expected_features=["price_list"],
        ),
        TestURL(
            url="https://cat-hotel.co.uk/suites",
            business_type="cattery",
            complexity="medium",
            notes="Different suite types and sizes",
            expected_features=["tiered_pricing"],
        ),
        TestURL(
            url="https://feline-retreat.co.uk",
            business_type="cattery",
            complexity="medium",
            notes="Multi-cat discounts, family pens",
            expected_features=["multi_cat_discount"],
        ),
        TestURL(
            url="https://country-cattery.co.uk",
            business_type="cattery",
            complexity="hard",
            notes="Mixed pricing formats",
            expected_features=["mixed_format"],
        ),
    ],
    "dog_groomer": [
        TestURL(
            url="https://pampered-paws.co.uk/prices",
            business_type="dog_groomer",
            complexity="easy",
            notes="Simple size-based pricing",
            expected_features=["size_pricing"],
        ),
        TestURL(
            url="https://wags-grooming.co.uk",
            business_type="dog_groomer",
            complexity="easy",
            notes="Clear service list with prices",
            expected_features=["service_list"],
        ),
        TestURL(
            url="https://style-hounds.co.uk/services",
            business_type="dog_groomer",
            complexity="medium",
            notes="Breed-specific pricing",
            expected_features=["breed_pricing"],
        ),
        TestURL(
            url="https://luxury-groom.co.uk",
            business_type="dog_groomer",
            complexity="medium",
            notes="Packages and add-on services",
            expected_features=["packages", "addons"],
        ),
        TestURL(
            url="https://professional-grooming.co.uk/price-list",
            business_type="dog_groomer",
            complexity="hard",
            notes="Complex breed/size matrix pricing",
            expected_features=["matrix_pricing"],
        ),
        TestURL(
            url="https://doggy-spa.co.uk",
            business_type="dog_groomer",
            complexity="hard",
            notes="Multiple pricing tiers and coat types",
            expected_features=["coat_type_pricing"],
        ),
        TestURL(
            url="https://mobile-groomer.co.uk",
            business_type="dog_groomer",
            complexity="medium",
            notes="Mobile grooming with area surcharges",
            expected_features=["mobile_pricing"],
        ),
        TestURL(
            url="https://budget-groom.co.uk",
            business_type="dog_groomer",
            complexity="easy",
            notes="Basic flat-rate pricing",
            expected_features=["flat_rate"],
        ),
    ],
    "veterinary_clinic": [
        TestURL(
            url="https://town-vets.co.uk/fees",
            business_type="veterinary_clinic",
            complexity="easy",
            notes="Consultation fees clearly listed",
            expected_features=["consultation_fees"],
        ),
        TestURL(
            url="https://family-vets.co.uk/prices",
            business_type="veterinary_clinic",
            complexity="easy",
            notes="Basic fee list",
            expected_features=["fee_list"],
        ),
        TestURL(
            url="https://village-practice.co.uk",
            business_type="veterinary_clinic",
            complexity="medium",
            notes="Vaccination and procedure prices",
            expected_features=["vaccinations", "procedures"],
        ),
        TestURL(
            url="https://caring-vets.co.uk/services",
            business_type="veterinary_clinic",
            complexity="medium",
            notes="Health plans with pricing",
            expected_features=["health_plans"],
        ),
        TestURL(
            url="https://pet-hospital.co.uk",
            business_type="veterinary_clinic",
            complexity="hard",
            notes="Comprehensive fee schedule",
            expected_features=["comprehensive_fees"],
        ),
        TestURL(
            url="https://specialist-vets.co.uk",
            business_type="veterinary_clinic",
            complexity="hard",
            notes="Specialist services, complex pricing",
            expected_features=["specialist_pricing"],
        ),
        TestURL(
            url="https://24hr-emergency-vets.co.uk",
            business_type="veterinary_clinic",
            complexity="medium",
            notes="Emergency/out-of-hours fees",
            expected_features=["emergency_fees"],
        ),
        TestURL(
            url="https://low-cost-vets.co.uk",
            business_type="veterinary_clinic",
            complexity="easy",
            notes="Budget vet with simple pricing",
            expected_features=["simple_pricing"],
        ),
        TestURL(
            url="https://premium-pet-care.co.uk",
            business_type="veterinary_clinic",
            complexity="hard",
            notes="PDF price list, contact for quote",
            expected_features=["pdf_pricing"],
        ),
        TestURL(
            url="https://countryside-vets.co.uk",
            business_type="veterinary_clinic",
            complexity="medium",
            notes="Mixed small and large animal",
            expected_features=["mixed_animals"],
        ),
    ],
    "dog_daycare": [
        TestURL(
            url="https://happy-tails-daycare.co.uk/prices",
            business_type="dog_daycare",
            complexity="easy",
            notes="Simple daily rates",
            expected_features=["daily_rates"],
        ),
        TestURL(
            url="https://doggy-daycare.co.uk",
            business_type="dog_daycare",
            complexity="easy",
            notes="Full day and half day options",
            expected_features=["half_day", "full_day"],
        ),
        TestURL(
            url="https://play-pals.co.uk/packages",
            business_type="dog_daycare",
            complexity="medium",
            notes="Package deals available",
            expected_features=["packages"],
        ),
        TestURL(
            url="https://premium-daycare.co.uk",
            business_type="dog_daycare",
            complexity="medium",
            notes="Membership pricing tiers",
            expected_features=["memberships"],
        ),
        TestURL(
            url="https://adventure-dogs.co.uk",
            business_type="dog_daycare",
            complexity="hard",
            notes="Complex package/membership matrix",
            expected_features=["complex_packages"],
        ),
        TestURL(
            url="https://social-pups.co.uk",
            business_type="dog_daycare",
            complexity="medium",
            notes="Trial day and regular pricing",
            expected_features=["trial_pricing"],
        ),
    ],
    "dog_sitter": [
        TestURL(
            url="https://local-dog-walker.co.uk/rates",
            business_type="dog_sitter",
            complexity="easy",
            notes="Simple per-walk pricing",
            expected_features=["walk_rates"],
        ),
        TestURL(
            url="https://trusted-pet-sitter.co.uk",
            business_type="dog_sitter",
            complexity="easy",
            notes="Home visit and walking rates",
            expected_features=["visit_rates", "walk_rates"],
        ),
        TestURL(
            url="https://professional-dog-walker.co.uk/services",
            business_type="dog_sitter",
            complexity="medium",
            notes="Multiple service types",
            expected_features=["multiple_services"],
        ),
        TestURL(
            url="https://overnight-pet-care.co.uk",
            business_type="dog_sitter",
            complexity="medium",
            notes="Overnight and day sitting options",
            expected_features=["overnight_rates"],
        ),
        TestURL(
            url="https://pet-sitting-service.co.uk",
            business_type="dog_sitter",
            complexity="hard",
            notes="Geographic zone pricing",
            expected_features=["zone_pricing"],
        ),
    ],
}


def get_urls_by_type(business_type: str) -> List[TestURL]:
    """Get all test URLs for a specific business type.

    Args:
        business_type: The type of business.

    Returns:
        List of TestURL objects for that type.

    Raises:
        ValueError: If business_type is not found.
    """
    if business_type not in TEST_URLS:
        raise ValueError(
            f"Unknown business type: {business_type}. "
            f"Available types: {list(TEST_URLS.keys())}"
        )
    return TEST_URLS[business_type]


def get_all_urls() -> List[TestURL]:
    """Get all test URLs across all business types.

    Returns:
        Flat list of all TestURL objects.
    """
    all_urls = []
    for urls in TEST_URLS.values():
        all_urls.extend(urls)
    return all_urls


def get_urls_by_complexity(complexity: str) -> List[TestURL]:
    """Get all test URLs with a specific complexity level.

    Args:
        complexity: One of "easy", "medium", "hard".

    Returns:
        List of TestURL objects matching the complexity.
    """
    matching = []
    for urls in TEST_URLS.values():
        for url in urls:
            if url.complexity == complexity:
                matching.append(url)
    return matching


def get_sample_statistics() -> Dict[str, int]:
    """Get statistics about the test sample.

    Returns:
        Dictionary with count statistics.
    """
    stats = {
        "total": 0,
        "by_type": {},
        "by_complexity": {"easy": 0, "medium": 0, "hard": 0},
    }

    for business_type, urls in TEST_URLS.items():
        stats["by_type"][business_type] = len(urls)
        stats["total"] += len(urls)
        for url in urls:
            stats["by_complexity"][url.complexity] += 1

    return stats


def validate_urls() -> List[str]:
    """Validate that all URLs are properly formatted.

    Returns:
        List of validation error messages (empty if all valid).
    """
    errors = []

    for business_type, urls in TEST_URLS.items():
        for url in urls:
            if not url.url.startswith("http"):
                errors.append(f"Invalid URL format: {url.url}")
            if url.business_type != business_type:
                errors.append(
                    f"Mismatched business type for {url.url}: "
                    f"expected {business_type}, got {url.business_type}"
                )
            if url.complexity not in ("easy", "medium", "hard"):
                errors.append(f"Invalid complexity for {url.url}: {url.complexity}")

    return errors


if __name__ == "__main__":
    # Print sample statistics when run directly
    stats = get_sample_statistics()
    print(f"Total URLs: {stats['total']}")
    print("\nBy business type:")
    for btype, count in stats["by_type"].items():
        print(f"  {btype}: {count}")
    print("\nBy complexity:")
    for complexity, count in stats["by_complexity"].items():
        print(f"  {complexity}: {count}")

    # Validate URLs
    errors = validate_urls()
    if errors:
        print("\nValidation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\nAll URLs valid!")
