"""C7 — the operator card documents exactly the implemented keys; prompts match the tool's EC-04 lines."""
import re
from pathlib import Path

from tripstate.seeding.session import KEYMAP, SeedingSession

ROOT = Path(__file__).resolve().parents[1]
OP = ROOT / "protocols" / "OPERATOR"
ALIASES = {"space": " "}


def card_keys() -> set[str]:
    keys = set()
    for line in (OP / "KEYMAP-CARD.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cell = line.split("|")[1]
        for k in re.findall(r"`([^`]+)`", cell):
            keys.add(ALIASES.get(k, k))
    return keys


def test_card_keys_equal_the_implemented_keymap():
    assert card_keys() == set(KEYMAP), (card_keys() ^ set(KEYMAP))


def test_anchor_prompts_quote_the_tools_ec04_lines():
    text = (OP / "ANCHOR-PROMPTS.md").read_text(encoding="utf-8")
    auto = SeedingSession("R", 100, 25.0, start_type="autostart", start_format="autostart")
    assert auto.start_prompt() in text
    flat = SeedingSession("R", 100, 25.0, start_type="volte", start_format="volte_flat")
    assert flat.start_prompt() in text
    hcp = SeedingSession("R", 100, 25.0, start_type="volte", start_format="volte_handicap", rendement_bands={2850: 5, 2875: 4})
    assert hcp.start_prompt().split(";")[0] in text


def test_walkthrough_uses_only_existing_tools_and_keys():
    text = (OP / "SEEDING-WALKTHROUGH.md").read_text(encoding="utf-8")
    for tool in re.findall(r"tools/([a-z0-9_]+\.py)", text):
        assert (ROOT / "tools" / tool).exists(), tool
    for k in re.findall(r"press `([^`]+)`", text, flags=re.IGNORECASE):
        assert ALIASES.get(k, k) in KEYMAP, k
    assert "not** human-minutes" in text or "not human-minutes" in text or "ignored" in text
