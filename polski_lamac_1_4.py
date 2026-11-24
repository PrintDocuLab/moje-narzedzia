
# ========== POCZĄTEK CZĘŚCI 1/4 ==========

import re
import sys
import zipfile
import tkinter as tk
import xml.etree.ElementTree as ET

from pathlib import Path
from tkinter import filedialog, messagebox

import pyphen


# ==================================================
# POLSKI ŁAMACZ 1.4
# TXT + DOCX
# ==================================================

DIC = pyphen.Pyphen(lang="pl_PL")

SOFT_HYPHEN = "\u00ad"
NBSP = "\u00a0"

SINGLE_LETTER_WORDS = "aAiIoOuUwWzZ"

POLISH_UPPER = "A-ZĄĆĘŁŃÓŚŹŻ"
POLISH_LOWER = "a-ząćęłńóśźż"


# ==================================================
# KATALOG PROGRAMU
# ==================================================

if getattr(sys, "frozen", False):
    PROGRAM_DIR = Path(sys.executable).resolve().parent
else:
    PROGRAM_DIR = Path(__file__).resolve().parent

EXCLUDED_FILE = PROGRAM_DIR / "wykluczone.txt"


# ==================================================
# PRZESTRZENIE NAZW DOCX
# ==================================================

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("w", W)
ET.register_namespace(
    "r",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)

TEXT_TAG = f"{{{W}}}t"
PARAGRAPH_TAG = f"{{{W}}}p"


# ==================================================
# SKRÓTY I KRÓTKIE OZNACZENIA
# ==================================================

PROTECTED_ABBREVIATIONS = {

    "a", "i", "o", "w", "u", "z", "e",

    "kg", "m", "g", "l", "s", "%",
    "zł", "km", "mm", "ft", "yd",
    "cm", "oz", "pd", "gr", "ha", "t",
    "mies", "godz", "min", "sek",

    "inż.", "dr", "dr.", "doc.",
    "mgr", "mgr.", "prof.", "post.",
    "sierż.", "asp.", "kom.", "insp.",
    "szer.", "kpr.", "plut.", "chor.",
    "ppor.", "por.", "kpt.", "mjr",
    "mjr.", "ppłk.", "płk.", "gen.",

    "sir", "hab.", "red.", "przew.",
    "bp", "ks.", "o.", "oo.", "św.",

    "str.", "ryc.", "rys.", "tab.",
    "art.", "vol.", "nr", "tabl.",
    "rozdz.", "ss.", "s.", "t.", "z.",

    "mln", "mld", "tys.",
    "że", "ul.", "pl.", "al.",
    "ok.", "r.", "ur."
}

PROTECTED_ABBREVIATIONS = {
    item.casefold()
    for item in PROTECTED_ABBREVIATIONS
}


# ==================================================
# JEDNOSTKI
# ==================================================

UNITS = [
    "km/h", "mm", "cm", "km", "kg", "mg", "ml",
    "m²", "m³", "°C", "°F", "min", "sek",
    "mm²", "cm²", "m", "g", "l", "s", "h",
    "zł", "PLN", "EUR", "USD", "%", "‰",
    "ft", "yd", "oz", "pd", "gr", "ha", "t"
]

UNITS_PATTERN = "|".join(
    re.escape(unit)
    for unit in sorted(UNITS, key=len, reverse=True)
)


# ==================================================
# WCZYTYWANIE SŁÓW WYKLUCZONYCH
# ==================================================

def load_excluded_words():

    excluded = set()

    if not EXCLUDED_FILE.is_file():
        return excluded

    with EXCLUDED_FILE.open(
        "r",
        encoding="utf-8-sig"
    ) as file:

        for line in file:

            word = line.strip()

            if word and not word.startswith("#"):
                excluded.add(word.casefold())

    return excluded


# ==================================================
# DZIELENIE WYRAZÓW
# ==================================================

def divide_words(text, excluded_words):

    def split_word(match):

        word = match.group(0)
        normalized = word.casefold()

        if len(word) < 4:
            return word

        if word.isupper():
            return word

        if normalized in excluded_words:
            return word

        if normalized in PROTECTED_ABBREVIATIONS:
            return word

        return DIC.inserted(
            word,
            hyphen=SOFT_HYPHEN
        )

    return re.sub(
        r"[^\W\d_]+",
        split_word,
        text,
        flags=re.UNICODE
    )


# ==================================================
# OCHRONA SKRÓTÓW
# ==================================================

def protect_abbreviations(text):

    pattern = (
        r"(?<!\w)"
        r"([^\W\d_]+\.?)"
        r"[ \t]+"
        r"(?=[^\W\s])"
    )

    def replace_abbreviation(match):

        abbreviation = match.group(1)

        if abbreviation.casefold() in PROTECTED_ABBREVIATIONS:
            return abbreviation + NBSP

        return match.group(0)

    text = re.sub(
        pattern,
        replace_abbreviation,
        text,
        flags=re.UNICODE
    )

    pattern_numbers = (
        r"(?<!\w)"
        r"(\d+(?:[ \u00a0]\d{3})*(?:[,.]\d+)?)"
        r"[ \t]+"
        r"([^\W\d_]+\.?)"
        r"(?!\w)"
    )

    def replace_number(match):

        unit = match.group(2)

        if unit.casefold() in PROTECTED_ABBREVIATIONS:
            return match.group(1) + NBSP + unit

        return match.group(0)

    return re.sub(
        pattern_numbers,
        replace_number,
        text,
        flags=re.UNICODE
    )


# ==================================================
# KONIEC CZĘŚCI 1/4
# ==================================================

# ========== POCZĄTEK CZĘŚCI 2/4 ==========


# ==================================================
# WISZĄCE SPÓJNIKI I PRZYIMKI
# ==================================================

def protect_single_words(text):

    pattern = (
        r"(?<!\w)"
        r"([" + SINGLE_LETTER_WORDS + r"])"
        r" "
        r"(?=[^\W\d_])"
    )

    return re.sub(
        pattern,
        lambda m: m.group(1) + NBSP,
        text,
        flags=re.UNICODE
    )


# ==================================================
# INICJAŁY I NAZWISKA
# ==================================================

def protect_initials(text):

    pattern = (
        r"(?<!\w)"
        r"([" + POLISH_UPPER + r"]\.)"
        r"[ \t]+"
        r"(?=[" + POLISH_UPPER + r"]"
        r"(?:[" + POLISH_LOWER + r"]+|\.))"
    )

    return re.sub(
        pattern,
        lambda m: m.group(1) + NBSP,
        text
    )


# ==================================================
# LICZBY I JEDNOSTKI
# ==================================================

def protect_numbers_units(text):

    pattern = (
        r"(?<![\w])"
        r"(\d+(?:[ \u00a0]\d{3})*(?:[,.]\d+)?)"
        r"[ \t]+"
        r"(" + UNITS_PATTERN + r")"
        r"(?!\w)"
    )

    return re.sub(
        pattern,
        lambda m: m.group(1) + NBSP + m.group(2),
        text,
        flags=re.IGNORECASE
    )


# ==================================================
# GŁÓWNE PRZETWARZANIE TEKSTU
# ==================================================

def process_text(
    text,
    excluded_words,
    divide=True,
    conjunctions=True,
    initials=True,
    numbers=True
):

    if divide:
        text = divide_words(text, excluded_words)

    text = protect_abbreviations(text)

    if conjunctions:
        text = protect_single_words(text)

    if initials:
        text = protect_initials(text)

    if numbers:
        text = protect_numbers_units(text)

    return text


# ==================================================
# PLIK KONTROLNY
# ==================================================

def make_control_text(text):

    return (
        text
        .replace(SOFT_HYPHEN, "[SHY]")
        .replace(NBSP, "[NBSP]")
    )


# ==================================================
# LICZENIE ZNAKÓW
# ==================================================

def count_special_characters(text):

    soft_count = text.count(SOFT_HYPHEN)
    nbsp_count = text.count(NBSP)

    return soft_count, nbsp_count


# ==================================================
# KONIEC CZĘŚCI 2/4
# ==================================================

# ========== POCZĄTEK CZĘŚCI 3/4 ==========


# ==================================================
# ROZPROWADZANIE ZMIENIONEGO TEKSTU
# PO ORYGINALNYCH FRAGMENTACH DOCX
# ==================================================

def distribute_text(original, result, nodes):

    if not nodes:
        return

    lengths = [
        len(node.text or "")
        for node in nodes
    ]

    starts = []
    position = 0

    for length in lengths:
        starts.append(position)
        position += length

    outputs = ["" for _ in nodes]

    def node_index_at(position):

        if position >= len(original):
            return len(nodes) - 1

        for index, start in enumerate(starts):

            end = start + lengths[index]

            if start <= position < end:
                return index

        return len(nodes) - 1

    matcher = __import__("difflib").SequenceMatcher(
        None,
        original,
        result,
        autojunk=False
    )

    for operation, i1, i2, j1, j2 in matcher.get_opcodes():

        if operation == "equal":

            for offset in range(i2 - i1):

                index = node_index_at(i1 + offset)

                outputs[index] += result[j1 + offset]

        elif operation == "replace":

            replacement = result[j1:j2]

            if replacement:

                index = node_index_at(i1)
                outputs[index] += replacement

        elif operation == "insert":

            inserted = result[j1:j2]

            if inserted:

                index = node_index_at(i1)
                outputs[index] += inserted

        # Usunięte fragmenty nie są kopiowane.

    for node, value in zip(nodes, outputs):

        node.text = value

        if value and (
            value.startswith(" ")
            or value.endswith(" ")
            or "  " in value
        ):

            node.set(
                f"{{{XML}}}space",
                "preserve"
            )


# ==================================================
# DODATKOWE PRZESTRZENIE NAZW WORD
# ==================================================

def register_docx_namespaces():

    namespaces = {
        "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
        "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
        "w16": "http://schemas.microsoft.com/office/word/2018/wordml",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
        "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
        "v": "urn:schemas-microsoft-com:vml",
        "o": "urn:schemas-microsoft-com:office:office",
        "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
        "wpc": "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas",
        "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
        "wpi": "http://schemas.microsoft.com/office/word/2010/wordprocessingInk",
        "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    }

    for prefix, uri in namespaces.items():

        ET.register_namespace(prefix, uri)


# ==================================================
# PRZETWARZANIE AKAPITÓW DOCX
# ==================================================

def process_docx_xml(
    xml_data,
    excluded_words,
    divide,
    conjunctions,
    initials,
    numbers,
    control_lines
):

    root = ET.fromstring(xml_data)

    paragraphs = root.iter(PARAGRAPH_TAG)

    for paragraph in paragraphs:

        text_nodes = list(paragraph.iter(TEXT_TAG))

        if not text_nodes:
            continue

        original = "".join(
            node.text or ""
            for node in text_nodes
        )

        if not original:
            continue

        result = process_text(
            original,
            excluded_words,
            divide,
            conjunctions,
            initials,
            numbers
        )

        if result != original:

            distribute_text(
                original,
                result,
                text_nodes
            )

        control_lines.append(result)

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True
    )


# ==================================================
# SPRAWDZANIE STRUKTURY DOCX
# ==================================================

def check_docx(source):

    with zipfile.ZipFile(source, "r") as archive:

        names = archive.namelist()

        if "word/document.xml" not in names:

            raise ValueError(
                "Dokument nie zawiera word/document.xml."
            )

        bad_file = archive.testzip()

        if bad_file is not None:

            raise ValueError(
                "Uszkodzony element archiwum DOCX: "
                + bad_file
            )


# ==================================================
# KONIEC CZĘŚCI 3/4
# ==================================================

# ========== POCZĄTEK CZĘŚCI 4/4 ==========


# ==================================================
# OBSŁUGA PLIKÓW DOCX
# ==================================================

def process_docx(
    source,
    excluded_words,
    divide,
    conjunctions,
    initials,
    numbers,
    create_control
):

    check_docx(source)
    register_docx_namespaces()

    path = Path(source)

    output = path.with_name(
        path.stem + "_podzielony.docx"
    )

    control_lines = []
    processed_parts = 0

    document_parts = re.compile(
        r"word/(document|header\d*|footer\d*|"
        r"footnotes|endnotes|comments)\.xml"
    )

    with zipfile.ZipFile(source, "r") as original_zip:

        with zipfile.ZipFile(
            output,
            "w",
            compression=zipfile.ZIP_DEFLATED
        ) as result_zip:

            for item in original_zip.infolist():

                data = original_zip.read(item.filename)

                if document_parts.fullmatch(item.filename):

                    data = process_docx_xml(
                        data,
                        excluded_words,
                        divide,
                        conjunctions,
                        initials,
                        numbers,
                        control_lines
                    )

                    processed_parts += 1

                result_zip.writestr(item, data)

    if processed_parts == 0:

        raise ValueError(
            "Nie znaleziono elementów dokumentu Word."
        )

    control_path = None

    result_text = "\n".join(control_lines)

    if create_control:

        control_path = path.with_name(
            path.stem + "_kontrola.txt"
        )

        control_path.write_text(
            make_control_text(result_text),
            encoding="utf-8"
        )

    return output, control_path, result_text


# ==================================================
# OBSŁUGA PLIKÓW TXT
# ==================================================

def process_txt(
    source,
    excluded_words,
    divide,
    conjunctions,
    initials,
    numbers,
    create_control
):

    path = Path(source)

    text = path.read_text(
        encoding="utf-8-sig"
    )

    if not text:

        raise ValueError(
            "Wybrany plik jest pusty."
        )

    result = process_text(
        text,
        excluded_words,
        divide,
        conjunctions,
        initials,
        numbers
    )

    output = path.with_name(
        path.stem + "_podzielony.txt"
    )

    output.write_text(
        result,
        encoding="utf-8"
    )

    control_path = None

    if create_control:

        control_path = path.with_name(
            path.stem + "_kontrola.txt"
        )

        control_path.write_text(
            make_control_text(result),
            encoding="utf-8"
        )

    return output, control_path, result


# ==================================================
# PRZETWARZANIE WYBRANEGO PLIKU
# ==================================================

def process_file():

    source = filedialog.askopenfilename(
        title="Wybierz plik do przetworzenia",
        filetypes=[
            ("Dokumenty TXT i Word", "*.txt *.docx"),
            ("Pliki tekstowe", "*.txt"),
            ("Dokumenty Word", "*.docx"),
            ("Wszystkie pliki", "*.*")
        ]
    )

    if not source:
        return

    path = Path(source)

    if path.suffix.lower() not in (".txt", ".docx"):

        messagebox.showwarning(
            "Nieobsługiwany format",
            "Wybierz plik TXT lub DOCX."
        )

        return

    try:

        excluded_words = load_excluded_words()

        options = {
            "divide": divide_var.get(),
            "conjunctions": conjunction_var.get(),
            "initials": initials_var.get(),
            "numbers": numbers_var.get(),
            "create_control": control_var.get()
        }

        if path.suffix.lower() == ".txt":

            output, control_path, result = process_txt(
                source,
                excluded_words,
                **options
            )

        else:

            output, control_path, result = process_docx(
                source,
                excluded_words,
                **options
            )

        soft_count, nbsp_count = count_special_characters(
            result
        )

        info = (
            "Przetwarzanie zakończone!\n\n"
            f"Plik wynikowy:\n{output}\n\n"
            f"Miękkie łączniki U+00AD: {soft_count}\n"
            f"Spacje nierozdzielające U+00A0: {nbsp_count}\n\n"
            f"Plik wykluczeń:\n{EXCLUDED_FILE}\n"
            f"Wczytane wykluczenia: {len(excluded_words)}"
        )

        if not EXCLUDED_FILE.is_file():

            info += (
                "\n\nUWAGA: Nie znaleziono pliku wykluczone.txt!"
            )

        if control_path:

            info += (
                f"\n\nPlik kontrolny:\n{control_path}"
            )

        messagebox.showinfo(
            "Polski Łamacz 1.4",
            info
        )

    except UnicodeDecodeError:

        messagebox.showerror(
            "Błąd kodowania",
            "Plik TXT nie jest zapisany w UTF-8."
        )

    except zipfile.BadZipFile:

        messagebox.showerror(
            "Błędny dokument",
            "Plik DOCX jest uszkodzony lub nieprawidłowy."
        )

    except PermissionError:

        messagebox.showerror(
            "Brak dostępu",
            "Nie można zapisać pliku. "
            "Sprawdź, czy dokument nie jest otwarty w Wordzie."
        )

    except Exception as error:

        messagebox.showerror(
            "Błąd przetwarzania",
            str(error)
        )


# ==================================================
# INTERFEJS PROGRAMU
# ==================================================

root = tk.Tk()

root.title("Polski Łamacz 1.4")
root.geometry("530x480")
root.resizable(False, False)


tk.Label(
    root,
    text="POLSKI ŁAMACZ 1.4",
    font=("Arial", 18, "bold")
).pack(pady=(20, 4))


tk.Label(
    root,
    text="Przygotowanie tekstu do składu DTP",
    font=("Arial", 10)
).pack(pady=4)


tk.Label(
    root,
    text="Obsługa plików TXT i DOCX",
    font=("Arial", 9),
    fg="gray"
).pack(pady=4)


# ==================================================
# OPCJE PROGRAMU
# ==================================================

divide_var = tk.BooleanVar(value=True)
conjunction_var = tk.BooleanVar(value=True)
initials_var = tk.BooleanVar(value=True)
numbers_var = tk.BooleanVar(value=True)
control_var = tk.BooleanVar(value=True)


options = [
    (
        "Automatyczne dzielenie polskich wyrazów",
        divide_var
    ),
    (
        "Zabezpieczanie wiszących spójników i przyimków",
        conjunction_var
    ),
    (
        "Zabezpieczanie inicjałów i nazwisk",
        initials_var
    ),
    (
        "Zabezpieczanie liczb i jednostek",
        numbers_var
    ),
    (
        "Twórz plik kontrolny [SHY] / [NBSP]",
        control_var
    )
]


for label, variable in options:

    tk.Checkbutton(
        root,
        text=label,
        variable=variable,
        font=("Arial", 10)
    ).pack(
        anchor="w",
        padx=35,
        pady=6
    )


# ==================================================
# PRZYCISK
# ==================================================

tk.Button(
    root,
    text="PRZETWÓRZ",
    command=process_file,
    font=("Arial", 12, "bold"),
    width=24,
    height=2,
    bg="#dcebdc"
).pack(pady=24)


tk.Label(
    root,
    text="TXT / DOCX | Windows / Linux",
    font=("Arial", 8),
    fg="gray"
).pack()


# ==================================================
# URUCHOMIENIE PROGRAMU
# ==================================================

root.mainloop()


# ========== KONIEC CZĘŚCI 4/4 ==========
