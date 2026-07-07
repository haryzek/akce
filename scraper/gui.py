"""
Jednoduché GUI ke scraperu (tkinter — je v Pythonu, žádná další závislost).

Nejdřív vybereš typ(y) akce (zaškrtávátka se plní automaticky podle dostupných
zdrojů v run.py), pak rozmezí datumu, a klikneš Spustit. Scrape běží na pozadí,
průběh se sype do log okna. Cíl: nescrapovat všech deset typů, když chceš jen kina.

Spouští se přes scrapni.bat (dvojklik), nebo `python gui.py`.
"""

import queue
import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, scrolledtext

import run

DATOVY_FORMAT = "%d-%m-%Y"


def _validni_datum(text):
    """True když text sedí na DD-MM-YYYY."""
    try:
        datetime.strptime(text, DATOVY_FORMAT)
        return True
    except ValueError:
        return False


class ScraperGui:
    def __init__(self, root):
        self.root = root
        self.log_q = queue.Queue()  # vlákno scraperu sem sype řádky, GUI je pravidelně vybírá
        self.bezi = False

        root.title("Scraper akcí")
        root.minsize(560, 520)

        ramec = ttk.Frame(root, padding=16)
        ramec.pack(fill="both", expand=True)

        ttk.Label(ramec, text="Scraper akcí", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            ramec,
            text="Vyber typ(y) akce a rozmezí datumu. Scrapne se jen to zaškrtnuté.",
            foreground="#666",
        ).pack(anchor="w", pady=(0, 12))

        # --- výběr typů akcí (zaškrtávátka podle dostupných zdrojů) ---
        box_typy = ttk.LabelFrame(ramec, text="Typ akce", padding=10)
        box_typy.pack(fill="x", pady=(0, 12))

        self.typ_vars = {}
        for typ in run.dostupne_typy():
            var = tk.BooleanVar(value=False)
            self.typ_vars[typ] = var
            ttk.Checkbutton(box_typy, text=run.popisek(typ), variable=var).pack(anchor="w")

        # rychlé přepínače Vše / Nic
        prepinace = ttk.Frame(box_typy)
        prepinace.pack(anchor="w", pady=(8, 0))
        ttk.Button(prepinace, text="Vše", width=8, command=lambda: self._nastav_vse(True)).pack(side="left")
        ttk.Button(prepinace, text="Nic", width=8, command=lambda: self._nastav_vse(False)).pack(side="left", padx=(6, 0))

        # --- rozmezí datumu (předvyplněno dnes až +30 dní) ---
        box_datum = ttk.LabelFrame(ramec, text="Rozmezí datumu (DD-MM-YYYY)", padding=10)
        box_datum.pack(fill="x", pady=(0, 12))

        dnes = datetime.now()
        self.e_od = ttk.Entry(box_datum, width=14)
        self.e_od.insert(0, dnes.strftime(DATOVY_FORMAT))
        self.e_do = ttk.Entry(box_datum, width=14)
        self.e_do.insert(0, (dnes + timedelta(days=30)).strftime(DATOVY_FORMAT))

        ttk.Label(box_datum, text="Od:").grid(row=0, column=0, sticky="w")
        self.e_od.grid(row=0, column=1, padx=(6, 18))
        ttk.Label(box_datum, text="Do:").grid(row=0, column=2, sticky="w")
        self.e_do.grid(row=0, column=3, padx=(6, 0))

        # --- spuštění + log ---
        self.btn = ttk.Button(ramec, text="Spustit scrape", command=self._spustit)
        self.btn.pack(anchor="w", pady=(0, 10))

        self.log = scrolledtext.ScrolledText(ramec, height=14, font=("Consolas", 9), state="disabled")
        self.log.pack(fill="both", expand=True)

        self.root.after(120, self._vyprazdni_log)

    # ---- ovládání ----

    def _nastav_vse(self, hodnota):
        for var in self.typ_vars.values():
            var.set(hodnota)

    def _pis(self, radek):
        """Bezpečný zápis do log okna (voláno z hlavního vlákna přes frontu)."""
        self.log.configure(state="normal")
        self.log.insert("end", radek + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _vyprazdni_log(self):
        """Pravidelně přelije řádky z fronty (od vlákna scraperu) do okna."""
        while not self.log_q.empty():
            zprava = self.log_q.get()
            if zprava == "__HOTOVO__":
                self.bezi = False
                self.btn.configure(state="normal", text="Spustit scrape")
                self._pis("--- Hotovo. Výsledek je ve složce output\\ ---")
            else:
                self._pis(zprava)
        self.root.after(120, self._vyprazdni_log)

    def _spustit(self):
        if self.bezi:
            return
        vybrane = [t for t, v in self.typ_vars.items() if v.get()]
        od, do = self.e_od.get().strip(), self.e_do.get().strip()

        # validace vstupů — radši srozumitelná hláška než záhadný pád scraperu
        if not vybrane:
            self._pis("Vyber aspoň jeden typ akce.")
            return
        if not (_validni_datum(od) and _validni_datum(do)):
            self._pis("Datum musí být ve formátu DD-MM-YYYY (např. 06-07-2026).")
            return
        if datetime.strptime(od, DATOVY_FORMAT) > datetime.strptime(do, DATOVY_FORMAT):
            self._pis("Datum OD je až po datu DO — prohoď je.")
            return

        self.bezi = True
        self.btn.configure(state="disabled", text="Scrapuju…")
        self._pis(f"Spouštím: {', '.join(run.popisek(t) for t in vybrane)}  ({od} až {do})")
        self._pis("")

        threading.Thread(target=self._worker, args=(od, do, vybrane), daemon=True).start()

    def _worker(self, od, do, vybrane):
        """Běží v samostatném vlákně, ať GUI nezamrzne. Log posílá přes frontu."""
        try:
            run.spust(od, do, typy=vybrane, log=self.log_q.put)
        except Exception as e:
            self.log_q.put(f"CHYBA: {e}")
        finally:
            self.log_q.put("__HOTOVO__")


def main():
    root = tk.Tk()
    ScraperGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
