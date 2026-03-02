"""Brain self-reflection — update SOUL.md and write daily memory logs."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path


def compute_genesis_hash(soul_path: Path) -> str:
    """Compute SHA-256 of the Core Purpose section in SOUL.md."""
    if not soul_path.exists():
        return ""
    content = soul_path.read_text(encoding="utf-8")
    match = re.search(
        r"# Core Purpose\s*\n(.*?)(?=\n# |\Z)",
        content,
        flags=re.DOTALL,
    )
    purpose = match.group(1).strip() if match else ""
    return hashlib.sha256(purpose.encode("utf-8")).hexdigest()


def update_soul_file(
    soul_path: Path,
    *,
    capabilities_update: dict[str, int] | None = None,
    strategy_update: str | None = None,
    lesson: str | None = None,
) -> None:
    """Update SOUL.md with new capabilities, strategy, and lessons. Bumps version."""
    if not soul_path.exists():
        return

    content = soul_path.read_text(encoding="utf-8")

    # Bump version in frontmatter
    content = re.sub(
        r"^(version:\s*)(\d+)",
        lambda m: f"{m.group(1)}{int(m.group(2)) + 1}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Update capabilities counters
    if capabilities_update:
        for key, value in capabilities_update.items():
            label = key.replace("_", " ").capitalize()
            content = re.sub(
                rf"(- {label}:\s*)\d+",
                rf"\g<1>{value}",
                content,
                flags=re.IGNORECASE,
            )

    # Update strategy section
    if strategy_update:
        content = re.sub(
            r"(# Strategy\s*\n).*?(?=\n# |\Z)",
            rf"\g<1>- Current focus: {strategy_update}\n",
            content,
            flags=re.DOTALL,
        )

    # Append lesson
    if lesson:
        if "# Lessons" in content:
            content = content.replace(
                "# Lessons",
                f"# Lessons\n- {lesson}",
            )
        else:
            content = content.rstrip() + f"\n\n# Lessons\n\n- {lesson}\n"

    soul_path.write_text(content, encoding="utf-8")


def write_daily_log(
    memory_dir: Path,
    goal_id: str,
    iterations: int = 0,
    skills_created: list[str] | None = None,
    total_cost: float = 0.0,
    key_decisions: list[str] | None = None,
    lesson: str = "",
) -> Path:
    """Append a goal completion entry to the daily memory log."""
    memory_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = memory_dir / f"{date_str}.md"

    skills_list = ", ".join(skills_created) if skills_created else "none"
    decisions_list = (
        "\n".join(f"  - {d}" for d in key_decisions) if key_decisions else "  - none"
    )

    entry = (
        f"\n## Goal: {goal_id}\n"
        f"- **Completed:** {datetime.now(timezone.utc).isoformat()}\n"
        f"- **Iterations:** {iterations}\n"
        f"- **Skills created/updated:** {skills_list}\n"
        f"- **Cost:** ${total_cost:.2f}\n"
        f"- **Key decisions:**\n{decisions_list}\n"
        f"- **Lesson:** {lesson}\n"
    )

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

    return log_path
