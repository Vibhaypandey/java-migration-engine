import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.models.migration import MigrationResult
from app.services.migration.migration_engine import run_migration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/migration", tags=["migration"])


def _resolve_workspace(project_id: str):
    """Validate UUID format and return the workspace Path, or raise 400/404."""
    if not re.fullmatch(r"[0-9a-f]{32}", project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format.")
    path = settings.workspace_dir / project_id
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace '{project_id}' not found.")
    return path


@router.post("/{project_id}/start", response_model=MigrationResult)
def start_migration(project_id: str):
    """
    Trigger Phase 1 migration for a previously uploaded and assessed project.

    Execution order:
      1. Create full backup  →  workspace/backups/{project_id}/
      2. Update pom.xml      →  Java 21, Spring Boot 3.3.4, plugins, dependencies
      3. Generate summary    →  workspace/reports/{project_id}_migration.html

    Java source files are NOT modified.
    Maven is NOT invoked.
    Returns a MigrationResult with per-step status and a summary_url.
    """
    logger.info("Migration start requested for project: %s", project_id)
    extract_dir = _resolve_workspace(project_id)
    return run_migration(project_id, extract_dir)


@router.get("/{project_id}/summary", response_class=FileResponse)
def get_migration_summary(project_id: str):
    """
    Serve the Migration Summary HTML page from disk.
    Returns HTTP 404 if migration has not been run yet for this project.
    """
    if not re.fullmatch(r"[0-9a-f]{32}", project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format.")

    summary_path = settings.reports_dir / f"{project_id}_migration.html"
    if not summary_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Migration summary not found. Run POST /migration/{project_id}/start first.",
        )

    logger.info("Serving migration summary: %s", summary_path)
    return FileResponse(
        path=str(summary_path),
        media_type="text/html",
        filename=f"migration-summary-{project_id}.html",
    )
