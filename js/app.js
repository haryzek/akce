// ---- app.js ----
// Tupý renderer: načte JSONy z data/, slouží filtry a řazení, vykreslí karty.
// Žádné AI, žádné API, jen práce s hotovými daty.

// Seznam JSON souborů, které se appka pokusí načíst při startu. Prohlížeč neumí
// přečíst obsah složky, tak držíme seznam očekávaných souborů tady. Soubory, které
// ještě neexistují, se ticho přeskočí — takže klidně nech v seznamu i budoucí typy.
// Přidat nový typ akce = přidat sem řádek (+ časem jeho vlastní kartu ve vykresliKartu).
const ZDROJE_DAT = [
  "data/filmy.json",
  "data/vystavy.json",
  "data/kvizy.json",
  "data/koncerty_klasika.json",
  "data/koncerty_jazzblues.json",
  "data/divadlo.json",
  "data/party.json",
  "data/prednasky.json",
  "data/odborne_psychoterapie.json",
];

// Termínové typy sdílí stejný datový tvar i kartu (koncerty klasika/jazz&blues, divadlo…):
// mají jeden nebo víc termínů, místo, thumbnail a žádná veřejná hodnocení — liší se jen
// zdrojem a barvou akcentu. Ať se nemusí vyjmenovávat na deseti místech, drží se tady.
const TERMINOVE_TYPY = new Set([
  "koncerty_klasika", "koncerty_jazzblues", "divadlo", "party", "odborne_psychoterapie",
]);
const jeTerminovy = (typ) => TERMINOVE_TYPY.has(typ);

let VSECHNY_AKCE = []; // sloučená, normalizovaná data ze všech zdrojů

// ---- režim "filmy na doma" (filmotéka) ----
// Samostatný pohled mimo běžné filtry: referenční žebříček filmů na doma
// (data/filmy_doma.json, ~3000 položek). Zapíná se ikonkou filmového pásu.
// Soubor má 3+ MB, proto se NENAČÍTÁ při startu, ale až při prvním zapnutí režimu.
let REZIM_DOMA = false;
let FILMY_DOMA = null; // null = soubor se ještě nestahoval; pak [{data, hledaci}]
let HLEDANI_DOMA = ""; // aktuální text ve vyhledávání
let DOMA_OBSERVER = null; // IntersectionObserver pro infinite scroll (vytváří init)
let DOMA_MAPA = new Map(); // domaId -> film (lookup pro dashboard po kliku na kartu)
const DOMA_DAVKA = 100; // karet na jednu dávku renderu (3000 karet naráz by DOM zabilo)
let DOMA_LIMIT = DOMA_DAVKA; // kolik karet je právě zobrazeno (infinite scroll zvyšuje)

// ---- oblíbené (localStorage, generické napříč typy akcí) ----

const OBLIBENE_KLIC = "akce-oblibene";
let JEN_OBLIBENE = false; // stav horního přepínače (jen runtime, nepersistuje se)

// horní přepínač "jen špička": aktivní = ukáže jen akce s estetickeSkore >= TOP_PRAH,
// napříč všemi typy i nezávisle na ostatních filtrech (škála je jednotná 0–100).
const TOP_PRAH = 80;
let JEN_TOP = false; // stav (jen runtime, nepersistuje se)

// Stabilní ID akce s prefixem typu, ať se různé typy nesrazí a přežije to přegenerování dat.
// Bere co je po ruce napříč typy; pro filmy = "filmy::nazevOrig|rezie".
function akceId(polozka) {
  const d = polozka.data || {};
  const nazev = d.nazevOrig || d.nazevCz || d.nazev || d.title || "";
  const dopl = d.rezie || d.autor || d.interpret || d.misto || "";
  return `${polozka.typAkce}::${nazev}|${dopl}`;
}

function nactiOblibene() {
  try {
    return new Set(JSON.parse(localStorage.getItem(OBLIBENE_KLIC) || "[]"));
  } catch {
    return new Set(); // rozbité/nedostupné úložiště appku nepoloží
  }
}

let OBLIBENE = nactiOblibene();

function ulozOblibene() {
  try {
    localStorage.setItem(OBLIBENE_KLIC, JSON.stringify([...OBLIBENE]));
  } catch {
    /* privátní režim / plné úložiště — tiše přejdeme, srdíčko aspoň drží do reloadu */
  }
}

// ---- viděné filmy (filmotéka) — klik na kolečko skóre, drží se v localStorage ----

const VIDENO_KLIC = "akce-videno";

function nactiVideno() {
  try {
    return new Set(JSON.parse(localStorage.getItem(VIDENO_KLIC) || "[]"));
  } catch {
    return new Set();
  }
}

let VIDENO = nactiVideno();

function ulozVideno() {
  try {
    localStorage.setItem(VIDENO_KLIC, JSON.stringify([...VIDENO]));
  } catch {
    /* stejné jako u oblíbených — tiše přejít */
  }
}

// Přepne "viděno" a synchronizuje všechna kolečka téhož filmu (karta + dashboard)
function prepniVideno(id) {
  const nove = !VIDENO.has(id);
  if (nove) VIDENO.add(id);
  else VIDENO.delete(id);
  ulozVideno();
  document.querySelectorAll(".skore[data-id]").forEach((s) => {
    if (decodeURIComponent(s.dataset.id) !== id) return;
    s.classList.toggle("videno", nove);
  });
}

// srdíčko na kartě (dva stavy). Sdílený helper, ať ho každý typ karty jen zavolá.
const IKONA_SRDCE =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.7l-1.55-1.4C6 15 2.75 12.1 2.75 8.5 2.75 5.9 4.8 3.9 7.4 3.9c1.5 0 2.9.7 3.8 1.8.9-1.1 2.3-1.8 3.8-1.8 2.6 0 4.65 2 4.65 4.6 0 3.6-3.25 6.5-7.7 10.8L12 20.7z"/></svg>';

// hvězda pro horní přepínač "jen špička" (stejný styl a dva stavy jako srdce)
const IKONA_HVEZDA =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.6l2.85 6.02 6.6.62-4.98 4.38 1.48 6.48L12 16.9l-5.95 3.2 1.48-6.48L2.55 9.24l6.6-.62z"/></svg>';

// filmový pás pro přepínač režimu "filmy na doma". Dvě cesty, mezi kterými přepíná
// CSS podle stavu (jako obrys→výplň u srdce/hvězdy): v klidu čárová obrysovka
// (samé linky — stroke na drobných uzavřených tvarech by se při 1.9rem slil do
// plochy), aktivní stav plný tvar s vyříznutými perforacemi a okénky (evenodd).
const IKONA_PAS =
  '<svg viewBox="0 0 24 24" aria-hidden="true">' +
  '<path class="pas-obrys" d="' +
  'M3.5 4.5h17v15h-17z ' + // obrys těla
  'M7.5 4.5v15 M16.5 4.5v15 ' + // sloupce perforace
  'M7.5 12h9 ' + // předěl okének
  'M3.5 9.5h4 M3.5 14.5h4 M16.5 9.5h4 M16.5 14.5h4' + // příčky perforace
  '"/>' +
  '<path class="pas-vypln" fill-rule="evenodd" d="' +
  'M3.5 4.5h17v15h-17z ' + // tělo pásu
  'M4.7 6h1.6v2H4.7z M4.7 11h1.6v2H4.7z M4.7 16h1.6v2H4.7z ' + // perforace vlevo
  'M17.7 6h1.6v2h-1.6z M17.7 11h1.6v2h-1.6z M17.7 16h1.6v2h-1.6z ' + // perforace vpravo
  'M8.8 5.8h6.4v4.9H8.8z M8.8 13.3h6.4v4.9H8.8z' + // dvě okénka
  '"/></svg>';

function vykresliSrdce(id, jeOblibene) {
  const stav = jeOblibene ? " je-oblibene" : "";
  return `<button type="button" class="srdce${stav}" data-id="${encodeURIComponent(id)}" aria-label="Oblíbené" aria-pressed="${jeOblibene}">${IKONA_SRDCE}</button>`;
}

// ---- automatická záloha do místní složky (File System Access API) ----
// Jen Chrome/Edge (žádný server, appka je statická — tohle je nejblíž "appka si
// sama čte/píše na disk", co bezpečnostní model prohlížeče vůbec dovolí). První
// klik ukáže systémový výběr složky (Bob v něm ručně najde a vybere `local/` —
// API neumí dialog na cestu navést), handle se uloží do IndexedDB a příště se
// znovu použije bez ptaní. Kde API není (Firefox/Safari/mobil), spadne se potichu
// na klasické stažení/nahrání (exportujZalohu/naimportujZalohu níže).
const ZALOHA_SOUBOR = "akce-zaloha.json"; // pevné jméno = v local/ vždy jen "poslední verze"
const PODPORA_FS_API = "showDirectoryPicker" in window;

function otevriZalohaDb() {
  return new Promise((resolve, reject) => {
    const pozadavek = indexedDB.open("akce-zaloha-db", 1);
    pozadavek.onupgradeneeded = () => pozadavek.result.createObjectStore("handles");
    pozadavek.onsuccess = () => resolve(pozadavek.result);
    pozadavek.onerror = () => reject(pozadavek.error);
  });
}

async function nactiUlozenouSlozku() {
  try {
    const db = await otevriZalohaDb();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction("handles", "readonly");
      const ziskej = tx.objectStore("handles").get("slozka");
      ziskej.onsuccess = () => resolve(ziskej.result || null);
      ziskej.onerror = () => reject(ziskej.error);
    });
  } catch {
    return null; // IndexedDB nedostupné (privátní režim apod.) — příště se prostě zase zeptá
  }
}

async function ulozSlozku(handle) {
  try {
    const db = await otevriZalohaDb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction("handles", "readwrite");
      tx.objectStore("handles").put(handle, "slozka");
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  } catch {
    /* nevadí, jen se handle nezapamatuje a příští klik znovu ukáže výběr složky */
  }
}

// Vrátí handle na složku se zápisovým oprávněním — z paměti (IndexedDB), nebo
// (poprvé/po odvolání oprávnění) čerstvě přes systémový dialog.
async function ziskejSlozkuZalohy() {
  const ulozeny = await nactiUlozenouSlozku();
  if (ulozeny) {
    let opravneni = await ulozeny.queryPermission({ mode: "readwrite" });
    if (opravneni !== "granted") opravneni = await ulozeny.requestPermission({ mode: "readwrite" });
    if (opravneni === "granted") return ulozeny;
  }
  const vybrany = await window.showDirectoryPicker({ mode: "readwrite" });
  await ulozSlozku(vybrany);
  return vybrany;
}

async function exportujZalohuAutomaticky() {
  const slozka = await ziskejSlozkuZalohy();
  const zaloha = { exportovanoAt: new Date().toISOString(), oblibene: [...OBLIBENE], videno: [...VIDENO] };
  const soubor = await slozka.getFileHandle(ZALOHA_SOUBOR, { create: true });
  const zapis = await soubor.createWritable();
  await zapis.write(JSON.stringify(zaloha, null, 2));
  await zapis.close();
}

async function naimportujZalohuAutomaticky() {
  const slozka = await ziskejSlozkuZalohy();
  let handle;
  try {
    handle = await slozka.getFileHandle(ZALOHA_SOUBOR);
  } catch {
    alert(`Ve vybrané složce zatím není ${ZALOHA_SOUBOR} — nejdřív jednou ulož zálohu (šipka dolů).`);
    return;
  }
  const data = JSON.parse(await (await handle.getFile()).text());
  const noveOblibene = Array.isArray(data.oblibene) ? data.oblibene : [];
  const noveVideno = Array.isArray(data.videno) ? data.videno : [];
  noveOblibene.forEach((id) => OBLIBENE.add(id));
  noveVideno.forEach((id) => VIDENO.add(id));
  ulozOblibene();
  ulozVideno();
  prekresli();
}

// Stáhne zálohu localStorage (oblíbené + viděné filmy) jako JSON — pro případ
// nechtěného smazání. Čte živé Sety (držené synchronně s localStorage při každé
// změně), ne přímo localStorage, ať export vždy sedí s aktuálním stavem appky.
// Fallback pro prohlížeče bez File System Access API (viz výše).
function exportujZalohu() {
  const zaloha = {
    exportovanoAt: new Date().toISOString(),
    oblibene: [...OBLIBENE],
    videno: [...VIDENO],
  };
  const blob = new Blob([JSON.stringify(zaloha, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const odkaz = document.createElement("a");
  odkaz.href = url;
  odkaz.download = `akce-zaloha-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(odkaz);
  odkaz.click();
  odkaz.remove();
  URL.revokeObjectURL(url);
}

// Nahraje zálohu zpět — SLUČUJE s aktuálním stavem (union), nic nemaže. Bezpečné
// i při omylem druhém nahrání stejného souboru (Set ignoruje duplicity).
function naimportujZalohu(soubor) {
  const cteni = new FileReader();
  cteni.onload = () => {
    let data;
    try {
      data = JSON.parse(cteni.result);
    } catch {
      alert("Soubor se nepodařilo přečíst — není to platná záloha appky Akce.");
      return;
    }
    const noveOblibene = Array.isArray(data.oblibene) ? data.oblibene : [];
    const noveVideno = Array.isArray(data.videno) ? data.videno : [];
    noveOblibene.forEach((id) => OBLIBENE.add(id));
    noveVideno.forEach((id) => VIDENO.add(id));
    ulozOblibene();
    ulozVideno();
    prekresli(); // ať se srdíčka/kolečka na obrazovce hned zobrazí správně
    alert(`Záloha nahrána: ${noveOblibene.length} oblíbených, ${noveVideno.length} viděných (sloučeno s aktuálním stavem).`);
  };
  cteni.readAsText(soubor);
}

// ---- pomocné funkce ----

// "10.07.2026" -> Date objekt, ať se dá řadit/filtrovat
function parsujDatum(retezec) {
  if (!retezec) return null;
  const [den, mesic, rok] = retezec.split(".").map(Number);
  if (!den || !mesic || !rok) return null;
  return new Date(rok, mesic - 1, den);
}

// "2026-07-05" z <input type=date> -> lokální Date (ne UTC!). konecDne=true nastaví
// čas na 23:59:59.999, ať se horní mez chová jako "celý ten den včetně".
function parsujIsoDatum(retezec, konecDne = false) {
  if (!retezec) return null;
  const [rok, mesic, den] = retezec.split("-").map(Number);
  if (!rok || !mesic || !den) return null;
  return konecDne
    ? new Date(rok, mesic - 1, den, 23, 59, 59, 999)
    : new Date(rok, mesic - 1, den);
}

// najde nejbližší nadcházející (nebo aspoň nejbližší) datum projekce z pole projekcí
function nejblizsiDatumProjekce(projekce) {
  if (!projekce || projekce.length === 0) return null;
  const datumy = projekce
    .map((p) => parsujDatum(p.datum))
    .filter((d) => d !== null)
    .sort((a, b) => a - b);
  return datumy[0] || null;
}

function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
}

// bezpečné čtení — pole ve stavu null/chybí appku nesmí položit
function hodnotaNebo(hodnota, nahrada = "—") {
  return hodnota === null || hodnota === undefined || hodnota === "" ? nahrada : hodnota;
}

// text bez diakritiky a malými písmeny — pro vyhledávání ("tarkov" najde Tarkovského)
function bezDiakritiky(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

// ---- načtení dat ----

async function nactiVsechnaData() {
  const vysledky = await Promise.all(
    ZDROJE_DAT.map(async (cesta) => {
      try {
        // no-cache = vždy ověřit u serveru, jestli se soubor nezměnil (data se mění
        // často a prohlížeč jinak umí držet starý JSON i přes obyčejný refresh)
        const odpoved = await fetch(cesta, { cache: "no-cache" });
        // soubor pro tenhle typ zatím neexistuje (404) — ticho přeskoč, není to chyba
        if (!odpoved.ok) return null;
        return await odpoved.json();
      } catch (chyba) {
        // sem spadne jen skutečný problém (rozbitý JSON, síť) — ten chceme vidět
        console.warn(`Chyba při čtení ${cesta}:`, chyba);
        return null;
      }
    })
  );

  const akce = [];
  for (const soubor of vysledky) {
    if (!soubor) continue;
    // Položky jsou v poli pojmenovaném podle typu akce (filmy -> soubor.filmy,
    // kvizy -> soubor.kvizy...). Když to nesedí, vezmeme první pole v objektu.
    const typ = soubor.typAkce || "neznamy";
    let polozky = Array.isArray(soubor[typ]) ? soubor[typ] : null;
    if (!polozky) {
      const klic = Object.keys(soubor).find((k) => Array.isArray(soubor[k]));
      polozky = klic ? soubor[klic] : [];
    }
    for (const polozka of polozky) {
      akce.push({ typAkce: typ, data: polozka });
    }
  }
  return akce;
}

// ---- filmy na doma: načtení a render ----

// Lazy načtení data/filmy_doma.json (až při prvním zapnutí režimu — soubor má 3+ MB).
// Každý film dostane předpočítaný "hledaci" řetězec (název + režie + rok + žánr bez
// diakritiky), ať fulltext při psaní nefiltruje přes normalize() tři tisíce položek pořád dokola.
async function nactiFilmyDoma() {
  if (FILMY_DOMA) return FILMY_DOMA;
  try {
    // no-cache je tu zásadní: fetch běží až při kliknutí na pás, takže ho nekryje
    // ani Ctrl+F5 — bez něj umí prohlížeč podstrčit starý JSON z diskové cache
    const odpoved = await fetch("data/filmy_doma.json", { cache: "no-cache" });
    if (!odpoved.ok) throw new Error(`HTTP ${odpoved.status}`);
    const soubor = await odpoved.json();
    FILMY_DOMA = (soubor.filmy || []).map((f) => ({
      data: f,
      hledaci: bezDiakritiky(
        [f.nazevCz, f.nazevOrig, f.rezie, f.rok, f.zanr].filter(Boolean).join(" ")
      ),
    }));
    // žebříček se řadí jednou tady (podle estetického skóre), režim nemá volbu řazení
    FILMY_DOMA.sort((a, b) => (b.data.estetickeSkore ?? -1) - (a.data.estetickeSkore ?? -1));
    DOMA_MAPA = new Map(FILMY_DOMA.map((f) => [domaId(f.data), f.data]));
  } catch (chyba) {
    console.warn("Chyba při čtení data/filmy_doma.json:", chyba);
    FILMY_DOMA = []; // ať se to nezkouší stahovat pořád dokola a appka žije dál
  }
  return FILMY_DOMA;
}

// ID pro srdíčka ve filmotéce — vlastní prefix, ať se watchlist "na doma" nemíchá
// s oblíbenými u filmů v kinech (jiný seznam, jiný význam srdíčka)
function domaId(film) {
  return akceId({ typAkce: "filmy_doma", data: film });
}

// Karta filmu "na doma" — klon filmové karty s prohozenými metrikami: v kolečku je
// vážený průměr (zaokrouhlený, ať se vejde), ve žlutém řádku estetické skóre + films101.
// Bez projekcí (žádné nejsou), popis se dočasně bere z duvodSkore (viz JSON kontrakt).
function vykresliKartuFilmuDoma(film, id) {
  const prumer = film.hodnoceni?.vazenePrumer;
  const skore = prumer === null || prumer === undefined ? "—" : Math.round(prumer);
  const rezieRok = [film.rezie, film.rok].filter(Boolean).join(" · ");

  // žlutý řádek: vpředu estetické skóre s ikonkou (role váženého průměru), za ním films101
  const est =
    film.estetickeSkore !== null && film.estetickeSkore !== undefined
      ? `<span class="prumer">${IKONA_PRUMER}${escapeHtml(film.estetickeSkore)}</span>`
      : "";
  const f101 =
    film.hodnoceni?.films101 !== null && film.hodnoceni?.films101 !== undefined
      ? `<span class="zdroj"><strong>f101</strong> <span class="zdroj-cislo">${escapeHtml(film.hodnoceni.films101)}</span></span>`
      : "";
  const radekHodnoceni = `<div class="hodnoceni-radek">${est + f101 || '<span class="bez-hodnoceni">Bez hodnocení</span>'}</div>`;

  return `
    <article class="karta karta-doma" data-film-id="${encodeURIComponent(id)}">
      <div class="karta-vrch">
        <div class="karta-vrch-text">
          <div class="karta-titulky">
            <h2>${escapeHtml(film.nazevCz)}</h2>
            ${film.nazevOrig && film.nazevOrig !== film.nazevCz ? `<p class="nazev-orig">${escapeHtml(film.nazevOrig)}</p>` : ""}
          </div>

          <div class="meta-blok">
            <div class="meta-radek">${escapeHtml(hodnotaNebo(rezieRok))}</div>
            <div class="meta-radek">${escapeHtml(hodnotaNebo(film.zanr))}</div>
            ${radekHodnoceni}
          </div>
        </div>

        <div class="karta-vpravo">
          <div class="skore skore-klik${VIDENO.has(id) ? " videno" : ""}" data-id="${encodeURIComponent(id)}"
               title="Vážený průměr · kliknutím označíš jako viděno">${escapeHtml(skore)}</div>
          ${vykresliSrdce(id, OBLIBENE.has(id))}
        </div>
      </div>

      <p class="popis">${escapeHtml(hodnotaNebo(film.duvodSkore ?? film.popis))}</p>

      ${vykresliTrailer(film.trailerUrl)}
    </article>
  `;
}

// ---- dashboard filmu (fullscreen popup ve filmotéce) ----

// Klik na kartu filmotéky otevře přes celé okno dashboard: velký trailer, plné texty,
// skóre, a boxíky-rozcestníky = předpřipravené vyhledávací odkazy (appka nic nestahuje,
// jen chytře zkonstruuje dotaz a otevře ho v novém tabu — viz tvrdé pravidlo bez API).

function ytSearch(dotaz) {
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(dotaz)}`;
}

function googleSearch(dotaz) {
  return `https://www.google.com/search?q=${encodeURIComponent(dotaz)}`;
}

// Boxíky-rozcestníky po sekcích. Dotazy staví na originálním názvu + roku (+ režii),
// to vyhledávače trefují nejlíp. Každá položka: [emoji, popisek, url].
function dashBoxy(film) {
  const nazev = film.nazevOrig || film.nazevCz || "";
  const rok = film.rok || "";
  const rezie = film.rezie || "";
  const zaklad = `${nazev} ${rok}`.trim();
  // čtvrtý prvek položky: true = boxík přes celou šířku sloupce, pátý = id pro pozdější dolití
  return [
    ["Kde to vidět", [
      // start jako neškodný fallback (Stremio homepage); naplnImdbAStremio přepne na
      // přímý deep link, jakmile dohledá IMDb ID (recykluje se s IMDb boxíkem níže)
      ["▶️", "Otevřít ve Stremiu", "https://www.strem.io/", true, "dash-stremio-box"],
      ["🔍", "Google", googleSearch(`${zaklad} film`), true],
    ]],
    ["Hlubší ponor", [
      ["🎙️", "Rozhovory s režisérem", ytSearch(`${rezie} interview ${nazev}`)],
      ["🎬", "Making-of a dokumenty", ytSearch(`${zaklad} making of documentary`)],
      ["🧠", "Video eseje a rozbory", ytSearch(`${zaklad} video essay analysis`)],
      ["🎵", "Soundtrack", ytSearch(`${zaklad} soundtrack`)],
    ]],
    ["Kritika", [
      ["✍️", "Roger Ebert", googleSearch(`site:rogerebert.com ${nazev}`)],
      ["🏛️", "Criterion eseje", googleSearch(`site:criterion.com ${nazev} essay`)],
      ["🟢", "Letterboxd recenze", `https://letterboxd.com/search/${encodeURIComponent(nazev)}/`],
    ]],
    // Profily: ani ČSFD, ani RT/Metacritic nemají veřejné CORS API pro přímý lookup
    // (jen IMDb má — viz imdbId níže), takže jedou přes site-scoped Google s rokem —
    // u běžných názvů (Solaris, Stalker) je to spolehlivější než fuzzy search webu
    // samotného, protože rok v dotazu prakticky vždy vytáhne správný film jako první.
    ["Profily", [
      // IMDb start jako fallback hledání; naplnImdbBox po vyhodnocení nahradí přímým odkazem
      ["🎞️", "IMDb", `https://www.imdb.com/find/?q=${encodeURIComponent(zaklad)}`, false, "dash-imdb-box"],
      ["🇨🇿", "ČSFD", googleSearch(`site:csfd.cz/film ${zaklad}`)],
      ["🍅", "Rotten Tomatoes", googleSearch(`site:rottentomatoes.com/m ${zaklad}`)],
      ["Ⓜ️", "Metacritic", googleSearch(`site:metacritic.com/movie ${zaklad}`)],
    ]],
  ];
}

// Pás příbuzných filmů dole: primárně další filmy téhož režiséra, když žádné nejsou,
// spadne na "podobný vibe" = stejný hlavní žánr a éra (±15 let). Vše z vlastních dat.
function dashPribuzne(film) {
  const id = domaId(film);
  const odRezisera = FILMY_DOMA
    .filter((f) => f.data.rezie && f.data.rezie === film.rezie && domaId(f.data) !== id)
    .map((f) => f.data);
  if (odRezisera.length) {
    // bez limitu — pás je svislý sloupec s prostorem do nekonečna
    return { titulek: `Další od: ${film.rezie}`, filmy: odRezisera, rezie: true };
  }
  const hlavniZanr = (film.zanr || "").split(",")[0].trim().toLowerCase();
  const rok = Number(film.rok) || null;
  const vibe = FILMY_DOMA
    .filter((f) => {
      if (domaId(f.data) === id) return false;
      if (!hlavniZanr || !(f.data.zanr || "").toLowerCase().includes(hlavniZanr)) return false;
      const r = Number(f.data.rok);
      return !rok || (r && Math.abs(r - rok) <= 15);
    })
    .map((f) => f.data);
  return { titulek: "Podobný vibe (žánr a éra)", filmy: vibe.slice(0, 12), rezie: false };
}

// Trailer pro dashboard: velká facade s maxres thumbnailem (fallback na hqdefault,
// maxres u starých filmů často chybí). Bez traileru nabídne aspoň vyhledání na YT.
function vykresliDashTrailer(film) {
  const id = youtubeId(film.trailerUrl);
  if (id) {
    // wrapper je nutný: prehrajFacade nahrazuje facade.parentElement.innerHTML
    // iframem — bez vlastního obalu by tím parentem byl rovnou .dash-hlavni
    // a spuštění trailem by smazalo i popis a wiki box pod ním (byl to bug)
    return `
      <div class="dash-trailer-slot">
        <button type="button" class="trailer-facade dash-trailer" data-yt-id="${id}" aria-label="Přehrát trailer">
          <img class="trailer-thumb" src="https://i.ytimg.com/vi/${id}/maxresdefault.jpg" alt=""
               onerror="this.onerror=null;this.src='https://i.ytimg.com/vi/${id}/hqdefault.jpg'"
               onload="if(this.naturalWidth<=120){this.onload=null;this.src='https://i.ytimg.com/vi/${id}/hqdefault.jpg';}">
          <span class="trailer-play" aria-hidden="true"></span>
        </button>
      </div>`;
  }
  const dotaz = `${film.nazevOrig || film.nazevCz || ""} ${film.rok || ""} trailer`.trim();
  return `
    <div class="dash-trailer dash-trailer-chybi">
      <p>Trailer se nepodařilo dohledat.</p>
      <a href="${ytSearch(dotaz)}" target="_blank" rel="noopener">Zkusit najít na YouTube →</a>
    </div>`;
}

// ---- Wikipedia box (jediná povolená API výjimka — otevřené API, bez klíče, CORS) ----
// Jeden dotaz: fulltext search + intro extract + hlavní obrázek + kanonická URL.
// Primárně anglická Wikipedia (filmová pokrytost), fallback česká. Cache per film.

const WIKI_CACHE = new Map(); // domaId -> {titul, text, obrazek, url} | null

async function hledejWiki(host, dotaz) {
  const url =
    `https://${host}/w/api.php?action=query&generator=search` +
    `&gsrsearch=${encodeURIComponent(dotaz)}&gsrlimit=1` +
    `&prop=extracts|pageimages|info&explaintext=1&exsectionformat=wiki` + // celý článek, nadpisy jako "== Plot =="
    `&piprop=original&pilicense=any&inprop=url&format=json&origin=*`; // pilicense=any: plakáty jsou non-free
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    const j = await r.json();
    const pages = j.query?.pages;
    if (!pages) return null;
    const p = Object.values(pages)[0];
    if (!p || !p.extract) return null;
    return {
      titul: p.title,
      text: p.extract,
      obrazek: p.original?.source || null,
      url: p.fullurl || `https://${host}/wiki/${encodeURIComponent(p.title)}`,
    };
  } catch {
    return null;
  }
}

async function nactiWiki(film) {
  const id = domaId(film);
  if (WIKI_CACHE.has(id)) return WIKI_CACHE.get(id);
  const nazev = film.nazevOrig || film.nazevCz || "";
  const dotaz = `${nazev} ${film.rok || ""} film`.trim();
  const vysledek =
    (await hledejWiki("en.wikipedia.org", dotaz)) ||
    (await hledejWiki("cs.wikipedia.org", dotaz));
  WIKI_CACHE.set(id, vysledek);
  return vysledek;
}

// Za tímhle nadpisem už v plaintextu nic čitelného není (seznamy odkazů, citace) —
// článek se usekne před první z těchto sekcí (EN i CZ varianty)
const WIKI_STOP_SEKCE = new Set([
  "references", "external links", "see also", "further reading", "notes",
  "bibliography", "sources", "footnotes",
  "reference", "externí odkazy", "odkazy", "literatura", "poznámky", "související články",
]);

// Plaintext extract (nadpisy jako "== Plot ==") -> HTML s pořádnými odstavci.
// DŮLEŽITÉ: MediaWiki extract odděluje jednotlivé odstavce JEN JEDNÍM \n — dvojitý
// \n\n se objevuje pouze před nadpisem sekce. Proto je každý neprázdný řádek vlastní
// <p> (i položky seznamů typu Cast — vyjde to jako spaced list, ne jako slitý blok).
// Prázdné řádky (jen kolem nadpisů) se přeskočí, nenesou obsah.
function wikiTextNaHtml(text) {
  const vystup = [];
  for (const radek of String(text).split("\n")) {
    if (!radek.trim()) continue;
    const nadpis = radek.match(/^(={2,})\s*(.+?)\s*={2,}$/);
    if (nadpis) {
      if (WIKI_STOP_SEKCE.has(nadpis[2].trim().toLowerCase())) break;
      // úroveň podle počtu "=" (== hlavní, === podsekce)
      const trida = nadpis[1].length > 2 ? "dash-wiki-nadpis dash-wiki-podnadpis" : "dash-wiki-nadpis";
      vystup.push(`<span class="${trida}">${escapeHtml(nadpis[2])}</span>`);
      continue;
    }
    vystup.push(`<p>${escapeHtml(radek)}</p>`);
  }
  return vystup.join("");
}

// Doplní wiki box v otevřeném dashboardu (volá se async po vykreslení skeletonu).
// Guard: mezitím mohl uživatel přejít na jiný film — pak výsledek zahodit.
async function naplnWikiBox(film) {
  const overlay = document.getElementById("dashboard-film");
  const id = domaId(film);
  const wiki = await nactiWiki(film);
  if (overlay.hidden || decodeURIComponent(overlay.dataset.filmId || "") !== id) return;
  const box = overlay.querySelector(".dash-wiki-obsah");
  if (!box) return;
  if (!wiki) {
    box.innerHTML =
      '<p class="dash-wiki-nenalezeno">Na Wikipedii se nepodařilo nic dohledat.</p>';
    return;
  }
  // plakát plave vpravo uvnitř scrollovatelného textu — novinová sazba
  box.innerHTML = `
    <div class="dash-wiki-text">${wiki.obrazek ? `<img class="dash-wiki-obrazek" src="${escapeHtml(wiki.obrazek)}" alt="" loading="lazy">` : ""}${wikiTextNaHtml(wiki.text)}</div>
    <a class="dash-wiki-odkaz" href="${escapeHtml(wiki.url)}" target="_blank" rel="noopener">číst celé na Wikipedii (${escapeHtml(wiki.titul)}) →</a>`;
}

// ---- IMDb přímý odkaz (druhá povolená API výjimka — veřejný, CORS-povolený
// suggest endpoint, který IMDb sám používá pro našeptávač; bez klíče, bez AI) ----
// RT a Metacritic obdobný endpoint nemají (ověřeno — CORS blokuje), proto tam
// zůstává jen site-scoped Google z dashBoxy výše.

const IMDB_CACHE = new Map(); // domaId -> "tt1234567" | null

async function imdbId(film) {
  const id = domaId(film);
  if (IMDB_CACHE.has(id)) return IMDB_CACHE.get(id);
  const nazev = (film.nazevOrig || film.nazevCz || "").trim();
  const slug = nazev.toLowerCase().replace(/[^a-z0-9]+/g, "");
  let vysledek = null;
  if (slug) {
    try {
      const r = await fetch(
        `https://v2.sg.media-imdb.com/suggestion/${slug[0]}/${encodeURIComponent(slug)}.json`
      );
      if (r.ok) {
        const j = await r.json();
        const kandidati = (j.d || []).filter((x) => x.qid === "movie" || x.q === "feature");
        const rok = Number(film.rok) || null;
        // přesná shoda roku vyhrává (řeší remaky/stejnojmenné filmy); bez roku první nabídnutý
        const presny = rok ? kandidati.find((k) => k.y === rok) : null;
        const nejblizsi =
          presny ||
          (rok
            ? kandidati.slice().sort((a, b) => Math.abs(a.y - rok) - Math.abs(b.y - rok))[0]
            : kandidati[0]);
        // bez roku v datech radši nehádat naslepo — jen když je shoda jistá (jediný kandidát)
        if (presny || (nejblizsi && !rok && kandidati.length === 1)) {
          vysledek = nejblizsi.id;
        } else if (nejblizsi && rok && Math.abs(nejblizsi.y - rok) <= 1) {
          vysledek = nejblizsi.id; // tolerance 1 rok (premiéra vs. certifikace apod.)
        }
      }
    } catch {
      /* selhání = zůstane null, box spadne na fallback vyhledávání */
    }
  }
  IMDB_CACHE.set(id, vysledek);
  return vysledek;
}

// Doplní přímé odkazy do IMDb a Stremio boxíků v otevřeném dashboardu (guard jako
// u wiki boxu). Obojí staví na stejném dohledaném ID, proto jeden společný lookup —
// Stremio adresuje obsah přes IMDb ID stejně jako IMDb samo (Cinemeta addon).
async function naplnImdbAStremio(film) {
  const overlay = document.getElementById("dashboard-film");
  const id = domaId(film);
  const tt = await imdbId(film);
  if (!tt || overlay.hidden || decodeURIComponent(overlay.dataset.filmId || "") !== id) return;
  const imdbBox = document.getElementById("dash-imdb-box");
  if (imdbBox) imdbBox.href = `https://www.imdb.com/title/${tt}/`;
  const stremioBox = document.getElementById("dash-stremio-box");
  // detail deep link (bez autoPlay) — otevře stránku filmu ve Stremiu, uživatel
  // si vybere zdroj sám; autoPlay=true by u nenainstalovaných/nenaladěných
  // addonů mohlo skončit prázdnou obrazovkou místo přehledu zdrojů
  if (stremioBox) stremioBox.href = `stremio:///detail/movie/${tt}/${tt}`;
}

function vykresliDashboard(film) {
  const id = domaId(film);
  const zanry = (film.zanr || "")
    .split(",").map((z) => z.trim()).filter(Boolean)
    .map((z) => `<span class="dash-zanr">${escapeHtml(z)}</span>`).join("");

  const prumer = film.hodnoceni?.vazenePrumer;
  const f101 = film.hodnoceni?.films101;

  // hlavní text = duvodSkore (viz kontrakt filmotéky), popis ukázat jen když se liší
  const hlavniText = film.duvodSkore ?? film.popis;
  const vedlejsiText = film.popis && film.popis !== hlavniText ? film.popis : null;

  const pribuzne = dashPribuzne(film);
  const tiles = pribuzne.filmy
    .map((p) => `
      <button type="button" class="dash-tile" data-film-id="${encodeURIComponent(domaId(p))}">
        <span class="dash-tile-nazev">${escapeHtml(p.nazevCz)}</span>
        <span class="dash-tile-meta">${escapeHtml(p.rok || "—")} · <strong>${escapeHtml(hodnotaNebo(p.estetickeSkore))}</strong></span>
      </button>`)
    .join("");
  const hledatRezisera = pribuzne.rezie
    ? `<button type="button" class="dash-hledat-rezisera" data-rezie="${escapeHtml(film.rezie)}">vyhledat ve filmotéce →</button>`
    : "";

  const boxy = dashBoxy(film)
    .map(([sekce, polozky]) => `
      <div class="dash-sekce">
        <h3>${escapeHtml(sekce)}</h3>
        <div class="dash-linky">
          ${polozky.map(([emoji, popisek, url, cely, znacka]) => `
            <a class="dash-box${cely ? " dash-box-cely" : ""}"${znacka ? ` id="${znacka}"` : ""}
               href="${escapeHtml(url)}" target="_blank" rel="noopener">
              <span class="dash-box-emoji" aria-hidden="true">${emoji}</span>${escapeHtml(popisek)}
            </a>`).join("")}
        </div>
      </div>`)
    .join("");

  return `
    <div class="dash-obsah">
      <button type="button" class="dash-zavrit" aria-label="Zavřít">×</button>

      <header class="dash-hlavicka">
        <div class="dash-titulky">
          <h2>${escapeHtml(film.nazevCz)}</h2>
          ${film.nazevOrig && film.nazevOrig !== film.nazevCz ? `<p class="dash-orig">${escapeHtml(film.nazevOrig)}</p>` : ""}
          <p class="dash-meta">${escapeHtml(hodnotaNebo(film.rezie))} · ${escapeHtml(hodnotaNebo(film.rok))}</p>
          <div class="dash-zanry">${zanry}</div>
        </div>
        <div class="dash-skore-blok">
          <div class="dash-skore-hlavni">
            <div class="skore dash-skore skore-klik${VIDENO.has(id) ? " videno" : ""}" data-id="${encodeURIComponent(id)}"
                 title="Estetické skóre · kliknutím označíš jako viděno">${escapeHtml(hodnotaNebo(film.estetickeSkore))}</div>
            <span class="dash-skore-popisek">estetické skóre</span>
          </div>
          <div class="dash-skore-vedlejsi">
            ${prumer !== null && prumer !== undefined ? `<span>${IKONA_PRUMER}${escapeHtml(Math.round(prumer))} vážený průměr</span>` : ""}
            ${f101 !== null && f101 !== undefined ? `<span><strong>f101</strong> ${escapeHtml(f101)}/5</span>` : ""}
          </div>
          ${vykresliSrdce(id, OBLIBENE.has(id))}
        </div>
      </header>

      <div class="dash-telo">
        <div class="dash-hlavni">
          ${vykresliDashTrailer(film)}
          <p class="dash-popis">${escapeHtml(hodnotaNebo(hlavniText))}</p>
          ${vedlejsiText ? `<p class="dash-duvod">${escapeHtml(vedlejsiText)}</p>` : ""}
          <div class="dash-sekce dash-wiki">
            <h3>Wikipedia</h3>
            <div class="dash-wiki-obsah">
              <p class="dash-wiki-nacitani">Načítám z Wikipedie…</p>
            </div>
          </div>
        </div>
        <aside class="dash-boxy">
          ${boxy}
          <div class="dash-sekce dash-pas">
            <h3>${escapeHtml(pribuzne.titulek)} ${hledatRezisera}</h3>
            ${tiles ? `<div class="dash-tiles">${tiles}</div>` : `<p class="dash-pas-prazdny">V žebříčku není nic dalšího podobného — tenhle je prostě unikát.</p>`}
          </div>
        </aside>
      </div>
    </div>`;
}

// Facade traileru -> skutečný YT přehrávač (sdílí karta v seznamu i dashboard)
function prehrajFacade(facade) {
  const id = facade.dataset.ytId;
  facade.parentElement.innerHTML =
    `<iframe class="trailer-embed" src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0" ` +
    `title="Trailer" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" ` +
    `allowfullscreen></iframe>`;
}

// Přepne oblíbenost + synchronizuje VŠECHNA srdíčka téhož filmu na stránce
// (karta v seznamu a dashboard můžou být vidět zároveň)
function prepniSrdce(srdce) {
  const id = decodeURIComponent(srdce.dataset.id);
  const noveOblibene = !OBLIBENE.has(id);
  if (noveOblibene) OBLIBENE.add(id);
  else OBLIBENE.delete(id);
  ulozOblibene();
  document.querySelectorAll(".srdce").forEach((s) => {
    if (decodeURIComponent(s.dataset.id || "") !== id) return;
    s.classList.toggle("je-oblibene", noveOblibene);
    s.setAttribute("aria-pressed", noveOblibene);
  });
  // když je zapnutý filtr oblíbených, odznačená karta musí zmizet → překreslit
  if (JEN_OBLIBENE) prekresli();
}

function otevriDashboardFilmu(film) {
  const overlay = document.getElementById("dashboard-film");
  overlay.dataset.filmId = encodeURIComponent(domaId(film)); // pro guard async doplnění
  overlay.innerHTML = vykresliDashboard(film);
  overlay.hidden = false;
  overlay.scrollTop = 0; // při brouzdání tile → tile začínat vždy nahoře
  document.body.classList.add("dashboard-otevreny"); // zamkne scroll pozadí
  naplnWikiBox(film); // wiki box se dolije async, skeleton už stojí
  naplnImdbAStremio(film); // IMDb + Stremio odkazy se přepnou na přímé, jakmile se dohledá ID
}

function zavriDashboard() {
  const overlay = document.getElementById("dashboard-film");
  overlay.hidden = true;
  overlay.innerHTML = ""; // uklidit případný hrající YT iframe
  document.body.classList.remove("dashboard-otevreny");
}

// Render filmotéky: fulltext filtr + srdíčka/špička + dávkování po DOMA_DAVKA kartách.
// "Zobrazit další" je poslední prvek gridu a jen zvedne DOMA_LIMIT.
function prekresliDoma() {
  const kontejner = document.getElementById("seznam-akci");
  const prazdnyStav = document.getElementById("prazdny-stav");
  const dotaz = bezDiakritiky(HLEDANI_DOMA.trim());

  const filmy = (FILMY_DOMA || []).filter((f) => {
    if (dotaz && !f.hledaci.includes(dotaz)) return false;
    if (JEN_OBLIBENE && !OBLIBENE.has(domaId(f.data))) return false;
    if (JEN_TOP && (f.data.estetickeSkore ?? -1) < TOP_PRAH) return false;
    return true;
  });

  if (filmy.length === 0) {
    kontejner.innerHTML = "";
    prazdnyStav.hidden = false;
    return;
  }

  prazdnyStav.hidden = true;
  const videt = filmy.slice(0, DOMA_LIMIT);
  let html = videt.map((f) => vykresliKartuFilmuDoma(f.data, domaId(f.data))).join("");
  if (filmy.length > DOMA_LIMIT) {
    // neviditelná zarážka pro infinite scroll — když se přiblíží do viewportu,
    // IntersectionObserver (viz init) zvedne DOMA_LIMIT a překreslí
    html += '<div id="doma-zarazka" aria-hidden="true"></div>';
  }
  kontejner.innerHTML = html;
  const zarazka = document.getElementById("doma-zarazka");
  if (DOMA_OBSERVER) {
    DOMA_OBSERVER.disconnect(); // stará zarážka je po innerHTML pryč, nedržet ji
    if (zarazka) DOMA_OBSERVER.observe(zarazka);
  }
}

// ---- filtrování a řazení ----

// překrývá se rozmezí výstavy [datumOd, datumDo] s filtrem? (obě meze filtru volitelné)
// Výstava nemá projekce, ale interval trvání — "spadá do filtru" = intervaly se protnou.
function maVystavaVRozmezi(data, datumOd, datumDo) {
  const od = parsujDatum(data.datumOd);
  const do_ = parsujDatum(data.datumDo) || od;
  if (!od) return true; // bez data radši nechat projít, ne skrýt
  if (datumDo && od > datumDo) return false; // výstava začíná až po konci filtru
  if (datumOd && (do_ || od) < datumOd) return false; // výstava skončila před filtrem
  return true;
}

// rozhodne podle typu akce, jestli položka spadá do datumového filtru
function maAkceVRozmezi(polozka, datumOd, datumDo) {
  // výstava má trvání (interval) → překryv; termínový typ (koncert/divadlo) s víc termíny
  // se filtruje jako filmové projekce (aspoň jeden termín v rozsahu), jednorázový přes interval.
  if (polozka.typAkce === "vystavy") {
    return maVystavaVRozmezi(polozka.data, datumOd, datumDo);
  }
  if (jeTerminovy(polozka.typAkce)) {
    const terminy = polozka.data.terminy;
    if (Array.isArray(terminy) && terminy.length) {
      return maProjekciVRozmezi(terminy, datumOd, datumDo);
    }
    return maVystavaVRozmezi(polozka.data, datumOd, datumDo);
  }
  return maProjekciVRozmezi(polozka.data.projekce, datumOd, datumDo);
}

// má akce aspoň jednu projekci v zadaném rozmezí (obě meze volitelné)?
function maProjekciVRozmezi(projekce, datumOd, datumDo) {
  if (!projekce || projekce.length === 0) return true; // bez dat radši nechat projít, ne skrýt
  return projekce.some((p) => {
    const d = parsujDatum(p.datum);
    if (!d) return true;
    if (datumOd && d < datumOd) return false;
    if (datumDo && d > datumDo) return false;
    return true;
  });
}

// aktuálně nastavený datumový filtr (obě meze volitelné). Sdílí ho filtrování
// i vykreslení, ať se karta a její projekce řídí stejným rozsahem.
function ziskejAktivniRozsah() {
  const datumOdRetezec = document.getElementById("filtr-od").value; // formát YYYY-MM-DD z <input type=date>
  const datumDoRetezec = document.getElementById("filtr-do").value;
  // POZOR: new Date("2026-07-05") se parsuje jako UTC půlnoc, kdežto datumy projekcí
  // parsujeme lokálně (parsujDatum). To by rozhodilo hranice o offset pásma. Proto
  // vstup z <input type=date> parsujeme taky ručně jako lokální čas.
  return {
    datumOd: parsujIsoDatum(datumOdRetezec, false),
    datumDo: parsujIsoDatum(datumDoRetezec, true), // horní mez = konec dne, ať "do" zahrnuje celý den
  };
}

function ziskejFiltrovaneARazene() {
  const typFiltr = document.getElementById("filtr-typ").value;
  const razeniPodle = document.getElementById("razeni").value;
  const { datumOd, datumDo } = ziskejAktivniRozsah();

  let vysledek = VSECHNY_AKCE.filter((polozka) => {
    if (typFiltr !== "vse" && polozka.typAkce !== typFiltr) return false;
    if (JEN_OBLIBENE && !OBLIBENE.has(akceId(polozka))) return false;
    if (JEN_TOP && (polozka.data.estetickeSkore ?? -1) < TOP_PRAH) return false;
    if ((datumOd || datumDo) && !maAkceVRozmezi(polozka, datumOd, datumDo)) return false;
    return true;
  });

  vysledek.sort((a, b) => {
    if (razeniPodle === "estetickeSkore") {
      return (b.data.estetickeSkore ?? -1) - (a.data.estetickeSkore ?? -1);
    }
    if (razeniPodle === "vazenePrumer") {
      return (b.data.hodnoceni?.vazenePrumer ?? -1) - (a.data.hodnoceni?.vazenePrumer ?? -1);
    }
    if (razeniPodle === "datum") {
      // výstavy i termínové typy řadí podle začátku (datumOd), filmy podle nejbližší projekce
      const podleData = (x) =>
        x.typAkce === "vystavy" || jeTerminovy(x.typAkce)
          ? parsujDatum(x.data.datumOd)
          : nejblizsiDatumProjekce(x.data.projekce);
      const dA = podleData(a);
      const dB = podleData(b);
      if (!dA && !dB) return 0;
      if (!dA) return 1;
      if (!dB) return -1;
      return dA - dB;
    }
    return 0;
  });

  return vysledek;
}

// ---- vykreslení ----

// nechá jen projekce spadající do rozsahu; když rozsah není nastavený, vrátí vše
function projekceVRozmezi(projekce, rozsah) {
  if (!projekce) return [];
  const { datumOd, datumDo } = rozsah || {};
  if (!datumOd && !datumDo) return projekce;
  return projekce.filter((p) => {
    const d = parsujDatum(p.datum);
    if (!d) return true; // bez parsovatelného data radši nechat, ať se něco ukáže
    if (datumOd && d < datumOd) return false;
    if (datumDo && d > datumDo) return false;
    return true;
  });
}

// jeden řádek projekce (datum · čas + kino s odkazem). Sdílí ho karta i modal.
// vsechny (nepovinné): když je předáno, za čas se přidá odkaz "(N)" na modal se všemi projekcemi.
function vykresliRadekProjekce(p, vsechny) {
  const misto = escapeHtml(hodnotaNebo(p.misto));
  const datum = escapeHtml(hodnotaNebo(p.datum));
  const cas = escapeHtml(hodnotaNebo(p.cas));
  const odkazOtevreny = p.odkaz
    ? `<a href="${escapeHtml(p.odkaz)}" target="_blank" rel="noopener">${misto}</a>`
    : misto;
  // odkaz s počtem DALŠÍCH projekcí (celkem − tahle jedna), otevře modal
  const vic =
    vsechny && vsechny.length > 1
      ? ` <a class="vic-projekci" href="#" data-projekce="${encodeURIComponent(JSON.stringify(vsechny))}">(${vsechny.length - 1})</a>`
      : "";
  return `<li><span class="proj-cas">${datum} · ${cas}${vic}</span> <span class="proj-misto">${odkazOtevreny}</span></li>`;
}

// V kartě ukážeme jen první projekci. Když je jich víc, za čas přijde odkaz "(N)" na modal.
function vykresliProjekce(projekce, rozsah) {
  const viditelne = projekceVRozmezi(projekce, rozsah);
  if (!viditelne || viditelne.length === 0) {
    return "<div class='projekce-blok'><p class='poznamka-hodnoceni'>Zatím žádné projekce v nabídce.</p></div>";
  }
  const radek = vykresliRadekProjekce(viditelne[0], viditelne);
  return `<div class="projekce-blok"><ul class="projekce-seznam">${radek}</ul></div>`;
}

// vytáhne 11znakové ID videa z různých podob YouTube URL
// (youtu.be/ID, watch?v=ID, embed/ID, shorts/ID, v/ID). Když to není YT, vrátí null.
function youtubeId(url) {
  if (!url) return null;
  const m = String(url).match(
    /(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|v\/))([\w-]{11})/
  );
  return m ? m[1] : null;
}

// "facade" trailer: v kartě je jen lehký náhled (thumbnail + play). Skutečný přehrávač
// se natáhne až po kliknutí (viz delegovaný listener v init) — ať appka nebrzdí desítkami
// iframů najednou. Když trailer chybí, vrátí "". Ne-YT odkaz spadne na prostý proklik.
function vykresliTrailer(trailerUrl) {
  if (!trailerUrl) return "";
  // ochrana proti AI datům: string "null" (i s poznámkou "null (nenalezen…)") = žádný trailer
  if (/^null\b/.test(String(trailerUrl).trim())) return "";
  const id = youtubeId(trailerUrl);
  if (!id) {
    return `<a class="trailer-odkaz" href="${escapeHtml(trailerUrl)}" target="_blank" rel="noopener">▶ Přehrát trailer</a>`;
  }
  // thumbnail jako <img loading="lazy"> (ne background-image) — stáhne se až když se
  // karta blíží do viewportu. Zásadní pro filmotéku (tisíce karet), potěší i akce.
  const thumb = `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;
  return `
    <div class="trailer">
      <button type="button" class="trailer-facade" data-yt-id="${id}" aria-label="Přehrát trailer">
        <img class="trailer-thumb" src="${thumb}" alt="" loading="lazy">
        <span class="trailer-play" aria-hidden="true"></span>
      </button>
    </div>`;
}

// malá ikonka "průměru" (mini sloupcový graf) před váženým průměrem
const IKONA_PRUMER =
  '<svg class="ikona-prumer" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">' +
  '<rect x="3" y="11" width="4" height="10" rx="1"/>' +
  '<rect x="10" y="5" width="4" height="16" rx="1"/>' +
  '<rect x="17" y="14" width="4" height="7" rx="1"/></svg>';

// Řádek hodnocení (žlutě, jako kolečko skóre): vpředu vážený průměr s ikonkou, za ním
// rozpad zdrojů jen s první hodnotou (bez /10 a %). poznamkaHodnoceni schválně nezobrazujeme.
function vykresliHodnoceniRadek(hodnoceni) {
  const prumer =
    hodnoceni && hodnoceni.vazenePrumer !== null && hodnoceni.vazenePrumer !== undefined
      ? `<span class="prumer">${IKONA_PRUMER}${escapeHtml(hodnoceni.vazenePrumer)}</span>`
      : "";

  const zdroje = hodnoceni
    ? [
        ["RT", hodnoceni.rottenTomatoesAudience],
        ["MC", hodnoceni.metacriticUser],
        ["IMDb", hodnoceni.imdb],
        ["ČSFD", hodnoceni.csfd],
      ]
        .filter(([, hodnota]) => hodnota !== null && hodnota !== undefined)
        .map(([nazev, hodnota]) => `<span class="zdroj"><strong>${nazev}</strong> ${escapeHtml(hodnota)}</span>`)
        .join("")
    : "";

  // když film nemá žádné hodnocení, ať řádek nezeje prázdnotou — žlutý nápis "Bez hodnocení"
  const obsah = prumer + zdroje || '<span class="bez-hodnoceni">Bez hodnocení</span>';
  return `<div class="hodnoceni-radek">${obsah}</div>`;
}

function vykresliKartuFilmu(film, rozsah, id) {
  const skore = hodnotaNebo(film.estetickeSkore, "—");

  return `
    <article class="karta">
      <div class="karta-vrch">
        <div class="karta-vrch-text">
          <div class="karta-titulky">
            <h2>${escapeHtml(film.nazevCz)}</h2>
            ${film.nazevOrig && film.nazevOrig !== film.nazevCz ? `<p class="nazev-orig">${escapeHtml(film.nazevOrig)}</p>` : ""}
          </div>

          <div class="meta-blok">
            <div class="meta-radek">${escapeHtml(hodnotaNebo(film.rezie))}</div>
            <div class="meta-radek">${escapeHtml(hodnotaNebo(film.zanr))}</div>
            ${vykresliHodnoceniRadek(film.hodnoceni)}
          </div>
        </div>

        <div class="karta-vpravo">
          <div class="skore" title="Estetické skóre">${escapeHtml(skore)}</div>
          ${vykresliSrdce(id, OBLIBENE.has(id))}
        </div>
      </div>

      ${film.specialniProjekce ? `<span class="stitek-special">${escapeHtml(hodnotaNebo(film.specialniPopis, "Speciální projekce"))}</span>` : ""}

      <p class="popis">${escapeHtml(hodnotaNebo(film.popis))}</p>

      ${film.duvodSkore ? `<p class="duvod-skore">${escapeHtml(film.duvodSkore)}</p>` : ""}

      ${film.vlastniRecenze ? `<p class="recenze">${escapeHtml(film.vlastniRecenze)}</p>` : ""}

      ${vykresliProjekce(film.projekce, rozsah)}

      ${vykresliTrailer(film.trailerUrl)}
    </article>
  `;
}

// datum rozmezí "01.08.2026 – 30.08.2026"; když od==do, jen jeden datum
function vykresliRozmeziDatumu(datumOd, datumDo) {
  const od = hodnotaNebo(datumOd, "");
  const do_ = hodnotaNebo(datumDo, "");
  if (od && do_ && od !== do_) return `${escapeHtml(od)} – ${escapeHtml(do_)}`;
  return escapeHtml(od || do_ || "—");
}

// thumbnail v 16:9 rámu (na místě filmového traileru), klikací na detail výstavy
function vykresliThumbnail(thumbnail, url, nazev) {
  if (!thumbnail) return "";
  const obrazek = `<img class="vystava-obrazek" src="${escapeHtml(thumbnail)}" alt="${escapeHtml(nazev)}" loading="lazy">`;
  if (!url) return `<div class="vystava-thumb">${obrazek}</div>`;
  return `<a class="vystava-thumb" href="${escapeHtml(url)}" target="_blank" rel="noopener" aria-label="Otevřít detail výstavy">${obrazek}</a>`;
}

function vykresliKartuVystavy(v, id) {
  const skore = hodnotaNebo(v.estetickeSkore, "—");
  // dolní blok: datum rozmezí + galerie (odkaz), přilepený dolů jako u filmových projekcí
  const galerie = v.url
    ? `<a href="${escapeHtml(v.url)}" target="_blank" rel="noopener">${escapeHtml(hodnotaNebo(v.misto))}</a>`
    : escapeHtml(hodnotaNebo(v.misto));

  return `
    <article class="karta karta-vystava">
      <div class="karta-vrch">
        <div class="karta-vrch-text">
          <div class="karta-titulky">
            <h2>${escapeHtml(v.nazevCz)}</h2>
            <p class="vystava-zanr">${escapeHtml(hodnotaNebo(v.zanr, ""))}</p>
          </div>
        </div>

        <div class="karta-vpravo">
          <div class="skore" title="Estetické skóre">${escapeHtml(skore)}</div>
          ${vykresliSrdce(id, OBLIBENE.has(id))}
        </div>
      </div>

      <p class="popis popis-vystava">${escapeHtml(hodnotaNebo(v.popis))}</p>

      ${v.duvodSkore ? `<p class="duvod-skore">${escapeHtml(v.duvodSkore)}</p>` : ""}

      <div class="projekce-blok">
        <ul class="projekce-seznam">
          <li><span class="proj-cas">${vykresliRozmeziDatumu(v.datumOd, v.datumDo)}</span> <span class="proj-misto">${galerie}</span></li>
        </ul>
      </div>

      ${vykresliThumbnail(v.thumbnail, v.url, v.nazevCz)}
    </article>
  `;
}

// Termíny koncertu ve tvaru {datum, cas, misto, odkaz} — ať se dají recyklovat filmové
// řádky projekcí i popup „(N)". Buď víc termínů z pole `terminy` (RAW extra u vícetermínových
// akcí), nebo jeden odvozený z datumOd/cas. Místo a odkaz jsou u koncertu společné pro všechny.
function normalizniTerminyKoncertu(k) {
  const spolecne = { misto: k.misto, odkaz: k.url };
  if (Array.isArray(k.terminy) && k.terminy.length) {
    return k.terminy.map((t) => ({ datum: t.datum, cas: t.cas, ...spolecne }));
  }
  return [{ datum: k.datumOd, cas: k.cas, ...spolecne }];
}

// CSS třída karty podle termínového typu — každý typ má vlastní barvu akcentu (klasika modrá,
// jazz&blues fialová, divadlo červená). Nový termínový typ = řádek sem + barva v CSS.
const TERMINOVA_CSS_TRIDA = {
  koncerty_klasika: "karta-koncert",
  koncerty_jazzblues: "karta-jazzblues",
  divadlo: "karta-divadlo",
  party: "karta-party",
  odborne_psychoterapie: "karta-psychoterapie",
};

// Karta termínového typu (koncert/divadlo) = klon výstavní (stejný skeleton), akcent podle typu
// (viz .karta-koncert / .karta-jazzblues / .karta-divadlo v CSS). Dolní blok = datum · čas +
// místo (odkaz) + volitelně cena. Když má akce víc termínů, přidá se za čas klikací „(N)" na
// modal se všemi termíny — přesně jako projekce u filmů.
function vykresliKartuTerminu(k, id, rozsah, typAkce) {
  const cssTrida = TERMINOVA_CSS_TRIDA[typAkce] || "karta-koncert";
  const skore = hodnotaNebo(k.estetickeSkore, "—");
  const klub = k.url
    ? `<a href="${escapeHtml(k.url)}" target="_blank" rel="noopener">${escapeHtml(hodnotaNebo(k.misto))}</a>`
    : escapeHtml(hodnotaNebo(k.misto));
  // cena jako decentní přívěsek na konec řádku, když je vyplněná
  const cena = k.cena ? ` <span class="koncert-cena">${escapeHtml(k.cena)}</span>` : "";

  // termíny profiltrované aktivním datumovým rozsahem (stejně jako projekce u filmu)
  const terminy = normalizniTerminyKoncertu(k);
  const viditelne = projekceVRozmezi(terminy, rozsah);
  const prvni = viditelne[0];

  let radek;
  if (prvni) {
    const datum = escapeHtml(hodnotaNebo(prvni.datum));
    const cas = prvni.cas ? ` · ${escapeHtml(prvni.cas)}` : "";
    // „(N)" na modal jen když je v rozsahu víc termínů (N = počet DALŠÍCH, jako u filmů)
    const vic =
      viditelne.length > 1
        ? ` <a class="vic-projekci" href="#" data-projekce="${encodeURIComponent(JSON.stringify(viditelne))}">(${viditelne.length - 1})</a>`
        : "";
    radek = `<li><span class="proj-cas">${datum}${cas}${vic}</span> <span class="proj-misto">${klub}${cena}</span></li>`;
  } else {
    // žádný termín v rozsahu — spadneme na rozmezí trvání, ať řádek nezeje prázdnotou
    radek = `<li><span class="proj-cas">${vykresliRozmeziDatumu(k.datumOd, k.datumDo)}</span> <span class="proj-misto">${klub}${cena}</span></li>`;
  }

  return `
    <article class="karta ${cssTrida}">
      <div class="karta-vrch">
        <div class="karta-vrch-text">
          <div class="karta-titulky">
            <h2>${escapeHtml(k.nazevCz)}</h2>
            ${k.autor ? `<p class="vystava-zanr">${escapeHtml(k.autor)}</p>` : `<p class="vystava-zanr">${escapeHtml(hodnotaNebo(k.zanr, ""))}</p>`}
          </div>
        </div>

        <div class="karta-vpravo">
          <div class="skore" title="Estetické skóre">${escapeHtml(skore)}</div>
          ${vykresliSrdce(id, OBLIBENE.has(id))}
        </div>
      </div>

      <p class="popis popis-vystava">${escapeHtml(hodnotaNebo(k.popis))}</p>

      ${k.duvodSkore ? `<p class="duvod-skore">${escapeHtml(k.duvodSkore)}</p>` : ""}

      <div class="projekce-blok">
        <ul class="projekce-seznam">${radek}</ul>
      </div>

      ${vykresliThumbnail(k.thumbnail, k.url, k.nazevCz)}
    </article>
  `;
}

function vykresliKartu(polozka, rozsah) {
  const id = akceId(polozka); // generické ID pro srdíčko/oblíbené, funguje napříč typy
  switch (polozka.typAkce) {
    case "filmy":
      return vykresliKartuFilmu(polozka.data, rozsah, id);
    case "vystavy":
      return vykresliKartuVystavy(polozka.data, id);
    case "koncerty_klasika":
    case "koncerty_jazzblues":
    case "divadlo":
    case "party":
    case "odborne_psychoterapie":
      return vykresliKartuTerminu(polozka.data, id, rozsah, polozka.typAkce);
    default:
      return "";
  }
}

function prekresli() {
  // režim "filmy na doma" má vlastní render (jiná data, fulltext, dávkování)
  if (REZIM_DOMA) {
    prekresliDoma();
    return;
  }

  const kontejner = document.getElementById("seznam-akci");
  const prazdnyStav = document.getElementById("prazdny-stav");
  const akce = ziskejFiltrovaneARazene();
  const rozsah = ziskejAktivniRozsah(); // karty zobrazí jen projekce z tohoto rozsahu

  if (akce.length === 0) {
    kontejner.innerHTML = "";
    prazdnyStav.hidden = false;
    return;
  }

  prazdnyStav.hidden = true;
  kontejner.innerHTML = akce.map((polozka) => vykresliKartu(polozka, rozsah)).join("");
}

// Hezké popisky do filtru pro slugy, kde by prosté "první písmeno velké" nestačilo
// (typicky víceslovné/podtypové slugy). Co tu není, spadne na fallback (capitalize).
const POPISKY_TYPU = {
  koncerty_klasika: "Klasika",
  koncerty_jazzblues: "Jazz&Blues",
  divadlo: "Divadlo",
  party: "Party",
  odborne_psychoterapie: "Psychoterapie",
};

// naplní select "Typ akce" podle toho, jaké typy skutečně přišly v datech
function naplnFiltrTypu() {
  const select = document.getElementById("filtr-typ");
  const typy = [...new Set(VSECHNY_AKCE.map((a) => a.typAkce))];
  for (const typ of typy) {
    const option = document.createElement("option");
    option.value = typ;
    option.textContent = POPISKY_TYPU[typ] || typ.charAt(0).toUpperCase() + typ.slice(1);
    select.appendChild(option);
  }
}

// ---- rychlé volby data (dnes / týden / měsíc / vše) ----

// Date -> "YYYY-MM-DD" pro naplnění <input type="date">
function naFormatVstupu(datum) {
  const rok = datum.getFullYear();
  const mesic = String(datum.getMonth() + 1).padStart(2, "0");
  const den = String(datum.getDate()).padStart(2, "0");
  return `${rok}-${mesic}-${den}`;
}

function nastavRychlyRozsah(rozsah) {
  const vstupOd = document.getElementById("filtr-od");
  const vstupDo = document.getElementById("filtr-do");
  const dnes = new Date();

  // pomocník: Date posunutý o dané dny/měsíce od dneška (nemutuje dnes)
  const posun = ({ dny = 0, mesice = 0 }) => {
    const d = new Date(dnes);
    d.setDate(d.getDate() + dny);
    d.setMonth(d.getMonth() + mesice);
    return d;
  };

  if (rozsah === "vse") {
    vstupOd.value = "";
    vstupDo.value = "";
  } else if (rozsah === "dnes") {
    vstupOd.value = naFormatVstupu(dnes);
    vstupDo.value = naFormatVstupu(dnes);
  } else if (rozsah === "zitra") {
    const zitra = posun({ dny: 1 });
    vstupOd.value = naFormatVstupu(zitra);
    vstupDo.value = naFormatVstupu(zitra);
  } else if (rozsah === "tyden") {
    vstupOd.value = naFormatVstupu(dnes);
    vstupDo.value = naFormatVstupu(posun({ dny: 7 }));
  } else if (rozsah === "pristi-tyden") {
    // navazující okno: den po „tomto týdnu" až o týden dál
    vstupOd.value = naFormatVstupu(posun({ dny: 8 }));
    vstupDo.value = naFormatVstupu(posun({ dny: 14 }));
  } else if (rozsah === "mesic") {
    vstupOd.value = naFormatVstupu(dnes);
    vstupDo.value = naFormatVstupu(posun({ mesice: 1 }));
  } else if (rozsah === "pristi-mesic") {
    // navazující okno: den po „tomto měsíci" až o měsíc dál
    vstupOd.value = naFormatVstupu(posun({ dny: 1, mesice: 1 }));
    vstupDo.value = naFormatVstupu(posun({ mesice: 2 }));
  }

  prekresli();
}

// ---- inicializace ----

async function init() {
  VSECHNY_AKCE = await nactiVsechnaData();
  naplnFiltrTypu();
  prekresli();

  // Hamburger na mobilu (schovaný na desktopu přes CSS): sbaluje/rozbaluje blok
  // typ/řazení/datum/rychlá volba. Hledací pole filmotéky je schválně mimo tenhle
  // obal (viz HTML) — zůstává vidět i po sbalení.
  const menuTlacitko = document.getElementById("menu-prepinac");
  const ovladaciObsah = document.getElementById("ovladaci-obsah");
  menuTlacitko.addEventListener("click", () => {
    const otevreno = ovladaciObsah.classList.toggle("otevreno");
    menuTlacitko.classList.toggle("aktivni", otevreno);
    menuTlacitko.setAttribute("aria-expanded", otevreno);
    menuTlacitko.querySelector(".menu-text").textContent = otevreno ? "Zavřít filtry" : "Filtry a řazení";
  });

  // Export/import zálohy: primárně tiché čtení/zápis do vybrané složky (viz výše),
  // se spadnutím na klasické stažení/nahrání, když API chybí NEBO cokoliv selže
  // (zrušený výběr složky bereme jako "AbortError" a nic nehlásíme — to je normální
  // uživatelovo rozmyšlení, ne chyba).
  document.getElementById("export-zaloha").addEventListener("click", async () => {
    if (!PODPORA_FS_API) return exportujZalohu();
    try {
      await exportujZalohuAutomaticky();
    } catch (chyba) {
      if (chyba.name !== "AbortError") {
        console.warn("Automatický zápis zálohy selhal, padám na stažení:", chyba);
        exportujZalohu();
      }
    }
  });

  const importSoubor = document.getElementById("import-soubor");
  document.getElementById("import-zaloha").addEventListener("click", async () => {
    if (!PODPORA_FS_API) return importSoubor.click();
    try {
      await naimportujZalohuAutomaticky();
    } catch (chyba) {
      if (chyba.name !== "AbortError") {
        console.warn("Automatické čtení zálohy selhalo, padám na výběr souboru:", chyba);
        importSoubor.click();
      }
    }
  });
  importSoubor.addEventListener("change", (e) => {
    const soubor = e.target.files[0];
    if (soubor) naimportujZalohu(soubor);
    e.target.value = ""; // reset, ať jde nahrát i ten samý soubor znovu
  });

  document.getElementById("filtr-typ").addEventListener("change", prekresli);
  document.getElementById("razeni").addEventListener("change", prekresli);
  document.getElementById("filtr-od").addEventListener("change", prekresli);
  document.getElementById("filtr-do").addEventListener("change", prekresli);

  document.querySelectorAll(".rychle-volby button[data-rozsah]").forEach((tlacitko) => {
    tlacitko.addEventListener("click", () => nastavRychlyRozsah(tlacitko.dataset.rozsah));
  });

  // Delegovaný klik na kontejner karet (karty se překreslují přes innerHTML, tak posloucháme
  // na rodiči): buď spustit trailer, nebo otevřít modal se všemi projekcemi.
  // infinite scroll filmotéky: když se zarážka na konci seznamu přiblíží k viewportu
  // (s předstihem 1200px, ať to uživatel nepostřehne), přidá se další dávka karet
  DOMA_OBSERVER = new IntersectionObserver(
    (zaznamy) => {
      if (zaznamy.some((z) => z.isIntersecting)) {
        DOMA_LIMIT += DOMA_DAVKA;
        prekresli();
      }
    },
    { rootMargin: "1200px 0px" }
  );

  document.getElementById("seznam-akci").addEventListener("click", (e) => {
    const facade = e.target.closest(".trailer-facade");
    if (facade) {
      prehrajFacade(facade);
      return;
    }
    const vic = e.target.closest(".vic-projekci");
    if (vic) {
      e.preventDefault(); // je to <a href="#">, ať to neskáče na začátek stránky
      const nazev = vic.closest(".karta")?.querySelector("h2")?.textContent || "";
      const projekce = JSON.parse(decodeURIComponent(vic.dataset.projekce));
      otevriModalProjekci(nazev, projekce);
      return;
    }
    const srdce = e.target.closest(".srdce");
    if (srdce) {
      prepniSrdce(srdce);
      return;
    }
    // kolečko skóre ve filmotéce = přepínač "viděno" (nesmí otevřít dashboard)
    const kolecko = e.target.closest(".skore-klik");
    if (kolecko) {
      prepniVideno(decodeURIComponent(kolecko.dataset.id));
      return;
    }
    // klik kamkoli jinam na kartu filmotéky (mimo odkazy) otevře dashboard filmu
    const kartaDoma = e.target.closest(".karta-doma");
    if (kartaDoma && !e.target.closest("a")) {
      const film = DOMA_MAPA.get(decodeURIComponent(kartaDoma.dataset.filmId || ""));
      if (film) otevriDashboardFilmu(film);
    }
  });

  // horní přepínač "jen oblíbené"
  const prepinacOblibene = document.getElementById("filtr-oblibene");
  prepinacOblibene.innerHTML = IKONA_SRDCE;
  prepinacOblibene.addEventListener("click", () => {
    JEN_OBLIBENE = !JEN_OBLIBENE;
    prepinacOblibene.classList.toggle("aktivni", JEN_OBLIBENE);
    prepinacOblibene.setAttribute("aria-pressed", JEN_OBLIBENE);
    prekresli();
  });

  // horní přepínač "jen špička" (skóre 80 a výš)
  const prepinacTop = document.getElementById("filtr-top");
  prepinacTop.innerHTML = IKONA_HVEZDA;
  prepinacTop.addEventListener("click", () => {
    JEN_TOP = !JEN_TOP;
    prepinacTop.classList.toggle("aktivni", JEN_TOP);
    prepinacTop.setAttribute("aria-pressed", JEN_TOP);
    prekresli();
  });

  // přepínač režimu "filmy na doma" (filmový pás): přepne pohled, schová běžné filtry
  // (CSS přes body.rezim-doma) a při prvním zapnutí líně stáhne 3+ MB JSON
  const prepinacDoma = document.getElementById("rezim-doma");
  prepinacDoma.innerHTML = IKONA_PAS;
  prepinacDoma.addEventListener("click", async () => {
    REZIM_DOMA = !REZIM_DOMA;
    prepinacDoma.classList.toggle("aktivni", REZIM_DOMA);
    prepinacDoma.setAttribute("aria-pressed", REZIM_DOMA);
    document.body.classList.toggle("rezim-doma", REZIM_DOMA);
    if (REZIM_DOMA && !FILMY_DOMA) {
      document.getElementById("seznam-akci").innerHTML =
        '<p class="nacitani">Načítám filmotéku…</p>';
      await nactiFilmyDoma();
    }
    DOMA_LIMIT = DOMA_DAVKA; // každé zapnutí začíná od první dávky
    window.scrollTo(0, 0);
    prekresli();
  });

  // fulltext ve filmotéce — filtruje při psaní, každá změna resetuje dávkování
  const hledani = document.getElementById("hledani-doma");
  hledani.addEventListener("input", () => {
    HLEDANI_DOMA = hledani.value;
    DOMA_LIMIT = DOMA_DAVKA;
    if (REZIM_DOMA) prekresli();
  });

  nastavModal();
  nastavDashboard();
}

// vytvoří fullscreen overlay dashboardu a nadrátuje interakce (delegovaně, obsah se
// generuje při každém otevření znovu): zavření, trailer, srdíčko, brouzdání po tiles
function nastavDashboard() {
  const overlay = document.createElement("div");
  overlay.id = "dashboard-film";
  overlay.className = "dash-overlay";
  overlay.hidden = true;
  document.body.appendChild(overlay);

  overlay.addEventListener("click", (e) => {
    if (e.target.closest(".dash-zavrit")) {
      zavriDashboard();
      return;
    }
    const facade = e.target.closest(".trailer-facade");
    if (facade) {
      prehrajFacade(facade);
      return;
    }
    const srdce = e.target.closest(".srdce");
    if (srdce) {
      prepniSrdce(srdce);
      return;
    }
    // kolečko skóre v dashboardu = přepínač "viděno" (synchronizuje se s kartou)
    const kolecko = e.target.closest(".skore-klik");
    if (kolecko) {
      prepniVideno(decodeURIComponent(kolecko.dataset.id));
      return;
    }
    // tile příbuzného filmu → otevřít jeho dashboard (brouzdání filmotékou)
    const tile = e.target.closest(".dash-tile");
    if (tile) {
      const film = DOMA_MAPA.get(decodeURIComponent(tile.dataset.filmId || ""));
      if (film) otevriDashboardFilmu(film);
      return;
    }
    // „vyhledat ve filmotéce" → zavřít dashboard a nalít režiséra do fulltextu
    const hledat = e.target.closest(".dash-hledat-rezisera");
    if (hledat) {
      zavriDashboard();
      const vstup = document.getElementById("hledani-doma");
      vstup.value = hledat.dataset.rezie || "";
      vstup.dispatchEvent(new Event("input"));
      window.scrollTo(0, 0);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !overlay.hidden) zavriDashboard();
  });
}

// ---- modal se všemi projekcemi ----

// vykreslí obsah modalu a zobrazí ho. Seznam projekcí je už profiltrovaný podle aktivního filtru.
function otevriModalProjekci(nazev, projekce) {
  const modal = document.getElementById("modal-projekci");
  modal.querySelector(".modal-nazev").textContent = nazev;
  modal.querySelector(".projekce-seznam").innerHTML = projekce.map(vykresliRadekProjekce).join("");
  modal.hidden = false;
}

function zavriModal() {
  document.getElementById("modal-projekci").hidden = true;
}

// modal vytvoříme jednou v JS (ať index.html zůstane čistý) a nadrátujeme zavírání:
// křížek, klik do pozadí (overlay) i Esc.
function nastavModal() {
  const modal = document.createElement("div");
  modal.id = "modal-projekci";
  modal.className = "modal-overlay";
  modal.hidden = true;
  modal.innerHTML = `
    <div class="modal-okno" role="dialog" aria-modal="true" aria-labelledby="modal-nadpis">
      <button type="button" class="modal-zavrit" aria-label="Zavřít">×</button>
      <h3 id="modal-nadpis"><span class="modal-nazev"></span> — všechny projekce</h3>
      <ul class="projekce-seznam"></ul>
    </div>`;
  document.body.appendChild(modal);

  modal.querySelector(".modal-zavrit").addEventListener("click", zavriModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) zavriModal(); // klik do ztmaveného pozadí, ne do okna
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hidden) zavriModal();
  });
}

init();
