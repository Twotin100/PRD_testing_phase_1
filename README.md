# Pet Care Data Extraction POC

Data extraction proof-of-concept for UK pet care business pricing data, using the Firecrawl API for web scraping and LLM-based structured extraction.

## Overview

This project extracts structured pricing data from UK pet care business websites (kennels, catteries, groomers, vets, daycares, dog sitters) using a two-pass extraction strategy:

1. **Pass 1: Content Capture** - Scrape webpage as markdown/HTML
2. **Pass 2: Structured Extraction** - LLM extracts data into Pydantic schema

## Project Structure

```
PRD_testing_phase_1/
├── src/
│   ├── config.py              # Firecrawl API configuration
│   ├── schemas.py             # Pydantic extraction schemas
│   ├── sample_urls.py         # 40 test URLs by business type
│   ├── test_extraction.py     # Full extraction pipeline
│   ├── quick_test.py          # Single URL testing
│   ├── quality_scoring.py     # Extraction quality metrics
│   └── analyze_results.py     # Results analysis tools
├── extraction_results/        # Output JSON/markdown files
├── docs/
│   └── PRD.md                 # Product Requirements Document
├── .env                       # API keys (not in git)
└── requirements.txt
```

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API key in `.env`:
```
FIRECRAWL_API_KEY=your_api_key_here
```

## Usage

```bash
# Test single URL
python src/quick_test.py "https://example-kennels.co.uk/prices" dog_kennel

# Run full test suite (all 40 URLs)
python src/test_extraction.py

# Run specific business type
python src/test_extraction.py --type dog_kennel
```

---

# Extraction Results & Findings

## Test Run Summary (2026-01-18)

### Results Overview

| Metric | Value |
|--------|-------|
| URLs Attempted | 40 |
| Successful Extractions | 6 (dog kennels only) |
| Failure Reason | Firecrawl API credit limit reached |
| Dog Kennel Success Rate | 100% |
| Average Quality Score (kennels) | 87.5/100 |

### Successful Extractions

| Kennel | Quality Score | Prices Extracted | Key Features |
|--------|---------------|------------------|--------------|
| Harker's Barkers | 74 | 3 | Flat rate, overnight premium |
| Whitehouse Kennels | 100 | 14 | Multi-service, size tiers |
| Ivy Kennels | 84 | 3 | Multi-dog pricing |
| Honeybottom Kennels | 75 | 6 | Size-based, single night premium |
| Green Lane Farm | 100 | 15 | Standard/Luxury tiers, VAT separate |
| Meadowview Kennels | 92 | 7 | Sharing discounts |

### Key Finding: URL Freshness Issue

One extraction (Honeybottom) returned 2025 prices instead of 2026. The URL `/boarding-prices/` redirected to `/boarding-prices-2025/` instead of the current `/boarding-prices-2026/`.

**Lesson:** Pricing pages often have year-specific URLs. Extraction pipeline should either:
- Use explicit year URLs where available
- Validate extracted dates against current date
- Flag potential stale data

---

## Pricing Structure Analysis

### Variation Dimensions Identified

Analysis of 3 kennels revealed significant structural differences:

| Dimension | Harker's Barkers | Green Lane Farm | Honeybottom |
|-----------|------------------|-----------------|-------------|
| **Size Categories** | None (flat rate) | 5 (Toy → Extra-large) | 6 (Extra Small → Giant) |
| **Accommodation Tiers** | 1 | 2 (Standard/Luxury) | 1 |
| **VAT Handling** | Included | Separate (+20%) | Included |
| **Base Unit** | per_day | per_night | per_day |
| **Single Night Premium** | £35 vs £27 (+30%) | Not explicit | +£6 surcharge |
| **Seasonal Pricing** | Christmas surcharge | Peak season rates | Christmas double |

### Size Category Mapping Challenge

Different kennels use different terminology and granularity:

```
Harker's:     [-------- ALL DOGS --------]  (no differentiation)

Green Lane:   [Toy] [Small] [Medium] [Large] [X-Large]
                A      B       C        D        E

Honeybottom:  [X-Small] [Small] [Medium] [Large] [X-Large] [Giant]
              Chihuahua  Westie  Beagle   Lab    Shepherd  Dane
```

### Additional Pricing Factors Observed

1. **Multi-dog discounts** - 10% for dogs sharing (Honeybottom)
2. **Long-stay discounts** - 50p/night for 8+ days, £1/night for 1+ month
3. **Bank holiday supplements** - £12 surcharge (Green Lane)
4. **Additional services** - Walks, bathing, grooming (variable pricing)
5. **Deposit requirements** - 20% non-refundable (Harker's)

---

## Proposed Database Schema

### Design Principles

1. **Normalize to canonical categories** - Map varied terminology to standard bands
2. **Always store VAT-inclusive** - Enable fair comparison regardless of display format
3. **Preserve raw data** - Keep original text for audit/debugging
4. **Handle missing dimensions** - NULL means "applies to all" (e.g., flat-rate kennels)
5. **Time-validity tracking** - Support seasonal and annual price changes

### Canonical Size Bands

| Band | Code | Weight Range | Example Breeds |
|------|------|--------------|----------------|
| Toy/Extra Small | XS | 0-4 kg | Chihuahua, Pomeranian |
| Small | S | 4-10 kg | Westie, Jack Russell |
| Medium | M | 10-25 kg | Beagle, Cocker Spaniel |
| Large | L | 25-40 kg | Labrador, Dalmatian |
| Extra Large | XL | 40-55 kg | German Shepherd, Rottweiler |
| Giant | G | 55+ kg | Great Dane, Wolfhound |

### Schema Design

```sql
-- Canonical reference data
CREATE TABLE dog_size_bands (
    id SERIAL PRIMARY KEY,
    code VARCHAR(2) NOT NULL,        -- XS, S, M, L, XL, G
    name VARCHAR(20) NOT NULL,       -- "Extra Small", "Small", etc.
    weight_min_kg DECIMAL(5,2),
    weight_max_kg DECIMAL(5,2),
    example_breeds TEXT[]
);

-- Business information
CREATE TABLE businesses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    business_type VARCHAR(50) NOT NULL,  -- dog_kennel, cattery, etc.
    url VARCHAR(500),
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    vat_registered BOOLEAN DEFAULT true,
    extraction_date TIMESTAMP,
    data_valid_from DATE,
    data_valid_to DATE
);

-- Core pricing data (normalized)
CREATE TABLE boarding_prices (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    size_band_id INTEGER REFERENCES dog_size_bands(id),  -- NULL = all sizes
    accommodation_tier VARCHAR(20) DEFAULT 'standard',   -- standard, luxury, premium

    -- Pricing
    price_ex_vat DECIMAL(10,2),
    price_inc_vat DECIMAL(10,2) NOT NULL,
    currency CHAR(3) DEFAULT 'GBP',

    -- Unit & conditions
    unit VARCHAR(20) NOT NULL,           -- per_night, per_day, per_week
    min_nights INTEGER DEFAULT 1,        -- 1 = single night rate
    max_nights INTEGER,                  -- NULL = no limit

    -- Validity
    season VARCHAR(20) DEFAULT 'standard',  -- standard, peak, christmas
    valid_from DATE,
    valid_to DATE,

    -- Original extracted data (for audit)
    raw_service_name TEXT,
    raw_price_text TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Map business-specific terminology to canonical sizes
CREATE TABLE size_band_mappings (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    raw_size_name VARCHAR(100),          -- "Category A", "Extra Small Dog"
    canonical_size_id INTEGER REFERENCES dog_size_bands(id),
    breed_examples TEXT[],
    confidence DECIMAL(3,2)              -- Mapping confidence score
);

-- Additional services (walks, grooming, etc.)
CREATE TABLE additional_services (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    service_name VARCHAR(100) NOT NULL,
    service_category VARCHAR(50),        -- walking, grooming, transport
    size_band_id INTEGER REFERENCES dog_size_bands(id),
    price_inc_vat DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20),                    -- per_session, per_hour, per_dog
    duration_minutes INTEGER,
    raw_service_name TEXT,
    raw_price_text TEXT
);

-- Surcharges and discounts
CREATE TABLE price_modifiers (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    modifier_type VARCHAR(20),           -- surcharge, discount
    trigger_condition VARCHAR(100),      -- 'christmas', 'multi_dog', 'long_stay'
    modifier_value DECIMAL(10,2),        -- Absolute amount
    modifier_percent DECIMAL(5,2),       -- Percentage (alternative)
    description TEXT
);
```

### Example Comparison Query

```sql
-- Compare standard boarding for medium dogs across all kennels
SELECT
    b.name AS kennel,
    COALESCE(dsb.name, 'All sizes') AS size_category,
    bp.price_inc_vat AS price_gbp,
    bp.unit,
    CASE bp.min_nights WHEN 1 THEN 'single night' ELSE 'multi-night' END AS rate_type,
    bp.accommodation_tier
FROM boarding_prices bp
JOIN businesses b ON bp.business_id = b.id
LEFT JOIN dog_size_bands dsb ON bp.size_band_id = dsb.id
WHERE (dsb.code = 'M' OR bp.size_band_id IS NULL)  -- Medium or flat-rate
  AND bp.accommodation_tier = 'standard'
  AND bp.season = 'standard'
  AND bp.min_nights > 1  -- Multi-night for fair comparison
ORDER BY bp.price_inc_vat;
```

**Expected Result:**
| Kennel | Size | Price | Unit | Rate Type |
|--------|------|-------|------|-----------|
| Honeybottom | Medium | £25.50 | per_day | multi-night |
| Harker's Barkers | All sizes | £27.00 | per_day | multi-night |
| Green Lane Farm | Medium | £32.40 | per_night | multi-night |

---

## Firecrawl API Credit Analysis

### Credit Usage Per URL (from Activity Logs)

Each URL requires two API calls:

| Operation | Credits | Purpose |
|-----------|---------|---------|
| `/scrape` | 1 | Capture page as markdown/HTML |
| `/extract` | 43-90 | LLM structured extraction |

**Extract credits vary by content complexity:**

| URL | Scrape | Extract | Total |
|-----|--------|---------|-------|
| harkersbarkers.co.uk | 1 | 43 | 44 |
| whitehouse-kennels.co.uk | 1 | 73 | 74 |
| ivykennels.co.uk | 1 | 52 | 53 |
| honeybottomkennels.co.uk | 1 | 50 | 51 |
| greenlanefarmboardingkennels.co.uk | 1 | 90 | 91 |
| meadowviewboardingkennels.co.uk | 1 | 62 | 63 |

**Average: ~63 credits per page**

### Full Site Extraction Scope

For comprehensive data extraction, we need to crawl **multiple pages per business**:

| Page Type | Data Extracted |
|-----------|----------------|
| **Pricing page** | Prices, rates, packages, size tiers |
| **Services/About** | Services offered, amenities, facilities |
| **Contact page** | Phone, email, address, location |
| **FAQ/Terms** | Vaccination requirements, cancellation policy, deposits |
| **Homepage** | Opening hours, overview, special offers |

**Estimated 4-5 pages per business**

### Credit Estimate for Full Extraction

| Scenario | Businesses | Pages/Business | Total Pages | Credits/Page | Total Credits |
|----------|------------|----------------|-------------|--------------|---------------|
| Minimum | 40 | 4 | 160 | 63 | **10,080** |
| Expected | 40 | 5 | 200 | 63 | **12,600** |
| With buffer | 40 | 5 | 200 | 75 | **15,000** |

### Firecrawl Plan Recommendation

| Plan | Credits/Month | Price | Fits Our Needs? |
|------|---------------|-------|-----------------|
| Free | 500 | £0 | ❌ Only ~8 pages |
| Hobby | 3,000 | £12 | ❌ Only ~48 pages |
| **Standard** | **100,000** | **£62** | ✅ **Recommended** |
| Growth | 500,000 | £249 | ❌ Overkill |

**Recommendation: Standard Plan (£62/month)**
- 100,000 credits provides 6x headroom over our estimate
- Allows for re-runs, testing, and schema iterations
- 50 concurrent requests enables faster crawling
- Room for expanding to more businesses

### Cost Optimization Strategies

1. **Crawl efficiently** - Use Firecrawl's `/crawl` endpoint to capture multiple pages in one call
2. **Cache markdown** - Store Pass 1 results to avoid re-scraping
3. **Batch extractions** - Combine content from multiple pages before extraction
4. **Local LLM fallback** - Use local models for simpler extractions

---

## Multi-Page Extraction Strategy

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PER-BUSINESS EXTRACTION FLOW                  │
└─────────────────────────────────────────────────────────────────┘

  Business URL (e.g., greenlanefarm.co.uk)
           │
           ▼
  ┌─────────────────┐
  │  1. Site Crawl  │  Firecrawl /crawl endpoint
  │  (5 pages max)  │  ~5 credits (scrape only)
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ 2. Page Filter  │  Identify pricing, contact, FAQ pages
  │                 │  by URL patterns and content
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ 3. Content Merge│  Combine relevant page content
  │                 │  into single extraction context
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ 4. Extract Once │  Single /extract call per business
  │                 │  ~60-90 credits
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  5. Normalize   │  Map to canonical schema
  │  & Store        │  Save to database with audit trail
  └─────────────────┘
```

### Data Storage for Audit Trail

All extracted data will be stored with full provenance:

```sql
-- Raw extraction audit table
CREATE TABLE extraction_runs (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    run_timestamp TIMESTAMP DEFAULT NOW(),
    firecrawl_scrape_ids TEXT[],          -- Array of scrape IDs
    pages_crawled TEXT[],                  -- URLs crawled
    raw_markdown TEXT,                     -- Combined markdown content
    raw_extraction JSONB,                  -- Raw LLM extraction output
    normalized_data JSONB,                 -- Post-processed normalized data
    credits_used INTEGER,
    extraction_duration_ms INTEGER,
    quality_score DECIMAL(5,2),
    error_message TEXT
);

-- Track individual page captures
CREATE TABLE page_captures (
    id SERIAL PRIMARY KEY,
    extraction_run_id INTEGER REFERENCES extraction_runs(id),
    url VARCHAR(500) NOT NULL,
    page_type VARCHAR(50),                 -- pricing, contact, faq, etc.
    scrape_id VARCHAR(100),
    markdown_content TEXT,
    html_content TEXT,
    metadata JSONB,
    captured_at TIMESTAMP DEFAULT NOW()
);
```

### Accuracy Validation

To ensure extraction accuracy:

1. **Manual spot-checks** - Randomly verify 10% of extractions against source
2. **Price range validation** - Flag outliers (e.g., £5/night or £500/night)
3. **Consistency checks** - Compare similar businesses in same region
4. **Temporal tracking** - Detect and flag significant price changes
5. **Source linking** - Every data point links back to source URL and capture timestamp

---

## Next Steps: Expanded Sampling

### Objective

Sample more businesses across all 6 types to identify additional pricing variations before finalizing the schema.

### Sampling Strategy

1. **Breadth over depth** - 2-3 URLs per business type (12-18 total)
2. **Complexity variety** - Include easy, medium, and hard complexity sites
3. **Multi-page crawling** - Test full site extraction on subset first

### Expected Additional Variations to Discover

| Business Type | Likely Pricing Variations |
|---------------|---------------------------|
| **Cattery** | Room size tiers, multi-cat discounts, feeding options |
| **Dog Groomer** | Breed-specific, coat type, service bundles |
| **Veterinary** | Consultation vs treatment, species, weight-based |
| **Dog Daycare** | Half-day vs full-day, packages, membership |
| **Dog Sitter** | Hourly vs daily, travel radius, overnight |

### Schema Evolution Plan

1. Complete expanded sampling across all business types
2. Document all new variations discovered
3. Update schema to accommodate edge cases
4. Build extraction post-processor to normalize data
5. Implement confidence scoring for ambiguous mappings
6. Deploy database with full audit trail capability

---

## Development

- Run tests: `pytest`
- Run linting: `ruff check .`
- Run type checking: `mypy src/`

## License

MIT
