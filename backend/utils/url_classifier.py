import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

def normalize_apply_url(url: str) -> str:
    """
    Strip tracking params and normalize trailing slashes.
    """
    if not url:
        return url
        
    parsed = urlparse(url)
    
    # Strip common tracking parameters
    tracking_params = {'ref', 'utm_source', 'utm_medium', 'utm_campaign', 'gh_src', 'src', 'source'}
    query = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_query = [(k, v) for k, v in query if k.lower() not in tracking_params]
    
    # Reconstruct query
    new_query = urlencode(filtered_query)
    
    # Normalize path: remove trailing slash if present (except for root "/")
    path = parsed.path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
        
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    return normalized

def is_job_listing_page(url: str) -> bool:
    """
    Returns True if URL looks like a catch-all jobs listing (not a specific job).
    Pattern: ends in /jobs, /careers, /openings without a job ID segment after.
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    
    if not path:
        return True # Just the domain root is usually a listing page
        
    # Check if the last path segment is exactly 'jobs', 'careers', or 'openings'
    # e.g., https://company.com/careers
    last_segment = path.split("/")[-1].lower()
    
    listing_keywords = {'jobs', 'careers', 'openings', 'search', 'vacancies'}
    if last_segment in listing_keywords:
        return True
        
    return False

def is_same_job(original_url: str, redirected_url: str) -> bool:
    """
    Returns True if the redirect kept us on the same job posting.
    Checks if a distinctive job ID or slug from the original URL is present in the redirected URL.
    """
    orig_parsed = urlparse(original_url)
    redir_parsed = urlparse(redirected_url)
    
    orig_path = orig_parsed.path.rstrip("/")
    redir_path = redir_parsed.path.rstrip("/")
    
    if orig_path == redir_path:
        return True
        
    # Extract the last substantive segment of the original URL (likely the ID or slug)
    orig_segments = [s for s in orig_path.split("/") if s]
    if not orig_segments:
        return False
        
    last_segment = orig_segments[-1]
    
    # Check if the redirected URL still contains this segment anywhere in its path
    # Using word boundaries to avoid partial matches, or just a simple 'in' check.
    if f"/{last_segment}" in redir_path or redir_path.endswith(f"/{last_segment}"):
        return True
        
    return False
