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
# Real UK pet care business URLs with pricing pages
TEST_URLS: Dict[str, List[TestURL]] = {
    "dog_kennel": [
        TestURL(
            url="https://www.harkersbarkers.co.uk/rates.html",
            business_type="dog_kennel",
            complexity="easy",
            notes="Clear pricing table, £27/day per dog",
            expected_features=["price_table", "vaccination_info"],
        ),
        TestURL(
            url="https://whitehouse-kennels.co.uk/price-list/",
            business_type="dog_kennel",
            complexity="easy",
            notes="Hotel-style per night pricing, 2026 prices",
            expected_features=["price_list", "booking_fee"],
        ),
        TestURL(
            url="https://ivykennels.co.uk/boarding-fees/",
            business_type="dog_kennel",
            complexity="medium",
            notes="Multi-dog pricing tiers, 1-3 dogs",
            expected_features=["tiered_pricing", "multi_dog_discount"],
        ),
        TestURL(
            url="https://honeybottomkennels.co.uk/boarding-prices-2026/",
            business_type="dog_kennel",
            complexity="medium",
            notes="Single night and longer stay discounts, 2026 prices",
            expected_features=["seasonal_pricing", "long_stay_discount"],
        ),
        TestURL(
            url="https://www.greenlanefarmboardingkennels.co.uk/prices/",
            business_type="dog_kennel",
            complexity="hard",
            notes="Size-based pricing (toy breeds), VAT separate",
            expected_features=["size_pricing", "vat_breakdown"],
        ),
        TestURL(
            url="https://meadowviewboardingkennels.co.uk/pricing/",
            business_type="dog_kennel",
            complexity="medium",
            notes="Norfolk kennels, dogs sharing pricing",
            expected_features=["multi_dog_discount", "christmas_pricing"],
        ),
    ],
    "cattery": [
        TestURL(
            url="https://www.pollyscatlodge.co.uk/prices-and-opening-times",
            business_type="cattery",
            complexity="easy",
            notes="Clear per day/week pricing, multi-cat rates",
            expected_features=["price_table", "delivery_service"],
        ),
        TestURL(
            url="https://www.catseyecattery.co.uk/our-rates/",
            business_type="cattery",
            complexity="easy",
            notes="Simple rates with long-stay discount",
            expected_features=["price_list", "long_stay_discount"],
        ),
        TestURL(
            url="https://www.oakworthcattery.co.uk/tariffs/",
            business_type="cattery",
            complexity="medium",
            notes="1-4 cats sharing, extra large rooms available",
            expected_features=["tiered_pricing", "room_types"],
        ),
        TestURL(
            url="https://www.cloverleacattery.co.uk/tariff-prices",
            business_type="cattery",
            complexity="hard",
            notes="Seasonal promotions, winter supplement charges",
            expected_features=["seasonal_pricing", "supplements"],
        ),
        TestURL(
            url="https://www.foxgloves-cattery.co.uk/boarding-fees",
            business_type="cattery",
            complexity="medium",
            notes="York cattery, enclosure size options",
            expected_features=["price_list", "room_sizes"],
        ),
    ],
    "dog_groomer": [
        TestURL(
            url="https://slobberandchops.com/pages/grooming-price-list",
            business_type="dog_groomer",
            complexity="easy",
            notes="Clear grooming price list",
            expected_features=["service_list", "size_pricing"],
        ),
        TestURL(
            url="https://www.absolutelyanimals.biz/dog-grooming-price-list/",
            business_type="dog_groomer",
            complexity="medium",
            notes="Minimum £65, requires £40 deposit",
            expected_features=["deposit_policy", "minimum_charge"],
        ),
        TestURL(
            url="https://brucesdoggydaycare.co.uk/service/dog-grooming/",
            business_type="dog_groomer",
            complexity="easy",
            notes="Puppy groom from £30, multiple service tiers",
            expected_features=["puppy_pricing", "service_tiers"],
        ),
        TestURL(
            url="https://pet-universe.co.uk/dog-grooming/dog-grooming-price-list/",
            business_type="dog_groomer",
            complexity="medium",
            notes="Detailed price list by service type",
            expected_features=["service_list", "price_table"],
        ),
        TestURL(
            url="https://www.pawfectly.co.uk/pricing",
            business_type="dog_groomer",
            complexity="hard",
            notes="Breed-specific pricing guide",
            expected_features=["breed_pricing", "coat_type_pricing"],
        ),
        TestURL(
            url="https://www.nimblefins.co.uk/average-cost-dog-grooming-uk",
            business_type="dog_groomer",
            complexity="hard",
            notes="Industry pricing guide with regional variations",
            expected_features=["regional_pricing", "service_breakdown"],
        ),
        TestURL(
            url="https://www.dogster.com/lifestyle/how-much-does-dog-grooming-cost-uk",
            business_type="dog_groomer",
            complexity="hard",
            notes="2026 price guide with size ranges",
            expected_features=["size_pricing", "service_types"],
        ),
        TestURL(
            url="https://articles.hepper.com/what-is-the-cost-of-dog-grooming-uk/",
            business_type="dog_groomer",
            complexity="medium",
            notes="Updated 2026 grooming costs",
            expected_features=["price_ranges", "factors"],
        ),
    ],
    "veterinary_clinic": [
        TestURL(
            url="https://www.bluecross.org.uk/check-our-affordable-prices",
            business_type="veterinary_clinic",
            complexity="easy",
            notes="Charity vet with price bands",
            expected_features=["price_bands", "operations"],
        ),
        TestURL(
            url="https://www.animaltrust.org.uk/prices",
            business_type="veterinary_clinic",
            complexity="easy",
            notes="Free consultations, pay for treatment only",
            expected_features=["consultation_fees", "treatment_prices"],
        ),
        TestURL(
            url="https://www.biltonvets.co.uk/prices",
            business_type="veterinary_clinic",
            complexity="medium",
            notes="January 2026 prices with VAT",
            expected_features=["price_list", "vaccinations"],
        ),
        TestURL(
            url="https://www.rvc.ac.uk/small-animal-vet/general-practice/price-list",
            business_type="veterinary_clinic",
            complexity="hard",
            notes="Royal Veterinary College comprehensive fees",
            expected_features=["comprehensive_fees", "specialist_services"],
        ),
        TestURL(
            url="https://www.beechhousevetclinic.co.uk/services-and-prices",
            business_type="veterinary_clinic",
            complexity="medium",
            notes="Services and prices combined page",
            expected_features=["service_list", "fee_list"],
        ),
        TestURL(
            url="https://thegreenvets.uk/price-list/",
            business_type="veterinary_clinic",
            complexity="medium",
            notes="York vets with vaccination and neutering prices",
            expected_features=["vaccinations", "neutering_prices"],
        ),
        TestURL(
            url="https://www.paxtonvets.co.uk/about-us/pricing",
            business_type="veterinary_clinic",
            complexity="medium",
            notes="South London vet prices",
            expected_features=["consultation_fees", "price_list"],
        ),
        TestURL(
            url="https://vethelpdirect.com/uk-vet-price-comparison/",
            business_type="veterinary_clinic",
            complexity="hard",
            notes="UK vet price comparison tool",
            expected_features=["price_comparison", "regional_data"],
        ),
        TestURL(
            url="https://www.sainsburysbank.co.uk/pet-insurance/guides/vet-fees",
            business_type="veterinary_clinic",
            complexity="hard",
            notes="Vet fee guide with treatment costs",
            expected_features=["treatment_costs", "fee_guide"],
        ),
        TestURL(
            url="https://manypets.com/uk/articles/dog-sitting-rates-services-and-benefits/",
            business_type="veterinary_clinic",
            complexity="hard",
            notes="Pet services cost guide",
            expected_features=["average_costs", "service_types"],
        ),
    ],
    "dog_daycare": [
        TestURL(
            url="https://frankiesdoggydaycare.co.uk/prices/",
            business_type="dog_daycare",
            complexity="easy",
            notes="Clear memberships and discounts",
            expected_features=["daily_rates", "multi_dog_discount"],
        ),
        TestURL(
            url="https://www.doggiedaycare-online.co.uk/our-prices/",
            business_type="dog_daycare",
            complexity="easy",
            notes="East Lothian daycare, £33/day",
            expected_features=["daily_rates", "puppy_pricing"],
        ),
        TestURL(
            url="https://bella-paws.co.uk/price-guide/",
            business_type="dog_daycare",
            complexity="medium",
            notes="Essex daycare, boarding and training prices",
            expected_features=["packages", "training_prices"],
        ),
        TestURL(
            url="https://dansdogdaycare.co.uk/price-list",
            business_type="dog_daycare",
            complexity="easy",
            notes="Simple price list format",
            expected_features=["price_list"],
        ),
        TestURL(
            url="https://www.thedoghousedaycare.co.uk/prices",
            business_type="dog_daycare",
            complexity="medium",
            notes="Suffolk daycare from £18, family discounts",
            expected_features=["daily_rates", "multi_dog_discount"],
        ),
        TestURL(
            url="https://happyhounds-beverley.co.uk/dog-boarding-and-daycare-price-list/",
            business_type="dog_daycare",
            complexity="medium",
            notes="Combined boarding and daycare prices",
            expected_features=["overnight_rates", "daycare_rates"],
        ),
    ],
    "dog_sitter": [
        TestURL(
            url="https://pawsitivewalks.co.uk/prices/",
            business_type="dog_sitter",
            complexity="easy",
            notes="Clear walking and sitting prices",
            expected_features=["walk_rates", "visit_rates"],
        ),
        TestURL(
            url="https://www.holtypaws.com/price-guide",
            business_type="dog_sitter",
            complexity="medium",
            notes="Solo walks £22/hr, home visits from £12",
            expected_features=["hourly_rates", "visit_rates"],
        ),
        TestURL(
            url="https://k9poshdogs.co.uk/charges/",
            business_type="dog_sitter",
            complexity="easy",
            notes="£16/hour walks, weekend premium rates",
            expected_features=["hourly_rates", "weekend_rates"],
        ),
        TestURL(
            url="https://www.wewalkwoofs.co.uk/harborne-dog-walkers-prices",
            business_type="dog_sitter",
            complexity="medium",
            notes="Birmingham area dog walking prices",
            expected_features=["walk_rates", "area_coverage"],
        ),
        TestURL(
            url="https://www.the-dogwalker.co.uk/payment-rates",
            business_type="dog_sitter",
            complexity="easy",
            notes="Simple payment rates page",
            expected_features=["walk_rates"],
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
