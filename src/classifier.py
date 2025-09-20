import os
from typing import Dict, List
from dotenv import load_dotenv
from openai import AsyncOpenAI
import json

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
AISLES = {
    "Produce": "Fresh fruits and vegetables",
    "Bread/Bakery": "Baked goods and bread",
    "Meat": "Fresh meats and poultry",
    "Pasta": "Dried pasta, sauce, tomato paste, etc.",
    "Hispanic": "Tortillas, Salsas, beans, etc.",
    "International": "Foods from various non hispanic 'international' (from USA POV) cuisines including Asian, Indian, Middle Eastern, and more.",
    "Cereal": "Breakfast cereals and granola",
    "Dairy": "Milk, cheese, yogurt, and eggs",
    "Gluten-Free": "Gluten-free products and alternatives",
    "Beverages": "Drinks and beverages",
    "Canned Goods": "Canned fruits, vegetables, and soups",
    "Frozen Foods": "Frozen meals, vegetables, and desserts",
    "Alcohol": "Beer, wine, and spirits",
    "Pet Supplies": "Pet food and supplies",
    "Household": "Paper goods, cleaning supplies, and toiletries",
    "Misc": "Items that don't fit into other categories",
}
ALLOWED_AISLES = list(AISLES.keys())


async def classify_items(items: list[str]) -> Dict[str, List[Dict[str, str]]]:
    """
    Classify a list of grocery items into sections using the LLM with structured output.
    Returns a dict with an 'items' key containing a list of {'item': str, 'section': str} dicts.
    """
    aisle_variants = [
        {"const": name, "description": desc} for name, desc in AISLES.items()
    ]
    schema = {  # type: ignore
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item": {"type": "string"},
                        "section": {"oneOf": aisle_variants},
                    },
                    "required": ["item", "section"],
                },
            }
        },
        "required": ["items"],
    }

    response = await client.chat.completions.create(
        model="gpt-4o-mini",  # supports structured outputs
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "You are a grocery store section classifier. Classify each item into the most appropriate section. DO NOT CORRECT SPELLING ERRORS, you must return EXACTLY the item text as provided.",
            },
            {
                "role": "user",
                "content": f"Classify these grocery items: {items}",
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "grocery_sections",
                "schema": schema,
            },
        },
    )

    content = None
    try:
        if response.choices:
            msg = response.choices[0].message
            if hasattr(msg, "content"):
                content = msg.content
        if isinstance(content, str):
            text = content.strip()
            return json.loads(text)
    except Exception:
        pass
    # As a last resort, fabricate a minimal compliant structure so callers don't explode
    return {"items": [{"item": it, "section": "Misc"} for it in items]}
