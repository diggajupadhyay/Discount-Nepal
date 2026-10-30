from discount_nepal.scrapers.dolpo import DolpoScraper
from discount_nepal.scrapers.evanmens import EvanMensScraper
from discount_nepal.scrapers.harrington import HarringtonWearScraper
from discount_nepal.scrapers.hubanepal import HubaNepalScraper
from discount_nepal.scrapers.instylenepal import InstyleNepalScraper
from discount_nepal.scrapers.kapadaa import KapadaaScraper
from discount_nepal.scrapers.ktmcty import KTMCTYScraper
from discount_nepal.scrapers.sonamgear import SonamGearScraper
from discount_nepal.scrapers.ufonepal import UfonepalScraper
from discount_nepal.scrapers.zoot import ZootScraper

SCRAPERS = {
    "Zoot": ZootScraper,
    "KTM CTY": KTMCTYScraper,
    "Evan Mens": EvanMensScraper,
    "Dolpo": DolpoScraper,
    "Sonam Gear": SonamGearScraper,
    "Harrington Wear": HarringtonWearScraper,
    "Huba Nepal": HubaNepalScraper,
    "Instyle Nepal": InstyleNepalScraper,
    "Kapadaa": KapadaaScraper,
    "UFO Nepal": UfonepalScraper,
}

if __name__ == "__main__":
    for name, cls in SCRAPERS.items():
        try:
            scraper = cls()
            products = scraper.run()
            print(f"{name}: {len(products)} products")
            for p in products[:2]:
                print(f"   - {p.name} | {p.sale_price} (was {p.regular_price})")
        except Exception as e:
            print(f"{name}: ERROR - {e}")
