"""
Web Research Engine

Fetches URLs, extracts content, and uses Claude to extract relevant facts and statistics.
"""

import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup, Tag
from anthropic import Anthropic
from dotenv import load_dotenv
from typing import Optional
from urllib.parse import urlparse

load_dotenv()

logger = logging.getLogger(__name__)
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Request headers to avoid being blocked - comprehensive headers to look like a real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries
REQUEST_TIMEOUT = 20  # seconds

# Patterns to exclude (sidebars, ads, navigation, etc.)
EXCLUDE_PATTERNS = [
    'sidebar', 'widget', 'recent', 'related', 'footer', 'nav', 'menu',
    'advertisement', 'ad-', 'ads-', 'advert', 'sponsor', 'promo',
    'comment', 'share', 'social', 'newsletter', 'subscribe',
    'breadcrumb', 'pagination', 'author-bio', 'meta', 'tags',
    'popular', 'trending', 'recommended', 'also-read', 'more-from'
]

# Patterns that indicate main content
CONTENT_PATTERNS = [
    'content', 'article', 'post', 'entry', 'story', 'body',
    'main', 'text', 'blog', 'news', 'prose'
]


def _should_exclude_element(element) -> bool:
    """Check if an element should be excluded based on its class/id."""
    try:
        if element is None:
            return False
        if not isinstance(element, Tag):
            return False

        # Get class and id attributes with safe defaults
        classes = element.get('class') if hasattr(element, 'get') else None
        if classes is None:
            classes = []
        elif isinstance(classes, str):
            classes = [classes]

        element_id = element.get('id') if hasattr(element, 'get') else None
        if element_id is None:
            element_id = ''

        # Combine all identifiers for pattern matching
        identifiers = ' '.join(str(c) for c in classes).lower() + ' ' + str(element_id).lower()

        for pattern in EXCLUDE_PATTERNS:
            if pattern in identifiers:
                return True
        return False
    except Exception as e:
        print(f"[WEB RESEARCH] Warning in _should_exclude_element: {e}")
        return False


def _is_content_element(element) -> bool:
    """Check if an element likely contains main content."""
    try:
        if element is None:
            return False
        if not isinstance(element, Tag):
            return False

        # Get class and id attributes with safe defaults
        classes = element.get('class') if hasattr(element, 'get') else None
        if classes is None:
            classes = []
        elif isinstance(classes, str):
            classes = [classes]

        element_id = element.get('id') if hasattr(element, 'get') else None
        if element_id is None:
            element_id = ''

        identifiers = ' '.join(str(c) for c in classes).lower() + ' ' + str(element_id).lower()

        for pattern in CONTENT_PATTERNS:
            if pattern in identifiers:
                return True
        return False
    except Exception as e:
        print(f"[WEB RESEARCH] Warning in _is_content_element: {e}")
        return False


def _get_text_density(element) -> tuple[int, int]:
    """Calculate text length and tag count for density comparison."""
    try:
        if element is None:
            return 0, 0
        text = element.get_text(strip=True) if hasattr(element, 'get_text') else ''
        tags = len(element.find_all()) if hasattr(element, 'find_all') else 0
        return len(text), tags
    except Exception as e:
        print(f"[WEB RESEARCH] Warning in _get_text_density: {e}")
        return 0, 0


def _clean_element(element) -> None:
    """Remove unwanted child elements from content."""
    try:
        if element is None or not hasattr(element, 'find_all'):
            return
        # Remove elements that match exclude patterns
        for child in element.find_all(True):
            if _should_exclude_element(child):
                try:
                    child.decompose()
                except Exception:
                    pass  # Element may have already been removed
    except Exception as e:
        print(f"[WEB RESEARCH] Warning in _clean_element: {e}")


def _extract_page_title(soup) -> str:
    """Extract the page title from <title> or <h1>."""
    try:
        if soup is None:
            return ""

        # Try <title> first
        title_tag = soup.find('title') if hasattr(soup, 'find') else None
        if title_tag:
            title = title_tag.get_text(strip=True) if hasattr(title_tag, 'get_text') else ''
            # Clean up common title suffixes
            title = re.split(r'\s*[|\-–—]\s*', title)[0].strip()
            if title:
                return title

        # Fall back to first <h1>
        h1 = soup.find('h1') if hasattr(soup, 'find') else None
        if h1:
            return h1.get_text(strip=True) if hasattr(h1, 'get_text') else ''

        return ""
    except Exception as e:
        print(f"[WEB RESEARCH] Warning in _extract_page_title: {e}")
        return ""


def _extract_tables(soup) -> str:
    """Extract data from tables on the page."""
    try:
        if soup is None or not hasattr(soup, 'find_all'):
            return ""

        tables_text = []

        for table in soup.find_all('table'):
            if _should_exclude_element(table):
                continue

            table_data = []

            # Extract headers
            headers = []
            for th in table.find_all('th') if hasattr(table, 'find_all') else []:
                text = th.get_text(strip=True) if hasattr(th, 'get_text') else ''
                headers.append(text)
            if headers:
                table_data.append(' | '.join(headers))
                table_data.append('-' * 40)

            # Extract rows
            for row in table.find_all('tr') if hasattr(table, 'find_all') else []:
                cells = []
                for td in row.find_all(['td', 'th']) if hasattr(row, 'find_all') else []:
                    text = td.get_text(strip=True) if hasattr(td, 'get_text') else ''
                    cells.append(text)
                if cells and any(cells):
                    table_data.append(' | '.join(cells))

            if table_data:
                tables_text.append('\n'.join(table_data))

        if tables_text:
            return "\n\n[TABLE DATA]\n" + "\n\n".join(tables_text)
        return ""
    except Exception as e:
        print(f"[WEB RESEARCH] Warning in _extract_tables: {e}")
        return ""


def _extract_image_data(soup) -> str:
    """Extract alt text from images that might contain data."""
    try:
        if soup is None or not hasattr(soup, 'find_all'):
            return ""

        image_info = []

        for img in soup.find_all('img'):
            alt = img.get('alt', '') if hasattr(img, 'get') else ''
            if alt and len(alt) > 20:  # Only include meaningful alt text
                # Filter out generic image descriptions
                if not any(skip in alt.lower() for skip in ['logo', 'icon', 'avatar', 'thumbnail', 'profile']):
                    image_info.append(f"[Image: {alt}]")

        if image_info:
            return "\n\n[IMAGE DESCRIPTIONS]\n" + "\n".join(image_info[:10])  # Limit to 10 images
        return ""
    except Exception as e:
        print(f"[WEB RESEARCH] Warning in _extract_image_data: {e}")
        return ""


def _find_largest_text_block(soup) -> Optional[Tag]:
    """Find the element with the most substantial text content."""
    try:
        if soup is None or not hasattr(soup, 'find_all'):
            return None

        candidates = []

        for tag in soup.find_all(['div', 'section', 'article', 'main']):
            if _should_exclude_element(tag):
                continue

            text_len, tag_count = _get_text_density(tag)

            # Skip if too little text
            if text_len < 200:
                continue

            # Calculate text density (text per tag)
            density = text_len / max(tag_count, 1)

            candidates.append((tag, text_len, density))

        if not candidates:
            return None

        # Sort by text length, preferring higher density
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)

        return candidates[0][0]
    except Exception as e:
        print(f"[WEB RESEARCH] Warning in _find_largest_text_block: {e}")
        return None


def _fetch_with_retry(url: str) -> Optional[requests.Response]:
    """
    Fetch a URL with retry logic.

    Returns the response object or None if all retries fail.
    """
    import traceback

    last_error = None

    print(f"\n[WEB RESEARCH] ========================================")
    print(f"[WEB RESEARCH] Attempting to fetch: {url}")
    print(f"[WEB RESEARCH] ========================================")

    for attempt in range(MAX_RETRIES):
        try:
            print(f"[WEB RESEARCH] Attempt {attempt + 1}/{MAX_RETRIES}...")
            logger.info(f"Fetching URL (attempt {attempt + 1}/{MAX_RETRIES}): {url}")

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )

            print(f"[WEB RESEARCH] Response status: {response.status_code}")
            print(f"[WEB RESEARCH] Content length: {len(response.text)} chars")
            print(f"[WEB RESEARCH] Content preview: {response.text[:500]}...")

            response.raise_for_status()

            logger.info(f"Successfully fetched {url} (status: {response.status_code})")
            print(f"[WEB RESEARCH] SUCCESS - Fetched {len(response.text)} chars")
            return response

        except requests.exceptions.Timeout as e:
            last_error = f"Timeout after {REQUEST_TIMEOUT}s"
            print(f"[WEB RESEARCH] TIMEOUT on attempt {attempt + 1}: {last_error}")
            logger.warning(f"Attempt {attempt + 1} timeout for {url}: {last_error}")

        except requests.exceptions.SSLError as e:
            last_error = f"SSL error: {str(e)}"
            print(f"[WEB RESEARCH] SSL ERROR on attempt {attempt + 1}: {last_error}")
            print(f"[WEB RESEARCH] Full traceback:\n{traceback.format_exc()}")
            logger.warning(f"Attempt {attempt + 1} SSL error for {url}: {last_error}")

        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection error: {str(e)}"
            print(f"[WEB RESEARCH] CONNECTION ERROR on attempt {attempt + 1}: {last_error}")
            print(f"[WEB RESEARCH] Full traceback:\n{traceback.format_exc()}")
            logger.warning(f"Attempt {attempt + 1} connection error for {url}: {last_error}")

        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP error {e.response.status_code}: {str(e)}"
            print(f"[WEB RESEARCH] HTTP ERROR on attempt {attempt + 1}: {last_error}")
            print(f"[WEB RESEARCH] Response body: {e.response.text[:500] if e.response.text else 'empty'}")
            logger.warning(f"Attempt {attempt + 1} HTTP error for {url}: {last_error}")
            # Don't retry on 4xx errors (client errors)
            if e.response.status_code < 500:
                print(f"[WEB RESEARCH] Not retrying - client error (4xx)")
                break

        except requests.exceptions.RequestException as e:
            last_error = f"Request error: {str(e)}"
            print(f"[WEB RESEARCH] REQUEST ERROR on attempt {attempt + 1}: {last_error}")
            print(f"[WEB RESEARCH] Full traceback:\n{traceback.format_exc()}")
            logger.warning(f"Attempt {attempt + 1} request error for {url}: {last_error}")

        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            print(f"[WEB RESEARCH] UNEXPECTED ERROR on attempt {attempt + 1}: {last_error}")
            print(f"[WEB RESEARCH] Full traceback:\n{traceback.format_exc()}")

        # Wait before retrying (except on last attempt)
        if attempt < MAX_RETRIES - 1:
            print(f"[WEB RESEARCH] Waiting {RETRY_DELAY}s before retry...")
            logger.info(f"Waiting {RETRY_DELAY}s before retry...")
            time.sleep(RETRY_DELAY)

    print(f"[WEB RESEARCH] FAILED - All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    logger.error(f"All {MAX_RETRIES} attempts failed for {url}. Last error: {last_error}")
    return None


def fetch_url_content(url: str) -> Optional[str]:
    """
    Fetch and extract text content from a URL with smart content detection.

    Returns string with title, content, tables, and image data, or None if fetching fails.
    """
    import traceback

    try:
        print(f"[WEB RESEARCH] Starting content extraction for: {url}")

        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            logger.error(f"Invalid URL format: {url}")
            return None

        # Fetch the page with retry logic
        response = _fetch_with_retry(url)
        if not response:
            return None

        print(f"[WEB RESEARCH] Parsing HTML...")

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        if soup is None:
            print(f"[WEB RESEARCH] ERROR: BeautifulSoup returned None")
            return None

        print(f"[WEB RESEARCH] Extracting page title...")
        # Extract page title first
        page_title = _extract_page_title(soup)
        print(f"[WEB RESEARCH] Title: {page_title[:100] if page_title else 'None'}...")

        print(f"[WEB RESEARCH] Extracting tables...")
        # Extract tables before removing elements
        tables_text = _extract_tables(soup)
        print(f"[WEB RESEARCH] Tables: {len(tables_text)} chars")

        print(f"[WEB RESEARCH] Extracting image data...")
        # Extract image alt text
        image_text = _extract_image_data(soup)
        print(f"[WEB RESEARCH] Images: {len(image_text)} chars")

        print(f"[WEB RESEARCH] Removing script/style elements...")
        # Remove script, style, and unwanted elements
        for element in soup(['script', 'style', 'noscript', 'iframe']):
            try:
                element.decompose()
            except Exception:
                pass

        print(f"[WEB RESEARCH] Removing excluded elements...")
        # Remove elements matching exclude patterns
        # Create a list first to avoid modifying while iterating
        elements_to_remove = []
        for element in soup.find_all(True):
            if _should_exclude_element(element):
                elements_to_remove.append(element)

        for element in elements_to_remove:
            try:
                element.decompose()
            except Exception:
                pass

        print(f"[WEB RESEARCH] Finding main content...")
        # Strategy 1: Look for <article> tag
        main_content = soup.find('article')
        extraction_method = "article tag"

        # Strategy 2: Look for <main> tag
        if not main_content:
            main_content = soup.find('main')
            extraction_method = "main tag"

        # Strategy 3: Look for elements with content-related classes/ids
        if not main_content:
            for tag in soup.find_all(['div', 'section']):
                if _is_content_element(tag):
                    text_len, _ = _get_text_density(tag)
                    if text_len > 200:
                        main_content = tag
                        extraction_method = "content class/id"
                        break

        # Strategy 4: Find largest text block
        if not main_content:
            main_content = _find_largest_text_block(soup)
            extraction_method = "largest text block"

        # Strategy 5: Fall back to body
        if not main_content:
            main_content = soup.find('body')
            extraction_method = "body fallback"

        print(f"[WEB RESEARCH] Extraction method: {extraction_method}")

        if main_content and hasattr(main_content, 'get_text'):
            # Clean the content element
            _clean_element(main_content)
            text = main_content.get_text(separator='\n', strip=True)
        elif soup and hasattr(soup, 'get_text'):
            text = soup.get_text(separator='\n', strip=True)
            extraction_method = "raw text"
        else:
            print(f"[WEB RESEARCH] ERROR: No content found")
            return None

        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)

        print(f"[WEB RESEARCH] Extracted {len(text)} chars of text")

        # Check if content seems too short or irrelevant
        if len(text) < 200:
            print(f"[WEB RESEARCH] Content too short ({len(text)} chars), trying paragraph fallback...")
            logger.warning(f"Extracted content too short ({len(text)} chars), trying alternative extraction")
            # Try getting all paragraph text as fallback
            try:
                paragraphs = soup.find_all('p') if hasattr(soup, 'find_all') else []
                p_texts = []
                for p in paragraphs:
                    if p and hasattr(p, 'get_text'):
                        p_content = p.get_text(strip=True)
                        if p_content and len(p_content) > 50:
                            p_texts.append(p_content)
                p_text = '\n'.join(p_texts)
                if len(p_text) > len(text):
                    text = p_text
                    extraction_method = "paragraph fallback"
                    print(f"[WEB RESEARCH] Paragraph fallback extracted {len(text)} chars")
            except Exception as para_e:
                print(f"[WEB RESEARCH] Warning in paragraph fallback: {para_e}")

        # Build final content with metadata
        final_content = ""
        if page_title:
            final_content += f"TITLE: {page_title}\n\n"

        final_content += f"MAIN CONTENT:\n{text}"

        if tables_text:
            final_content += f"\n\n{tables_text}"

        if image_text:
            final_content += f"\n\n{image_text}"

        # Truncate if too long (keep first ~8000 chars for Claude context)
        if len(final_content) > 8000:
            final_content = final_content[:8000] + "\n[Content truncated...]"

        print(f"[WEB RESEARCH] SUCCESS - Final content: {len(final_content)} chars using {extraction_method}")
        logger.info(f"Extracted {len(final_content)} characters from {url} using {extraction_method}")
        return final_content

    except Exception as e:
        print(f"[WEB RESEARCH] ERROR in fetch_url_content: {str(e)}")
        print(f"[WEB RESEARCH] Full traceback:\n{traceback.format_exc()}")
        logger.error(f"Error processing content from {url}: {str(e)}")
        return None


def extract_facts_from_content(content: str, topic: str, url: str) -> dict:
    """
    Use Claude to extract relevant facts, statistics, and quotes from content.

    Args:
        content: The text content from the webpage
        topic: The topic/idea the user is writing about
        url: The source URL for citation

    Returns:
        Dict with extracted_facts, summary, and source info
    """
    try:
        # Get the domain for source attribution
        parsed = urlparse(url)
        source_name = parsed.netloc.replace('www.', '')

        prompt = f"""Analyze this web content and extract relevant facts, statistics, and quotes that could support a LinkedIn post about the following topic:

TOPIC: {topic}

WEB CONTENT:
{content}

SOURCE: {source_name}

Please extract:
1. Specific statistics or data points (with exact numbers)
2. Key quotes that could be cited
3. Main findings or conclusions relevant to the topic
4. Any industry trends mentioned

Format your response as JSON:
{{
    "extracted_facts": [
        {{
            "fact": "The specific fact or statistic",
            "type": "statistic" | "quote" | "finding" | "trend",
            "citation_text": "How to cite this (e.g., 'According to [source]...')"
        }}
    ],
    "summary": "A 2-3 sentence summary of the most relevant information for this topic",
    "relevance_score": 1-10 (how relevant is this content to the topic)
}}

If no relevant facts are found, return empty extracted_facts array with relevance_score of 1.
Only include facts that are directly relevant to the topic. Be precise with numbers - don't estimate or round."""

        response = anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text

        # Parse JSON from response
        import json

        # Try to extract JSON from the response
        try:
            # Handle markdown code blocks
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            result = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response, using raw text")
            result = {
                "extracted_facts": [],
                "summary": response_text[:500],
                "relevance_score": 5
            }

        # Add source info
        result["url"] = url
        result["source_name"] = source_name

        return result

    except Exception as e:
        logger.error(f"Error extracting facts from content: {str(e)}")
        return {
            "url": url,
            "source_name": urlparse(url).netloc.replace('www.', ''),
            "extracted_facts": [],
            "summary": f"Error extracting content: {str(e)}",
            "relevance_score": 0
        }


def fetch_and_extract(url: str, topic: str) -> dict:
    """
    Main function: Fetch a URL and extract relevant facts for a topic.

    Args:
        url: The URL to fetch
        topic: The topic/idea the user is writing about

    Returns:
        Dict with url, extracted_facts, summary, source_name, relevance_score
    """
    logger.info(f"Fetching and extracting from URL: {url}")
    logger.info(f"Topic: {topic[:100]}...")

    # Fetch content
    content = fetch_url_content(url)

    if not content:
        return {
            "url": url,
            "source_name": urlparse(url).netloc.replace('www.', ''),
            "extracted_facts": [],
            "summary": "Failed to fetch content from URL",
            "relevance_score": 0,
            "error": True
        }

    # Extract facts using Claude
    result = extract_facts_from_content(content, topic, url)

    logger.info(f"Extracted {len(result.get('extracted_facts', []))} facts with relevance score {result.get('relevance_score', 0)}")

    return result


def process_research_urls(urls: list[str], topic: str) -> list[dict]:
    """
    Process multiple research URLs and extract facts from each.

    Args:
        urls: List of URLs to process
        topic: The topic/idea the user is writing about

    Returns:
        List of extraction results
    """
    results = []

    for url in urls:
        if url and url.strip():
            result = fetch_and_extract(url.strip(), topic)
            results.append(result)

    return results
