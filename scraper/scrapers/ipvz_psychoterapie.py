"""
Subscraper: vzdělávací akce z portal.ipvz.cz (Institut postgraduálního vzdělávání
ve zdravotnictví) — katedra klinické psychologie (studyDepartmentId=58).

Portál je React SPA, ale program tahá z veřejného JSON API (stejný vzor jako
goout — voláme endpoint napřímo, bez tokenů, stačí normální User-Agent):

  GET https://portal.ipvz.cz/api/v1/portal/educationEventTerms/list?studyDepartmentId=58

Odpověď vrací VŠECHNY termíny katedry naráz (records[], desítky kusů), takže
žádné stránkování ani serverový datumový filtr netřeba — okno filtrujeme
lokálně. Jeden record = jeden TERMÍN (dateFrom/dateTo, price, facilityName,
locationDescription, annotation, activityList = typ akce). Opakující se akce
("Cyklus jednodenních specializačních seminářů…") má record na každý termín →
seskupíme podle názvu do jedné položky s polem `terminy` (obdoba goout
event.id, jen tady je klíčem název — nic lepšího API nedává).

URL detailu si portál skládá jako /vzdelavaci-akce/{id}-{slug-z-nazvu};
slug vyrábíme stejně (odstranit diakritiku, ne-alfanumerika → pomlčky).
"""

import re
import unicodedata
from collections import OrderedDict

import requests

try:
    from ..common import polozka
    from .psychoterapie_common import TYP_AKCE, v_okne, je_vycvik, odhadni_zanr
except ImportError:  # když se modul spustí samostatně
    from common import polozka
    from scrapers.psychoterapie_common import TYP_AKCE, v_okne, je_vycvik, odhadni_zanr

ZDROJ = "ipvz.cz"
API = "https://portal.ipvz.cz/api/v1/portal/educationEventTerms/list"
KATEDRA = 58  # klinická psychologie (Bobův filtr z URL portálu)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept": "application/json",
}
MAX_TERMINY = 12

# zkoušky a testy nejsou vzdělávací akce ("Test po základním kmeni…")
_ZKOUSKA = re.compile(r"^test\b|atestač|zkoušk", re.I)


def _datum_cas(iso):
    """"2026-09-03T09:00:00" → ("03-09-2026", "09:00"). Chybějící → (None, None)."""
    if not iso or "T" not in iso:
        return None, None
    den, cas = iso.split("T", 1)
    r, m, d = den.split("-")
    return f"{d}-{m}-{r}", cas[:5]


def _slug(nazev):
    """Název → slug pro URL detailu (bez diakritiky, ne-alfanumerika → pomlčky)."""
    bez_hacku = unicodedata.normalize("NFD", nazev)
    bez_hacku = "".join(c for c in bez_hacku if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", bez_hacku.lower())


def _cena(rec):
    """price 1900.0 → "1 900 Kč" (mezera po tisících, jak to píše portál)."""
    price = rec.get("price")
    if not price:
        return None
    return f"{int(price):,}".replace(",", " ") + " Kč"


def _misto(rec):
    """facilityName + destinationName → "IPVZ Budějovická, Praha"."""
    kusy = [rec.get("facilityName"), rec.get("destinationName")]
    return ", ".join(k for k in kusy if k) or None


def _zanr(rec):
    """activityList nese typ akce ("Specializační kurz", "Seminář"…)."""
    aktivity = [a.get("name") for a in rec.get("activityList") or [] if a.get("name")]
    return ", ".join(aktivity[:2]) or None


def scrape(od, do):
    """Hlavní vstup. od/do ve formátu DD-MM-YYYY. Vrací list položek."""
    r = requests.get(API, params={"studyDepartmentId": KATEDRA}, headers=HEADERS, timeout=25)
    r.raise_for_status()
    records = r.json().get("records") or []
    print(f"  [ipvz.cz] záznamů z API: {len(records)}")

    # seskupení termínů téže akce podle názvu (viz docstring), pořadí dle API
    skupiny = OrderedDict()
    for rec in records:
        nazev = (rec.get("name") or "").strip()
        if not nazev:
            continue
        skupiny.setdefault(nazev, []).append(rec)

    polozky = []
    vyrazeno = 0
    for nazev, recs in skupiny.items():
        if je_vycvik(nazev) or _ZKOUSKA.search(nazev):
            vyrazeno += 1
            continue

        # termíny seřazené podle začátku, jen ty v Bobově okně
        recs.sort(key=lambda x: x.get("dateFrom") or "")
        terminy = []
        for rec in recs:
            d_od, cas = _datum_cas(rec.get("dateFrom"))
            d_do, _ = _datum_cas(rec.get("dateTo"))
            if d_od and v_okne(d_od, d_do or d_od, od, do):
                terminy.append({"datum": d_od, "cas": cas, "_rec": rec})
        if not terminy:
            continue

        prvni = terminy[0]["_rec"]
        d_od, cas = _datum_cas(prvni.get("dateFrom"))
        d_do, _ = _datum_cas(prvni.get("dateTo"))
        p = polozka(
            ZDROJ,
            nazevCz=nazev,
            zanr=_zanr(prvni) or odhadni_zanr(nazev),
            datumOd=d_od,
            datumDo=terminy[-1]["datum"] if len(terminy) > 1 else (d_do or d_od),
            cas=cas,
            misto=_misto(prvni),
            adresa=prvni.get("locationDescription"),
            url=f"https://portal.ipvz.cz/vzdelavaci-akce/{prvni.get('id')}-{_slug(nazev)}",
            cena=_cena(prvni),
            popis=(prvni.get("annotation") or "").replace("\r\n", " ").strip() or None,
        )
        if len(terminy) > 1:
            p["terminy"] = [{"datum": t["datum"], "cas": t["cas"]} for t in terminy[:MAX_TERMINY]]
        polozky.append(p)

    if vyrazeno:
        print(f"  [ipvz.cz] vyřazeno (výcviky/zkoušky): {vyrazeno}")
    return polozky
