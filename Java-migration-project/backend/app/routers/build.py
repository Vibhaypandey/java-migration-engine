import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from app.config import settings
from app.models.build import BuildResult
from app.services.build.build_loop import run_build_loop

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/build", tags=["build"])


def _validate_id(project_id: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{32}", project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID format.")


def _resolve_workspace(project_id: str):
    _validate_id(project_id)
    path = settings.workspace_dir / project_id
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace '{project_id}' not found.")
    return path


@router.post("/{project_id}/start", response_model=BuildResult)
def start_build(project_id: str):
    """
    Trigger Phase 3: Maven build verification with AI-assisted error resolution.

    Flow:
      1. Run mvn clean package
      2. On failure: parse first error → ask AI → patch files → retry
      3. Repeat up to build_max_retries (default 5)
      4. Return BuildResult with full attempt history and report URL

    Prerequisite: POST /migration/{project_id}/start must have run first.
    """
    logger.info("Build start requested: %s", project_id)
    project_dir = _resolve_workspace(project_id)
    return run_build_loop(project_id, project_dir)


@router.get("/{project_id}/report", response_class=FileResponse)
def get_build_report(project_id: str):
    """
    Serve the Build Report HTML page from disk.
    Returns 404 if POST /build/{project_id}/start has not been run yet.
    """
    _validate_id(project_id)
    report_path = settings.reports_dir / f"{project_id}_build.html"
    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Build report not found. Run POST /build/{project_id}/start first.",
        )
    logger.info("Serving build report: %s", report_path)
    return FileResponse(path=str(report_path), media_type="text/html")


@router.get("/{project_id}/logs/{attempt}", response_class=PlainTextResponse)
def get_build_log(project_id: str, attempt: int):
    """
    Return the raw Maven log for a specific attempt number as plain text.
    Useful for debugging individual failures.
    """
    _validate_id(project_id)
    log_path = settings.build_logs_dir / project_id / f"attempt_{attempt}.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"Log for attempt {attempt} not found.")
    return PlainTextResponse(content=log_path.read_text(encoding="utf-8", errors="replace"))
