# Výběr a seřazení psychoterapeutických akcí pro veřejnost pro Boba

Ahoj! Tvým úkolem je z hrubého seznamu akcí vytvořit spolehlivý, seřazený JSON,
který poslouží jako zdroj dat pro Bobovu aplikaci. Nejdůležitější je správnost a čistota dat.
Nic si nevymýšlej – pracuj **pouze** s tím, co je ve vstupním souboru. Žádná externí
dohledávání, žádný starší JSON.

## Vstupy (přečti si je sám ze složky projektu)
- **RAW data:** `scraper/output/verejnost_psychoterapie.json` – syrový, deduplikovaný
  seznam akcí ze scraperu.
- **Bobův estetický profil:** `support/esteticky-profil.md` – doplňkový vstup; hlavní
  profil pro tenhle typ akce je popsaný níže v Kroku 1.

> **DŮLEŽITÉ k RAW souboru:** je to **vždy kompletní, validní JSON**. Když se ti nevejde
> do jednoho čtení, **načti ho po částech** (offset/limit) a slož si celý obsah — **nikdy
> nepředpokládej, že je useknutý**, a kvůli domnělému useknutí nezahazuj žádnou položku.

## KROK 1 – UDĚLEJ SI MAPU BOBA (osobní profil)
Tenhle typ akce jsou **sebezkušenostní a rozvojové akce z psychoterapeutického světa,
na které se chodí jako ČLOVĚK, ne jako odborník**: mindfulness kurzy a skupiny,
jungovsky laděné víkendy, focusing, meditační kurzy, práce s tématem smrti, hledání
vize… Bob je sice psychoterapeut (psychodynamicky a psychoanalyticky orientovaný),
ale sem si vybírá věci pro vlastní prožitek a vnitřní práci.

Co ho táhne (vyšší skóre):
- **mindfulness a meditace** s poctivým vedením (zkušení lektoři s terapeutickým
  zázemím, ne víkendová ezoterika),
- **jungovská a hlubinná témata**: sny, stín, vnitřní dítě, anima/animus, archetypy,
- **existenciální hloubka**: smrt a konečnost, hledání vize, smysl — souzní s jeho
  zálibou v existenciální hloubce (viz estetický profil),
- **prožitkové metody s tělem a vnímáním**: focusing, všímavost k tělesnému prožívání,
- buddhistická psychologie a meditace v serióznějším podání.

Co ho táhne míň (nižší skóre, ale nechat v seznamu):
- čistě relaxační/wellness formáty bez hloubky (jóga smíchu, spa vibe),
- ezoterický okraj (šamanské rituály, čakry, věštění),
- akce cílené na velmi specifickou skupinu, do které nepatří (ženské kruhy,
  akce pro rodiče s dětmi, mládež).

## KROK 2 – VYHOĎ JEN VYLOŽENÝ BALAST
Odstraň položky, které do tohoto typu fakticky nepatří:
- **čistě odborné akce pro terapeuty a odborníky** (klinické semináře, kazuistiky,
  supervize, odborné konference — ty patří do typu `odborne_psychoterapie`
  a zpracovávají se zvlášť; **rozdělení je přísně vylučovací**: když je akce na hraně
  mezi odbornou a sebezkušenostní, **nech ji TADY** — druhý prompt ji vyhazuje),
- **individuální služby**, ne akce s termínem (individuální terapie/konzultace,
  objednávání, ceníky),
- položky, které nejsou skutečná akce (rozpisy lekcí, provozní oznámení, stránkový
  balast, který scraperu proklouzl),
- duplicitní zbytky (stejná akce dvakrát pod trochu jiným názvem — nech bohatší záznam).
Buď spíš zdrženlivý: **profil slouží k seřazení, ne k mazání.** Žádný horní limit
počtu akcí není.

## KROK 3 – SKÓRE (BOB-FIT) + DŮVOD DOPORUČENÍ
Každé zbývající akci přiřaď `estetickeSkore` na škále **0–100** (vyšší = větší šance,
že Boba obohatí a bude ho to bavit). Skóruj podle mapy z Kroku 1 — hlavně z názvu,
popisu a lektora.
Do `duvodSkore` napiš **jednu jedinou krátkou větu (do ~90 znaků)**, proč Bobovi akci
doporučuješ – osobně, konkrétně, žádné omáčky. (Zobrazuje se pod popisem na kartě.)

## KROK 4 – PŘEČISTI POPISY (neškrť je natvrdo) A NÁZVY
Popisy ze zdrojů jsou často slepenec pozvánky, organizačních pokynů a marketingu.
Učeš je na čtivý text o obsahu akce:
- **vyhoď**: storno podmínky, přihlašovací instrukce, opakování datumu/místa/ceny
  (na to má karta vlastní pole), reference účastníků, oslovení,
- **nech**: o čem akce je, pro koho je určená, kdo ji vede a čím je zajímavá,
- klidně nech 300–800 znaků, pokud text nese obsah; karta pojme ~860 znaků a delší text
  se sám ořízne „…". Když je zdrojový popis chudý, nech ho krátký – nic nedomýšlej.
- **názvy uprav na čistý název akce**: RAW názvy občas nesou provozní přílepky
  („… | ÚTERÝ 10:00-12:00") nebo jsou vzaté z mezinadpisu stránky („Témata
  jednotlivých lekcí…") — srovnej je na věcný název kurzu/akce, nic nevymýšlej.
U online akcí bez místa nastav `misto` na `"Online"` (pokud zdroj neuvádí platformu,
např. Zoom — tu pak nech).

## KROK 5 – DATUM A POLE
- Datumy převeď z `DD-MM-YYYY` (RAW) na **`DD.MM.YYYY`** (tečky).
- Pole `terminy` (pokud u položky je) přenes se stejnou konverzí datumů; má ho jen
  vícetermínová/víceběhová akce (paralelní skupiny, víc běhů kurzu).
- `autor` = lektor/lektoři; když chybí a je znám pořadatel, dej pořadatele.
- Ostatní pole (misto, adresa, url, cena, thumbnail, zanr, nazevOrig) přenes beze změny;
  prázdné nech jako null. `cena` můžeš zkrátit na podstatné („5800 Kč / 8 setkání").
  `zanr` můžeš zpřesnit (skupina/kurz/workshop/víkendový seminář…), když je ze
  scraperu nepřesný nebo chybí.

## KROK 6 – SEŘAĎ
Seřaď akce **sestupně podle `estetickeSkore`** (nejlepší nahoře).

## KROK 7 – VÝSTUP
Ulož výsledek jako **`data/verejnost_psychoterapie.json`**. Struktura MUSÍ být PŘESNĚ
tato – nepřidávej pole, neměň názvy, pořadí ani typy:

```json
{
  "typAkce": "verejnost_psychoterapie",
  "vygenerovanoAt": "YYYY-MM-DDTHH:MM:SS",
  "obdobiOd": "dd.mm.yyyy",
  "obdobiDo": "dd.mm.yyyy",
  "verejnost_psychoterapie": [
    {
      "nazevCz": "",
      "nazevOrig": null,
      "autor": null,
      "zanr": null,
      "datumOd": "dd.mm.yyyy",
      "datumDo": "dd.mm.yyyy",
      "cas": null,
      "misto": null,
      "adresa": null,
      "url": null,
      "cena": null,
      "thumbnail": null,
      "popis": null,
      "estetickeSkore": null,
      "duvodSkore": null,
      "terminy": [
        {"datum": "dd.mm.yyyy", "cas": null}
      ]
    }
  ]
}
```

Pole `terminy` uveď **jen** u akcí, které ho mají v RAW (jinak ho úplně vynech).
`obdobiOd`/`obdobiDo` vezmi z hlavičky RAW souboru (převeď na tečkový formát).
`vygenerovanoAt` = aktuální čas.

## KONTROLA PŘED ODEVZDÁNÍM
- vyhozen je jen vyložený balast (odborné akce pro terapeuty, individuální služby,
  ne-akce),
- hraniční akce mezi odbornou a sebezkušenostní jsou ponechané TADY (vylučovací
  pravidlo),
- každá akce má `estetickeSkore` (0–100) i `duvodSkore` (jedna krátká věta, do ~90 znaků),
- popisy jsou zbavené organizačních pokynů, názvy jsou čisté názvy akcí,
- všechny datumy jsou v tečkovém formátu `DD.MM.YYYY` (i uvnitř `terminy`),
- online akce mají `misto` = "Online" (nebo platformu, např. "Zoom"),
- nic není vymyšlené, data pocházejí jen ze vstupního RAW souboru,
- akce jsou seřazené sestupně podle skóre,
- JSON přesně odpovídá zadané struktuře a je uložen jako `data/verejnost_psychoterapie.json`.
