// ---- app.js ----
// Tupý renderer: načte JSONy z data/, slouží filtry a řazení, vykreslí karty.
// Žádné AI, žádné API, jen práce s hotovými daty.

// Seznam JSON souborů, které appka umí načíst. Když přibude nový typ akce
// (kvízy, koncerty...), stačí sem přidat soubor a appka ho zvládne bez dalších změn.
const ZDROJE_DAT = ["data/filmy.json"];

let VSECHNY_AKCE = []; // sloučená, normalizovaná data ze všech zdrojů

// ---- pomocné funkce ----

// "10.07.2026" -> Date objekt, ať se dá řadit/filtrovat
function parsujDatum(retezec) {
  if (!retezec) return null;
  const [den, mesic, rok] = retezec.split(".").map(Number);
  if (!den || !mesic || !rok) return null;
  return new Date(rok, mesic - 1, den);
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
        if (!odpoved.ok) throw new Error(`HTTP ${odpoved.status}`);
        return await odpoved.json();
      } catch (chyba) {
        console.warn(`Nepodařilo se načíst ${cesta}:`, chyba);
        return null;
      }
    })
  );

  const akce = [];
  for (const soubor of vysledky) {
    if (!soubor) continue;
    // zatím jediný typ akce je "filmy" — pole s položkami je pojmenované podle typu
    if (Array.isArray(soubor.filmy)) {
      for (const film of soubor.filmy) {
        akce.push({ typAkce: soubor.typAkce || "filmy", data: film });
      }
    }
    // sem se časem přidá "if (Array.isArray(soubor.kvizy)) ..." atd.
  }
  return akce;
}

// ---- filtrování a řazení ----

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

function ziskejFiltrovaneARazene() {
  const typFiltr = document.getElementById("filtr-typ").value;
  const razeniPodle = document.getElementById("razeni").value;
  const datumOdRetezec = document.getElementById("filtr-od").value; // formát YYYY-MM-DD z <input type=date>
  const datumDoRetezec = document.getElementById("filtr-do").value;
  const datumOd = datumOdRetezec ? new Date(datumOdRetezec) : null;
  const datumDo = datumDoRetezec ? new Date(datumDoRetezec) : null;
  if (datumDo) datumDo.setHours(23, 59, 59, 999); // ať "do" zahrnuje celý ten den

  let vysledek = VSECHNY_AKCE.filter((polozka) => {
    if (typFiltr !== "vse" && polozka.typAkce !== typFiltr) return false;
    if ((datumOd || datumDo) && !maProjekciVRozmezi(polozka.data.projekce, datumOd, datumDo)) return false;
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
      const dA = nejblizsiDatumProjekce(a.data.projekce);
      const dB = nejblizsiDatumProjekce(b.data.projekce);
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

function vykresliProjekce(projekce) {
  if (!projekce || projekce.length === 0) {
    return "<p class='poznamka-hodnoceni'>Zatím žádné projekce v nabídce.</p>";
  }
  const polozky = projekce
    .map((p) => {
      const misto = escapeHtml(hodnotaNebo(p.misto));
      const datum = escapeHtml(hodnotaNebo(p.datum));
      const cas = escapeHtml(hodnotaNebo(p.cas));
      const odkazOtevreny = p.odkaz
        ? `<a href="${escapeHtml(p.odkaz)}" target="_blank" rel="noopener">${misto}</a>`
        : misto;
      return `<li><span>${datum} · ${cas}</span> ${odkazOtevreny}</li>`;
    })
    .join("");
  return `<ul class="projekce-seznam">${polozky}</ul>`;
}

function vykresliHodnoceniRozpad(hodnoceni) {
  if (!hodnoceni) return "";
  const polozky = [
    ["RT", hodnoceni.rottenTomatoesAudience, "%"],
    ["MC", hodnoceni.metacriticUser, "/10"],
    ["IMDb", hodnoceni.imdb, "/10"],
    ["ČSFD", hodnoceni.csfd, "%"],
  ]
    .filter(([, hodnota]) => hodnota !== null && hodnota !== undefined)
    .map(([nazev, hodnota, jednotka]) => `<span><strong>${nazev}</strong> ${hodnota}${jednotka}</span>`)
    .join("");

  const poznamka = hodnoceni.poznamkaHodnoceni
    ? `<p class="poznamka-hodnoceni">${escapeHtml(hodnoceni.poznamkaHodnoceni)}</p>`
    : "";

  return `<div class="hodnoceni-rozpad">${polozky}</div>${poznamka}`;
}

function vykresliKartuFilmu(film) {
  const skore = hodnotaNebo(film.estetickeSkore, "—");
  const vazenePrumer = film.hodnoceni?.vazenePrumer;

  return `
    <article class="karta">
      <div class="karta-hlavicka">
        <div class="karta-titulky">
          <h2>${escapeHtml(film.nazevCz)}</h2>
          ${film.nazevOrig && film.nazevOrig !== film.nazevCz ? `<p class="nazev-orig">${escapeHtml(film.nazevOrig)}</p>` : ""}
        </div>
        <div class="skore" title="Estetické skóre">${escapeHtml(skore)}</div>
      </div>

      <div class="metadata">
        <span>${escapeHtml(hodnotaNebo(film.rezie))}</span>
        <span>·</span>
        <span>${escapeHtml(hodnotaNebo(film.zanr))}</span>
        ${vazenePrumer !== null && vazenePrumer !== undefined ? `<span>·</span><span>Hodnocení ${escapeHtml(vazenePrumer)}</span>` : ""}
      </div>

      ${film.specialniProjekce ? `<span class="stitek-special">${escapeHtml(hodnotaNebo(film.specialniPopis, "Speciální projekce"))}</span>` : ""}

      <p class="popis">${escapeHtml(hodnotaNebo(film.popis))}</p>

      ${film.duvodSkore ? `<p class="duvod-skore">${escapeHtml(film.duvodSkore)}</p>` : ""}

      ${vykresliHodnoceniRozpad(film.hodnoceni)}

      ${film.vlastniRecenze ? `<p class="recenze">${escapeHtml(film.vlastniRecenze)}</p>` : ""}

      ${vykresliProjekce(film.projekce)}
    </article>
  `;
}

function vykresliKartu(polozka) {
  // zatím jediný typ, ale switch je připravený na rozšíření
  switch (polozka.typAkce) {
    case "filmy":
      return vykresliKartuFilmu(polozka.data);
    default:
      return "";
  }
}

function prekresli() {
  const kontejner = document.getElementById("seznam-akci");
  const prazdnyStav = document.getElementById("prazdny-stav");
  const akce = ziskejFiltrovaneARazene();

  if (akce.length === 0) {
    kontejner.innerHTML = "";
    prazdnyStav.hidden = false;
    return;
  }

  prazdnyStav.hidden = true;
  kontejner.innerHTML = akce.map(vykresliKartu).join("");
}

// naplní select "Typ akce" podle toho, jaké typy skutečně přišly v datech
function naplnFiltrTypu() {
  const select = document.getElementById("filtr-typ");
  const typy = [...new Set(VSECHNY_AKCE.map((a) => a.typAkce))];
  for (const typ of typy) {
    const option = document.createElement("option");
    option.value = typ;
    option.textContent = typ.charAt(0).toUpperCase() + typ.slice(1);
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

  document.querySelectorAll(".rychle-volby button").forEach((tlacitko) => {
    tlacitko.addEventListener("click", () => nastavRychlyRozsah(tlacitko.dataset.rozsah));
  });
}

init();
