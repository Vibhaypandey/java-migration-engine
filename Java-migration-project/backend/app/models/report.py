from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Section 1 — Project Information
# ---------------------------------------------------------------------------

class ProjectInfo(BaseModel):
    project_name: str
    build_tool: Literal["maven", "gradle"]
    packaging: str | None           # "jar" | "war" | None
    java_version: int | None
    spring_boot_version: str | None
    spring_framework_version: str | None


# ---------------------------------------------------------------------------
# Section 2 — Dependency Analysis
# ---------------------------------------------------------------------------

class DependencyInfo(BaseModel):
    group_id: str
    artifact_id: str
    current_version: str | None
    recommended_version: str | None
    upgrade_required: bool
    upgrade_priority: Literal["High", "Medium", "Low"]
    compatibility_notes: str


class DependencyAnalysis(BaseModel):
    total_dependencies: int
    dependencies_requiring_upgrade: int
    dependencies: list[DependencyInfo]


# ---------------------------------------------------------------------------
# Section 3 — Java Migration Analysis
# ---------------------------------------------------------------------------

class JavaMigrationAnalysis(BaseModel):
    current_version: int | None
    target_version: int                 # always 21
    migration_supported: bool
    risk_level: Literal["Low", "Medium", "High"]
    migration_notes: list[str]


# ---------------------------------------------------------------------------
# Section 4 — Spring Boot Migration
# ---------------------------------------------------------------------------

class SpringBootMigration(BaseModel):
    current_version: str | None
    recommended_version: str            # "3.3.x"
    upgrade_required: bool
    breaking_changes: list[str]


# ---------------------------------------------------------------------------
# Section 5 — Code Refactoring Analysis
# ---------------------------------------------------------------------------

class RefactoringItem(BaseModel):
    category: str
    description: str
    files_affected: int
    risk_level: Literal["Low", "Medium", "High"]


class CodeRefactoringAnalysis(BaseModel):
    total_java_files: int
    files_likely_to_change: int
    estimated_imports_affected: int
    estimated_effort: Literal["Low", "Medium", "High"]
    overall_risk: Literal["Low", "Medium", "High"]
    refactoring_items: list[RefactoringItem]


# ---------------------------------------------------------------------------
# Section 6 — Build Configuration
# ---------------------------------------------------------------------------

class PluginInfo(BaseModel):
    artifact_id: str
    current_version: str | None
    recommended_version: str | None
    update_required: bool


class BuildConfiguration(BaseModel):
    build_tool: str
    source_compatibility: str | None
    target_compatibility: str | None
    encoding: str | None
    compiler_plugin: PluginInfo | None
    surefire_plugin: PluginInfo | None
    other_plugins_requiring_update: list[PluginInfo]


# ---------------------------------------------------------------------------
# Section 7 — Database Analysis
# ---------------------------------------------------------------------------

class DatabaseInfo(BaseModel):
    database: str
    driver_artifact: str
    current_version: str | None
    recommended_version: str | None
    compatibility_notes: str


class DatabaseAnalysis(BaseModel):
    databases_detected: list[DatabaseInfo]
    no_database_detected: bool


# ---------------------------------------------------------------------------
# Section 8 — Docker Readiness
# ---------------------------------------------------------------------------

class DockerReadiness(BaseModel):
    dockerfile_exists: bool
    docker_compose_exists: bool
    recommendations: list[str]


# ---------------------------------------------------------------------------
# Section 9 — Migration Summary
# ---------------------------------------------------------------------------

class MigrationSummary(BaseModel):
    current_java: int | None
    target_java: int
    current_spring_boot: str | None
    target_spring_boot: str
    total_dependencies: int
    dependencies_to_upgrade: int
    estimated_files_to_change: int
    migration_complexity: Literal["Low", "Medium", "High"]
    migration_confidence: Literal["Low", "Medium", "High"]
    top_risks: list[str]


# ---------------------------------------------------------------------------
# Root report
# ---------------------------------------------------------------------------

class AssessmentReport(BaseModel):
    project_id: str
    status: Literal["SUCCESS", "FAILED"]
    report_url: str                     # e.g. /assessment/{project_id}/report
    project_info: ProjectInfo
    dependency_analysis: DependencyAnalysis
    java_migration: JavaMigrationAnalysis
    spring_boot_migration: SpringBootMigration
    code_refactoring: CodeRefactoringAnalysis
    build_configuration: BuildConfiguration
    database_analysis: DatabaseAnalysis
    docker_readiness: DockerReadiness
    migration_summary: MigrationSummary
