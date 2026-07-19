import logging
import re
from pathlib import Path

from app.models.build import BuildError

logger = logging.getLogger(__name__)

# Maven compiler error line pattern:
# [ERROR] /abs/path/To/File.java:[42,8] error message here
_COMPILE_ERROR_RE = re.compile(
    r"\[ERROR\]\s+(.+?\.java):\[(\d+),\d+\]\s+(.+)"
)

# Simpler fallback: [ERROR] some message
_GENERIC_ERROR_RE = re.compile(r"\[ERROR\]\s+(.+)")

# Number of source lines to include around the error line for context
_CONTEXT_LINES = 8


def parse_first_error(maven_output: str, project_dir: Path) -> BuildError | None:
    """
    Scan Maven output for the first compilation error.
    Returns a BuildError with file path, line number, message, and a
    source snippet — or None if no parseable error is found.

    Why only the first error?
    Subsequent errors are often cascading failures caused by the first one.
    Fixing the root cause usually resolves the chain.
    """
    for line in maven_output.splitlines():
        m = _COMPILE_ERROR_RE.search(line)
        if m:
            raw_path, line_no_str, message = m.group(1), m.group(2), m.group(3)
            line_no = int(line_no_str)
            snippet = _read_snippet(Path(raw_path), line_no)

            logger.info(
                "First compile error: %s line %d — %s",
                raw_path, line_no, message[:80],
            )
            return BuildError(
                file_path=raw_path,
                line_number=line_no,
                error_message=message.strip(),
                raw_snippet=snippet,
            )

    # Fallback — no file:line pattern found, grab first [ERROR] line
    for line in maven_output.splitlines():
        m = _GENERIC_ERROR_RE.search(line)
        if m:
            msg = m.group(1).strip()
            if msg and "BUILD FAILURE" not in msg:
                logger.info("Generic build error: %s", msg[:120])
                return BuildError(
                    file_path="unknown",
                    line_number=None,
                    error_message=msg,
                    raw_snippet="",
                )

    logger.warning("Could not parse any error from Maven output")
    return None


def _read_snippet(file_path: Path, error_line: int) -> str:
    """
    Read _CONTEXT_LINES lines before and after error_line from the source file.
    Returns an empty string if the file cannot be read.
    """
    if not file_path.exists():
        return ""

    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ""

    start = max(0, error_line - _CONTEXT_LINES - 1)
    end   = min(len(lines), error_line + _CONTEXT_LINES)

    numbered = []
    for i, text in enumerate(lines[start:end], start=start + 1):
        marker = ">>>" if i == error_line else "   "
        numbered.append(f"{marker} {i:4d} | {text}")

    return "\n".join(numbered)
