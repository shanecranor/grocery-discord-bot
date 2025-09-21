import sys
import pathlib
import types
import pytest
from typing import Any, List, AsyncIterator, Optional

pytestmark = pytest.mark.anyio


@pytest.fixture(params=["asyncio"], scope="session")
def anyio_backend(request):  # type: ignore[override]
    return request.param  # type: ignore


# Ensure src on path
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from groce_cli import cmd_list  # type: ignore
from constants import GROCE_CHANNEL_NAME


# Minimal fakes for discord objects we interact with
class FakeChannel:
    def __init__(self, name: str = "chan", messages: Optional[List[Any]] = None):
        self.name = name
        self._messages = messages or []
        self.sent: list[tuple[str, dict[str, Any]]] = []

    async def send(self, content: str, **kwargs: Any):  # type: ignore[override]
        self.sent.append((content, kwargs))
        return types.SimpleNamespace(content=content, **kwargs)

    def history(self, limit: int = 100, oldest_first: bool = True) -> AsyncIterator[Any]:  # type: ignore[override]
        async def _gen():
            for m in self._messages[:limit]:
                yield m

        return _gen()


class FakeGuild:
    def __init__(self, channels: List[FakeChannel]):
        self.text_channels = channels


class FakeMessage:
    def __init__(
        self,
        content: str,
        channel: FakeChannel | None = None,
        guild: FakeGuild | None = None,
    ):
        self.content = content
        self.channel: FakeChannel = channel or FakeChannel("reply")
        self.guild = guild


# Existing test
async def test_cmd_list_no_guild():
    msg = FakeMessage("list")  # guild None
    await cmd_list(msg)  # type: ignore[arg-type]
    assert msg.channel.sent[0][0] == "Command must be used in a guild."


async def test_cmd_list_channel_missing():
    other = FakeChannel("other")
    guild = FakeGuild([other])
    msg = FakeMessage("list", guild=guild)
    await cmd_list(msg)  # type: ignore[arg-type]
    assert msg.channel.sent[0][0] == f"Channel '{GROCE_CHANNEL_NAME}' not found."


async def test_cmd_list_no_items():
    groce = FakeChannel(GROCE_CHANNEL_NAME, messages=[])
    guild = FakeGuild([groce])

    msg = FakeMessage("list", guild=guild)
    await cmd_list(msg)  # type: ignore[arg-type]
    assert msg.channel.sent[0][0] == "No grocery items found."


async def test_cmd_list_non_grouped(monkeypatch):  # type: ignore
    # Prepare grocery channel with some messages
    class Msg:  # minimal message mimic
        def __init__(self, content: str):
            self.content = content

    groce_msgs = [Msg("storeA: apples"), Msg("storeA: bread"), Msg("storeB: milk")]
    groce = FakeChannel(GROCE_CHANNEL_NAME, messages=groce_msgs)
    guild = FakeGuild([groce])
    msg = FakeMessage("list storeA", guild=guild)

    async def fake_filter(items, store_filter, is_grouped, enable_llm=False):  # type: ignore
        # Validate parameters passed in from cmd_list
        assert is_grouped is False
        assert store_filter == "storea"  # lower-cased by cmd_list
        return "- storeA: apples\n- storeA: bread"

    monkeypatch.setattr("groce_cli.filter_and_group_items", fake_filter)  # type: ignore
    await cmd_list(msg)  # type: ignore[arg-type]
    # Expect single send with list text
    assert msg.channel.sent[0][0].splitlines() == [
        "- storeA: apples",
        "- storeA: bread",
    ]


async def test_cmd_list_grouped(monkeypatch):  # type: ignore
    class Msg:
        def __init__(self, content: str):
            self.content = content
            self.id = id(self)

    groce_msgs = [Msg("storeA: apples"), Msg("storeA: milk"), Msg("storeA: bread")]
    groce = FakeChannel(GROCE_CHANNEL_NAME, messages=groce_msgs)
    guild = FakeGuild([groce])
    msg = FakeMessage("list storeA group", guild=guild)

    async def fake_filter(items, store_filter, is_grouped, enable_llm=True, return_mapping=True):  # type: ignore
        assert is_grouped is True
        assert store_filter == "storea"
        # Return grouped_text and mapping
        grouped = "**Produce**\n- apples\n\n**Dairy**\n- milk"
        mapping = {"Produce": ["apples"], "Dairy": ["milk"]}
        return grouped, mapping

    monkeypatch.setattr("groce_cli.filter_and_group_items", fake_filter)  # type: ignore
    await cmd_list(msg)  # type: ignore[arg-type]
    # Two headers should be sent (sections)
    sent_headers = [c for c, _ in msg.channel.sent]
    assert sent_headers == ["**Produce**", "**Dairy**"]
