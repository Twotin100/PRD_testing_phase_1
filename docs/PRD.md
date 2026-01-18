# Product Requirements Document
# Pet Care Data Extraction - Proof of Concept Testing

**Document Version:** 1.0  
**Date:** January 2025  
**Author:** Steve  
**Status:** Ready for Execution

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Background & Context](#2-background--context)
3. [Objectives](#3-objectives)
4. [Scope](#4-scope)
5. [Test Methodology](#5-test-methodology)
6. [Test Cases & Sample Selection](#6-test-cases--sample-selection)
7. [Success Criteria](#7-success-criteria)
8. [Execution Plan](#8-execution-plan)
9. [Data Collection & Analysis](#9-data-collection--analysis)
10. [Risk Assessment](#10-risk-assessment)
11. [Decision Framework](#11-decision-framework)
12. [Resource Requirements](#12-resource-requirements)
13. [Appendices](#13-appendices)

---

## 1. Executive Summary

### Purpose
This document defines the proof-of-concept (POC) testing phase for the Pet Care Business Data Platform. The POC will validate our data extraction approach on a small sample of real websites before committing resources to the full 3,000-site extraction.

### Key Questions to Answer
1. Can Firecrawl reliably extract structured data from diverse pet care websites?
2. Does our two-pass extraction strategy (capture + extract) work effectively?
3. Can we extract pricing data with sufficient accuracy despite format diversity?
4. Do business-type-specific schemas improve extraction quality?
5. What is the realistic success rate we can expect at scale?

### Investment
- **Time:** 2-3 days
- **Cost:** ~$10-15 (Firecrawl API credits)
- **URLs Tested:** 40 websites across 6 business types

### Go/No-Go Decision
Testing results will determine whether to proceed with full implementation, refine the approach, or pivot to alternative methods.

---

## 2. Background & Context

### Project Overview
We are building a comprehensive data platform to extract and organize information from approximately 3,000 pet care business websites across the UK. The platform must capture both:

- **Structured data** (pricing, services, hours, contact information) for comparable queries
- **Unstructured data** (policies, vaccination requirements, procedures) for semantic search

### The Core Challenge
Pet care website pricing is extraordinarily diverse:

| Business Type | Pricing Complexity | Example Variations |
|--------------|-------------------|-------------------|
| Dog Kennels | Medium | Per-night rates, size tiers, multi-dog discounts, holiday surcharges |
| Catteries | Medium | Per-night rates, multi-cat discounts, pen type variations |
| Dog Groomers | High | Breed-specific, coat-type, size-based, add-on services |
| Dog Daycare | Medium-High | Full/half day, packages, memberships, trial sessions |
| Dog Sitters | Low-Medium | Per-walk, per-visit, overnight, geographic variations |
| Veterinary Clinics | Very High | Procedures, diagnostics, consultations, packages, emergency fees |

### Previous Approach Limitations
Initial attempts at extraction struggled because:
- Single generic schema couldn't capture business-type variations
- Pricing formats vary wildly (tables, prose, PDFs, hidden tabs)
- Qualitative data (policies) mixed with quantitative data (prices)

### Proposed Solution
A two-pass extraction strategy:
1. **Pass 1:** Capture raw content (markdown, HTML) for storage and reprocessing
2. **Pass 2:** Extract structured data using business-type-specific Pydantic schemas

This POC will validate whether this approach works in practice.

---

## 3. Objectives

### Primary Objectives

| ID | Objective | Measurement |
|----|-----------|-------------|
| O1 | Validate Firecrawl can capture complete page content | Markdown/HTML length, content completeness |
| O2 | Validate structured extraction works with schemas | JSON extraction success rate |
| O3 | Measure pricing extraction accuracy | Prices found vs prices on actual website |
| O4 | Compare schema-based vs prompt-only extraction | Quality scores for each method |
| O5 | Identify business types requiring special handling | Per-type success rates |

### Secondary Objectives

| ID | Objective | Measurement |
|----|-----------|-------------|
| O6 | Estimate realistic costs for full extraction | Credits used per URL by type |
| O7 | Identify common failure patterns | Categorized error analysis |
| O8 | Validate quality scoring methodology | Correlation with manual assessment |
| O9 | Test fallback strategies | Success rate of prompt-only fallback |

---

## 4. Scope

### In Scope

| Item | Description |
|------|-------------|
| URL Testing | 40 real pet care business websites |
| Business Types | Dog kennels, catteries, dog groomers, veterinary clinics, dog daycare, dog sitters |
| Extraction Methods | Two-pass extraction, schema-based, prompt-only fallback |
| Data Types | Structured (pricing, contact) and unstructured (policies) |
| Quality Analysis | Automated scoring plus manual verification |
| Geographic Focus | UK websites (.co.uk) |

### Out of Scope

| Item | Rationale |
|------|-----------|
| Database storage | Testing extraction only, not persistence |
| Vector embeddings | Will test separately after extraction validated |
| Full 3,000 URL processing | Dependent on POC success |
| API development | Post-extraction phase |
| Multi-page crawling | Testing single-page extraction first |
| PDF extraction | Separate test if needed based on findings |

### Constraints

- **Budget:** Maximum $20 in API credits
- **Timeline:** Complete within 1 week
- **URLs:** Must be real, active pet care businesses
- **Manual verification:** Limited to 20 URLs (50% sample)

---

## 5. Test Methodology

### 5.1 Extraction Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TEST EXECUTION FLOW                          │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │  Input URL   │
    │  + Bus Type  │
    └──────┬───────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────────────┐
    │  PASS 1: CONTENT CAPTURE                                      │
    │  ┌────────────────────────────────────────────────────────┐  │
    │  │  Firecrawl scrape with formats=['markdown', 'html']    │  │
    │  │  • waitFor: 3000ms (JS rendering)                      │  │
    │  │  • onlyMainContent: false (capture everything)         │  │
    │  │  • timeout: 60000ms                                    │  │
    │  └────────────────────────────────────────────────────────┘  │
    │                           │                                   │
    │                           ▼                                   │
    │  Output: markdown_content, html_content, metadata             │
    └──────────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────────────┐
    │  PASS 2: STRUCTURED EXTRACTION                                │
    │  ┌────────────────────────────────────────────────────────┐  │
    │  │  Firecrawl scrape with formats=[{type: 'json', ...}]   │  │
    │  │  • schema: BusinessTypeSchema.model_json_schema()      │  │
    │  │  • prompt: Business-type-specific extraction prompt    │  │
    │  │  • timeout: 120000ms                                   │  │
    │  └────────────────────────────────────────────────────────┘  │
    │                           │                                   │
    │              ┌────────────┴────────────┐                     │
    │              ▼                          ▼                     │
    │         Success                     Failure                   │
    │              │                          │                     │
    │              │                          ▼                     │
    │              │            ┌──────────────────────────────┐   │
    │              │            │  FALLBACK: Prompt-only       │   │
    │              │            │  extraction without schema   │   │
    │              │            └──────────────────────────────┘   │
    │              │                          │                     │
    │              └──────────────┬───────────┘                     │
    │                             ▼                                 │
    │  Output: structured_data (JSON)                               │
    └──────────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────────────┐
    │  QUALITY ANALYSIS                                             │
    │  • Calculate automated quality score                          │
    │  • Save all outputs to files                                  │
    │  • Log metrics and errors                                     │
    └──────────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────────────┐
    │  MANUAL VERIFICATION (50% sample)                             │
    │  • Compare extracted data to actual website                   │
    │  • Record accuracy metrics                                    │
    │  • Identify failure patterns                                  │
    └──────────────────────────────────────────────────────────────┘
```

### 5.2 Test Types

#### Test Type A: Basic Capture Validation
**Purpose:** Confirm Firecrawl returns usable raw content
**Method:** Pass 1 only
**Metrics:**
- Markdown length (expect >1,000 chars for real content)
- HTML length (expect >5,000 chars)
- Metadata extraction (title, description)

#### Test Type B: Schema Extraction Validation
**Purpose:** Test structured extraction with Pydantic schemas
**Method:** Pass 2 with schema + prompt
**Metrics:**
- Extraction success (no errors)
- Fields populated vs expected
- Price count and accuracy

#### Test Type C: Prompt-Only Extraction
**Purpose:** Test fallback extraction method
**Method:** JSON extraction with prompt only (no schema)
**Metrics:**
- Extraction success rate
- Data structure consistency
- Comparison to schema-based results

#### Test Type D: Cross-Business-Type Comparison
**Purpose:** Identify which business types need special handling
**Method:** Run all tests, compare by type
**Metrics:**
- Per-type success rates
- Per-type quality scores
- Per-type pricing accuracy

### 5.3 Quality Scoring Algorithm

```
Quality Score (0-100) = Sum of:

┌─────────────────────────────────────────────────────────────────┐
│ Component                    │ Points │ Criteria                │
├─────────────────────────────────────────────────────────────────┤
│ Extraction succeeds          │   20   │ No errors thrown        │
│ Business name found          │   10   │ Non-empty string        │
│ Contact info found           │   10   │ Email OR phone OR addr  │
│ Has pricing data             │   30   │ At least 1 price found  │
│ Multiple prices (bonus)      │  +2/ea │ Max 20 bonus points     │
│ Vaccination info found       │    5   │ Any vaccination data    │
│ Policy info found            │    5   │ Cancellation OR deposit │
├─────────────────────────────────────────────────────────────────┤
│ Maximum possible             │  100   │                         │
└─────────────────────────────────────────────────────────────────┘
```

### 5.4 Manual Verification Protocol

For 50% of tested URLs (20 sites), perform manual verification:

1. **Open the actual website** in a browser
2. **Record ground truth data:**
   - Exact business name
   - All services with exact prices
   - Contact information
   - Vaccination requirements
   - Key policies
3. **Compare to extracted data:**
   - Name match (exact or close)
   - Price accuracy (within 10%)
   - Field completeness
4. **Document discrepancies:**
   - What was missed?
   - What was incorrect?
   - Why might it have failed?

---

## 6. Test Cases & Sample Selection

### 6.1 Sample Size by Business Type

| Business Type | Sample Size | Rationale |
|--------------|-------------|-----------|
| Dog Kennels | 6 | Medium complexity, common format |
| Catteries | 5 | Similar to kennels, verify transferability |
| Dog Groomers | 8 | Highest pricing complexity, most variations |
| Veterinary Clinics | 10 | Highest value data, most complex structure |
| Dog Daycare | 6 | Package pricing complexity |
| Dog Sitters | 5 | Simplest structure, baseline comparison |
| **Total** | **40** | |

### 6.2 Sample Selection Criteria

Each business type sample should include:

| Criterion | Count | Purpose |
|-----------|-------|---------|
| Professional website with clear pricing | 2-3 | Best-case scenario |
| Basic website with some pricing | 2-3 | Typical scenario |
| Complex pricing (tables, tiers) | 1-2 | Stress test |
| Prices in unusual format (prose, PDF link) | 1 | Edge case |

### 6.3 URL Selection Process

**Step 1: Search Queries**
```
For each business type, use Google:

Dog Kennels:
  "dog boarding kennels" "prices" site:.co.uk
  "dog kennels" "rates" "per night" site:.co.uk

Catteries:
  "cattery" "prices" site:.co.uk
  "cat boarding" "price list" site:.co.uk

Dog Groomers:
  "dog grooming" "prices" site:.co.uk
  "dog groomer" "price list" site:.co.uk

Veterinary Clinics:
  "veterinary" "fees" site:.co.uk
  "vets" "price list" site:.co.uk

Dog Daycare:
  "dog daycare" "prices" site:.co.uk
  "doggy daycare" "rates" site:.co.uk

Dog Sitters:
  "dog walking" "prices" site:.co.uk
  "dog sitter" "rates" site:.co.uk
```

**Step 2: Validation Checklist**
Before adding a URL to the test set:
- [ ] Is it a real business website (not a directory)?
- [ ] Does it have pricing information visible?
- [ ] Is it currently active and accessible?
- [ ] Is it based in the UK?
- [ ] Does it represent the intended complexity tier?

**Step 3: Documentation**
For each selected URL, record:
- URL
- Business type
- Expected complexity (easy/medium/hard)
- Notable features (PDF prices, tabbed content, etc.)

### 6.4 Test Case Definitions

#### TC-001: Dog Kennel - Standard Price Table
**URL Type:** Professional site with clear pricing table
**Expected Outcome:** 
- Business name extracted correctly
- All accommodation types with prices
- Multi-dog discounts if present
- Vaccination requirements

#### TC-002: Dog Kennel - Prose Pricing
**URL Type:** Basic site with prices in paragraph text
**Expected Outcome:**
- Prices extracted from prose
- May have lower accuracy than tables
- Tests prompt effectiveness

#### TC-003: Dog Groomer - Breed-Specific Pricing
**URL Type:** Groomer with different prices per breed
**Expected Outcome:**
- Multiple price entries for same service
- Breed variations captured in structured format
- Tests schema flexibility

#### TC-004: Veterinary - Comprehensive Fee List
**URL Type:** Vet with detailed procedure pricing
**Expected Outcome:**
- Consultation fees extracted
- Vaccination prices extracted
- Procedure categories identified
- Tests handling of complex data

#### TC-005: Veterinary - Minimal Pricing
**URL Type:** Vet with "prices from" or "contact for quote"
**Expected Outcome:**
- Captures whatever pricing exists
- Correctly handles missing data
- Tests graceful degradation

[Additional test cases TC-006 through TC-040 would follow similar patterns]

---

## 7. Success Criteria

### 7.1 Primary Success Metrics

| Metric | Target | Minimum Acceptable | Measurement Method |
|--------|--------|-------------------|-------------------|
| Overall extraction success rate | >90% | >80% | Extractions without errors / Total |
| Quality score average | >65 | >50 | Mean of all quality scores |
| Pricing data found | >75% | >60% | URLs with ≥1 price / Total |
| Price accuracy (manual verified) | >80% | >65% | Correct prices / Expected prices |
| Business name accuracy | >95% | >85% | Correct names / Total |

### 7.2 Per-Business-Type Targets

| Business Type | Min Quality Score | Min Pricing Found |
|--------------|-------------------|-------------------|
| Dog Kennels | 60 | 70% |
| Catteries | 60 | 70% |
| Dog Groomers | 55 | 65% |
| Veterinary Clinics | 50 | 60% |
| Dog Daycare | 60 | 70% |
| Dog Sitters | 65 | 75% |

*Note: Veterinary and groomers have lower targets due to higher complexity*

### 7.3 Secondary Success Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Schema extraction success | >85% | Before fallback |
| Fallback success rate | >70% | When schema fails |
| Average extraction time | <30s | Per URL, both passes |
| Cost per URL | <$0.30 | Both passes combined |

### 7.4 Quality Gates

**Gate 1: Basic Functionality**
- [ ] Firecrawl API connects successfully
- [ ] At least one URL extracts without errors
- [ ] Output files are created correctly

**Gate 2: Content Capture**
- [ ] Markdown content is meaningful (not just navigation)
- [ ] HTML content is complete
- [ ] Metadata is extracted

**Gate 3: Structured Extraction**
- [ ] JSON extraction returns valid data
- [ ] Schema-based extraction works for ≥80% of URLs
- [ ] Fallback handles schema failures

**Gate 4: Data Quality**
- [ ] Average quality score ≥50
- [ ] Pricing found in ≥60% of URLs
- [ ] Manual verification shows ≥65% accuracy

---

## 8. Execution Plan

### 8.1 Timeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ DAY 1: Setup & Initial Testing                                      │
├─────────────────────────────────────────────────────────────────────┤
│ Morning (2-3 hours)                                                 │
│ • Set up environment and dependencies                               │
│ • Verify Firecrawl API key works                                   │
│ • Run quick_test.py on 2-3 URLs to validate setup                  │
│                                                                     │
│ Afternoon (3-4 hours)                                               │
│ • Find and document 40 test URLs                                    │
│ • Categorize by business type and complexity                        │
│ • Add URLs to sample_urls.py                                        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ DAY 2: Full Test Execution                                          │
├─────────────────────────────────────────────────────────────────────┤
│ Morning (3-4 hours)                                                 │
│ • Run test_extraction.py for all business types                     │
│ • Monitor for errors, note any issues                               │
│ • Estimated runtime: 40 URLs × ~45s = ~30 minutes                  │
│                                                                     │
│ Afternoon (3-4 hours)                                               │
│ • Review automated quality scores                                   │
│ • Identify URLs for manual verification                             │
│ • Create ground_truth.json template                                 │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ DAY 3: Manual Verification & Analysis                               │
├─────────────────────────────────────────────────────────────────────┤
│ Morning (3-4 hours)                                                 │
│ • Manual verification of 20 URLs                                    │
│ • Fill in ground_truth.json with actual website data               │
│ • Document failure patterns                                         │
│                                                                     │
│ Afternoon (2-3 hours)                                               │
│ • Run analyze_results.py                                            │
│ • Compile findings and recommendations                              │
│ • Make go/no-go decision                                            │
│ • Document next steps                                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.2 Execution Steps

#### Phase 1: Environment Setup

```bash
# Step 1: Create project directory
mkdir pet-care-extraction-poc
cd pet-care-extraction-poc

# Step 2: Install dependencies
pip install firecrawl-py pydantic rich

# Step 3: Set API key
export FIRECRAWL_API_KEY="fc-your-key-here"

# Step 4: Copy test scripts
# (Copy quick_test.py, test_extraction.py, sample_urls.py, analyze_results.py)

# Step 5: Validate setup
python quick_test.py "https://any-test-url.co.uk" dog_kennel
```

#### Phase 2: URL Collection

1. Open `sample_urls.py`
2. For each business type:
   - Run Google searches (see Section 6.3)
   - Open candidate websites in browser
   - Verify they have pricing information
   - Add URL to the appropriate list
   - Note complexity rating

3. Validate final list:
   - 40 total URLs
   - At least 5 per business type
   - Mix of complexity levels

#### Phase 3: Test Execution

```bash
# Run all tests (recommended approach)
python test_extraction.py 2>&1 | tee test_output.log

# Or run by business type for easier monitoring
python test_extraction.py --type dog_kennel
python test_extraction.py --type cattery
python test_extraction.py --type dog_groomer
python test_extraction.py --type veterinary_clinic
python test_extraction.py --type dog_daycare
python test_extraction.py --type dog_sitter
```

#### Phase 4: Manual Verification

1. Select 20 URLs for manual verification:
   - Include highest and lowest quality scores
   - Include at least 3 per business type
   - Prioritize URLs with pricing data found

2. For each URL:
   - Open website in browser
   - Document actual data in ground_truth.json
   - Note any extraction issues

```bash
# Create template
python analyze_results.py extraction_results/ --create-template

# After filling in ground_truth.json
python analyze_results.py extraction_results/
```

#### Phase 5: Analysis & Decision

1. Review automated metrics:
   - Overall success rate
   - Per-type quality scores
   - Pricing extraction rates

2. Review manual verification:
   - Price accuracy
   - Common failure patterns
   - Business types needing work

3. Make go/no-go decision (see Section 11)

---

## 9. Data Collection & Analysis

### 9.1 Automated Data Collection

For each URL, the test suite collects:

| Data Point | Source | Storage |
|------------|--------|---------|
| URL | Input | Metrics JSON |
| Business type | Input | Metrics JSON |
| Extraction success (bool) | Pass 2 result | Metrics JSON |
| Quality score | Calculated | Metrics JSON |
| Markdown length | Pass 1 | Metrics JSON |
| HTML length | Pass 1 | Metrics JSON |
| Business name found | Pass 2 JSON | Metrics JSON |
| Contact info found | Pass 2 JSON | Metrics JSON |
| Price count | Pass 2 JSON | Metrics JSON |
| Has vaccination info | Pass 2 JSON | Metrics JSON |
| Has policies | Pass 2 JSON | Metrics JSON |
| Extraction time (seconds) | Measured | Metrics JSON |
| Error message (if any) | Exception | Metrics JSON |
| Full markdown | Pass 1 | Separate .md file |
| Extracted JSON | Pass 2 | Separate .json file |

### 9.2 Manual Verification Data

For each manually verified URL, record in ground_truth.json:

```json
{
  "url": "https://example-kennels.co.uk",
  "business_type": "dog_kennel",
  "business_name": "Example Kennels Ltd",
  "phone": "01onal 234 5678",
  "email": "info@example-kennels.co.uk",
  "address": "123 Farm Road, Somewhere, AB1 2CD",
  "services": [
    {
      "service_name": "Standard Kennel",
      "price": 25.00,
      "unit": "per_night"
    },
    {
      "service_name": "Deluxe Suite", 
      "price": 35.00,
      "unit": "per_night"
    },
    {
      "service_name": "Second dog (same kennel)",
      "price": 20.00,
      "unit": "per_night"
    }
  ],
  "vaccination_requirements": [
    "Distemper",
    "Parvovirus",
    "Kennel Cough (within 12 months)"
  ],
  "verification_notes": "Prices clearly displayed in table on Prices page"
}
```

### 9.3 Analysis Outputs

#### Output 1: Summary Report

```
EXTRACTION TEST SUMMARY
=======================

Overall Metrics:
  Total URLs tested: 40
  Successful extractions: 37 (92.5%)
  Average quality score: 68.4
  URLs with pricing found: 31 (77.5%)

By Business Type:
  ┌──────────────────┬────────┬─────────┬───────────┬────────────┐
  │ Type             │ Tested │ Success │ Avg Score │ Has Prices │
  ├──────────────────┼────────┼─────────┼───────────┼────────────┤
  │ dog_kennel       │      6 │     6/6 │      72.3 │        83% │
  │ cattery          │      5 │     5/5 │      69.8 │        80% │
  │ dog_groomer      │      8 │     7/8 │      61.2 │        75% │
  │ veterinary_clinic│     10 │     9/10│      58.6 │        60% │
  │ dog_daycare      │      6 │     6/6 │      71.5 │        83% │
  │ dog_sitter       │      5 │     4/5 │      74.2 │        80% │
  └──────────────────┴────────┴─────────┴───────────┴────────────┘
```

#### Output 2: Accuracy Analysis

```
EXTRACTION ACCURACY ANALYSIS
============================

Manual Verification Results (20 URLs):

  Name extraction accuracy: 95% (19/20)
  
  Price extraction:
    Expected prices: 156
    Prices found: 128
    Correct prices (within 10%): 112
    Price accuracy: 87.5%
  
  Field coverage: 78%
  
  Overall accuracy score: 81%
```

#### Output 3: Failure Pattern Analysis

```
FAILURE PATTERN ANALYSIS
========================

Common Issues Identified:

1. Prices in PDF only (3 URLs)
   - Solution: Add PDF link detection and extraction

2. Prices behind accordion/tabs (2 URLs)
   - Solution: Add browser actions to click elements

3. "Contact for pricing" (2 URLs)
   - Solution: Accept as valid "no pricing" result

4. Complex breed pricing tables (2 URLs)
   - Solution: Refine groomer schema and prompt

5. JavaScript-loaded content (1 URL)
   - Solution: Increase waitFor timeout
```

### 9.4 Data Storage Structure

```
extraction_results/
├── dog_kennel_examplekennels_20250115_143022_markdown.md
├── dog_kennel_examplekennels_20250115_143022_extracted.json
├── dog_kennel_examplekennels_20250115_143022_metrics.json
├── dog_kennel_happypaws_20250115_143145_markdown.md
├── dog_kennel_happypaws_20250115_143145_extracted.json
├── dog_kennel_happypaws_20250115_143145_metrics.json
├── ... (additional results)
├── ground_truth.json
├── summary_report.txt
└── failure_analysis.txt
```

---

## 10. Risk Assessment

### 10.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Firecrawl API rate limiting | Medium | Medium | Implement delays between requests |
| Websites block scraping | Low | Low | Use Firecrawl's built-in proxy rotation |
| Schema extraction fails frequently | Medium | High | Fallback to prompt-only extraction |
| Pricing formats too diverse | High | High | Accept lower accuracy for complex types |
| JavaScript content not loading | Medium | Medium | Increase waitFor timeout |
| Test websites change during testing | Low | Low | Complete testing in short timeframe |

### 10.2 Process Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Insufficient test URLs found | Low | Medium | Start URL collection early |
| Manual verification takes too long | Medium | Medium | Limit to 20 URLs, use template |
| Results inconclusive | Medium | High | Define clear decision thresholds |
| Bias in URL selection | Medium | Medium | Follow selection criteria strictly |

### 10.3 Cost Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Higher than expected API costs | Low | Low | Monitor usage, stop if exceeding $20 |
| Retries increase costs | Medium | Low | Limit retries to 2 per URL |

---

## 11. Decision Framework

### 11.1 Decision Matrix

Based on test results, choose one of four paths:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DECISION MATRIX                              │
└─────────────────────────────────────────────────────────────────────┘

                        Quality Score Average
                    │  <50    │  50-65  │   >65   │
    ────────────────┼─────────┼─────────┼─────────┤
    Pricing   <60%  │  STOP   │ REFINE  │ REFINE  │
    Found     ────────────────┼─────────┼─────────┤
              60-75%│ REFINE  │ PROCEED*│ PROCEED │
              ────────────────┼─────────┼─────────┤
              >75%  │ REFINE  │ PROCEED │ PROCEED │
    
    * PROCEED with caution, monitor closely during scale-up
```

### 11.2 Decision Paths

#### Path A: PROCEED
**Criteria:** Quality ≥65, Pricing ≥60%
**Actions:**
1. Document successful approach
2. Scale to 100-URL validation batch
3. Build full infrastructure (Supabase, storage)
4. Begin production extraction

#### Path B: PROCEED WITH CAUTION
**Criteria:** Quality 50-65, Pricing 60-75%
**Actions:**
1. Identify weakest business types
2. Refine schemas/prompts for problem areas
3. Run additional 20-URL test on refined approach
4. If improved, proceed to Path A
5. If not improved, move to Path C

#### Path C: REFINE
**Criteria:** Quality 50-65 with Pricing <60%, OR Quality <50
**Actions:**
1. Analyze failure patterns in detail
2. Consider alternative approaches:
   - Use `/extract` endpoint for multi-page sites
   - Use `/agent` for complex veterinary sites
   - Add browser actions for interactive content
   - Implement PDF extraction
3. Create refined test with 20 new URLs
4. Re-evaluate against same criteria

#### Path D: STOP / PIVOT
**Criteria:** Quality <50 AND Pricing <60% after refinement
**Actions:**
1. Document limitations of automated extraction
2. Consider alternative approaches:
   - Manual data entry for high-value types (vets)
   - Hybrid approach (automated + manual QA)
   - Different extraction service
   - Reduced scope (fewer business types)
3. Re-scope project based on findings

### 11.3 Business Type Specific Decisions

Some business types may pass while others fail. In this case:

| Scenario | Decision |
|----------|----------|
| All types pass | PROCEED with full extraction |
| Vets fail, others pass | PROCEED with 5 types, use `/agent` for vets |
| Groomers fail, others pass | PROCEED with 5 types, refine groomer approach |
| Multiple types fail | REFINE overall approach |
| Most types fail | STOP / PIVOT |

---

## 12. Resource Requirements

### 12.1 Technical Resources

| Resource | Specification | Purpose |
|----------|--------------|---------|
| Python 3.8+ | Local or cloud | Run test scripts |
| Firecrawl API key | Free tier sufficient | Web scraping |
| Internet connection | Stable | Access test URLs |
| Text editor | Any | Review output files |
| Web browser | Chrome/Firefox | Manual verification |
| ~50MB disk space | Local | Store test outputs |

### 12.2 API Credits

| Item | Estimated Cost |
|------|---------------|
| Pass 1 captures (40 URLs) | ~$4-6 |
| Pass 2 extractions (40 URLs) | ~$4-6 |
| Retries and failures | ~$2 |
| Buffer | ~$3 |
| **Total** | **~$13-17** |

### 12.3 Time Investment

| Activity | Estimated Time |
|----------|---------------|
| Environment setup | 30 minutes |
| URL collection | 2-3 hours |
| Test execution | 1 hour |
| Monitoring/troubleshooting | 1-2 hours |
| Manual verification | 3-4 hours |
| Analysis and documentation | 2-3 hours |
| **Total** | **10-14 hours** |

---

## 13. Appendices

### Appendix A: Test Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `quick_test.py` | Single URL validation | `python quick_test.py <url> <type>` |
| `test_extraction.py` | Full test suite | `python test_extraction.py [--type TYPE]` |
| `sample_urls.py` | URL configuration | Edit to add test URLs |
| `analyze_results.py` | Results analysis | `python analyze_results.py <dir>` |

### Appendix B: Schema Reference

The test uses a simplified `BusinessExtraction` schema that works across all types:

```python
class BusinessExtraction(BaseModel):
    business_name: Optional[str]
    business_type: Optional[str]
    description: Optional[str]
    contact: Optional[ContactInfo]
    services: List[ServicePrice]
    vaccination_requirements: List[VaccinationReq]
    drop_off_procedure: Optional[str]
    pick_up_procedure: Optional[str]
    cancellation_policy: Optional[str]
    deposit_policy: Optional[str]
    amenities: List[str]
    opening_hours: Optional[str]
```

Full business-type-specific schemas are defined in the main approach document and will be used in production.

### Appendix C: Extraction Prompts

See `test_extraction.py` for the `EXTRACTION_PROMPTS` dictionary containing business-type-specific prompts.

### Appendix D: Ground Truth Template

```json
{
  "_instructions": "Fill in expected values by checking actual websites",
  "urls": [
    {
      "url": "https://example.co.uk",
      "business_type": "dog_kennel",
      "business_name": "",
      "phone": "",
      "email": "",
      "services": [
        {"service_name": "", "price": 0.00, "unit": ""}
      ],
      "vaccination_requirements": [],
      "_source_file": "dog_kennel_example_..._extracted.json"
    }
  ]
}
```

### Appendix E: Glossary

| Term | Definition |
|------|------------|
| Pass 1 | First extraction pass capturing raw markdown and HTML |
| Pass 2 | Second extraction pass generating structured JSON |
| Quality Score | Automated 0-100 score based on extraction completeness |
| Ground Truth | Manually verified data from actual websites |
| Schema | Pydantic model defining expected data structure |
| Fallback | Prompt-only extraction when schema-based fails |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Jan 2025 | Steve | Initial document |

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Project Owner | | | |
| Technical Lead | | | |

---

*End of Document*
