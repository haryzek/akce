"""
Subscraper: Party (klubová/taneční scéna) z goout.net

Klon goout_divadlo.py — stejná mechanika (veřejné JSON API, kurzorové stránkování,
seskupení repríz přes event.id), liší se jen kategorií a jedním navíc: lokálním
datumovým guardem.

Rozdíl proti divadlu:
- `categories[]=clubbing` místo `play`.
- goout u clubbingu do výsledku přimíchává i akce s termíny MIMO zadané okno
  (viděli jsme květnovou párty při okně v červenci). Server `after`/`before` tu
  tedy není spolehlivý jako u divadla, proto termíny ještě jednou profiltrujeme
  lokálně přes `_v_okne` a akci bez jediného termínu v okně zahodíme. Do RAW pak
  jde jen to, co do Bobova okna opravdu spadá.

Ostatní (mapování polí, thumbnail, cena, účinkující, dedup přes event.id) je 1:1
jako u divadla — viz komentáře tam.
"""

import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

# --- import společných helperů (funguje ať se spouští odkudkoli) ---
try:
    from ..common import polozka
except ImportError:  # když se modul spustí samostatně
    from common import polozka

TYP_AKCE = "party"
ZDROJ = "goout.net"

API = "https://goout.net/services/entities/v1/schedules"
CITY_PRAHA = 101748113
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json",
}
PRAHA = ZoneInfo("Europe/Prague")
PAUZA = 0.5
LIMIT = 50
MAX_STRAN = 40
MAX_TERMINY = 12


def _iso_utc(datum_ddmmyyyy, konec_dne):
    """"13-07-2026" → ISO 8601 UTC pro after/before (00:00, resp. 23:59:59 pražského času)."""
    den, mesic, rok = (int(x) for x in datum_ddmmyyyy.split("-"))
    if konec_dne:
        lokalni = datetime(rok, mesic, den, 23, 59, 59, tzinfo=PRAHA)
    else:
        lokalni = datetime(rok, mesic, den, 0, 0, 0, tzinfo=PRAHA)
    return lokalni.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _den_klic(datum_ddmmyyyy):
    """"13-07-2026" → 20260713 (int) pro snadné porovnání v okně. None když nejde."""
    try:
        den, mesic, rok = (int(x) for x in datum_ddmmyyyy.split("-"))
        return rok * 10000 + mesic * 100 + den
    except (ValueError, AttributeError):
        return None


def _params(od, do, scroll_id):
    """Query parametry pro jednu stránku. Party = categories[]=clubbing."""
    p = [
        ("languages[]", "cs"),
        ("categories[]", "clubbing"),
        ("after", _iso_utc(od, konec_dne=False)),
        ("before", _iso_utc(do, konec_dne=True)),
        ("grouped", "false"),
        ("notScheduleTags[]", "online"),
        ("sort", "popularity:desc"),
        ("limit", str(LIMIT)),
        ("cityIds[]", str(CITY_PRAHA)),
        ("countryIsos[]", "cz"),
        ("include", "events,venues,images,performers"),
    ]
    if scroll_id:
        p.append(("scrollId", scroll_id))
    return p


def _cas(start_at, has_time):
    if not has_time or not start_at or "T" not in start_at:
        return None
    return start_at[11:16]


def _datum(start_at):
    if not start_at or "T" not in start_at:
        return None
    r, m, d = start_at[0:10].split("-")
    return f"{d}-{m}-{r}"


def _cena(attrs):
    pricing = attrs.get("pricing")
    if not pricing:
        return None
    mena = (attrs.get("currency") or "").lower()
    if mena == "czk":
        return f"{pricing} Kč"
    return f"{pricing} {mena}".strip() if mena else pricing


def _lokal(entita, pole):
    if not entita:
        return None
    return (entita.get("locales", {}).get("cs", {}) or {}).get(pole)


def _thumbnail(event, images):
    rels = (event or {}).get("relationships", {}).get("images", []) or []
    for ref in rels:
        img = images.get(str(ref.get("id")))
        url = (img or {}).get("attributes", {}).get("url")
        if url:
            return url
    return None


def _autor(event, performers):
    rels = (event or {}).get("relationships", {}).get("performers", []) or []
    jmena = []
    for ref in rels:
        jmeno = _lokal(performers.get(str(ref.get("id"))), "name")
        if jmeno:
            jmena.append(jmeno)
    return ", ".join(jmena[:3]) or None


def _zanr(event):
    tags = (event or {}).get("attributes", {}).get("tags", []) or []
    if not tags:
        return None
    return ", ".join(t.replace("_", " ") for t in tags[:3])


def _sluc_included(cil, raw, klic):
    data = (raw or {}).get(klic)
    if isinstance(data, dict):
        for obj in data.values():
            cil[str(obj.get("id"))] = obj
    elif isinstance(data, list):
        for obj in data:
            cil[str(obj.get("id"))] = obj


def _stahni_schedules(od, do):
    session = requests.Session()
    schedules = []
    included = {"events": {}, "venues": {}, "images": {}, "performers": {}}
    scroll_id = ""

    for strana in range(MAX_STRAN):
        r = session.get(API, params=_params(od, do, scroll_id), headers=HEADERS, timeout=25)
        r.raise_for_status()
        j = r.json()
        davka = j.get("schedules") or []
        if not davka:
            break
        schedules.extend(davka)
        for klic in included:
            _sluc_included(included[klic], j.get("included"), klic)
        print(f"  [goout.net/party] strana {strana + 1}: {len(davka)} termínů")

        scroll_id = (j.get("meta") or {}).get("nextScrollId")
        if not scroll_id:
            break
        time.sleep(PAUZA)

    return schedules, included


def scrape(od, do):
    """
    Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek — seskupených přes
    event.id, s termíny profiltrovanými na Bobovo okno (goout u clubbingu vrací i mimo).
    """
    od_klic, do_klic = _den_klic(od), _den_klic(do)

    def v_okne(datum):
        k = _den_klic(datum)
        if k is None:
            return True  # nedatovatelné radši nechat, ať se něco neztratí
        return (od_klic is None or k >= od_klic) and (do_klic is None or k <= do_klic)

    schedules, included = _stahni_schedules(od, do)
    events = included["events"]
    venues = included["venues"]
    images = included["images"]
    performers = included["performers"]

    skupiny = {}
    for s in schedules:
        eid = (s.get("relationships", {}).get("event") or {}).get("id")
        if eid is None:
            continue
        skupiny.setdefault(eid, []).append(s)

    polozky = []
    for eid, sched_list in skupiny.items():
        event = events.get(str(eid))
        sched_list.sort(key=lambda s: s.get("attributes", {}).get("startAt") or "")
        terminy = []
        videne = set()
        for s in sched_list:
            start = s.get("attributes", {}).get("startAt")
            has_time = s.get("attributes", {}).get("hasTime")
            datum = _datum(start)
            cas = _cas(start, has_time)
            klic = (datum, cas)
            # lokální datumový guard: mimo Bobovo okno termín zahodíme
            if datum and v_okne(datum) and klic not in videne:
                videne.add(klic)
                terminy.append({"datum": datum, "cas": cas})

        if not terminy:
            continue  # akce nemá jediný termín v okně → není pro nás

        prvni = sched_list[0]
        venue = venues.get(str((prvni.get("relationships", {}).get("venue") or {}).get("id")))
        p = polozka(
            ZDROJ,
            nazevCz=_lokal(event, "name"),
            autor=_autor(event, performers),
            zanr=_zanr(event),
            datumOd=terminy[0]["datum"],
            datumDo=terminy[-1]["datum"],
            cas=terminy[0]["cas"],
            misto=_lokal(venue, "name"),
            adresa=(venue or {}).get("attributes", {}).get("address"),
            url=_lokal(prvni, "siteUrl"),
            cena=_cena(prvni.get("attributes", {})),
            thumbnail=_thumbnail(event, images),
            popis=_lokal(event, "description"),
        )
        if len(terminy) > 1:
            p["terminy"] = terminy[:MAX_TERMINY]
        polozky.append(p)

    return polozky
