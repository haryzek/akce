"""
Subscraper: Party (klubová/taneční scéna) z ra.co (Resident Advisor)

Druhý zdroj pro typ `party` vedle goout_party.py. RA je pro pražskou elektroniku
kvalitnější zdroj — má line-upy, žánrové tagy a bohaté popisy od promotérů.

Mechanika (třetí varianta v repu, po prague.eu HTML a goout JSON:API):
- ra.co je Next.js SPA, program si tahá z **veřejného GraphQL endpointu**
  `POST https://ra.co/graphql`. Scraper volá ten endpoint napřímo — bez cookies,
  bez tokenu, stačí realistický User-Agent (DataDome na tenhle endpoint nesahá).
- **Stránkování je normální číslo strany** (`page` + `pageSize`), ne kurzor jako
  u goout. Odpověď nese `totalResults`, takže víme, kdy skončit.
- **Datumový filtr je serverový** — `filters.listingDate: {gte, lte}` v prostém
  `YYYY-MM-DD`. Žádný lokální guard netřeba (na rozdíl od goout clubbingu).
- Nekonečný scroll na webu je jen fasáda nad tímhle API.

Praha = `areaId 451` (vytaženo z `__NEXT_DATA__` na /events/cz/prague).

Jedna položka = jeden `event`. RA vrací "listings" (termíny), ale jedna akce může
mít víc listingů se stejným `event.id` → seskupíme přes to ID do `terminy`,
stejně jako goout. Deterministicky přes ID, ne fuzzy.

Pozn. k ceně: RA `cost` je volný text od promotéra a bez konzistentní měny —
viděli jsme "300", "33", "80€", "250-400 CZK". U holého čísla nevíme, jestli jsou
to koruny nebo eura, takže ho zahazujeme (viz `_cena`). Radši žádná cena než
"33" u akce za 330 Kč; dedup ji navíc často doplní z goout, kde je spolehlivá.
"""

import time

import requests

# --- import společných helperů (funguje ať se spouští odkudkoli) ---
try:
    from ..common import polozka
except ImportError:  # když se modul spustí samostatně
    from common import polozka

TYP_AKCE = "party"
ZDROJ = "ra.co"

API = "https://ra.co/graphql"
AREA_PRAHA = 451  # Prague, z __NEXT_DATA__ na /events/cz/prague
BASE = "https://ra.co"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "ra-content-language": "en",
    "Referer": "https://ra.co/events/cz/prague",
}

PAUZA = 0.5
PAGE_SIZE = 50
MAX_STRAN = 20
MAX_TERMINY = 12
MAX_POPIS = 2000  # RA popisy bývají ukecané (line-upy, safe-space manifesty)

# GraphQL dotaz. Všechno, co potřebujeme, jde v jednom průchodu — popis (`content`),
# cena, žánry i adresa jsou přímo v listingu, detail akce dotahovat netřeba.
QUERY = """
query GET_EVENT_LISTINGS($filters: FilterInputDtoInput, $pageSize: Int, $page: Int) {
  eventListings(
    filters: $filters
    pageSize: $pageSize
    page: $page
    sort: {listingDate: {order: ASCENDING}}
  ) {
    data {
      event {
        id
        title
        content
        date
        startTime
        contentUrl
        cost
        genres { name }
        artists { name }
        images { filename type }
        venue { name address }
      }
    }
    totalResults
  }
}
"""


def _iso_den(datum_ddmmyyyy):
    """"18-07-2026" → "2026-07-18" (formát, který chce filtr listingDate)."""
    den, mesic, rok = (int(x) for x in datum_ddmmyyyy.split("-"))
    return f"{rok:04d}-{mesic:02d}-{den:02d}"


def _datum(iso):
    """"2026-07-18T22:00:00.000" → "18-07-2026". None když se nedá."""
    if not iso or len(iso) < 10:
        return None
    r, m, d = iso[0:10].split("-")
    return f"{d}-{m}-{r}"


def _cas(iso):
    """Čas ze startTime. RA ho má skoro vždycky; půlnoc bereme jako platnou."""
    if not iso or "T" not in iso:
        return None
    return iso[11:16]


def _spoj(seznam, pole, limit=3):
    """[{name: "Techno"}, …] → "Techno, House". None když nic."""
    jmena = [(x or {}).get(pole) for x in (seznam or [])]
    jmena = [j for j in jmena if j]
    return ", ".join(jmena[:limit]) or None


def _thumbnail(event):
    """Přednostně flyer, jinak první obrázek, co má URL."""
    obrazky = event.get("images") or []
    for img in obrazky:
        if (img or {}).get("type") == "FLYERFRONT" and img.get("filename"):
            return img["filename"]
    for img in obrazky:
        if (img or {}).get("filename"):
            return img["filename"]
    return None


def _cena(event):
    """
    RA `cost` je volný text bez konzistentní měny, promotéři tam píšou ledacos.
    Pustíme dál jen to, co něco říká:
      "749 Kč", "80€", "250-400 CZK" → číslo I s měnou, OK
      "free", "zdarma"               → slovní, OK
      "33"                           → číslo bez měny, nevíme Kč/€ → zahodit
      "??", "-"                      → žádná informace → zahodit
    Zahozenou cenu často doplní dedup z goout, kde je spolehlivá.
    """
    cost = (event.get("cost") or "").strip()
    if not cost:
        return None
    if not any(c.isalnum() for c in cost):
        return None  # samá interpunkce ("??", "-") — nulová informace
    if any(c.isdigit() for c in cost) and not any(c.isalpha() or c in "€$£" for c in cost):
        return None  # holé číslo bez měny — nejednoznačné
    return cost


def _popis(event):
    popis = (event.get("content") or "").strip()
    if not popis:
        return None
    return popis[:MAX_POPIS]


def _stahni_eventy(od, do):
    """Projde stránky a vrátí syrové `event` objekty (můžou se opakovat)."""
    session = requests.Session()
    eventy = []

    for strana in range(1, MAX_STRAN + 1):
        telo = {
            "operationName": "GET_EVENT_LISTINGS",
            "query": QUERY,
            "variables": {
                "filters": {
                    "areas": {"eq": AREA_PRAHA},
                    "listingDate": {"gte": _iso_den(od), "lte": _iso_den(do)},
                },
                "pageSize": PAGE_SIZE,
                "page": strana,
            },
        }
        r = session.post(API, json=telo, headers=HEADERS, timeout=25)
        r.raise_for_status()
        j = r.json()

        if j.get("errors"):
            # GraphQL vrací 200 i s chybou — nesmí to projít potichu
            raise RuntimeError(f"GraphQL chyba: {j['errors'][0].get('message')}")

        listing = (j.get("data") or {}).get("eventListings") or {}
        davka = listing.get("data") or []
        if not davka:
            break

        for polozka_listingu in davka:
            event = (polozka_listingu or {}).get("event")
            if event:
                eventy.append(event)

        celkem = listing.get("totalResults") or 0
        print(f"  [ra.co/party] strana {strana}: {len(davka)} listingů (celkem {celkem})")

        if strana * PAGE_SIZE >= celkem:
            break
        time.sleep(PAUZA)

    return eventy


def scrape(od, do):
    """
    Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list RAW položek,
    seskupených přes event.id (jedna akce = jedna položka, i když má víc termínů).
    """
    eventy = _stahni_eventy(od, do)

    # seskupení přes event.id — deterministické, žádné fuzzy porovnávání
    skupiny = {}
    for event in eventy:
        eid = event.get("id")
        if eid is None:
            continue
        skupiny.setdefault(str(eid), []).append(event)

    polozky = []
    for varianty in skupiny.values():
        varianty.sort(key=lambda e: e.get("startTime") or e.get("date") or "")
        event = varianty[0]

        terminy = []
        videne = set()
        for v in varianty:
            datum = _datum(v.get("date") or v.get("startTime"))
            cas = _cas(v.get("startTime"))
            klic = (datum, cas)
            if datum and klic not in videne:
                videne.add(klic)
                terminy.append({"datum": datum, "cas": cas})

        if not terminy:
            continue

        venue = event.get("venue") or {}
        contentUrl = event.get("contentUrl")

        p = polozka(
            ZDROJ,
            nazevCz=event.get("title"),
            autor=_spoj(event.get("artists"), "name"),
            zanr=_spoj(event.get("genres"), "name"),
            datumOd=terminy[0]["datum"],
            datumDo=terminy[-1]["datum"],
            cas=terminy[0]["cas"],
            misto=venue.get("name"),
            adresa=venue.get("address"),
            url=f"{BASE}{contentUrl}" if contentUrl else None,
            cena=_cena(event),
            thumbnail=_thumbnail(event),
            popis=_popis(event),
        )
        if len(terminy) > 1:
            p["terminy"] = terminy[:MAX_TERMINY]
        polozky.append(p)

    return polozky
