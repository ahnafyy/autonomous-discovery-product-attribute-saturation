from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"missing frontmatter: {path}"
    _, raw, _ = text.split("---", 2)
    value = yaml.safe_load(raw)
    assert isinstance(value, dict), f"invalid frontmatter: {path}"
    return value


def test_agent_customizations_have_discoverable_frontmatter() -> None:
    customization_files = [
        *ROOT.glob(".github/agents/*.agent.md"),
        *ROOT.glob(".github/instructions/*.instructions.md"),
        *ROOT.glob(".github/prompts/*.prompt.md"),
    ]
    assert customization_files
    for path in customization_files:
        metadata = _frontmatter(path)
        assert isinstance(metadata.get("description"), str)
