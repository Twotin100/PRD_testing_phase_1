"""
Page classifier using a cheap LLM (Claude Haiku) to categorize crawled pages.

Classifies pages into types (pricing, contact, terms, etc.) and assigns
relevance scores for extraction priority.

Cost-optimized: ~$0.001 per page using Claude Haiku
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from crawl_config import get_anthropic_api_key, get_classifier_config
from crawl_schemas import CrawledPage, PageClassification, PageType


# Keyword patterns for rule-based pre-classification (free, fast)
URL_PATTERNS = {
    PageType.PRICING: [
        r"/pric", r"/rate", r"/fee", r"/cost", r"/tariff",
        r"/charge", r"/boarding-price", r"/grooming-price",
    ],
    PageType.CONTACT: [
        r"/contact", r"/location", r"/find-us", r"/directions",
        r"/where", r"/visit", r"/get-in-touch",
    ],
    PageType.ABOUT: [
        r"/about", r"/our-story", r"/who-we-are", r"/team",
        r"/history", r"/meet-the-team",
    ],
    PageType.SERVICES: [
        r"/service", r"/what-we-do", r"/our-service", r"/treatment",
        r"/grooming", r"/boarding", r"/daycare",
    ],
    PageType.TERMS: [
        r"/term", r"/condition", r"/polic", r"/t-and-c", r"/t&c",
        r"/cancellation", r"/booking-term",
    ],
    PageType.FAQ: [
        r"/faq", r"/question", r"/help", r"/info",
        r"/frequently-asked",
    ],
    PageType.BOOKING: [
        r"/book", r"/reserv", r"/appointment", r"/availability",
        r"/schedule",
    ],
    PageType.GALLERY: [
        r"/gallery", r"/photo", r"/image", r"/picture",
        r"/virtual-tour",
    ],
    PageType.BLOG: [
        r"/blog", r"/news", r"/article", r"/post",
        r"/update", r"/latest",
    ],
}

# Content patterns for relevance scoring
PRICING_SIGNALS = [
    r"£\d+", r"£ \d+", r"\d+\.\d{2}",  # Price patterns
    r"per night", r"per day", r"per hour", r"per session",
    r"from £", r"prices from", r"rates from",
    r"price list", r"our prices", r"our rates",
    r"small dog", r"medium dog", r"large dog",  # Size-based pricing
    r"full groom", r"bath and dry", r"nail trim",  # Grooming services
]

CONTACT_SIGNALS = [
    r"\b\d{5}\s?\d{6}\b",  # UK phone numbers
    r"\b0\d{2,4}\s?\d{6,7}\b",  # UK landlines
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email
    r"[A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2}",  # UK postcode
    r"opening hours", r"open mon", r"open daily",
]


def classify_by_url(url: str) -> Tuple[Optional[PageType], float]:
    """
    Quick classification based on URL patterns.
    Returns (page_type, confidence) or (None, 0) if no match.
    """
    path = urlparse(url).path.lower()

    # Check if it's the homepage
    if path in ("", "/", "/index", "/index.html", "/home"):
        return PageType.HOMEPAGE, 0.9

    # Check URL patterns
    for page_type, patterns in URL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return page_type, 0.8

    return None, 0.0


def count_content_signals(content: str, patterns: List[str]) -> int:
    """Count how many signal patterns match in the content."""
    count = 0
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        count += len(matches)
    return count


def analyze_content_signals(markdown: str) -> Dict[str, Any]:
    """
    Analyze content for pricing and contact signals.
    Returns signal counts and boolean flags.
    """
    pricing_count = count_content_signals(markdown, PRICING_SIGNALS)
    contact_count = count_content_signals(markdown, CONTACT_SIGNALS)

    return {
        "pricing_signal_count": pricing_count,
        "contact_signal_count": contact_count,
        "has_pricing_signals": pricing_count >= 2,
        "has_contact_signals": contact_count >= 2,
        "word_count": len(markdown.split()),
    }


def classify_with_rules(page: CrawledPage) -> PageClassification:
    """
    Rule-based classification (free, instant).
    Used as first pass before LLM classification.
    """
    # Try URL-based classification first
    url_type, url_confidence = classify_by_url(page.url)

    # Analyze content signals
    signals = analyze_content_signals(page.markdown)

    # Determine page type
    if url_type:
        page_type = url_type
        confidence = url_confidence
    elif signals["has_pricing_signals"] and signals["pricing_signal_count"] > 5:
        page_type = PageType.PRICING
        confidence = 0.7
    elif signals["has_contact_signals"] and signals["contact_signal_count"] > 3:
        page_type = PageType.CONTACT
        confidence = 0.6
    else:
        page_type = PageType.OTHER
        confidence = 0.3

    # Calculate relevance score
    relevance = calculate_relevance_score(page_type, signals)

    return PageClassification(
        page_type=page_type,
        confidence=confidence,
        reasoning=f"Rule-based: URL pattern + {signals['pricing_signal_count']} pricing signals, {signals['contact_signal_count']} contact signals",
        relevance_for_extraction=relevance,
    )


def calculate_relevance_score(page_type: PageType, signals: Dict[str, Any]) -> float:
    """
    Calculate how relevant a page is for extraction (0-1).
    Higher scores = more likely to contain useful data.
    """
    # Base relevance by page type
    base_relevance = {
        PageType.PRICING: 1.0,
        PageType.SERVICES: 0.9,
        PageType.CONTACT: 0.85,
        PageType.TERMS: 0.8,
        PageType.FAQ: 0.75,
        PageType.BOOKING: 0.7,
        PageType.ABOUT: 0.5,
        PageType.HOMEPAGE: 0.6,
        PageType.GALLERY: 0.1,
        PageType.BLOG: 0.1,
        PageType.OTHER: 0.3,
    }

    relevance = base_relevance.get(page_type, 0.3)

    # Boost for pricing signals (important for our use case)
    if signals.get("has_pricing_signals"):
        relevance = min(1.0, relevance + 0.2)

    # Boost for contact signals
    if signals.get("has_contact_signals"):
        relevance = min(1.0, relevance + 0.1)

    # Penalize very short pages
    word_count = signals.get("word_count", 0)
    if word_count < 100:
        relevance *= 0.5
    elif word_count < 300:
        relevance *= 0.8

    return round(relevance, 2)


def build_classification_prompt(pages: List[CrawledPage]) -> str:
    """Build a batch classification prompt for the LLM."""
    prompt = """You are classifying web pages from a pet care business website.
For each page, determine:
1. page_type: One of: pricing, contact, about, services, terms, faq, booking, gallery, blog, homepage, other
2. confidence: 0.0 to 1.0
3. relevance: 0.0 to 1.0 (how useful for extracting business info like prices, contact, policies)

Focus on:
- PRICING pages have prices, rates, fees, tariffs
- CONTACT pages have address, phone, email, location
- SERVICES pages describe what the business offers
- TERMS pages have T&Cs, policies, cancellation rules
- FAQ pages have common questions and answers

Return JSON array with one object per page:
[{"page_index": 0, "page_type": "pricing", "confidence": 0.9, "relevance": 0.95, "reason": "Contains price list"}]

Pages to classify:
"""

    for i, page in enumerate(pages):
        # Truncate content for prompt efficiency
        content_preview = page.markdown[:1500] if page.markdown else "(empty)"
        prompt += f"""
---
Page {i}:
URL: {page.url}
Title: {page.title or '(no title)'}
Content preview:
{content_preview}
---
"""

    return prompt


def classify_with_llm(
    pages: List[CrawledPage],
    api_key: Optional[str] = None,
) -> List[PageClassification]:
    """
    Classify pages using Claude Haiku (cheap LLM).
    Falls back to rule-based if no API key.
    """
    if api_key is None:
        api_key = get_anthropic_api_key()

    if not api_key:
        # Fall back to rule-based classification
        return [classify_with_rules(page) for page in pages]

    try:
        import anthropic

        config = get_classifier_config()
        client = anthropic.Anthropic(api_key=api_key)

        prompt = build_classification_prompt(pages)

        response = client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens * len(pages),  # Scale with batch size
            temperature=config.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse LLM response
        response_text = response.content[0].text
        classifications = parse_llm_response(response_text, len(pages))

        return classifications

    except ImportError:
        # anthropic package not installed
        return [classify_with_rules(page) for page in pages]
    except Exception as e:
        # Any LLM error - fall back to rules
        print(f"LLM classification failed: {e}, falling back to rules")
        return [classify_with_rules(page) for page in pages]


def parse_llm_response(response_text: str, expected_count: int) -> List[PageClassification]:
    """Parse the LLM's JSON response into PageClassification objects."""
    try:
        # Try to extract JSON from response
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON array found in response")

        data = json.loads(json_match.group())

        classifications = []
        for item in data:
            page_type_str = item.get("page_type", "other").lower()
            try:
                page_type = PageType(page_type_str)
            except ValueError:
                page_type = PageType.OTHER

            classifications.append(PageClassification(
                page_type=page_type,
                confidence=float(item.get("confidence", 0.5)),
                relevance_for_extraction=float(item.get("relevance", 0.5)),
                reasoning=item.get("reason"),
            ))

        # Pad with defaults if LLM returned fewer items
        while len(classifications) < expected_count:
            classifications.append(PageClassification(
                page_type=PageType.OTHER,
                confidence=0.0,
                relevance_for_extraction=0.3,
                reasoning="LLM did not classify this page",
            ))

        return classifications

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # Return default classifications on parse error
        return [
            PageClassification(
                page_type=PageType.OTHER,
                confidence=0.0,
                relevance_for_extraction=0.3,
                reasoning=f"Parse error: {e}",
            )
            for _ in range(expected_count)
        ]


def classify_pages(
    pages: List[CrawledPage],
    use_llm: bool = True,
    api_key: Optional[str] = None,
    batch_size: int = 10,
) -> List[CrawledPage]:
    """
    Classify a list of crawled pages.

    Strategy:
    1. First pass: Rule-based classification (free, instant)
    2. Second pass: LLM classification for uncertain pages (cheap, more accurate)

    Args:
        pages: List of crawled pages to classify
        use_llm: Whether to use LLM for uncertain classifications
        api_key: Anthropic API key (optional, will try env var)
        batch_size: Number of pages to classify per LLM call

    Returns:
        Same pages with classification fields populated
    """
    # First pass: Rule-based classification
    for page in pages:
        signals = analyze_content_signals(page.markdown)
        classification = classify_with_rules(page)

        page.page_type = classification.page_type
        page.page_type_confidence = classification.confidence
        page.relevance_score = classification.relevance_for_extraction
        page.has_pricing_signals = signals["has_pricing_signals"]
        page.has_contact_signals = signals["has_contact_signals"]
        page.word_count = signals["word_count"]

    # Second pass: LLM classification for low-confidence pages
    if use_llm:
        uncertain_pages = [p for p in pages if p.page_type_confidence < 0.7]

        if uncertain_pages:
            # Process in batches
            for i in range(0, len(uncertain_pages), batch_size):
                batch = uncertain_pages[i:i + batch_size]
                llm_classifications = classify_with_llm(batch, api_key)

                for page, classification in zip(batch, llm_classifications):
                    # Only update if LLM is more confident
                    if classification.confidence > page.page_type_confidence:
                        page.page_type = classification.page_type
                        page.page_type_confidence = classification.confidence
                        page.relevance_score = classification.relevance_for_extraction

    return pages


def get_classification_summary(pages: List[CrawledPage]) -> Dict[str, Any]:
    """Get a summary of page classifications."""
    type_counts = {}
    total_relevance = 0.0

    for page in pages:
        type_name = page.page_type.value if page.page_type else "unknown"
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
        total_relevance += page.relevance_score

    return {
        "total_pages": len(pages),
        "type_distribution": type_counts,
        "average_relevance": total_relevance / len(pages) if pages else 0,
        "high_relevance_pages": len([p for p in pages if p.relevance_score >= 0.7]),
        "pages_with_pricing_signals": len([p for p in pages if p.has_pricing_signals]),
        "pages_with_contact_signals": len([p for p in pages if p.has_contact_signals]),
    }


if __name__ == "__main__":
    # Example usage
    test_pages = [
        CrawledPage(
            url="https://example-kennels.co.uk/",
            markdown="Welcome to Example Kennels. We offer dog boarding services.",
            title="Example Kennels - Home",
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/prices",
            markdown="Our prices: Small dogs £25 per night. Large dogs £30 per night.",
            title="Prices - Example Kennels",
        ),
        CrawledPage(
            url="https://example-kennels.co.uk/contact",
            markdown="Call us on 01onal234 567890. Email: info@example.co.uk. AB1 2CD",
            title="Contact Us",
        ),
    ]

    classified = classify_pages(test_pages, use_llm=False)

    for page in classified:
        print(f"{page.url}")
        print(f"  Type: {page.page_type.value}, Confidence: {page.page_type_confidence}")
        print(f"  Relevance: {page.relevance_score}")
        print()

    print("Summary:", get_classification_summary(classified))
