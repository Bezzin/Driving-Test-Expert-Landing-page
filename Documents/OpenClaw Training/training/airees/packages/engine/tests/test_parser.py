# tests/test_parser.py
import pytest
from pathlib import Path
from airees_engine.parser import parse_agent_file, parse_workflow_file


def test_parse_agent_file(tmp_path):
    agent_yaml = tmp_path / "researcher.yaml"
    agent_yaml.write_text("""
name: researcher
description: "Finds info"
model: claude-sonnet-4-6
instructions: |
  You are a research specialist.
tools:
  - web_search
  - web_fetch
max_turns: 15
""")
    config = parse_agent_file(agent_yaml)
    assert config["name"] == "researcher"
    assert config["model"] == "claude-sonnet-4-6"
    assert len(config["tools"]) == 2
    assert config["max_turns"] == 15


def test_parse_workflow_file(tmp_path):
    wf_yaml = tmp_path / "pipeline.yaml"
    wf_yaml.write_text("""
name: research-pipeline
description: "Research and write"
pattern: pipeline
steps:
  - agent: researcher
    task: "Research {{topic}}"
  - agent: writer
    task: "Write about {{previous_output}}"
variables:
  topic:
    description: "The topic"
    required: true
""")
    config = parse_workflow_file(wf_yaml)
    assert config["name"] == "research-pipeline"
    assert config["pattern"] == "pipeline"
    assert len(config["steps"]) == 2


def test_parse_invalid_yaml(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("name: \n  invalid: [unbalanced")
    with pytest.raises(ValueError):
        parse_agent_file(bad_yaml)
