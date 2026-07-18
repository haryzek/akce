# Vytvoření TOP 50 filmů z programu pražských artových kin

Karolínko, přikládám:
- měsíční program kin z ČSFD (XLS),
- můj estetický profil (DOCX).

Tvým úkolem je vytvořit spolehlivý JSON, který bude sloužit jako zdroj dat pro moji filmovou aplikaci. Nepoužívej žádný starší JSON ani žádná data z předchozích konverzací.

## KROK 1 – ZPRACUJ PROGRAM KIN
Program je strukturován:
Praha – název kina
↓
datum
↓
filmy
↓
časy
Vytěž všechny projekce. Pokud jsou časy zalomené na další řádek, připoj je ke stejnému filmu.

## KROK 2 – FILTR KIN
Použij pouze tato kina:
- Bio Oko
- Edison Filmhub
- Kino Aero
- Kino Atlas
- Kino Lucerna
- Kino MAT
- Kino Pilotů
- Kino Světozor
- Komorní kino Evald
- Modřanský biograf
- Přítomnost Boutique Cinema
- Kampus Hybernská
- MeetFactory
- Spirála

Jakékoli jiné kino kompletně ignoruj.

## KROK 3 – OČIŠTĚNÍ NÁZVŮ
Odstraň suffixy sálů:
- Gold Class
- Dolby Atmos
- Dolby Atmos sál
- IMAX
- VIP
- Theatre Deluxe
- 4DX sál
- ČSFD Sál
- jiné obdobné názvy sálů

Například
PozváníČSFD Sál
↓
Pozvání

## KROK 4 – SLOUČENÍ PROJEKCÍ
Jeden film = jeden objekt. Spoj všechny projekce stejného filmu. Nejdříve slučuj podle českého názvu. Později po identifikaci podle:
originální název + rok + režisér.

## KROK 5A – IDENTIFIKUJ FILMY
U každého filmu zjisti: originální název, režiséra, žánr, stručný popis
České názvy bývají nejednoznačné. Proto vždy nejdříve ověř identitu filmu.
Používej dostupné veřejné databáze (například ČSFD jako rozcestník, IMDb, TMDb, Letterboxd, Wikipedii, stránky kin nebo distributora).
Pokud si nejsi jistá identitou, nic si nevymýšlej.

## KROK 5B – ODKAZ NA PROGRAM KINA
U každé projekce dohledej `odkaz` na program (webovou stránku) toho kina, kde se projekce koná. Cílem je, aby mě odkaz z karty filmu dovedl co nejblíž k nákupu lístku.
Preferuj v tomto pořadí:
1. stránka konkrétního filmu na webu daného kina,
2. stránka programu / rozvrhu daného kina,
3. hlavní web daného kina.
Nevymýšlej si URL. Nepoužívej odkaz na ČSFD, agregátory ani obecné vyhledávání. Deep-link přímo do košíku na konkrétní čas nedohledávej – spolehlivě neexistuje; stačí spolehlivá stránka kina.
Pokud se spolehlivý odkaz na dané kino nepodaří dohledat, ponech `odkaz` null. Nikdy odkaz nevymýšlej.

## KROK 6 – BOB-FIT
Na základě mého estetického profilu spočítej pro VŠECHNY filmy hodnotu:
estetickeSkore 0–100
Vyšší skóre znamená vyšší pravděpodobnost, že se mi film bude líbit.
Při výpočtu využij celý můj estetický profil.
Neomezuj se pouze žánrem.
Hodnoť hlavně:
- psychologickou hloubku
- existenciální témata
- autorskou režii
- vizuální styl
- filozofický přesah
- morální ambivalenci
- melancholii
- inteligentní sci-fi
- evropský, japonský a kvalitní americký autorský film

Naopak snižuj skóre u:
- dětských animáků
- rutinních blockbusterů
- generických komedií
- čistě efektových filmů
- laciných hororů
- filmů bez psychologické hloubky

Do pole duvodSkore stručně vysvětli své rozhodnutí.

## KROK 7 – VÝBĚR KANDIDÁTŮ
Spočítej Bob-fit pro všechny filmy.
Poté seřaď všechny filmy podle Bob-fit.
Následně vyber kandidáty pro dohledávání veřejných hodnocení.
Pokud je filmů s vysokým Bob-fit méně než 50, postupně přidávej další filmy podle pořadí Bob-fit, dokud nebudeš mít alespoň 50 kandidátů.

## KROK 8 – DOHLEDÁNÍ VEŘEJNÝCH HODNOCENÍ
Pouze u těchto kandidátů dohledávej:
- Rotten Tomatoes – Použij výhradně Audience Score (ne Tomatometer).
- Metacritic – Použij výhradně User Score (ne Metascore kritiků).
- IMDb – Použij běžný IMDb rating.
- ČSFD – Použij procentuální hodnocení.

Pokud některé hodnocení není dostupné, ponech hodnotu null. Nikdy hodnoty nevymýšlej.

## KROK 9 – VÁŽENÉ SKÓRE
Spočítej:
- Rotten Tomatoes Audience 40 %
- Metacritic User 30 %
- IMDb 20 %
- ČSFD 10 %

IMDb i Metacritic nejdříve převeď na škálu 0–100.
Pokud některý zdroj chybí, normalizuj váhy pouze podle dostupných zdrojů.

## KROK 10 – FINÁLNÍ VÝBĚR
Po výpočtu veřejných hodnocení spočítej interně:
70 % Bob-fit
30 % vážené veřejné skóre.
Toto skóre slouží pouze pro výběr. Do JSON jej nezapisuj.
Podle něj vyber TOP 50 filmů.

## KROK 11 – RECENZE
Ke každému filmu napiš: krátký popis a vlastní doporučení pro mě.
Bez spoilerů.
Nepřebírej dlouhé citace z recenzí.
Shrň vlastními slovy.

## KROK 12 – Najdi trailer

Tento krok je povinná validační brána. Finální soubor filmy.json nesmíš vytvořit, dokud neprovedeš samostatné a důkladné vyhledávání traileru pro každý jednotlivý film z finální TOP 50.

Pro každý film proveď postupně minimálně tato vyhledávání:

"český název" trailer
"originální název" trailer
"originální název" official trailer
"originální název" rok trailer
"originální název" režisér trailer
český název i originální název přímo na YouTube
případně název filmu v původním písmu nebo alternativní anglický distribuční název

Výsledky vyhodnocuj podle identity filmu, nikoli podle oficiality kanálu. Ověř shodu alespoň pomocí názvu, roku, režiséra, herců, popisu nebo obrazového obsahu.

Povolené jsou:

oficiální trailery,
festivalové a distribuční trailery,
trailery zveřejněné kinem nebo streamovací službou,
kvalitní reupload původního traileru,
původní kinotrailer ze starého nebo archivního filmového kanálu,
teaser trailer, pokud plnohodnotný trailer neexistuje,
trailer bez českých titulků,
trailer v původním jazyce.

Nepoužívej pouze reaction videa, recenze, videoeseje, fanmade sestřihy, playlisty, vyhledávací stránky ani videa, která zjevně patří k jinému filmu.

trailerUrl: null je povoleno pouze ve zcela výjimečném případě, kdy všechna výše uvedená hledání selhala. Neoficialita, nízký počet zhlédnutí, staré video, cizí jazyk ani neznámý YouTube kanál nejsou důvodem pro null.

Před odevzdáním vytvoř interní kontrolní seznam všech 50 filmů a u každého zaznamenej:

nalezeno / nenalezeno,
použitý vyhledávací dotaz,
název nalezeného videa,
důvod, proč video odpovídá danému filmu.

Tento kontrolní seznam nevkládej do výsledného JSON, ale použij jej pro závěrečnou validaci.

Pokud je trailerUrl vyplněno u méně než 50 filmů, nepovažuj úkol za dokončený. Vrať se ke všem filmům s hodnotou null a proveď druhý rešeršní průchod s alternativními názvy, rokem, režisérem, původním jazykem a méně přísnými nároky na zdroj.

Cílový stav je přesně:

50 filmů / 50 přímých odkazů na konkrétní YouTube video

Teprve po druhém kompletním průchodu může výjimečně zůstat null. V takovém případě musí být v poznamkaHodnoceni stručně uvedeno, že trailer nebyl nalezen ani po opakovaném hledání. Nikdy nepoužij null jen proto, že jsi našla pouze neoficiální, archivní nebo cizojazyčný trailer.

Za neúspěšný výsledek považuj jakýkoli JSON, ve kterém není trailerUrl vyplněn alespoň u 48 z 50 filmů. Pokud je vyplněn u méně filmů, vrať se k položkám s hodnotou null a pokračuj v hledání; soubor zatím nevytvářej.

## KROK 13 – VÝSTUP
Výstupní JSON MUSÍ být PŘESNĚ v této struktuře. Nepřidávej žádná další pole. Neměň názvy polí. Neměň pořadí polí. Neměň datové typy. Použij přesně tuto strukturu:

```json
{
  "typAkce": "filmy",
  "vygenerovanoAt": "YYYY-MM-DDTHH:MM:SS",
  "obdobiOd": "dd.mm.yyyy",
  "obdobiDo": "dd.mm.yyyy",
  "poznamka": "Výběr TOP 50 filmů z programu 14 pražských artových kin, seřazený podle kombinace estetického profilu a dostupných veřejných hodnocení.",
  "filmy": [
    {
      "nazevCz": "",
      "nazevOrig": null,
      "rezie": null,
      "zanr": null,
      "popis": null,
      "trailerUrl": null,
      "hodnoceni": {
        "rottenTomatoesAudience": null,
        "metacriticUser": null,
        "imdb": null,
        "csfd": null,
        "vazenePrumer": null,
        "poznamkaHodnoceni": null
      },
      "estetickeSkore": null,
      "duvodSkore": null,
      "vlastniRecenze": null,
      "specialniProjekce": false,
      "specialniPopis": null,
      "projekce": [
        {
          "datum": "dd.mm.yyyy",
          "cas": "HH:MM",
          "misto": "",
          "odkaz": null
        }
      ]
    }
  ]
}
```

## KONTROLA PŘED ODEVZDÁNÍM
Před vytvořením souboru proveď kontrolu:
- jsou použita pouze povolená kina,
- nejsou v názvech filmů suffixy sálů,
- žádný film není duplicitně,
- všechny projekce jsou správně sloučené,
- Rotten Tomatoes používá pouze Audience Score,
- Metacritic používá pouze User Score,
- veřejná hodnocení nejsou vymyšlená,
- vážené skóre je správně spočítané,
- JSON obsahuje maximálně 50 filmů,
- JSON přesně odpovídá zadané struktuře.
- trailerUrl je buď přímý odkaz na konkrétní YouTube video nebo null (zcela výjimečně, jen když nenajdeš ani stopu po traileru),
- trailerUrl nevede na fanmade trailer, reaction video, rozbor, recenzi, playlist ani vyhledávání; kvalitní reupload skutečného původního traileru je povolen,
- odkaz u projekce vede na stránku kina (film / program / hlavní web), ne na ČSFD, agregátor ani vyhledávání, nebo je null,
- odkaz u projekce není vymyšlený.

Výsledek ulož jako filmy.json.
