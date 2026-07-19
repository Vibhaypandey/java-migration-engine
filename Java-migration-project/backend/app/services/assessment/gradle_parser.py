import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Matches: implementation 'group:artifact:version'  or  implementation("group:artifact:version")
_DEP_PATTERN = re.compile(
    r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation|annotationProcessor)\s*[("']"""
    r"""([a-zA-Z0-9.\-_]+):([a-zA-Z0-9.\-_]+)(?::([a-zA-Z0-9.\-_]+))?[)"']""",
    re.MULTILINE,
)

# Matches: id 'org.springframework.boot' version '3.2.0'
_PLUGIN_PATTERN = re.compile(
    r"""id\s*[("']([a-zA-Z0-9.\-_]+)[)"']\s*version\s*[("']([a-zA-Z0-9.\-_]+)[)"']""",
    re.MULTILINE,
)

_JAVA_PATTERNS = [
    re.compile(r"""(?:source|target)Compatibility\s*=\s*['"']?(?:JavaVersion\.VERSION_)?(\d+)"""),
    re.compile(r"""jvmTarget\s*=\s*['"](\d+)['"]"""),
    re.compile(r"""JavaLanguageVersion\.of\((\d+)\)"""),
    re.compile(r"""\brelease\s*=\s*(\d+)"""),
]

_SPRING_BOOT_PLUGIN = "org.springframework.boot"


def parse_gradle(build_path: Path) -> dict:
    """
    Parse a Gradle build file and return the same dict shape as maven_parser.parse_pom().
    Works for both Groovy DSL (build.gradle) and Kotlin DSL (build.gradle.kts).
    """
    try:
        text = build_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        logger.error("Cannot read Gradle build file: %s", exc)
        return {}

    project_name = build_path.parent.name
    java_version = _detect_java_version(text)
    spring_boot_version = None
    plugins = []

    for m in _PLUGIN_PATTERN.finditer(text):
        plugin_id, version = m.group(1), m.group(2)
        plugins.append({"group_id": "gradle-plugin", "artifact_id": plugin_id, "version": version})
        if plugin_id == _SPRING_BOOT_PLUGIN:
            spring_boot_version = version

    dependencies = []
    for m in _DEP_PATTERN.finditer(text):
        dependencies.append({
            "group_id": m.group(1),
            "artifact_id": m.group(2),
            "version": m.group(3),
        })

    # Detect encoding hint
    enc_match = re.search(r"""compileJava\.options\.encoding\s*=\s*['"]([^'"]+)['"]""", text)
    encoding = enc_match.group(1) if enc_match else None

    logger.info(
        "build.gradle parsed: project=%s, java=%s, spring_boot=%s, deps=%d, plugins=%d",
        project_name, java_version, spring_boot_version, len(dependencies), len(plugins),
    )

    return {
        "project_name": project_name,
        "group_id": None,
        "artifact_id": project_name,
        "version": None,
        "packaging": "jar",
        "java_version": java_version,
        "source_compatibility": str(java_version) if java_version else None,
        "target_compatibility": str(java_version) if java_version else None,
        "encoding": encoding,
        "spring_boot_version": spring_boot_version,
        "spring_framework_version": None,
        "dependencies": dependencies,
        "plugins": plugins,
    }


def _detect_java_version(text: str) -> int | None:
    for pattern in _JAVA_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None
