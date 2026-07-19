import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.models.report import AssessmentReport
from app.services.assessment.report_builder import build_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assessment", tags=["assessment"])


def _resolve_workspace(workspace_id: str):
    """Validate UUID format and return the workspace Path, or raise 400/404."""
    if not re.fullmatch(r"[0-9a-f]{32}", workspace_id):
        raise HTTPException(status_code=400, detail="Invalid workspace ID format.")
    path = settings.workspace_dir / workspace_id
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")
    return path


@router.get("/{project_id}", response_model=AssessmentReport)
def get_assessment(project_id: str):
    """
    Run a full migration assessment and return structured JSON.
    The JSON includes a report_url field pointing to the HTML report endpoint.
    """
    logger.info("JSON assessment requested: %s", project_id)
    extract_dir = _resolve_workspace(project_id)
    return build_report(project_id, extract_dir)


@router.get("/{project_id}/report", response_class=FileResponse)
def get_report_html(project_id: str):
    """
    Serve the pre-generated HTML report file directly from disk.
    Returns Content-Type: text/html so the browser renders it natively.
    Runs GET /{project_id} first if the file does not exist yet.
    """
    if not re.fullmatch(r"[0-9a-f]{32}", project_id):
        raise HTTPException(status_code=400, detail="Invalid workspace ID format.")

    report_path = settings.reports_dir / f"{project_id}.html"

    # If the HTML file was never generated, run the assessment now to create it
    if not report_path.exists():
        logger.info("Report file not found — generating for: %s", project_id)
        extract_dir = _resolve_workspace(project_id)
        build_report(project_id, extract_dir)

    # Re-check after generation attempt
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report could not be generated.")

    logger.info("Serving HTML report: %s", report_path)
    return FileResponse(
        path=str(report_path),
        media_type="text/html",
        filename=f"migration-report-{project_id}.html",
    )
