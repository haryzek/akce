"""
Subscraper: Výstavy z goout.net

Druhý zdroj pro typ `vystavy` vedle prague_vystavy.py. goout má výstav výrazně víc
(v testovaném měsíci 220 proti 105 z prague.eu, překryv jen 38) a skoro u všech
nese popis — je to pro tenhle typ bohatší zdroj.

Mechanicky je to klon goout_divadlo/goout_party (veřejné JSON API, kurzorové
stránkování, JSON:API-like `included`), ale se **třemi zásadními odchylkami**,
které plynou z toho, že výstava trvá měsíce, kdežto párty jeden večer:

1. **`grouped=true`** (party i divadlo mají `false`). Zásadní: výstava má vlastní
   `schedule` na KAŽDÝ otevírací den, takže s `grouped=false` vrátí stránka
   50 záznamů = jedna jediná výstava. S `grouped=true` je to ~48 různých výstav
   na stránku. Bez tohohle je scraper nepoužitelný.

2. **Trvání se bere z `event.attributes.schedulesRange`** ({first, last}), ne ze
   `schedule.startAt/endAt`. Grouped schedule totiž často nese jen ten jeden den,
   který spadl do okna ("2026-07-20 10:00 → 2026-07-20 23:59"), zatímco výstava
   běží od loňska do srpna. Appka filtruje výstavy překryvem trvání s vybraným
   rozmezím, takže useknutý rozsah by ji rozbil. `schedulesRange` může chybět
   (null) → fallback na schedule.

3. **Filtr doprovodného programu** (`_je_balast`). goout pod `exhibitions` vede
   i komentované prohlídky, workshopy, přednášky a vstupenky do stálých expozic
   ("Komentovaná prohlídka výstavy X", "O umění zblízka: …", "Vstup do Kunsthalle
   Praha"). To nejsou výstavy a v RAW jen ředí AI krok, tak je vyhazujeme rovnou.
   Filtr je schválně konzervativní — chytá jen jasné vzorce v názvu.

4. **Stálé expozice pryč** (`schedule.attributes.isPermanent`). Dvě třetiny toho,
   co goout vede pod výstavami, jsou trvalky — Loreta, Muzeum Karla Zemana, Zoo
   Mořský Svět, stálé expozice NG. Bobovi jde o to, co se právě děje, ne o věci,
   které tam visí roky. Škrtá 220 na 75 a je to největší jednotlivá úspora.

5. **Žánrový filtr lokálně, ne v API** (`_zanr_sedi`). Bob chce jen výtvarné žánry
   (ZANRY_BOB — odpovídají `?genres=…` na webu). Serverový `tags[]` filtr na to ale
   použít NELZE: ze 75 dočasných výstav jich 21 nemá vyplněný žádný tag a whitelist
   by je zahodil — a jsou to zrovna ty nejlepší (Kentridge v Kunsthalle, Petrbok
   v DOXu, Bienále Ve věci umění, Vytiska). Proto filtrujeme až tady pravidlem
   **"má Bobův žánr NEBO nemá žádný"**: tagované mimo obor vypadnou, netagované
   projdou a doskóruje je AI krok. Bonus — vypadne tím i balast, který se špatně
   pozná z názvu (`in_city_guided_tour` má 12 položek, `workshop`, `for_children_*`).

Navíc proti ostatním goout scraperům: `exhibitionMeta.curator` → `autor`.
"""

import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

# --- import společných helperů (funguje ať se spouští odkudkoli) ---
try:
    from ..common import polozka, je_trvalka
except ImportError:  # když se modul spustí samostatně
    from common import polozka, je_trvalka

TYP_AKCE = "vystavy"
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
MAX_POPIS = 2000  # karta pojme ~860 znaků; delší text jen nafukuje RAW pro AI krok

# Vzorce doprovodného programu — když název začíná některým z nich (nebo ho
# obsahuje jako celý úsek), není to výstava, ale akce k výstavě.
BALAST_ZACATKY = (
    "komentovana prohlidka", "komentovka", "komentovane prohlidky",
    "soukroma komentovana", "prohlidka s", "vstup do", "vstupenka",
    "o umeni zblizka", "v expozici na hodinku", "workshop", "prednaska",
    "beseda", "vernisaz", "derniera", "dernisaz", "kurzy", "kurz ",
    "vytvarna dilna", "tvurci dilna", "detsky den", "denni tabor",
    "prochazka", "exkurze", "audioprohlidka", "audio prohlidka",
)
BALAST_OBSAHUJE = (
    "komentovana prohlidka", "komentovanou prohlidku", "s kuratorem",
    "s kuratorkou", "na objednavku", "pro skoly", "pro deti a rodice",
    # vstupenky a členství, ne výstavy ("Roční členství Kunsthalle Praha")
    "rocni clenstvi", "darkova vstupenka", "darkovy poukaz", "vstupenka do",
    "permanentka", "voucher",
    # kurátorské a doprovodné série (poznají se až uvnitř názvu)
    "ocima kuratoru", "detsky den", "dilna pro", "prohlidka pro",
    "den s autor", "s umelcem a kuratorem", "s kuratorem a", "doxygen",
)


# Výtvarné žánry, které Boba zajímají (na webu goout = `?genres=…`).
# Používá se lokálně, ne jako serverový filtr — viz bod 5 v docstringu modulu.
ZANRY_BOB = {
    "exhibitions_contemporary", "exhibition_objects", "exhibitions_graphics",
    "exhibitions_photography", "exhibitions_design", "exhibitions_classic",
    "exhibitions_mixed_media", "exhibitions_paintings", "drawings", "glass",
}


def _zanr_sedi(event):
    """
    Pustí výstavu, když má aspoň jeden Bobův žánr — nebo když nemá žádný tag.
    Netagované se nesmí zahazovat: je jich pětina a bývají to ty nejlepší výstavy
    (goout je prostě neotaguje). Vypadne tak jen to, co je tagované mimo obor.
    """
    tags = set((event or {}).get("attributes", {}).get("tags") or [])
    if not tags:
        return True
    return bool(tags & ZANRY_BOB)


def _bez_diakritiky(s):
    """Malá písmena bez diakritiky — pro porovnávání vzorců v názvu."""
    import unicodedata
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _je_balast(nazev):
    """
    Je to doprovodný program místo výstavy? Konzervativně — radši nechat projít
    hraniční případ (od toho je skóre v AI kroku) než vyhodit skutečnou výstavu.
    """
    n = _bez_diakritiky(nazev)
    if not n:
        return False
    if any(n.startswith(z) for z in BALAST_ZACATKY):
        return True
    return any(o in n for o in BALAST_OBSAHUJE)


def _iso_utc(datum_ddmmyyyy, konec_dne):
    """"20-07-2026" → ISO 8601 UTC pro after/before (pražská půlnoc, resp. 23:59:59)."""
    den, mesic, rok = (int(x) for x in datum_ddmmyyyy.split("-"))
    if konec_dne:
        lokalni = datetime(rok, mesic, den, 23, 59, 59, tzinfo=PRAHA)
    else:
        lokalni = datetime(rok, mesic, den, 0, 0, 0, tzinfo=PRAHA)
    return lokalni.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _params(od, do, scroll_id):
    """Query parametry pro jednu stránku. Výstavy = exhibitions + grouped=true (viz docstring)."""
    p = [
        ("languages[]", "cs"),
        ("categories[]", "exhibitions"),
        ("after", _iso_utc(od, konec_dne=False)),
        ("before", _iso_utc(do, konec_dne=True)),
        ("grouped", "true"),  # KLÍČOVÉ — viz bod 1 v docstringu modulu
        ("notScheduleTags[]", "online"),
        ("sort", "popularity:desc"),
        ("limit", str(LIMIT)),
        ("cityIds[]", str(CITY_PRAHA)),
        ("countryIsos[]", "cz"),
        ("include", "events,venues,images"),
    ]
    if scroll_id:
        p.append(("scrollId", scroll_id))
    return p


def _datum(iso):
    """"2026-07-20T10:00:00+02:00" → "20-07-2026". None když nejde."""
    if not iso or len(iso) < 10:
        return None
    r, m, d = iso[0:10].split("-")
    return f"{d}-{m}-{r}"


def _lokal(entita, pole):
    if not entita:
        return None
    return (entita.get("locales", {}).get("cs", {}) or {}).get(pole)


def _cena(attrs):
    pricing = attrs.get("pricing")
    if not pricing:
        return None
    mena = (attrs.get("currency") or "").lower()
    if mena == "czk":
        return f"{pricing} Kč"
    return f"{pricing} {mena}".strip() if mena else pricing


def _thumbnail(event, images):
    rels = (event or {}).get("relationships", {}).get("images", []) or []
    for ref in rels:
        img = images.get(str(ref.get("id")))
        url = (img or {}).get("attributes", {}).get("url")
        if url:
            return url
    return None


def _zanr(event):
    """Tagy typu "exhibitions_new_media" → "new media"."""
    tags = (event or {}).get("attributes", {}).get("tags", []) or []
    cisté = []
    for t in tags[:3]:
        t = t.replace("exhibitions_", "").replace("_", " ").strip()
        if t:
            cisté.append(t)
    return ", ".join(cisté) or None


def _kurator(event):
    meta = (event or {}).get("attributes", {}).get("exhibitionMeta") or {}
    return meta.get("curator")


def _trvani(event, schedule):
    """
    Trvání výstavy: přednostně z event.schedulesRange (celý rozsah), jinak ze
    schedule. Viz bod 2 v docstringu — grouped schedule nese často jen jeden den.
    """
    rozsah = (event or {}).get("attributes", {}).get("schedulesRange") or {}
    od = _datum(rozsah.get("first"))
    do = _datum(rozsah.get("last"))
    if od:
        return od, do or od
    attrs = (schedule or {}).get("attributes", {})
    od = _datum(attrs.get("startAt"))
    do = _datum(attrs.get("endAt"))
    return od, (do or od)


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
    included = {"events": {}, "venues": {}, "images": {}}
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
        print(f"  [goout.net/vystavy] strana {strana + 1}: {len(davka)} záznamů")

        scroll_id = (j.get("meta") or {}).get("nextScrollId")
        if not scroll_id:
            break
        time.sleep(PAUZA)

    return schedules, included


def scrape(od, do):
    """
    Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list RAW položek — jedna
    výstava = jedna položka, doprovodný program odfiltrovaný.
    """
    schedules, included = _stahni_schedules(od, do)
    events = included["events"]
    venues = included["venues"]
    images = included["images"]

    # grouped=true vrací zpravidla jeden záznam na výstavu, ale pro jistotu
    # seskupíme přes event.id (deterministicky, jako ostatní goout scrapery)
    skupiny = {}
    for s in schedules:
        eid = (s.get("relationships", {}).get("event") or {}).get("id")
        if eid is not None:
            skupiny.setdefault(str(eid), []).append(s)

    polozky = []
    vyhozeno = 0
    stalych = 0
    mimo_zanr = 0
    for eid, sched_list in skupiny.items():
        event = events.get(eid)
        nazev = _lokal(event, "name")
        if not nazev:
            continue
        if _je_balast(nazev):
            vyhozeno += 1
            continue
        if not _zanr_sedi(event):
            mimo_zanr += 1
            continue

        sched_list.sort(key=lambda s: s.get("attributes", {}).get("startAt") or "")
        prvni = sched_list[0]

        # stálá expozice = trvalka, ne aktuální dění → ven (viz bod 4 v docstringu)
        if prvni.get("attributes", {}).get("isPermanent"):
            stalych += 1
            continue

        datum_od, datum_do = _trvani(event, prvni)
        # druhá pojistka: goout `isPermanent` nedává spolehlivě (ATLAS běží 4 roky
        # a označený není), tak co trvá přes rok bereme jako expozici taky
        if je_trvalka(datum_od, datum_do):
            stalych += 1
            continue
        venue = venues.get(str((prvni.get("relationships", {}).get("venue") or {}).get("id")))

        polozky.append(polozka(
            ZDROJ,
            nazevCz=nazev,
            autor=_kurator(event),
            zanr=_zanr(event),
            datumOd=datum_od,
            datumDo=datum_do,
            misto=_lokal(venue, "name"),
            adresa=(venue or {}).get("attributes", {}).get("address"),
            url=_lokal(prvni, "siteUrl"),
            cena=_cena(prvni.get("attributes", {})),
            thumbnail=_thumbnail(event, images),
            popis=(_lokal(event, "description") or "")[:MAX_POPIS] or None,
        ))

    if vyhozeno or stalych or mimo_zanr:
        print(f"  [goout.net/vystavy] odfiltrováno: stálé expozice {stalych}, "
              f"mimo žánr {mimo_zanr}, doprovodný program {vyhozeno}")
    return polozky
