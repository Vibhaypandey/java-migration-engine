import logging
import re
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.services.java_version_service import ProjectInfo, validate_java_project_in_zip

logger = logging.getLogger(__name__)

# Human-readable error messages kept here so they're easy to update in one place
_ERR_NOT_A_ZIP = "Invalid file type. Please upload a ZIP file."
_ERR_CORRUPT_ZIP = "The uploaded ZIP file is corrupt or unreadable."
_ERR_NOT_JAVA = "Invalid project. Please upload a valid Java project ZIP."
_ERR_VERSION_LOW = "Java version not supported. Please upload a project using Java 11 or higher."
_ERR_EXTRACT_FAIL = "Failed to extract the uploaded ZIP."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _assert_zip_file(file: UploadFile) -> None:
    """
    Fast pre-check on filename and MIME type before reading any bytes.
    Raises HTTP 400 immediately for obviously wrong file types.
    """
    logger.info("Checking file type: name=%s, content_type=%s", file.filename, file.content_type)

    valid_mime = {
        "application/zip",
        "application/x-zip-compressed",
        "application/octet-stream",  # some browsers send this for ZIP
    }

    if not file.filename.endswith(".zip") or file.content_type not in valid_mime:
        logger.warning("Rejected non-ZIP upload: %s (%s)", file.filename, file.content_type)
        raise HTTPException(status_code=400, detail=_ERR_NOT_A_ZIP)


def _validate_in_memory(file: UploadFile) -> tuple[bytes, ProjectInfo]:
    """
    Read the entire uploaded file into memory, open it as a ZIP, and run
    all project validations WITHOUT writing anything to disk.

    Returns (raw_bytes, ProjectInfo) on success.
    Raises HTTP 400 for every validation failure.

    Why in-memory?
    Reading into bytes lets us both validate the ZIP structure and pass the
    same ZipFile object to the validator — no temp file, no cleanup needed.
    """
    logger.info("Reading uploaded file into memory for validation")
    raw = file.file.read()

    # Verify the bytes are actually a ZIP archive (magic-byte check)
    if not zipfile.is_zipfile(__import__("io").BytesIO(raw)):
        logger.warning("Uploaded file failed ZIP magic-byte check: %s", file.filename)
        raise HTTPException(status_code=400, detail=_ERR_CORRUPT_ZIP)

    try:
        import io
        with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
            project_info = validate_java_project_in_zip(zf)
    except zipfile.BadZipFile:
        logger.error("BadZipFile while opening: %s", file.filename)
        raise HTTPException(status_code=400, detail=_ERR_CORRUPT_ZIP)
    except ValueError as exc:
        # Translate the short error codes from the validator into HTTP responses
        if str(exc) == "not_java_project":
            raise HTTPException(status_code=400, detail=_ERR_NOT_JAVA)
        if str(exc) == "version_too_low":
            raise HTTPException(status_code=400, detail=_ERR_VERSION_LOW)
        raise  # unexpected — let the global handler deal with it

    return raw, project_info


def _save_and_extract(raw: bytes, filename: str) -> tuple[Path, int]:
    """
    Persist the validated ZIP bytes to uploads/ then extract into a
    unique workspace/ subdirectory.

    This function is only called AFTER all validations have passed.
    """
    import io

    # Save raw bytes to uploads/
    dest = settings.upload_dir / filename
    dest.write_bytes(raw)
    logger.info("Saved validated ZIP: %s", dest)

    # Extract into a UUID-named folder to prevent concurrent-upload collisions
    extract_dir = settings.workspace_dir / uuid.uuid4().hex
    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
            members = zf.namelist()
            zf.extractall(extract_dir)
    except Exception as exc:
        # Extraction failed after validation passed — clean up the partial folder
        shutil.rmtree(extract_dir, ignore_errors=True)
        logger.exception("Extraction failed for %s", filename)
        raise HTTPException(status_code=500, detail=_ERR_EXTRACT_FAIL) from exc

    file_count = sum(1 for m in members if not m.endswith("/"))
    logger.info("Extracted %d files to %s", file_count, extract_dir)
    return extract_dir, file_count


# ---------------------------------------------------------------------------
# Public API — called by the router
# ---------------------------------------------------------------------------

def process_upload(file: UploadFile) -> tuple[Path, int, ProjectInfo]:
    """
    Full upload pipeline:
      1. Check file extension + MIME type          → HTTP 400 if wrong
      2. Read bytes, validate ZIP structure         → HTTP 400 if corrupt
      3. Confirm Maven or Gradle build file exists  → HTTP 400 if missing
      4. Detect and validate Java version >= 11     → HTTP 400 if too low
      5. Save ZIP to uploads/ and extract to workspace/

    Nothing is written to disk until step 5.
    """
    # Step 1 — fast MIME / extension gate
    _assert_zip_file(file)

    # Steps 2-4 — in-memory validation, zero disk I/O
    raw, project_info = _validate_in_memory(file)

    # Step 5 — write to disk only after all checks pass
    extract_dir, file_count = _save_and_extract(raw, file.filename)

    return extract_dir, file_count, project_info


def delete_workspace(workspace_id: str) -> None:
    """
    Delete an extracted workspace folder by its UUID hex name.
    Raises HTTP 400 for invalid IDs, HTTP 404 if the folder does not exist.
    The UUID format check also prevents path-traversal attacks.
    """
    if not re.fullmatch(r"[0-9a-f]{32}", workspace_id):
        raise HTTPException(status_code=400, detail="Invalid workspace ID format.")

    target = settings.workspace_dir / workspace_id
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    shutil.rmtree(target)
    logger.info("Deleted workspace: %s", target)
