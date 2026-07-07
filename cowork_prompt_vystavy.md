# Výběr a seřazení pražských výstav pro Boba

Ahoj! Tvým úkolem je z hrubého seznamu výstav vytvořit spolehlivý, seřazený JSON, který
poslouží jako zdroj dat pro Bobovu aplikaci. Nejdůležitější je správnost a čistota dat.
Nic si nevymýšlej – pracuj **pouze** s tím, co je ve vstupním souboru. Žádná externí
dohledávání, žádná hodnocení z internetu, žádný starší JSON.

## Vstupy (přečti si je sám ze složky projektu)
- **RAW data:** `scraper/output/vystavy.json` – syrový, deduplikovaný seznam výstav ze scraperu.
- **Bobův estetický profil:** `support/esteticky-profil.md` – kompletní profil.

## KROK 1 – UDĚLEJ SI MAPU BOBA (pro vizuální umění)
Přečti si CELÝ estetický profil, ne jen sekci o vizuálu. Sestav si vlastní vnitřní mapu
toho, co Boba na umění a výstavách táhne. Vodítka (neomezuj se na ně):
- existenciální hloubka, samota, ticho, introspekce, melancholie, atmosféra světla a prostoru,
- emocionální pravdivost a estetická integrita nad čistým konceptem,
- přesahy do jeho témat: vědomí, povaha reality, fyzika, kognitivní vědy, AI, technologie,
  psychologie, filozofie mysli,
- afinita k impresionismu, expresionismu, rané moderně (Hopper, van Gogh, Cézanne, Monet),
  ale i k modernímu umění, pokud drží emocionální a vizuální srozumitelnost.
Bob NEMÁ rád: čistě konceptuální, cynické nebo záměrně prázdné umění, intelektuální provokaci
bez estetické či emocionální kvality.

## KROK 2 – VYHOĎ JEN VYLOŽENÝ BALAST
Odstraň položky, které fakticky **nejsou umělecká/kulturní výstava**, například:
- veletrhy a sběratelské burzy (známky, mince, minerály…),
- dětské pátrací/venkovní hry a čistě edukativní atrakce pro děti,
- ryze turistické prohlídkové okruhy a expozice bez uměleckého přesahu
  (historické sály, kasematy, „příběh hradu", propagační expozice institucí).
Buď spíš zdrženlivý: když je něco na hraně (menší galerie, komorní nebo konceptuálnější
projekt), NECHEJ to v seznamu – od toho je skóre. **Profil slouží k seřazení, ne k mazání.**
Žádný horní limit počtu výstav není – nech všechno, co uměleckou výstavou opravdu je.

## KROK 3 – ESTETICKÉ SKÓRE (BOB-FIT) + DŮVOD DOPORUČENÍ
Každé zbývající výstavě přiřaď `estetickeSkore` na škále **0–100** (vyšší = větší šance,
že se Bobovi bude líbit). Skóruj podle své mapy z Kroku 1, hlavně z názvu, autora, žánru
a popisu.
Do `duvodSkore` napiš **jednu jedinou krátkou větu (do ~90 znaků)**, proč Bobovi tuhle
výstavu doporučuješ – osobně, konkrétně, žádné omáčky. (Zobrazuje se pod popisem na kartě.)

## KROK 4 – PŘEČISTI POPISY (neškrť je natvrdo)
U výstav je popis ze zdroje to nejcennější, proto ho **nech bohatý** – jen ho učeš:
- odstraň marketingové fráze, opakování, zbytečná zalomení a balast,
- oprav zjevné překlepy a rozházené znaky, sjednoť do plynulého textu, bez spoilerů,
- **neškrť pod smysl** – klidně nech 400–800 znaků, pokud text nese obsah.
Karta v aplikaci pojme zhruba **860 znaků**; delší text se sám elegantně ořízne „…", takže
se nemusíš trefovat do limitu. Necpi ale výplň jen kvůli délce – když je zdrojový popis
krátký, nech ho krátký. Když popis ve vstupu chybí (null), nech null – nic nedomýšlej.

## KROK 5 – DATUM
Datumy převeď z formátu `DD-MM-YYYY` (RAW) na **`DD.MM.YYYY`** (tečky), který používá aplikace.
Ostatní pole (misto, adresa, url, cena, thumbnail, autor, zanr, nazevOrig) přenes beze změny;
prázdné nech jako null.

## KROK 6 – SEŘAĎ
Seřaď výstavy **sestupně podle `estetickeSkore`** (nejlepší nahoře).

## KROK 7 – VÝSTUP
Ulož výsledek jako **`data/vystavy.json`**. Struktura MUSÍ být PŘESNĚ tato – nepřidávej pole,
neměň názvy, pořadí ani typy:

```json
{
  "typAkce": "vystavy",
  "vygenerovanoAt": "YYYY-MM-DDTHH:MM:SS",
  "obdobiOd": "dd.mm.yyyy",
  "obdobiDo": "dd.mm.yyyy",
  "vystavy": [
    {
      "nazevCz": "",
      "nazevOrig": null,
      "autor": null,
      "zanr": null,
      "datumOd": "dd.mm.yyyy",
      "datumDo": "dd.mm.yyyy",
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

`obdobiOd`/`obdobiDo` vezmi z hlavičky RAW souboru (převeď na tečkový formát).
`vygenerovanoAt` = aktuální čas.

## KONTROLA PŘED ODEVZDÁNÍM
- vyhozen je jen vyložený balast (veletrhy, dětské hry, turistické okruhy), umělecké výstavy zůstaly,
- žádný horní limit se neuplatnil,
- každá výstava má `estetickeSkore` (0–100) i `duvodSkore` (jedna krátká věta, do ~90 znaků),
- popisy jsou přečištěné od balastu, ale ne uměle zkrácené (klidně 400–800 znaků),
- všechny datumy jsou v tečkovém formátu `DD.MM.YYYY`,
- nic není vymyšlené, data pocházejí jen ze vstupního RAW souboru,
- výstavy jsou seřazené sestupně podle skóre,
- JSON přesně odpovídá zadané struktuře a je uložen jako `data/vystavy.json`.
