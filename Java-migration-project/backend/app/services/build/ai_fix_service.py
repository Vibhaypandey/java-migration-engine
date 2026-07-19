import json
import logging
import re
from pathlib import Path

from app.config import settings
from app.models.build import BuildError

logger = logging.getLogger(__name__)

# System prompt — instructs the model to be surgical and return structured JSON
_SYSTEM_PROMPT = """You are an expert Java migration engineer.
A Maven build has failed during a Java 11 → Java 21 / Spring Boot 3.x migration.

Your job:
1. Identify the ROOT CAUSE of the compilation error.
2. Produce the MINIMAL fix — modify only the file(s) directly responsible.
3. Do NOT rewrite unrelated files.
4. Do NOT change business logic.
5. Preserve all existing imports that are still valid.
6. Return ONLY a JSON object in this exact format:

{
  "root_cause": "one sentence explanation",
  "files": {
    "/absolute/path/to/File.java": "complete corrected file content here"
  }
}

If the fix requires changes to pom.xml instead of a Java file, include pom.xml in files.
Do not include markdown fences. Return raw JSON only."""


def request_ai_fix(
    error: BuildError,
    project_dir: Path,
    pom_path: Path | None,
    attempt: int,
) -> dict[str, str]:
    """
    Send the error context to OpenAI and return a {file_path: new_content} dict.

    Returns an empty dict if:
    - OPENAI_API_KEY is not configured
    - The API call fails
    - The response cannot be parsed

    Never raises — build loop must continue even if AI is unavailable.
    """
    if not settings.openai_api_key:
        logger.warning("[AI] OPENAI_API_KEY not set — skipping AI fix for attempt %d", attempt)
        return {}

    try:
        from openai import OpenAI  # imported here so missing key doesn't crash startup
        client = OpenAI(api_key=settings.openai_api_key)
    except ImportError:
        logger.error("[AI] openai package not installed — run: pip install openai")
        return {}

    user_message = _build_user_message(error, project_dir, pom_path)
    logger.info("[AI] Requesting fix for: %s line %s (attempt %d)", error.file_path, error.line_number, attempt)

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.1,   # low temperature = deterministic, conservative fixes
            max_tokens=4096,
        )
    except Exception as exc:
        logger.error("[AI] API call failed: %s", exc)
        return {}

    raw = response.choices[0].message.content or ""
    logger.info("[AI] Response received (%d chars)", len(raw))

    return _parse_ai_response(raw)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_user_message(error: BuildError, project_dir: Path, pom_path: Path | None) -> str:
    """
    Build a focused prompt containing only what the AI needs:
    - The error message and location
    - The affected source file content
    - The pom.xml (only if the error is dependency/plugin related)
    """
    parts = [
        f"## Build Error (Attempt context)",
        f"**File:** {error.file_path}",
        f"**Line:** {error.line_number or 'unknown'}",
        f"**Error:** {error.error_message}",
        "",
        "## Affected Source Code",
        "```java",
        error.raw_snippet or "(snippet unavailable)",
        "```",
    ]

    # Include full file if snippet is available and file is readable
    file_path = Path(error.file_path)
    if file_path.exists() and file_path.suffix == ".java":
        try:
            full_source = file_path.read_text(encoding="utf-8", errors="ignore")
            parts += [
                "",
                "## Full File Content",
                "```java",
                full_source[:6000],  # cap at 6000 chars to stay within token budget
                "```",
            ]
        except OSError:
            pass

    # Include pom.xml for dependency/import errors
    if pom_path and pom_path.exists() and _is_dependency_error(error.error_message):
        try:
            pom_content = pom_path.read_text(encoding="utf-8", errors="ignore")
            parts += [
                "",
                "## Current pom.xml",
                "```xml",
                pom_content[:4000],
                "```",
            ]
        except OSError:
            pass

    parts += [
        "",
        "Fix the compilation error. Return only the JSON object as specified.",
    ]

    return "\n".join(parts)


def _is_dependency_error(message: str) -> bool:
    """Heuristic: does this error look like a missing class / package?"""
    keywords = ("cannot find symbol", "package does not exist", "import", "javax.", "jakarta.")
    return any(kw in message.lower() for kw in keywords)


def _parse_ai_response(raw: str) -> dict[str, str]:
    """
    Extract the JSON object from the AI response.
    Handles responses that accidentally include markdown fences.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find a JSON object anywhere in the response
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            logger.error("[AI] Could not parse JSON from response")
            return {}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            logger.error("[AI] JSON parse failed even after extraction")
            return {}

    root_cause = data.get("root_cause", "")
    files = data.get("files", {})

    if root_cause:
        logger.info("[AI] Root cause: %s", root_cause)

    if not isinstance(files, dict):
        logger.error("[AI] 'files' key is not a dict in AI response")
        return {}

    logger.info("[AI] Fix targets %d file(s): %s", len(files), list(files.keys()))
    return files
