# tests/test_memory_file.py
import pytest
from pathlib import Path
from airees.memory.file_store import FileMemoryStore


@pytest.fixture
def store(tmp_path):
    return FileMemoryStore(base_path=tmp_path)


def test_write_and_read(store):
    store.write("researcher", "SOUL.md", "You are a research specialist.")
    content = store.read("researcher", "SOUL.md")
    assert content == "You are a research specialist."


def test_read_nonexistent_returns_empty(store):
    content = store.read("unknown", "SOUL.md")
    assert content == ""


def test_append(store):
    store.write("agent", "MEMORY.md", "Fact 1\n")
    store.append("agent", "MEMORY.md", "Fact 2\n")
    content = store.read("agent", "MEMORY.md")
    assert "Fact 1" in content
    assert "Fact 2" in content


def test_list_files(store):
    store.write("agent", "SOUL.md", "soul")
    store.write("agent", "MEMORY.md", "memory")
    files = store.list_files("agent")
    assert set(files) == {"SOUL.md", "MEMORY.md"}


def test_list_files_empty(store):
    files = store.list_files("nonexistent")
    assert files == []


def test_write_creates_directories(store):
    store.write("new-agent", "deep/nested/file.md", "content")
    assert store.read("new-agent", "deep/nested/file.md") == "content"
