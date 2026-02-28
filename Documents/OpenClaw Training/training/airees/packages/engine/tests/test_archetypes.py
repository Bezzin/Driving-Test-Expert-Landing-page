# tests/test_archetypes.py
from airees_engine.archetypes.loader import load_all_archetypes, load_archetype


def test_load_all_archetypes():
    archetypes = load_all_archetypes()
    assert len(archetypes) >= 8
    assert "researcher" in archetypes
    assert "coder" in archetypes
    assert "router" in archetypes


def test_archetype_has_required_fields():
    archetypes = load_all_archetypes()
    for name, config in archetypes.items():
        assert "name" in config, f"Archetype {name} missing 'name'"
        assert "model" in config, f"Archetype {name} missing 'model'"
        assert "instructions" in config, f"Archetype {name} missing 'instructions'"


def test_load_single_archetype():
    config = load_archetype("researcher")
    assert config["name"] == "researcher"
    assert "tools" in config
