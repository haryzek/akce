"""
Subscraper: odborné akce z psychoterapeuti.cz (Česká psychoterapeutická společnost ČLS JEP)

Joomla blog — stránka /pro-odborniky/odborne-akce-spolecnosti je výpis článků
(div.blog-item), kde jeden článek = jedna akce, ale VŠECHNO je volný text bez
struktury ("Datum: Pátek 16. 10. 2026 od 10:00…", "Místo konání: Lékařský
dům…"). Mezi articles se navíc pletou i ne-akce (odkazy na věstníky apod.).

Postup: z výpisu vezmeme jen články, jejichž text obsahuje datum, dojedeme na
detail pro plný text a pak regexy lovíme: datumy (najdi_datumy — titulek mívá
datum taky), čas, místo (řádek za "Místo konání:"), přednášející → autor,
cena (částky v Kč z řádku "Platba…"). Popis = plný text článku; učesat ho na
kartu je práce Cowork promptu, ne scraperu.

Akcí tu bývá jednotkově (2-4), takže detaily nebolí.
"""

import re
import time

import requests
from bs4 import BeautifulSoup

try:
    from ..common import polozka
    from .psychoterapie_common import (
        TYP_AKCE, v_okne, je_vycvik, najdi_datumy, najdi_cas, odhadni_zanr,
    )
except ImportError:  # když se modul spustí samostatně
    from common import polozka
    from scrapers.psychoterapie_common import (
        TYP_AKCE, v_okne, je_vycvik, najdi_datumy, najdi_cas, odhadni_zanr,
    )

ZDROJ = "psychoterapeuti.cz"
WEB = "https://www.psychoterapeuti.cz"
BASE = WEB + "/pro-odborniky/odborne-akce-spolecnosti"
HEADERS = {"User-Agent": "Mozilla/5.0 (akce-scraper; osobni pouziti)"}
PAUZA = 0.5


def _za_labelem(text, label,
                stop=r"(?:Pořadatel|O přednáše|Přednášející|Platba|Storno|Přihlášky|Čas|Téma|Program|$)"):
    """Vytáhne úsek textu mezi labelem (např. "Místo konání:") a další sekcí."""
    m = re.search(label + r"\s*:?\s*(.+?)\s*" + stop, text, re.S)
    if not m:
        return None
    kus = re.sub(r"\s+", " ", m.group(1)).strip(" .,;")
    return kus or None


def _cena(text):
    """Částky v Kč z řádku o platbě → "400 / 600 Kč". Bez částek → None."""
    okoli = _za_labelem(text, r"Platba[^:]*", stop=r"(?:Storno|Přihlášky|Přednášející|$)") or text
    castky = re.findall(r"(\d[\d\s]*)\s*,?-?\s*Kč", okoli)
    cisla = []
    for c in castky:
        c = re.sub(r"\s", "", c)
        if c and c not in cisla:
            cisla.append(c)
    if not cisla:
        return None
    return " / ".join(cisla[:2]) + " Kč"


def _detail_text(session, url):
    """Plný text článku z detailu (div.item-page), nebo None."""
    try:
        r = session.get(url, headers=HEADERS, timeout=20)
        s = BeautifulSoup(r.text, "html.parser")
        clanek = s.find(class_="item-page") or s.find("main")
        return clanek.get_text("\n", strip=True) if clanek else None
    except requests.RequestException:
        return None


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    session = requests.Session()
    r = session.get(BASE, headers=HEADERS, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")

    polozky = []
    for bi in s.find_all("div", class_="blog-item"):
        nadpis = bi.find(["h1", "h2", "h3"])
        odkaz = nadpis.find("a") if nadpis else None
        nazev = nadpis.get_text(" ", strip=True) if nadpis else None
        if not nazev or not odkaz or not odkaz.get("href"):
            continue
        # článek bez datumu v textu není akce (věstníky, trvalé informace)
        if not najdi_datumy(bi.get_text(" ", strip=True)):
            continue
        if je_vycvik(nazev):
            continue

        url = odkaz["href"]
        if url.startswith("/"):
            url = WEB + url
        text = _detail_text(session, url) or bi.get_text("\n", strip=True)
        time.sleep(PAUZA)

        # titulek mívá datum konání v sobě ("Vědecká schůze … 16. 10. 2026") —
        # ten má přednost; jinak první datum z textu (další bývají storno lhůty)
        datumy = najdi_datumy(nazev) or najdi_datumy(
            _za_labelem(text, r"(?:Datum|Termín(?:\s+konání)?)") or text)
        d_od = datumy[0] if datumy else None
        d_do = datumy[-1] if datumy else d_od
        if not v_okne(d_od, d_do, od, do):
            continue

        polozky.append(polozka(
            ZDROJ,
            # z titulku pryč datum na konci ("… 16. 10. 2026"), na kartě by strašilo dvakrát
            nazevCz=re.sub(r"\s*\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*$", "", nazev),
            # jen jména — medailonky za "O přednášejících" utne stop ve výchozím vzoru
            autor=_za_labelem(text, r"Přednášející"),
            zanr=odhadni_zanr(nazev),
            datumOd=d_od,
            datumDo=d_do,
            cas=najdi_cas(_za_labelem(text, r"Čas(?:\s+konání)?") or
                          _za_labelem(text, r"(?:Datum|Termín(?:\s+konání)?)") or ""),
            misto=_za_labelem(text, r"Místo\s*(?:konání)?"),
            url=url,
            cena=_cena(text),
            popis=re.sub(r"\s+", " ", text)[:1500] if text else None,
        ))

    print(f"  [psychoterapeuti.cz] akcí: {len(polozky)}")
    return polozky
