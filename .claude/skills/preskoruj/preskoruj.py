"""Mechanika rituálu /preskoruj — Bobův žebříček → profil → přeskórování filmotéky.

Příkazy (spouštět z kořene repa, `python -I .claude/skills/preskoruj/preskoruj.py …`):

  zebricek <vystup.json>
      Bobova čísla ze zálohy local/akce-zaloha.json — kotvy + dopočet z pozice per
      druh (film / serial / dokument), ruční přeřazení druhu; 1:1 jako appka
      (prepocitejSkoreZebricku v js/app.js). Výstup: seznam filmů v pořadí žebříčku
      s poli nazev, nazevCz, rok, rezie, zanr, druh, poradi, bob, kotva, ai, f101, imdb.

  test-priprav <zebricek.json> <adresar>
      Rozdělí žebříček na známou část (2/3) a skrytou testovací (1/3, stratifikovaně
      podle skóre) → znamy.json (s čísly) + odhadni.json (bez čísel) + pravda.json.

  test-vyhodnot <adresar> <predikce.json>
      Porovná odhady s pravdou: průměrná chyba, Spearman, posun, srovnání se starým
      AI skóre a s hloupým odhadem „všem průměr". Vypíše největší chyby.

  davky <adresar> [velikost=300]
      Celá filmotéka + čekárna v kompaktní podobě po dávkách davka_NN.json
      ({klic, nazev, rok, rezie, zanr, f101, imdb}). Klíč = "nazevOrig|rok".

  slij <adresar>
      Načte všechny vysledek_NN.json ({klic: skóre 0–100}), zkontroluje úplnost
      a rozsahy a zapíše `estetickeSkore` do data/filmy_doma.json
      a data/filmy_doma_pridane.json. Ověří, že se nic jiného nezměnilo,
      a zachová formát souborů (indent 2, konce řádků, unicode).
"""
import json
import random
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ZALOHA = ROOT / "local" / "akce-zaloha.json"
DOMA = ROOT / "data" / "filmy_doma.json"
PRIDANE = ROOT / "data" / "filmy_doma_pridane.json"
DRUHY = ("film", "serial", "dokument")

sys.stdout.reconfigure(encoding="utf-8")


def nacti(cesta):
    return json.loads(Path(cesta).read_text(encoding="utf-8"))


def uloz(cesta, data):
    Path(cesta).parent.mkdir(parents=True, exist_ok=True)
    Path(cesta).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def appka_id(f):
    # stejné jako akceId() v appce pro typ filmy_doma
    return f"filmy_doma::{f.get('nazevOrig') or f.get('nazevCz') or ''}|{f.get('rezie') or ''}"


def klic(f):
    return f"{f['nazevOrig']}|{f.get('rok')}"


def druh_filmu(f):
    zanr = (f or {}).get("zanr") or ""
    if re.match(r"^seri[aá]l", zanr, re.I):
        return "serial"
    if re.search("documentary", zanr, re.I):
        return "dokument"
    return "film"


def vsechny_filmy():
    doma = nacti(DOMA)["filmy"]
    pridane = nacti(PRIDANE)["filmy"] if PRIDANE.exists() else []
    znama = {appka_id(f) for f in doma}
    return doma + [f for f in pridane if appka_id(f) not in znama]


# ---------- zebricek ----------

def bobova_cisla():
    z = nacti(ZALOHA)
    mapa = {appka_id(f): f for f in vsechny_filmy()}
    zeb, kotvy, rucne = z.get("zebricek", []), z.get("zebricekSkore", {}), z.get("zebricekDruh", {})

    def druh(i):
        return rucne.get(i) or druh_filmu(mapa.get(i))

    vystup = []
    for d in DRUHY:
        seznam = [i for i in zeb if druh(i) == d]
        kot = [(k, kotvy[i]) for k, i in enumerate(seznam) if i in kotvy]
        for k, i in enumerate(seznam):
            if not kot:
                s = None
            elif i in kotvy:
                s = kotvy[i]
            else:
                nad = next((x for x in reversed(kot) if x[0] < k), None)
                pod = next((x for x in kot if x[0] > k), None)
                s = nad[1] + (pod[1] - nad[1]) * (k - nad[0]) / (pod[0] - nad[0]) if nad and pod else (nad or pod)[1]
                s = round(s)
            f = mapa.get(i) or {}
            h = f.get("hodnoceni") or {}
            vystup.append({
                "nazev": f.get("nazevOrig") or i.split("::", 1)[-1].split("|")[0],
                "nazevCz": f.get("nazevCz"), "rok": f.get("rok"), "rezie": f.get("rezie"),
                "zanr": f.get("zanr"), "druh": d, "poradi": k + 1, "bob": s, "kotva": i in kotvy,
                "ai": f.get("estetickeSkore"), "f101": h.get("films101"), "imdb": h.get("imdb"),
                "vDatech": bool(f),
            })
    return z.get("exportovanoAt"), vystup


def cmd_zebricek(vystup):
    kdy, radky = bobova_cisla()
    uloz(vystup, radky)
    for d in DRUHY:
        r = [x for x in radky if x["druh"] == d]
        print(f"{d:9} {len(r):3} filmů, kotev {sum(x['kotva'] for x in r)}")
    print(f"záloha z {kdy}; bez skóre (druh bez kotev): {sum(x['bob'] is None for x in radky)}")


# ---------- test naslepo ----------

def cmd_test_priprav(zebricek, adresar):
    adr = Path(adresar)
    adr.mkdir(parents=True, exist_ok=True)
    radky = [r for r in nacti(zebricek) if r["bob"] is not None and r["vDatech"]]
    serazene = sorted(radky, key=lambda r: -r["bob"])
    test = [r for k, r in enumerate(serazene) if k % 3 == 1]
    jmena = {r["nazev"] for r in test}
    verejne = ("nazev", "nazevCz", "rok", "rezie", "zanr", "druh")
    uloz(adr / "znamy.json", [{k: r[k] for k in verejne + ("bob", "kotva")} for r in radky if r["nazev"] not in jmena])
    skryte = [{k: r[k] for k in verejne + ("f101", "imdb")} for r in test]
    random.Random(7).shuffle(skryte)
    uloz(adr / "odhadni.json", skryte)
    uloz(adr / "pravda.json", test)
    print(f"známých {len(radky) - len(test)}, testovacích {len(test)} → {adr}")


def _rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def _pearson(a, b):
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else 0.0


def cmd_test_vyhodnot(adresar, predikce):
    adr = Path(adresar)
    pravda = {r["nazev"]: r for r in nacti(adr / "pravda.json")}
    znamy = nacti(adr / "znamy.json")
    prumer = st.mean(r["bob"] for r in znamy)
    rad = [(p, pravda[p["nazev"]]) for p in nacti(predikce) if p["nazev"] in pravda]
    bob = [t["bob"] for _, t in rad]
    odh = [p["odhad"] for p, _ in rad]
    print(f"n={len(rad)}")
    print(f"odhad:        chyba {st.mean(abs(a - b) for a, b in zip(odh, bob)):5.1f}  "
          f"spearman {_pearson(_rank(odh), _rank(bob)):+.2f}  posun {st.mean(a - b for a, b in zip(odh, bob)):+.1f}  "
          f"v ±10: {sum(abs(a - b) <= 10 for a, b in zip(odh, bob))}/{len(rad)}")
    ai = [(t["ai"], t["bob"]) for _, t in rad if t["ai"] is not None]
    if ai:
        a, b = zip(*ai)
        print(f"staré AI:     chyba {st.mean(abs(x - y) for x, y in ai):5.1f}  "
              f"spearman {_pearson(_rank(a), _rank(b)):+.2f}  posun {st.mean(x - y for x, y in ai):+.1f}")
    print(f"všem {prumer:.0f}:      chyba {st.mean(abs(prumer - b) for b in bob):5.1f}")
    print("\nnejvětší chyby:")
    for p, t in sorted(rad, key=lambda x: -abs(x[0]["odhad"] - x[1]["bob"]))[:12]:
        print(f"  {p['odhad'] - t['bob']:+4}  Bob {t['bob']:>3}  odhad {p['odhad']:>3}  {t['nazev']} ({t['rok']}) — {p.get('duvod', '')}")


# ---------- dávky a slití ----------

def cmd_davky(adresar, velikost=300):
    adr = Path(adresar)
    adr.mkdir(parents=True, exist_ok=True)
    filmy = vsechny_filmy()
    kompakt = []
    for f in filmy:
        h = f.get("hodnoceni") or {}
        kompakt.append({"klic": klic(f), "nazev": f["nazevOrig"], "rok": f.get("rok"),
                        "rezie": f.get("rezie"), "zanr": f.get("zanr"),
                        "f101": h.get("films101"), "imdb": h.get("imdb")})
    velikost = int(velikost)
    n = 0
    for n, start in enumerate(range(0, len(kompakt), velikost), 1):
        uloz(adr / f"davka_{n:02}.json", kompakt[start:start + velikost])
    print(f"{len(kompakt)} filmů → {n} dávek po {velikost} v {adr}")


def _zapis_skore(cesta, skore):
    original = cesta.read_text(encoding="utf-8")
    crlf = "\r\n" in original
    d = json.loads(original)
    zmeneno = 0
    for f in d["filmy"]:
        k = klic(f)
        if k in skore:
            f["estetickeSkore"] = skore[k]
            zmeneno += 1
    puvodni = json.loads(original)
    for x in (puvodni, d):
        for f in x["filmy"]:
            f.pop("estetickeSkore", None)
    assert puvodni == json.loads(json.dumps(d)), f"{cesta.name}: změnilo se něco kromě estetickeSkore — nezapisuju."
    d = json.loads(original)
    for f in d["filmy"]:
        if klic(f) in skore:
            f["estetickeSkore"] = skore[klic(f)]
    text = json.dumps(d, ensure_ascii=False, indent=2)
    if crlf:
        text = text.replace("\n", "\r\n")
    cesta.write_text(text, encoding="utf-8", newline="")
    return zmeneno


def cmd_slij(adresar):
    adr = Path(adresar)
    skore = {}
    for soubor in sorted(adr.glob("vysledek_*.json")):
        for k, v in nacti(soubor).items():
            if not (isinstance(v, int) and 0 <= v <= 100):
                sys.exit(f"Neplatné skóre {v!r} u {k} ({soubor.name})")
            skore[k] = v
    ocekavane = {klic(f) for f in vsechny_filmy()}
    chybi = ocekavane - set(skore)
    navic = set(skore) - ocekavane
    if navic:
        sys.exit("Ve výsledcích jsou neznámé klíče:\n  " + "\n  ".join(sorted(navic)[:20]))
    if chybi:
        sys.exit(f"Chybí skóre u {len(chybi)} filmů, např.:\n  " + "\n  ".join(sorted(chybi)[:20]))
    a = _zapis_skore(DOMA, skore)
    b = _zapis_skore(PRIDANE, skore) if PRIDANE.exists() else 0
    hodnoty = list(skore.values())
    print(f"Zapsáno: filmotéka {a}, čekárna {b}. Průměr {st.mean(hodnoty):.1f}, "
          f"medián {st.median(hodnoty)}, ≥80: {sum(v >= 80 for v in hodnoty)}, <50: {sum(v < 50 for v in hodnoty)}")


if __name__ == "__main__":
    prikazy = {"zebricek": cmd_zebricek, "test-priprav": cmd_test_priprav, "test-vyhodnot": cmd_test_vyhodnot,
               "davky": cmd_davky, "slij": cmd_slij}
    if len(sys.argv) < 2 or sys.argv[1] not in prikazy:
        sys.exit(__doc__)
    prikazy[sys.argv[1]](*sys.argv[2:])
