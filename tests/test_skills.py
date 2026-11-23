"""Skills follow the Agent Skills specification (https://agentskills.io/specification)."""

import re
from pathlib import Path

import pytest

SKILLS = sorted((Path(__file__).resolve().parents[1] / ".agents" / "skills").glob("*/SKILL.md"))
# What each skill must cover, by the heading that covers it.
SECTIONS = ["When to use", "Typical failures", "Verification", "Example"]


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert match, f"{path}: no YAML frontmatter"
    return dict(line.split(": ", 1) for line in match.group(1).splitlines())


def test_there_are_skills():
    assert SKILLS


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_follows_the_specification(path):
    meta = frontmatter(path)
    name = meta["name"]
    assert name == path.parent.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64
    assert 1 <= len(meta["description"]) <= 1024
    assert len(meta.get("compatibility", "x")) <= 500
    assert len(path.read_text(encoding="utf-8").splitlines()) <= 500


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_says_when_how_and_how_to_check(path):
    text = path.read_text(encoding="utf-8")
    for heading in SECTIONS:
        assert f"## {heading}" in text, f"{path.parent.name} has no '{heading}' section"
    assert "Use when" in frontmatter(path)["description"] or "Use before" in frontmatter(path)["description"]


def test_agents_md_names_every_skill():
    agents = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_text(encoding="utf-8")
    for path in SKILLS:
        assert path.parent.name in agents
