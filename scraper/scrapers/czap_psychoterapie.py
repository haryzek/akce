"""
Subscraper: odborné akce z czap.cz (Česká asociace pro psychoterapii)

ČAP jede na Wild Apricot (členský CMS). Stránka /Akce-CAP je server-side
rendered výpis nadcházejících akcí — žádné API, žádné stránkování, prostě
jeden seznam <li class="boxesListItem">. Wild Apricot má naštěstí sémantické
třídy, takže se nemusí hádat z textu:

  a.eventDetailsLink            → název + URL detailu
  .eventInfoStartDate .eventInfoBoxValue → datum od (DD/MM/YYYY);
                                  jednodenní akce mají label "When", vícedenní "Start"
  .eventInfoEndDate  .eventInfoBoxValue  → datum do (jen vícedenní)
  .eventInfoStartTime                    → čas ("18:00" nebo "18:00 - 19:30")
  .eventInfoLocation .eventInfoBoxValue  → místo (často "Zoom" = online)
  .gadgetEventEditableArea               → popis (plný text, ne zkrácený)

Bob z ČAP chce: kratší akce, kurzy, semináře i webináře. NE dlouhé výcviky
(poznají se délkou trvání — kurz přes měsíc a půl je program, ne akce) a NE
setkání členů / institutů (nevzdělávací provozní schůze — poznají se slovem
"setkání" v názvu; vzdělávací akce ČAP takhle nepojmenovává).
"""

import re
import requests
from bs4 import BeautifulSoup

try:
    from ..common import polozka
    from .psychoterapie_common import (
        TYP_AKCE, v_okne, je_vycvik, je_dlouhodoba, najdi_cas, odhadni_zanr,
    )
except ImportError:  # když se modul spustí samostatně
    from common import polozka
    from scrapers.psychoterapie_common import (
        TYP_AKCE, v_okne, je_vycvik, je_dlouhodoba, najdi_cas, odhadni_zanr,
    )

ZDROJ = "czap.cz"
BASE = "https://czap.cz/Akce-CAP"
HEADERS = {"User-Agent": "Mozilla/5.0 (akce-scraper; osobni pouziti)"}

_SETKANI = re.compile(r"setkání|setkani", re.I)


def _hodnota(el, trida):
    """Text .eventInfoBoxValue uvnitř elementu dané třídy, nebo None."""
    box = el.find(class_=trida)
    if not box:
        return None
    val = box.find(class_="eventInfoBoxValue")
    return val.get_text(" ", strip=True) if val else None


def _datum(text_ddmmyyyy):
    """"22/06/2026" → "22-06-2026" (RAW formát), nebo None."""
    if not text_ddmmyyyy:
        return None
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text_ddmmyyyy)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    r = requests.get(BASE, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    polozky = []
    vyrazeno = 0
    for li in s.find_all("li", class_="boxesListItem"):
        odkaz = li.find("a", class_="eventDetailsLink")
        nazev = odkaz.get_text(" ", strip=True) if odkaz else None
        if not nazev:
            continue

        d_od = _datum(_hodnota(li, "eventInfoStartDate"))
        d_do = _datum(_hodnota(li, "eventInfoEndDate")) or d_od

        # členské/provozní schůze a dlouhodobé výcviky nejsou Bobova jednorázovka
        if _SETKANI.search(nazev) or je_vycvik(nazev) or je_dlouhodoba(d_od, d_do):
            vyrazeno += 1
            continue
        if not v_okne(d_od, d_do, od, do):
            continue

        cas_el = li.find(class_="eventInfoStartTime")
        popis_el = li.find(class_="gadgetEventEditableArea")
        popis = popis_el.get_text(" ", strip=True) if popis_el else None

        polozky.append(polozka(
            ZDROJ,
            nazevCz=nazev,
            zanr=odhadni_zanr(nazev),
            datumOd=d_od,
            datumDo=d_do,
            cas=najdi_cas(cas_el.get_text(" ", strip=True) if cas_el else None),
            misto=_hodnota(li, "eventInfoLocation"),
            url=odkaz.get("href"),
            popis=popis,
        ))

    print(f"  [czap.cz] akcí: {len(polozky)}, vyřazeno (setkání/výcviky): {vyrazeno}")
    return polozky
