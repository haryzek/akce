"""
Společný základ pro všechny subscrapery.

Každý subscraper (soubor v scrapers/) musí vystavit:
    TYP_AKCE : str    — např. "vystavy", "koncerty" (název výsledného JSONu)
    ZDROJ    : str    — např. "prague.eu" (píše se do každé položky)
    def scrape(od: str, do: str) -> list[dict]
         od/do jsou datumy ve formátu "DD-MM-YYYY"
         vrací list položek ve formátu polozka() níže

Runner (run.py) subscrapery posbírá, sloučí položky se stejným TYP_AKCE
do jednoho souboru a zapíše výsledný RAW JSON do output/<typAkce>.json.
"""

from datetime import datetime
import json
import os

# 14 polí RAW kontraktu. Každé smí být None — appka i AI krok to musí přežít.
POLE = [
    "zdroj", "nazevCz", "nazevOrig", "autor", "zanr",
    "datumOd", "datumDo", "cas", "misto", "adresa",
    "url", "cena", "thumbnail", "popis",
]


def je_trvalka(datum_od, datum_do, prah_dni=365):
    """
    Je to stálá expozice podle délky trvání? (DD-MM-YYYY, oba můžou být None)

    Pojistka pro typy s dlouhotrvajícími akcemi — hlavně výstavy. goout sice má
    příznak `isPermanent`, ale nedává ho spolehlivě (ATLAS běží 4 roky a označený
    není) a prague.eu žádný takový příznak nemá vůbec. Co běží přes rok, není
    výstava, ale expozice — a Bobovi jde o to, co se právě děje.

    Práh 365 dní je se slušnou rezervou: nejdelší legitimní výstava v reálných
    datech měla 178 dní.
    """
    try:
        od = datetime.strptime(datum_od, "%d-%m-%Y")
        do = datetime.strptime(datum_do, "%d-%m-%Y")
    except (ValueError, TypeError):
        return False  # bez datumů nesoudíme, radši nechat projít
    return (do - od).days >= prah_dni


def polozka(zdroj, **kwargs):
    """Vyrobí jednu položku se všemi poli; chybějící doplní None."""
    p = {k: None for k in POLE}
    p["zdroj"] = zdroj
    for k, v in kwargs.items():
        if k not in POLE:
            raise KeyError(f"Neznámé pole '{k}' — není v RAW kontraktu.")
        # prázdný string bereme jako None, ať je JSON čistý
        p[k] = v if v not in ("", None) else None
    return p


def zapis_raw(typ_akce, od, do, polozky, output_dir):
    """Zabalí položky do RAW obálky a zapíše output/<typAkce>.json."""
    obal = {
        "typAkce": typ_akce,
        "scrapedAt": datetime.now().isoformat(timespec="seconds"),
        "obdobiOd": od.replace("-", "."),
        "obdobiDo": do.replace("-", "."),
        "polozky": polozky,
    }
    os.makedirs(output_dir, exist_ok=True)
    cesta = os.path.join(output_dir, f"{typ_akce}.json")
    with open(cesta, "w", encoding="utf-8") as f:
        json.dump(obal, f, ensure_ascii=False, indent=2)
    return cesta
