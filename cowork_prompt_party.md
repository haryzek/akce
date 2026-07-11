# Výběr a seřazení pražských party pro Boba

Ahoj! Tvým úkolem je z hrubého seznamu party (klubová/taneční scéna) vytvořit spolehlivý,
seřazený JSON, který poslouží jako zdroj dat pro Bobovu aplikaci. Nejdůležitější je správnost
a čistota dat. Nic si nevymýšlej – pracuj **pouze** s tím, co je ve vstupním souboru. Žádná
externí dohledávání, žádná hodnocení z internetu, žádný starší JSON.

Poznámka: jde o Bobovu appkovou kategorii **Party** — spadá sem klubová a taneční scéna, DJ
noci, elektronika, koncerty v klubech s tanečním přesahem. Zdroj (goout.net) je bohatý
agregátor, takže RAW nese slušné popisy, účinkující (DJ/kapely) i cenu.

## Vstupy (přečti si je sám ze složky projektu)
- **RAW data:** `scraper/output/party.json` – syrový, deduplikovaný seznam party ze scraperu.
- **Bobův estetický profil:** `support/esteticky-profil.md` – kompletní profil.

> **DŮLEŽITÉ k RAW souboru:** bývá dlouhý (klidně přes 2000 řádků) a je to **vždy kompletní,
> validní JSON**. Když se ti nevejde do jednoho čtení, **načti ho po částech** (offset/limit)
> a slož si celý obsah — **nikdy nepředpokládej, že je useknutý**, a kvůli domnělému useknutí
> nezahazuj žádnou položku. Pokud narazíš na skutečnou syntaktickou chybu, nahlas ji, ale
> napřed ověř, že nejde jen o limit tvého čtení.

## KROK 1 – UDĚLEJ SI MAPU BOBA (pro klubovou/taneční scénu)
Přečti si CELÝ estetický profil, ne jen sekci o hudbě. Sestav si vlastní vnitřní mapu toho,
co Boba na klubové a taneční noci táhne. Vodítka (neomezuj se na ně):
- atmosféra, groove, kvalitní kurátorský dramaturgický výběr nad komerční mainstream masovkou,
- afinita k poctivé elektronice, d/b, house, techno s vkusem, world/organic a žánrovým přesahům,
- emocionální a estetická integrita, autorská a klubová identita nad prvoplánovou „mejdan" show,
- přesahy do jeho témat: noční nálada, ponor, tělo a rytmus, opravdovost nad pózou.
Bob NEMÁ rád: tuctové komerční mega-akce pro masu, prvoplánové „hit" mejdany bez kurátorské
a hudební kvality, turistickou klubovou show.

## KROK 2 – VYHOĎ JEN VYLOŽENÝ BALAST
Odstraň položky, které fakticky **nejsou plnohodnotná umělecká/kurátorská klubová noc**, například:
- ryze komerční turistické mega-párty a „drink & dance" pro projíždějící návštěvníky,
- reklamní a firemní eventy, soukromé akce, atrakce bez hudební a kurátorské kvality.
Buď spíš zdrženlivý: když je něco na hraně (menší klub, žánrový přesah, méně známý DJ/label),
NECHEJ to v seznamu – od toho je skóre. **Profil slouží k seřazení, ne k mazání.** Žádný horní
limit počtu party není – nech všechno, co uměleckou/kurátorskou klubovou nocí opravdu je.

## KROK 3 – ESTETICKÉ SKÓRE (BOB-FIT) + DŮVOD DOPORUČENÍ
Každé zbývající party přiřaď `estetickeSkore` na škále **0–100** (vyšší = větší šance, že se
Bobovi bude líbit). Skóruj podle své mapy z Kroku 1, hlavně z názvu, účinkujících (DJ/label),
žánru a popisu.
Do `duvodSkore` napiš **jednu jedinou krátkou větu (do ~90 znaků)**, proč Bobovi tuhle party
doporučuješ – osobně, konkrétně, žádné omáčky. (Zobrazuje se pod popisem na kartě.)

## KROK 4 – PŘEČISTI POPISY (neškrť je natvrdo)
Popis ze zdroje je to nejcennější, proto ho **nech bohatý** – jen ho učeš:
- odstraň marketingové fráze, opakování, zbytečná zalomení a balast,
- **RAW popis je v Markdownu** (hvězdičky pro tučné/kurzívu, odkazy) – převeď na čistý plain
  text: zahoď `*`, `**`, `[text](url)` nahraď jen textem. Karta Markdown nerenderuje.
- oprav zjevné překlepy a rozházené znaky, sjednoť do plynulého textu,
- **neškrť pod smysl** – klidně nech 400–800 znaků, pokud text nese obsah.
Karta v aplikaci pojme zhruba **860 znaků**; delší text se sám elegantně ořízne „…". Necpi
ale výplň jen kvůli délce – když je zdrojový popis krátký, nech ho krátký. Když popis ve
vstupu chybí (null), nech null – nic nedomýšlej.

## KROK 5 – DATUM, ČAS, CENA, ÚČINKUJÍCÍ
- **Datum** převeď z `DD-MM-YYYY` (RAW) na **`DD.MM.YYYY`** (tečky). Jednorázová párty má
  `datumOd` == `datumDo`; u vícedenní/reprízované série nech skutečné rozmezí (od prvního
  do posledního termínu).
- **Čas (`cas`)** už z RAW přichází vyplněný (scraper ho tahá přímo ze zdroje) – ten
  **respektuj a přenes beze změny**. Jen když je v RAW `null` a v popisu je čas uveden
  explicitně, smíš ho doplnit ve formátu `HH:MM`. Nikdy ho nepřepisuj.
- **Cena (`cena`)** z RAW většinou přichází vyplněná (goout ji dodává). Přenes ji beze změny.
  Když je null a v popisu je explicitně, vytáhni krátký řetězec („od 250 Kč", „zdarma").
  Když nikde není, nech null – **nic nevymýšlej**.
- **Účinkující / DJ / label (`autor`)** – z RAW přichází vyplněný. Přenes beze změny;
  zobrazí se pod názvem místo žánru. Když je null, nech null.
- **Termíny (`terminy`)** – vícetermínové/reprízované party mají v RAW pole `terminy` = list
  `{datum, cas}`. Pokud tam je, **přenes ho** a u každého termínu převeď `datum` na tečkový
  formát `DD.MM.YYYY` (čas nech, jak je). Když v RAW `terminy` není, do výstupu pole
  **nedávej** (jednorázová párty ho nepotřebuje — appka si vystačí s datumOd/cas).

Ostatní pole (misto, adresa, url, thumbnail, nazevOrig, zanr) přenes beze změny;
prázdné nech jako null. `zanr` z goout bývá strojový slug („drum and bass", „techno") –
smíš ho učesat na čitelný tvar, nebo nech jak je.

## KROK 6 – SEŘAĎ
Seřaď party **sestupně podle `estetickeSkore`** (nejlepší nahoře).

## KROK 7 – VÝSTUP
Ulož výsledek jako **`data/party.json`**. Tenhle soubor je **generovaný výstup** — když už
existuje (z dřívějšího běhu nebo předchozí session), **CELÝ ho přepiš** čistou novou verzí.
Nenavazuj na starou verzi, negeneruj přírůstkově, neřeš její obsah — prostě ji nahraď.

Struktura MUSÍ být PŘESNĚ tato (pole `terminy` je jediné volitelné — dej ho jen
k vícetermínovým party, viz KROK 5). Jinak nepřidávej pole, neměň názvy, pořadí ani typy:

```json
{
  "typAkce": "party",
  "vygenerovanoAt": "YYYY-MM-DDTHH:MM:SS",
  "obdobiOd": "dd.mm.yyyy",
  "obdobiDo": "dd.mm.yyyy",
  "party": [
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
      "duvodSkore": null
    }
  ]
}
```

Pole `terminy` (jen u vícetermínových party) má tento tvar a vkládá se za `duvodSkore`:

```json
      "terminy": [
        {"datum": "14.07.2026", "cas": "22:00"},
        {"datum": "21.07.2026", "cas": "22:00"}
      ]
```

`obdobiOd`/`obdobiDo` vezmi z hlavičky RAW souboru (převeď na tečkový formát).
`vygenerovanoAt` = aktuální čas.

## KONTROLA PŘED ODEVZDÁNÍM
- vyhozen je jen vyložený balast (komerční mega-párty, firemní/soukromé eventy), kurátorské klubové noci zůstaly,
- žádný horní limit se neuplatnil,
- každá párty má `estetickeSkore` (0–100) i `duvodSkore` (jedna krátká věta, do ~90 znaků),
- popisy jsou přečištěné od Markdownu i balastu, ale ne uměle zkrácené (klidně 400–800 znaků),
- všechny datumy jsou v tečkovém formátu `DD.MM.YYYY`,
- `cas`, `cena` a `autor` z RAW jsou zachované beze změny (doplněné z popisu jen když v RAW chyběly),
- `terminy` je přenesené jen u vícetermínových party (datumy převedené na tečky), jinak vynechané,
- nic není vymyšlené, data pocházejí jen ze vstupního RAW souboru,
- party jsou seřazené sestupně podle skóre,
- JSON přesně odpovídá zadané struktuře a je uložen jako `data/party.json`.
