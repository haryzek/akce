"""
Subscraper: Píčovinky z thirdcoastpizza.cz (Under the Sauce Pub Quiz)

Druhý zdroj typu "picovinky" (viz cozebar_picovinky.py — platí stejná odchylka:
typ nemá AI krok, RAW jde rovnou do data/, proto tečkové datumy DD.MM.YYYY
a grupování opakované akce do `terminy` už tady).

Third Coast Pizza (Žižkov) má na webu stránku svého týdenního pub kvízu se
sekcí "Upcoming Dates" — je to jedna akce pořád dokola (každou středu), ale
Bob ji chce vidět v appce, protože občas mají pauzu/prázdniny a termíny se
mění. Občas je speciální edice s jiným názvem ("Under the Rainbow Pub Quiz")
→ grupuje se podle názvu, takže edice dostane vlastní kartu.

Server-side HTML (Next.js SSR) → requests + BeautifulSoup. Termín = <a> karta
s <h3> názvem, <p> anglickým datem ("Wednesday, 22 July 2026" — s rokem,
žádné dopočítávání) a <p> časem ("19:00 – 21:30" → bereme začátek).

Obrázek: og:image vede na S3 s podepsanou URL (X-Amz-Signature — expiruje!),
ale bucket je veřejný a bez query stringu vrací 200 → podpis se uřízne.

Popis se schválně nescrapuje (na webu je jen anglický marketing) — nechává se
null a appka ho doplní Bobovým fix textem podle druhu akce (DRUHY_PICOVINEK
v app.js; "quiz" v názvu → kvízový text). Cena se loví regexem z textu
stránky ("100 Kč entry"), ať se sama aktualizuje, když zdraží.
"""

import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

TYP_AKCE = "picovinky"
ZDROJ = "thirdcoastpizza.cz"

# --- import společných helperů (funguje ať se spouští odkudkoli) ---
try:
    from ..common import polozka
except ImportError:  # když se modul spustí samostatně
    from common import polozka

BASE = "https://www.thirdcoastpizza.cz/en/events/under-the-sauce-pub-quiz"
HEADERS = {"User-Agent": "Mozilla/5.0 (akce-scraper; osobni pouziti)"}

MISTO = "Third Coast Pizza"
ADRESA = "Chvalova 1, Praha 3 — Žižkov"

MESICE_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


def _datum(text):
    """'Wednesday, 22 July 2026' -> date, nebo None. Den v týdnu ignorujeme."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text or "")
    if not m:
        return None
    mesic = MESICE_EN.get(m.group(2).lower())
    if not mesic:
        return None
    try:
        return datetime(int(m.group(3)), mesic, int(m.group(1))).date()
    except ValueError:
        return None


def _cena(s):
    """Cena z textu stránky ('100 Kč entry') — první částka v Kč, jinak None."""
    m = re.search(r"(\d[\d\s]*)\s*Kč", s.get_text(" ", strip=True))
    return f"{m.group(1).strip()} Kč" if m else None


def _thumbnail(s):
    """og:image bez podpisového query stringu (podepsaná URL by expirovala)."""
    meta = s.find("meta", property="og:image")
    return meta["content"].split("?")[0] if meta and meta.get("content") else None


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    okno_od = datetime.strptime(od, "%d-%m-%Y").date()
    okno_do = datetime.strptime(do, "%d-%m-%Y").date()

    r = requests.get(BASE, headers=HEADERS, timeout=20)
    s = BeautifulSoup(r.text, "html.parser")

    cena = _cena(s)
    thumbnail = _thumbnail(s)

    # termíny = <a> karty odkazující na detail termínu (BASE + "/<id>");
    # grupujeme podle názvu, ať speciální edice dostane vlastní kartu
    skupiny = {}  # {nazev: [(date, cas), …]}, drží pořadí prvního výskytu
    for a in s.select('a[href*="/events/under-the-sauce-pub-quiz/"]'):
        nazev_el = a.find("h3")
        if not nazev_el:
            continue
        nazev = nazev_el.get_text(" ", strip=True)
        text = a.get_text(" ", strip=True)
        d = _datum(text)
        if not d or not (okno_od <= d <= okno_do):
            continue  # bez data / mimo scrapované okno
        c = re.search(r"(\d{1,2}:\d{2})", text)  # "19:00 – 21:30" → začátek
        skupiny.setdefault(nazev, []).append((d, c.group(1) if c else None))

    polozky = []
    for nazev, terminy in skupiny.items():
        terminy.sort()
        p = polozka(
            ZDROJ,
            nazevCz=nazev,
            datumOd=terminy[0][0].strftime("%d.%m.%Y"),
            datumDo=terminy[-1][0].strftime("%d.%m.%Y"),
            cas=terminy[0][1],
            misto=MISTO,
            adresa=ADRESA,
            url=BASE,
            cena=cena,
            thumbnail=thumbnail,
            # popis schválně null → doplní appka fix textem (viz docstring)
        )
        if len(terminy) > 1:
            p["terminy"] = [
                {"datum": d.strftime("%d.%m.%Y"), "cas": c} for d, c in terminy
            ]
        polozky.append(p)

    print(f"  [thirdcoastpizza.cz/picovinky] {len(polozky)} akcí")
    return polozky
