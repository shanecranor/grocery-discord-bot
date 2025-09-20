import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY")
)


async def categorize_items(items: list[str]) -> dict[str, list[str]]:
    response = await client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": f"Categorize these items: {items}"}],
    )

    return response.choices[0].message.content


async def filter_and_group_items(
    items: list[str], store: str | None, is_grouped: bool, enable_llm: bool = True
) -> str:
    """
    If store is provided, filter items to only those from that store.
    If is_grouped is True, group items by section in the store.
    """
    items = [item.strip() for item in items if item.strip()]
    if store:
        items = [item for item in items if item.lower().startswith(store.lower() + ":")]
        if not items:
            raise ValueError(f"No items found for store '{store}'.")

    if not is_grouped:
        return "\n".join(f"- {item}" for item in items)

    categories: dict[str, list[str]] = {}
    for item in items:
        if "(" in item and item.endswith(")"):
            category = item[item.rfind("(") + 1 : -1].strip()
            item_name = item[: item.rfind("(")].strip()
        else:
            category = "Misc"
            item_name = item
        categories.setdefault(category, []).append(item_name)
    if enable_llm:
        # use llm to categorize items without a category
        uncategorized_items = categories.pop("Misc", [])
        if uncategorized_items:
            llm_categorized = await categorize_items(
                uncategorized_items, categories.keys(), store
            )
            for cat, cat_items in llm_categorized.items():
                categories.setdefault(cat, []).extend(cat_items)

    grouped_items: list[str] = []
    for category, section_items in categories.items():
        grouped_items.append(f"**{category}**")
        grouped_items.extend(f"- {itm}" for itm in section_items)
        grouped_items.append("")  # Add a blank line between sections
    return "\n".join(grouped_items).strip()
