"""
Subscraper: události z psychoanalyza.cz (Česká psychoanalytická společnost)

Stejná mechanika jako cspap_psychoterapie.py — WordPress + The Events Calendar
REST API — takže si odtud půjčujeme stahování i převod eventu (stahni_tec,
preved_event) a měníme jen URL a filtr.

Filtr je tu důležitější než u ČSPP: kalendář ČPS je z většiny zaplněný
opakovanou výukou Psychoanalytického institutu ("Výuka PI ČPS: přednášky,
semináře" — klidně 11 termínů v jednom měsíci) a kurzy diagnostických metod
IKP ("KURZ IKP: TAT…", ROR, OPD). Obojí je výuka pro kandidáty ve výcviku,
ne jednorázová akce pro Boba — jeho zadání pro tenhle zdroj zní: klinické
semináře a přednášky ANO, výcvik a výuka NE.
"""

import re

try:
    from .cspap_psychoterapie import stahni_tec, preved_event, _cisty_text
    from .psychoterapie_common import TYP_AKCE, je_vycvik
except ImportError:  # když se modul spustí samostatně
    from scrapers.cspap_psychoterapie import stahni_tec, preved_event, _cisty_text
    from scrapers.psychoterapie_common import TYP_AKCE, je_vycvik

ZDROJ = "psychoanalyza.cz"
API = "https://www.psychoanalyza.cz/wp-json/tribe/events/v1/events"

# výuka institutu a metodické kurzy pro kandidáty = ne akce, ale škola
_VYUKA = re.compile(r"^výuka|^vyuka|^kurz ikp", re.I)
_UZAVRENA = re.compile(r"uzavřen|uzavren", re.I)


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    polozky = []
    vyrazeno = 0
    for event in stahni_tec(API, od, do, "psychoanalyza.cz"):
        nazev = _cisty_text(event.get("title")) or ""
        if _VYUKA.search(nazev) or _UZAVRENA.search(nazev) or je_vycvik(nazev):
            vyrazeno += 1
            continue
        polozky.append(preved_event(event, ZDROJ))
    if vyrazeno:
        print(f"  [psychoanalyza.cz] vyřazeno (výuka/kurzy IKP/uzavřené): {vyrazeno}")
    return polozky
