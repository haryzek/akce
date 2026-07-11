"""
Subscraper: Jazz & Blues (klubová scéna) z prague.eu

První zdroj pro Bobovu appkovou kategorii "koncerty_jazzblues" (Jazz&Blues).
prague.eu nemá kategorii přímo takhle pojmenovanou — nejblíž tomu, co Bob do
téhle škatulky sype (jazz, soul, blues, swing…), je jejich "klubová scéna",
tak tahá odsud. Časem přibudou další zdroje z jinak pojmenovaných kategorií;
runner je slévá do jednoho souboru pod stejný TYP_AKCE.

Struktura je 1:1 klon prague_koncerty.py (klasika) — koncertní tvar dat je
stejný (jednorázová akce nebo víc termínů, žádná veřejná hodnocení, thumbnail),
liší se jen URL kategorie a slug typu. URL nese datum i stránkování:
  https://prague.eu/cs/akce-kategorie/klubova-scena/?pg=1&start_date=DD-MM-YYYY&end_date=DD-MM-YYYY

Server-side HTML, žádný JS → requests + BeautifulSoup. Pozn.: prague.eu vrací
pořád stejnou stránku (pg=2 == pg=1), takže reálné stránkování nefunguje a
anti-loop přes data-poid se zastaví hned po první straně — ale kdyby zdroj někdy
začal stránkovat, tahle smyčka to projede automaticky.

Čas a cena: prague.eu je pro tyhle koncerty nedodává strojově čitelně (žádný
Event schema, v textu nekonzistentní), proto je scraper nechává null. Když jsou
v popisu explicitně, dolije je až AI krok (cowork_prompt_koncerty_jazzblues.md).
"""

import json
import time
import requests
from bs4 import BeautifulSoup

TYP_AKCE = "koncerty_jazzblues"
ZDROJ = "prague.eu"

# --- import společných helperů (funguje ať se spouští odkudkoli) ---
try:
    from ..common import polozka
except ImportError:  # když se modul spustí samostatně
    from common import polozka

BASE = "https://prague.eu/cs/akce-kategorie/klubova-scena/"
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


def _casova_mapa(s):
    """
    Z detailu vytáhne mapu {datum "DD-MM-YYYY": čas "HH:MM"} z atributu data-date_list.

    prague.eu drží všechny termíny akce v JSONu na <span data-date_list='[[{...}]]'>
    (start ve tvaru "DD/MM/YYYY HH:MM"). Čas "00:00" znamená "nezadáno" → přeskočíme,
    ať appce necpeme falešnou půlnoc. Struktura je list skupin, každá skupina list slotů.
    """
    span = s.find(attrs={"data-date_list": True})
    if not span:
        return {}
    try:
        skupiny = json.loads(span["data-date_list"])
    except (ValueError, KeyError, TypeError):
        return {}

    mapa = {}
    for skupina in skupiny:
        for slot in skupina:
            start = (slot.get("start") or "").split(" ")
            if len(start) < 2:
                continue
            datum = start[0].replace("/", "-")  # "15/06/2026" -> "15-06-2026"
            cas = start[1]
            if cas == "00:00":  # placeholder pro "čas neuveden"
                continue
            mapa.setdefault(datum, cas)  # první čas pro daný den stačí
    return mapa


def _vyber_cas(casova_mapa, datum_od):
    """Čas pro náš termín: přesná shoda s datem akce, jinak jediný čas (když je shodný)."""
    if not casova_mapa:
        return None
    if datum_od and datum_od in casova_mapa:
        return casova_mapa[datum_od]
    casy = set(casova_mapa.values())
    return casy.pop() if len(casy) == 1 else None  # jednoznačné jen když je čas jediný


MAX_TERMINY = 10  # strop na počet termínů — rezidenční kapely a jam session hrají klidně
#                   každý večer a nagenerují stovky termínů, což nafoukne RAW soubor a popup je
#                   stejně k ničemu. datumOd/datumDo drží plný rozsah, takže info „běží pořád" nemizí.


def _terminy(tile, casova_mapa):
    """
    Víc termínů akce jako list {datum "DD-MM-YYYY", cas "HH:MM"|None}.

    Vrací None, když je koncert jednorázový (jeden den v okně) — pak stačí
    datumOd/cas a nezanášíme položku polem navíc. Pole je koncertní extra mimo
    sdílený RAW kontrakt (14 polí), appka ho použije na filmový popup „(N)".
    Dny bere z data-event_date (už profiltrované na scrapované okno), čas z mapy,
    a ořízne na MAX_TERMINY (rezidenční klubové série mají klidně 178 termínů).
    """
    dny = sorted(d for d in (tile.get("data-event_date") or "").split(",") if d)
    if len(dny) <= 1:
        return None
    return [{"datum": den, "cas": casova_mapa.get(den)} for den in dny[:MAX_TERMINY]]


def _datumy(tile):
    """
    datumOd/Do z data-atributů karty. Koncert bývá jednorázový (od == do).
    data-event_date = CSV konkrétních dnů (DD-MM-YYYY) spadajících do okna,
    data-limitedend = reálný konec akce.
    """
    dny = [d for d in (tile.get("data-event_date") or "").split(",") if d]
    od = min(dny) if dny else None  # pozn.: string min, ale formát DD-MM stačí pro RAW
    do = tile.get("data-limitedend") or (max(dny) if dny else None)
    return od, do


def _scrape_detail(session, url):
    """Z detailu koncertu vytáhne misto, adresu, popis a mapu termín→čas. Chyby nezabíjí běh."""
    misto = adresa = popis = None
    casova_mapa = {}
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
        # čas(y) z data-date_list — spolehlivější než dolování z textu
        casova_mapa = _casova_mapa(s)
    except requests.RequestException:
        pass  # detail se nepovedl — necháme null, položku nezahazujeme
    return misto, adresa, popis, casova_mapa


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
            cas = None
            casova_mapa = {}
            if url:
                misto, adresa, popis, casova_mapa = _scrape_detail(session, url)
                cas = _vyber_cas(casova_mapa, d_od)
                time.sleep(PAUZA)

            p = polozka(
                ZDROJ,
                nazevCz=_text(tile.find(["h2", "h3"])),
                zanr=_text(tile.find("span", class_="tile-switching__beforeHeading")),
                # u koncertu je afterHeading přímo místo (klub/scéna)
                misto=misto or _text(tile.find("span", class_="tile-switching__afterHeading")),
                adresa=adresa,
                datumOd=d_od,
                datumDo=d_do,
                cas=cas,  # z data-date_list; "00:00" (neuvedeno) přišlo jako None
                url=url,
                thumbnail=_thumbnail(tile),
                popis=popis,
                # cenu zdroj strojově nedodává → null, dolije ji AI krok z popisu
            )
            # koncertní extra: víc termínů → pole {datum, cas} pro popup „(N)" v appce
            terminy = _terminy(tile, casova_mapa)
            if terminy:
                p["terminy"] = terminy
            polozky.append(p)

        print(f"  [prague.eu/koncerty_jazzblues] strana {pg}: {len(tiles)} akcí")
        pg += 1
        time.sleep(PAUZA)

    return polozky
