"""Phase 4 integration: verify all new components are exported and work together."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_all_phase4_exports():
    """Verify every Phase 4 class is importable from airees."""
    mod = importlib.import_module("airees")
    for name in [
        "CorpusSearchEngine",
        "CorpusResult",
        "CorpusDocument",
        "SkillStore",
        "SkillResult",
        "SkillDocument",
        "ContextCompressor",
    ]:
        assert hasattr(mod, name), f"Missing export: {name}"


def test_phase4_event_types():
    from airees import EventType
    phase4_events = [
        "CORPUS_SEARCH",
        "SKILL_MATCHED",
        "SKILL_CREATED",
        "SKILL_UPDATED",
        "CONTEXT_COMPRESSED",
        "SOUL_UPDATED",
        "REFLECTION_TRIGGERED",
    ]
    for name in phase4_events:
        assert hasattr(EventType, name), f"Missing event type: {name}"


def test_corpus_and_skill_search_together(tmp_path: Path):
    """Test that corpus and skill engines can coexist and search independently."""
    from airees.corpus_search import CorpusSearchEngine
    from airees.skill_store import SkillStore

    corpus_dir = tmp_path / "corpus"
    cat = corpus_dir / "01-fundamentals"
    cat.mkdir(parents=True)
    (cat / "01-basics.md").write_text(
        "# Agent Basics\n\nAgents use tools to accomplish tasks.\n",
        encoding="utf-8",
    )
    cat2 = corpus_dir / "02-deployment"
    cat2.mkdir(parents=True)
    (cat2 / "01-infra.md").write_text(
        "# Infrastructure Setup\n\nServers run in containers with Docker.\n",
        encoding="utf-8",
    )
    cat3 = corpus_dir / "03-security"
    cat3.mkdir(parents=True)
    (cat3 / "01-overview.md").write_text(
        "# Security Overview\n\nEncryption protects sensitive data in transit.\n",
        encoding="utf-8",
    )

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "api-builder.md").write_text(
        "---\nname: api-builder\ndescription: Build REST APIs\nversion: 1\n"
        "triggers:\n  - build an api\n---\n\n# API Builder\n",
        encoding="utf-8",
    )

    corpus = CorpusSearchEngine(corpus_dir=corpus_dir)
    skills = SkillStore(skills_dir=skills_dir)

    corpus_results = corpus.search("agents tools tasks")
    skill_results = skills.search("build an api")

    assert len(corpus_results) == 1
    assert corpus_results[0].title == "Agent Basics"
    assert len(skill_results) == 1
    assert skill_results[0].name == "api-builder"


def test_reflection_functions_importable():
    from airees.brain.reflection import (
        compute_genesis_hash,
        update_soul_file,
        write_daily_log,
    )
    assert callable(compute_genesis_hash)
    assert callable(update_soul_file)
    assert callable(write_daily_log)
