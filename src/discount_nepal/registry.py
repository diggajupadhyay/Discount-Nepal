"""Store scraper registry — maps store keys to scraper classes."""

from __future__ import annotations

from typing import List, Type

from .scrapers.base import BaseScraper
from .scrapers.dolpo import DolpoScraper
from .scrapers.evanmens import EvanMensScraper
from .scrapers.harrington import HarringtonWearScraper
from .scrapers.hubanepal import HubaNepalScraper
from .scrapers.instylenepal import InstyleNepalScraper
from .scrapers.kapadaa import KapadaaScraper
from .scrapers.ktmcty import KTMCTYScraper
from .scrapers.sonamgear import SonamGearScraper
from .scrapers.ufonepal import UfonepalScraper
from .scrapers.zoot import ZootScraper

# Ordered list of (key, scraper_class). The key is used as the `website`
# value and as the frontend filter option.
REGISTRY: List[tuple[str, Type[BaseScraper]]] = [
    ("dolpo", DolpoScraper),
    ("sonamgear", SonamGearScraper),
    ("ktmcty", KTMCTYScraper),
    ("zoot", ZootScraper),
    ("evanmens", EvanMensScraper),
    ("harrington", HarringtonWearScraper),
    ("hubanepal", HubaNepalScraper),
    ("instylenepal", InstyleNepalScraper),
    ("kapadaa", KapadaaScraper),
    ("ufonepal", UfonepalScraper),
]


def get_scraper(store_key: str) -> Type[BaseScraper] | None:
    """Return the scraper class for *store_key*, or ``None`` if unknown."""
    for key, cls in REGISTRY:
        if key == store_key:
            return cls
    return None


def list_stores() -> List[dict]:
    """Return metadata for every *enabled* store (frontend-friendly)."""
    return [
        {"key": key, "name": cls.store_name, "url": cls.base_url or "#"}
        for key, cls in REGISTRY
        if cls.enabled
    ]


def all_scrapers() -> List[BaseScraper]:
    """Instantiate one scraper per registered store."""
    return [cls() for _, cls in REGISTRY]
