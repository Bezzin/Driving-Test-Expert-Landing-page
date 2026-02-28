"""Tests for decision document generation."""
import pytest

from airees.decision_doc import DecisionDocument, DecisionEntry


def test_document_creation():
    doc = DecisionDocument(project_id="proj-001", title="Test App")
    assert doc.project_id == "proj-001"
    assert doc.entries == []


def test_add_entry():
    doc = DecisionDocument(project_id="proj-001", title="Test")
    updated = doc.add_entry(DecisionEntry(
        phase="research",
        agent="researcher",
        decision="Chose fitness niche",
        reasoning="High demand, low competition",
        confidence=0.85,
    ))
    assert len(updated.entries) == 1
    assert updated.entries[0].phase == "research"


def test_add_multiple_entries():
    doc = DecisionDocument(project_id="proj-001", title="Test")
    doc = doc.add_entry(DecisionEntry(
        phase="research",
        agent="researcher",
        decision="A",
        reasoning="B",
        confidence=0.9,
    ))
    doc = doc.add_entry(DecisionEntry(
        phase="build",
        agent="builder",
        decision="C",
        reasoning="D",
        confidence=0.8,
    ))
    assert len(doc.entries) == 2


def test_to_markdown():
    doc = DecisionDocument(project_id="proj-001", title="Test App")
    doc = doc.add_entry(DecisionEntry(
        phase="research",
        agent="researcher",
        decision="Target fitness niche",
        reasoning="High demand, low competition",
        confidence=0.85,
    ))
    md = doc.to_markdown()
    assert "# Test App" in md
    assert "## research" in md
    assert "Target fitness niche" in md
    assert "85%" in md


def test_immutability():
    doc = DecisionDocument(project_id="proj-001", title="Test")
    doc.add_entry(DecisionEntry(
        phase="x",
        agent="a",
        decision="d",
        reasoning="r",
        confidence=0.5,
    ))
    assert len(doc.entries) == 0
