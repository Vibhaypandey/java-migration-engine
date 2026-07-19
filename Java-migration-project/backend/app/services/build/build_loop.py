import logging
import shutil
from pathlib import Path

from app.config import settings
from app.models.build import AttemptRecord, BuildResult, BuildError
from app.services.build.maven_runner import run_maven_build, find_jar
from app.services.build.error_parser import parse_first_error
from app.services.build.ai_fix_service import request_ai_fix
from app.services.build.file_patcher import apply_fixes
from app.services.build.build_html import render_build_report

logger = logging.getLogger(__name__)


def run_build_loop(project_id: str, project_dir: Path) -> BuildResult:
    """
    Phase 3 Build Loop.

    Algorithm:
      for attempt in 1..MAX_RETRIES:
          run mvn clean package
          if success → done
          parse first error
          if no error parseable → stop (can't fix what we can't read)
          request AI fix
          if AI returns nothing → stop (no key or API failure)
          backup + patch files
          continue

    Saves a Build Report HTML to workspace/reports/{project_id}_build.html.
    Returns BuildResult regardless of outcome.
    """
    max_retries = settings.build_max_retries
    logger.info("═══ Build loop started: %s (max %d attempts) ═══", project_id, max_retries)

    attempts: list[AttemptRecord] = []
    all_modified_files: list[str] = []
    errors_fixed = 0
    pom_path = next(project_dir.rglob("pom.xml"), None)

    for attempt_num in range(1, max_retries + 1):
        logger.info("─── Attempt %d/%d ───", attempt_num, max_retries)

        # ── Run Maven ─────────────────────────────────────────────────────────
        run = run_maven_build(project_id, project_dir, attempt_num)
        success = run.exit_code == 0

        if success:
            logger.info("Build SUCCESS on attempt %d", attempt_num)
            jar = find_jar(project_dir)
            attempts.append(AttemptRecord(
                attempt_number=attempt_num,
                status="SUCCESS",
                exit_code=run.exit_code,
                duration_seconds=run.duration,
                log_file=str(run.log_path),
                error=None,
                files_modified=[],
                ai_fix_reason="",
            ))
            return _finalise(
                project_id=project_id,
                status="SUCCESS",
                jar_path=jar,
                attempts=attempts,
                errors_fixed=errors_fixed,
                all_modified=all_modified_files,
                manual=False,
            )

        # ── Build failed — parse first error ──────────────────────────────────
        logger.info("Build FAILED (exit=%d) — parsing error", run.exit_code)
        error = parse_first_error(run.combined, project_dir)

        if error is None:
            logger.warning("Cannot parse error from output — stopping loop")
            attempts.append(AttemptRecord(
                attempt_number=attempt_num,
                status="FAILED",
                exit_code=run.exit_code,
                duration_seconds=run.duration,
                log_file=str(run.log_path),
                error=None,
                files_modified=[],
                ai_fix_reason="Could not parse error from Maven output",
            ))
            break

        # ── Request AI fix ────────────────────────────────────────────────────
        logger.info("Requesting AI fix for: %s line %s", error.file_path, error.line_number)
        file_map = request_ai_fix(error, project_dir, pom_path, attempt_num)

        if not file_map:
            logger.warning("AI returned no fix — stopping loop")
            attempts.append(AttemptRecord(
                attempt_number=attempt_num,
                status="FAILED",
                exit_code=run.exit_code,
                duration_seconds=run.duration,
                log_file=str(run.log_path),
                error=error,
                files_modified=[],
                ai_fix_reason="AI fix unavailable (no API key or API error)",
            ))
            break

        # ── Backup + patch ────────────────────────────────────────────────────
        patch_backup = settings.backups_dir / f"{project_id}_build_attempt_{attempt_num}"
        patch_backup.mkdir(parents=True, exist_ok=True)

        modified = apply_fixes(file_map, project_dir, patch_backup)
        all_modified_files.extend(m for m in modified if m not in all_modified_files)
        errors_fixed += 1

        logger.info("Attempt %d: patched %d file(s): %s", attempt_num, len(modified), modified)

        attempts.append(AttemptRecord(
            attempt_number=attempt_num,
            status="FAILED",
            exit_code=run.exit_code,
            duration_seconds=run.duration,
            log_file=str(run.log_path),
            error=error,
            files_modified=modified,
            ai_fix_reason=f"AI fix applied to: {', '.join(modified)}",
        ))

    # ── Max retries exceeded ──────────────────────────────────────────────────
    logger.warning("Build loop exhausted %d attempts without success", max_retries)
    return _finalise(
        project_id=project_id,
        status="FAILED",
        jar_path=None,
        attempts=attempts,
        errors_fixed=errors_fixed,
        all_modified=all_modified_files,
        manual=True,
    )


def _finalise(
    project_id: str,
    status: str,
    jar_path: Path | None,
    attempts: list[AttemptRecord],
    errors_fixed: int,
    all_modified: list[str],
    manual: bool,
) -> BuildResult:
    """Assemble BuildResult, save HTML report, return."""

    # Copy JAR to workspace/output/ for easy retrieval
    jar_location = ""
    jar_generated = jar_path is not None and jar_path.exists()
    if jar_generated:
        dest = settings.output_dir / jar_path.name
        shutil.copy2(jar_path, dest)
        jar_location = str(dest)
        logger.info("JAR copied to output: %s", dest)

    result = BuildResult(
        project_id=project_id,
        status=status,
        build_status=status,
        jar_generated=jar_generated,
        jar_location=jar_location,
        total_attempts=len(attempts),
        errors_fixed=errors_fixed,
        files_modified=all_modified,
        attempts=attempts,
        build_report_url=f"/build/{project_id}/report",
        manual_intervention_required=manual,
    )

    # Save HTML report
    try:
        html = render_build_report(result)
        report_path = settings.reports_dir / f"{project_id}_build.html"
        report_path.write_text(html, encoding="utf-8")
        logger.info("Build report saved: %s", report_path)
    except Exception as exc:
        logger.error("Failed to save build report: %s", exc)

    logger.info(
        "═══ Build loop %s: %d attempts, %d errors fixed, JAR=%s ═══",
        status, len(attempts), errors_fixed, jar_generated,
    )
    return result
