from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class BuildError(BaseModel):
    """First compilation error extracted from Maven output."""
    file_path: str
    line_number: int | None
    error_message: str
    raw_snippet: str          # surrounding lines from the source file


class AttemptRecord(BaseModel):
    """One full build attempt — win or lose."""
    attempt_number: int
    status: Literal["SUCCESS", "FAILED"]
    exit_code: int
    duration_seconds: float
    log_file: str             # absolute path to the captured log
    error: BuildError | None  # None on success
    files_modified: list[str] # files the AI touched this attempt
    ai_fix_reason: str        # empty string on first attempt or success


class BuildResult(BaseModel):
    project_id: str
    status: Literal["SUCCESS", "FAILED"]
    build_status: Literal["SUCCESS", "FAILED"]
    jar_generated: bool
    jar_location: str         # empty string if not generated
    total_attempts: int
    errors_fixed: int
    files_modified: list[str]
    attempts: list[AttemptRecord]
    build_report_url: str     # /build/{project_id}/report
    manual_intervention_required: bool
