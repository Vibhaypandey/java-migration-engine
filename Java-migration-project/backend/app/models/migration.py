from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class StepResult(BaseModel):
    step: str
    status: Literal["SUCCESS", "SKIPPED", "FAILED"]
    detail: str


class SourceChange(BaseModel):
    """One logical change applied to a single .java file."""
    file_path: str          # relative path from project root
    category: str           # e.g. "javax → jakarta"
    description: str        # human-readable description of what changed
    occurrences: int        # how many replacements were made in this file


class DependencyChange(BaseModel):
    """One dependency version bump recorded in pom.xml."""
    artifact_id: str
    group_id: str
    old_version: str | None
    new_version: str
    source: str             # "maven_central" | "knowledge_base" | "spring_bom"


class MigrationResult(BaseModel):
    project_id: str
    status: Literal["COMPLETED", "FAILED"]
    build_status: Literal["Not Executed", "SUCCESS", "FAILED"]
    backup_path: str
    updated_pom_path: str
    migration_report_url: str
    steps: list[StepResult]
    # New: detailed change records for the HTML report
    source_changes: list[SourceChange] = []
    dependency_changes: list[DependencyChange] = []
    total_files_modified: int = 0
    total_source_changes: int = 0
