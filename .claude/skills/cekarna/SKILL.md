---
name: cekarna
description: Přidá Bobovy filmy z čekárny (support/cekarna.txt nebo seznam v chatu) do filmotéky appky Akce — dohledá IMDb/OMDb hodnocení, trailer, napíše popis, oskóruje podle profilu a zapíše do data/filmy_doma_pridane.json. Použij, když Bob řekne „v čekárně jsou nový filmy", „přidej filmy do filmotéky/čekárny", vloží seznam filmů, co chce vidět, nebo spustí /cekarna.
---

# Čekárna — Bobovy filmy do filmotéky

Bob si sem sype filmy, na které si vzpomene (chce je vidět, nebo už je viděl a chce je
mít v žebříčku). Cíl: každý film dostane totéž co filmy z films101 — trailer, popis,
estetické skóre podle profilu, dobovou zátěž (dudlík), vážený průměr — a v appce nese
štítek „čekárna". Appka soubor `data/filmy_doma_pridane.json` přilepí k filmotéce sama.

## Vstup

- `support/cekarna.txt` — jeden film na řádek, rok volitelně („Pelíšky", „Kristián 1939").
  Řádky s `#` jsou komentáře. Když Bob pošle seznam (nebo zkopírovaný sloupec z Excelu)
  rovnou do chatu, zapiš ho nejdřív do tohohle souboru.
- Na konec řádku jde dát natvrdo IMDb ID (`Kouř 1991 tt0102234`) — pro filmy, co
  automatika nenajde.

## Postup

1. **Dohledání** (mechanika, skript):
   ```
   python -I .claude/skills/cekarna/cekarna.py dohledej support/cekarna.txt <scratchpad>/cekarna_prace.json
   ```
   Klíč OMDb je v proměnné prostředí `OMDB_KEY` (uživatelská, nastavená přes `setx`).
   Když ji běžící proces nevidí (app nebyla restartovaná), přečti ji z registru:
   `[Environment]::GetEnvironmentVariable("OMDB_KEY","User")`. Klíč NIKDY do repa.
   Když OMDb hlásí limit/neplatný klíč, skript sám skončí — nahlas to Bobovi.

2. **Kontrola shody** — skript tiskne značky:
   - `OK` = název sedí, `?!` = jiný název (typicky český vstup vs. anglický IMDb titul —
     „Pelíšky" → „Cosy Dens" je správně), `??` = nenalezeno.
   - U KAŽDÉHO filmu (i OK) zkontroluj v pracovním JSONu `omdb.Director`/`Year`/`Plot`, že je
     to opravdu ten film. Při omylu vyber ze `imdbKandidati`, nebo dohledej ID (WebSearch
     „<název> <rok> imdb"), doplň `tt…` na řádek a skript pro ty řádky pusť znova.
   - `[UŽ JE V DATECH]` = film už ve filmotéce/čekárně je → nepřidávat, jen Bobovi říct
     (žebříček/viděno u něj funguje už teď).

3. **Trailer** — z `trailery` (všechny jsou ověřené přes oEmbed) vyber podle titulku a kanálu
   ten, co je opravdu trailer TOHO filmu (pozor na stejnojmenné filmy: „Kouř" ≠ „Smoke" 1995).
   Preferuj oficiální/restaurovaný trailer; u starých českých filmů je OK i
   „Some like it Czech" nebo ukázka z filmu. Nic vhodného → `trailerUrl: null`.

4. **Texty a skóre** — přečti `support/esteticky-profil.md` a pro každý film napiš:
   - `popis`: 2–3 věty česky o filmu, bez spoilerů (o čem to je, jaký to má tón).
   - `duvodSkore`: JEDNA věta, proč to Bobovi sedne / nesedne (karta ji ukazuje jako hlavní text).
   - `estetickeSkore`: 0–100 podle profilu, stejná přísnost jako zbytek filmotéky
     (pro kalibraci se podívej na pár podobných filmů v `data/filmy_doma.json`).
   - `dobovaZatez`: 0–10 = kolik z pověsti filmu nese doba vzniku, technika, vliv, závažnost
     tématu — NE provedení z dnešního pohledu. Kalibrace: 0 = Mulholland Dr., Festen,
     Parasite; 3–4 = 400 Blows, Vertigo, 2001; 6–7 = Tokyo Story, Citizen Kane, Ordet;
     9–10 = Joan of Arc, Potěmkin, Jeanne Dielman, němý film obecně.

5. **Sestav hotový JSON** (pole objektů) do scratchpadu, jeden film:
   ```json
   {
     "nazevCz": "Pelíšky",              // jak to Bob zná (český distribuční název)
     "nazevOrig": "Cosy Dens",          // anglický titul z OMDb (Title) — jako zbytek filmotéky;
                                        //   na něm stojí ID srdíček/žebříčku a Wikipedie/IMDb lookup
     "rok": "1999",                     // z pracovního JSONu ("rok", = IMDb rok vzniku), string
     "rezie": "Jan Hřebejk",            // s diakritikou (OMDb ji občas ztrácí)
     "zanr": "Comedy, Drama",           // z OMDb Genre
     "popis": "…",
     "duvodSkore": "…",
     "estetickeSkore": 78,
     "dobovaZatez": 1,
     "trailerUrl": "https://www.youtube.com/watch?v=…",
     "imdbId": "tt0167331",
     "cesky": true,                     // česká/československá produkce (OMDb Country
                                        //   obsahuje "Czech"); appka podle něj hledá „český"
     "hodnoceni": { … }                 // 1:1 z pracovního JSONu (imdb, metacritic,
                                        //   rottenTomatoes, vazenePrumer, poznamkaHodnoceni)
   }
   ```
   `films101` tam není (null/chybí) — karta místo něj ukáže IMDb.
   Seriál (IMDb `TV series`/`TV mini-series`) je v pořádku — Bob tam dává i Vinyl nebo
   Babylon Berlin; do `zanr` dej na začátek „Seriál, " a do `rezie` tvůrce/showrunnera
   (OMDb má u seriálů Director N/A).
   Bob píše názvy z hlavy, česky i s překlepy, někdy jen hlášku nebo herce
   („Zavřete oči, odcházím" = píseň z Kristiána, „Humr" = The Lobster) — rozlušti
   je předem a do vstupu pro skript dej anglický/originální název s rokem.
   Co nejde rozlousknout ani přes WebSearch, nech v čekárně a zeptej se.

6. **Zápis**:
   ```
   python -I .claude/skills/cekarna/cekarna.py zapis <scratchpad>/cekarna_hotove.json
   ```
   Skript hlídá povinná pole, rozsahy a duplicity a doplní zbytek kontraktu
   (`projekce: []`, `pridanoAt` …).

7. **Úklid a commit** — z `support/cekarna.txt` smaž zpracované řádky (nechej hlavičku
   s komentářem a řádky, co se nepovedly), commitni (`Čekárna: +N filmů (…)`).
   **Nepushuj** — push jde po celcích (šetrně ke GitHubu), Bobovi jen řekni, že je to
   připravené.

8. **Hlášení Bobovi** — krátce: co přibylo (název, rok, skóre), co bylo duplicitní,
   co se nenašlo a proč. V appce je najde ve filmotéce (pás), štítek „čekárna";
   do hledání stačí napsat `cekarna` a ukážou se jen jeho přídavky, `český` = jen české.
