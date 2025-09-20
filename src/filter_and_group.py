import os
from typing import Dict, List
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)


async def filter_and_group_items(
    items: list[str], store: str | None, is_grouped: bool, enable_llm: bool = True
) -> str:
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
        return "\n".join(f"- {item}" for item in items)

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
        ai = await categorize_items(misc)
        for sec, vals in ai.items():
            parsed.setdefault(sec, []).extend(vals)
    elif misc:
        # Heuristic fallback only (no LLM)
        hb = heuristic_bucket(misc)
        for sec, vals in hb.items():
            parsed.setdefault(sec, []).extend(vals)

    lines: list[str] = []
    for section in sorted(parsed.keys()):
        lines.append(f"**{section}**")
        lines.extend(f"- {v}" for v in parsed[section])
        lines.append("")
    return "\n".join(lines).strip()
