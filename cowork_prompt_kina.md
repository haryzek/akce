# Cowork task: Research filmů v pražských kinech

## KRITÉRIA VYHLEDÁVÁNÍ
- Typ akce: filmy v kinech
- Lokalita: Praha
- Časové rozmezí: ode dneška (den spuštění tasku) na následujících 14 dní. Nejdřív si zjisti dnešní datum a spočítej z něj rozmezí od–do ve formátu dd.mm.yyyy.

## POSTUP (v tomto pořadí, kvůli úspoře tokenů)

### Krok 1 – Najdi filmy
Projdi tato kina a agregátory a sestav seznam filmů běžících v daném období:
- Nezávislá a artová kina (primární cíl): Edison Filmhub, Kino Atlas, Komorní kino Evald,
  Kino Pilotů, Kino Aero, Kino MAT, Kino Dlabačov, Modřanský biograf, Bio Oko,
  Ponrepo, Kino Přítomnost, Kino 35 (Francouzský institut), Kino Lucerna
- Klasická kina/multiplexy (sekundární cíl): CineStar, Cinema City, Kino Hostivař
- Agregátory: GoOut.net (sekce Kino/Filmy), Kudyznudy.cz, Citybee.cz

### Krok 2 – Ohodnoť a přefiltruj
Pro každý nalezený film vyhledej hodnocení ze 4 zdrojů (mezinárodní zdroje preferuj,
ČSFD jen jako doplněk pro český kontext):
- rottentomatoes.com — **Audience/Popcornmeter score, NIKDY Tomatometer (kritici)**
- metacritic.com — User Score
- imdb.com
- csfd.cz

Spočítej **vážené skóre** s váhami:
- Rotten Tomatoes (audience) 40 %
- Metacritic (user) 30 %
- IMDb 20 %
- ČSFD 10 %

Pokud některý zdroj chybí, přepočítej váhy poměrně mezi dostupné zdroje a v poli
`poznamkaHodnoceni` uveď, který zdroj chyběl.

Poté každý film oskóruj **esteticky (1–10)** podle profilu níže a **krátce zdůvodni**.
Do dalšího kroku (Krok 3) postup pouze filmy s estetickým skóre **6 a více** —
tím se omezí počet filmů, ke kterým se dohledávají konkrétní projekce, a ušetří se čas/tokeny.

**Estetický profil (pro skórování i osobní recenzi):**

Jádro vkusu: **psychologické drama, art-house, ambiciózní sci-fi.** Sjednocující tón napříč vším
je **melancholie, existenciální tíha a syrovost** — hledá filmy, které se ptají po povaze reality,
vědomí, svobodné vůli a smyslu, a nebojí se temnoty ani ambivalence.

Silně zvyšuje skóre:
- **Vizuální propracovanost a detail** — obraz, kompozice, práce se světlem; kochá se detaily,
  vizuálno je pro něj samostatná hodnota, ne jen nosič děje.
- **Psychologická hloubka postav** — vnitřní konflikt, morální šeď, rozpad, osamělost.
- **Krajinná estetika**: pouště, polopouště, kaňony, skály, vyprahlý prostor; fascinují ho i
  megaměsta a jejich odcizenost. Film s tímhle settingem (přírodní i urbánní) skóruj výš.
- **Literární gravitace** ve stylu jeho oblíbených autorů — Cormac McCarthy (syrovost, násilí,
  metafyzika, poušť), Houellebecq (odcizení, civilizační úpadek), Frank Herbert (filozofické sci-fi),
  D. F. Wallace, Murakami (snovost, melancholie), Remarque, H. Miller. Filmy rezonující s touhle
  poetikou prioritizuj.
- **Pomalé, atmosférické, meditativní tempo** spíš než akční spád.

Snižuje / vyřazuje:
- Čisté komedie, frašky, muzikály, rodinné/dětské filmy.
- Akční blockbustery bez hlubšího přesahu, mainstreamová "oddechovka".
- **Ale**: umělecky ambiciózní snímek z malého studia nikdy nediskvalifikuj kvůli velikosti produkce
  ani nízké návštěvnosti — naopak to bývá plus.

Napiš také krátkou (3–5 vět) vlastní recenzi **bez spoilerů**, v češtině — s ohledem na tenhle profil,
tzn. řekni na rovinu, jestli si myslíš, že to Boba chytne a proč.

### Krok 3 – Dohledej projekce (jen pro filmy, co prošly filtrem)
Pro každý film, který prošel filtrem, dohledej konkrétní promítání v daném období:
datum, čas, kino, přímý odkaz na vstupenky/rozpis (kino web nebo GoOut).
Jeden film může mít víc projekcí ve víc kinech — všechny uveď.

## STRIKTNÍ PRAVIDLA
- Žádné halucinace: pokud si nejsi jistý datem/kinem, projekci nezařazuj.
- Žádné dlouhé rešerše o historii filmů/kin — jen fakta a hodnocení.
- Pokud info nezjistíš, napiš `null` (v JSON), nikdy si nedomýšlej.
- Speciální projekce (delegace tvůrců, Q&A, festivalové uvedení) označ v poli `specialniProjekce`.

## VÝSTUP
Ulož **pouze JSON** (žádný markdown okolo, žádný komentář) přesně v této struktuře:

```json
{
  "typAkce": "filmy",
  "vygenerovanoAt": "YYYY-MM-DDTHH:MM:SS",
  "obdobiOd": "dd.mm.yyyy",
  "obdobiDo": "dd.mm.yyyy",
  "filmy": [
    {
      "nazevCz": "string",
      "nazevOrig": "string",
      "rezie": "string",
      "zanr": "string",
      "popis": "string (1-2 věty, bez spoilerů)",
      "hodnoceni": {
        "rottenTomatoesAudience": 85,
        "metacriticUser": 7.8,
        "imdb": 7.2,
        "csfd": 78,
        "vazenePrumer": 81.4,
        "poznamkaHodnoceni": "string nebo null"
      },
      "estetickeSkore": 8,
      "duvodSkore": "string, krátké zdůvodnění",
      "vlastniRecenze": "string, 3-5 vět bez spoilerů",
      "specialniProjekce": false,
      "specialniPopis": "string nebo null",
      "projekce": [
        {"datum": "dd.mm.yyyy", "cas": "HH:MM", "misto": "string", "odkaz": "string"}
      ]
    }
  ]
}
```

Výsledný JSON ulož jako soubor `filmy.json` do složky "_dev/akce/data/" (přepiš stávající, pokud tam je). Nikam nic nepushuj, žádnej git, jen zapiš soubor na disk.