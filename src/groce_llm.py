import os
from typing import Dict, List, Any
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import RootModel, ValidationError

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)


# ---------- Schema (model must output this EXACT shape) ----------
class Categories(RootModel[Dict[str, List[str]]]):
    """Root model holding mapping: section -> list of item strings."""


JSON_SCHEMA: Dict[str, Any] = {
    "name": "GroceryCategories",
    "schema": {
        "type": "object",
        "additionalProperties": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "strict": True,  # disallow extra keys/types
}

SYSTEM_RULES = """You are a grocery categorizer.
Return ONLY JSON that matches the schema: { section: string[] }.
- Sections should be typical store areas like: Produce, Meat, Dairy, Frozen, Pantry, Bakery, Deli, Beverages, Household, Pharmacy, Misc.
- Keep item names verbatim from input, do not invent.
- If unsure, put in 'Misc'. No explanations, no markdown, no trailing text."""

# ---------- Light heuristic as a safety net ----------
KEYWORDS = [
    ("Produce", ["apple", "banana", "lettuce", "tomato", "onion", "cilantro", "lime"]),
    ("Meat", ["chicken", "beef", "pork", "turkey", "salmon"]),
    ("Dairy", ["milk", "cheese", "yogurt", "butter", "cream"]),
    ("Bakery", ["bread", "bagel", "bun", "tortilla"]),
    ("Frozen", ["frozen", "ice cream", "peas"]),
    ("Pantry", ["rice", "pasta", "beans", "flour", "sugar", "salt", "oil", "spice"]),
    ("Beverages", ["coffee", "tea", "soda", "juice", "water"]),
    ("Household", ["detergent", "foil", "paper", "towel", "trash"]),
    ("Pharmacy", ["ibuprofen", "acetaminophen", "vitamin"]),
]


def heuristic_bucket(items: list[str]) -> Dict[str, List[str]]:
    buckets: Dict[str, List[str]] = {}
    for raw in items:
        s = raw.strip()
        low = s.lower()
        placed = False
        for section, words in KEYWORDS:
            if any(w in low for w in words):
                buckets.setdefault(section, []).append(s)
                placed = True
                break
        if not placed:
            buckets.setdefault("Misc", []).append(s)
    return buckets


# ---------- LLM categorization (strict JSON) ----------
async def categorize_items(items: list[str]) -> Dict[str, List[str]]:
    # Guard: strip empties
    items = [i.strip() for i in items if i and i.strip()]
    if not items:
        return {}

    # Ask the model to output EXACT JSON per schema
    print("Categorizing items with LLM:", items)
    resp = await client.chat.completions.create(
        model="openai/gpt-5-mini",  # supports structured outputs & tool calls on OpenRouter
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_RULES},
            {
                "role": "user",
                "content": f"Categorize these grocery items into store sections: {items}",
            },
        ],
        response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},  # type: ignore[arg-type]
        # Optional: set a seed if the model supports it for determinism
        # "seed": 7,
    )

    raw = resp.choices[0].message.content or "{}"
    print("Raw LLM response:", raw)
    # Validate with Pydantic for ironclad safety
    try:
        model_obj = Categories.model_validate_json(raw)
    except ValidationError:
        print("LLM response failed validation, falling back to heuristic.")
        # Single repair attempt: fall back to heuristic, then keep model’s sections for the rest
        return heuristic_bucket(items)
    else:
        return model_obj.root


# ---------- Your grouping function, with optional LLM assist ----------
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
