"""Dolije pole `dobovaZatez` (0-10) do data/filmy_doma.json z dávkového souboru.

Použití:  python support/pridej_zatez.py cesta/k/davce.json

Dávka = JSON objekt {"<nazevOrig>|<rok>": <0-10>, ...}. Klíč (nazevOrig, rok)
je v datech unikátní. Filmy mimo dávku zůstávají beze změny (pole se nepřidá
ani nepřepíše); film v dávce, který v datech není, skript vypíše a skončí chybou.
Po zápisu ověří, že se kromě `dobovaZatez` nezměnil ani jeden bajt hodnot.
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "filmy_doma.json"


def klic(f):
    return f"{f['nazevOrig']}|{f.get('rok')}"


def main(davka_cesta):
    davka = json.loads(Path(davka_cesta).read_text(encoding="utf-8"))
    original = DATA.read_text(encoding="utf-8")
    d = json.loads(original)
    filmy = d["filmy"]

    podle_klice = {klic(f): f for f in filmy}
    chybi = [k for k in davka if k not in podle_klice]
    if chybi:
        print("V datech nejsou:", *chybi, sep="\n  ")
        sys.exit(1)

    for k, z in davka.items():
        if not (isinstance(z, int) and 0 <= z <= 10):
            print(f"Neplatná zátěž {z!r} u {k}")
            sys.exit(1)
        podle_klice[k]["dobovaZatez"] = z

    # Kontrola: bez dobovaZatez musí být data 1:1 s originálem.
    puvodni = json.loads(original)
    for f in puvodni["filmy"]:
        f.pop("dobovaZatez", None)
    kopie = json.loads(json.dumps(d))
    for f in kopie["filmy"]:
        f.pop("dobovaZatez", None)
    assert puvodni == kopie, "Něco kromě dobovaZatez se změnilo — nezapisuju."

    # Zachovat formát originálu: indent 2, CRLF, bez escapování unicode.
    text = json.dumps(d, ensure_ascii=False, indent=2).replace("\n", "\r\n")
    DATA.write_text(text, encoding="utf-8", newline="")
    celkem = sum("dobovaZatez" in f for f in filmy)
    print(f"Zapsáno {len(davka)} z dávky, celkem má dobovaZatez {celkem}/{len(filmy)} filmů.")


if __name__ == "__main__":
    main(sys.argv[1])
