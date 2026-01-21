"""
Database schemas and Pydantic models for the full-site crawl architecture.

Implements versioned crawl storage with 18-month retention for audit purposes.
Re-crawl frequency: Every 6 months (3 versions retained per business).

Reference: Firecrawl /crawl endpoint documentation
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PageType(str, Enum):
    """Classification of crawled pages by content type."""

    PRICING = "pricing"           # Prices, rates, fees
    CONTACT = "contact"           # Contact details, location, map
    ABOUT = "about"               # About us, our story, team
    SERVICES = "services"         # Services offered, what we do
    TERMS = "terms"               # T&Cs, policies, cancellation
    FAQ = "faq"                   # FAQs, common questions
    BOOKING = "booking"           # Booking info, availability
    GALLERY = "gallery"           # Photos, images
    BLOG = "blog"                 # Blog posts, news, articles
    HOMEPAGE = "homepage"         # Main landing page
    OTHER = "other"               # Uncategorized


class CrawlStatus(str, Enum):
    """Status of a crawl job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"           # Some pages failed
    FAILED = "failed"


class CrawledPage(BaseModel):
    """A single page captured during a crawl."""

    url: str = Field(..., description="Full URL of the page")
    page_type: PageType = Field(PageType.OTHER, description="Classified page type")
    page_type_confidence: float = Field(0.0, description="Confidence score 0-1 for classification")

    # Content
    markdown: str = Field("", description="Markdown content of the page")
    html: Optional[str] = Field(None, description="Raw HTML content (optional, for audit)")

    # Metadata from Firecrawl
    title: Optional[str] = Field(None, description="Page title")
    description: Optional[str] = Field(None, description="Meta description")
    status_code: int = Field(200, description="HTTP status code")

    # Extraction relevance scoring
    relevance_score: float = Field(0.0, description="How relevant this page is for extraction (0-1)")
    word_count: int = Field(0, description="Approximate word count")
    has_pricing_signals: bool = Field(False, description="Contains price-like patterns")
    has_contact_signals: bool = Field(False, description="Contains contact-like patterns")

    # Timestamps
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class SiteCrawl(BaseModel):
    """A complete crawl of a business website."""

    # Identifiers
    crawl_id: str = Field(..., description="Unique crawl identifier from Firecrawl")
    business_url: str = Field(..., description="Starting URL for the crawl")
    business_type: str = Field(..., description="Type of pet care business")

    # Crawl metadata
    status: CrawlStatus = Field(CrawlStatus.PENDING)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)

    # Results
    pages: List[CrawledPage] = Field(default_factory=list)
    total_pages_found: int = Field(0)
    pages_crawled: int = Field(0)
    pages_failed: int = Field(0)

    # Cost tracking
    credits_used: int = Field(0)

    # Version control for 18-month retention
    crawl_version: int = Field(1, description="Version number for this business (1, 2, 3...)")
    expires_at: Optional[datetime] = Field(None, description="When this crawl data expires")

    # Error tracking
    errors: List[str] = Field(default_factory=list)


class PageClassification(BaseModel):
    """Result of LLM-based page classification."""

    page_type: PageType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: Optional[str] = Field(None, description="Brief explanation of classification")
    relevance_for_extraction: float = Field(..., ge=0.0, le=1.0)


class MergedContent(BaseModel):
    """Combined content from multiple pages for extraction."""

    crawl_id: str
    business_url: str
    business_type: str

    # Merged content by priority
    merged_markdown: str = Field(..., description="Combined markdown from relevant pages")

    # Source tracking
    source_pages: List[str] = Field(default_factory=list, description="URLs of pages included")
    page_types_included: List[PageType] = Field(default_factory=list)

    # Stats
    total_word_count: int = Field(0)
    pages_merged: int = Field(0)
    pages_excluded: int = Field(0)

    # Metadata
    merged_at: datetime = Field(default_factory=datetime.utcnow)


# SQL Schema for Supabase/PostgreSQL
DATABASE_SCHEMA = """
-- ============================================================================
-- PET CARE DATA PLATFORM - FULL SITE CRAWL SCHEMA
-- ============================================================================
-- Implements versioned crawl storage with 18-month retention
-- Re-crawl frequency: Every 6 months
-- ============================================================================

-- -----------------------------------------------------------------------------
-- ENUM TYPES
-- -----------------------------------------------------------------------------

CREATE TYPE page_type AS ENUM (
    'pricing', 'contact', 'about', 'services', 'terms',
    'faq', 'booking', 'gallery', 'blog', 'homepage', 'other'
);

CREATE TYPE crawl_status AS ENUM (
    'pending', 'in_progress', 'completed', 'partial', 'failed'
);

CREATE TYPE business_type AS ENUM (
    'dog_kennel', 'cattery', 'dog_groomer',
    'veterinary_clinic', 'dog_daycare', 'dog_sitter'
);

-- -----------------------------------------------------------------------------
-- BUSINESSES - Master record for each pet care business
-- -----------------------------------------------------------------------------

CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identification
    name TEXT,
    business_type business_type NOT NULL,
    primary_url TEXT NOT NULL UNIQUE,

    -- Contact (denormalized for quick access)
    phone TEXT,
    email TEXT,
    address TEXT,
    postcode TEXT,

    -- Metadata
    first_crawled_at TIMESTAMPTZ,
    last_crawled_at TIMESTAMPTZ,
    next_crawl_due TIMESTAMPTZ,  -- 6 months from last crawl
    crawl_count INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT true,
    last_extraction_quality_score INTEGER,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_businesses_type ON businesses(business_type);
CREATE INDEX idx_businesses_next_crawl ON businesses(next_crawl_due) WHERE is_active = true;
CREATE INDEX idx_businesses_postcode ON businesses(postcode);

-- -----------------------------------------------------------------------------
-- SITE_CRAWLS - Each full-site crawl execution
-- -----------------------------------------------------------------------------

CREATE TABLE site_crawls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,

    -- Firecrawl identifiers
    firecrawl_job_id TEXT NOT NULL,

    -- Crawl configuration (no limit = full site)
    starting_url TEXT NOT NULL,
    crawl_config JSONB DEFAULT '{}',  -- Store any config options used

    -- Status tracking
    status crawl_status DEFAULT 'pending',
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,

    -- Results summary
    total_pages_found INTEGER DEFAULT 0,
    pages_crawled INTEGER DEFAULT 0,
    pages_failed INTEGER DEFAULT 0,

    -- Cost tracking
    credits_used INTEGER DEFAULT 0,

    -- Version control (for 18-month retention policy)
    crawl_version INTEGER NOT NULL,  -- 1, 2, 3 for each business
    expires_at TIMESTAMPTZ NOT NULL,  -- 18 months from crawl date

    -- Error log
    errors JSONB DEFAULT '[]',

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_site_crawls_business ON site_crawls(business_id);
CREATE INDEX idx_site_crawls_status ON site_crawls(status);
CREATE INDEX idx_site_crawls_expires ON site_crawls(expires_at);

-- -----------------------------------------------------------------------------
-- PAGE_CAPTURES - Individual pages from each crawl
-- -----------------------------------------------------------------------------

CREATE TABLE page_captures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_crawl_id UUID REFERENCES site_crawls(id) ON DELETE CASCADE,

    -- Page identification
    url TEXT NOT NULL,
    url_path TEXT,  -- Path portion only (e.g., /prices)

    -- Classification (from cheap LLM)
    page_type page_type DEFAULT 'other',
    page_type_confidence FLOAT DEFAULT 0.0,
    classification_reasoning TEXT,

    -- Relevance scoring
    relevance_score FLOAT DEFAULT 0.0,  -- 0-1, how useful for extraction
    has_pricing_signals BOOLEAN DEFAULT false,
    has_contact_signals BOOLEAN DEFAULT false,

    -- Content storage
    markdown_content TEXT,
    html_content TEXT,  -- Optional, for audit trail

    -- Metadata from Firecrawl
    page_title TEXT,
    meta_description TEXT,
    http_status_code INTEGER DEFAULT 200,
    word_count INTEGER DEFAULT 0,

    -- Timestamps
    scraped_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_page_captures_crawl ON page_captures(site_crawl_id);
CREATE INDEX idx_page_captures_type ON page_captures(page_type);
CREATE INDEX idx_page_captures_relevance ON page_captures(relevance_score DESC);

-- -----------------------------------------------------------------------------
-- EXTRACTION_RUNS - Each extraction attempt from crawled content
-- -----------------------------------------------------------------------------

CREATE TABLE extraction_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_crawl_id UUID REFERENCES site_crawls(id) ON DELETE CASCADE,
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,

    -- Input tracking
    pages_used UUID[] DEFAULT '{}',  -- References to page_captures.id
    merged_content_hash TEXT,  -- For deduplication
    total_input_tokens INTEGER,

    -- Extraction configuration
    extraction_prompt TEXT,
    schema_version TEXT,

    -- Results
    extracted_data JSONB,  -- The BusinessExtraction result
    extraction_method TEXT,  -- 'schema', 'fallback', 'failed'

    -- Quality metrics
    quality_score INTEGER,
    prices_extracted INTEGER DEFAULT 0,
    fields_populated INTEGER DEFAULT 0,

    -- Cost tracking
    credits_used INTEGER DEFAULT 0,
    extraction_time_seconds FLOAT,

    -- Errors
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_extraction_runs_crawl ON extraction_runs(site_crawl_id);
CREATE INDEX idx_extraction_runs_business ON extraction_runs(business_id);
CREATE INDEX idx_extraction_runs_quality ON extraction_runs(quality_score DESC);

-- -----------------------------------------------------------------------------
-- NORMALIZED DATA TABLES (populated from extraction_runs)
-- -----------------------------------------------------------------------------

-- Size bands for price normalization
CREATE TABLE dog_size_bands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,  -- 'XS', 'S', 'M', 'L', 'XL', 'G'
    name TEXT NOT NULL,
    min_weight_kg FLOAT,
    max_weight_kg FLOAT,
    typical_breeds TEXT[]
);

-- Insert standard size bands
INSERT INTO dog_size_bands (code, name, min_weight_kg, max_weight_kg, typical_breeds) VALUES
    ('XS', 'Extra Small / Toy', 0, 4, ARRAY['Chihuahua', 'Yorkshire Terrier', 'Pomeranian']),
    ('S', 'Small', 4, 10, ARRAY['Jack Russell', 'Shih Tzu', 'Miniature Dachshund']),
    ('M', 'Medium', 10, 25, ARRAY['Cocker Spaniel', 'Border Collie', 'Beagle']),
    ('L', 'Large', 25, 40, ARRAY['Labrador', 'Golden Retriever', 'German Shepherd']),
    ('XL', 'Extra Large', 40, 55, ARRAY['Rottweiler', 'Doberman', 'Boxer']),
    ('G', 'Giant', 55, NULL, ARRAY['Great Dane', 'St Bernard', 'Irish Wolfhound']);

-- Normalized boarding prices
CREATE TABLE boarding_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
    extraction_run_id UUID REFERENCES extraction_runs(id) ON DELETE SET NULL,

    -- Price details
    size_band_id UUID REFERENCES dog_size_bands(id),
    accommodation_tier TEXT,  -- 'standard', 'deluxe', 'luxury', etc.

    price_per_night DECIMAL(10, 2),
    price_includes_vat BOOLEAN DEFAULT true,

    -- Pricing unit
    unit TEXT DEFAULT 'per_night',  -- 'per_night', 'per_day', 'per_week'

    -- Validity
    season TEXT,  -- 'standard', 'peak', 'christmas', etc.
    valid_from DATE,
    valid_to DATE,

    -- Raw data for audit
    raw_service_name TEXT,
    raw_price_text TEXT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_boarding_prices_business ON boarding_prices(business_id);
CREATE INDEX idx_boarding_prices_size ON boarding_prices(size_band_id);

-- Additional services (walks, grooming add-ons, etc.)
CREATE TABLE additional_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
    extraction_run_id UUID REFERENCES extraction_runs(id) ON DELETE SET NULL,

    service_name TEXT NOT NULL,
    service_category TEXT,  -- 'walk', 'grooming', 'transport', 'medication', etc.

    price DECIMAL(10, 2),
    price_includes_vat BOOLEAN DEFAULT true,
    unit TEXT,  -- 'per_walk', 'per_session', 'per_day', etc.

    description TEXT,

    raw_price_text TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_additional_services_business ON additional_services(business_id);

-- Price modifiers (discounts, surcharges)
CREATE TABLE price_modifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
    extraction_run_id UUID REFERENCES extraction_runs(id) ON DELETE SET NULL,

    modifier_type TEXT NOT NULL,  -- 'discount', 'surcharge'
    trigger_condition TEXT NOT NULL,  -- 'multi_dog', 'long_stay', 'christmas', 'bank_holiday'

    modifier_value DECIMAL(10, 2),  -- Absolute amount
    modifier_percent DECIMAL(5, 2),  -- Percentage (use one or the other)

    description TEXT,
    raw_text TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_price_modifiers_business ON price_modifiers(business_id);

-- Vaccination requirements
CREATE TABLE vaccination_requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
    extraction_run_id UUID REFERENCES extraction_runs(id) ON DELETE SET NULL,

    vaccine_name TEXT NOT NULL,
    is_required BOOLEAN DEFAULT true,
    validity_period TEXT,  -- 'within 12 months', 'annual', etc.
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_vaccination_reqs_business ON vaccination_requirements(business_id);

-- Business policies
CREATE TABLE business_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
    extraction_run_id UUID REFERENCES extraction_runs(id) ON DELETE SET NULL,

    policy_type TEXT NOT NULL,  -- 'cancellation', 'deposit', 'drop_off', 'pick_up'
    policy_text TEXT NOT NULL,

    -- Structured cancellation details (if applicable)
    cancellation_notice_hours INTEGER,
    cancellation_fee_percent DECIMAL(5, 2),
    deposit_percent DECIMAL(5, 2),
    deposit_amount DECIMAL(10, 2),

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_business_policies_business ON business_policies(business_id);

-- -----------------------------------------------------------------------------
-- RETENTION MANAGEMENT
-- -----------------------------------------------------------------------------

-- Function to clean up expired crawls (run via cron job)
CREATE OR REPLACE FUNCTION cleanup_expired_crawls()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete crawls older than 18 months
    DELETE FROM site_crawls
    WHERE expires_at < now();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate next crawl due date (6 months from last crawl)
CREATE OR REPLACE FUNCTION update_next_crawl_due()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' THEN
        UPDATE businesses
        SET
            last_crawled_at = NEW.completed_at,
            next_crawl_due = NEW.completed_at + INTERVAL '6 months',
            crawl_count = crawl_count + 1
        WHERE id = NEW.business_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_crawl_schedule
    AFTER UPDATE OF status ON site_crawls
    FOR EACH ROW
    WHEN (NEW.status = 'completed')
    EXECUTE FUNCTION update_next_crawl_due();

-- -----------------------------------------------------------------------------
-- USEFUL VIEWS
-- -----------------------------------------------------------------------------

-- Businesses due for re-crawl
CREATE VIEW businesses_due_for_crawl AS
SELECT
    b.id,
    b.name,
    b.business_type,
    b.primary_url,
    b.last_crawled_at,
    b.next_crawl_due,
    b.crawl_count,
    b.last_extraction_quality_score
FROM businesses b
WHERE b.is_active = true
  AND (b.next_crawl_due IS NULL OR b.next_crawl_due <= now());

-- Latest crawl for each business
CREATE VIEW latest_crawls AS
SELECT DISTINCT ON (business_id)
    sc.*,
    b.name as business_name,
    b.business_type
FROM site_crawls sc
JOIN businesses b ON sc.business_id = b.id
WHERE sc.status = 'completed'
ORDER BY business_id, sc.completed_at DESC;

-- Page type distribution across all crawls
CREATE VIEW page_type_stats AS
SELECT
    page_type,
    COUNT(*) as page_count,
    AVG(relevance_score) as avg_relevance,
    AVG(word_count) as avg_word_count
FROM page_captures
GROUP BY page_type
ORDER BY page_count DESC;
"""
