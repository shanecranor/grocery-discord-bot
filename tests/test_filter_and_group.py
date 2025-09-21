import pytest
import sys
import pathlib

# Match async test style from test_classifier using anyio
pytestmark = pytest.mark.anyio


@pytest.fixture(params=["asyncio"], scope="session")
def anyio_backend(request):  # type: ignore[override]
    return request.param  # type: ignore


# Ensure src directory is on sys.path for direct imports matching runtime usage
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from filter_and_group import filter_and_group_items


async def test_non_grouped_simple_list():
    items = ["apples", " bread ", "milk", "", "  "]
    out = await filter_and_group_items(
        items, store=None, is_grouped=False, enable_llm=False
    )
    assert out.splitlines() == ["- apples", "- bread", "- milk"]


async def test_store_filter_case_insensitive():
    items = ["Costco: Milk", "costco: Bread", "HEB: Eggs"]
    out = await filter_and_group_items(
        items, store="COSTCO", is_grouped=False, enable_llm=False
    )
    assert out.splitlines() == ["- Costco: Milk", "- costco: Bread"]


async def test_store_filter_no_matches_error():
    items = ["StoreA: Milk", "StoreB: Bread"]
    with pytest.raises(ValueError):
        await filter_and_group_items(
            items, store="Missing", is_grouped=False, enable_llm=False
        )


async def test_grouping_explicit_sections_and_order():
    items = [
        "Bananas (Produce)",
        "Apples (Produce)",
        "Spaghetti (Pasta)",
        "Tortillas (Hispanic)",
    ]
    out = await filter_and_group_items(
        items, store=None, is_grouped=True, enable_llm=False
    )
    # Sections should follow order defined in AISLES constant: Produce before Pasta before Hispanic
    expected = "**Produce**\n- Bananas\n- Apples\n\n**Pasta**\n- Spaghetti\n\n**Hispanic**\n- Tortillas"
    assert out == expected


async def test_grouping_with_llm_mock(monkeypatch):  # type: ignore
    items = [
        "Bananas (Produce)",  # explicit
        "Milk",  # needs classification
        "Bread",  # needs classification
    ]

    async def fake_classify(items_list):  # type: ignore
        assert items_list == ["Milk", "Bread"]
        return {
            "items": [
                {"item": "Milk", "section": "Dairy"},
                {"item": "Bread", "section": "Bread/Bakery"},
            ]
        }

    monkeypatch.setattr("filter_and_group.classify_items", fake_classify)  # type: ignore
    out = await filter_and_group_items(
        items, store=None, is_grouped=True, enable_llm=True
    )
    # Sections should be sorted in order they appear in AISLES constant
    expected = (
        "**Produce**\n- Bananas\n\n**Bread/Bakery**\n- Bread\n\n**Dairy**\n- Milk"
    )
    assert out == expected


async def test_grouping_llm_disabled_misc_ignored():
    # Items without explicit section and LLM disabled -> they won't appear
    items = ["Milk", "Bread", "Bananas (Produce)"]
    out = await filter_and_group_items(
        items, store=None, is_grouped=True, enable_llm=False
    )
    # Only Produce section should be rendered
    expected = "**Produce**\n- Bananas"
    assert out == expected


async def test_duplicate_items_same_section():
    items = [
        "Bananas (Produce)",
        "Bananas (Produce)",
        "Apples (Produce)",
    ]
    out = await filter_and_group_items(
        items, store=None, is_grouped=True, enable_llm=False
    )
    # Keep duplicates (function doesn't dedupe)
    expected = "**Produce**\n- Bananas\n- Bananas\n- Apples"
    assert out == expected


async def test_empty_input_returns_empty_string():
    out = await filter_and_group_items(
        [], store=None, is_grouped=False, enable_llm=False
    )
    assert out == ""
