"""
Subscraper: Píčovinky z cozebar.cz

První zdroj Bobovy appkové kategorie "picovinky" — menší komunitní akcičky
(open mic, pub quiz, workshopy, slowdating…). Cože? je bar na Letné, který má
měsíčně pár takových akcí na jednostránkovém webu v sekci #eventy.

DŮLEŽITÁ ODCHYLKA OD OSTATNÍCH TYPŮ: picovinky nemají AI krok (žádný Cowork
prompt) — RAW soubor jde rovnou do data/ a čte ho appka. Proto:
  * datumy píšeme rovnou v appkovém formátu DD.MM.YYYY (tečky, ne pomlčky
    RAW kontraktu — appčin parsujDatum() umí jen tečky),
  * opakované akce ("Open mic/Jam" každý pátek) grupujeme podle názvu do
    jedné položky s polem `terminy` už tady (jako goout scrapery). Nejde jen
    o hezčí kartu: všechny akce sdílí stejné místo, takže generický dedup by
    stejnojmenné večery slil do jednoho a termíny navíc by ZAHODIL.

Server-side HTML, žádný JS → requests + BeautifulSoup. Jedna stránka, žádné
stránkování ani detaily. Struktura: <article class="event"> s .event__day
(den v týdnu — nepoužíváme, plyne z datumu), .event__time ("22. 7. od 19:30")
a .event__name (název).

Pasti zdroje:
  * datum je BEZ ROKU → rok se dopočítá tak, aby datum padlo do scrapovaného
    okna (co se do okna nevejde, se zahazuje — okno je zároveň filtr),
  * formát času občas ujede ("27. 6.00:00" bez " od "), čas 00:00 = neuvedeno,
  * popis akce web nemá — delší názvy ho ale mívají nacpaný v sobě za
    pomlčkou ("Slowdating - Tinder ani speed dating Ti nefungují? …"),
    tak ho heuristicky odsekneme do `popis`,
  * "ZAVŘENO: Privátní akce" není akce pro veřejnost → filtrujeme.
"""

import re
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

TYP_AKCE = "picovinky"
ZDROJ = "cozebar.cz"

# --- import společných helperů (funguje ať se spouští odkudkoli) ---
try:
    from ..common import polozka
except ImportError:  # když se modul spustí samostatně
    from common import polozka

BASE = "https://www.cozebar.cz/"
HEADERS = {"User-Agent": "Mozilla/5.0 (akce-scraper; osobni pouziti)"}

# místo je vždy stejné — je to web jednoho baru
MISTO = "Cože?"
ADRESA = "Malířská 227/14, Praha 7 — Letná"
URL_EVENTY = "https://www.cozebar.cz/#eventy"

# akce na webu vlastní obrázky nemají → všem dáme hero fotku baru, ať má karta
# stejný formát jako výstavy (16:9 box v appce si ji ořízne sám, na výšku nevadí)
THUMBNAIL = "https://www.cozebar.cz/assets/hero.jpg"

# názvy, které nejsou akce pro veřejnost (porovnává se bez velikosti písmen)
BLACKLIST = ("zavřeno", "privátní akce")

# od kolika znaků za pomlčkou bereme zbytek názvu jako popis — krátké přívěsky
# ("Dopisy našim předkům - Praha 7") jsou součást názvu, dlouhá souvětí popis
MIN_DELKA_POPISU = 30


def _rozdel_nazev(nazev):
    """Odsekne z dlouhého názvu popis za první pomlčkou (viz past v docstringu)."""
    m = re.split(r"\s[-–—]\s", nazev, maxsplit=1)
    if len(m) == 2 and len(m[1].strip()) >= MIN_DELKA_POPISU:
        return m[0].strip(), m[1].strip()
    return nazev, None


def _datum_v_okne(den, mesic, od, do):
    """
    Doplní roku zbavenému datumu rok tak, aby padlo do okna [od, do].
    Vrací date, nebo None když se do okna nevejde (= akci zahazujeme).
    Okno smí přetéct přes Silvestra, proto se zkouší oba krajní roky.
    """
    for rok in range(od.year, do.year + 1):
        try:
            d = date(rok, mesic, den)
        except ValueError:
            continue  # nesmyslné datum (31. 6.) — zkusíme další rok, stejně selže
        if od <= d <= do:
            return d
    return None


def _rozeber_cas(text):
    """
    Z ".event__time" ('22. 7. od 19:30') vytáhne (den, měsíc, čas|None).
    Vrací None, když v textu není ani datum. Toleruje rozbité formáty
    ('27. 6.00:00') a čas 00:00 bere jako neuvedený.
    """
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.", text or "")
    if not m:
        return None
    c = re.search(r"(\d{1,2}:\d{2})", (text or "")[m.end():])
    cas = c.group(1) if c else None
    if cas in ("0:00", "00:00"):
        cas = None
    return int(m.group(1)), int(m.group(2)), cas


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    okno_od = datetime.strptime(od, "%d-%m-%Y").date()
    okno_do = datetime.strptime(do, "%d-%m-%Y").date()

    r = requests.get(BASE, headers=HEADERS, timeout=20)
    s = BeautifulSoup(r.text, "html.parser")

    # posbíráme termíny seskupené podle názvu akce: {nazev: [(date, cas), …]}
    skupiny = {}  # dict drží pořadí prvního výskytu
    popisy = {}
    for event in s.select("article.event"):
        nazev_el = event.select_one(".event__name")
        cas_el = event.select_one(".event__time")
        nazev_cely = nazev_el.get_text(" ", strip=True) if nazev_el else None
        if not nazev_cely:
            continue
        if any(b in nazev_cely.lower() for b in BLACKLIST):
            continue

        rozebrano = _rozeber_cas(cas_el.get_text(" ", strip=True) if cas_el else "")
        if not rozebrano:
            continue  # bez datumu akci nemáme kam zařadit
        den, mesic, cas = rozebrano
        d = _datum_v_okne(den, mesic, okno_od, okno_do)
        if not d:
            continue  # mimo scrapované okno

        nazev, popis = _rozdel_nazev(nazev_cely)
        skupiny.setdefault(nazev, []).append((d, cas))
        if popis:
            popisy.setdefault(nazev, popis)

    polozky = []
    for nazev, terminy in skupiny.items():
        terminy.sort()
        prvni_datum, prvni_cas = terminy[0]
        p = polozka(
            ZDROJ,
            nazevCz=nazev,
            datumOd=prvni_datum.strftime("%d.%m.%Y"),
            datumDo=terminy[-1][0].strftime("%d.%m.%Y"),
            cas=prvni_cas,
            misto=MISTO,
            adresa=ADRESA,
            url=URL_EVENTY,
            thumbnail=THUMBNAIL,
            popis=popisy.get(nazev),
            # zanr/cena zdroj nedává → null
        )
        if len(terminy) > 1:
            # opakovaná akce → pole termínů pro popup „(N)" v appce
            p["terminy"] = [
                {"datum": d.strftime("%d.%m.%Y"), "cas": cas} for d, cas in terminy
            ]
        polozky.append(p)

    print(f"  [cozebar.cz/picovinky] {len(polozky)} akcí")
    return polozky
