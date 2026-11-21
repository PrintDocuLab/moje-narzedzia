import os
import re
import ctypes

import numpy as np
from PIL import Image
from pymupdf import mupdf


CMYK_NAMES = ("Cyan", "Magenta", "Yellow", "Black")


def _safe_name(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", str(name))
    return name.strip(" .") or "Channel"


def _open_document(pdf_path):
    path = os.path.abspath(str(pdf_path))

    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    return mupdf.fz_open_document(path)


def _get_page_channels(page):
    seps = mupdf.fz_page_separations(page)
    spot_names = []

    if seps:
        count = mupdf.fz_count_separations(seps)

        for index in range(count):
            name = str(
                mupdf.fz_separation_name(seps, index)
            )

            spot_names.append(name)

            mupdf.fz_set_separation_behavior(
                seps,
                index,
                mupdf.FZ_SEPARATION_SPOT
            )

    return seps, list(CMYK_NAMES) + spot_names


def analyze_separations(pdf_path):
    """
    Zwraca informacje o separacjach dla każdej strony PDF.
    Nie zapisuje żadnych plików.
    """
    doc = _open_document(pdf_path)
    result = []

    page_count = mupdf.fz_count_pages(doc)

    for page_number in range(page_count):
        page = mupdf.fz_load_page(doc, page_number)

        try:
            seps, names = _get_page_channels(page)

            result.append({
                "page": page_number + 1,
                "channels": names,
                "cmyk": list(CMYK_NAMES),
                "spots": names[4:],
                "spot_count": len(names) - 4,
            })

        except Exception as exc:
            raise RuntimeError(
                f"Błąd analizy strony {page_number + 1}: {exc}"
            ) from exc

    return result


def _pixmap_to_array(pix):
    """
    Kopiuje dane pixmapy MuPDF do niezależnej tablicy NumPy.
    """
    width = pix.w()
    height = pix.h()
    channels = pix.n()
    stride = pix.stride()

    if width <= 0 or height <= 0 or channels <= 0:
        raise ValueError("Nieprawidłowe wymiary pixmapy.")

    samples_ptr = mupdf.fz_pixmap_samples(pix)

    buffer_size = stride * height

    raw = (
        ctypes.c_ubyte * buffer_size
    ).from_address(int(samples_ptr))

    data = bytes(raw)

    arr = np.frombuffer(
        data,
        dtype=np.uint8
    )

    arr = arr.reshape(height, stride)
    arr = arr[:, :width * channels]

    return arr.reshape(height, width, channels)


def render_separations(
    pdf_path,
    output_dir,
    dpi=150,
    selected_channels=None,
    page_indices=None,
    progress_callback=None
):
    """
    Renderuje osobne płyty CMYK i Spot do plików PNG.

    selected_channels:
        None = wszystkie kanały
        lista nazw = tylko wybrane kanały

    page_indices:
        None = wszystkie strony
        lista indeksów od zera = wybrane strony

    progress_callback:
        callback(page_number, page_count, channel_name)
    """

    if not isinstance(dpi, (int, float)) or dpi <= 0:
        raise ValueError("DPI musi być większe od zera.")

    output_dir = os.path.abspath(str(output_dir))
    os.makedirs(output_dir, exist_ok=True)

    doc = _open_document(pdf_path)
    page_count = mupdf.fz_count_pages(doc)

    if page_indices is None:
        pages = list(range(page_count))
    else:
        pages = sorted(set(int(p) for p in page_indices))

        if any(p < 0 or p >= page_count for p in pages):
            raise ValueError("Nieprawidłowy indeks strony PDF.")

    zoom = float(dpi) / 72.0
    ctm = mupdf.fz_scale(zoom, zoom)
    device = mupdf.fz_device_cmyk()

    saved_files = []
    errors = []

    for page_index in pages:
        page = mupdf.fz_load_page(doc, page_index)

        try:
            seps, names = _get_page_channels(page)

            if selected_channels is None:
                selected = set(names)
            else:
                selected = set(selected_channels)

            if seps:
                pix = mupdf.fz_new_pixmap_from_page_with_separations(
                    page,
                    ctm,
                    device,
                    seps,
                    0
                )
            else:
                pix = mupdf.fz_new_pixmap_from_page(
                    page,
                    ctm,
                    device,
                    0
                )

            arr = _pixmap_to_array(pix)

            if arr.shape[2] < 4:
                raise ValueError(
                    "Renderowanie CMYK zwróciło mniej niż 4 kanały."
                )

            if arr.shape[2] != len(names):
                raise ValueError(
                    "Niezgodna liczba kanałów: "
                    f"pixmapa={arr.shape[2]}, "
                    f"lista={len(names)}. "
                    "Przerwano zapis, aby nie przypisać "
                    "błędnych nazw separacjom."
                )

            for channel_index, channel_name in enumerate(names):

                if channel_name not in selected:
                    continue

                gray = 255 - arr[:, :, channel_index]
                gray = np.ascontiguousarray(gray)

                safe_name = _safe_name(channel_name)

                filename = (
                    f"page_{page_index + 1:03d}_"
                    f"{channel_index + 1:02d}_"
                    f"{safe_name}.png"
                )

                output_path = os.path.join(
                    output_dir,
                    filename
                )

                Image.fromarray(
                    gray,
                    mode="L"
                ).save(output_path)

                saved_files.append(output_path)

                if progress_callback is not None:
                    progress_callback(
                        page_index + 1,
                        page_count,
                        channel_name
                    )

        except Exception as exc:
            errors.append({
                "page": page_index + 1,
                "error": str(exc)
            })

    return {
        "files": saved_files,
        "errors": errors,
        "page_count": page_count,
        "saved_count": len(saved_files),
        "output_dir": output_dir,
    }
