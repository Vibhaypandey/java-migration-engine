import logging

from fastapi import APIRouter, File, UploadFile

from app.models.upload import DeleteResponse, UploadResponse
from app.services.upload_service import delete_workspace, process_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResponse)
async def upload_project(file: UploadFile = File(...)):
    """
    Upload a Java project ZIP.
    Validates that the ZIP contains a Maven or Gradle project with Java >= 11
    before extracting it into the workspace.
    """
    logger.info("Upload received: %s (%s)", file.filename, file.content_type)
    extract_dir, file_count, project_info = process_upload(file)
    workspace_id = extract_dir.name  # UUID hex folder name
    return UploadResponse(
        message="Upload successful",
        workspace_id=workspace_id,
        build_tool=project_info.build_tool,
        detected_java_version=project_info.java_version,
        extracted_folder=str(extract_dir),
        file_count=file_count,
    )


@router.delete("/workspace/{workspace_id}", response_model=DeleteResponse)
def delete_project_workspace(workspace_id: str):
    """Delete an extracted workspace folder by its UUID."""
    logger.info("Delete request for workspace: %s", workspace_id)
    delete_workspace(workspace_id)
    return DeleteResponse(message="Workspace deleted successfully.", workspace_id=workspace_id)
