"""Čekárna filmotéky — mechanická půlka skillu /cekarna.

Dva příkazy:

  python cekarna.py dohledej  [vstup.txt] [vystup.json]
      Pro každý řádek čekárny (název filmu, volitelně rok) najde IMDb ID
      (suggest endpoint), stáhne OMDb data, spočítá vážený průměr a najde
      kandidáty na trailer (YouTube search + ověření přes oEmbed).
      Výstup = pracovní JSON pro Clauda: ten u každého filmu zkontroluje
      shodu, vybere trailer a dopíše texty, skóre a dobovou zátěž.

  python cekarna.py zapis  hotove.json
      Hotové filmy (pole objektů v kontraktu filmotéky) připíše do
      data/filmy_doma_pridane.json. Hlídá povinná pole a duplicity
      (proti filmotéce i proti už přidaným).

Klíč OMDb se bere z proměnné prostředí OMDB_KEY (do repa nikdy!).
Jen standardní knihovna, žádné závislosti.
"""

import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

KOREN = Path(__file__).resolve().parents[3]  # .claude/skills/cekarna → repo
FILMOTEKA = KOREN / "data" / "filmy_doma.json"
PRIDANE = KOREN / "data" / "filmy_doma_pridane.json"
CEKARNA = KOREN / "support" / "cekarna.txt"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

# váhy váženého průměru — stejné jako u filmů v kinech (viz CLAUDE.md)
VAHY = {"imdb": 0.5, "metacritic": 0.3, "rottenTomatoes": 0.2}


def http(url, json_out=True):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read().decode("utf-8", errors="replace")
    return json.loads(data) if json_out else data


def bez_diakritiky(text):
    t = unicodedata.normalize("NFD", str(text or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


# ---------- dohledej ----------

def rozeber_radek(radek):
    """'Marketa Lazarová 1967' → ('Marketa Lazarová', 1967, None).
    Rok je volitelný; na konec řádku jde dát i natvrdo IMDb ID ('Kristián 1939 tt0167242')
    pro filmy, které suggest nenajde."""
    tt = re.search(r"\b(tt\d{6,9})\b", radek)
    radek = re.sub(r"\btt\d{6,9}\b", "", radek).strip()
    m = re.match(r"^(.*?)[\s,;(]+((?:18|19|20)\d\d)\)?\s*$", radek)
    if m:
        return m.group(1).strip(), int(m.group(2)), tt and tt.group(1)
    return radek.strip(), None, tt and tt.group(1)


def imdb_kandidati(nazev, rok=None):
    # s rokem se ptáme nejdřív "název rok" — suggest pak najde i staré české filmy,
    # které pod holým názvem utonou mezi lidmi (Kristián → herci jménem Kristian)
    if rok:
        s_rokem = _suggest(f"{nazev} {rok}")
        if s_rokem:
            return s_rokem
    return _suggest(nazev)


def _suggest(nazev):
    slug = bez_diakritiky(nazev)
    if not slug:
        return []
    url = f"https://v2.sg.media-imdb.com/suggestion/{slug[0]}/{urllib.parse.quote(slug)}.json"
    try:
        d = http(url).get("d", [])
    except Exception:
        return []
    # filmy i seriály (Bob si do čekárny dává i Vinyl nebo Babylon Berlin), ne lidi
    return [
        {"id": x["id"], "nazev": x.get("l"), "rok": x.get("y"), "druh": x.get("q"),
         "herci": x.get("s"), "rank": x.get("rank")}
        for x in d
        if x.get("id", "").startswith("tt")
        and x.get("qid") in ("movie", "tvMovie", "short", "video", "tvSeries", "tvMiniSeries")
    ]


def vyber_imdb(kandidati, rok):
    """Suggest řadí podle relevance k dotazu → bereme první (s rokem první, co sedí ±1).
    NE podle rank (popularity): u 'Pelíšky' by vyhrál Dodgeball. Výběr je jen návrh,
    Claude ho v skillu kontroluje proti režii/roku/ději z OMDb."""
    if not kandidati:
        return None
    if rok:
        return next((k for k in kandidati if k["rok"] and abs(k["rok"] - rok) <= 1), None)
    return kandidati[0]


def podobnost(a, b):
    from difflib import SequenceMatcher
    return round(SequenceMatcher(None, bez_diakritiky(a), bez_diakritiky(b)).ratio(), 2)


def omdb(imdb_id):
    klic = os.environ.get("OMDB_KEY")
    if not klic:
        sys.exit("Chybí proměnná prostředí OMDB_KEY.")
    d = http(f"https://www.omdbapi.com/?i={imdb_id}&apikey={klic}")
    if d.get("Response") == "False":
        # limit nebo klíč = stop, ať se to neplete s filmem bez hodnocení
        if "limit" in d.get("Error", "").lower() or "key" in d.get("Error", "").lower():
            sys.exit(f"OMDb odmítl: {d.get('Error')}")
        return None
    return d


def hodnoceni_z_omdb(d):
    def cislo(s, fn):
        try:
            return fn(s)
        except (TypeError, ValueError):
            return None

    imdb = cislo(d.get("imdbRating"), float)
    mc = cislo(d.get("Metascore"), int)
    rt = None
    for r in d.get("Ratings", []):
        if r.get("Source") == "Rotten Tomatoes":
            rt = cislo(r.get("Value", "").rstrip("%"), int)
    h = {"imdb": imdb, "metacritic": mc, "rottenTomatoes": rt}
    body = {"imdb": imdb * 10 if imdb is not None else None, "metacritic": mc, "rottenTomatoes": rt}
    dostupne = {k: v for k, v in body.items() if v is not None}
    if dostupne:
        suma_vah = sum(VAHY[k] for k in dostupne)
        h["vazenePrumer"] = round(sum(v * VAHY[k] for k, v in dostupne.items()) / suma_vah, 1)
    else:
        h["vazenePrumer"] = None
    chybi = [n for n, k in (("IMDb", "imdb"), ("Metacritic", "metacritic"), ("RT", "rottenTomatoes")) if h[k] is None]
    pozn = f"Zdroj: OMDb pro IMDb ID {d.get('imdbID')}."
    if chybi and dostupne:
        pozn += f" OMDb neuvádí: {', '.join(chybi)}; váhy přepočteny."
    h["poznamkaHodnoceni"] = pozn
    return h


def trailery(dotaz, kolik=4):
    """YouTube search (HTML) → videoId → oEmbed (ověří existenci, vrátí titulek)."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(dotaz)
    try:
        html = http(url, json_out=False)
    except Exception:
        return []
    ids = []
    for vid in re.findall(r'"videoId":"([\w-]{11})"', html):
        if vid not in ids:
            ids.append(vid)
    vysledek = []
    for vid in ids[: kolik * 2]:
        watch = f"https://www.youtube.com/watch?v={vid}"
        try:
            o = http("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(watch))
        except Exception:
            continue  # smazané/soukromé/neembedovatelné video
        vysledek.append({"url": watch, "titulek": o.get("title"), "kanal": o.get("author_name")})
        if len(vysledek) >= kolik:
            break
    return vysledek


def nacti_json(cesta, vychozi):
    if cesta.exists():
        return json.loads(cesta.read_text(encoding="utf-8"))
    return vychozi


def zname_filmy():
    """Mapa název (bez diakritiky) → množina roků všeho, co už v datech je
    (filmotéka + čekárna). Rok se porovnává s tolerancí ±1 — OMDb, IMDb
    i films101 se u premiér na přelomu roku rozcházejí (Stalker 1979 vs 1980)."""
    mapa = {}
    for f in nacti_json(FILMOTEKA, {"filmy": []})["filmy"] + nacti_json(PRIDANE, {"filmy": []})["filmy"]:
        for n in (f.get("nazevOrig"), f.get("nazevCz")):
            if n:
                mapa.setdefault(bez_diakritiky(n), set()).add(int(f["rok"]) if str(f.get("rok") or "").isdigit() else None)
    return mapa


def je_znamy(mapa, nazev, rok):
    roky = mapa.get(bez_diakritiky(nazev))
    if not roky:
        return False
    rok = int(rok) if str(rok or "").isdigit() else None
    return rok is None or None in roky or any(abs(r - rok) <= 1 for r in roky if r)


def dohledej(vstup, vystup):
    radky = [r.strip() for r in Path(vstup).read_text(encoding="utf-8-sig").splitlines()]
    radky = [r for r in radky if r and not r.startswith("#")]
    zname = zname_filmy()
    pridane_ids = {f.get("imdbId") for f in nacti_json(PRIDANE, {"filmy": []})["filmy"]}
    vysledky = []
    for radek in radky:
        nazev, rok, tt = rozeber_radek(radek)
        kandidati = imdb_kandidati(nazev, rok)
        if tt:  # ručně zadané ID má přednost
            vybrany = next((k for k in kandidati if k["id"] == tt), {"id": tt, "nazev": nazev, "rok": rok})
        else:
            vybrany = vyber_imdb(kandidati, rok)
        polozka = {"vstup": radek, "imdbKandidati": kandidati[:6], "imdbVybrany": vybrany}
        if vybrany:
            d = omdb(vybrany["id"])
            if d:
                # rok bereme z IMDb (rok vzniku), OMDb "Year" bývá rok premiéry
                rok_filmu = vybrany.get("rok") or (d.get("Year") or "")[:4]
                polozka["rok"] = str(rok_filmu)
                polozka["omdb"] = {k: d.get(k) for k in (
                    "Title", "Year", "Director", "Genre", "Country", "Language", "Runtime", "Plot", "Actors")}
                polozka["hodnoceni"] = hodnoceni_z_omdb(d)
                polozka["duplicita"] = (
                    vybrany["id"] in pridane_ids
                    or je_znamy(zname, d.get("Title"), rok_filmu)
                    or je_znamy(zname, vybrany["nazev"], rok_filmu)
                    or je_znamy(zname, nazev, rok_filmu)
                )
                # anglický titul + titul ze vstupu (u českých filmů najde české trailery);
                # vybírá Claude podle titulku/kanálu, skript jen sbírá ověřené kandidáty
                tr = trailery(f"{d.get('Title')} {rok_filmu} trailer")
                if bez_diakritiky(nazev) != bez_diakritiky(d.get("Title")):
                    tr += [t for t in trailery(f"{nazev} {rok_filmu} trailer")
                           if t["url"] not in {x["url"] for x in tr}]
                polozka["trailery"] = tr
        # OK = název sedí i textově; ?! = jiný název (překlad? omyl?) → Claude ověří;
        # ?? = nic nenalezeno → Claude dohledá ID a doplní ho do řádku (… tt1234567)
        if vybrany:
            polozka["shodaNazvu"] = max(podobnost(nazev, vybrany["nazev"] or ""),
                                        podobnost(nazev, (polozka.get("omdb") or {}).get("Title") or ""))
        znacka = "?? " if not vybrany else ("OK " if tt or polozka["shodaNazvu"] >= 0.8 else "?! ")
        print(f"{znacka} {radek} → {vybrany and vybrany['nazev']} ({vybrany and vybrany['rok']})"
              + (" [UŽ JE V DATECH]" if polozka.get("duplicita") else ""))
        vysledky.append(polozka)
    Path(vystup).write_text(json.dumps(vysledky, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nPracovní JSON: {vystup}")


# ---------- zapis ----------

POVINNA = ("nazevCz", "nazevOrig", "rok", "rezie", "zanr", "popis", "duvodSkore",
           "estetickeSkore", "dobovaZatez", "hodnoceni", "imdbId")


def zapis(hotove):
    nove = json.loads(Path(hotove).read_text(encoding="utf-8"))
    soubor = nacti_json(PRIDANE, {
        "typAkce": "filmy_doma",
        "poznamka": "Čekárna — filmy přidané Bobem přes skill /cekarna. Appka je přilepí k filmotéce.",
        "filmy": [],
    })
    zname = zname_filmy()
    ids = {f.get("imdbId") for f in soubor["filmy"]}
    pridano = 0
    for f in nove:
        chybi = [k for k in POVINNA if k not in f]
        if chybi:
            sys.exit(f"{f.get('nazevOrig')}: chybí pole {chybi}")
        if not (0 <= f["dobovaZatez"] <= 10) or not (0 <= f["estetickeSkore"] <= 100):
            sys.exit(f"{f['nazevOrig']}: skóre/zátěž mimo rozsah")
        if f["imdbId"] in ids or je_znamy(zname, f["nazevOrig"], f["rok"]):
            print(f"přeskakuji duplicitu: {f['nazevOrig']} ({f['rok']})")
            continue
        # zbytek kontraktu filmotéky, ať karta i dashboard mají, co čekají
        f.setdefault("trailerUrl", None)
        f.setdefault("vlastniRecenze", None)
        f.setdefault("specialniProjekce", False)
        f.setdefault("specialniPopis", None)
        f.setdefault("projekce", [])
        f.setdefault("pridanoAt", datetime.now().strftime("%Y-%m-%d"))
        soubor["filmy"].append(f)
        ids.add(f["imdbId"])
        pridano += 1
    soubor["vygenerovanoAt"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    PRIDANE.write_text(json.dumps(soubor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Přidáno {pridano} filmů, čekárna má celkem {len(soubor['filmy'])}.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in ("dohledej", "zapis"):
        sys.exit(__doc__)
    if sys.argv[1] == "dohledej":
        vstup = sys.argv[2] if len(sys.argv) > 2 else CEKARNA
        vystup = sys.argv[3] if len(sys.argv) > 3 else "cekarna_prace.json"
        dohledej(vstup, vystup)
    else:
        zapis(sys.argv[2])
