"""Tests for corpus search engine."""
from __future__ import annotations

from pathlib import Path

import pytest

from airees.corpus_search import CorpusDocument, CorpusResult, CorpusSearchEngine


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    """Create a minimal corpus directory with sample files."""
    cat1 = tmp_path / "01-fundamentals" / "concepts"
    cat1.mkdir(parents=True)
    (cat1 / "01-agent-basics.md").write_text(
        "# Agent Basics\n\n## Summary\n\nAgents use tools to accomplish tasks.\n"
        "## Key Concepts\n- Tool use\n- Planning\n- Evaluation\n",
        encoding="utf-8",
    )

    cat2 = tmp_path / "02-prompts" / "patterns"
    cat2.mkdir(parents=True)
    (cat2 / "01-chain-of-thought.md").write_text(
        "# Chain of Thought\n\n## Summary\n\nChain of thought prompting improves reasoning.\n"
        "## Key Concepts\n- Step-by-step reasoning\n- Self-consistency\n",
        encoding="utf-8",
    )

    cat3 = tmp_path / "07-security" / "hardening"
    cat3.mkdir(parents=True)
    (cat3 / "01-input-validation.md").write_text(
        "# Input Validation\n\n## Summary\n\nAlways validate user input to prevent injection.\n"
        "## Key Concepts\n- SQL injection\n- XSS prevention\n- Sanitization\n",
        encoding="utf-8",
    )
    return tmp_path


def test_engine_builds_index(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("agent tools", top_k=3)
    assert len(results) > 0
    assert all(isinstance(r, CorpusResult) for r in results)


def test_search_returns_relevant_results(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("security input validation injection", top_k=1)
    assert len(results) == 1
    assert "security" in results[0].category.lower() or "validation" in results[0].title.lower()


def test_search_respects_top_k(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("concepts", top_k=2)
    assert len(results) <= 2


def test_empty_corpus(tmp_path: Path):
    engine = CorpusSearchEngine(corpus_dir=tmp_path)
    results = engine.search("anything", top_k=3)
    assert results == []


def test_corpus_document_fields(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("agent", top_k=1)
    assert len(results) == 1
    r = results[0]
    assert r.path is not None
    assert r.title != ""
    assert r.score > 0
    assert r.excerpt != ""


def test_index_cached_across_searches(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    engine.search("agent", top_k=1)
    results = engine.search("security", top_k=1)
    assert len(results) > 0
    assert engine._index is not None
    assert len(engine._documents) == 3


def test_format_results(corpus_dir: Path):
    engine = CorpusSearchEngine(corpus_dir=corpus_dir)
    results = engine.search("agent tools", top_k=2)
    formatted = engine.format_results(results)
    assert "###" in formatted
    assert "Category:" in formatted
