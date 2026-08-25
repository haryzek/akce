"""
Sdílené jádro pro Lávku (centrum-lavka.cz) — Psychoterapeutické centrum Lávka.

Lávka je jeden web, ale krmí DVA typy akcí: odborne_psychoterapie (semináře
zajímavé i pro terapeuty) a verejnost_psychoterapie (sebezkušenostní kurzy
a skupiny pro veřejnost — mindfulness, jungovské víkendy, focusing…).
Rozdělení NEdělá scraper — obě tenké obálky (lavka_psychoterapie.py,
lavka_verejnost.py) dostávají STEJNÝ kompletní seznam a vyzobání řeší až
Cowork prompty (přísně vylučovací, hraniční akce patří veřejnosti).
Proto tu je cache per okno — web se leze jen jednou, ne dvakrát.

Mechanika (čtvrtá v repu — "univerzální lovec stop"):
WordPress/Gutenberg, server-side HTML, ale ŽÁDNÝ kalendářní plugin — akce
jsou ručně nasekané odstavce po různu na podstránkách. Proto se nescrapuje
konkrétní výpis, ale: (1) z homepage se vyparsuje hlavní menu (ul.menu) a
vezmou se VŠECHNY interní odkazy — žádný hardcode podstránek, přeskládané
menu scraper přežije; (2) každá stránka se proleze a hledá se kotva
"Termín:" / "Termíny:" — jediný konzistentní vzor webu. Kolem kotvy bývá
"Lektor:", "Místo:", "Cena:"/"Kurzovné:". Stránka bez kotvy (kontakt,
články…) prostě nic nedá.

Pasti zdroje:
- datumy jsou SLOVNÍ česky ("26. – 27. září 2026", "30. říjen – 1. listopad
  2026", i rozbité "20 .- 22. březen 2026") → najdi_datumy_slovni
  z psychoterapie_common; rok se u rozsahů píše až na konci (dědí se zprava),
- hodnota kotvy je někdy v témže <p>, jindy v <li> seznamu POD ní → sbírá se
  okno elementů od kotvy k dalšímu nadpisu/kotvě,
- na stránkách visí i mrtvoly z minulých let (vyfiltruje okno) a "Termín:
  bude upřesněno" (bez datumu → zahodit),
- "obsazeno" se přilepuje do popisu (Bob se může hlásit jako náhradník),
- SCHVÁLNĚ se tu NEpoužívá je_vycvik ani je_dlouhodoba: "Základní výcvik
  mindfulness" je 8týdenní kurz, který Bob výslovně chce — o výcvicích
  v pravém slova smyslu rozhodují Cowork prompty.
"""

import copy
import re
import time
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

try:
    from ..common import polozka
    from .psychoterapie_common import (
        v_okne, najdi_cas, najdi_datumy, najdi_datumy_slovni, odhadni_zanr,
        parsuj_den, _bez_diakritiky,
    )
except ImportError:  # když se modul spustí samostatně
    from common import polozka
    from scrapers.psychoterapie_common import (
        v_okne, najdi_cas, najdi_datumy, najdi_datumy_slovni, odhadni_zanr,
        parsuj_den, _bez_diakritiky,
    )

ZDROJ = "centrum-lavka.cz"
BASE = "https://centrum-lavka.cz/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/126 Safari/537.36"}
PAUZA = 0.4  # slušnost mezi stránkami

_CACHE = {}  # (od, do) -> list položek; dvě obálky = jeden crawl

# kotva termínu ("Termín:", "Termíny:", i "Termín :" s mezerou)
_KOTVA = re.compile(r"\btermin(y)?\s*:", re.I)
_OBSAZENO = re.compile(r"obsazen", re.I)

# labely, na kterých končí hodnota předchozího labelu (v jednom slitém odstavci)
_DALSI_LABEL = (r"(?:(?:Lektor(?:ka|ky|i)?|Místo|Cena|Kurzovné|Termín(?:y)?|Čas"
                r"|Max\.?\s*počet[^:]{0,20}|Počet\s*účastníků|Ubytování|Strava)\s*:"
                r"|Skupina je)")


def _vysek(text, label):
    """Hodnota za "Label:" až po další label nebo konec, ořezaná. None když chybí."""
    m = re.search(rf"{label}\s*:\s*(.+?)(?=\s*{_DALSI_LABEL}|$)", text, re.I)
    if not m:
        return None
    hodnota = m.group(1).strip(" |•-–")
    return hodnota[:120] or None


def _odkazy_z_menu(soup):
    """Interní odkazy z hlavního menu — unikátní, bez homepage a externích webů."""
    odkazy = []
    videne = set()
    for a in soup.select("ul.menu a[href]"):
        url = urljoin(BASE, a["href"]).split("#")[0]
        casti = urlsplit(url)
        if casti.netloc != urlsplit(BASE).netloc:
            continue  # mindfulness-institut.cz apod. — cizí web
        if casti.path in ("", "/"):
            continue  # homepage samotná akce nenese
        if not url.endswith("/"):
            url += "/"
        if url not in videne:
            videne.add(url)
            odkazy.append(url)
    return odkazy


def _intervaly_z_bloku(blok, od, do):
    """
    Text bloku → (datumOd, datumDo, terminy) v RAW formátu DD-MM-YYYY.

    Slovní intervaly + číselné datumy ("14.1.2026"). Měsíční rozsahy
    ("září-říjen 2026") jen roztahují krajní meze — konkrétní den ("1. setkání
    8. září") je přesnější začátek, tak má přednost. Víc oddělených běhů
    (dva víkendy téhož kurzu) → pole terminy se začátky běhů.

    Filtr oknem od–do běží už tady per interval: na stránkách visí i termíny
    z minulých let a bez filtru by prosákly do pole terminy (akce jako celek
    by oknem prošla přes jediný živý termín).
    """
    denni = []    # intervaly s konkrétním dnem
    mesicni = []  # rozsahy jen z měsíců
    for zacatek, konec in najdi_datumy_slovni(blok):
        if not v_okne(zacatek, konec, od, do):
            continue
        if zacatek.startswith("01-") and konec[:2] in ("28", "29", "30", "31") \
                and zacatek[3:5] != konec[3:5]:
            mesicni.append((zacatek, konec))
        else:
            denni.append((zacatek, konec))
    for d in najdi_datumy(blok):  # číselná data ("14.1.2026") = jednodenní
        if v_okne(d, d, od, do):
            denni.append((d, d))
    denni = sorted(set(denni), key=lambda iv: parsuj_den(iv[0]))

    if not denni and not mesicni:
        return None, None, None

    vsechny = denni + mesicni
    datum_od = min((iv[0] for iv in denni), default=None, key=parsuj_den) \
        or min(iv[0] for iv in mesicni)
    datum_do = max((iv[1] for iv in vsechny), key=parsuj_den)
    terminy = [iv[0] for iv in denni] if len(denni) >= 2 else None
    return datum_od, datum_do, terminy


def _popis_stranky(content):
    """Úvodní anotace stránky: první delší odstavce entry-content, ~800 znaků."""
    kusy = []
    for p in content.find_all("p"):
        t = p.get_text(" ", strip=True)
        if _KOTVA.search(_bez_diakritiky(t)):
            break  # od první kotvy dál už jsou termínové bloky, ne anotace
        if len(t) >= 60:
            kusy.append(t)
        if sum(len(k) for k in kusy) > 800:
            break
    return " ".join(kusy)[:900] or None


def _og(soup, prop):
    meta = soup.find("meta", property=f"og:{prop}")
    return meta.get("content") if meta and meta.get("content") else None


def _bloky_stranky(content):
    """
    Projde elementy entry-content po pořadí a vrací (nadpis, text_bloku) pro
    každou kotvu "Termín:". Blok = element s kotvou + následující elementy
    (typicky <li> s datumy) až po další nadpis/kotvu, plus text nadpisu
    (nese často datum i čas, viz mindfulness skupiny).
    """
    elementy = content.find_all(["h1", "h2", "h3", "h4", "p", "li"])
    bloky = []
    nadpis = None
    i = 0
    while i < len(elementy):
        el = elementy[i]
        text = el.get_text(" ", strip=True)
        if el.name in ("h1", "h2", "h3", "h4"):
            nadpis = text or nadpis
            i += 1
            continue
        if _KOTVA.search(_bez_diakritiky(text)):
            kusy = [text]
            j = i + 1
            while j < len(elementy) and j - i < 8:
                dalsi = elementy[j]
                dalsi_text = dalsi.get_text(" ", strip=True)
                if dalsi.name in ("h1", "h2", "h3", "h4") \
                        or _KOTVA.search(_bez_diakritiky(dalsi_text)):
                    break
                kusy.append(dalsi_text)
                j += 1
            bloky.append((nadpis, ((nadpis or "") + " | " + " ".join(kusy)).strip(" |")))
            i = j
            continue
        i += 1
    return bloky


def _sluc_varianty(polozky):
    """
    Intra-zdroj dedup (jako grupování přes event.id u goout): varianty téže akce
    na jedné stránce — Lávka vypisuje paralelní běhy kurzu jako samostatné bloky
    s nadpisy "Mindfulness skupina | září-říjen 2026 | ÚTERÝ 10:00-12:00" vs
    "| STŘEDA 19:00-21:00". Generický dedup by je stejně slil (stejné místo,
    podobný název), ale zahodil by termín i čas druhé varianty. Tady se slévají
    řízeně: klíč = stránka + část nadpisu před prvním "|", varianty → terminy.
    """
    skupiny, poradi = {}, []
    for p in polozky:
        klic = (p["url"], (p["nazevCz"] or "").split("|")[0].strip().lower())
        if klic not in skupiny:
            skupiny[klic] = []
            poradi.append(klic)
        skupiny[klic].append(p)

    vysledek = []
    for klic in poradi:
        grupa = skupiny[klic]
        if len(grupa) == 1:
            vysledek.append(grupa[0])
            continue
        zaklad = grupa[0]
        zaklad["nazevCz"] = (zaklad["nazevCz"] or "").split("|")[0].strip()
        terminy = []
        for p in grupa:
            for t in (p.get("terminy") or [{"datum": p["datumOd"], "cas": p["cas"]}]):
                if t not in terminy:
                    terminy.append(t)
        terminy.sort(key=lambda t: (parsuj_den(t["datum"]), t["cas"] or ""))
        zaklad["terminy"] = terminy
        zaklad["datumOd"] = min((p["datumOd"] for p in grupa), key=parsuj_den)
        zaklad["datumDo"] = max((p["datumDo"] for p in grupa), key=parsuj_den)
        zaklad["cas"] = terminy[0]["cas"]
        # lektoři paralelních běhů se můžou lišit (úterý Honzík, čtvrtek Keprt)
        lektori = [p["autor"] for p in grupa if p["autor"]]
        zaklad["autor"] = ", ".join(dict.fromkeys(lektori)) or None
        vysledek.append(zaklad)
    return vysledek


def scrape_lavka(od, do):
    """Jeden crawl webu pro okno od–do (DD-MM-YYYY). Výsledek se cachuje per okno."""
    if (od, do) in _CACHE:
        return copy.deepcopy(_CACHE[(od, do)])

    r = requests.get(BASE, headers=HEADERS, timeout=25)
    r.raise_for_status()
    stranky = _odkazy_z_menu(BeautifulSoup(r.text, "html.parser"))
    print(f"  [{ZDROJ}] menu: {len(stranky)} interních stránek k prolezení")

    polozky = []
    videne = set()  # (nazev, datumOd) — pojistka proti duplicitě napříč stránkami
    for url in stranky:
        time.sleep(PAUZA)
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  [{ZDROJ}] ! {url}: {e}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        content = soup.find("div", class_="entry-content")
        if not content:
            continue

        titulek = _og(soup, "title") or (soup.title.get_text(strip=True) if soup.title else None)
        thumbnail = _og(soup, "image")
        popis_stranky = _popis_stranky(content)

        for nadpis, blok in _bloky_stranky(content):
            datum_od, datum_do, terminy = _intervaly_z_bloku(blok, od, do)
            if not datum_od:  # "Termín: bude upřesněno" nebo nic v okně
                continue
            nazev = nadpis or titulek
            if not nazev or (nazev, datum_od) in videne:
                continue
            videne.add((nazev, datum_od))

            popis = popis_stranky
            if _OBSAZENO.search(blok):
                pozn = "Termín je aktuálně obsazený, hlásit se lze jako náhradník."
                popis = f"{popis} ({pozn})" if popis else pozn

            polozky.append(polozka(
                ZDROJ,
                nazevCz=nazev,
                autor=_vysek(blok, r"Lektor(?:ka|ky|i)?"),
                zanr=odhadni_zanr(nazev) or odhadni_zanr(blok),
                datumOd=datum_od,
                datumDo=datum_do,
                cas=najdi_cas(blok),
                misto=_vysek(blok, "Místo"),
                url=url,
                cena=_vysek(blok, "(?:Cena|Kurzovné)"),
                thumbnail=thumbnail,
                popis=popis,
            ))
            if terminy:
                polozky[-1]["terminy"] = [{"datum": t, "cas": najdi_cas(blok)} for t in terminy]

    polozky = _sluc_varianty(polozky)
    print(f"  [{ZDROJ}] akcí s termínem v okně: {len(polozky)}")
    _CACHE[(od, do)] = polozky
    return copy.deepcopy(polozky)
