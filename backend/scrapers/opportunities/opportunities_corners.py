import asyncio
import re
import argparse
import logging
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date

import sys
from pathlib import Path

# Add backend dir to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scrapers.opportunities.base import BaseOpportunityScraper, logger

OPPORTUNITIES_CORNERS_CATEGORIES = {
    'bachelor-master-phd-scholarships': 'scholarship',
    'scholarships-in-australia': 'scholarship',
    'scholarships-in-canada': 'scholarship',
    'scholarships-in-china': 'scholarship',
    'scholarships-in-europe': 'scholarship',
    'scholarships-in-japan': 'scholarship',
    'middle-east-scholarships': 'scholarship',
    'scholarships-in-singapore': 'scholarship',
    'scholarships-in-south-korea': 'scholarship',
    'scholarships-in-usa': 'scholarship',
    'scholarships-in-uk': 'scholarship',
    'internships': 'internship',
    'exchange-programs': 'exchange_program',
    'online-courses': 'online_course',
    'conferences': 'conference',
    'fellowships': 'fellowship',
    'competitions': 'competition',
    'trainings': 'training',
}

class OpportunitiesCornersScraper(BaseOpportunityScraper):
    def __init__(self):
        super().__init__(source_name="OpportunitiesCorners", base_url="https://opportunitiescorners.com")

    def extract_links_from_listing(self, soup: BeautifulSoup) -> List[str]:
        links = []
        # Typically wrapped in articles or divs with classes like 'post'
        for article in soup.select('article, div.post, div.type-post'):
            # Find link inside title
            title_a = article.select_one('.entry-title a, h2 a, h3 a')
            if title_a and title_a.has_attr('href'):
                links.append(title_a['href'])
        return links

    def _extract_deadline(self, text: str) -> Optional[str]:
        patterns = [
            r'Deadline:\s*([A-Z][a-zA-Z]+\s+\d{1,2},\s*\d{4})',
            r'Last Date:\s*([A-Z][a-zA-Z]+\s+\d{1,2},\s*\d{4})',
            r'Application Deadline:\s*([A-Z][a-zA-Z]+\s+\d{1,2},\s*\d{4})',
            r'Deadline:\s*(\d{1,2}\s+[A-Z][a-zA-Z]+\s+\d{4})'
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                try:
                    dt = parse_date(match.group(1))
                    return dt.date().isoformat()
                except Exception:
                    pass
        return None

    def _extract_funding(self, title: str, text: str) -> str:
        combined = (title + " " + text).lower()
        if "fully funded" in combined:
            return "fully_funded"
        elif "partially funded" in combined or "partial funding" in combined:
            return "partially_funded"
        elif any(k in combined for k in ["stipend", "paid", "€", "$", "usd", "eur"]):
            return "paid"
        return "unknown"

    def _extract_country(self, title: str) -> Optional[str]:
        match = re.search(r'\bin\s+([A-Z][a-zA-Z\s]+?)(?:\s*\(|\s*$|,)', title)
        if match:
            # Clean up trailing spaces or words
            country = match.group(1).strip()
            # Ignore common false positives
            if country.lower() not in ['the', 'a', 'an', 'this']:
                return country
        return None

    def _extract_organization(self, title: str, soup: BeautifulSoup) -> Optional[str]:
        # Try to get from OpenGraph site name first if it's the university
        # Often og:site_name is just 'Opportunities Corners', so fallback to title regex
        match = re.search(r'^(.+?)\s+(?:Scholarship|Fellowship|Internship|Exchange Program)', title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_tags(self, title: str, soup: BeautifulSoup) -> List[str]:
        tags = set()
        # From meta keywords
        meta_kws = soup.find('meta', {'name': 'keywords'})
        if meta_kws and meta_kws.get('content'):
            for kw in meta_kws['content'].split(','):
                tags.add(kw.strip().lower())
        
        # Simple extraction from title
        stopwords = {'in', 'for', 'the', 'and', 'to', 'of', 'at', 'a', 'an'}
        words = [w.strip().lower() for w in re.split(r'\W+', title) if w.strip()]
        for w in words:
            if w not in stopwords and len(w) > 3:
                tags.add(w)
                
        return list(tags)

    async def scrape_post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        soup = await self.fetch_html(url)
        if not soup:
            return None

        # Title
        title_el = soup.select_one('h1.entry-title, title')
        title = title_el.get_text(strip=True) if title_el else ""
        title = re.sub(r'\s*[-|]\s*Opportunities\s*Corners.*$', '', title, flags=re.IGNORECASE).strip()

        # Description
        content_el = soup.select_one('.entry-content, .post-content')
        full_text = content_el.get_text(separator=' ', strip=True) if content_el else ""
        description = full_text[:2000]

        opp_type = kwargs.get('opportunity_type', 'other')
        deadline = self._extract_deadline(full_text)
        funding = self._extract_funding(title, full_text)
        country = self._extract_country(title)
        org = self._extract_organization(title, soup)
        tags = self._extract_tags(title, soup)

        return {
            "source_url": url,
            "title": title,
            "description": description,
            "opportunity_type": opp_type,
            "funding_type": funding,
            "country": country,
            "region": None,
            "organization": org,
            "deadline": deadline,
            "start_date": None,
            "tags": tags
        }

    async def crawl_category(self, category_slug: str, **kwargs) -> List[Dict[str, Any]]:
        opp_type = kwargs.get('opportunity_type', 'other')
        limit = kwargs.get('limit', None)
        
        category_url = f"{self.base_url}/category/{category_slug}/"
        logger.info(f"[OpportunitiesCorners] Crawling category: {category_slug}")
        
        urls = await self.get_all_listing_urls(category_url)
        if limit:
            urls = urls[:limit]
            
        logger.info(f"[OpportunitiesCorners] Found {len(urls)} URLs in {category_slug}. Scraping posts...")
        
        records = []
        for url in urls:
            post_data = await self.scrape_post(url, opportunity_type=opp_type)
            if post_data:
                records.append(post_data)
                
        return records


async def main():
    parser = argparse.ArgumentParser(description="Opportunities Corners Scraper")
    parser.add_argument("--category", type=str, help="Category slug to scrape")
    parser.add_argument("--all", action="store_true", help="Scrape all categories")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of posts per category")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    scraper = OpportunitiesCornersScraper()

    if args.all:
        for cat, opp_type in OPPORTUNITIES_CORNERS_CATEGORIES.items():
            records = await scraper.crawl_category(cat, opportunity_type=opp_type, limit=args.limit)
            await scraper.upsert_opportunities(records)
    elif args.category:
        opp_type = OPPORTUNITIES_CORNERS_CATEGORIES.get(args.category, 'other')
        records = await scraper.crawl_category(args.category, opportunity_type=opp_type, limit=args.limit)
        await scraper.upsert_opportunities(records)
    else:
        print("Please specify --category <slug> or --all")

    await scraper._close()

if __name__ == "__main__":
    asyncio.run(main())
