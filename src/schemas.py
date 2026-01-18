"""
Pydantic schemas for structured data extraction across 6 pet care business types.

This module defines the data models used by Firecrawl for extracting
structured information from pet care business websites.

Reference: PRD Section 2, Appendix B
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    """Contact information for a business."""

    phone: Optional[str] = Field(None, description="Primary phone number")
    email: Optional[str] = Field(None, description="Primary email address")
    address: Optional[str] = Field(None, description="Physical address")
    website: Optional[str] = Field(None, description="Website URL if different from scraped URL")


class ServicePrice(BaseModel):
    """A single service with pricing information."""

    service_name: str = Field(..., description="Name of the service")
    price: Optional[float] = Field(None, description="Price as a decimal number")
    price_text: Optional[str] = Field(
        None, description="Original price text if parsing fails (e.g., 'from 25')"
    )
    unit: Optional[str] = Field(
        None,
        description="Pricing unit (e.g., 'per_night', 'per_session', 'per_hour')",
    )
    description: Optional[str] = Field(None, description="Additional service description")
    variations: Optional[List[str]] = Field(
        None, description="Service variations (e.g., sizes, breeds)"
    )


class VaccinationRequirement(BaseModel):
    """Vaccination requirement for pets."""

    vaccine_name: str = Field(..., description="Name of required vaccination")
    requirement_details: Optional[str] = Field(
        None, description="Additional requirements (e.g., 'within 12 months')"
    )


class BusinessExtraction(BaseModel):
    """
    Main schema for extracting pet care business information.

    This unified schema works across all business types:
    - Dog Kennels: Per-night rates, size tiers, multi-dog discounts
    - Catteries: Per-night rates, multi-cat discounts, pen types
    - Dog Groomers: Breed-specific, coat-type, size-based pricing
    - Veterinary Clinics: Procedures, diagnostics, consultations
    - Dog Daycare: Full/half day, packages, memberships
    - Dog Sitters: Per-walk, per-visit, overnight rates
    """

    # Basic business info
    business_name: Optional[str] = Field(
        None, description="Official name of the business"
    )
    business_type: Optional[str] = Field(
        None,
        description="Type of business (dog_kennel, cattery, dog_groomer, veterinary_clinic, dog_daycare, dog_sitter)",
    )
    description: Optional[str] = Field(
        None, description="Brief description of the business"
    )

    # Contact information
    contact: Optional[ContactInfo] = Field(None, description="Contact details")

    # Services and pricing
    services: List[ServicePrice] = Field(
        default_factory=list, description="List of services with prices"
    )

    # Pet requirements
    vaccination_requirements: List[VaccinationRequirement] = Field(
        default_factory=list, description="Required vaccinations for pets"
    )

    # Procedures and policies
    drop_off_procedure: Optional[str] = Field(
        None, description="Check-in/drop-off procedure"
    )
    pick_up_procedure: Optional[str] = Field(
        None, description="Check-out/pick-up procedure"
    )
    cancellation_policy: Optional[str] = Field(
        None, description="Cancellation policy details"
    )
    deposit_policy: Optional[str] = Field(
        None, description="Deposit requirements"
    )

    # Additional info
    amenities: List[str] = Field(
        default_factory=list, description="Available amenities and features"
    )
    opening_hours: Optional[str] = Field(
        None, description="Business operating hours"
    )
    special_notes: Optional[str] = Field(
        None, description="Any other important information"
    )


# Business-type-specific extraction prompts
EXTRACTION_PROMPTS = {
    "dog_kennel": """
Extract information from this dog boarding kennel website. Focus on:
- Business name and contact details
- Boarding rates (per night, per day)
- Different kennel/room types and their prices
- Multi-dog discounts
- Required vaccinations (especially kennel cough)
- Drop-off and pick-up times/procedures
- Cancellation and deposit policies
- Amenities (outdoor runs, heating, webcams, etc.)

Extract all pricing information you can find, including any size-based tiers
(small, medium, large dogs) and seasonal variations.
""",
    "cattery": """
Extract information from this cattery/cat boarding website. Focus on:
- Business name and contact details
- Boarding rates (per night, per day)
- Different pen/suite types and their prices
- Multi-cat discounts (same family)
- Required vaccinations
- Drop-off and pick-up times/procedures
- Cancellation and deposit policies
- Amenities (heating, individual rooms, outdoor access, etc.)

Extract all pricing information you can find.
""",
    "dog_groomer": """
Extract information from this dog grooming website. Focus on:
- Business name and contact details
- Grooming services and prices
- Different pricing by dog size (small, medium, large, giant)
- Different pricing by coat type or breed
- Individual services (bath, nail trim, ear cleaning, etc.)
- Package deals or combinations
- Puppy/first groom pricing

Extract ALL pricing information, noting size/breed variations.
This type often has complex pricing tables - capture everything.
""",
    "veterinary_clinic": """
Extract information from this veterinary clinic website. Focus on:
- Practice name and contact details
- Consultation fees (standard, emergency, out-of-hours)
- Vaccination prices
- Common procedure prices if listed
- Diagnostic services (blood tests, x-rays, etc.)
- Health plans or wellness packages
- Registration fees for new clients

Extract whatever pricing is publicly available. Many vets don't list all prices,
so capture what's there and note any "contact for quote" situations.
""",
    "dog_daycare": """
Extract information from this dog daycare website. Focus on:
- Business name and contact details
- Day care rates (full day, half day)
- Package deals (5 days, 10 days, monthly)
- Membership or subscription options
- Trial day pricing
- Multi-dog discounts
- Required vaccinations
- Drop-off and pick-up times
- Cancellation policy

Extract all pricing including any package or bulk discounts.
""",
    "dog_sitter": """
Extract information from this dog sitting/walking service website. Focus on:
- Business name and contact details
- Dog walking prices (30 min, 1 hour)
- Home visit prices
- Overnight sitting rates
- Puppy visit rates
- Additional dog pricing
- Geographic coverage area
- Cancellation policy

This type typically has straightforward pricing - capture all service types and rates.
""",
}


def get_extraction_prompt(business_type: str) -> str:
    """Get the extraction prompt for a specific business type.

    Args:
        business_type: One of the supported business types.

    Returns:
        The extraction prompt string.

    Raises:
        ValueError: If business_type is not supported.
    """
    if business_type not in EXTRACTION_PROMPTS:
        raise ValueError(
            f"Unknown business type: {business_type}. "
            f"Supported types: {list(EXTRACTION_PROMPTS.keys())}"
        )
    return EXTRACTION_PROMPTS[business_type]


def get_schema_dict() -> dict:
    """Get the JSON schema dictionary for Firecrawl.

    Returns:
        The JSON schema as a dictionary.
    """
    return BusinessExtraction.model_json_schema()
