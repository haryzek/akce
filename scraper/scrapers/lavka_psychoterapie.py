"""
Subscraper: akce z centrum-lavka.cz pro typ "odborne_psychoterapie".

Tenká obálka nad lavka_common.py (viz jeho docstring — tam žije celá mechanika
i pasti). Vrací KOMPLETNÍ seznam akcí Lávky — stejný dostává i sesterská obálka
lavka_verejnost.py. Odborné vs. sebezkušenostní pro veřejnost rozdělují až
Cowork prompty (přísně vylučovací, hraniční akce → veřejnost).
"""

try:
    from .lavka_common import ZDROJ, scrape_lavka
    from .psychoterapie_common import TYP_AKCE
except ImportError:  # když se modul spustí samostatně
    from scrapers.lavka_common import ZDROJ, scrape_lavka
    from scrapers.psychoterapie_common import TYP_AKCE


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    return scrape_lavka(od, do)
