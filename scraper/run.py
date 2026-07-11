"""
Runner. Spustí subscrapery pro zadané rozmezí datumu a zapíše RAW JSONy do
output/ — jeden soubor na typ akce (víc zdrojů stejného typu se slévá dohromady).

Volitelně jede jen pro vybrané typy akcí (GUI si nechá vypsat dostupné typy a
pustí jen ty zaškrtnuté — ať se nescrapuje všech deset typů, když chceš jen kina).

Použití z příkazky:
    python run.py 12-11-2026 21-11-2026                 # všechny typy
    python run.py 12-11-2026 21-11-2026 koncerty_klasika # jen vybrané typy

Přidání nového zdroje = přidat modul do scrapers/ a dopsat ho do SUBSCRAPERY.
"""

import importlib
import os
import sys

# Windows konzole bývá cp1250 — přepneme výstup na UTF-8, ať čeština v logu neshoří.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from common import zapis_raw
from dedup import deduplikuj

# Seznam subscraperů (název modulu ve scrapers/). Sem přibývají nové zdroje.
# Runner si z každého přečte jeho TYP_AKCE a seskupí je — jeden typ může mít víc zdrojů.
SUBSCRAPERY = [
    "prague_vystavy",
    "prague_koncerty",
    "prague_jazzblues",
]

# Hezké popisky typů akcí pro GUI (slug -> lidský název). Co tu není, spadne na fallback.
POPISKY_TYPU = {
    "vystavy": "Výstavy",
    "koncerty_klasika": "Klasika (vážná hudba)",
    "koncerty_jazzblues": "Jazz & Blues (klubová scéna)",
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# nad kolik řádků RAW souboru varovat (AI krok v Coworku čte ~2000 řádků najednou)
LIMIT_RADKU = 1800


def _registr():
    """Načte subscrapery a seskupí je podle TYP_AKCE: {typ: [(jmeno, modul), …]}."""
    registr = {}
    for jmeno in SUBSCRAPERY:
        modul = importlib.import_module(f"scrapers.{jmeno}")
        registr.setdefault(modul.TYP_AKCE, []).append((jmeno, modul))
    return registr


def dostupne_typy():
    """Seřazený seznam typů akcí, které umíme scrapovat (pro GUI i CLI nápovědu)."""
    return sorted(_registr().keys())


def popisek(typ):
    """Lidský název typu pro GUI. Fallback: slug s podtržítky na mezery, první velké."""
    return POPISKY_TYPU.get(typ, typ.replace("_", " ").capitalize())


def _guardrail(cesta, polozky, log):
    """Po zápisu upozorní, když je soubor moc dlouhý pro AI krok, a ukáže největšího žrouta."""
    try:
        with open(cesta, encoding="utf-8") as f:
            radku = sum(1 for _ in f)
    except OSError:
        return
    if radku <= LIMIT_RADKU:
        return
    zrout = max(polozky, key=lambda p: len(p.get("terminy") or []), default=None)
    detail = ""
    if zrout and zrout.get("terminy"):
        detail = f' Největší žrout: „{zrout.get("nazevCz")}" ({len(zrout["terminy"])} termínů).'
    log(f"  [pozor] soubor má {radku} řádků (AI krok čte ~2000).{detail}")


def spust(od, do, typy=None, log=print):
    """
    Spustí subscrapery pro rozmezí od–do (DD-MM-YYYY). typy = list vybraných TYP_AKCE,
    nebo None pro všechny. log = callback na řádek výstupu (GUI si tím plní okno).
    """
    registr = _registr()
    if typy:
        registr = {t: subs for t, subs in registr.items() if t in typy}

    if not registr:
        log("Nic k scrapování — žádný vybraný typ akce nesedí na dostupné zdroje.")
        return

    for typ, subs in registr.items():
        log(f"=== {popisek(typ)} ({typ}) ===")
        polozky = []  # všechny položky tohoto typu napříč zdroji
        for jmeno, modul in subs:
            log(f"> {jmeno} ({modul.ZDROJ}) ...")
            try:
                nasbirane = modul.scrape(od, do)
            except Exception as e:  # jeden padlý scraper nezabije ostatní
                log(f"  ! chyba v {jmeno}: {e}")
                continue
            polozky.extend(nasbirane)
            log(f"  OK {len(nasbirane)} položek")

        # dedup napříč všemi zdroji daného typu — jedna akce = jedna položka
        cistych = deduplikuj(polozky)
        cesta = zapis_raw(typ, od, do, cistych, OUTPUT_DIR)
        log(f"[uloženo] {cesta}  ({len(polozky)} -> {len(cistych)} po dedup)")
        _guardrail(cesta, cistych, log)
        log("")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Použití: python run.py DD-MM-YYYY DD-MM-YYYY [typ ...]")
        print("Dostupné typy:", ", ".join(dostupne_typy()))
        sys.exit(1)
    od, do = sys.argv[1], sys.argv[2]
    vybrane_typy = sys.argv[3:] or None  # bez uvedení = všechny typy
    spust(od, do, vybrane_typy)
