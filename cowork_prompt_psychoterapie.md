# Výběr a seřazení odborných psychoterapeutických akcí pro Boba

Ahoj! Tvým úkolem je z hrubého seznamu odborných akcí vytvořit spolehlivý, seřazený JSON,
který poslouží jako zdroj dat pro Bobovu aplikaci. Nejdůležitější je správnost a čistota dat.
Nic si nevymýšlej – pracuj **pouze** s tím, co je ve vstupním souboru. Žádná externí
dohledávání, žádný starší JSON.

## Vstupy (přečti si je sám ze složky projektu)
- **RAW data:** `scraper/output/odborne_psychoterapie.json` – syrový, deduplikovaný seznam
  akcí ze scraperu (7 zdrojů: ČAP, ČSPP, ČSP, PVŠPS, ČPS ČLS JEP, AKP, IPVZ).
- **Bobův estetický profil:** `support/esteticky-profil.md` – doplňkový vstup; hlavní
  profil pro tenhle typ akce je popsaný níže v Kroku 1.

> **DŮLEŽITÉ k RAW souboru:** je to **vždy kompletní, validní JSON**. Když se ti nevejde
> do jednoho čtení, **načti ho po částech** (offset/limit) a slož si celý obsah — **nikdy
> nepředpokládej, že je useknutý**, a kvůli domnělému useknutí nezahazuj žádnou položku.

## KROK 1 – UDĚLEJ SI MAPU BOBA (profesní profil)
Bob je **psychoterapeut pracující psychodynamicky a psychoanalyticky, s přesahem do KBT,
schematerapie a IFS**. Na akce chodí kvůli odbornému obohacení a inspiraci — chce si
**občas vyrazit na zajímavou jednorázovou akci**, ne nastupovat do výcviku či školy.

Co ho táhne (vyšší skóre):
- **psychoanalytické a psychodynamické myšlení**: klinické semináře, kazuistiky, čtení
  klasiků (Bion, Winnicott, Freud…), přenos/protipřenos, teorie objektních vztahů,
- **supervizní a kazuistické formáty** otevřené hostům — živá klinická práce,
- **trauma, psychosomatika, vztahová a hlubinná témata**, existenciální a daseinsanalytické
  přesahy (souzní s jeho zálibou v existenciální hloubce — viz estetický profil),
- schematerapie, IFS, párová a skupinová dynamika,
- kvalitní řečníci a instituce (ČPS/psychoanalytická obec, zavedené instituty),
- konference s dobrým tématem (trauma, válka a mír v nás, tělo v psychoterapii…).

Co ho táhne míň (nižší skóre, ale nechat v seznamu):
- čistě KBT/behaviorální témata (přesah má, ale není to jeho jádro),
- techniky vzdálené jeho praxi (koučování, asertivita, arteterapie/muzikoterapie
  jako řemeslo), wellness/ezoterický okraj (šamanismus, jóga smíchu),
- akce primárně pro jiné profese (zdravotní sestry, OSPOD, pedagogy)
  nebo pro rodiče a veřejnost.

## KROK 2 – VYHOĎ JEN VYLOŽENÝ BALAST
Odstraň položky, které fakticky **nejsou jednorázová odborná akce pro terapeuta**:
- **dlouhodobé výcviky, výukové cykly a školy** (víceletý program, „výcvik", „cyklus
  seminářů" rozložený přes rok — poznávací znamení: trvání přes ~2 měsíce nebo cena
  v řádu desetitisíců za celý cyklus),
- **povinná specializační/atestační výuka** (akce „povinná 1× za semestr", kvalifikační
  kurzy, akce výslovně jen pro zařazené do specializační přípravy — Bob v ní není),
- **zkoušky a testy** (atestační testy apod.),
- **členské a provozní schůze** (valné hromady, setkání členů, jednání institutů),
- akce **pro rodiče/veřejnost nebo děti**, ne pro odborníky,
- duplicitní zbytky (stejná akce dvakrát pod trochu jiným názvem — nech bohatší záznam).
Buď spíš zdrženlivý: když je něco na hraně (vícedenní konference, dvouvíkendový kurz
krizové intervence), NECHEJ to v seznamu – od toho je skóre. **Profil slouží k seřazení,
ne k mazání.** Žádný horní limit počtu akcí není.

## KROK 3 – SKÓRE (BOB-FIT) + DŮVOD DOPORUČENÍ
Každé zbývající akci přiřaď `estetickeSkore` na škále **0–100** (vyšší = větší šance,
že Boba obohatí a bude ho to bavit). Skóruj podle mapy z Kroku 1 — hlavně z názvu,
popisu, pořadatele a lektora.
Do `duvodSkore` napiš **jednu jedinou krátkou větu (do ~90 znaků)**, proč Bobovi akci
doporučuješ – osobně, konkrétně, žádné omáčky. (Zobrazuje se pod popisem na kartě.)

## KROK 4 – PŘEČISTI POPISY (neškrť je natvrdo)
Popisy ze zdrojů jsou často slepenec pozvánky, organizačních pokynů a právního textu.
Učeš je na čtivý text o obsahu akce:
- **vyhoď**: storno podmínky, čísla účtů, přihlašovací instrukce, GDPR/cookie věty,
  opakování datumu/místa/ceny (na to má karta vlastní pole), oslovení („Milé kolegyně…"),
- **nech**: o čem akce je, pro koho je určená, kdo ji vede a čím je zajímavá,
- medailonky přednášejících zhusti do jedné věty, pokud nesou informaci,
- klidně nech 300–800 znaků, pokud text nese obsah; karta pojme ~860 znaků a delší text
  se sám ořízne „…". Když je zdrojový popis chudý, nech ho krátký – nic nedomýšlej.
U webinářů a online akcí bez místa nastav `misto` na `"Online"` (pokud zdroj neuvádí
platformu, např. Zoom — tu pak nech).

## KROK 5 – DATUM A POLE
- Datumy převeď z `DD-MM-YYYY` (RAW) na **`DD.MM.YYYY`** (tečky).
- Pole `terminy` (pokud u položky je) přenes se stejnou konverzí datumů; má ho jen
  vícetermínová akce (např. opakovaný seminář IPVZ).
- `autor` = lektor/přednášející; když chybí a je znám pořadatel, dej pořadatele.
- Ostatní pole (misto, adresa, url, cena, thumbnail, zanr, nazevOrig) přenes beze změny;
  prázdné nech jako null. `zanr` můžeš zpřesnit (webinář/seminář/konference/supervize…),
  když je ze scraperu nepřesný nebo chybí.

## KROK 6 – SEŘAĎ
Seřaď akce **sestupně podle `estetickeSkore`** (nejlepší nahoře).

## KROK 7 – VÝSTUP
Ulož výsledek jako **`data/odborne_psychoterapie.json`**. Struktura MUSÍ být PŘESNĚ tato –
nepřidávej pole, neměň názvy, pořadí ani typy:

```json
{
  "typAkce": "odborne_psychoterapie",
  "vygenerovanoAt": "YYYY-MM-DDTHH:MM:SS",
  "obdobiOd": "dd.mm.yyyy",
  "obdobiDo": "dd.mm.yyyy",
  "odborne_psychoterapie": [
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
- vyhozen je jen vyložený balast (výcviky, povinná výuka, zkoušky, schůze, akce pro laiky),
- každá akce má `estetickeSkore` (0–100) i `duvodSkore` (jedna krátká věta, do ~90 znaků),
- popisy jsou zbavené organizačních pokynů a storno podmínek, ale nesou obsah akce,
- všechny datumy jsou v tečkovém formátu `DD.MM.YYYY` (i uvnitř `terminy`),
- online akce mají `misto` = "Online" (nebo platformu, např. "Zoom"),
- nic není vymyšlené, data pocházejí jen ze vstupního RAW souboru,
- akce jsou seřazené sestupně podle skóre,
- JSON přesně odpovídá zadané struktuře a je uložen jako `data/odborne_psychoterapie.json`.
