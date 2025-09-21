from typing import Dict, List, Tuple, overload, Union
from classifier import classify_items
from constants import AISLES


@overload
async def filter_and_group_items(
    items: list[str],
    store: str | None,
    is_grouped: bool,
    enable_llm: bool = True,
    return_mapping: bool = False,
) -> str: ...


@overload
async def filter_and_group_items(
    items: list[str],
    store: str | None,
    is_grouped: bool,
    enable_llm: bool = True,
    return_mapping: bool = True,
) -> Tuple[str, Dict[str, List[str]]]: ...


async def filter_and_group_items(
    items: list[str],
    store: str | None,
    is_grouped: bool,
    enable_llm: bool = True,
    return_mapping: bool = False,
) -> Union[str, Tuple[str, Dict[str, List[str]]]]:
    """
    If store is provided, filter items to only those from that store (prefix 'store: item').
    If is_grouped is True, group items by section.
    """
    items = [item.strip() for item in items if item.strip()]
    if store:
        prefix = store.lower() + ":"
        items = [i for i in items if i.lower().startswith(prefix)]
        if not items:
            raise ValueError(f"No items found for store '{store}'.")

    if not is_grouped:
        out_simple = "\n".join(f"- {item}" for item in items)
        return (out_simple, {}) if return_mapping else out_simple

    # First: parse any explicit "(Section)" suffixes you already support
    parsed: Dict[str, List[str]] = {}
    misc: List[str] = []
    for item in items:
        if "(" in item and item.endswith(")"):
            section = item[item.rfind("(") + 1 : -1].strip()
            name = item[: item.rfind("(")].strip()
            parsed.setdefault(section, []).append(name)
        else:
            misc.append(item)

    if enable_llm and misc:
        # Classify remaining items with LLM
        llm_out = await classify_items(misc)
        for row in llm_out["items"]:
            parsed.setdefault(row["section"], []).append(row["item"])
    lines: list[str] = []
    # Sort sections by order in AISLES constant
    aisle_order = list(AISLES.keys())
    sorted_sections = sorted(
        parsed.keys(),
        key=lambda s: aisle_order.index(s) if s in AISLES else len(AISLES),
    )
    for section in sorted_sections:
        lines.append(f"**{section}**")
        # remove prefix of store if present
        # e.g. "joes: joes O's" -> "joes O's"
        if store:
            prefix = store.lower() + ":"
            parsed[section] = [
                item[len(prefix) :].strip() if item.lower().startswith(prefix) else item
                for item in parsed[section]
            ]
        lines.extend(f"- {v}" for v in parsed[section])
        lines.append("")
    out_grouped = "\n".join(lines).strip()
    return (out_grouped, parsed) if return_mapping else out_grouped
