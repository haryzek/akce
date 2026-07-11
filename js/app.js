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
  "data/prednasky.json",
];

// Koncertní typy sdílí stejný datový tvar i kartu (klasika, jazz&blues, …) — liší se jen
// zdrojem a barvou akcentu. Ať se nemusí vyjmenovávat na deseti místech, drží se tady.
const KONCERTNI_TYPY = new Set(["koncerty_klasika", "koncerty_jazzblues"]);
const jeKoncert = (typ) => KONCERTNI_TYPY.has(typ);

let VSECHNY_AKCE = []; // sloučená, normalizovaná data ze všech zdrojů

// ---- oblíbené (localStorage, generické napříč typy akcí) ----

const OBLIBENE_KLIC = "akce-oblibene";
let JEN_OBLIBENE = false; // stav horního přepínače (jen runtime, nepersistuje se)

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

// srdíčko na kartě (dva stavy). Sdílený helper, ať ho každý typ karty jen zavolá.
const IKONA_SRDCE =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.7l-1.55-1.4C6 15 2.75 12.1 2.75 8.5 2.75 5.9 4.8 3.9 7.4 3.9c1.5 0 2.9.7 3.8 1.8.9-1.1 2.3-1.8 3.8-1.8 2.6 0 4.65 2 4.65 4.6 0 3.6-3.25 6.5-7.7 10.8L12 20.7z"/></svg>';

function vykresliSrdce(id, jeOblibene) {
  const stav = jeOblibene ? " je-oblibene" : "";
  return `<button type="button" class="srdce${stav}" data-id="${encodeURIComponent(id)}" aria-label="Oblíbené" aria-pressed="${jeOblibene}">${IKONA_SRDCE}</button>`;
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

// ---- načtení dat ----

async function nactiVsechnaData() {
  const vysledky = await Promise.all(
    ZDROJE_DAT.map(async (cesta) => {
      try {
        const odpoved = await fetch(cesta);
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
  // výstava má trvání (interval) → překryv; koncert s víc termíny se filtruje jako
  // filmové projekce (aspoň jeden termín v rozsahu), jednorázový koncert zas přes interval.
  if (polozka.typAkce === "vystavy") {
    return maVystavaVRozmezi(polozka.data, datumOd, datumDo);
  }
  if (jeKoncert(polozka.typAkce)) {
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
      // výstavy i koncerty řadí podle začátku (datumOd), filmy podle nejbližší projekce
      const podleData = (x) =>
        x.typAkce === "vystavy" || jeKoncert(x.typAkce)
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
  const id = youtubeId(trailerUrl);
  if (!id) {
    return `<a class="trailer-odkaz" href="${escapeHtml(trailerUrl)}" target="_blank" rel="noopener">▶ Přehrát trailer</a>`;
  }
  const thumb = `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;
  return `
    <div class="trailer">
      <button type="button" class="trailer-facade" data-yt-id="${id}"
              style="background-image:url('${thumb}')" aria-label="Přehrát trailer">
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

// CSS třída karty podle koncertního typu — každý typ má vlastní barvu akcentu
// (klasika modrá, jazz&blues fialová). Nový koncertní typ = řádek sem + barva v CSS.
const KONCERT_CSS_TRIDA = {
  koncerty_klasika: "karta-koncert",
  koncerty_jazzblues: "karta-jazzblues",
};

// Karta koncertu = klon výstavní (stejný skeleton), akcent podle typu (viz .karta-koncert /
// .karta-jazzblues v CSS). Dolní blok = datum · čas + klub (odkaz) + volitelně cena. Když má
// koncert víc termínů, přidá se za čas klikací „(N)" na modal se všemi termíny — jako u filmů.
function vykresliKartuKoncertu(k, id, rozsah, typAkce) {
  const cssTrida = KONCERT_CSS_TRIDA[typAkce] || "karta-koncert";
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
      return vykresliKartuKoncertu(polozka.data, id, rozsah, polozka.typAkce);
    default:
      return "";
  }
}

function prekresli() {
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

  if (rozsah === "vse") {
    vstupOd.value = "";
    vstupDo.value = "";
  } else if (rozsah === "dnes") {
    vstupOd.value = naFormatVstupu(dnes);
    vstupDo.value = naFormatVstupu(dnes);
  } else if (rozsah === "tyden") {
    const konec = new Date(dnes);
    konec.setDate(konec.getDate() + 7);
    vstupOd.value = naFormatVstupu(dnes);
    vstupDo.value = naFormatVstupu(konec);
  } else if (rozsah === "mesic") {
    const konec = new Date(dnes);
    konec.setMonth(konec.getMonth() + 1);
    vstupOd.value = naFormatVstupu(dnes);
    vstupDo.value = naFormatVstupu(konec);
  }

  prekresli();
}

// ---- inicializace ----

async function init() {
  VSECHNY_AKCE = await nactiVsechnaData();
  naplnFiltrTypu();
  prekresli();

  document.getElementById("filtr-typ").addEventListener("change", prekresli);
  document.getElementById("razeni").addEventListener("change", prekresli);
  document.getElementById("filtr-od").addEventListener("change", prekresli);
  document.getElementById("filtr-do").addEventListener("change", prekresli);

  document.querySelectorAll(".rychle-volby button[data-rozsah]").forEach((tlacitko) => {
    tlacitko.addEventListener("click", () => nastavRychlyRozsah(tlacitko.dataset.rozsah));
  });

  // Delegovaný klik na kontejner karet (karty se překreslují přes innerHTML, tak posloucháme
  // na rodiči): buď spustit trailer, nebo otevřít modal se všemi projekcemi.
  document.getElementById("seznam-akci").addEventListener("click", (e) => {
    const facade = e.target.closest(".trailer-facade");
    if (facade) {
      const id = facade.dataset.ytId;
      facade.parentElement.innerHTML =
        `<iframe class="trailer-embed" src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0" ` +
        `title="Trailer" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" ` +
        `allowfullscreen></iframe>`;
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
      const id = decodeURIComponent(srdce.dataset.id);
      const noveOblibene = !OBLIBENE.has(id);
      if (noveOblibene) OBLIBENE.add(id);
      else OBLIBENE.delete(id);
      ulozOblibene();
      srdce.classList.toggle("je-oblibene", noveOblibene);
      srdce.setAttribute("aria-pressed", noveOblibene);
      // když je zapnutý filtr oblíbených, odznačená karta musí zmizet → překreslit
      if (JEN_OBLIBENE) prekresli();
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

  nastavModal();
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
