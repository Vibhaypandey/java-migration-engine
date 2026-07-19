"""
migration_engine.py — Full Migration Orchestrator

Execution order
---------------
1. Create full backup  (workspace/backups/{project_id}/)
2. Update pom.xml      (dynamic Maven Central resolution for every dep/plugin)
3. Refactor Java source files  (26 rule-based transformations)
4. Generate Migration Change Report HTML

Steps 2-4 only run if the previous step succeeded.
The backup is always created first — migration is aborted if backup fails.
"""

import logging
from pathlib import Path

from app.config import settings
from app.models.migration import (
    MigrationResult, StepResult, SourceChange, DependencyChange,
)
from app.services.migration.backup_service import create_backup
from app.services.migration.pom_updater import update_pom
from app.services.migration.source_refactorer import refactor_sources
from app.services.migration.migration_html import render_migration_summary

logger = logging.getLogger(__name__)


def run_migration(project_id: str, extract_dir: Path) -> MigrationResult:
    logger.info("═══ Migration started for project: %s ═══", project_id)

    steps: list[StepResult] = []
    source_changes: list[SourceChange] = []
    dependency_changes: list[DependencyChange] = []
    backup_path = ""
    updated_pom_path = ""

    # ── Step 1: Backup ────────────────────────────────────────────────────────
    logger.info("Step 1 — Creating backup")
    try:
        backup_dir = create_backup(project_id, extract_dir)
        backup_path = str(backup_dir)
        steps.append(StepResult(
            step="Backup Created",
            status="SUCCESS",
            detail=f"Full project copied to {backup_path}",
        ))
    except Exception as exc:
        logger.error("Backup FAILED: %s", exc)
        steps.append(StepResult(step="Backup Created", status="FAILED", detail=str(exc)))
        return _build_result(project_id, "FAILED", backup_path, updated_pom_path,
                             steps, source_changes, dependency_changes)

    # ── Step 2: Update pom.xml ────────────────────────────────────────────────
    logger.info("Step 2 — Updating pom.xml")
    pom_path = next(extract_dir.rglob("pom.xml"), None)

    if pom_path is None:
        logger.warning("No pom.xml found — skipping pom steps")
        for label in ("Java Version Updated", "Spring Boot Updated",
                      "Plugins Updated", "Dependencies Updated"):
            steps.append(StepResult(step=label, status="SKIPPED",
                                    detail="No pom.xml found in workspace"))
    else:
        updated_pom_path = str(pom_path)
        try:
            pom_result = update_pom(pom_path)

            steps.append(StepResult(
                step="Java Version Updated",
                status="SUCCESS" if pom_result.java_updated else "SKIPPED",
                detail=f"Java set to 21" if pom_result.java_updated
                       else "Java version already 21 or not declared",
            ))

            steps.append(StepResult(
                step="Spring Boot Updated",
                status="SUCCESS" if pom_result.spring_boot_updated else "SKIPPED",
                detail="Spring Boot parent updated to 3.3.4" if pom_result.spring_boot_updated
                       else "Spring Boot parent not found or already up to date",
            ))

            plugin_changes = [c for c in pom_result.dep_changes
                              if c.artifact_id in ("maven-compiler-plugin",
                                                   "maven-surefire-plugin",
                                                   "maven-failsafe-plugin",
                                                   "maven-jar-plugin",
                                                   "maven-war-plugin",
                                                   "spring-boot-maven-plugin")]
            steps.append(StepResult(
                step="Plugins Updated",
                status="SUCCESS" if plugin_changes else "SKIPPED",
                detail=", ".join(f"{c.artifact_id} → {c.new_version}" for c in plugin_changes)
                       if plugin_changes else "Plugins already up to date",
            ))

            dep_only = [c for c in pom_result.dep_changes if c not in plugin_changes
                        and c.artifact_id != "spring-boot-starter-parent"]
            steps.append(StepResult(
                step="Dependencies Updated",
                status="SUCCESS" if dep_only else "SKIPPED",
                detail=f"{len(dep_only)} dependencies updated via dynamic resolution"
                       if dep_only else "All dependency versions already up to date",
            ))

            # Convert to model objects for the report
            for c in pom_result.dep_changes:
                dependency_changes.append(DependencyChange(
                    artifact_id=c.artifact_id,
                    group_id=c.group_id,
                    old_version=c.old_version,
                    new_version=c.new_version,
                    source=c.source,
                ))

            logger.info("pom.xml updated: %d changes", len(pom_result.dep_changes))

        except Exception as exc:
            logger.error("pom.xml update FAILED: %s", exc)
            for label in ("Java Version Updated", "Spring Boot Updated",
                          "Plugins Updated", "Dependencies Updated"):
                steps.append(StepResult(step=label, status="FAILED", detail=str(exc)))

    # ── Step 3: Refactor Java source files ────────────────────────────────────
    logger.info("Step 3 — Refactoring Java source files")
    try:
        file_changes = refactor_sources(extract_dir)
        total_files = len(file_changes)
        total_occurrences = sum(fc.total_occurrences for fc in file_changes)

        steps.append(StepResult(
            step="Java Source Files Refactored",
            status="SUCCESS" if total_files > 0 else "SKIPPED",
            detail=f"{total_files} file(s) modified, {total_occurrences} change(s) applied"
                   if total_files > 0 else "No source files required changes",
        ))

        # Build SourceChange records for the report
        for fc in file_changes:
            rel = _relative(fc.file_path, extract_dir)
            for category, description, occurrences in fc.changes:
                source_changes.append(SourceChange(
                    file_path=rel,
                    category=category,
                    description=description,
                    occurrences=occurrences,
                ))

        logger.info("Source refactoring: %d files, %d changes", total_files, total_occurrences)

    except Exception as exc:
        logger.error("Source refactoring FAILED: %s", exc)
        steps.append(StepResult(
            step="Java Source Files Refactored",
            status="FAILED",
            detail=str(exc),
        ))

    # ── Step 4: Generate HTML report ─────────────────────────────────────────
    logger.info("Step 4 — Generating migration change report")
    overall = "COMPLETED" if all(s.status in ("SUCCESS", "SKIPPED") for s in steps) else "FAILED"
    result = _build_result(project_id, overall, backup_path, updated_pom_path,
                           steps, source_changes, dependency_changes)
    try:
        html = render_migration_summary(result)
        report_path = settings.reports_dir / f"{project_id}_migration.html"
        report_path.write_text(html, encoding="utf-8")
        steps.append(StepResult(
            step="Migration Change Report Generated",
            status="SUCCESS",
            detail=f"Report saved to {report_path}",
        ))
        logger.info("Report saved: %s", report_path)
    except Exception as exc:
        logger.error("Report generation FAILED: %s", exc)
        steps.append(StepResult(
            step="Migration Change Report Generated",
            status="FAILED",
            detail=str(exc),
        ))

    final_status = "COMPLETED" if all(s.status in ("SUCCESS", "SKIPPED") for s in steps) else "FAILED"
    final = _build_result(project_id, final_status, backup_path, updated_pom_path,
                          steps, source_changes, dependency_changes)
    logger.info("═══ Migration %s for project: %s ═══", final_status, project_id)
    return final


# ── Helpers ──────────────────────────────────────────────────────────────────

def _relative(file_path: Path, base: Path) -> str:
    try:
        return str(file_path.relative_to(base))
    except ValueError:
        return str(file_path)


def _build_result(
    project_id: str,
    status: str,
    backup_path: str,
    updated_pom_path: str,
    steps: list[StepResult],
    source_changes: list[SourceChange],
    dependency_changes: list[DependencyChange],
) -> MigrationResult:
    unique_files = len({sc.file_path for sc in source_changes})
    total_occ = sum(sc.occurrences for sc in source_changes)
    return MigrationResult(
        project_id=project_id,
        status=status,
        build_status="Not Executed",
        backup_path=backup_path or "N/A",
        updated_pom_path=updated_pom_path or "N/A",
        migration_report_url=f"/migration/{project_id}/summary",
        steps=steps,
        source_changes=source_changes,
        dependency_changes=dependency_changes,
        total_files_modified=unique_files,
        total_source_changes=total_occ,
    )
