"""
Subscraper: akce z centrum-lavka.cz pro typ "verejnost_psychoterapie"
(psychoterapeutické akce pro veřejnost — sebezkušenostní kurzy a skupiny:
mindfulness, jungovské víkendy, focusing, práce se smrtí…).

Tenká obálka nad lavka_common.py (viz jeho docstring — tam žije celá mechanika
i pasti). Vrací KOMPLETNÍ seznam akcí Lávky — stejný dostává i sesterská obálka
lavka_psychoterapie.py; díky cache v lavka_common se web leze jen jednou.
Odborné vs. pro veřejnost rozdělují až Cowork prompty (přísně vylučovací,
hraniční akce → veřejnost).
"""

try:
    from .lavka_common import ZDROJ, scrape_lavka
except ImportError:  # když se modul spustí samostatně
    from scrapers.lavka_common import ZDROJ, scrape_lavka

TYP_AKCE = "verejnost_psychoterapie"


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    return scrape_lavka(od, do)
