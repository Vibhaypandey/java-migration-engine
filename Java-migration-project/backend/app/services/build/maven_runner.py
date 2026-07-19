import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Maven timeout — 10 minutes per attempt is generous for any real project
_TIMEOUT_SECONDS = 600


@dataclass
class MavenRunResult:
    exit_code: int
    stdout: str
    stderr: str
    combined: str       # stdout + stderr interleaved (what the user sees)
    duration: float
    log_path: Path


def run_maven_build(project_id: str, project_dir: Path, attempt: int) -> MavenRunResult:
    """
    Execute `mvn clean package -B` (or mvnw on Unix) inside project_dir.

    -B flag = batch mode: no ANSI colours, no interactive prompts.
    -DskipTests is NOT set — we want test failures to surface too.

    Logs are written to build-logs/{project_id}/attempt_{n}.log so every
    attempt is preserved for the final report.

    Returns MavenRunResult regardless of success/failure.
    Raises RuntimeError only if Maven cannot be found at all.
    """
    log_dir = settings.build_logs_dir / project_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"attempt_{attempt}.log"

    cmd = _resolve_maven_command(project_dir)
    logger.info("[Build %s] Attempt %d — running: %s", project_id, attempt, " ".join(cmd))
    logger.info("[Build %s] Working dir: %s", project_id, project_dir)
    logger.info("[Build %s] Log: %s", project_id, log_path)

    start = time.monotonic()

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            env={**os.environ, "JAVA_TOOL_OPTIONS": ""},  # suppress JVM startup noise
        )
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        msg = f"Maven build timed out after {_TIMEOUT_SECONDS}s"
        logger.error("[Build %s] %s", project_id, msg)
        log_path.write_text(msg, encoding="utf-8")
        return MavenRunResult(
            exit_code=1, stdout="", stderr=msg,
            combined=msg, duration=duration, log_path=log_path,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Maven executable not found. Install Maven and ensure 'mvn' is on PATH."
        ) from exc

    duration = time.monotonic() - start
    combined = _interleave(proc.stdout, proc.stderr)

    # Write full log to disk
    log_path.write_text(combined, encoding="utf-8")

    status_word = "SUCCESS" if proc.returncode == 0 else "FAILED"
    logger.info(
        "[Build %s] Attempt %d %s (exit=%d, %.1fs)",
        project_id, attempt, status_word, proc.returncode, duration,
    )

    return MavenRunResult(
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        combined=combined,
        duration=duration,
        log_path=log_path,
    )


def find_jar(project_dir: Path) -> Path | None:
    """
    Locate the generated JAR/WAR under target/.
    Skips *-sources.jar and *-javadoc.jar.
    Returns the first match or None.
    """
    for pattern in ("target/*.jar", "target/*.war"):
        for p in project_dir.glob(pattern):
            if not any(skip in p.name for skip in ("-sources", "-javadoc", "-tests")):
                return p
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_maven_command(project_dir: Path) -> list[str]:
    """
    Prefer Maven Wrapper (mvnw / mvnw.cmd) if present in the project root.
    Falls back to system `mvn`.
    """
    is_windows = platform.system() == "Windows"

    wrapper = project_dir / ("mvnw.cmd" if is_windows else "mvnw")
    if wrapper.exists():
        logger.info("Using Maven Wrapper: %s", wrapper)
        cmd = [str(wrapper)]
    else:
        cmd = ["mvn"]

    return cmd + ["clean", "package", "-B"]


def _interleave(stdout: str, stderr: str) -> str:
    """
    Combine stdout and stderr into a single string.
    Maven writes almost everything to stdout in batch mode, but some
    plugin warnings go to stderr — we want both in the log.
    """
    parts = []
    if stdout.strip():
        parts.append(stdout)
    if stderr.strip():
        parts.append("--- STDERR ---\n" + stderr)
    return "\n".join(parts)
