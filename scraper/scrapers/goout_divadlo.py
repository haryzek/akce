"""
Subscraper: Divadlo z goout.net

První zdroj z jiného webu než prague.eu — a jiným mechanismem. goout je Nuxt SPA,
která si program tahá z veřejného JSON API (to samé volá jejich frontend). My voláme
ten endpoint napřímo, takže nescrapujeme HTML, ale rovnou strukturovaná data:

  https://goout.net/services/entities/v1/schedules?categories[]=play&cityIds[]=101748113
    &after=<ISO UTC>&before=<ISO UTC>&include=events,venues,images,performers&limit=50

Tři věci, které se liší od prague.eu scraperů:

1. STRÁNKOVÁNÍ je kurzorové, ne přes číslo strany. Odpověď nese `meta.nextScrollId`
   (base64 kurzor); do dalšího requestu ho pošleme jako `scrollId`. `offset` API ignoruje.
   Jedeme dokola, dokud chodí nějaké schedules.

2. DATUMOVÝ FILTR jede serverově přes `after`/`before`, ale chce ISO 8601 v UTC
   (…Z). Bobovo okno DD-MM-YYYY je v pražském čase (00:00 od, 23:59 do), tak ho
   přes zoneinfo("Europe/Prague") převedeme na UTC. (Proto tzdata v requirements.)

3. DEDUPLIKACE PŘEDSTAVENÍ řešíme rovnou tady. goout vrací `schedules` = jednotlivé
   termíny, takže jedna hra se objeví tolikrát, kolik má repríz (klidně 5× víc řádků
   než her). ALE každý termín nese `relationships.event.id` a všechny reprízy téže hry
   mají stejné event.id → seskupíme podle něj a vyrobíme JEDNU položku s polem `terminy`.
   Deterministické přes ID, žádné dohadování z názvů (to řeší až generický dedup.py
   napříč zdroji). Tohle je „intra-zdroj" dedup, patří do subscraperu.

Data jsou v JSON:API-like tvaru: `schedules[]` drží termíny, `included` je slovník
navázaných entit (events, venues, images, performers) klíčovaný podle ID.
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

TYP_AKCE = "divadlo"
ZDROJ = "goout.net"

API = "https://goout.net/services/entities/v1/schedules"
CITY_PRAHA = 101748113
# realistický UA — goout má Cloudflare, který holý „python-requests" UA nemusí pustit
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json",
}
PRAHA = ZoneInfo("Europe/Prague")
PAUZA = 0.5          # sekundy mezi requesty — slušný robot neklepe zběsile
LIMIT = 50           # kolik schedules na stránku (API default je 24, 50 je pořád v pohodě)
MAX_STRAN = 40       # tvrdý strop na počet stran, ať se smyčka nikdy nezacyklí
MAX_TERMINY = 12     # strop na počet termínů v položce (dlouhoběžící hry mají desítky repríz)


def _iso_utc(datum_ddmmyyyy, konec_dne):
    """
    "13-07-2026" → ISO 8601 v UTC pro parametr after/before.
    konec_dne=False → 00:00 pražského času (dolní mez), True → 23:59:59 (horní mez).
    Pražský čas převedeme na UTC, protože to API chce (…Z).
    """
    den, mesic, rok = (int(x) for x in datum_ddmmyyyy.split("-"))
    if konec_dne:
        lokalni = datetime(rok, mesic, den, 23, 59, 59, tzinfo=PRAHA)
    else:
        lokalni = datetime(rok, mesic, den, 0, 0, 0, tzinfo=PRAHA)
    utc = lokalni.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _params(od, do, scroll_id):
    """Query parametry pro jednu stránku. Divadlo = categories[]=play (bez tagů)."""
    p = [
        ("languages[]", "cs"),
        ("categories[]", "play"),
        ("after", _iso_utc(od, konec_dne=False)),
        ("before", _iso_utc(do, konec_dne=True)),
        ("grouped", "false"),               # ploché termíny — grupování si děláme sami přes event.id
        ("notScheduleTags[]", "online"),    # bez online streamů, chceme živé divadlo
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
    """Z "2026-07-11T14:00:00+02:00" vytáhne "14:00"; když akce nemá čas, vrátí None."""
    if not has_time or not start_at or "T" not in start_at:
        return None
    return start_at[11:16]  # HH:MM z ISO řetězce


def _datum(start_at):
    """Z "2026-07-11T14:00:00+02:00" vyrobí RAW datum "11-07-2026"."""
    if not start_at or "T" not in start_at:
        return None
    r, m, d = start_at[0:10].split("-")
    return f"{d}-{m}-{r}"


def _cena(attrs):
    """pricing "250–550" + currency "czk" → "250–550 Kč". Bez ceny → None."""
    pricing = attrs.get("pricing")
    if not pricing:
        return None
    mena = (attrs.get("currency") or "").lower()
    if mena == "czk":
        return f"{pricing} Kč"
    return f"{pricing} {mena}".strip() if mena else pricing


def _lokal(entita, pole):
    """Bezpečně vytáhne entita.locales.cs.<pole> (např. name, description)."""
    if not entita:
        return None
    return (entita.get("locales", {}).get("cs", {}) or {}).get(pole)


def _thumbnail(event, images):
    """URL prvního obrázku eventu. goout dává hotovou URL v image.attributes.url."""
    rels = (event or {}).get("relationships", {}).get("images", []) or []
    for ref in rels:
        img = images.get(str(ref.get("id")))
        url = (img or {}).get("attributes", {}).get("url")
        if url:
            return url
    return None


def _autor(event, performers):
    """Účinkující/soubor: jména performerů eventu spojená čárkou (max 3), jinak None."""
    rels = (event or {}).get("relationships", {}).get("performers", []) or []
    jmena = []
    for ref in rels:
        jmeno = _lokal(performers.get(str(ref.get("id"))), "name")
        if jmeno:
            jmena.append(jmeno)
    return ", ".join(jmena[:3]) or None


def _zanr(event):
    """Žánr z tagů eventu (čitelněji než mainCategory 'play'). Bez tagů → None."""
    tags = (event or {}).get("attributes", {}).get("tags", []) or []
    if not tags:
        return None
    # tagy jsou strojové slugy (stand_up_comedy) → uděláme z nich lidský text
    return ", ".join(t.replace("_", " ") for t in tags[:3])


def _sluc_included(cil, raw, klic):
    """
    Navázané entity daného druhu z odpovědi přidá do indexu `cil` {str(id): obj}.
    goout vrací `included[klic]` jednou jako slovník {id: obj}, jindy jako list [obj] —
    obě podoby normalizujeme na slovník klíčovaný ID (ať lookup nezávisí na tvaru).
    """
    data = (raw or {}).get(klic)
    if isinstance(data, dict):
        for obj in data.values():
            cil[str(obj.get("id"))] = obj
    elif isinstance(data, list):
        for obj in data:
            cil[str(obj.get("id"))] = obj


def _stahni_schedules(od, do):
    """Kurzorem projede všechny stránky a vrátí (schedules, included_slovníky)."""
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
        # posbíráme navázané entity ze všech stran do jednoho indexu {id: obj}
        for klic in included:
            _sluc_included(included[klic], j.get("included"), klic)
        print(f"  [goout.net/divadlo] strana {strana + 1}: {len(davka)} termínů")

        scroll_id = (j.get("meta") or {}).get("nextScrollId")
        if not scroll_id:
            break
        time.sleep(PAUZA)

    return schedules, included


def scrape(od, do):
    """
    Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek — už seskupených
    přes event.id (jedna hra = jedna položka s polem `terminy`).
    """
    schedules, included = _stahni_schedules(od, do)
    events = included["events"]
    venues = included["venues"]
    images = included["images"]
    performers = included["performers"]

    # seskupení termínů podle event.id — zachováváme pořadí prvního výskytu (popularita)
    skupiny = {}  # event_id -> list schedulů
    for s in schedules:
        eid = (s.get("relationships", {}).get("event") or {}).get("id")
        if eid is None:
            continue
        skupiny.setdefault(eid, []).append(s)

    polozky = []
    for eid, sched_list in skupiny.items():
        event = events.get(str(eid))
        # termíny seřadíme podle data+času a odstraníme duplicity (stejný den+čas)
        sched_list.sort(key=lambda s: s.get("attributes", {}).get("startAt") or "")
        terminy = []
        videne = set()
        for s in sched_list:
            start = s.get("attributes", {}).get("startAt")
            has_time = s.get("attributes", {}).get("hasTime")
            datum = _datum(start)
            cas = _cas(start, has_time)
            klic = (datum, cas)
            if datum and klic not in videne:
                videne.add(klic)
                terminy.append({"datum": datum, "cas": cas})

        prvni = sched_list[0]
        venue = venues.get(str((prvni.get("relationships", {}).get("venue") or {}).get("id")))
        p = polozka(
            ZDROJ,
            nazevCz=_lokal(event, "name"),
            autor=_autor(event, performers),
            zanr=_zanr(event),
            datumOd=terminy[0]["datum"] if terminy else None,
            datumDo=terminy[-1]["datum"] if terminy else None,
            cas=terminy[0]["cas"] if terminy else None,
            misto=_lokal(venue, "name"),
            adresa=(venue or {}).get("attributes", {}).get("address"),
            url=_lokal(prvni, "siteUrl"),
            cena=_cena(prvni.get("attributes", {})),
            thumbnail=_thumbnail(event, images),
            popis=_lokal(event, "description"),
        )
        # víc termínů → koncertní extra pole pro popup „(N)" v appce (ořízneme na strop)
        if len(terminy) > 1:
            p["terminy"] = terminy[:MAX_TERMINY]
        polozky.append(p)

    return polozky
