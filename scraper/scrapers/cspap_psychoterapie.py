"""
Subscraper: odborné akce z cspap.cz (Česká společnost pro psychoanalytickou psychoterapii)

Web je WordPress s pluginem The Events Calendar — a ten má veřejné REST API,
takže se neškrábe HTML, ale volá rovnou:

  https://cspap.cz/wp-json/tribe/events/v1/events
      ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&per_page=50&page=N

Datumový filtr je serverový (start_date/end_date), stránkuje se přes `page`
a `total_pages` v odpovědi. Event nese title/description v HTML (entity typu
&#8211; a tagy — čistíme přes html.unescape + BeautifulSoup), start_date
"2026-09-03 19:30:00" (lokální čas), venue objekt s adresou, cost, image.

Filtr navíc: ČSPP vede v kalendáři i interní akce s "UZAVŘENÁ AKCE" v názvu
(supervizní semináře jen pro členy a kandidáty ČSPAP) — na ty se Bob nedostane,
ven s nimi už tady.
"""

import html as html_mod
import re
import time

import requests
from bs4 import BeautifulSoup

try:
    from ..common import polozka
    from .psychoterapie_common import TYP_AKCE, je_vycvik, odhadni_zanr
except ImportError:  # když se modul spustí samostatně
    from common import polozka
    from scrapers.psychoterapie_common import TYP_AKCE, je_vycvik, odhadni_zanr

ZDROJ = "cspap.cz"
API = "https://cspap.cz/wp-json/tribe/events/v1/events"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept": "application/json",
}
PAUZA = 0.5
MAX_STRAN = 10

# interní akce jen pro členy — Bob se na ně nepřihlásí
_UZAVRENA = re.compile(r"uzavřen|uzavren", re.I)


def _iso(ddmmyyyy):
    """"18-07-2026" → "2026-07-18" pro API parametry."""
    d, m, r = ddmmyyyy.split("-")
    return f"{r}-{m}-{d}"


def _datum(tec_datum):
    """"2026-09-03 19:30:00" → ("03-09-2026", "19:30"). Chybějící → (None, None)."""
    if not tec_datum or " " not in tec_datum:
        return None, None
    den, cas = tec_datum.split(" ", 1)
    r, m, d = den.split("-")
    return f"{d}-{m}-{r}", cas[:5]


def _cisty_text(html_text):
    """HTML popis z TEC → čistý text (entity, tagy, zalomení pryč)."""
    if not html_text:
        return None
    return BeautifulSoup(html_mod.unescape(html_text), "html.parser").get_text(" ", strip=True) or None


def _misto(event):
    """venue objekt → (název místa, adresa). TEC venue má address/city zvlášť."""
    venue = event.get("venue")
    if not isinstance(venue, dict):
        return None, None
    kusy = [venue.get("address"), venue.get("city")]
    adresa = ", ".join(k for k in kusy if k) or None
    return venue.get("venue"), adresa


def _thumbnail(event):
    """image je buď objekt s url, nebo string "False" — TEC API je svérázné."""
    img = event.get("image")
    return img.get("url") if isinstance(img, dict) else None


def _autor(event):
    """Jméno prvního organizátora, když ho TEC nese (bývá to institut/sekce)."""
    org = event.get("organizer")
    if isinstance(org, list) and org and isinstance(org[0], dict):
        return _cisty_text(org[0].get("organizer"))
    return None


def stahni_tec(api_url, od, do, log_prefix):
    """Projede stránky TEC API v okně od–do a vrátí list eventů (sdílí ČSPP i ČSP)."""
    eventy = []
    for strana in range(1, MAX_STRAN + 1):
        r = requests.get(api_url, params={
            "start_date": _iso(od), "end_date": _iso(do),
            "per_page": 50, "page": strana,
        }, headers=HEADERS, timeout=25)
        # TEC vrací 404 pro stránku za koncem — to je regulérní konec, ne chyba
        if r.status_code == 404:
            break
        r.raise_for_status()
        j = r.json()
        eventy.extend(j.get("events") or [])
        print(f"  [{log_prefix}] strana {strana}: {len(j.get('events') or [])} akcí")
        if strana >= (j.get("total_pages") or 1):
            break
        time.sleep(PAUZA)
    return eventy


def preved_event(event, zdroj):
    """Jeden TEC event → RAW položka (sdílené jádro pro ČSPP i ČSP)."""
    nazev = _cisty_text(event.get("title"))
    d_od, cas = _datum(event.get("start_date"))
    d_do, _ = _datum(event.get("end_date"))
    misto, adresa = _misto(event)
    return polozka(
        zdroj,
        nazevCz=nazev,
        autor=_autor(event),
        zanr=odhadni_zanr(nazev),
        datumOd=d_od,
        datumDo=d_do,
        cas=cas,
        misto=misto,
        adresa=adresa,
        url=event.get("url"),
        cena=_cisty_text(event.get("cost")),
        thumbnail=_thumbnail(event),
        popis=_cisty_text(event.get("description")),
    )


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    polozky = []
    vyrazeno = 0
    for event in stahni_tec(API, od, do, "cspap.cz"):
        nazev = _cisty_text(event.get("title")) or ""
        if _UZAVRENA.search(nazev) or je_vycvik(nazev):
            vyrazeno += 1
            continue
        polozky.append(preved_event(event, ZDROJ))
    if vyrazeno:
        print(f"  [cspap.cz] vyřazeno (uzavřené/výcviky): {vyrazeno}")
    return polozky
