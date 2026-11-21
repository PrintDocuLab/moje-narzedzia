
from pathlib import Path
import pikepdf

from .pdf_analyzer import analyze_page, needs_overprint_correction


TEXT_OPERATORS = {"Tj", "TJ", "'", '"'}
FILL = {"f", "F", "f*"}
STROKE = {"S", "s"}
BOTH = {"B", "B*", "b", "b*"}
PAINT = FILL | STROKE | BOTH


def _instruction(operator, operands=None):
    return pikepdf.ContentStreamInstruction(
        operands or [],
        pikepdf.Operator(operator),
    )


def _object_identity(obj):
    try:
        objgen = tuple(obj.objgen)
        if objgen != (0, 0):
            return objgen
    except (AttributeError, TypeError):
        pass

    return id(obj)


def _vector_qualifies(item):
    state = item["state"]
    operator = item["operator"]

    checks = []

    if operator in FILL | BOTH:
        checks.append((
            state["op"],
            state["fill_space"],
            state["fill_color"],
        ))

    if operator in STROKE | BOTH:
        checks.append((
            state["OP"],
            state["stroke_space"],
            state["stroke_color"],
        ))

    active = [c for c in checks if c[0]]

    if not active:
        return False

    return all(
        state["OPM"] == 0
        and space == "DeviceCMYK"
        and color is not None
        and len(color) == 4
        and any(component == 0 for component in color)
        for _, space, color in active
    )


def _qualified_text_blocks(instructions, analysis, path):
    by_index = {
        item["index"]: item
        for item in analysis
        if item["path"] == path
        and item["operator"] in TEXT_OPERATORS
    }

    blocks = []
    start = None
    text_indices = []
    has_internal_gs = False

    for index, instruction in enumerate(instructions):
        operator = str(instruction.operator)

        if operator == "BT":
            start = index
            text_indices = []
            has_internal_gs = False

        elif start is not None:
            if operator == "gs":
                has_internal_gs = True

            elif operator in TEXT_OPERATORS:
                text_indices.append(index)

            elif operator == "ET":
                if text_indices and not has_internal_gs:
                    if all(
                        i in by_index
                        and needs_overprint_correction(by_index[i])
                        for i in text_indices
                    ):
                        blocks.append((start, index))

                start = None
                text_indices = []
                has_internal_gs = False

    return blocks


def _new_extgstate(resources):
    new_resources = pikepdf.Dictionary(
        {key: value for key, value in resources.items()}
    )

    ext_states = resources.get(
        "/ExtGState",
        pikepdf.Dictionary(),
    )

    new_ext_states = pikepdf.Dictionary(
        {key: value for key, value in ext_states.items()}
    )

    name = "/SeparatorPDF_OPM1"
    suffix = 1

    while name in new_ext_states:
        suffix += 1
        name = f"/SeparatorPDF_OPM1_{suffix}"

    new_ext_states[name] = pikepdf.Dictionary({
        "/Type": pikepdf.Name("/ExtGState"),
        "/OPM": 1,
    })

    new_resources["/ExtGState"] = new_ext_states

    return new_resources, name


def _transform_stream(
    pdf,
    stream,
    owner,
    resources,
    analysis,
    path,
    is_page=False,
):
    instructions = pikepdf.parse_content_stream(stream)

    text_blocks = _qualified_text_blocks(
        instructions,
        analysis,
        path,
    )

    vector_indices = {
        item["index"]
        for item in analysis
        if item["path"] == path
        and item["operator"] in PAINT
        and _vector_qualifies(item)
    }

    if not text_blocks and not vector_indices:
        return 0, 0, resources

    new_resources, gs_name = _new_extgstate(resources)

    owner["/Resources"] = new_resources

    starts = {start for start, end in text_blocks}
    ends = {end for start, end in text_blocks}

    output = []

    for index, instruction in enumerate(instructions):

        if index in starts:
            output.append(_instruction("q"))
            output.append(_instruction(
                "gs",
                [pikepdf.Name(gs_name)],
            ))

        if index in vector_indices:
            output.append(_instruction("q"))
            output.append(_instruction(
                "gs",
                [pikepdf.Name(gs_name)],
            ))

        output.append(instruction)

        if index in vector_indices:
            output.append(_instruction("Q"))

        if index in ends:
            output.append(_instruction("Q"))

    data = pikepdf.unparse_content_stream(output)

    if is_page:
        owner["/Contents"] = pdf.make_stream(data)
    else:
        stream.write(data)

    return len(text_blocks), len(vector_indices), new_resources


def _transform_forms(
    pdf,
    resources,
    analysis,
    parent_path,
    recursion_stack,
    processed,
):
    corrected_text = 0
    corrected_vector = 0

    xobjects = resources.get("/XObject", {})

    for name, xobject in xobjects.items():

        if str(xobject.get("/Subtype", "")) != "/Form":
            continue

        identity = _object_identity(xobject)

        if identity in recursion_stack:
            raise ValueError(
                f"Cyclic Form XObject reference: {name}"
            )

        if identity in processed:
            continue

        processed.add(identity)

        path = parent_path + (str(name),)

        # Form może korzystać z zasobów odziedziczonych.
        child_resources = xobject.get("/Resources")

        if child_resources is None:
            child_resources = resources

        text_count, vector_count, effective_resources = (
            _transform_stream(
                pdf=pdf,
                stream=xobject,
                owner=xobject,
                resources=child_resources,
                analysis=analysis,
                path=path,
            )
        )

        corrected_text += text_count
        corrected_vector += vector_count

        # Rekurencyjne wejście do kolejnych Form XObjects.
        child_text, child_vector = _transform_forms(
            pdf=pdf,
            resources=effective_resources,
            analysis=analysis,
            parent_path=path,
            recursion_stack=recursion_stack | {identity},
            processed=processed,
        )

        corrected_text += child_text
        corrected_vector += child_vector

    return corrected_text, corrected_vector


def transform_pdf(input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)

    if input_path.resolve() == output_path.resolve():
        raise ValueError(
            "Output musi być innym plikiem niż input."
        )

    corrected_text = 0
    corrected_vector = 0
    corrected_form_text = 0
    corrected_form_vector = 0

    with pikepdf.open(str(input_path)) as pdf:

        for page_number, page in enumerate(pdf.pages, 1):

            analysis = analyze_page(page)
            page_resources = page.Resources

            # Obiekty bezpośrednio na stronie.
            text_count, vector_count, effective_resources = (
                _transform_stream(
                    pdf=pdf,
                    stream=page,
                    owner=page.obj,
                    resources=page_resources,
                    analysis=analysis,
                    path=(),
                    is_page=True,
                )
            )

            corrected_text += text_count
            corrected_vector += vector_count

            # Wszystkie Form XObjects, rekurencyjnie.
            form_text, form_vector = _transform_forms(
                pdf=pdf,
                resources=effective_resources,
                analysis=analysis,
                parent_path=(),
                recursion_stack=set(),
                processed=set(),
            )

            corrected_form_text += form_text
            corrected_form_vector += form_vector

            print(
                f"Strona {page_number}: "
                f"tekst={text_count}, "
                f"wektory={vector_count}, "
                f"Form tekst={form_text}, "
                f"Form wektory={form_vector}"
            )

        pdf.save(str(output_path))

    total = (
        corrected_text
        + corrected_vector
        + corrected_form_text
        + corrected_form_vector
    )

    print("\n========== RAPORT separatorPDF ==========")
    print("Tekst na stronach:", corrected_text)
    print("Wektory na stronach:", corrected_vector)
    print("Tekst w Form XObjects:", corrected_form_text)
    print("Wektory w Form XObjects:", corrected_form_vector)
    print("Łączna liczba korekt:", total)

    return total
