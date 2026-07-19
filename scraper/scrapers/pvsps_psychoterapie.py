"""
Subscraper: víkendové semináře z pvsps.cz (Pražská vysoká škola psychosociálních studií)

Seznam seminářů je e-shopový výpis přímo na stránce /seminare-a-vycviky/
vikendove-seminare/ — server-side HTML, stránkuje se přes ?productlist_page=N
(stránkování jedeme, dokud chodí nové položky). Jedna položka = div.item:

  h4            → název
  .item-term    → termín volným textem ("23.-24.7.2026 oba dny 9.30-16.00")
  .item-lector h5 → lektor
  a.cmsbutton   → URL detailu

Z detailu se dotahuje zbytek: table.product-params (řádky Termín / Místo
konání), tr.price-high td (cena), div.product-descr (popis). Datumy se loví
regexem z volného textu termínu — najdi_datumy() umí i rozsah "23.-24.7.2026".

Semináře jsou sebezkušenostní víkendovky pro veřejnost — přesně Bobův formát.
Vyhazujeme jen víceleté programy (tříletý daseinsanalytický seminář apod.,
chytá je je_vycvik / je_dlouhodoba) a akce mimo okno.
"""

import re
import time

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

ZDROJ = "pvsps.cz"
BASE = "https://www.pvsps.cz/seminare-a-vycviky/vikendove-seminare/"
HEADERS = {"User-Agent": "Mozilla/5.0 (akce-scraper; osobni pouziti)"}
PAUZA = 0.5
MAX_STRAN = 10


def _detail(session, url):
    """Z detailu semináře vytáhne (misto, cena, popis, termin). Chyba běh nezabíjí."""
    misto = cena = popis = termin = None
    try:
        r = session.get(url, headers=HEADERS, timeout=20)
        s = BeautifulSoup(r.text, "html.parser")

        # table.product-params: řádky <strong>Termín/Místo konání</strong> + hodnota
        params = s.find("table", class_="product-params")
        if params:
            for tr in params.find_all("tr"):
                bunky = tr.find_all("td")
                if len(bunky) < 2:
                    continue
                label = bunky[0].get_text(" ", strip=True).lower()
                if "místo" in label:
                    misto = bunky[1].get_text(" ", strip=True) or None
                elif "termín" in label:
                    termin = bunky[1].get_text(" ", strip=True) or None

        radek_ceny = s.find("tr", class_="price-high")
        if radek_ceny:
            # buňka s cenou obsahuje i label "Cena:" — bereme jen částku s Kč
            text = radek_ceny.get_text(" ", strip=True)
            m = re.search(r"([\d\s]+Kč)", text)
            cena = m.group(1).strip() if m else None

        popis_el = s.find("div", class_="product-descr")
        popis = popis_el.get_text(" ", strip=True) if popis_el else None
    except requests.RequestException:
        pass
    return misto, cena, popis, termin


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    session = requests.Session()
    polozky = []
    videne = set()  # URL už zpracovaných seminářů — pojistka proti opakující se stránce
    vyrazeno = 0

    for strana in range(1, MAX_STRAN + 1):
        r = session.get(BASE, params={"productlist_page": strana}, headers=HEADERS, timeout=25)
        r.raise_for_status()
        s = BeautifulSoup(r.text, "html.parser")
        itemy = []
        for item in s.find_all("div", class_="item"):
            odkaz = item.find("a", class_="cmsbutton")
            if odkaz and odkaz.get("href") and odkaz["href"] not in videne:
                itemy.append((item, odkaz["href"]))
        if not itemy:
            break  # došly stránky (nebo se začaly opakovat)

        for item, url in itemy:
            videne.add(url)
            nazev_el = item.find("h4")
            nazev = nazev_el.get_text(" ", strip=True) if nazev_el else None
            if not nazev:
                continue

            termin_el = item.find(class_="item-term")
            termin_text = termin_el.get_text(" ", strip=True) if termin_el else None
            datumy = najdi_datumy(termin_text)

            if je_vycvik(nazev):
                vyrazeno += 1
                continue
            # datumy známé už z výpisu a mimo okno → detail nemá cenu stahovat
            if datumy and not v_okne(datumy[0], datumy[-1], od, do):
                continue

            lektor_el = item.select_one(".item-lector h5")
            misto, cena, popis, termin_detail = _detail(session, url)
            time.sleep(PAUZA)

            # obsazené/nevypsané semináře mají ve výpisu jen časy bez datumu
            # ("so 9:00-19:00 - ne 9:00-16:00") — zkusíme Termín z detailu,
            # a když datum není ani tam, seminář nemá vypsaný termín → pryč
            if not datumy:
                termin_text = termin_detail or termin_text
                datumy = najdi_datumy(termin_text)
            if not datumy:
                vyrazeno += 1
                continue
            d_od, d_do = datumy[0], datumy[-1]
            if je_dlouhodoba(d_od, d_do):
                vyrazeno += 1
                continue
            if not v_okne(d_od, d_do, od, do):
                continue

            polozky.append(polozka(
                ZDROJ,
                nazevCz=nazev,
                autor=lektor_el.get_text(" ", strip=True) if lektor_el else None,
                zanr=odhadni_zanr(nazev) or "seminář",  # celý výpis jsou semináře
                datumOd=d_od,
                datumDo=d_do,
                cas=najdi_cas(termin_text),
                misto=misto or "PVŠPS, Hekrova 805, Praha 4",  # default z hlavičky stránky
                url=url,
                cena=cena,
                popis=popis,
            ))

        print(f"  [pvsps.cz] strana {strana}: {len(itemy)} seminářů")
        time.sleep(PAUZA)

    if vyrazeno:
        print(f"  [pvsps.cz] vyřazeno (víceleté programy / bez termínu): {vyrazeno}")
    return polozky
