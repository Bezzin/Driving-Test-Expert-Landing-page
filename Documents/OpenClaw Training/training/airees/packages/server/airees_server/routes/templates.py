"""Workflow template API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from airees_engine.templates.loader import load_all_templates, load_template

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
def list_templates():
    return load_all_templates()


@router.get("/{name}")
def get_template(name: str):
    try:
        return load_template(name)
    except ValueError:
        raise HTTPException(404, f"Template not found: {name}")
