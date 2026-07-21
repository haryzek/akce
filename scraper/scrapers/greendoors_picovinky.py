"""
Subscraper: Píčovinky z greendoors.cz — Café Na půl cesty (JEN open mic)

Třetí zdroj typu "picovinky" (viz cozebar_picovinky.py — platí stejná odchylka:
typ nemá AI krok, RAW jde rovnou do data/, proto tečkové datumy DD.MM.YYYY
a grupování opakované akce do `terminy`).

Tenhle scraper je ATYP — je to "hlídač open miců": Café Na půl cesty (Green
Doors, Centrální park Pankrác) má v kulturním programu koncerty všeho druhu,
ale Boba z toho zajímá JEN open mic (občas ho pořádají, občas ne). Scraper
proto program filtruje na klíčová slova v NÁZVU a všechno ostatní zahazuje.
Nula nalezených akcí je normální stav, ne chyba — znamená to, že open mic
zrovna v programu není.

Očuchávání schválně JEN podle názvu, ne popisu: v popisech účinkujících se
běžně píše "písničkář, kterého můžete znát i z našich open miců" — match přes
popis by vysával koncerty, které s open micem nesouvisí. Klíčová slova se
porovnávají po normalizaci (bez diakritiky, jen písmena a číslice), takže
"Open mic" / "openmic" / "OPEN-MIC" / "otevřený mikrofon" chytne jeden klíč.

Server-side HTML (WordPress) → requests + BeautifulSoup. Program je v
section#program: <li> s .date (.day číslo + .month český název měsíce BEZ
ROKU → rok se dopočítá tak, aby datum padlo do scrapovaného okna), .grey čas,
<h4> název, <p> popis (ořezává se sponzorský boilerplate na konci) a odkaz
na detail. Akce vlastní obrázky nemají (detail má jen loga) → fix fotka
kavárny z galerie na landing page.
"""

import re
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

TYP_AKCE = "picovinky"
ZDROJ = "greendoors.cz"

# --- import společných helperů (funguje ať se spouští odkudkoli) ---
try:
    from ..common import polozka
except ImportError:  # když se modul spustí samostatně
    from common import polozka

BASE = "https://www.greendoors.cz/cs/landing_page/cafe-na-pul-cesty-3/"
HEADERS = {"User-Agent": "Mozilla/5.0 (akce-scraper; osobni pouziti)"}

MISTO = "Café Na půl cesty"
ADRESA = "Centrální park Pankrác, Praha 4"

# fix fotka kavárny z galerie na landing page (akce vlastní obrázky nemají)
THUMBNAIL = "https://www.greendoors.cz/wp-content/uploads/2016/01/cafe-davidveres0070-800x600.jpg"

# klíčová slova open micu — porovnává se s názvem po _normalizuj() (bez
# diakritiky, bez mezer/pomlček), takže pokrývají všechny varianty zápisu.
# Příbuzný druh open micu = přidat klíč sem.
KLICE_OPEN_MIC = ("openmic", "openstage", "otevrenymikrofon")

# sponzorský boilerplate na konci popisů — od tohohle textu dál se popis ořízne
BOILERPLATE = re.compile(r"Koncerty a akce v Café Na Půl Cesty.*", re.S | re.I)

MESICE_CZ = {
    "leden": 1, "únor": 2, "březen": 3, "duben": 4, "květen": 5, "červen": 6,
    "červenec": 7, "srpen": 8, "září": 9, "říjen": 10, "listopad": 11,
    "prosinec": 12,
}


def _normalizuj(s):
    """malá písmena, bez diakritiky, jen písmena a číslice (i bez mezer)."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return "".join(c for c in s if c.isalnum())


def _je_open_mic(nazev):
    n = _normalizuj(nazev)
    return any(k in n for k in KLICE_OPEN_MIC)


def _datum_v_okne(den, mesic, od, do):
    """Doplní rok tak, aby datum padlo do okna [od, do]; jinak None (= zahodit)."""
    for rok in range(od.year, do.year + 1):
        try:
            d = date(rok, mesic, den)
        except ValueError:
            continue
        if od <= d <= do:
            return d
    return None


def _popis(p_el):
    """Popis z <p> — sloučené řádky, bez sponzorského boilerplate, nebo None."""
    if not p_el:
        return None
    text = p_el.get_text(" ", strip=True)
    text = BOILERPLATE.sub("", text).strip(" -–\n")
    return text or None


def _cena(popis):
    """'vstupné dobrovolné' nebo částka v Kč z popisu, jinak None."""
    if not popis:
        return None
    m = re.search(r"\d[\d ]*\s*Kč", popis)
    if m:
        return m.group(0)
    if re.search(r"vstupné\s+dobrovolné", popis, re.I):
        return "vstupné dobrovolné"
    return None


def _parsuj_program(s, okno_od, okno_do):
    """Ze soup vytáhne open mic akce programu jako skupiny {nazev: {...}}."""
    skupiny = {}  # {nazev: {"terminy": [(date, cas)], "popis": …, "url": …}}
    program = s.find(id="program")
    if not program:
        return skupiny

    for li in program.select(".program_table li"):
        nazev_el = li.find("h4")
        nazev = nazev_el.get_text(" ", strip=True) if nazev_el else None
        if not nazev or not _je_open_mic(nazev):
            continue  # není open mic — jediný důvod existence tohohle scraperu

        den_el, mesic_el = li.select_one(".date .day"), li.select_one(".date .month")
        try:
            den = int(den_el.get_text(strip=True))
            mesic = MESICE_CZ[mesic_el.get_text(strip=True).lower()]
        except (AttributeError, KeyError, ValueError):
            continue  # bez čitelného datumu akci nezařadíme
        d = _datum_v_okne(den, mesic, okno_od, okno_do)
        if not d:
            continue  # mimo scrapované okno

        cas_el = li.select_one(".text .grey")
        cas = cas_el.get_text(strip=True) if cas_el else None
        cas = cas if re.fullmatch(r"\d{1,2}:\d{2}", cas or "") else None

        odkaz = li.find("a", class_="block_a")
        skupina = skupiny.setdefault(nazev, {"terminy": [], "popis": None, "url": None})
        skupina["terminy"].append((d, cas))
        if not skupina["popis"]:
            skupina["popis"] = _popis(li.select_one(".text p"))
        if not skupina["url"] and odkaz and odkaz.get("href"):
            skupina["url"] = odkaz["href"]

    return skupiny


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    okno_od = datetime.strptime(od, "%d-%m-%Y").date()
    okno_do = datetime.strptime(do, "%d-%m-%Y").date()

    r = requests.get(BASE, headers=HEADERS, timeout=20)
    s = BeautifulSoup(r.text, "html.parser")
    skupiny = _parsuj_program(s, okno_od, okno_do)

    polozky = []
    for nazev, sk in skupiny.items():
        terminy = sorted(sk["terminy"])
        p = polozka(
            ZDROJ,
            nazevCz=nazev,
            datumOd=terminy[0][0].strftime("%d.%m.%Y"),
            datumDo=terminy[-1][0].strftime("%d.%m.%Y"),
            cas=terminy[0][1],
            misto=MISTO,
            adresa=ADRESA,
            url=sk["url"] or BASE,
            cena=_cena(sk["popis"]),
            thumbnail=THUMBNAIL,
            popis=sk["popis"],
        )
        if len(terminy) > 1:
            p["terminy"] = [
                {"datum": d.strftime("%d.%m.%Y"), "cas": c} for d, c in terminy
            ]
        polozky.append(p)

    # nula akcí = open mic zrovna není v programu, normální stav (viz docstring)
    print(f"  [greendoors.cz/picovinky] {len(polozky)} akcí (open mic filtr)")
    return polozky
