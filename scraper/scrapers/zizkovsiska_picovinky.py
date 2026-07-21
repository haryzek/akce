"""
Subscraper: Píčovinky z zizkovsiska.cz (Open Mic Tuesday)

Čtvrtý zdroj typu "picovinky" (viz cozebar_picovinky.py — platí stejná
odchylka: typ nemá AI krok, RAW jde rovnou do data/, proto tečkové datumy
DD.MM.YYYY a `terminy`).

Druhý ATYP vedle greendoors: Žižkovšiška má open mic KAŽDÉ úterý od 20:00,
ale stránka je statická vizitka bez seznamu termínů (Wix). Scraper proto
termíny NEparsuje, ale GENERUJE — všechna úterý ve scrapovaném okně — a dělá
jen "existenční kontrolu": (1) stránka vrací 200, (2) v textu se pořád mluví
o open micu a úterku (guard proti tomu, kdyby URL někdy začala vést na něco
jiného). Když kontrola neprojde, vrátí 0 akcí a akce z appky sama zmizí —
přesně jak Bob chce ("stabilně každé úterý, dokud stránka existuje").

Popis se schválně nechává null (na webu je jen anglický marketing) → doplní
ho appka Bobovým fix textem podle druhu ("openmic" → "Čapni kytaru, oslíku…").
Thumbnail se bere živě z og:image (wixstatic CDN, veřejná stabilní URL).
"""

import re
import unicodedata
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

TYP_AKCE = "picovinky"
ZDROJ = "zizkovsiska.cz"

# --- import společných helperů (funguje ať se spouští odkudkoli) ---
try:
    from ..common import polozka
except ImportError:  # když se modul spustí samostatně
    from common import polozka

BASE = "https://www.zizkovsiska.cz/open-mic-tuesday-jam-session-prague"
HEADERS = {"User-Agent": "Mozilla/5.0 (akce-scraper; osobni pouziti)"}

NAZEV = "Open Mic Tuesday"  # fixní — v názvu musí zůstat "open mic" kvůli
#                             očuchávadlu skóre/popisu v appce (DRUHY_PICOVINEK)
MISTO = "Žižkovšiška"
ADRESA = "Husitská 888/11, Praha 3 — Žižkov"
CAS = "20:00"  # every Tuesday from 8pm (z textu stránky, 12 slotů do půlnoci)
UTERY = 1  # date.weekday() úterka


def _normalizuj(s):
    """malá písmena, bez diakritiky, jen písmena a číslice — na guard kontrolu."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return "".join(c for c in s if c.isalnum())


def _stranka_zije(r, s):
    """Existenční kontrola: 200 + na stránce se pořád mluví o open micu v úterý."""
    if r.status_code != 200:
        return False
    text = _normalizuj(s.get_text(" ", strip=True))
    return "openmic" in text and ("tuesday" in text or "utery" in text)


def _thumbnail(s):
    meta = s.find("meta", property="og:image")
    return meta["content"] if meta and meta.get("content") else None


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    okno_od = datetime.strptime(od, "%d-%m-%Y").date()
    okno_do = datetime.strptime(do, "%d-%m-%Y").date()

    try:
        r = requests.get(BASE, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        # síť/DNS spadly — nevíme, jestli stránka žije, radši 0 akcí než lhát
        print(f"  [zizkovsiska.cz/picovinky] stránka nedostupná ({e}) -> 0 akcí")
        return []
    s = BeautifulSoup(r.text, "html.parser")

    if not _stranka_zije(r, s):
        print("  [zizkovsiska.cz/picovinky] stránka neexistuje nebo už není o open micu -> 0 akcí")
        return []

    # všechna úterý ve scrapovaném okně (termíny se negenerují z dat stránky —
    # stránka žádná nemá, akce prostě JE každé úterý)
    prvni = okno_od + timedelta(days=(UTERY - okno_od.weekday()) % 7)
    uterky = []
    d = prvni
    while d <= okno_do:
        uterky.append(d)
        d += timedelta(days=7)
    if not uterky:
        return []  # okno kratší než týden bez úterka

    p = polozka(
        ZDROJ,
        nazevCz=NAZEV,
        datumOd=uterky[0].strftime("%d.%m.%Y"),
        datumDo=uterky[-1].strftime("%d.%m.%Y"),
        cas=CAS,
        misto=MISTO,
        adresa=ADRESA,
        url=BASE,
        thumbnail=_thumbnail(s),
        # popis schválně null → doplní appka fix textem podle druhu (viz docstring)
    )
    if len(uterky) > 1:
        p["terminy"] = [{"datum": u.strftime("%d.%m.%Y"), "cas": CAS} for u in uterky]

    print(f"  [zizkovsiska.cz/picovinky] 1 akce ({len(uterky)} úterků v okně)")
    return [p]
