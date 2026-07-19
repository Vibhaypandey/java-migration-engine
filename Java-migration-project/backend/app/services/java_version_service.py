import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MIN_JAVA_VERSION = 11

# Canonical build file names this tool recognises
_MAVEN_BUILD_FILE = "pom.xml"
_GRADLE_BUILD_FILES = ("build.gradle", "build.gradle.kts")

# Maps legacy Maven source/target strings "1.6" → 6, "1.8" → 8, etc.
_LEGACY_VERSION_MAP = {f"1.{v}": v for v in range(1, 10)}


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

@dataclass
class ProjectInfo:
    build_tool: str       # "maven" | "gradle"
    java_version: int | None  # detected major version, None if undetectable


# ---------------------------------------------------------------------------
# Version string parsing
# ---------------------------------------------------------------------------

def _parse_version(raw: str) -> int | None:
    """
    Normalise any Java version string to an integer major version.
    Covers: "8", "11", "17", "21", "1.8", "1.6", "17.0.1"
    """
    raw = raw.strip()
    if raw in _LEGACY_VERSION_MAP:
        return _LEGACY_VERSION_MAP[raw]
    match = re.match(r"^(\d+)", raw)
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Maven (pom.xml) — read from raw bytes, no temp file needed
# ---------------------------------------------------------------------------

def _version_from_pom(content: bytes) -> int | None:
    """
    Parse pom.xml bytes and extract the Java version from:
      1. <properties><maven.compiler.source>
      2. <properties><maven.compiler.target>
      3. <properties><java.version>          (Spring Boot convention)
      4. <maven-compiler-plugin><configuration><source|target|release>
    Returns the first version found, or None.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        logger.warning("pom.xml parse error: %s", exc)
        return None

    # pom.xml carries a default XML namespace — extract it so find() works
    ns_match = re.match(r"\{(.*?)\}", root.tag)
    ns = f"{{{ns_match.group(1)}}}" if ns_match else ""

    # --- <properties> block ---
    props = root.find(f"{ns}properties")
    if props is not None:
        for key in ("maven.compiler.source", "maven.compiler.target", "java.version"):
            node = props.find(f"{ns}{key}")
            if node is not None and node.text:
                version = _parse_version(node.text)
                if version:
                    logger.info("Maven: detected Java %d via <properties><%s>", version, key)
                    return version

    # --- maven-compiler-plugin <configuration> block ---
    for plugin in root.iter(f"{ns}plugin"):
        artifact_id = plugin.find(f"{ns}artifactId")
        if artifact_id is not None and artifact_id.text == "maven-compiler-plugin":
            config = plugin.find(f"{ns}configuration")
            if config is not None:
                for key in ("source", "target", "release"):
                    node = config.find(f"{ns}{key}")
                    if node is not None and node.text:
                        version = _parse_version(node.text)
                        if version:
                            logger.info("Maven: detected Java %d via compiler-plugin <%s>", version, key)
                            return version

    logger.info("Maven: pom.xml found but no Java version declared")
    return None


# ---------------------------------------------------------------------------
# Gradle (build.gradle / build.gradle.kts) — regex scan of raw text
# ---------------------------------------------------------------------------

def _version_from_gradle(content: bytes) -> int | None:
    """
    Scan Gradle build script text for Java version declarations.
    Handles both Groovy DSL and Kotlin DSL patterns:
      - sourceCompatibility = '11'  /  sourceCompatibility = JavaVersion.VERSION_11
      - targetCompatibility = '17'
      - jvmTarget = "17"            (Kotlin plugin)
      - java { toolchain { languageVersion = JavaLanguageVersion.of(21) } }
      - release = 17                (compiler options)
    Returns the first version found, or None.
    """
    text = content.decode("utf-8", errors="ignore")

    patterns = [
        # sourceCompatibility / targetCompatibility = '11' or = JavaVersion.VERSION_11
        r"(?:source|target)Compatibility\s*=\s*['\"]?(?:JavaVersion\.VERSION_)?(\d+)",
        # jvmTarget = "17"
        r"jvmTarget\s*=\s*['\"](\d+)['\"]",
        # JavaLanguageVersion.of(21)
        r"JavaLanguageVersion\.of\((\d+)\)",
        # release = 17
        r"\brelease\s*=\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            version = _parse_version(match.group(1))
            if version:
                logger.info("Gradle: detected Java %d via pattern '%s'", version, pattern)
                return version

    logger.info("Gradle: build file found but no Java version declared")
    return None


# ---------------------------------------------------------------------------
# ZIP inspection — entry point, no disk writes
# ---------------------------------------------------------------------------

def _find_build_file(members: list[str]) -> tuple[str, str] | None:
    """
    Scan ZIP member names for a recognised build file.
    Returns (member_name, build_tool) or None.

    Walks all members so it works whether the ZIP root is flat or has a
    top-level project folder (e.g. my-project/pom.xml).
    """
    for member in members:
        filename = member.split("/")[-1]  # basename only
        if filename == _MAVEN_BUILD_FILE:
            logger.info("Found Maven build file: %s", member)
            return member, "maven"
        if filename in _GRADLE_BUILD_FILES:
            logger.info("Found Gradle build file: %s", member)
            return member, "gradle"
    return None


def validate_java_project_in_zip(zf: zipfile.ZipFile) -> ProjectInfo:
    """
    Inspect an open ZipFile in-memory and return a ProjectInfo.

    Raises:
        ValueError("not_java_project")   — no Maven or Gradle build file found
        ValueError("version_too_low")    — detected Java version < MIN_JAVA_VERSION
    """
    members = zf.namelist()
    logger.info("Inspecting ZIP with %d members", len(members))

    # Gate 1 — must contain a recognised build file
    result = _find_build_file(members)
    if result is None:
        logger.warning("ZIP rejected: no pom.xml or build.gradle found")
        raise ValueError("not_java_project")

    build_file_member, build_tool = result

    # Gate 2 — read the build file bytes directly from the ZIP (no extraction)
    build_content = zf.read(build_file_member)

    if build_tool == "maven":
        java_version = _version_from_pom(build_content)
    else:
        java_version = _version_from_gradle(build_content)

    # Gate 3 — version must be >= MIN_JAVA_VERSION if it could be determined
    if java_version is not None and java_version < MIN_JAVA_VERSION:
        logger.warning(
            "ZIP rejected: Java %d < minimum required Java %d", java_version, MIN_JAVA_VERSION
        )
        raise ValueError("version_too_low")

    logger.info(
        "ZIP accepted: build_tool=%s, java_version=%s",
        build_tool,
        java_version if java_version else "undetected",
    )
    return ProjectInfo(build_tool=build_tool, java_version=java_version)
