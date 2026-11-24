import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

from core.pdf_analyzer import run_full_inspection


def _resource_path(relative_path):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative_path)


class PrintPDFInspectorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PrintPDF Inspector — Preflight & Kontrola Druku")
        self.geometry("760x620")
        self.minsize(720, 580)

        icon_file = _resource_path("icon.ico")
        if os.path.isfile(icon_file):
            try:
                img = Image.open(icon_file); self._icon_ref = ImageTk.PhotoImage(img); self.iconphoto(True, self._icon_ref)
            except Exception:
                pass

        self.pdf_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=os.path.abspath("output"))

        # Checkboxy modułów
        self.chk_rgb_var = tk.BooleanVar(value=True)
        self.chk_tac_var = tk.BooleanVar(value=True)
        self.chk_dpi_var = tk.BooleanVar(value=True)
        self.chk_fonts_var = tk.BooleanVar(value=True)
        self.chk_overprint_var = tk.BooleanVar(value=True)
        self.chk_hairlines_var = tk.BooleanVar(value=True)

        # Parametry progowe
        self.tac_profile_var = tk.StringVar(value="300")
        self.tac_limit_var = tk.StringVar(value="300")
        self.min_dpi_var = tk.StringVar(value="250")
        self.min_pt_var = tk.StringVar(value="5.0")
        self.min_line_var = tk.StringVar(value="0.25")

        self.status_var = tk.StringVar(value="Gotowy do pracy. Wybierz plik PDF.")
        self.report_paths = {}

        self._build_ui()
        self.deiconify()
        self.lift()
        self.focus_force()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # 1. Sekcja wyboru plików
        file_frame = ttk.LabelFrame(self, text="Plik źródłowy i folder raportów")
        file_frame.pack(fill="x", **pad)

        ttk.Label(file_frame, text="Plik PDF:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(file_frame, textvariable=self.pdf_path_var).grid(row=0, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(file_frame, text="Wybierz PDF...", command=self._browse_pdf).grid(row=0, column=2, padx=8, pady=6)

        ttk.Label(file_frame, text="Folder raportów:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(file_frame, textvariable=self.output_dir_var).grid(row=1, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(file_frame, text="Zmień...", command=self._browse_output).grid(row=1, column=2, padx=8, pady=6)
        file_frame.columnconfigure(1, weight=1)

        # 2. Sekcja reguł preflightu
        rules_frame = ttk.LabelFrame(self, text="Reguły kontroli przed drukiem (Preflight)")
        rules_frame.pack(fill="x", **pad)

        # Wiersz 0: RGB / SPOT
        ttk.Checkbutton(
            rules_frame,
            text="Wykrywanie przestrzeni RGB oraz kolorów dodatkowych Pantone / SPOT",
            variable=self.chk_rgb_var
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=4)

        # Wiersz 1: TAC
        ttk.Checkbutton(
            rules_frame,
            text="Analiza pokrycia farbą TAC (%):",
            variable=self.chk_tac_var
        ).grid(row=1, column=0, sticky="w", padx=8, pady=4)

        ttk.Radiobutton(
            rules_frame, text="Powlekany (300%)", variable=self.tac_profile_var, value="300",
            command=lambda: self.tac_limit_var.set("300")
        ).grid(row=1, column=1, sticky="w", padx=4)

        ttk.Radiobutton(
            rules_frame, text="Niepowlekany / Gazeta (240%)", variable=self.tac_profile_var, value="240",
            command=lambda: self.tac_limit_var.set("240")
        ).grid(row=1, column=2, sticky="w", padx=4)

        ttk.Entry(rules_frame, textvariable=self.tac_limit_var, width=7).grid(row=1, column=3, sticky="w", padx=8)

        # Wiersz 2: DPI
        ttk.Checkbutton(
            rules_frame,
            text="Minimalna rozdzielczość bitmap (DPI):",
            variable=self.chk_dpi_var
        ).grid(row=2, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(rules_frame, textvariable=self.min_dpi_var, width=7).grid(row=2, column=1, sticky="w", padx=4)

        # Wiersz 3: Małe fonty
        ttk.Checkbutton(
            rules_frame,
            text="Minimalny rozmiar fontu (pt):",
            variable=self.chk_fonts_var
        ).grid(row=3, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(rules_frame, textvariable=self.min_pt_var, width=7).grid(row=3, column=1, sticky="w", padx=4)

        # Wiersz 4: Biały overprint
        ttk.Checkbutton(
            rules_frame,
            text="Wykrywanie białych tekstów i wektorów na nadruku (White Overprint)",
            variable=self.chk_overprint_var
        ).grid(row=4, column=0, columnspan=4, sticky="w", padx=8, pady=4)

        # Wiersz 5: Cienkie linie
        ttk.Checkbutton(
            rules_frame,
            text="Minimalna grubość linii / obrysu (pt):",
            variable=self.chk_hairlines_var
        ).grid(row=5, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(rules_frame, textvariable=self.min_line_var, width=7).grid(row=5, column=1, sticky="w", padx=4)
        # 3. Przyciski akcji i pasek postępu
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", **pad)

        self.run_btn = ttk.Button(action_frame, text="URUCHOM INSPEKCJĘ PDF", command=self._start_inspection)
        self.run_btn.pack(side="left", ipadx=14, ipady=6)

        ttk.Button(action_frame, text="Otwórz folder raportów", command=self._open_output_dir).pack(side="right", ipady=4)

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=12, pady=2)

        ttk.Label(self, textvariable=self.status_var, foreground="#1a5fb4").pack(anchor="w", padx=12, pady=2)

        # 4. Tabela wyników
        result_frame = ttk.LabelFrame(self, text="Wyniki inspekcji (kliknij dwukrotnie wiersz, aby otworzyć raport PDF)")
        result_frame.pack(fill="both", expand=True, **pad)

        columns = ("test", "count", "file")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=8)
        self.tree.heading("test", text="Kontrolowany parametr")
        self.tree.heading("count", text="Wykryte błędy")
        self.tree.heading("file", text="Wygenerowany raport PDF")

        self.tree.column("test", width=260)
        self.tree.column("count", width=110, anchor="center")
        self.tree.column("file", width=330)

        self.tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree.bind("<Double-1>", self._on_row_double_click)

    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik PDF do sprawdzenia",
            filetypes=(("Pliki PDF", "*.pdf"), ("Wszystkie pliki", "*.*"))
        )
        if path:
            self.pdf_path_var.set(os.path.abspath(path))

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Wybierz folder zapisu raportów")
        if folder:
            self.output_dir_var.set(os.path.abspath(folder))

    def _open_output_dir(self):
        folder = self.output_dir_var.get().strip()
        if folder and os.path.isdir(folder):
            os.startfile(folder)
        else:
            messagebox.showwarning("Brak folderu", "Folder raportów jeszcze nie istnieje.")

    def _on_row_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = next(iter(selected))
        pdf_file = self.report_paths.get(item_id)
        if pdf_file and os.path.isfile(pdf_file):
            os.startfile(pdf_file)

    def _start_inspection(self):
        pdf_path = self.pdf_path_var.get().strip()
        output_dir = self.output_dir_var.get().strip()

        if not pdf_path or not os.path.isfile(pdf_path):
            messagebox.showerror("Błąd", "Wybierz prawidłowy plik PDF.")
            return

        try:
            tac_limit = int(float(self.tac_limit_var.get().replace(",", ".")))
            min_dpi = int(float(self.min_dpi_var.get().replace(",", ".")))
            min_pt = float(self.min_pt_var.get().replace(",", "."))
            min_line = float(self.min_line_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Błąd parametrów", "Wprowadź poprawne wartości liczbowe w polach progów.")
            return

        for row in self.tree.get_children():
            self.tree.delete(row)
        self.report_paths.clear()

        self.run_btn.config(state="disabled")
        self.progress.start(12)
        self.status_var.set("Rozpoczynam analizę pliku PDF...")

        worker = threading.Thread(
            target=self._run_worker,
            args=(pdf_path, output_dir, tac_limit, min_dpi, min_pt, min_line),
            daemon=True
        )
        worker.start()

    def _run_worker(self, pdf_path, output_dir, tac_limit, min_dpi, min_pt, min_line):
        try:
            summary = run_full_inspection(
                pdf_path=pdf_path,
                output_dir=output_dir,
                check_rgb_spot=self.chk_rgb_var.get(),
                check_tac=self.chk_tac_var.get(),
                tac_limit=tac_limit,
                check_dpi=self.chk_dpi_var.get(),
                min_dpi=min_dpi,
                check_fonts=self.chk_fonts_var.get(),
                min_pt=min_pt,
                check_overprint=self.chk_overprint_var.get(),
                check_hairlines=self.chk_hairlines_var.get(),
                min_width_pt=min_line,
                progress_callback=lambda msg: self.after(0, self.status_var.set, msg)
            )
            self.after(0, self._on_inspection_done, summary)
        except Exception as err:
            self.after(0, self._on_inspection_error, str(err))

    def _on_inspection_done(self, summary):
        self.progress.stop()
        self.run_btn.config(state="normal")

        reports = summary.get("reports", ())
        if not reports:
            self.status_var.set("Zakończono: Brak błędów! Plik spełnia wszystkie wybrane kryteria.")
            self.tree.insert("", "end", values=("Wszystkie wybrane testy", "0 (OK)", "Brak uwag"))
            messagebox.showinfo("Wynik inspekcji", "Nie wykryto żadnych błędów w pliku PDF!")
            return

        for label, count, path in reports:
            row_id = self.tree.insert("", "end", values=(label, count, os.path.basename(path)))
            self.report_paths.update({row_id: path})

        self.status_var.set(f"Zakończono! Wygenerowano {len(reports)} raport(y) z wykrytymi uwagami.")

    def _on_inspection_error(self, err_msg):
        self.progress.stop()
        self.run_btn.config(state="normal")
        self.status_var.set("Wystąpił błąd podczas analizy.")
        messagebox.showerror("Błąd analizy", err_msg)


def launch_gui():
    app = PrintPDFInspectorApp()
    
    try:
        import pyi_splash
        if pyi_splash.is_alive():
            pyi_splash.close()
    except ImportError:
        pass

    app.mainloop()

