"""Tests for KnowledgeStore — ChromaDB-based semantic search."""
from __future__ import annotations

from pathlib import Path

import pytest

from airees.knowledge.store import KnowledgeResult, KnowledgeStore


@pytest.fixture
def store(tmp_path: Path) -> KnowledgeStore:
    return KnowledgeStore(data_dir=tmp_path / "knowledge")


def test_ingest_text_file(store: KnowledgeStore, tmp_path: Path):
    """Ingesting a text file makes it searchable."""
    doc = tmp_path / "notes.txt"
    doc.write_text("The quarterly budget was approved for $50,000.", encoding="utf-8")

    store.ingest(doc)
    results = store.search("budget approved")

    assert len(results) >= 1
    assert "budget" in results[0].text.lower()


def test_ingest_markdown_file(store: KnowledgeStore, tmp_path: Path):
    """Ingesting a markdown file works."""
    doc = tmp_path / "meeting.md"
    doc.write_text("# Meeting Notes\n\nDiscussed the new AI deployment timeline.", encoding="utf-8")

    store.ingest(doc)
    results = store.search("AI deployment timeline")

    assert len(results) >= 1


def test_search_empty_store_returns_empty(store: KnowledgeStore):
    """Searching an empty store returns empty list."""
    results = store.search("anything")
    assert results == []


def test_delete_removes_document(store: KnowledgeStore, tmp_path: Path):
    """Deleting a document removes it from search."""
    doc = tmp_path / "temp.txt"
    doc.write_text("Temporary data for testing.", encoding="utf-8")

    store.ingest(doc)
    assert len(store.search("temporary data")) >= 1

    store.delete(str(doc))
    assert len(store.search("temporary data")) == 0


def test_stats_reports_counts(store: KnowledgeStore, tmp_path: Path):
    """stats() returns document count."""
    assert store.stats()["document_count"] == 0

    doc = tmp_path / "a.txt"
    doc.write_text("Test content.", encoding="utf-8")
    store.ingest(doc)

    assert store.stats()["document_count"] >= 1
