import re
from datetime import datetime, timedelta

def parse_relative_date(date_str: str) -> datetime:
    """Smart date parsing (e.g., '3 days ago', 'Posted today')."""
    if not date_str:
        return datetime.now()

    date_str = date_str.lower()
    
    if "today" in date_str or "just now" in date_str or "hour" in date_str or "minute" in date_str:
        return datetime.now()
        
    days_match = re.search(r'(\d+)\s*days?', date_str)
    if days_match:
        return datetime.now() - timedelta(days=int(days_match.group(1)))
        
    weeks_match = re.search(r'(\d+)\s*weeks?', date_str)
    if weeks_match:
        return datetime.now() - timedelta(weeks=int(weeks_match.group(1)))
        
    months_match = re.search(r'(\d+)\s*months?', date_str)
    if months_match:
        return datetime.now() - timedelta(days=30 * int(months_match.group(1)))

    return datetime.now()

def extract_salary_from_text(text: str) -> tuple[int, int, str]:
    """
    Regex-based salary extraction. Returns (min, max, currency).
    Handles ₹X - ₹Y LPA / ₹X LPA / X-Y lakhs / $Xk - $Yk / $X,000 - $Y,000
    """
    if not text:
        return 0, 0, "INR"
        
    text_lower = text.lower()
    
    # LPA patterns
    lpa_match = re.search(r'(?:₹|rs\.?|inr)?\s*([\d\.]+)\s*(?:-|to)\s*(?:₹|rs\.?|inr)?\s*([\d\.]+)\s*(?:lpa|lakhs?)', text_lower)
    if lpa_match:
        return int(float(lpa_match.group(1)) * 100000), int(float(lpa_match.group(2)) * 100000), "INR"
        
    lpa_single = re.search(r'(?:₹|rs\.?|inr)?\s*([\d\.]+)\s*(?:lpa|lakhs?)', text_lower)
    if lpa_single:
        val = int(float(lpa_single.group(1)) * 100000)
        return val, val, "INR"

    # USD patterns
    usd_k_match = re.search(r'\$\s*([\d\.]+)\s*k\s*(?:-|to)\s*\$?\s*([\d\.]+)\s*k', text_lower)
    if usd_k_match:
        return int(float(usd_k_match.group(1)) * 1000), int(float(usd_k_match.group(2)) * 1000), "USD"
        
    usd_match = re.search(r'\$\s*([\d,]+)\s*(?:-|to)\s*\$?\s*([\d,]+)', text_lower)
    if usd_match:
        min_val = int(usd_match.group(1).replace(",", ""))
        max_val = int(usd_match.group(2).replace(",", ""))
        if min_val > 1000: # Ensure it's likely an annual salary
            return min_val, max_val, "USD"

    return 0, 0, "INR"

def detect_remote(title: str, location: str, desc: str) -> bool:
    """Remote detection logic."""
    title = (title or "").lower()
    location = (location or "").lower()
    desc = (desc or "").lower()
    
    if "remote" in location or "anywhere" in location:
        return True
    if "work from home" in desc or "wfh" in title or "remote" in title:
        return True
        
    return False

def clean_description(html_desc: str) -> str:
    """Strip HTML and boilerplate."""
    if not html_desc:
        return ""
    
    # Very basic HTML stripping if BeautifulSoup isn't available everywhere
    try:
        from bs4 import BeautifulSoup
        text = BeautifulSoup(html_desc, "html.parser").get_text(separator="\n", strip=True)
    except ImportError:
        text = re.sub(r'<[^>]+>', ' ', html_desc)
        
    text = re.sub(r'\s+', ' ', text)
    
    # Remove boilerplate (simple examples)
    text = re.sub(r'apply now', '', text, flags=re.IGNORECASE)
    text = re.sub(r'cookie consent', '', text, flags=re.IGNORECASE)
    
    return text.strip()

def is_valid_apply_url(url: str) -> bool:
    """Dead link prevention."""
    if not url:
        return False
        
    # Check if it's just a root domain
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    if not parsed.netloc:
        return False
        
    if not parsed.path or parsed.path == "/":
        return False
        
    return True
