"""Tests for the skill store — create, search, update skills."""
from __future__ import annotations

from pathlib import Path

import pytest

from airees.skill_store import SkillDocument, SkillResult, SkillStore


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    """Create a skills directory with a sample skill."""
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "web-scraper.md").write_text(
        "---\n"
        "name: web-scraper\n"
        "description: Scrape and parse web pages for data extraction\n"
        "version: 2\n"
        "success_rate: 0.9\n"
        "triggers:\n"
        "  - scrape a website\n"
        "  - extract data from web\n"
        "tools_required:\n"
        "  - web_search\n"
        "  - web_extract\n"
        "---\n\n"
        "# Web Scraper Pipeline\n\n"
        "## Task Graph\n"
        "1. Identify target URLs\n"
        "2. Fetch pages\n"
        "3. Parse content\n\n"
        "## Lessons Learned\n"
        "- Use retry logic for flaky sites\n\n"
        "## Known Pitfalls\n"
        "- Respect robots.txt\n",
        encoding="utf-8",
    )
    return skills


def test_search_finds_matching_skill(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    results = store.search("scrape a website to extract data")
    assert len(results) >= 1
    assert results[0].name == "web-scraper"


def test_search_returns_skill_result_fields(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    results = store.search("web scraper", top_k=1)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, SkillResult)
    assert r.name == "web-scraper"
    assert r.version == 2
    assert r.success_rate == 0.9
    assert r.score > 0
    assert "Task Graph" in r.content


def test_search_empty_dir(tmp_path: Path):
    store = SkillStore(skills_dir=tmp_path)
    results = store.search("anything")
    assert results == []


def test_create_skill(tmp_path: Path):
    store = SkillStore(skills_dir=tmp_path)
    store.create_skill(
        name="api-builder",
        description="Build REST APIs with FastAPI",
        triggers=["build an api", "create rest endpoint"],
        task_graph="1. Design schema\n2. Implement routes\n3. Test",
        lessons_learned="Use Pydantic for validation",
        quality_gates="All endpoints return 200",
        known_pitfalls="Don't forget CORS",
    )
    path = tmp_path / "api-builder.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "name: api-builder" in content
    assert "version: 1" in content
    assert "success_rate: 1.0" in content
    assert "build an api" in content
    assert "## Task Graph" in content
    assert "Use Pydantic for validation" in content


def test_update_skill(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    store.update_skill(
        name="web-scraper",
        lessons_learned="Also handle JavaScript-rendered pages",
        known_pitfalls="Watch for rate limits",
    )
    content = (skills_dir / "web-scraper.md").read_text(encoding="utf-8")
    assert "version: 3" in content
    assert "JavaScript-rendered" in content
    assert "rate limits" in content
    assert "Respect robots.txt" in content
    assert "Use retry logic" in content


def test_update_skill_bumps_execution_count(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    store.update_skill(name="web-scraper", success=True)
    content = (skills_dir / "web-scraper.md").read_text(encoding="utf-8")
    assert "version: 3" in content


def test_update_nonexistent_skill_raises(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    with pytest.raises(FileNotFoundError):
        store.update_skill(name="nonexistent")


def test_invalidate_rebuilds_index(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    store.search("web scraper")
    assert store._index is not None
    store.invalidate()
    assert store._index is None


def test_load_skill_content(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    content = store.load_skill("web-scraper")
    assert "Web Scraper Pipeline" in content
    assert "Task Graph" in content


def test_load_nonexistent_skill_returns_none(skills_dir: Path):
    store = SkillStore(skills_dir=skills_dir)
    content = store.load_skill("nonexistent")
    assert content is None
