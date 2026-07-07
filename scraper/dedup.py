"""
Deduplikace RAW položek — generická, nezávislá na typu akce.

Proč: jednu výstavu (koncert, …) vidíme z víc zdrojů. Do AI kroku chceme
pár desítek unikátních akcí, ne stovky duplicit. Slučování musí být
deterministické (vždy stejný výsledek), proto se dělá tady, ne v AI.

Kdy jsou dvě položky tentýž event (PŘÍSNĚ):
    podobnost názvu >= PRAH_NAZEV
    A ZÁROVEŇ (překryv datumů  NEBO  shoda místa)
Samotný název nestačí (dvě různé akce se stejným slovem), samotné datum
taky ne (deset akcí ve stejný den). Radši občasný duplikát než chybné
sloučení dvou různých akcí.

Merge: první záznam je základ, prázdná pole se doplní z dalších.
`zdroj` (str) se ve sloučené položce mění na `zdroje` (list).
"""

from difflib import SequenceMatcher
from datetime import datetime
import unicodedata

PRAH_NAZEV = 0.86  # přísně; výš = míň slučuje, níž = víc riskuje chybná spojení


def _normalizuj(s):
    """malá písmena, bez diakritiky, jen písmena a číslice + mezery."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def _podobnost(a, b):
    return SequenceMatcher(None, _normalizuj(a), _normalizuj(b)).ratio()


def _nazev_shoda(a, b):
    """
    Podobnost názvů odolná vůči rozdílné délce.
    Zdroje často dávají různě dlouhý název téže akce ("Fragmenty paměti"
    vs "Fragmenty paměti – … v zrcadle současného umění"). Proto měříme,
    jak moc se ten KRATŠÍ název (v slovech) schová do delšího (containment),
    ne přímé ratio, které délkový rozdíl přehnaně trestá.

    Jednoslovné/generické názvy touto cestou neprojdou (min. 2 slova),
    tam padáme zpět na přísné znakové ratio.
    """
    ta = set(_normalizuj(a).split())
    tb = set(_normalizuj(b).split())
    if not ta or not tb:
        return 0.0
    mensi = min(len(ta), len(tb))
    if mensi >= 2:
        return len(ta & tb) / mensi  # kolik slov kratšího názvu je v delším
    return _podobnost(a, b)


def _den(s):
    """DD-MM-YYYY -> date, nebo None."""
    try:
        return datetime.strptime(s, "%d-%m-%Y").date()
    except (ValueError, TypeError):
        return None


def _datum_se_prekryva(a, b):
    """Překrývají se intervaly [datumOd, datumDo] obou položek?"""
    a1, a2 = _den(a.get("datumOd")), _den(a.get("datumDo") or a.get("datumOd"))
    b1, b2 = _den(b.get("datumOd")), _den(b.get("datumDo") or b.get("datumOd"))
    if not (a1 and b1):
        return False
    a2, b2 = a2 or a1, b2 or b1
    return a1 <= b2 and b1 <= a2


def _misto_sedi(a, b):
    """Shoda místa — jeden název je podřetězcem druhého, nebo jsou si blízké."""
    ma, mb = _normalizuj(a.get("misto")), _normalizuj(b.get("misto"))
    if not ma or not mb:
        return False
    if ma in mb or mb in ma:
        return True
    return _podobnost(a.get("misto"), b.get("misto")) >= 0.80


def _je_tentyz(a, b):
    if _nazev_shoda(a.get("nazevCz"), b.get("nazevCz")) < PRAH_NAZEV:
        return False
    return _datum_se_prekryva(a, b) or _misto_sedi(a, b)


def _sluc(zaklad, dalsi):
    """Do základu doplní prázdná pole z `dalsi` a přidá jeho zdroj."""
    for k, v in dalsi.items():
        if k in ("zdroj", "zdroje"):
            continue
        if zaklad.get(k) in (None, "") and v not in (None, ""):
            zaklad[k] = v
    for z in dalsi.get("zdroje", []):
        if z not in zaklad["zdroje"]:
            zaklad["zdroje"].append(z)
    return zaklad


def deduplikuj(polozky):
    """Vrátí nový list bez duplicit. Pořadí zachováno podle prvního výskytu."""
    vysledek = []
    for p in polozky:
        p = dict(p)  # neničíme vstup
        # zdroj (str) -> zdroje (list) hned na začátku, ať merge má kam psát
        p["zdroje"] = [p.pop("zdroj")] if p.get("zdroj") else []
        for u in vysledek:
            if _je_tentyz(u, p):
                _sluc(u, p)
                break
        else:
            vysledek.append(p)
    return vysledek
