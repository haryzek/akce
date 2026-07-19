"""
Sdílené helpery pro subscrapery typu "odborne_psychoterapie".

Sedm zdrojů (ČAP, ČSPP, ČSP, PVŠPS, ČPS, AKP, IPVZ) = sedm různých mechanik,
ale všechny řeší stejné tři věci: (1) vylovit české datumy z volného textu,
(2) rozhodnout, jestli akce spadá do Bobova okna, (3) vyhodit dlouhodobé
výcviky a jinou hrubou vatu už ve scraperu. To bydlí tady, ať se to nekopíruje
sedmkrát. Mechaniku stahování si každý zdroj řeší po svém ve svém modulu.

Bobovo zadání pro tenhle typ: KRÁTKÉ, víceméně jednorázové odborné akce pro
terapeuty (semináře, webináře, přednášky, konference, supervize). NE dlouhodobé
výcviky, NE výuka/školy, NE členské schůze. Scraper filtruje jen to tvrdé a
jednoznačné (výcvik v názvu, akce delší než ~měsíc); jemné rozhodování nechává
na Cowork promptu.
"""

import re
from datetime import datetime

TYP_AKCE = "odborne_psychoterapie"  # jeden slug pro všech 7 zdrojů — runner je slije


def parsuj_den(ddmmyyyy):
    """"18-07-2026" → date, nebo None když formát nesedí."""
    try:
        return datetime.strptime(ddmmyyyy, "%d-%m-%Y").date()
    except (ValueError, TypeError):
        return None


def v_okne(datum_od, datum_do, okno_od, okno_do):
    """
    Překrývá se trvání akce s Bobovým oknem? Všechna data DD-MM-YYYY.
    Akce bez datumu radši projde (rozhodne Cowork), stejně jako u výstav.
    """
    a_od = parsuj_den(datum_od)
    a_do = parsuj_den(datum_do) or a_od
    o_od = parsuj_den(okno_od)
    o_do = parsuj_den(okno_do)
    if a_od is None:
        return True
    if o_do and a_od > o_do:
        return False
    if o_od and a_do < o_od:
        return False
    return True


# Tvrdý filtr názvů: dlouhodobé výcvikové programy nejsou jednorázová akce.
# Schválně jen jednoznačná slova — "seminář o výcviku" tu nehrozí, česká scéna
# slovo "výcvik" používá výhradně pro dlouhodobé programy.
_VYCVIK = re.compile(r"výcvik|vycvik|dlouhodobý kurz|tříletý|trilety|dvouletý", re.I)


def je_vycvik(nazev):
    """Podle názvu: dlouhodobý výcvikový program → pryč už ve scraperu."""
    return bool(nazev and _VYCVIK.search(nazev))


def je_dlouhodoba(datum_od, datum_do, prah_dni=45):
    """
    Akce trvající přes ~1,5 měsíce = vícemodulový kurz/výcvik, ne jednorázovka.
    (Obdoba je_trvalka() u výstav, jen s kratším prahem — víkendovka má 2-3 dny,
    konference týden; co má víc než měsíc a půl, je vzdělávací PROGRAM.)
    """
    od, do = parsuj_den(datum_od), parsuj_den(datum_do)
    if not od or not do:
        return False  # bez datumů nesoudíme
    return (do - od).days >= prah_dni


# --- vylovení datumů z českého volného textu ---
# Chytá "16.9.2026", "2. 12. 2026" i rozstřelené "2 . 12 .20 26" (Google Sites
# na AKP láme datum přes několik <span>ů, takže mezery můžou být kdekoli).
_DATUM = re.compile(r"(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{2}\s*\d{2}|\d{4})")
# Rozsah "23.-24.7.2026" — první den bez měsíce, měsíc a rok se dědí z druhého.
_ROZSAH = re.compile(r"(\d{1,2})\.\s*[-–]\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{4})")


def _slozit(den, mesic, rok):
    """Kousky datumu (stringy, klidně s mezerami) → "DD-MM-YYYY", nebo None."""
    try:
        d, m, r = int(den), int(mesic), int(re.sub(r"\s", "", rok))
        datetime(r, m, d)  # validace (31.2. apod.)
        return f"{d:02d}-{m:02d}-{r}"
    except ValueError:
        return None


def najdi_datumy(text):
    """
    Všechny datumy z volného textu, seřazené, formát DD-MM-YYYY.
    Umí i rozsah "23.-24.7.2026" (vrátí oba krajní dny).
    """
    if not text:
        return []
    nalezene = set()
    for m in _ROZSAH.finditer(text):
        d1, d2, mesic, rok = m.groups()
        for den in (d1, d2):
            datum = _slozit(den, mesic, rok)
            if datum:
                nalezene.add(datum)
    for m in _DATUM.finditer(text):
        datum = _slozit(*m.groups())
        if datum:
            nalezene.add(datum)
    return sorted(nalezene, key=parsuj_den)


# Čas: napřed dvojtečková podoba (17:00), pak tečková (9.30) — ta ale s negativním
# lookaheadem, ať se z datumu "16.9.2026" nestane čas.
_CAS_DVOJTECKA = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
_CAS_TECKA = re.compile(r"\b([01]?\d|2[0-3])\.([0-5]\d)\b(?!\s*\.?\s*\d)")


def najdi_cas(text):
    """První čas ve volném textu → "HH:MM", nebo None."""
    if not text:
        return None
    m = _CAS_DVOJTECKA.search(text) or _CAS_TECKA.search(text)
    if not m:
        return None
    return f"{int(m.group(1)):02d}:{m.group(2)}"


# Odhad žánru z názvu — hrubé škatulky pro kartu (pod názvem, když chybí autor).
_ZANRY = [
    ("webinář", re.compile(r"webin", re.I)),
    ("konference", re.compile(r"konference|sympozi", re.I)),
    ("přednáška", re.compile(r"přednáš|prednas", re.I)),
    ("supervize", re.compile(r"superviz", re.I)),
    ("workshop", re.compile(r"workshop|dílna", re.I)),
    ("kurz", re.compile(r"kurz", re.I)),
    ("seminář", re.compile(r"seminá|semina", re.I)),
]


def odhadni_zanr(text):
    """Z názvu (příp. popisu) odhadne typ akce: webinář/seminář/konference…"""
    if not text:
        return None
    for zanr, vzor in _ZANRY:
        if vzor.search(text):
            return zanr
    return None
