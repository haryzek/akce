"""
Subscraper: akce z akpcr.cz (Asociace klinických psychologů ČR)

Web je Google Sites — server-side HTML, ale s generovanými třídami (zfr3Q…),
na které se nedá spolehnout. Co se dá: každá akce bydlí ve vlastním <section>
s <h2> nadpisem. Iterujeme sekce a za akci bereme tu, která má nadpis a v
textu datum.

Dvě pasti Google Sites:
1. Datum bývá rozlámané přes několik <span>ů ("2 . 12 .20 26") — najdi_datumy
   ve sdíleném modulu proto toleruje mezery kdekoli uvnitř datumu.
2. Pole jsou jen konvence textu: popis je mezi datumem a "Místo konání:",
   místo mezi "Místo konání:" a "Pořadatel", pořadatel za "Pořadatel". Odkaz
   "Webové stránky" v sekci vede na web akce (bereme jako url; vlastní detail
   na AKP webu akce nemají).

AKP publikuje akce třetích stran vč. výcviků — je_vycvik() je čistí už tady
("Komplexní výcvik CWS", "Supervizní výcvik…"). Řádek "Vloženo: DD.MM.YYYY"
na konci sekce je datum publikace, ne konání — před lovem datumů ho odřízneme.
"""

import re

import requests
from bs4 import BeautifulSoup

try:
    from ..common import polozka
    from .psychoterapie_common import (
        TYP_AKCE, v_okne, je_vycvik, je_dlouhodoba,
        najdi_datumy, najdi_cas, odhadni_zanr,
    )
except ImportError:  # když se modul spustí samostatně
    from common import polozka
    from scrapers.psychoterapie_common import (
        TYP_AKCE, v_okne, je_vycvik, je_dlouhodoba,
        najdi_datumy, najdi_cas, odhadni_zanr,
    )

ZDROJ = "akpcr.cz"
BASE = "https://www.akpcr.cz/pro-odbornou-ve%C5%99ejnost/akce"
HEADERS = {"User-Agent": "Mozilla/5.0 (akce-scraper; osobni pouziti)"}


def _usek(text, start, konec):
    """Úsek textu mezi dvěma značkami (konec = regex), učesaný na jeden řádek."""
    m = re.search(re.escape(start) + r"\s*:?\s*(.+?)\s*(?:" + konec + r"|$)", text, re.S)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip(" .,;") or None


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    r = requests.get(BASE, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    polozky = []
    vyrazeno = 0
    for sekce in s.find_all("section"):
        nadpis = sekce.find("h2")
        if not nadpis:
            continue
        nazev = re.sub(r"\s+", " ", nadpis.get_text(" ", strip=True)).strip()
        text = re.sub(r"\s+", " ", sekce.get_text(" ", strip=True))
        # "Vloženo: …" je datum publikace příspěvku — ať se nám neplete mezi termíny
        text = re.split(r"Vloženo\s*:", text)[0]

        datumy = najdi_datumy(text)
        if not nazev or not datumy:
            continue  # sekce bez nadpisu nebo datumu není akce (úvod, patička…)
        if je_vycvik(nazev):
            vyrazeno += 1
            continue

        d_od, d_do = datumy[0], datumy[-1]
        if je_dlouhodoba(d_od, d_do):
            vyrazeno += 1
            continue
        if not v_okne(d_od, d_do, od, do):
            continue

        # odkaz "Webové stránky" → web akce (leták přeskakujeme, bývá PDF/JPG)
        url = None
        for a in sekce.find_all("a", href=True):
            if "webov" in a.get_text(" ", strip=True).lower():
                url = a["href"]
                break

        # popis = text mezi nadpisem/datumem a "Místo konání" (datum z něj uřízneme)
        popis = _usek(text, nazev, r"Místo konání")
        if popis:
            popis = re.sub(r"^[\d\s.]+", "", popis).strip() or None

        polozky.append(polozka(
            ZDROJ,
            nazevCz=nazev,
            autor=_usek(text, "Pořadatel", r"Kontakt|Webové|Letáček"),
            zanr=odhadni_zanr(nazev + " " + (popis or "")),
            datumOd=d_od,
            datumDo=d_do,
            cas=najdi_cas(popis),
            misto=_usek(text, "Místo konání", r"Pořadatel|Kontakt"),
            url=url,
            popis=popis,
        ))

    print(f"  [akpcr.cz] akcí: {len(polozky)}, vyřazeno (výcviky/dlouhodobé): {vyrazeno}")
    return polozky
