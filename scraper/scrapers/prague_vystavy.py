"""
Subscraper: výstavy z prague.eu

Zdroj má krásně čitelné URL — datum i stránkování je přímo v adrese:
  https://prague.eu/cs/akce-kategorie/vystavy-expozice/?pg=1&start_date=DD-MM-YYYY&end_date=DD-MM-YYYY

Obsah je server-side rendered (žádný JS), takže stačí requests + BeautifulSoup.
Z výpisu bereme nazevCz, zanr, datum, url, thumbnail; pro adresu a popis
dojedeme ještě na detail každé akce.
"""

import time
import requests
from bs4 import BeautifulSoup

TYP_AKCE = "vystavy"
ZDROJ = "prague.eu"

# --- import společných helperů (funguje ať se spouští odkudkoli) ---
try:
    from ..common import polozka
except ImportError:  # když se modul spustí samostatně
    from common import polozka

BASE = "https://prague.eu/cs/akce-kategorie/vystavy-expozice/"
HEADERS = {"User-Agent": "Mozilla/5.0 (akce-scraper; osobni pouziti)"}
PAUZA = 0.5  # sekundy mezi requesty — buďme ke zdroji slušní


def _text(el):
    """Bezpečně vytáhne text z elementu, nebo None když element chybí."""
    return el.get_text(" ", strip=True) if el else None


def _thumbnail(tile):
    """Z <picture> vytáhne první rozumnou URL obrázku."""
    source = tile.find("source")
    if source and source.get("srcset"):
        # srcset je "url 1x, url 2x" — bereme první URL
        return source["srcset"].split()[0]
    img = tile.find("img")
    return img.get("src") if img else None


def _datumy(tile):
    """
    datumOd/Do z data-atributů karty.
    data-event_date = CSV konkrétních dnů (DD-MM-YYYY) spadajících do okna,
    data-limitedend = reálný konec akce.
    """
    dny = [d for d in (tile.get("data-event_date") or "").split(",") if d]
    od = min(dny) if dny else None  # pozn.: string min, ale formát DD-MM stačí pro RAW
    do = tile.get("data-limitedend") or (max(dny) if dny else None)
    return od, do


def _scrape_detail(session, url):
    """Z detailu akce vytáhne misto, adresu a popis. Chyby nezabíjí běh."""
    misto = adresa = popis = None
    try:
        r = session.get(url, headers=HEADERS, timeout=20)
        s = BeautifulSoup(r.text, "html.parser")

        # blok s místem a adresou: article-sidebar__event-places
        # první textový řádek = název místa, druhý = adresa
        box = s.find("div", class_="article-sidebar__event-places")
        if box:
            radky = [t.strip() for t in box.stripped_strings if t.strip()]
            if radky:
                misto = radky[0]
            if len(radky) > 1:
                adresa = radky[1]

        # popis: perex (hlavní odstavec)
        popis = _text(s.find("p", class_="perex"))
    except requests.RequestException:
        pass  # detail se nepovedl — necháme null, položku nezahazujeme
    return misto, adresa, popis


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    session = requests.Session()
    polozky = []
    videne = set()  # data-poid už zpracovaných akcí — ochrana proti smyčce
    pg = 1

    while True:
        params = {"pg": pg, "start_date": od, "end_date": do}
        r = session.get(BASE, params=params, headers=HEADERS, timeout=20)
        s = BeautifulSoup(r.text, "html.parser")
        # jen karty, které jsme ještě neviděli (prague.eu vrací pg=1 i pro pg=2…)
        tiles = [t for t in s.find_all("div", class_="tile-switching")
                 if t.get("data-poid") not in videne]
        if not tiles:
            break  # nic nového → konec (buď došly strany, nebo se opakují)

        for tile in tiles:
            videne.add(tile.get("data-poid"))
            odkaz = tile.find("figure").find("a") if tile.find("figure") else None
            url = odkaz["href"] if odkaz and odkaz.get("href") else None
            d_od, d_do = _datumy(tile)

            misto = adresa = popis = None
            if url:
                misto, adresa, popis = _scrape_detail(session, url)
                time.sleep(PAUZA)

            polozky.append(polozka(
                ZDROJ,
                nazevCz=_text(tile.find(["h2", "h3"])),
                zanr=_text(tile.find("span", class_="tile-switching__beforeHeading")),
                # misto z detailu je přesnější; fallback na afterHeading z výpisu
                misto=misto or _text(tile.find("span", class_="tile-switching__afterHeading")),
                adresa=adresa,
                datumOd=d_od,
                datumDo=d_do,
                url=url,
                thumbnail=_thumbnail(tile),
                popis=popis,
            ))

        print(f"  [prague.eu/vystavy] strana {pg}: {len(tiles)} akcí")
        pg += 1
        time.sleep(PAUZA)

    return polozky
