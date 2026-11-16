---
name: preskoruj
description: Rituál učení z Bobova žebříčku v appce Akce — přečte zálohu (žebříček + kotvy), vyčte z něj nový filmový profil do support/esteticky-profil.md a přeskóruje celou filmotéku (data/filmy_doma.json + čekárnu) po dávkách. Použij, když Bob řekne „přeskóruj filmotéku", „nauč se z žebříčku", „v žebříčku přibyly filmy", nebo spustí /preskoruj. Doporučený rytmus: když v žebříčku přibude ~20 filmů nebo Bob přepíše hodně kotev.
---

# Přeskórování — filmotéka se učí z Bobova žebříčku

Bob v appce řadí viděné filmy do žebříčku (tři: film / seriál / dokument) a u některých
píše natvrdo skóre (kotvy); ostatní se dopočítají z pozice. Jeho čísla appka ukazuje
sama a okamžitě. Tenhle rituál řeší **zbytek** — AI odhad `estetickeSkore` u filmů,
které Bob neviděl: vyčte z žebříčku, jak Bob skutečně hodnotí, a podle toho přeskóruje
filmotéku. Skóre = jak moc se to bude líbit Bobovi, ne jak je film dobrý.

**Do žebříčku, kotev ani zálohy nikdy nesahej** — jsou jen Bobovy, rituál je jen čte.

Mechanika: `python -I .claude/skills/preskoruj/preskoruj.py <příkaz>` (popis příkazů
v hlavičce skriptu). Pracovní soubory patří do scratchpadu (dál `<S>`).

## Postup

1. **Čerstvá záloha.** Bob ji uloží v appce (šipka dolů, desktop) do
   `local/akce-zaloha.json`. Skript vypíše datum zálohy — když je stará (Bob od té doby
   řadil), řekni mu, ať ji uloží znovu.
   ```
   python -I .claude/skills/preskoruj/preskoruj.py zebricek <S>/zebricek.json
   ```

2. **Profil ze žebříčku** — pusť čerstvého agenta (general-purpose, na pozadí), který
   čte JEN `<S>/zebricek.json` (žádný starý profil — nesmí ho ovlivnit) a napíše
   `<S>/profil.md`. Zadání (osvědčené 2026-11-16):
   - vyčíst skutečný vkus ze všech dimenzí (tón, emoce pravdivá vs. tlačená, tempo,
     realismus vs. stylizace, herectví, režie, obraz/zvuk/hudba, struktura, téma,
     ambivalence vs. didaktičnost, humor vřelý vs. satirický, doba a stárnutí, žánr…);
   - psát **tendence s váhou a protipříklady, ne zákony** — žádné stropy podle roku,
     výjimky (2001 = 100, Harold a Maude 97, Kmotr 70) přiznat a nechat je na sousedech;
   - pole `ai`/`f101`/`imdb` v souboru ignorovat;
   - struktura: nadpis `### Filmový vkus — vyčteno ze žebříčku (<datum>, <N> filmů)`,
     pod ním `####` Jádro vkusu / Tendence / Rozchod s kánonem / Kalibrace škály
     (připomenout, že neviděný průměrný film začíná ~60–65) / Seriály a dokumenty /
     Nejistoty; rozsah 1–2 strany.
   Přečti výsledek a zkontroluj, že nepíše zákony ani nesmysly.

3. **Zápis profilu** — v `support/esteticky-profil.md` nahraď blok mezi
   `<!-- ZEBRICEK-PROFIL:START -->` a `<!-- ZEBRICEK-PROFIL:END -->` obsahem
   `<S>/profil.md`. Sekci „Jak odhadovat skóre filmu" nad blokem nech (je to metoda,
   ne vkus) a zbytek profilu (hudba, literatura, typy akcí) nikdy neměň — čtou ho
   Cowork prompty ostatních typů akcí.

4. **Test naslepo (volitelný, ~2 agenti navíc)** — dělej ho, když Bob chce vidět,
   jak se učení zlepšuje (třeba každé druhé kolo):
   ```
   python -I .claude/skills/preskoruj/preskoruj.py test-priprav <S>/zebricek.json <S>/test
   ```
   a) agent vyčte profil JEN z `<S>/test/znamy.json` (stejné zadání jako bod 2) →
      `<S>/test/profil.md`; b) druhý čerstvý agent dostane ten profil + `znamy.json`
      + `odhadni.json` a odhadne skryté filmy (jen tyhle tři soubory, nic z `data/`
      ani `local/`!) → `<S>/test/predikce.json` = `[{nazev, odhad, sousede, duvod}]`;
   ```
   python -I .claude/skills/preskoruj/preskoruj.py test-vyhodnot <S>/test <S>/test/predikce.json
   ```
   Výsledek připiš do `support/preskoruj-historie.md` (datum, počet filmů a kotev,
   chyba, spearman, posun, srovnání se starým AI). Profil z bodu 2 nesmí do testu
   (viděl skryté filmy).

5. **Dávky a přeskórování** —
   ```
   python -I .claude/skills/preskoruj/preskoruj.py davky <S>/presk 350
   ```
   Na každou dávku jeden agent na pozadí (všechny naráz). Zadání: přečti
   `support/esteticky-profil.md` (sekce Jak odhadovat + Filmový vkus), `<S>/zebricek.json`
   (Bobovy filmy s čísly — sousedi) a `<S>/presk/davka_NN.json`; pro každý film podle
   toho, co o něm víš, najdi podobné filmy v žebříčku, vsuň ho mezi ně a dej celé číslo
   0–100. f101/IMDb jen jako slabý výchozí bod; film, o kterém skoro nic nevíš → opatrně
   kolem 55–65 podle žánru a f101. Výstup `<S>/presk/vysledek_NN.json` = `{klic: skóre}`
   pro VŠECHNY filmy dávky (klíč přesně z pole `klic`). Nic jiného nečíst (ne `data/`).

6. **Slití** —
   ```
   python -I .claude/skills/preskoruj/preskoruj.py slij <S>/presk
   ```
   Skript zkontroluje úplnost a rozsahy, zapíše jen `estetickeSkore` (ověří, že se nic
   jiného nezměnilo) a vypíše rozložení. Rozumné je průměr kolem 60–65 a „≥80" v řádu
   stovek, ne tisíců (hvězda = práh 80). Kdyby jedna dávka ujela (průměr o 10+ jinde
   než ostatní), pusť ji znovu.

7. **Commit, nepushovat** — `Filmotéka: přeskórováno podle žebříčku (N filmů, K kotev)`
   + zvlášť profil. Push až v balíku (šetrně ke GitHubu).

8. **Hlášení Bobovi** — krátce: z kolika filmů a kotev se učilo, co nového profil
   vyčetl, výsledek testu (když běžel) a pár zajímavých posunů (film, staré → nové).
   Text `duvodSkore` u filmů zůstává z dřívějška a nemusí ke skóre sedět — Bob o tom ví.
