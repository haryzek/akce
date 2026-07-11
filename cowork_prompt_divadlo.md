# Výběr a seřazení pražského divadla pro Boba

Ahoj! Tvým úkolem je z hrubého seznamu divadelních představení vytvořit spolehlivý, seřazený
JSON, který poslouží jako zdroj dat pro Bobovu aplikaci. Nejdůležitější je správnost a čistota
dat. Nic si nevymýšlej – pracuj **pouze** s tím, co je ve vstupním souboru. Žádná externí
dohledávání, žádná hodnocení z internetu, žádný starší JSON.

Poznámka: jde o Bobovu appkovou kategorii **Divadlo** — spadá sem činohra, autorské a alternativní
divadlo, tanec/pohyb, loutky, černé divadlo, stand-up. Zdroj (goout.net) je bohatý agregátor,
takže RAW nese slušné popisy, účinkující i cenu. Dále používám vždy slovo „představení".

## Vstupy (přečti si je sám ze složky projektu)
- **RAW data:** `scraper/output/divadlo.json` – syrový, deduplikovaný seznam představení ze scraperu.
- **Bobův estetický profil:** `support/esteticky-profil.md` – kompletní profil.

> **DŮLEŽITÉ k RAW souboru:** bývá dlouhý (klidně přes 2000 řádků) a je to **vždy kompletní,
> validní JSON**. Když se ti nevejde do jednoho čtení, **načti ho po částech** (offset/limit)
> a slož si celý obsah — **nikdy nepředpokládej, že je useknutý**, a kvůli domnělému useknutí
> nezahazuj žádnou položku. Pokud narazíš na skutečnou syntaktickou chybu, nahlas ji, ale
> napřed ověř, že nejde jen o limit tvého čtení.

## KROK 1 – UDĚLEJ SI MAPU BOBA (pro divadlo)
Přečti si CELÝ estetický profil, ne jen sekci o divadle/performing arts. Sestav si vlastní
vnitřní mapu toho, co Boba na živém divadle táhne. Vodítka (neomezuj se na ně):
- existenciální hloubka, introspekce, melancholie, atmosféra, poctivá autorská výpověď,
- afinita k alternativě, autorskému a pohybovému/tanečnímu divadlu, silné vizuální řeči,
- emocionální pravdivost a estetická integrita nad efektem, komercí a zábavou pro zábavu,
- přesahy do jeho témat: vědomí, povaha reality, čas, ticho, spiritualita bez dogmatu.
Bob NEMÁ rád: turistickou show, komerční „crowd-pleaser" produkce, prvoplánovou zábavu bez
umělecké a emocionální kvality.

## KROK 2 – VYHOĎ JEN VYLOŽENÝ BALAST
Odstraň položky, které fakticky **nejsou plnohodnotné umělecké představení**, například:
- ryze turistické show cílené na projíždějící návštěvníky (marketingový popis, „must see"),
- reklamní a firemní eventy, prohlídky s divadelní kulisou, atrakce pro děti bez umělecké ambice.
Buď spíš zdrženlivý: když je něco na hraně (stand-up, komornější scéna, žánrový přesah, méně
známý soubor), NECHEJ to v seznamu – od toho je skóre. **Profil slouží k seřazení, ne k mazání.**
Žádný horní limit počtu představení není – nech všechno, co uměleckým divadlem opravdu je.

## KROK 3 – ESTETICKÉ SKÓRE (BOB-FIT) + DŮVOD DOPORUČENÍ
Každému zbývajícímu představení přiřaď `estetickeSkore` na škále **0–100** (vyšší = větší šance,
že se Bobovi bude líbit). Skóruj podle své mapy z Kroku 1, hlavně z názvu, souboru/účinkujících,
žánru a popisu.
Do `duvodSkore` napiš **jednu jedinou krátkou větu (do ~90 znaků)**, proč Bobovi tohle
představení doporučuješ – osobně, konkrétně, žádné omáčky. (Zobrazuje se pod popisem na kartě.)

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
- **Datum** převeď z `DD-MM-YYYY` (RAW) na **`DD.MM.YYYY`** (tečky). Jednorázové představení má
  `datumOd` == `datumDo`; u vícedenní reprízované hry nech skutečné rozmezí (od prvního do posledního termínu).
- **Čas (`cas`)** už z RAW přichází vyplněný (scraper ho tahá přímo ze zdroje) – ten
  **respektuj a přenes beze změny**. Jen když je v RAW `null` a v popisu je čas uveden
  explicitně, smíš ho doplnit ve formátu `HH:MM`. Nikdy ho nepřepisuj.
- **Cena (`cena`)** z RAW většinou přichází vyplněná (goout ji dodává, např. „450–650 Kč“).
  Přenes ji beze změny. Když je null a v popisu je explicitně, vytáhni krátký řetězec
  („od 390 Kč", „zdarma"). Když nikde není, nech null – **nic nevymýšlej**.
- **Účinkující / soubor (`autor`)** – z RAW přichází vyplněný (soubor, herci, stand-uppeři).
  Přenes beze změny; zobrazí se pod názvem místo žánru. Když je null, nech null.
- **Termíny (`terminy`)** – reprízovaná představení mají v RAW pole `terminy` = list
  `{datum, cas}`. Pokud tam je, **přenes ho** a u každého termínu převeď `datum` na tečkový
  formát `DD.MM.YYYY` (čas nech, jak je). Když v RAW `terminy` není, do výstupu pole
  **nedávej** (jednorázové představení ho nepotřebuje — appka si vystačí s datumOd/cas).

Ostatní pole (misto, adresa, url, thumbnail, nazevOrig, zanr) přenes beze změny;
prázdné nech jako null. `zanr` z goout bývá strojový slug („play dance", „stand up comedy") –
smíš ho učesat na čitelný český tvar („taneční divadlo", „stand-up"), nebo nech jak je.

## KROK 6 – SEŘAĎ
Seřaď představení **sestupně podle `estetickeSkore`** (nejlepší nahoře).

## KROK 7 – VÝSTUP
Ulož výsledek jako **`data/divadlo.json`**. Tenhle soubor je **generovaný výstup** — když už
existuje (z dřívějšího běhu nebo předchozí session), **CELÝ ho přepiš** čistou novou verzí.
Nenavazuj na starou verzi, negeneruj přírůstkově, neřeš její obsah — prostě ji nahraď.

Struktura MUSÍ být PŘESNĚ tato (pole `terminy` je jediné volitelné — dej ho jen
k reprízovaným představením, viz KROK 5). Jinak nepřidávej pole, neměň názvy, pořadí ani typy:

```json
{
  "typAkce": "divadlo",
  "vygenerovanoAt": "YYYY-MM-DDTHH:MM:SS",
  "obdobiOd": "dd.mm.yyyy",
  "obdobiDo": "dd.mm.yyyy",
  "divadlo": [
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

Pole `terminy` (jen u reprízovaných představení) má tento tvar a vkládá se za `duvodSkore`:

```json
      "terminy": [
        {"datum": "14.07.2026", "cas": "20:00"},
        {"datum": "15.07.2026", "cas": "20:00"}
      ]
```

`obdobiOd`/`obdobiDo` vezmi z hlavičky RAW souboru (převeď na tečkový formát).
`vygenerovanoAt` = aktuální čas.

## KONTROLA PŘED ODEVZDÁNÍM
- vyhozen je jen vyložený balast (turistická show, firemní eventy, atrakce), umělecká představení zůstala,
- žádný horní limit se neuplatnil,
- každé představení má `estetickeSkore` (0–100) i `duvodSkore` (jedna krátká věta, do ~90 znaků),
- popisy jsou přečištěné od Markdownu i balastu, ale ne uměle zkrácené (klidně 400–800 znaků),
- všechny datumy jsou v tečkovém formátu `DD.MM.YYYY`,
- `cas`, `cena` a `autor` z RAW jsou zachované beze změny (doplněné z popisu jen když v RAW chyběly),
- `terminy` je přenesené jen u reprízovaných představení (datumy převedené na tečky), jinak vynechané,
- nic není vymyšlené, data pocházejí jen ze vstupního RAW souboru,
- představení jsou seřazená sestupně podle skóre,
- JSON přesně odpovídá zadané struktuře a je uložen jako `data/divadlo.json`.
