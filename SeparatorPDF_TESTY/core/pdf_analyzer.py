
import pikepdf


DRAW_OPERATORS = {
    "f", "F", "f*", "S", "s",
    "B", "B*", "b", "b*",
    "Do", "Tj", "TJ", "'", '"',
}


FILL_OPERATORS = {"f", "F", "f*"}
STROKE_OPERATORS = {"S", "s"}
BOTH_OPERATORS = {"B", "B*", "b", "b*"}


def _initial_state():
    return {
        "OP": False,
        "op": False,
        "OPM": 0,
        "fill_space": None,
        "stroke_space": None,
        "fill_color": None,
        "stroke_color": None,
        "text_rendering_mode": 0,
    }

def _effective_state(ext_gstate, previous):
    op = ext_gstate.get("/OP", previous["OP"])
    op_small = ext_gstate.get("/op", op)
    opm = ext_gstate.get("/OPM", previous["OPM"])

    return {
        **previous,
        "OP": bool(op),
        "op": bool(op_small),
        "OPM": int(opm),
    }


def _object_identity(obj):
    try:
        objgen = tuple(obj.objgen)
        if objgen != (0, 0):
            return objgen
    except (AttributeError, TypeError):
        pass

    return id(obj)


def _get_resources(obj, inherited):
    resources = obj.get("/Resources")

    if resources is None:
        return inherited

    return resources


def _analyze_stream(
    stream,
    resources,
    initial_state,
    path,
    recursion_stack,
):
    state = initial_state.copy()
    stack = []
    results = []

    ext_states = resources.get("/ExtGState", {})
    xobjects = resources.get("/XObject", {})

    instructions = pikepdf.parse_content_stream(stream)

    for index, instruction in enumerate(instructions):
        operator = str(instruction.operator)
        operands = instruction.operands

        if operator == "q":
            stack.append(state.copy())
            continue

        if operator == "Q":
            if not stack:
                raise ValueError(
                    f"Unmatched Q at {path}, instruction {index}"
                )

            state = stack.pop()
            continue

        if operator == "gs":
            name = str(operands[0])
            ext_gstate = ext_states.get(name)

            if ext_gstate is None:
                raise ValueError(
                    f"Missing ExtGState {name} at {path}"
                )

            state = _effective_state(ext_gstate, state)

        elif operator == "k":
            state["fill_space"] = "DeviceCMYK"
            state["fill_color"] = tuple(operands)

        elif operator == "K":
            state["stroke_space"] = "DeviceCMYK"
            state["stroke_color"] = tuple(operands)

        elif operator == "cs":
            state["fill_space"] = str(operands[0])
            state["fill_color"] = None

        elif operator == "CS":
            state["stroke_space"] = str(operands[0])
            state["stroke_color"] = None

        elif operator in ("sc", "scn"):
            state["fill_color"] = tuple(operands)

        elif operator in ("SC", "SCN"):
            state["stroke_color"] = tuple(operands)

        elif operator == "Tr":
            state["text_rendering_mode"] = int(operands[0])

        if operator in DRAW_OPERATORS:
            results.append({
                "index": index,
                "operator": operator,
                "operands": list(operands),
                "state": state.copy(),
                "path": path,
            })

        if operator == "Do":
            name = str(operands[0])
            xobject = xobjects.get(name)

            if xobject is None:
                raise ValueError(
                    f"Missing XObject {name} at {path}"
                )

            subtype = str(xobject.get("/Subtype", ""))

            if subtype != "/Form":
                continue

            identity = _object_identity(xobject)

            if identity in recursion_stack:
                raise ValueError(
                    f"Cyclic Form XObject reference: {name}"
                )

            child_resources = _get_resources(
                xobject,
                resources,
            )

            child_path = path + (name,)

            child_results = _analyze_stream(
                stream=xobject,
                resources=child_resources,
                initial_state=state,
                path=child_path,
                recursion_stack=recursion_stack | {identity},
            )

            results.extend(child_results)

    if stack:
        raise ValueError(
            f"Unclosed graphics state q at {path}"
        )

    return results


def analyze_page(page):
    """
    Analyze page content and recursively inspect Form XObjects.

    Does not modify the PDF.
    """

    resources = page.Resources

    initial_state = _initial_state()

    return _analyze_stream(
        stream=page,
        resources=resources,
        initial_state=initial_state,
        path=(),
        recursion_stack=set(),
    )


def needs_overprint_correction(item):
    """
    Detect CMYK fill/stroke objects potentially requiring
    an OPM 0 -> OPM 1 prepress correction.
    """

    state = item["state"]
    operator = item["operator"]

    checks = []

    if operator in FILL_OPERATORS or operator in BOTH_OPERATORS:
        checks.append((
            state["op"],
            state["fill_space"],
            state["fill_color"],
        ))

    if operator in STROKE_OPERATORS or operator in BOTH_OPERATORS:
        checks.append((
            state["OP"],
            state["stroke_space"],
            state["stroke_color"],
        ))

    if operator in {"Tj", "TJ", "'", '"'}:
        mode = state["text_rendering_mode"]

        if mode in {0, 2, 4, 6}:
            checks.append((
                state["op"],
                state["fill_space"],
                state["fill_color"],
            ))

        if mode in {1, 2, 5, 6}:
            checks.append((
                state["OP"],
                state["stroke_space"],
                state["stroke_color"],
            ))

    for overprint, color_space, color in checks:

        if not overprint:
            continue

        if color_space != "DeviceCMYK":
            continue

        if color is None or len(color) != 4:
            continue

        if state["OPM"] != 0:
            continue

        if any(component == 0 for component in color):
            return True

    return False
