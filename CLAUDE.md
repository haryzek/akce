# CLAUDE.md — projekt "akce"

## Co stavíme a proč

Statická webová appka, která zobrazuje **kulturní akce v Praze** filtrované podle mého (Bobova)
osobního vkusu. Appka je **tupý renderer** — čte hotové JSON soubory a hezky je zobrazuje.
**Žádné AI, žádné API volání, žádný build, žádný framework.** Čistá vanilla HTML/CSS/JS.

Prototyp a první typ akce = **filmy v pražských (hlavně artových) kinech.** Další typy akcí
(kvízy, koncerty, přednášky…) se přidají později stejným systémem = další JSON soubory.

## Architektura

```
akce/
├── index.html          # jediná stránka, vanilla, žádný build
├── css/style.css       # (nebo inline ve <style>, jak uznáš za vhodné)
├── js/app.js           # (nebo inline ve <script>)
├── data/
│   ├── filmy.json      # data plněná Coworkem (viz JSON kontrakt níže)
│   └── …               # časem kvizy.json, koncerty.json atd.
└── CLAUDE.md
```

- **Jedna URL** (GitHub Pages), jedna appka, více JSON souborů (jeden na typ akce).
- Appka na startu načte všechny dostupné JSONy ze složky `data/`.
- Deploy: **GitHub Pages** (proto veřejná URL dostupná i z mobilu).

## Data flow (důležité pro pochopení celku)

```
Cowork task (jinde, používá AI)
   → research akcí + skórování podle vkusu
   → vygeneruje JSON
   → commitne JSON přímo do tohoto repa (do data/)
        → GitHub Pages se aktualizují
             → Bob otevře URL a kouká
```

Appka samotná v tomhle flow **nedělá nic chytrého** — jen renderuje to, co Cowork připravil.
Research a skórování dělá samostatný Cowork prompt (`cowork_prompt_kina.md`), který žije mimo
tento repo. Ten prompt je **kontrakt** — appka musí umět zobrazit přesně tu strukturu, kterou
prompt generuje (viz níže).

## JSON kontrakt — filmy

Soubor `data/filmy.json`. Struktura (appka na ni musí sedět 1:1):

```json
{
  "typAkce": "filmy",
  "vygenerovanoAt": "2026-07-04T14:32:00",
  "obdobiOd": "04.07.2026",
  "obdobiDo": "18.07.2026",
  "filmy": [
    {
      "nazevCz": "string",
      "nazevOrig": "string",
      "rezie": "string",
      "zanr": "string",
      "popis": "string (1-2 věty, bez spoilerů)",
      "trailerUrl": "string (odkaz na YouTube trailer, libovolná podoba) nebo null",
      "hodnoceni": {
        "rottenTomatoesAudience": 85,
        "metacriticUser": 7.8,
        "imdb": 7.2,
        "csfd": 78,
        "vazenePrumer": 81.4,
        "poznamkaHodnoceni": "string nebo null"
      },
      "estetickeSkore": 8,
      "duvodSkore": "string",
      "vlastniRecenze": "string, 3-5 vět bez spoilerů",
      "specialniProjekce": false,
      "specialniPopis": "string nebo null",
      "projekce": [
        {"datum": "10.07.2026", "cas": "20:00", "misto": "Kino Aero", "odkaz": "https://…"}
      ]
    }
  ]
}
```

Vážené skóre `vazenePrumer` počítá Cowork z vah: RT audience 40 %, Metacritic user 30 %,
IMDb 20 %, ČSFD 10 %. Appka ho jen zobrazuje, nepočítá.

Pozn.: **jeden film = jedna karta**, ale může mít **více projekcí** (pole `projekce`) —
různá kina, různé časy. Nezobrazovat stejný film víckrát.

## Funkce appky (co musí umět)

1. **Načíst** všechny JSONy z `data/` a sloučit do jednoho seznamu akcí.
2. **Řadit** defaultně podle `estetickeSkore` (sestupně). Volitelně přeřadit podle
   `vazenePrumer` (hodnocení) nebo podle nejbližšího data projekce.
3. **Filtrovat**:
   - podle **typu akce** (`typAkce`) — teď jen filmy, ale připravit UI na víc typů
   - podle **data** (rozmezí / od kdy) — akce mimo rozsah skrýt
4. **Zobrazit kartu filmu** přehledně: název (CZ + orig), režie, žánr, krátký popis,
   estetické skóre (vizuálně zvýrazněné), vážené hodnocení + rozpad na 4 zdroje,
   vlastní recenze, seznam projekcí (datum/čas/kino + odkaz), případně štítek speciální projekce.
5. Být **rozšiřitelná** — přidání nového typu akce = nový JSON + minimální/žádná změna kódu.
   Karty různých typů akcí můžou mít mírně jiný layout, ale sdílet společný základ.

## Design direction

- **Tmavý, čistý, melancholicky minimalistický.** Antracit/černá pozadí, jemné akcenty,
  hodně prostoru (whitespace), výborná typografie zaměřená na čtení.
- Klid, žádný křik, žádné gradientové cirkusy. Elegance přes zdrženlivost.
- Estetické skóre ať je vizuálně čitelné na první pohled (to je hlavní řadicí a rozhodovací
  metrika).
- Desktop first (hlavní použití domácí komp), ale ať to není rozbité na mobilu (responsivní
  aspoň basic).
- Dobrá čitelnost > efekty.

## Tvrdá pravidla

- Vanilla HTML/CSS/JS. **Žádný React, žádný build step, žádné npm závislosti**, ať to na
  GitHub Pages běží jako prostý statický web.
- Appka **nikdy nevolá žádné AI ani API.** Jen čte lokální JSON.
- Když nějaké pole v JSONu chybí nebo je `null`, appka to musí elegantně přežít (zobrazit
  „—" nebo pole skrýt), ne spadnout.
- Kód drž čitelný a komentovaný, ať se v tom Bob (vibe-coder) vyzná a umí si drobnost upravit sám.

## Poznámka k tónu (pro agenta)

Bob je zkušený uživatel, mluv s ním česky, nespisovně, na rovinu, bez korporátních vsuvek.
Preferuje flowing prózu před odrážkovými seznamy. Drž si vlastní názor a nauč se říct „tohle
bych udělal jinak, protože…".
