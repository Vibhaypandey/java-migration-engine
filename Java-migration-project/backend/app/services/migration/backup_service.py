import logging
import shutil
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


def create_backup(project_id: str, source_dir: Path) -> Path:
    """
    Copy the entire extracted project directory into workspace/backups/{project_id}/.

    Why copy instead of move?
    The source workspace stays intact so the assessment report and future
    re-runs still work against the original files.  The backup is the
    safety net — if migration goes wrong the user can restore from it.

    Returns the backup root path.
    Raises RuntimeError if the backup cannot be created.
    """
    backup_dest = settings.backups_dir / project_id

    if backup_dest.exists():
        # A backup already exists — remove it so we get a clean, fresh copy.
        # This handles the case where migration is re-triggered on the same project.
        logger.info("Removing existing backup at %s", backup_dest)
        shutil.rmtree(backup_dest)

    logger.info("Creating backup: %s → %s", source_dir, backup_dest)

    try:
        shutil.copytree(src=source_dir, dst=backup_dest)
    except Exception as exc:
        logger.exception("Backup failed for project %s", project_id)
        raise RuntimeError(f"Backup failed: {exc}") from exc

    # Verify the backup actually landed on disk
    if not backup_dest.exists():
        raise RuntimeError("Backup directory was not created.")

    file_count = sum(1 for _ in backup_dest.rglob("*") if _.is_file())
    logger.info("Backup complete: %d files copied to %s", file_count, backup_dest)
    return backup_dest
