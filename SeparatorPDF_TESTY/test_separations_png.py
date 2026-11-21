
import os
import re
import ctypes
import numpy as np
from PIL import Image
from pymupdf import mupdf


# ==========================================
# KONFIGURACJA
# ==========================================

PDF = "over_test.pdf"
OUTPUT_DIR = "output/separations_test"
DPI = 150

CHANNEL_NAMES = [
    "Cyan",
    "Magenta",
    "Yellow",
    "Black"
]


# ==========================================
# PRZYGOTOWANIE
# ==========================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

doc = mupdf.fz_open_document(PDF)

page_count = mupdf.fz_count_pages(doc)

zoom = DPI / 72.0
ctm = mupdf.fz_scale(zoom, zoom)
cmyk = mupdf.fz_device_cmyk()

print("======================================")
print("TEST SEPARACJI PDF")
print("======================================")
print("Plik:", PDF)
print("Strony:", page_count)
print("DPI:", DPI)


# ==========================================
# PRZETWARZANIE STRON
# ==========================================

for page_num in range(page_count):

    page = mupdf.fz_load_page(doc, page_num)

    seps = mupdf.fz_page_separations(page)

    spot_names = []

    print("\n--------------------------------------")
    print("STRONA:", page_num + 1)
    print("--------------------------------------")

    # Wykrywanie kolorów dodatkowych

    if seps:

        spot_count = mupdf.fz_count_separations(seps)

        for i in range(spot_count):

            name = str(
                mupdf.fz_separation_name(seps, i)
            )

            spot_names.append(name)

            mupdf.fz_set_separation_behavior(
                seps,
                i,
                mupdf.FZ_SEPARATION_SPOT
            )

            print("Wykryto Spot:", name)

    else:

        spot_count = 0

        print("Brak kolorów Spot")

    # Renderowanie strony

    try:

        if spot_count > 0:

            pix = mupdf.fz_new_pixmap_from_page_with_separations(
                page,
                ctm,
                cmyk,
                seps,
                0
            )

        else:

            pix = mupdf.fz_new_pixmap_from_page(
                page,
                ctm,
                cmyk,
                0
            )

        width = pix.w()
        height = pix.h()
        channels = pix.n()
        stride = pix.stride()

        print("Renderowanie OK")
        print("Rozdzielczość:", width, "x", height)
        print("Kanały:", channels)

        # Odczyt pamięci MuPDF

        samples_ptr = mupdf.fz_pixmap_samples(pix)

        buffer_size = stride * height

        raw_bytes = (
            ctypes.c_ubyte * buffer_size
        ).from_address(int(samples_ptr))

        arr = np.frombuffer(
            raw_bytes,
            dtype=np.uint8
        )

        # Usunięcie ewentualnego paddingu

        arr = arr.reshape(height, stride)

        arr = arr[:, :width * channels]

        arr = arr.reshape(
            height,
            width,
            channels
        )

        # Nazwy kanałów

        names = CHANNEL_NAMES + spot_names

        # Zapisywanie osobnych płyt

        for ch in range(channels):

            if ch < len(names):

                name = names[ch]

            else:

                name = f"Channel_{ch + 1}"

            safe_name = re.sub(
                r'[<>:"/\\|?*]',
                "_",
                name
            )

            # 0% farby = biały
            # 100% farby = czarny

            gray = 255 - arr[:, :, ch]

            gray = np.ascontiguousarray(gray)

            output_file = os.path.join(
                OUTPUT_DIR,
                f"page_{page_num + 1}_{ch + 1}_{safe_name}.png"
            )

            image = Image.fromarray(
                gray,
                mode="L"
            )

            image.save(output_file)

            print("Zapisano:", output_file)

    except Exception as e:

        print("BŁĄD:", repr(e))


# ==========================================
# KONIEC
# ==========================================

print("\n======================================")
print("TEST SEPARACJI ZAKOŃCZONY")
print("Wyniki:", OUTPUT_DIR)
print("======================================")
