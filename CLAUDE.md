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
├── cowork_prompt_psychoterapie.md # prompt pro odborné akce pro terapeuty (Cowork)
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
scéna), divadlo, party i odborné akce pro psychoterapeuty end-to-end. Filmy plní Bobův vychytaný
ChatGPT prompt (ručně), zbytek Cowork prompty nad RAW ze scraperu. Dva zdroje mají **party**
(ra.co + goout.net) i **výstavy** (prague.eu + goout.net), **psychoterapie** jich má sedm
(profesní organizace + vzdělavatelé, viz níže). Další typy
akcí = nový scraper + nový prompt (postup viz existující scrapery — prague.eu klony, goout jako
vzor JSON-API zdroje, ra.co jako vzor GraphQL zdroje).

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
  Shoda názvu (`_nazev_shoda`) bere **maximum z containmentu a znakového ratia** (každá
  metrika chytá jiný typ rozdílu) a porovnává **kmeny slov** (`_kmen` uřízne českou koncovku,
  ať „Muzeum Karla Zemana" potká „Stálá expozice Muzea Karla Zemana").
  Má **agresivní profily** (`deduplikuj(polozky, profil="party")`), zapínané per typ přes
  `PROFIL_DEDUP` v `run.py` — dnes jen `party`. Profil přidává druhou cestu ke sloučení:
  *místo + konkrétní den + aspoň jedno výrazné společné slovo* (nebo podobnost názvu ≥ 0.5).
  Proč: RA a goout dávají téže klubovce různě dlouhý název („Poseidon" vs „POSEIDON:
  Paralich, TRANSmisia, …") a přísný práh je nespojí. Dva guardy proti přestřelení —
  `GENERICKA_SLOVA` (aby „techno"/„night" samo nespojilo dvě párty) a `SATELITNI_SLOVA`
  (aby se afterparty neslila s hlavní akcí: „Ben Böhmer LIVE" vs „Ben Böhmer Afterparty").
  **Výstavy profil schválně nemají** — zkoušený tolerantnější práh (0.62 + povinné místo
  i překryv trvání) přidal na reálných datech 4 sloučení a všechna byla chybná („Hornictví"
  + „Hutnictví" v NTM). Výstavy mají krátké popisné názvy, které si jsou v jedné instituci
  přirozeně podobné. Nedávej jim profil, přísné pravidlo tu stačí.
- **RAW kontrakt** (14 polí, každé nullovatelné): hlavička `typAkce`, `scrapedAt`,
  `obdobiOd`, `obdobiDo` + pole `polozky[]` s `zdroj`, `nazevCz`, `nazevOrig`, `autor`,
  `zanr`, `datumOd`, `datumDo`, `cas`, `misto`, `adresa`, `url`, `cena`, `thumbnail`, `popis`.
- Zdroje **prague.eu** (server-side HTML, čtou i detail akce): `prague_vystavy.py` (výstavy),
  `prague_koncerty.py` (klasika, kat. „klasická hudba"), `prague_jazzblues.py` (Jazz&Blues, kat.
  „klubová scéna" — převážně jazz/soul/blues). Koncertní scrapery jsou si datově blízké
  (jednorázová/vícetermínová akce, bez hodnocení, thumbnail) → novej stejný typ se klonuje
  z nejbližšího a mění se jen `TYP_AKCE` + `BASE` URL.
- Zdroj **goout.net** (`goout_divadlo.py` = divadlo `categories[]=play`, `goout_party.py` = party
  `categories[]=clubbing`, `goout_vystavy.py` = výstavy `categories[]=exhibitions`): jiná mechanika — goout je Nuxt SPA, která si program tahá z veřejného
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
- **`goout_vystavy.py`** (druhý zdroj výstav vedle prague.eu). Odchylky od ostatních goout
  scraperů, první tři plynou z toho, že výstava trvá měsíce, kdežto párty jeden večer:
  (1) **`grouped=true`** — zásadní,
  protože výstava má vlastní `schedule` na KAŽDÝ otevírací den, takže s `grouped=false` vrátí
  stránka 50 záznamů = jedna jediná výstava (s `true` je to ~48 různých); (2) **trvání se bere
  z `event.attributes.schedulesRange`** ({first,last}), ne ze `schedule.startAt/endAt` — grouped
  schedule nese často jen ten jeden den, co spadl do okna, a appka filtruje výstavy překryvem
  trvání, takže useknutý rozsah by ji rozbil; (3) **filtr doprovodného programu** (`_je_balast`) —
  goout pod `exhibitions` vede i komentované prohlídky, workshopy, dětské dny a vstupenky
  („Roční členství Kunsthalle Praha"), filtr je konzervativní a zbytek dočistí Cowork prompt
  (poznávací znamení: `datumOd` == `datumDo`); (4) **stálé expozice pryč** přes
  `schedule.attributes.isPermanent` — dvě třetiny toho, co goout vede pod výstavami, jsou
  trvalky (Loreta, Muzeum Karla Zemana, Zoo Mořský Svět), Bobovi jde o aktuální dění.
  **Druhá pojistka `je_trvalka()` v `common.py`** (trvání ≥ 365 dní): goout `isPermanent`
  nedává spolehlivě (ATLAS běží 4 roky a označený není) a **prague.eu žádný takový příznak
  nemá vůbec**, proto ji používají oba scrapery výstav. V `prague_vystavy.py` je schválně
  *před* dotažením detailu, ať se na trvalku zbytečně nejezdí. Práh má rezervu — nejdelší
  legitimní výstava v reálných datech měla 178 dní;
  (5) **žánrový filtr lokálně, ne v API** (`ZANRY_BOB` + `_zanr_sedi`) — Bob chce jen výtvarné
  žánry (na webu `?genres=…`), ale serverový `tags[]` whitelist použít NELZE: pětina dočasných
  výstav nemá vyplněný žádný tag a whitelist by je zahodil, přičemž jsou to zrovna ty nejlepší
  (Kentridge, Petrbok, Bienále, Vytiska). Pravidlo je proto **„má Bobův žánr NEBO nemá žádný"**;
  bonusem vypadne balast, co se z názvu pozná špatně (`in_city_guided_tour`, `workshop`,
  `for_children_*`). Navíc `exhibitionMeta.curator` → `autor`.
  Dohromady tyhle filtry srazí goout z 220 na ~40 položek a RAW z 4455 na 2345 řádků.
- Zdroj **ra.co** (`ra_party.py` — Resident Advisor, druhý zdroj typu `party` vedle goout).
  Třetí mechanika v repu: ra.co je Next.js SPA s nekonečným scrollem, ale program tahá
  z **veřejného GraphQL endpointu** `POST https://ra.co/graphql` — scraper ho volá napřímo,
  bez cookies a tokenu, stačí realistický User-Agent (DataDome na endpoint nesahá). Praha =
  `areaId 451` (z `__NEXT_DATA__` na /events/cz/prague). Proti goout je to jednodušší:
  **stránkování je normální číslo strany** (`page`/`pageSize` + `totalResults`) a **datumový
  filtr je serverový a spolehlivý** (`filters.listingDate: {gte, lte}` v `YYYY-MM-DD`),
  takže lokální guard netřeba. Popis (`content`), cena, žánry i adresa jdou **rovnou
  v listingu** — detail akce dotahovat netřeba. Dvě pasti: (1) RA `cost` je volný text bez
  konzistentní měny („300", „33", „80€", „??") → `_cena()` pouští dál jen to, z čeho jde měna
  poznat, zbytek zahodí a nechá doplnit dedupem z goout; (2) popisy jsou **anglicky** a mívají
  na konci provozní přílepky (set-times, ceníky, safe-space kodexy) → řeší Cowork prompt,
  který je překládá do češtiny a přílepky vyhazuje.
- Typ **odborne_psychoterapie** (odborné akce pro terapeuty — semináře, webináře, supervize,
  konference; NE výcviky, výuka ani členské schůze): **sedm zdrojů, sedm mechanik**, sdílená
  logika (parsování českých datumů z volného textu, okno, filtry výcviků/dlouhodobých akcí,
  odhad žánru) žije v `scrapers/psychoterapie_common.py`. Zdroje:
  `czap_psychoterapie.py` (ČAP — Wild Apricot, server-side HTML se sémantickými třídami
  `eventInfo*`; filtruje „setkání" = členské schůze), `cspap_psychoterapie.py` (ČSPP —
  WordPress plugin The Events Calendar má **veřejné REST API** `/wp-json/tribe/events/v1/events`
  se serverovým datumovým filtrem; filtruje „UZAVŘENÁ AKCE"), `csp_psychoterapie.py`
  (ČSP psychoanalyza.cz — TEC klon ČSPP, půjčuje si z něj `stahni_tec`/`preved_event`;
  agresivně filtruje „Výuka PI" a „KURZ IKP" = výuka institutu), `pvsps_psychoterapie.py`
  (PVŠPS víkendovky — e-shop výpis `div.item` + stránkování `?productlist_page=N` + detail
  pro místo/cenu/popis; past: obsazené semináře na konci výpisu nemají datum → bez termínu
  i na detailu se zahazují, jinak by lezly do každého okna), `cps_psychoterapie.py`
  (ČPS ČLS JEP psychoterapeuti.cz — Joomla blog, VOLNÝ text; datumy/čas/místo/cena se loví
  regexy, jednotky akcí), `akp_psychoterapie.py` (AKP — Google Sites, jedna akce = jeden
  `<section>` s `<h2>`; past: datumy rozlámané přes `<span>`y „2 . 12 .20 26" → `najdi_datumy`
  toleruje mezery uvnitř), `ipvz_psychoterapie.py` (IPVZ — React SPA, ale program jede z
  veřejného JSON API `portal.ipvz.cz/api/v1/portal/educationEventTerms/list?studyDepartmentId=58`
  = katedra klinické psychologie, vrací vše naráz; termíny téže akce se grupují podle názvu
  do `terminy`, URL detailu se skládá `{id}-{slug}`; filtruje zkoušky/testy).
  Scraper filtruje jen tvrdé jistoty, jemné rozhodování (povinná specializační výuka, akce
  pro laiky, KBT vs. psychodynamika) dělá `cowork_prompt_psychoterapie.md`.
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

## Filmotéka — „filmy na doma" (`data/filmy_doma.json`)

Samostatný pohled **mimo běžné filtry a typy akcí**: referenční žebříček ~3100 filmů
z films101.com oskórovaných podle Bobova profilu (jednorázový AI výstup, ne scraper).
Zapíná se ikonkou filmového pásu v rychlých volbách (přepínač jako srdíčko/hvězda,
třída `.pas`, stav `REZIM_DOMA` + `body.rezim-doma`). V režimu se schovají typ, řazení,
datumy i datumové zkratky; srdíčko, hvězda a pás zůstávají.

JSON má tvar filmového kontraktu s odchylkami: navíc `rok` a `hodnoceni.films101`
(škála 0–5), veřejná hodnocení jsou null, `projekce` prázdné, text je (dočasně) jen
v `duvodSkore` — appka ho renderuje jako popis (fallback na `popis`). Karta
(`vykresliKartuFilmuDoma`, třída `karta-doma`) prohazuje metriky: **kolečko =
`vazenePrumer`** (zaokrouhlený), **žlutý řádek = `estetickeSkore` + f101** (číslo bold);
meta řádek je „režie · rok".

Zásadní pro výkon: soubor má **3+ MB**, proto **není v `ZDROJE_DAT`** a stahuje se
líně až při prvním zapnutí režimu (`nactiFilmyDoma`); renderuje se po dávkách 100 karet
přes **infinite scroll** (zarážka `#doma-zarazka` + `DOMA_OBSERVER`, předstih 1200px).
Thumbnaily trailerů jsou `<img loading="lazy">` (ne background-image), takže se stahují
až u viewportu. Fulltext (`#hledani-doma`) hledá substring bez diakritiky
v předpočítaném řetězci název+režie+rok+žánr — schválně bez rozlišování polí.
Srdíčka mají prefix `filmy_doma::`, takže watchlist se nemíchá s oblíbenými z kin.

Klik na **kolečko skóre** karty (i v dashboardu) přepíná **„viděno"** — kolečko zezelená
(`--videno`), drží se v localStorage (`akce-videno`, stejná ID jako srdíčka) a synchronizuje
se mezi kartou a dashboardem (`prepniVideno`, třída `.skore-klik`).

Klik na kartu otevře **fullscreen dashboard filmu** (`otevriDashboardFilmu`, overlay
`#dashboard-film`, zavírá křížek/Esc): velký trailer (maxres thumbnail s fallbackem),
plné texty, skóre blok, srdíčko (synchronizované se seznamem přes `prepniSrdce`),
**wiki box s nalitým obsahem** (viz níže) a **boxíky-rozcestníky** — ty nic nestahují,
jen staví vyhledávací URL (YouTube/Google/JustWatch/ČSFD/IMDb/Letterboxd/Wikipedia)
z `nazevOrig + rok + rezie` a otevírají je v novém tabu. Dole pás příbuzných: další filmy
režiséra, fallback „podobný vibe" (stejný hlavní žánr, ±15 let); tiles otevírají další
dashboardy. Trailery mají ověřené URL (skript přes YouTube oEmbed; ~99,5 % pokrytí).

Dashboard zkouší nejdřív `maxresdefault.jpg` (karta v seznamu rovnou `hqdefault.jpg`) —
past: když `maxresdefault` pro video neexistuje, YouTube **nevrátí chybu**, jen tiše
podstrčí 120×90 šedou zástupnou grafiku (HTTP 200), takže `onerror` fallback na ni
nezareaguje. Řeší `onload` kontrola `naturalWidth<=120` → přepnutí na `hqdefault.jpg`.

**Wiki box a IMDb odkaz = jediné dvě povolené API výjimky v appce** (viz Tvrdá pravidla):

- **Wiki box**: dashboard po otevření dotáhne z Wikipedie intro extract + hlavní
  obrázek (plakát) + URL článku. Jeden dotaz na action API (`generator=search` +
  `extracts|pageimages|info`, **nutné `pilicense=any`** — filmové plakáty jsou non-free
  a bez toho nechodí), EN primárně, CS fallback, cache per film (`WIKI_CACHE`), async
  dolití s guardem na přepnutí filmu (`naplnWikiBox`). Selhání = decentní hláška.
- **IMDb**: boxík v Profilech startuje jako fallback `imdb.com/find` a async se
  přepne na přímý odkaz na film (`naplnImdbAStremio` → `imdbId`), přes IMDb vlastní
  **suggest endpoint** `v2.sg.media-imdb.com/suggestion/<písmeno>/<slug>.json`
  (CORS povolený — používá ho jejich vlastní našeptávač, bez klíče). Matchuje se
  podle roku (`film.rok`), tolerance ±1 rok, bez shody zůstane fallback link.
  Stejné ID recykluje i **Stremio boxík** v „Kde to vidět" (start jako fallback
  `strem.io` homepage) — Stremio adresuje obsah přes IMDb ID (Cinemeta addon),
  deep link je `stremio:///detail/movie/<tt>/<tt>` (bez `?autoPlay=true`, ať
  uživatel dostane výběr zdrojů, ne riziko prázdné obrazovky bez nastavených
  addonů). Žádný nový fetch — obě boxíky sdílí jeden `imdbId()` lookup.
- **ČSFD, Rotten Tomatoes, Metacritic nemají veřejné CORS API** (ověřeno), zůstávají
  jako site-scoped Google odkazy (`site:csfd.cz/film`, `site:rottentomatoes.com/m`,
  `site:metacritic.com/movie` + název + rok) — spolehlivější než fuzzy search
  jednotlivých webů u běžných názvů (Solaris, Stalker apod.).

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

**Termínové typy** (koncerty klasika/Jazz&Blues, divadlo, party, psychoterapie) sdílí **jeden tvar
i jednu kartu** — mají termín(y), místo, thumbnail, `autor` a žádná veřejná hodnocení; liší se jen
slugem/souborem, zdrojem a barvou akcentu. Klasika = `data/koncerty_klasika.json` (akcent modrá),
Jazz&Blues = `data/koncerty_jazzblues.json` (fialová), divadlo = `data/divadlo.json` (červená),
party = `data/party.json` (oranžová), psychoterapie = `data/odborne_psychoterapie.json` (teal).
Pole se jmenuje podle slugu (`koncerty`/`divadlo`/`party`/`odborne_psychoterapie`). Struktura
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
   Dvě šedé ikonky vlevo od filtru typu — export/import srdíček i „viděno".
   Primárně **tiché čtení/zápis do vybrané složky** přes File System Access API
   (`PODPORA_FS_API`, jen Chrome/Edge — appka je statická, tohle je nejblíž
   „appka si sama píše na disk", co bezpečnostní model prohlížeče dovolí):
   první klik ukáže systémový výběr složky (Bob v něm vybere `local/` — API
   neumí dialog na cestu navést), handle se zapamatuje v IndexedDB
   (`ziskejSlozkuZalohy`), příští kliky už jedou beze ptaní a přepisují pořád
   stejný soubor `local/akce-zaloha.json` (= vždy „poslední verze", žádné
   datumové kopie). Kdekoliv to selže nebo API chybí (Firefox/Safari/mobil),
   spadne se na klasické stažení/nahrání (`exportujZalohu`/`naimportujZalohu`,
   `input[type=file]`) — SLUČuje se s aktuálním stavem (union do Setů), nikdy
   nemaže.
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
- Desktop first (hlavní použití domácí komp), ale ať to není rozbité na mobilu — pod 600px
  (`@media` na konci `style.css`) se filtry sbalí za hamburger (`menu-prepinac` →
  `#ovladaci-obsah.otevreno`), hledací pole filmotéky zůstává vidět i po sbalení
  (mimo sbalitelný obal, je to hlavní ovládací prvek toho režimu). Past, na kterou
  narazit znovu: grid/flex položky mají default `min-width:auto`, takže se nesmrsknou
  pod svůj obsah — `.karta` proto má `min-width: 0` explicitně.
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
- Appka **nikdy nevolá žádné AI ani API.** Jen čte lokální JSON. **Dvě výjimky:**
  dashboard filmotéky smí dotáhnout obsah z Wikipedie a přímé ID z IMDb suggest
  endpointu (obojí otevřené API bez klíče, CORS, deterministické, bez AI) — nic
  dalšího, žádné další služby.
- Když nějaké pole v JSONu chybí nebo je `null`, appka to musí elegantně přežít (zobrazit
  „—" nebo pole skrýt), ne spadnout.
- Kód drž čitelný a komentovaný, ať se v tom Bob (vibe-coder) vyzná a umí si drobnost upravit sám.

## Poznámka k tónu (pro agenta)

Bob je zkušený uživatel, mluv s ním česky, nespisovně, na rovinu, bez korporátních vsuvek.
Preferuje flowing prózu před odrážkovými seznamy. Drž si vlastní názor a nauč se říct „tohle
bych udělal jinak, protože…".
