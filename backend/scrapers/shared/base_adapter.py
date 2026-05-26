import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)

class ATSAdapterBase(ABC):
    """
    Base class for all ATS scrapers. Ensures consistent config parsing
    and job extraction structure across all integrations.
    """
    def __init__(self, company_config: dict):
        self.company_config = company_config
        self.company_name = company_config.get("name", "Unknown")
        self.priority = company_config.get("priority", 10)
        self.tags = company_config.get("tags", [])
        self.company_type = company_config.get("company_type", "")
        
    def _format_tags(self) -> str:
        return ", ".join(self.tags) if self.tags else ""
        
    @abstractmethod
    async def scrape(self, query: str = "", location: str = "") -> list[dict]:
        """
        Execute the scraping logic. Must be implemented by subclasses.
        Must return a list of standardized job dictionaries.
        """
        pass
