import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def apply_fixes(file_map: dict[str, str], project_dir: Path, backup_dir: Path) -> list[str]:
    """
    Write AI-generated file content to disk.

    Safety rules enforced here:
    1. Every file is backed up to backup_dir before being overwritten.
    2. The target path must be inside project_dir (path traversal guard).
    3. Only .java and pom.xml files are accepted — nothing else.

    Returns a list of file paths that were successfully written.
    """
    written: list[str] = []

    for raw_path, new_content in file_map.items():
        target = Path(raw_path)

        # ── Guard 1: only Java source files and pom.xml ──────────────────────
        if target.suffix not in (".java",) and target.name != "pom.xml":
            logger.warning("[Patcher] Skipping non-Java/pom file: %s", raw_path)
            continue

        # ── Guard 2: path must be inside project_dir ─────────────────────────
        try:
            target.resolve().relative_to(project_dir.resolve())
        except ValueError:
            logger.warning("[Patcher] Path escapes project dir — skipping: %s", raw_path)
            continue

        if not target.exists():
            logger.warning("[Patcher] Target file does not exist — skipping: %s", raw_path)
            continue

        # ── Backup before overwrite ───────────────────────────────────────────
        rel = target.resolve().relative_to(project_dir.resolve())
        backup_path = backup_dir / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup_path)
        logger.info("[Patcher] Backed up: %s → %s", target, backup_path)

        # ── Write new content ─────────────────────────────────────────────────
        try:
            target.write_text(new_content, encoding="utf-8")
            written.append(str(target))
            logger.info("[Patcher] Written: %s (%d chars)", target, len(new_content))
        except OSError as exc:
            logger.error("[Patcher] Write failed for %s: %s", target, exc)

    return written
