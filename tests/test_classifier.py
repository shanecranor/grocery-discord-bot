# tests/test_classify_items.py

import os
import sys
import pathlib
import time
from typing import Dict
import pytest
from dotenv import load_dotenv

load_dotenv()

# anyio lets pytest run async tests; explicitly param only asyncio backend
pytestmark = pytest.mark.anyio


# # Force pytest-anyio to use only asyncio backend (avoids needing trio dependency)
@pytest.fixture(params=["asyncio"], scope="session")
def anyio_backend(request):  # type: ignore[override]
    return request.param  # type: ignore


# Ensure src directory is on sys.path for direct imports when project not installed as a package
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from classifier import ALLOWED_AISLES as ALLOWED_SECTIONS


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set; skipping live LLM test.",
)
async def test_classify_items_structured_output_import_and_shape():
    start = time.time()
    print("[TEST] Starting classification test")
    # Import after env check so module import can succeed without a key elsewhere
    from classifier import (
        classify_items,
    )  # imported from src via sys.path injection above

    print("[TEST] Imported classify_items successfully")

    items_map: Dict[str, str] = {
        "mulk": "dairy",
        "dog fooud": "pet supplies",
        "ginger": "produce",
        "mirin": "international",
        "gochujang": "international",
        "paper towels": "household",
        "chicken": "meat",
        "apples": "produce",
        "bread": "bread/bakery",
        "yogurt": "dairy",
        "eggs": "dairy",
        "tortillas": "hispanic",
        "pasta": "pasta",
        "malk": "dairy",
    }
    items = list(items_map.keys())
    print(f"[TEST] Input items: {items}")
    out = await classify_items(items)
    assert isinstance(out, dict), f"Expected dict, got {type(out)}: {out!r}"
    assert "items" in out, f"Missing 'items' key in: {out!r}"
    assert isinstance(out["items"], list), "'items' must be a list"

    # Basic per-item checks
    for row in out["items"]:
        print(f"[TEST] Validating row: {row}")
        assert isinstance(row, dict), f"Each item must be an object: {row!r}"
        assert "item" in row and "section" in row, f"Missing keys in {row!r}"
        assert (
            isinstance(row["item"], str) and row["item"].strip()
        ), f"Bad item: {row!r}"
        assert row["section"] in ALLOWED_SECTIONS, f"Invalid section: {row['section']}"
        assert (
            row["section"].lower() == items_map[row["item"]].lower()
        ), f"Misclassified item '{row['item']}': expected '{items_map[row['item']]}' got '{row['section']}'"

    # Ensure all inputs appear in output (case-insensitive set compare)
    in_set = {s.lower() for s in items}
    out_set: set[str] = {r["item"].lower() for r in out["items"]}
    missing = in_set - out_set
    assert not missing, f"Some inputs missing in output: {missing}"
    print(f"[TEST] All inputs accounted for. Total items: {len(out['items'])}")
    print(f"[TEST] Completed in {time.time()-start:.2f}s")
