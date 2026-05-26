import asyncio
import re
import argparse
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date

import sys
from pathlib import Path

# Add backend dir to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scrapers.opportunities.base import BaseOpportunityScraper, logger
# Reuse the extraction helpers from Corners since they are similar
from scrapers.opportunities.opportunities_corners import OpportunitiesCornersScraper

OPPORTUNITIES_CIRCLE_CATEGORIES = {
    'scholarships': 'scholarship',
    'scholarships/undergraduate-scholarship': 'scholarship',
    'scholarships/masters-scholarships': 'scholarship',
    'scholarships/phd-scholarships': 'scholarship',
    'fellowships': 'fellowship',
    'exchange-programs': 'exchange_program',
    'events': 'conference',
    'internships': 'internship',
    'conferences': 'conference',
    'competitions': 'competition',
}

class OpportunitiesCircleScraper(BaseOpportunityScraper):
    def __init__(self):
        super().__init__(source_name="OpportunitiesCircle", base_url="https://www.opportunitiescircle.com")
        self.corners_helpers = OpportunitiesCornersScraper()

    def extract_links_from_listing(self, soup: BeautifulSoup) -> List[str]:
        # This will not be used directly if we override crawl_category to parse listing cards
        return []

    async def scrape_post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        soup = await self.fetch_html(url)
        if not soup:
            return None

        # Title
        title_el = soup.select_one('h1.entry-title, title')
        title = title_el.get_text(strip=True) if title_el else ""
        title = re.sub(r'\s*[-|]\s*Opportunities\s*Circle.*$', '', title, flags=re.IGNORECASE).strip()

        # Description
        content_el = soup.select_one('.entry-content, .post-content')
        full_text = content_el.get_text(separator=' ', strip=True) if content_el else ""
        description = full_text[:2000]

        opp_type = kwargs.get('opportunity_type', 'other')
        deadline = kwargs.get('deadline') or self.corners_helpers._extract_deadline(full_text)
        funding = self.corners_helpers._extract_funding(title, full_text)
        country = self.corners_helpers._extract_country(title)
        org = self.corners_helpers._extract_organization(title, soup)
        tags = self.corners_helpers._extract_tags(title, soup)

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
        
        category_url = f"{self.base_url}/{category_slug}/"
        logger.info(f"[OpportunitiesCircle] Crawling category: {category_slug}")
        
        records = []
        page = 1
        consecutive_empty = 0
        seen_urls = set()

        while page <= 500:
            soup = await self.fetch_listing_page(category_url, page)
            if not soup:
                break
                
            # Find listing cards
            articles = soup.select('article, .td_module_wrap')
            if not articles:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    break
            else:
                consecutive_empty = 0
            
            added_any = False
            for article in articles:
                if limit and len(records) >= limit:
                    break
                    
                title_a = article.select_one('h3.entry-title a, .td-module-title a')
                if not title_a or not title_a.has_attr('href'):
                    continue
                    
                url = title_a['href']
                if 'opportunitiescircle.com' not in url or url in seen_urls:
                    continue
                    
                seen_urls.add(url)
                added_any = True
                
                # Check for deadline on the listing page
                # "Deadline: Month DD, YYYY"
                article_text = article.get_text(separator=' ')
                deadline = self.corners_helpers._extract_deadline(article_text)
                title = title_a.get_text(strip=True)
                
                # If we have deadline and sufficient info, we can skip full fetch.
                # However, description is needed for pgvector semantic search. 
                # We'll extract a snippet from the card as description if available,
                # else we fallback to fetching the post.
                excerpt = article.select_one('.td-excerpt, .entry-content p')
                snippet = excerpt.get_text(strip=True) if excerpt else ""
                
                if deadline and len(snippet) > 50:
                    # Construct record from listing page
                    funding = self.corners_helpers._extract_funding(title, snippet)
                    country = self.corners_helpers._extract_country(title)
                    org = self.corners_helpers._extract_organization(title, BeautifulSoup("", "html.parser"))
                    tags = self.corners_helpers._extract_tags(title, BeautifulSoup("", "html.parser"))
                    
                    records.append({
                        "source_url": url,
                        "title": title,
                        "description": snippet,
                        "opportunity_type": opp_type,
                        "funding_type": funding,
                        "country": country,
                        "region": None,
                        "organization": org,
                        "deadline": deadline,
                        "start_date": None,
                        "tags": tags
                    })
                else:
                    # Fallback to fetching individual post
                    post_data = await self.scrape_post(url, opportunity_type=opp_type, deadline=deadline)
                    if post_data:
                        records.append(post_data)

            if not added_any or (limit and len(records) >= limit):
                break
                
            page += 1
            
        logger.info(f"[OpportunitiesCircle] Finished crawling {category_slug}. Found {len(records)} records.")
        return records

async def main():
    parser = argparse.ArgumentParser(description="Opportunities Circle Scraper")
    parser.add_argument("--category", type=str, help="Category slug to scrape")
    parser.add_argument("--all", action="store_true", help="Scrape all categories")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of posts per category")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    scraper = OpportunitiesCircleScraper()

    if args.all:
        for cat, opp_type in OPPORTUNITIES_CIRCLE_CATEGORIES.items():
            records = await scraper.crawl_category(cat, opportunity_type=opp_type, limit=args.limit)
            await scraper.upsert_opportunities(records)
    elif args.category:
        opp_type = OPPORTUNITIES_CIRCLE_CATEGORIES.get(args.category, 'other')
        records = await scraper.crawl_category(args.category, opportunity_type=opp_type, limit=args.limit)
        await scraper.upsert_opportunities(records)
    else:
        print("Please specify --category <slug> or --all")

    await scraper._close()

if __name__ == "__main__":
    asyncio.run(main())
