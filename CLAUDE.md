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
├── index.html               # jediná stránka, vanilla, žádný build
├── css/style.css            # styly
├── js/app.js                # renderer + filtry + řazení
├── data/                    # HOTOVÉ JSONy pro appku (jde na GitHub Pages)
│   ├── filmy.json           # plní Cowork/ChatGPT (viz kontrakt níže)
│   ├── vystavy.json         # plní Cowork (viz kontrakt níže)
│   └── …                    # časem kvizy.json, koncerty.json atd.
├── scraper/                 # Python nástroj: web → RAW JSON (NEjde na Pages)
│   ├── scrapni.bat          # spouštění na dvojklik (zeptá se od–do)
│   ├── run.py               # runner: sběr → dedup → zápis
│   ├── common.py            # RAW kontrakt (14 polí) + zápis souboru
│   ├── dedup.py             # deduplikace napříč zdroji (generická)
│   ├── scrapers/            # jeden modul = jeden zdroj (prague_vystavy.py…)
│   └── output/              # RAW JSONy — meziprodukt, NEpro appku
├── support/
│   └── esteticky-profil.md  # Bobův profil pro AI výběr (čte ho Cowork)
├── cowork_prompt_kina.md    # prompt pro výběr/skórování filmů (ChatGPT)
├── cowork_prompt_vystavy.md # prompt pro výběr/skórování výstav (Cowork)
└── CLAUDE.md
```

- **Jedna URL** (GitHub Pages), jedna appka, více JSON souborů (jeden na typ akce).
- Appka na startu načte všechny dostupné JSONy ze složky `data/` (seznam v `ZDROJE_DAT`
  v `js/app.js`; neexistující soubory se tiše přeskočí).
- Deploy: **GitHub Pages** (proto veřejná URL dostupná i z mobilu).
- Složky `scraper/` a `support/` jsou nástroje/podklady — leží v repu, ale appka je nepoužívá.

## Data flow (důležité pro pochopení celku)

Celý řetěz stojí na oddělení **tupých spolehlivých** dílů (scraper, appka) od **chytrého
nespolehlivého** (AI výběr). Každý dělá jednu věc pořádně:

```
1. SCRAPER (Python, scraper/)
   Bob zadá rozmezí datumu → scrapery zkopnou vhodné weby → RAW JSON per typ akce
   (scraper/output/vystavy.json …). Víc zdrojů se slévá do jednoho souboru a DEDUPLIKUJE.
        ↓
2. COWORK / ChatGPT (chytrý krok, prompt v repu)
   Vezme RAW JSON + Bobův estetický profil (support/) → vyčistí balast, oskóruje podle
   vkusu, přečistí popisy → uloží HOTOVÝ JSON do data/ (1:1 na kontrakt níže).
        ↓
3. APPKA (statická, GitHub Pages)
   Načte JSONy z data/, tupě renderuje. Žádné AI, žádné API.
        ↓
   Bob otevře URL (i z mobilu) a kouká.
```

Appka v tomhle flow **nedělá nic chytrého** — jen renderuje hotová data. Research/scrape dělá
Python, výběr a skórování dělá AI krok podle promptů (`cowork_prompt_kina.md`,
`cowork_prompt_vystavy.md`). Prompty jsou **kontrakt** — appka musí umět zobrazit přesně tu
strukturu, kterou generují (viz níže).

**Stav (2026-07):** kompletně běží filmy, výstavy, klasika (vážná hudba), Jazz&Blues (klubová
scéna), divadlo i party end-to-end. Filmy plní Bobův vychytaný ChatGPT prompt (ručně), zbytek
Cowork prompty nad RAW ze scraperu. Další typy akcí = nový scraper + nový prompt (postup viz
existující scrapery — prague.eu klony, nebo goout jako vzor JSON-API zdroje).

## Scraper (Python nástroj, `scraper/`)

Čistá vanilla Python (`requests` + `beautifulsoup4` + `tzdata`, `requirements.txt`). Účel: vytáhnout
akce do **RAW JSONu** — buď z HTML webů s čitelnou URL (prague.eu), nebo z veřejného JSON API
agregátoru (goout.net). Každý zdroj = jeden modul, mechaniku si řeší po svém, výstup je stejný RAW kontrakt.

- **Spuštění:** Bob dvojklikne `scrapni.bat`, zadá rozmezí `DD-MM-YYYY` (max ~1 měsíc),
  ono doinstaluje závislosti a spustí `run.py`. Výstup padá do `scraper/output/<typ>.json`.
- **Rozšiřitelnost:** jeden zdroj = jeden modul v `scraper/scrapers/` s `TYP_AKCE`, `ZDROJ`
  a funkcí `scrape(od, do)`. Přidat zdroj = nový modul + řádek v `SUBSCRAPERY` v `run.py`.
  Runner slévá všechny zdroje stejného typu do jednoho souboru.
- **Dedup** (`dedup.py`) je generický, běží po sběru per typ: sloučí stejnou akci z víc
  zdrojů (přísný práh na názvy odolný vůči různé délce + shoda datumu/místa), prázdná pole
  doplní z ostatních, `zdroj` → `zdroje` (list). Cíl: do AI kroku jdou desítky, ne stovky.
- **RAW kontrakt** (14 polí, každé nullovatelné): hlavička `typAkce`, `scrapedAt`,
  `obdobiOd`, `obdobiDo` + pole `polozky[]` s `zdroj`, `nazevCz`, `nazevOrig`, `autor`,
  `zanr`, `datumOd`, `datumDo`, `cas`, `misto`, `adresa`, `url`, `cena`, `thumbnail`, `popis`.
- Zdroje **prague.eu** (server-side HTML, čtou i detail akce): `prague_vystavy.py` (výstavy),
  `prague_koncerty.py` (klasika, kat. „klasická hudba"), `prague_jazzblues.py` (Jazz&Blues, kat.
  „klubová scéna" — převážně jazz/soul/blues). Koncertní scrapery jsou si datově blízké
  (jednorázová/vícetermínová akce, bez hodnocení, thumbnail) → novej stejný typ se klonuje
  z nejbližšího a mění se jen `TYP_AKCE` + `BASE` URL.
- Zdroj **goout.net** (`goout_divadlo.py` = divadlo `categories[]=play`, `goout_party.py` = party
  `categories[]=clubbing`): jiná mechanika — goout je Nuxt SPA, která si program tahá z veřejného
  JSON API (`/services/entities/v1/schedules`), a scraper volá ten endpoint napřímo. Tři odlišnosti
  od prague.eu: (1) **stránkování kurzorem** `meta.nextScrollId` (ne číslo strany; `offset` API
  ignoruje); (2) **datumový filtr serverově** přes `after`/`before` v ISO UTC (Bobovo okno se přes
  `zoneinfo` Europe/Prague převede z pražského času → proto `tzdata`); (3) **intra-zdroj dedup přímo
  v subscraperu** — API vrací `schedules` (jednotlivé termíny), jedna akce = N repríz, ale všechny
  sdílí `relationships.event.id` → seskupí se podle něj do jedné položky s polem `terminy`
  (deterministicky přes ID, ne fuzzy). Data jsou JSON:API-like: `schedules[]` + `included`
  (events/venues/images/performers) klíčované ID. Cloudflare goout nevadí, stačí realistický
  User-Agent. Pozn.: některé kategorie (clubbing) vrací i termíny mimo `after`/`before` okno —
  `goout_party.py` proto navíc lokálně filtruje termíny přes okno (guard `_v_okne`). Nový goout typ
  = klon nejbližšího `goout_*` se změnou `categories`/`tags` + mapování.
- ČSFD je za antibotem, program filmů se bere jinudy (Bobův ChatGPT prompt z ČSFD XLS).

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
různá kina, různé časy. Nezobrazovat stejný film víckrát. Pole `odkaz` u projekce (odkaz na
program kina) appka renderuje jako proklik z názvu kina, když je vyplněné.

## JSON kontrakt — výstavy

Soubor `data/vystavy.json`. Výstava je jinej tvar než film — nemá veřejná hodnocení,
projekce ani trailer, zato má trvání (rozmezí), místo a obrázek. Struktura:

```json
{
  "typAkce": "vystavy",
  "vygenerovanoAt": "2026-07-06T18:40:00",
  "obdobiOd": "01.08.2026",
  "obdobiDo": "30.08.2026",
  "vystavy": [
    {
      "nazevCz": "string",
      "nazevOrig": "string nebo null",
      "autor": "string nebo null",
      "zanr": "string nebo null",
      "datumOd": "01.08.2026",
      "datumDo": "30.08.2026",
      "misto": "string (galerie/muzeum)",
      "adresa": "string nebo null",
      "url": "string (detail na zdroji) nebo null",
      "cena": "string nebo null",
      "thumbnail": "string (URL obrázku) nebo null",
      "popis": "string (bohatý popis ze zdroje, přečištěný; karta pojme ~860 znaků)",
      "estetickeSkore": 68,
      "duvodSkore": "string (JEDNA krátká věta, proč doporučeno)"
    }
  ]
}
```

`estetickeSkore` je 0–100 (stejná škála jako filmy). Datum je tečkový `DD.MM.YYYY`. Profil
**skóruje a řadí, nelimituje** — žádný top50 strop, balast se jen vyhodí a zbytek dostane
nízké skóre. Karta výstavy: název + skóre-kolečko + srdíčko, žánr pod názvem, dominantní
popis + jednověté doporučení, dole datum rozmezí + galerie (odkaz) a klikací thumbnail (16:9).

## JSON kontrakt — termínové typy (koncerty i divadlo)

**Termínové typy** (koncerty klasika/Jazz&Blues, divadlo, party) sdílí **jeden tvar i jednu kartu** —
mají termín(y), místo, thumbnail, `autor` a žádná veřejná hodnocení; liší se jen slugem/souborem,
zdrojem a barvou akcentu. Klasika = `data/koncerty_klasika.json` (akcent modrá), Jazz&Blues =
`data/koncerty_jazzblues.json` (fialová), divadlo = `data/divadlo.json` (červená), party =
`data/party.json` (oranžová). Pole se jmenuje podle slugu (`koncerty`/`divadlo`/`party`). Struktura
je jako výstava, ale bez `nazevOrig`, s `autor`/`cas` a volitelným polem `terminy`:

```json
{
  "typAkce": "koncerty_jazzblues",
  "vygenerovanoAt": "2026-07-11T12:00:00",
  "obdobiOd": "11.07.2026",
  "obdobiDo": "10.08.2026",
  "koncerty": [
    {
      "nazevCz": "string",
      "nazevOrig": "string nebo null",
      "autor": "string nebo null (interpret/kapela; zobrazí se pod názvem místo žánru)",
      "zanr": "string nebo null",
      "datumOd": "01.08.2026",
      "datumDo": "01.08.2026",
      "cas": "20:00 nebo null",
      "misto": "string (klub/síň)",
      "adresa": "string nebo null",
      "url": "string (detail na zdroji) nebo null",
      "cena": "string nebo null",
      "thumbnail": "string (URL) nebo null",
      "popis": "string (přečištěný, ~860 znaků) nebo null",
      "estetickeSkore": 74,
      "duvodSkore": "string (JEDNA krátká věta)",
      "terminy": [
        {"datum": "04.08.2026", "cas": "20:00"}
      ]
    }
  ]
}
```

Pole `terminy` je **volitelné** — jen u vícetermínových akcí (repríz/vícedenních koncertů; list
`{datum, cas}`); jednorázová akce ho vynechá a appka si vystačí s `datumOd`/`cas`. Appka termínové
typy filtruje i řadí přes helper `jeTerminovy` a množinu `TERMINOVE_TYPY` (víc termínů → jako
filmové projekce, jinak přes interval trvání), renderuje je `vykresliKartuTerminu` a barvu bere
z mapy `TERMINOVA_CSS_TRIDA`. Karta = klon výstavní, dole datum · čas + místo (odkaz) + volitelně
cena, a „(N)" popup na další termíny jako u filmů.

## Funkce appky (co musí umět)

1. **Načíst** všechny JSONy z `data/` a sloučit do jednoho seznamu akcí.
2. **Řadit** defaultně podle `estetickeSkore` (sestupně). Volitelně podle `vazenePrumer`
   (hodnocení) nebo nejbližšího data. U výstav se řadí podle `datumOd` (nemají projekce).
3. **Filtrovat**:
   - podle **typu akce** (`typAkce`) — select se plní automaticky podle načtených dat.
   - podle **data** — filmy podle projekcí, **výstavy podle překryvu jejich trvání**
     s filtrem (funkce `maAkceVRozmezi` rozhoduje podle typu).
4. **Zobrazit kartu** — renderer je switch podle `typAkce` (`vykresliKartuFilmu`,
   `vykresliKartuVystavy`, default nic). Karta filmu: název, režie, žánr, žlutý řádek
   hodnocení, popis, důvod, recenze, projekce, trailer. Karta výstavy viz kontrakt výše.
5. **Oblíbené** (srdíčko) — generické napříč typy, drží se v `localStorage` (`akceId`
   dělá stabilní ID z toho, co je po ruce). Horní přepínač filtruje jen oblíbené.
6. **Barevný kód typu** — akcentní barva (kolečko skóre, odkazy, srdíčko) se liší podle typu:
   filmy zlatá (`--akcent`), výstavy zelená (přepis `--akcent` na `.karta-vystava`). Nový typ
   = jeden CSS řádek s vlastní barvou. V míchaném pohledu „Vše" tak oko hned pozná typ.
7. Být **rozšiřitelná** — nový typ akce = nový JSON + `case` v rendereru + barva + řádek
   v `ZDROJE_DAT`. Karty sdílí společný skeleton (vrch se skóre + srdíčko, meta, spodní
   blok kdy/kde, mediální pole), obsah si každý typ naplní po svém.

## Design direction

- **Tmavý, čistý, melancholicky minimalistický.** Antracit/černá pozadí, jemné akcenty,
  hodně prostoru (whitespace), výborná typografie zaměřená na čtení.
- Klid, žádný křik, žádné gradientové cirkusy. Elegance přes zdrženlivost.
- Estetické skóre ať je vizuálně čitelné na první pohled (to je hlavní řadicí a rozhodovací
  metrika).
- Desktop first (hlavní použití domácí komp), ale ať to není rozbité na mobilu (responsivní
  aspoň basic).
- Dobrá čitelnost > efekty.

## Jak plnit data (provozní postup)

**Výstavy (a budoucí typy se scraperem):**
1. Bob spustí `scraper/scrapni.bat`, zadá rozmezí (max ~měsíc) → vznikne
   `scraper/output/vystavy.json` (RAW, deduplikovaný).
2. Cowork task dostane `cowork_prompt_vystavy.md` → sám si přečte RAW + `support/esteticky-profil.md`,
   vybere/oskóruje, uloží `data/vystavy.json`.
3. Commit → GitHub Pages → appka ukazuje.

**Filmy (zatím bez scraperu):** Bob má vlastní vychytaný ChatGPT prompt
(`cowork_prompt_kina.md`) — vloží měsíční program kin z ČSFD (XLS) + profil, ChatGPT
dohledá hodnocení/trailery/odkazy a vyplivne `data/filmy.json`.

Prompty jsou verzované v repu a jsou **kontrakt** — když se mění struktura JSONu nebo karty,
musí se změnit i příslušný prompt (a naopak). Estetický profil (`support/esteticky-profil.md`)
je společný vstup pro AI výběr; drží se odděleně, protože se cizeluje dlouhodobě.

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
