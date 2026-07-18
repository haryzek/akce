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

AGRESIVNÍ PROFILY (`deduplikuj(polozky, profil="party")`) — zapínají se per typ
akce v run.py (`PROFIL_DEDUP`). Přidávají DRUHOU cestu ke sloučení pro případy,
kdy přísný práh na název nestačí. Profil je per typ schválně: co je bezpečné
u klubovek, je nebezpečné u výstav a naopak.

  "party"   — místo + stejný konkrétní den + aspoň jedno výrazné společné slovo.
              Proč: ra.co a goout dávají téže noci různě dlouhý název ("Poseidon"
              vs "POSEIDON: Paralich, TRANSmisia, PAY2PLAY, Big Lil & XENEA
              LUMRA"). Na jednom klubu v jeden večer bývá jedna akce, takže je to
              bezpečné. Guardy: GENERICKA_SLOVA (aby dvě párty nespojilo samotné
              "techno") a SATELITNI_SLOVA (aby se afterparty neslila s hlavní akcí).

Proč VÝSTAVY profil nemají (a nedávej jim ho): zkoušeli jsme pro ně tolerantnější
práh na název (0.62) vykoupený povinným místem i překryvem trvání. Na reálných
datech (prague.eu + goout, 299 položek) přidal přesně 4 sloučení a všechna byla
chybná — "Hornictví" + "Hutnictví" v Národním technickém muzeu, "Ateliér
Františka Bílka" + "Grafická dílna Františka Bílka". Výstavy mají krátké
popisné názvy, které si jsou v jedné instituci přirozeně podobné, aniž by šlo
o tutéž věc. Přísné pravidlo tu funguje dobře; skutečné duplicity se ukázaly
být problém metriky názvu (viz `_nazev_shoda`), ne prahu.
"""

from difflib import SequenceMatcher
from datetime import datetime
import unicodedata

PRAH_NAZEV = 0.86  # přísně; výš = míň slučuje, níž = víc riskuje chybná spojení

# --- agresivní profily ---
PRAH_NAZEV_AGRESIVNI = 0.50  # party: alternativa ke společnému slovu
MIN_DELKA_SLOVA = 4          # kratší slova nejsou dost výrazná na identifikaci akce

# Slova, která v názvech klubovek nic neidentifikují — nesmí sama o sobě spojit
# dvě akce ("Techno Night Prague" vs "Techno Open Air" je pořád jiná párty).
GENERICKA_SLOVA = {
    "praha", "prague", "party", "night", "nights", "club", "open", "air",
    "live", "show", "festival", "presents", "present", "invites", "with",
    "feat", "featuring", "vol", "part", "edition", "summer", "winter",
    "spring", "autumn", "afterparty", "after", "warmup", "closing", "opening",
    "techno", "house", "disco", "rave", "dance", "music", "sound", "sounds",
    "special", "guest", "guests", "session", "sessions", "and", "the",
}

# Slova, která z akce dělají SATELIT hlavní akce. Afterparty ke koncertu je na
# stejném místě, ve stejný den a se stejným headlinerem v názvu — agresivní
# pravidlo by ji jinak slilo s hlavní akcí ("Ben Böhmer - PRAGUE / LIVE" vs
# "Ben Böhmer Official Afterparty"). Když je má jen jedna ze dvou položek,
# sloučení zamítáme.
SATELITNI_SLOVA = {"afterparty", "after", "warmup", "preparty", "pregame", "aftershow"}


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


def _kmen(slovo):
    """
    Hrubý kmen slova — uřízne českou koncovku, ať se "Muzeum Karla Zemana"
    potká se "Stálá expozice Muzea Karla Zemana". Žádná morfologie, jen délkové
    pravidlo: dost dlouhá slova zkrátíme, krátká necháme být (u nich by ořez
    smazal význam a spojil nesouvisející věci).
    """
    if not slovo:
        return slovo
    if len(slovo) >= 6:
        return slovo[:-2]
    if len(slovo) >= 5:
        return slovo[:-1]
    return slovo


def _nazev_shoda(a, b):
    """
    Podobnost názvů odolná vůči rozdílné délce.
    Zdroje často dávají různě dlouhý název téže akce ("Fragmenty paměti"
    vs "Fragmenty paměti – … v zrcadle současného umění"). Proto měříme,
    jak moc se ten KRATŠÍ název (v slovech) schová do delšího (containment),
    ne přímé ratio, které délkový rozdíl přehnaně trestá.

    Jednoslovné/generické názvy touto cestou neprojdou (min. 2 slova),
    tam padáme zpět na přísné znakové ratio.

    Bereme MAXIMUM z containmentu a znakového ratia — každá metrika chytá jiný
    typ rozdílu a nepřítomnost jedné nesmí přebít druhou. Např. "1796—1917:
    Umění dlouhého století" vs "1796–1918: Umění dlouhého století" je zjevně
    tatáž výstava (ratio 0.97), ale containment ji kvůli jednomu odlišnému
    tokenu (1917/1918) srazí na 0.80 a přísný práh by ji rozdělil.
    """
    ta = {_kmen(s) for s in _normalizuj(a).split()}
    tb = {_kmen(s) for s in _normalizuj(b).split()}
    if not ta or not tb:
        return 0.0
    mensi = min(len(ta), len(tb))
    if mensi >= 2:
        containment = len(ta & tb) / mensi  # kolik slov kratšího názvu je v delším
        return max(containment, _podobnost(a, b))
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


# --- agresivní režim (jen pro typy uvedené v run.py) ---

def _dny(p):
    """
    Množina konkrétních dní akce. Z `terminy` když jsou, jinak z datumOd/datumDo.
    Schválně NE celý interval mezi nimi — u klubovek se porovnávají konkrétní
    večery, roztažený interval by zbytečně zvyšoval riziko chybného sloučení.
    """
    dny = set()
    for t in p.get("terminy") or []:
        d = _den(t.get("datum"))
        if d:
            dny.add(d)
    if not dny:
        for klic in ("datumOd", "datumDo"):
            d = _den(p.get(klic))
            if d:
                dny.add(d)
    return dny


def _sdili_den(a, b):
    """Mají obě položky aspoň jeden společný konkrétní den?"""
    da, db = _dny(a), _dny(b)
    return bool(da and db and (da & db))


def _vyrazna_slova(nazev):
    """Slova z názvu, která něco identifikují — dost dlouhá a ne generická."""
    return {
        s for s in _normalizuj(nazev).split()
        if len(s) >= MIN_DELKA_SLOVA and s not in GENERICKA_SLOVA
    }


def _nazev_aspon_naznacuje(a, b):
    """
    Slabší test názvu pro agresivní režim: stačí jedno výrazné společné slovo
    (typicky název akce/promotéra), nebo obstojná celková podobnost.
    """
    if _vyrazna_slova(a.get("nazevCz")) & _vyrazna_slova(b.get("nazevCz")):
        return True
    return _nazev_shoda(a.get("nazevCz"), b.get("nazevCz")) >= PRAH_NAZEV_AGRESIVNI


def _je_satelit(nazev):
    """Je to afterparty/warmup (tedy doprovodná akce, ne ta hlavní)?"""
    return bool(set(_normalizuj(nazev).split()) & SATELITNI_SLOVA)


def _je_tentyz_party(a, b):
    """Profil "party": místo + konkrétní den + náznak shody názvu."""
    if _je_satelit(a.get("nazevCz")) != _je_satelit(b.get("nazevCz")):
        return False  # hlavní akce vs její afterparty — dvě různé věci
    return _misto_sedi(a, b) and _sdili_den(a, b) and _nazev_aspon_naznacuje(a, b)


# Registr profilů. Klíč = hodnota v PROFIL_DEDUP v run.py.
PROFILY = {
    "party": _je_tentyz_party,
}


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


def deduplikuj(polozky, profil=None):
    """
    Vrátí nový list bez duplicit. Pořadí zachováno podle prvního výskytu.

    `profil` = název agresivního profilu ("party", "vystavy") nebo None pro
    samotné přísné pravidlo. Viz docstring modulu. Nastavuje se per typ akce
    v run.py (`PROFIL_DEDUP`).
    """
    navic = PROFILY.get(profil)
    vysledek = []
    for p in polozky:
        p = dict(p)  # neničíme vstup
        # zdroj (str) -> zdroje (list) hned na začátku, ať merge má kam psát
        p["zdroje"] = [p.pop("zdroj")] if p.get("zdroj") else []
        for u in vysledek:
            if _je_tentyz(u, p) or (navic and navic(u, p)):
                _sluc(u, p)
                break
        else:
            vysledek.append(p)
    return vysledek
