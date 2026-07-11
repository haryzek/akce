# Výběr a seřazení pražských koncertů Jazz & Blues (klubová scéna) pro Boba

Ahoj! Tvým úkolem je z hrubého seznamu koncertů vytvořit spolehlivý, seřazený JSON, který
poslouží jako zdroj dat pro Bobovu aplikaci. Nejdůležitější je správnost a čistota dat.
Nic si nevymýšlej – pracuj **pouze** s tím, co je ve vstupním souboru. Žádná externí
dohledávání, žádná hodnocení z internetu, žádný starší JSON.

Poznámka: jde o Bobovu appkovou kategorii **Jazz & Blues** — spadá sem jazz, soul, blues,
swing, funk, world a příbuzné živé kluby (NE rock/punk, ten si Bob třídí jinam, a NE vážná
hudba, ta má vlastní typ). Zdroj (prague.eu „klubová scéna") je převážně jazzově laděný,
ale zvládne i přesahy. Dále používám vždy slovo „koncert".

## Vstupy (přečti si je sám ze složky projektu)
- **RAW data:** `scraper/output/koncerty_jazzblues.json` – syrový, deduplikovaný seznam koncertů ze scraperu.
- **Bobův estetický profil:** `support/esteticky-profil.md` – kompletní profil.

> **DŮLEŽITÉ k RAW souboru:** bývá dlouhý (klidně přes 2000 řádků) a je to **vždy kompletní,
> validní JSON**. Když se ti nevejde do jednoho čtení, **načti ho po částech** (offset/limit)
> a slož si celý obsah — **nikdy nepředpokládej, že je useknutý**, a kvůli domnělému useknutí
> nezahazuj žádnou položku. Pokud narazíš na skutečnou syntaktickou chybu, nahlas ji, ale
> napřed ověř, že nejde jen o limit tvého čtení.

## KROK 1 – UDĚLEJ SI MAPU BOBA (pro živou hudbu)
Přečti si CELÝ estetický profil, ne jen sekci o hudbě. Sestav si vlastní vnitřní mapu
toho, co Boba na hudbě a živém provedení táhne. Vodítka (neomezuj se na ně):
- emocionální pravdivost, atmosféra, groove a intimita klubu nad efektem a exhibicí,
- afinita k jazzu, soulu, blues, swingu, funku a jejich poctivým, hráčsky vyzrálým provedením,
- kvalita interpretů a souborů, autorský program před turistickým „best of",
- přesahy do jeho témat: introspekce, noční nálada, opravdovost, prostor a ticho mezi tóny.
Bob NEMÁ rád: prázdnou show, tuctové coververze pro turisty, jarmareční efekt bez hudební
a emocionální kvality.

## KROK 2 – VYHOĎ JEN VYLOŽENÝ BALAST
Odstraň položky, které fakticky **nejsou plnohodnotný umělecký koncert**, například:
- ryze turistické „dinner & music" a „best of" večery cílené na projíždějící návštěvníky
  (opakující se komerční program každý večer, marketingový popis),
- reklamní a firemní eventy, prohlídky s hudební kulisou, edukativní atrakce pro děti.
Buď spíš zdrženlivý: když je něco na hraně (méně známý soubor, jam session, festivalový
večer, žánrový přesah), NECHEJ to v seznamu – od toho je skóre. **Profil slouží k seřazení,
ne k mazání.** Žádný horní limit počtu koncertů není – nech všechno, co uměleckým koncertem
opravdu je.

## KROK 3 – ESTETICKÉ SKÓRE (BOB-FIT) + DŮVOD DOPORUČENÍ
Každému zbývajícímu koncertu přiřaď `estetickeSkore` na škále **0–100** (vyšší = větší šance,
že se Bobovi bude líbit). Skóruj podle své mapy z Kroku 1, hlavně z názvu, interpreta,
programu a popisu.
Do `duvodSkore` napiš **jednu jedinou krátkou větu (do ~90 znaků)**, proč Bobovi tenhle
koncert doporučuješ – osobně, konkrétně, žádné omáčky. (Zobrazuje se pod popisem na kartě.)

## KROK 4 – PŘEČISTI POPISY (neškrť je natvrdo)
Popis ze zdroje je to nejcennější, proto ho **nech bohatý** – jen ho učeš:
- odstraň marketingové fráze, opakování, zbytečná zalomení a balast,
- oprav zjevné překlepy a rozházené znaky, sjednoť do plynulého textu,
- **neškrť pod smysl** – klidně nech 400–800 znaků, pokud text nese obsah.
Karta v aplikaci pojme zhruba **860 znaků**; delší text se sám elegantně ořízne „…". Necpi
ale výplň jen kvůli délce – když je zdrojový popis krátký, nech ho krátký. Když popis ve
vstupu chybí (null), nech null – nic nedomýšlej.

## KROK 5 – DATUM, ČAS, CENA, INTERPRET
- **Datum** převeď z `DD-MM-YYYY` (RAW) na **`DD.MM.YYYY`** (tečky). Koncert bývá jednorázový,
  takže `datumOd` == `datumDo`; u vícedenního festivalu nech skutečné rozmezí.
- **Čas (`cas`)** už z RAW většinou přichází vyplněný (scraper ho tahá přímo ze zdroje) –
  ten **respektuj a přenes beze změny**. Jen když je v RAW `null` a v popisu je čas uveden
  explicitně („začátek v 20:00"), smíš ho doplnit ve formátu `HH:MM`. Nikdy ho nepřepisuj.
- **Cena (`cena`)** je v RAW skoro vždy null – zdroj ji strojově nedodává. Pokud je
  **explicitně v popisu** („vstupné od 390 Kč", „vstup zdarma"), vytáhni ji jako krátký
  řetězec, jak dává smysl („od 390 Kč", „zdarma"). Když v popisu není, nech null – **nic nevymýšlej**.
- **Interpret / soubor (`autor`)** – když je z názvu nebo popisu zřejmý hlavní interpret,
  kapela nebo lídr, dej ho do `autor` (zobrazí se pod názvem místo žánru). Jinak null.
- **Termíny (`terminy`)** – vícetermínové koncerty mají v RAW pole `terminy` = list
  `{datum, cas}`. Pokud tam je, **přenes ho** a u každého termínu převeď `datum` na tečkový
  formát `DD.MM.YYYY` (čas nech, jak je). Když v RAW `terminy` není, do výstupu pole
  **nedávej** (jednorázový koncert ho nepotřebuje — appka si vystačí s datumOd/cas).

Ostatní pole (misto, adresa, url, thumbnail, nazevOrig, zanr) přenes beze změny;
prázdné nech jako null.

## KROK 6 – SEŘAĎ
Seřaď koncerty **sestupně podle `estetickeSkore`** (nejlepší nahoře).

## KROK 7 – VÝSTUP
Ulož výsledek jako **`data/koncerty_jazzblues.json`**. Tenhle soubor je **generovaný výstup** —
když už existuje (z dřívějšího běhu nebo předchozí session), **CELÝ ho přepiš** čistou novou
verzí. Nenavazuj na starou verzi, negeneruj přírůstkově, neřeš její obsah — prostě ji nahraď.

Struktura MUSÍ být PŘESNĚ tato (pole `terminy` je jediné volitelné — dej ho jen
k vícetermínovým koncertům, viz KROK 5). Jinak nepřidávej pole, neměň názvy, pořadí ani typy:

```json
{
  "typAkce": "koncerty_jazzblues",
  "vygenerovanoAt": "YYYY-MM-DDTHH:MM:SS",
  "obdobiOd": "dd.mm.yyyy",
  "obdobiDo": "dd.mm.yyyy",
  "koncerty": [
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

Pole `terminy` (jen u vícetermínových koncertů) má tento tvar a vkládá se za `duvodSkore`:

```json
      "terminy": [
        {"datum": "04.08.2026", "cas": "20:00"},
        {"datum": "13.08.2026", "cas": "20:00"}
      ]
```

`obdobiOd`/`obdobiDo` vezmi z hlavičky RAW souboru (převeď na tečkový formát).
`vygenerovanoAt` = aktuální čas.

## KONTROLA PŘED ODEVZDÁNÍM
- vyhozen je jen vyložený balast (turistická dinner-show, firemní eventy, atrakce), umělecké koncerty zůstaly,
- žádný horní limit se neuplatnil,
- každý koncert má `estetickeSkore` (0–100) i `duvodSkore` (jedna krátká věta, do ~90 znaků),
- popisy jsou přečištěné od balastu, ale ne uměle zkrácené (klidně 400–800 znaků),
- všechny datumy jsou v tečkovém formátu `DD.MM.YYYY`,
- `cas` z RAW je zachovaný beze změny (doplněný z popisu jen když v RAW chyběl); `cena`/`autor`
  jsou vyplněné jen tam, kde je zdroj (popis) opravdu nese – jinak null,
- `terminy` je přenesené jen u vícetermínových koncertů (datumy převedené na tečky), jinak vynechané,
- nic není vymyšlené, data pocházejí jen ze vstupního RAW souboru,
- koncerty jsou seřazené sestupně podle skóre,
- JSON přesně odpovídá zadané struktuře a je uložen jako `data/koncerty_jazzblues.json`.
