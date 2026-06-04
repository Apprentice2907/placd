"""
Placd — Company Logo & Metadata Enrichment

Logo sources (tried in order):
  1. Clearbit Logo API (free): https://logo.clearbit.com/{domain}
  2. Google Favicon: https://www.google.com/s2/favicons?domain={domain}&sz=128
  3. Fallback: None (frontend renders initials avatar)
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# ── Known company → domain mapping ──────────────────────────────────────────

KNOWN_DOMAINS: dict[str, str] = {
    "google": "google.com",
    "microsoft": "microsoft.com",
    "amazon": "amazon.com",
    "apple": "apple.com",
    "meta": "meta.com",
    "netflix": "netflix.com",
    "nvidia": "nvidia.com",
    "intel": "intel.com",
    "amd": "amd.com",
    "qualcomm": "qualcomm.com",
    "broadcom": "broadcom.com",
    "stripe": "stripe.com",
    "airbnb": "airbnb.com",
    "uber": "uber.com",
    "lyft": "lyft.com",
    "twitter": "x.com",
    "linkedin": "linkedin.com",
    "salesforce": "salesforce.com",
    "oracle": "oracle.com",
    "sap": "sap.com",
    "ibm": "ibm.com",
    "accenture": "accenture.com",
    "deloitte": "deloitte.com",
    "openai": "openai.com",
    "anthropic": "anthropic.com",
    "deepmind": "deepmind.google",
    "mistral": "mistral.ai",
    "cohere": "cohere.com",
    "databricks": "databricks.com",
    "snowflake": "snowflake.com",
    "cloudflare": "cloudflare.com",
    "datadog": "datadoghq.com",
    "hashicorp": "hashicorp.com",
    "figma": "figma.com",
    "notion": "notion.so",
    "airtable": "airtable.com",
    "asana": "asana.com",
    "slack": "slack.com",
    "zoom": "zoom.us",
    "shopify": "shopify.com",
    "square": "squareup.com",
    "twilio": "twilio.com",
    "sendgrid": "sendgrid.com",
    "okta": "okta.com",
    "auth0": "auth0.com",
    "mongodb": "mongodb.com",
    "elastic": "elastic.co",
    "confluent": "confluent.io",
    "flipkart": "flipkart.com",
    "razorpay": "razorpay.com",
    "phonepe": "phonepe.com",
    "paytm": "paytm.com",
    "swiggy": "swiggy.com",
    "zomato": "zomato.com",
    "meesho": "meesho.com",
    "cred": "cred.club",
    "groww": "groww.in",
    "zerodha": "zerodha.com",
    "freshworks": "freshworks.com",
    "zoho": "zoho.com",
    "dream11": "dream11.com",
    "ola": "olacabs.com",
    "tcs": "tcs.com",
    "infosys": "infosys.com",
    "wipro": "wipro.com",
    "hcl": "hcltech.com",
    "tech mahindra": "techmahindra.com",
    "cognizant": "cognizant.com",
    "capgemini": "capgemini.com",
    "adobe": "adobe.com",
    "atlassian": "atlassian.com",
    "github": "github.com",
    "gitlab": "gitlab.com",
    "vercel": "vercel.com",
    "supabase": "supabase.com",
    "postman": "postman.com",
    "docker": "docker.com",
    "red hat": "redhat.com",
    "vmware": "vmware.com",
    "dell": "dell.com",
    "hp": "hp.com",
    "samsung": "samsung.com",
    "sony": "sony.com",
    "siemens": "siemens.com",
    "bosch": "bosch.com",
    "tesla": "tesla.com",
    "spacex": "spacex.com",
    "palantir": "palantir.com",
    "jpmorgan": "jpmorgan.com",
    "goldman sachs": "goldmansachs.com",
    "morgan stanley": "morganstanley.com",
    "visa": "visa.com",
    "mastercard": "mastercard.com",
    "paypal": "paypal.com",
    "coinbase": "coinbase.com",
    "canva": "canva.com",
    "miro": "miro.com",
    "linear": "linear.app",
    "retool": "retool.com",
    "lenskart": "lenskart.com",
    "nykaa": "nykaa.com",
    "delhivery": "delhivery.com",
    "practo": "practo.com",
    "browserstack": "browserstack.com",
    "hasura": "hasura.io",
    "chargebee": "chargebee.com",
    "clevertap": "clevertap.com",
    "darwinbox": "darwinbox.com",
}


def infer_company_domain(company_name: str) -> Optional[str]:
    """
    Infer the company's web domain from its name.
    Returns None if unknown.
    """
    name_lower = company_name.lower().strip()
    # Strip common suffixes
    for suffix in (" inc.", " inc", " ltd.", " ltd", " pvt.", " pvt",
                    " llp", " corp.", " corp", " technologies",
                    " technology", " solutions", " services",
                    " private limited", " limited"):
        if name_lower.endswith(suffix):
            name_lower = name_lower[: -len(suffix)].strip()

    return KNOWN_DOMAINS.get(name_lower)


async def get_company_logo_url(company_name: str, company_domain: str = None) -> Optional[str]:
    """
    Try to find a logo URL for the company.
    Returns the first working URL, or None.
    """
    domain = company_domain or infer_company_domain(company_name)
    if not domain:
        return None

    # Priority 1: Clearbit Logo API
    clearbit_url = f"https://logo.clearbit.com/{domain}"
    if await _url_returns_200(clearbit_url):
        return clearbit_url

    # Priority 2: Google Favicon (always works, lower quality)
    google_favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    return google_favicon


async def _url_returns_200(url: str) -> bool:
    """HEAD request to check if URL is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.head(url, follow_redirects=True)
            return resp.status_code == 200
    except Exception:
        return False


async def enrich_job_with_logo(job: dict) -> dict:
    """
    Enrich a single job dict with company_logo_url and company_domain.
    Called as a background task after saving.
    """
    company = job.get("company", "")
    if not company:
        return job

    domain = infer_company_domain(company)
    if domain:
        job["company_domain"] = domain

    logo_url = await get_company_logo_url(company, domain)
    if logo_url:
        job["company_logo_url"] = logo_url

    return job
