# Vytvoření TOP 50 filmů z programu pražských artových kin

Karolínko, přikládám:
- měsíční program kin z ČSFD (XLS),
- můj estetický profil (DOCX).

Tvým úkolem je vytvořit spolehlivý JSON, který bude sloužit jako zdroj dat pro moji filmovou aplikaci. Nejdůležitější je správnost dat. Raději vrať méně informací než informace vymyšlené. Nepoužívej žádný starší JSON ani žádná data z předchozích konverzací.

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

## KROK 5B – Najdi trailer
U každého filmu dohledávej trailer na YouTube. Priorita je mít vyplněný trailerUrl u co největšího počtu filmů.
Preferuj v tomto pořadí:
1. oficiální trailer od distributora, studia, festivalu, kina nebo streamovací platformy,
2. trailer z důvěryhodného filmového kanálu,
3. kvalitní reupload traileru,
4. jakýkoli YouTube trailer, který podle názvu, roku, režiséra nebo obsahu zjevně odpovídá danému filmu.
Nepoužívej reaction videa, rozbory, recenze, fanmade střihy, playlisty ani obecné výsledky vyhledávání. Trailer ale nemusí být dokonale oficiální. Důležitější je, aby trailerUrl nebyl zbytečně null.
Hodnotu null použij pouze tehdy, pokud se trailer nepodaří dohledat vůbec, nebo pokud existuje vážné riziko, že jde o úplně jiný film.jsi

## KROK 5C – ODKAZ NA PROGRAM KINA
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

## KROK 12 – VÝSTUP
Výstupní JSON MUSÍ být PŘESNĚ v této struktuře. Nepřidávej žádná další pole. Neměň názvy polí. Neměň pořadí polí. Neměň datové typy. Použij přesně tuto strukturu:

```json
{
  "typAkce": "filmy",
  "vygenerovanoAt": "YYYY-MM-DDTHH:MM:SS",
  "obdobiOd": "dd.mm.yyyy",
  "obdobiDo": "dd.mm.yyyy",
  "poznamka": "Surový seznam filmů z 14 artových kin (ČSFD měsíční program). Hodnocení a estetické skóre zatím nedoplněno – slouží jako zdroj pro další krok.",
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
- trailerUrl je buď přímý odkaz na konkrétní YouTube video, ideálně oficiální trailer, nebo null,
- trailerUrl nevede na fanouškovský reupload, reaction video, playlist ani vyhledávání,
- trailerUrl odpovídá přesně identifikovanému filmu.
- odkaz u projekce vede na stránku kina (film / program / hlavní web), ne na ČSFD, agregátor ani vyhledávání, nebo je null,
- odkaz u projekce není vymyšlený.

Výsledek ulož jako filmy.json.
