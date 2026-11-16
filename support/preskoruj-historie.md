# Přeskórování — historie testů naslepo

Test: žebříček se rozdělí na 2/3 známé a 1/3 skryté (stratifikovaně podle skóre),
čerstvý agent odhaduje skryté filmy. Chyba = průměrná absolutní odchylka od Bobova
čísla (kotva nebo dopočet z pozice), spearman = jak sedí pořadí (1 = přesně).
Postup viz `.claude/skills/preskoruj/SKILL.md`.

| datum | filmů / kotev | metoda | chyba | spearman | posun | pozn. |
|---|---|---|---|---|---|---|
| 2026-11-16 | 95 / 19 | staré AI skóre (původní profil, bez žebříčku) | 17,8 | +0,27 | +16,6 | systematicky přestřeluje |
| 2026-11-16 | 95 / 19 | původní profil + sousedi ze žebříčku | 12,8 (bez oblíbených z profilu 13,8) | +0,55 | −3,5 | 5 testovacích filmů bylo v profilu jako oblíbené → opsáno |
| 2026-11-16 | 95 / 19 | profil vyčtený ze 2/3 žebříčku + sousedi | 14,2 (bez oblíbených 13,3) | +0,34 | −3,6 | přeučený („po 2013 strop", „metafyzika dolů") → 2001, Harold a Maude, Stalker dolů |

Hloupý odhad „všem průměr (79)" měl chybu 14,3 — test je nejtěžší možný řez
(rozlišovat mezi filmy, které Bob sám vybral a viděl). Pravda je zatím z velké části
dopočet z 19 kotev, takže sama kolísá o pár bodů; s víc kotvami bude test ostřejší.
