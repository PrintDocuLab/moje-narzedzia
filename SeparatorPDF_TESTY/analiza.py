
import pikepdf

pdf = pikepdf.open("over_test.pdf")

for i, page in enumerate(pdf.pages):
    print(f"\n=== STRONA {i+1} ===")

    resources = page.get("/Resources")

    if resources and "/ExtGState" in resources:
        print("\n=== EXTGSTATE ===")
        for name, obj in resources["/ExtGState"].items():
            print(name, obj)

    print("\n=== CONTENT STREAM ===")

    contents = page.get("/Contents")

    if isinstance(contents, pikepdf.Array):
        for stream in contents:
            print(stream.read_bytes().decode("latin-1"))
    else:
        print(contents.read_bytes().decode("latin-1"))

pdf.close()
