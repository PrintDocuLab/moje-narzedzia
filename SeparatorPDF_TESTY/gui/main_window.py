
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path


class SeparatorPDFApp:

    def __init__(self, root):
        self.root = root
        self.root.title("separatorPDF")

        # Ustawienia głównego okna
        self.center_window(root, 960, 1050)
        self.root.minsize(850, 800)
        self.root.resizable(True, True)

        self.files = []
        self.mode = tk.StringVar(value="A")

        self.cmyk_vars = {
            "Cyan": tk.BooleanVar(value=True),
            "Magenta": tk.BooleanVar(value=True),
            "Yellow": tk.BooleanVar(value=True),
            "Black": tk.BooleanVar(value=True)
        }

        self.pantone_colors = []

        self.setup_style()
        self.create_interface()

        self.root.update_idletasks()
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.state("normal")
        self.root.deiconify()
        self.root.lift()

    def center_window(self, window, width, height):
        window.update_idletasks()

        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # Nie wychodź poza dostępny ekran
        width = min(width, screen_width - 40)
        height = min(height, screen_height - 80)

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)

        window.geometry(f"{width}x{height}+{x}+{y}")

    def setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 23, "bold"),
            foreground="#183653"
        )

        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 10),
            foreground="#657587"
        )

        style.configure(
            "Section.TLabel",
            font=("Segoe UI", 12, "bold"),
            foreground="#263c50"
        )

        style.configure(
            "Action.TButton",
            font=("Segoe UI", 10),
            padding=8
        )

    # SEPARATORPDF_UI_PATCH_V1

    def create_interface(self):

        self.documents_view = ttk.Frame(self.root)
        self.preview_view = ttk.Frame(self.root)

        self._create_documents_view()
        self.create_preview_view()

        self.documents_view.pack(
            fill="both",
            expand=True
        )

    def create_preview_view(self):

        header = ttk.Frame(
            self.preview_view,
            padding=20
        )
        header.pack(fill="x")

        ttk.Label(
            header,
            text="separatorPDF – Podgląd separacji",
            style="Title.TLabel"
        ).pack(side="left")

        ttk.Button(
            header,
            text="← Powrót do dokumentów",
            command=self.show_documents_view
        ).pack(side="right")

        self.preview_info = ttk.Label(
            self.preview_view,
            text="Podgląd dokumentu"
        )
        self.preview_info.pack(
            anchor="w",
            padx=22,
            pady=5
        )

        content = ttk.Frame(
            self.preview_view,
            padding=(20, 10)
        )
        content.pack(
            fill="both",
            expand=True
        )

        left = ttk.LabelFrame(
            content,
            text="Podgląd strony PDF – skala szarości",
            padding=10
        )
        left.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )

        self.preview_placeholder = tk.Label(
            left,
            text="Tutaj pojawi się podgląd separacji PDF",
            background="#e5e5e5",
            foreground="#333333",
            font=("Segoe UI", 14)
        )
        self.preview_placeholder.pack(
            fill="both",
            expand=True
        )

        right = ttk.LabelFrame(
            content,
            text="Separacje CMYK / Pantone",
            padding=10
        )
        right.pack(
            side="right",
            fill="y"
        )

        self.preview_channels = tk.Listbox(
            right,
            width=30,
            font=("Segoe UI", 11),
            selectmode=tk.EXTENDED
        )
        self.preview_channels.pack(
            fill="both",
            expand=True
        )

        for channel in (
            "Cyan (C)",
            "Magenta (M)",
            "Yellow (Y)",
            "Black (K)"
        ):
            self.preview_channels.insert("end", channel)

        self.preview_channels.insert(
            "end",
            "Pantone / Spot – po analizie"
        )

        self.preview_channels.configure(
            state="disabled"
        )

    def show_documents_view(self):

        self.preview_view.pack_forget()

        self.documents_view.pack(
            fill="both",
            expand=True
        )

    def show_separations_view(self):

        self.documents_view.pack_forget()

        self.preview_view.pack(
            fill="both",
            expand=True
        )

    def _create_documents_view(self):

        main = ttk.Frame(self.documents_view, padding=22)
        main.pack(fill="both", expand=True)

        # Nagłówek
        ttk.Label(
            main,
            text="separatorPDF",
            style="Title.TLabel"
        ).pack(anchor="w")

        ttk.Label(
            main,
            text="Kontrola i analiza separacji kolorystycznych PDF",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(2, 15))

        ttk.Separator(main).pack(fill="x", pady=(0, 15))

        # Dokumenty PDF
        ttk.Label(
            main,
            text="DOKUMENTY PDF",
            style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=(0, 8))

        ttk.Button(
            buttons,
            text="Dodaj pliki PDF",
            command=self.add_files,
            style="Action.TButton"
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Wybierz folder",
            command=self.add_folder,
            style="Action.TButton"
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="Usuń zaznaczone",
            command=self.remove_selected
        ).pack(side="right")

        list_frame = ttk.Frame(main)
        list_frame.pack(fill="both", expand=True)

        self.file_list = tk.Listbox(
            list_frame,
            font=("Segoe UI", 10),
            selectmode=tk.EXTENDED,
            activestyle="none",
            relief="solid",
            borderwidth=1,
            background="white",
            height=7
        )

        self.file_list.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.file_list.yview
        )
        scrollbar.pack(side="right", fill="y")

        self.file_list.configure(
            yscrollcommand=scrollbar.set
        )

        # Tryb analizy
        ttk.Label(
            main,
            text="TRYB ANALIZY",
            style="Section.TLabel"
        ).pack(anchor="w", pady=(15, 7))

        modes = ttk.Frame(main)
        modes.pack(fill="x")

        ttk.Radiobutton(
            modes,
            text="A – Analizuj oryginalny PDF",
            variable=self.mode,
            value="A",
            command=self.update_mode_description
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            modes,
            text="B – Analizuj po korekcie zgodności",
            variable=self.mode,
            value="B",
            command=self.update_mode_description
        ).pack(anchor="w", pady=2)

        self.mode_description = ttk.Label(
            main,
            text="",
            wraplength=900,
            foreground="#657587",
            justify="left"
        )
        self.mode_description.pack(
            anchor="w",
            pady=(5, 5)
        )

        ttk.Button(
            main,
            text="Co oznacza korekta zgodności?",
            command=self.show_help
        ).pack(anchor="w", pady=(0, 12))

        # Wybór separacji
        ttk.Separator(main).pack(fill="x", pady=(3, 12))

        ttk.Label(
            main,
            text="WYBÓR SEPARACJI",
            style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 10))

        separation_frame = ttk.Frame(main)
        separation_frame.pack(fill="x")

        # CMYK
        cmyk_frame = ttk.LabelFrame(
            separation_frame,
            text="Kolory procesowe CMYK",
            padding=10
        )
        cmyk_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8)
        )

        cmyk_items = [
            ("Cyan", "Cyan (C)", "#00A6D6"),
            ("Magenta", "Magenta (M)", "#E6007E"),
            ("Yellow", "Yellow (Y)", "#E5C900"),
            ("Black", "Black (K)", "#222222")
        ]

        for key, label, color in cmyk_items:
            line = ttk.Frame(cmyk_frame)
            line.pack(anchor="w", pady=4)

            color_box = tk.Label(
                line,
                background=color,
                width=2,
                height=1,
                relief="solid",
                borderwidth=1
            )
            color_box.pack(side="left", padx=(0, 7))

            ttk.Checkbutton(
                line,
                text=label,
                variable=self.cmyk_vars[key]
            ).pack(side="left")

        # Pantone / Spot
        spot_frame = ttk.LabelFrame(
            separation_frame,
            text="Kolory dodatkowe Pantone / Spot",
            padding=10
        )
        spot_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(8, 0)
        )

        self.spot_list = tk.Listbox(
            spot_frame,
            font=("Segoe UI", 10),
            selectmode=tk.EXTENDED,
            height=6,
            relief="solid",
            borderwidth=1,
            background="white"
        )
        self.spot_list.pack(fill="both", expand=True)

        self.spot_list.insert(
            "end",
            "Kolory pojawią się po analizie PDF."
        )
        self.spot_list.configure(state="disabled")

        ttk.Label(
            spot_frame,
            text="Lista zostanie wypełniona automatycznie.",
            foreground="#657587",
            wraplength=350
        ).pack(anchor="w", pady=(7, 0))

        # Zaznaczanie kolorów
        selection_buttons = ttk.Frame(main)
        selection_buttons.pack(fill="x", pady=(10, 10))

        ttk.Button(
            selection_buttons,
            text="Zaznacz wszystkie CMYK",
            command=self.select_all_cmyk
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            selection_buttons,
            text="Odznacz wszystkie CMYK",
            command=self.deselect_all_cmyk
        ).pack(side="left")

        self.update_mode_description()

        # Dolny pasek
        ttk.Separator(main).pack(fill="x", pady=(5, 12))

        bottom = ttk.Frame(main)
        bottom.pack(fill="x")

        self.status = ttk.Label(
            bottom,
            text="Dodaj dokumenty PDF, aby rozpocząć."
        )
        self.status.pack(side="left")

        self.start_button = ttk.Button(
            bottom,
            text="Rozpocznij analizę",
            command=self.start_processing,
            style="Action.TButton",
            state="disabled"
        )
        self.start_button.pack(side="right")

    def show_help(self):

        help_window = tk.Toplevel(self.root)
        help_window.title("Korekta zgodności – pomoc")

        help_width = 720
        help_height = 720

        self.center_window(
            help_window,
            help_width,
            help_height
        )

        help_window.minsize(620, 550)
        help_window.resizable(True, True)
        help_window.transient(self.root)

        help_window.state("normal")
        help_window.deiconify()
        help_window.lift()

        container = ttk.Frame(
            help_window,
            padding=22
        )
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Co oznacza korekta zgodności?",
            font=("Segoe UI", 16, "bold"),
            foreground="#183653"
        ).pack(anchor="w", pady=(0, 15))

        text_frame = ttk.Frame(container)
        text_frame.pack(fill="both", expand=True)

        help_text = tk.Text(
            text_frame,
            wrap="word",
            font=("Segoe UI", 12),
            relief="flat",
            borderwidth=0,
            padx=8,
            pady=8,
            background=help_window.cget("background"),
            spacing1=3,
            spacing3=7,
            cursor="arrow"
        )

        scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=help_text.yview
        )

        help_text.configure(
            yscrollcommand=scrollbar.set
        )

        scrollbar.pack(side="right", fill="y")
        help_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        help_text.tag_configure(
            "heading",
            font=("Segoe UI", 13, "bold"),
            foreground="#183653",
            spacing1=12,
            spacing3=5
        )

        help_text.tag_configure(
            "normal",
            font=("Segoe UI", 12)
        )

        sections = [
            (
                "heading",
                "Czym jest nadruk (overprint)?\n"
            ),
            (
                "normal",
                "W dokumencie PDF elementy mogą mieć ustawioną "
                "właściwość nadruku. Oznacza to, że kolor danego "
                "elementu jest drukowany na kolorach znajdujących "
                "się pod nim, zamiast powodować ich całkowite "
                "wybicie (wycięcie).\n\n"
                "Nadruk jest normalnym i często celowo stosowanym "
                "mechanizmem w przygotowaniu publikacji do druku.\n\n"
            ),
            (
                "heading",
                "Dlaczego potrzebna jest korekta zgodności?\n"
            ),
            (
                "normal",
                "Dokumenty PDF mogą zawierać różne kombinacje "
                "ustawień nadruku i trybów ich interpretacji. "
                "W określonych przypadkach sposób zapisania tych "
                "ustawień może prowadzić do różnic w interpretacji "
                "kolorów i wyglądzie separacji.\n\n"
                "Korekta zgodności ma na celu dostosowanie "
                "wybranych ustawień, aby uzyskać bardziej "
                "przewidywalny wynik analizy i podglądu.\n\n"
            ),
            (
                "heading",
                "Na czym polega działanie separatorPDF?\n"
            ),
            (
                "normal",
                "Program analizuje rzeczywiste właściwości "
                "elementów dokumentu PDF. W trybie B wykonuje "
                "selektywną korektę tylko tych przypadków, które "
                "spełniają warunki przewidziane przez mechanizm "
                "korekty.\n\n"
                "Nie oznacza to automatycznego usuwania wszystkich "
                "ustawień nadruku. W wielu dokumentach korekta "
                "nie będzie potrzebna.\n\n"
            ),
            (
                "heading",
                "Czy oryginalny dokument zostanie zmieniony?\n"
            ),
            (
                "normal",
                "Nie. Dokument źródłowy pozostaje bez zmian. "
                "Wynik pracy w trybie korekty jest przeznaczony "
                "do dalszej analizy i podglądu.\n\n"
            ),
            (
                "heading",
                "Który tryb wybrać?\n"
            ),
            (
                "normal",
                "A – Analizuj oryginalny PDF:\n"
                "Kontrola i podgląd dokumentu bez wprowadzania "
                "korekty.\n\n"
                "B – Analizuj po korekcie zgodności:\n"
                "Kontrola i podgląd dokumentu po zastosowaniu "
                "selektywnej korekty ustawień nadruku.\n"
            )
        ]

        for tag, content in sections:
            help_text.insert("end", content, tag)

        help_text.configure(state="disabled")

        ttk.Button(
            container,
            text="Zamknij",
            command=help_window.destroy
        ).pack(anchor="e", pady=(12, 0))

        help_window.focus_set()

    def select_all_cmyk(self):

        for variable in self.cmyk_vars.values():
            variable.set(True)

    def deselect_all_cmyk(self):

        for variable in self.cmyk_vars.values():
            variable.set(False)

    def add_files(self):

        paths = filedialog.askopenfilenames(
            title="Wybierz dokumenty PDF",
            filetypes=[("Dokumenty PDF", "*.pdf")],
            parent=self.root
        )

        self.add_paths(paths)

    def add_folder(self):

        folder = filedialog.askdirectory(
            title="Wybierz folder z dokumentami PDF",
            parent=self.root
        )

        if not folder:
            return

        try:
            paths = sorted(
                str(path)
                for path in Path(folder).iterdir()
                if path.is_file()
                and path.suffix.lower() == ".pdf"
            )

        except OSError as error:

            messagebox.showerror(
                "Błąd odczytu folderu",
                str(error),
                parent=self.root
            )
            return

        self.add_paths(paths)

    def add_paths(self, paths):

        added = 0

        for path in paths:

            normalized = str(Path(path).resolve())

            if normalized not in self.files:

                self.files.append(normalized)

                self.file_list.insert(
                    "end",
                    Path(normalized).name
                )

                added += 1

        self.update_status()

        if added == 0 and paths:

            messagebox.showinfo(
                "separatorPDF",
                "Wybrane dokumenty są już na liście.",
                parent=self.root
            )

    def remove_selected(self):

        selected = list(
            self.file_list.curselection()
        )

        for index in reversed(selected):

            self.file_list.delete(index)
            del self.files[index]

        self.update_status()

    def update_status(self):

        count = len(self.files)

        self.status.config(
            text=f"Dokumenty na liście: {count}"
        )

        self.start_button.config(
            state="normal" if count else "disabled"
        )

    def update_mode_description(self):

        if self.mode.get() == "A":

            description = (
                "Kontrola i podgląd oryginalnego dokumentu PDF. "
                "Bez wprowadzania korekty ustawień nadruku."
            )

        else:

            description = (
                "Kontrola i podgląd dokumentu po selektywnej "
                "korekcie wybranych ustawień nadruku. "
                "Oryginał pozostaje bez zmian."
            )

        self.mode_description.config(
            text=description
        )

    def start_processing(self):

        if not self.files:
            return

        self.preview_info.config(
            text=(
                f"Wybrano dokumentów: {len(self.files)}. "
                "Podgląd separacji zostanie podłączony "
                "w kolejnym etapie."
            )
        )

        self.show_separations_view()


def main():

    root = tk.Tk()

    app = SeparatorPDFApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
