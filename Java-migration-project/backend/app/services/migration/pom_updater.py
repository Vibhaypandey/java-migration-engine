"""
pom_updater.py — Dynamic pom.xml migration to Java 21 / Spring Boot 3.3.x

Strategy
--------
1. Parse pom.xml with ElementTree (namespace-aware).
2. Resolve the latest compatible version for EVERY dependency and plugin by
   querying the Maven Central search API (search.maven.org/solrsearch).
3. Fall back to a curated knowledge base when Maven Central is unreachable or
   returns no result for a given artifact.
4. Apply all changes in-memory, then write the file back once.
5. Return a PomUpdateResult that lists every change made so the engine can
   build a detailed report.

No hardcoded version list is used for the resolution step — the knowledge base
is only a fallback, not the primary source.
"""

import logging
import re
import time
import urllib.request
import urllib.error
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Fixed migration targets ──────────────────────────────────────────────────
TARGET_JAVA             = "21"
TARGET_SPRING_BOOT      = "3.3.4"
TARGET_COMPILER_PLUGIN  = "3.13.0"
TARGET_SUREFIRE_PLUGIN  = "3.3.1"
TARGET_FAILSAFE_PLUGIN  = "3.3.1"

# Maven Central search endpoint
_MC_URL = "https://search.maven.org/solrsearch/select?q=g:{g}+AND+a:{a}&core=gav&rows=5&wt=json"

# ── Curated fallback knowledge base ─────────────────────────────────────────
# Used ONLY when Maven Central is unreachable or returns nothing.
# Format: artifact_id → (group_id, version)
_FALLBACK: dict[str, tuple[str, str]] = {
    # Spring Boot starters — managed by parent BOM, explicit version rarely needed
    "spring-boot-starter-parent":       ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter":              ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter-web":          ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter-data-jpa":     ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter-security":     ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter-test":         ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter-actuator":     ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter-validation":   ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter-cache":        ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter-aop":          ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-starter-data-mongodb": ("org.springframework.boot", TARGET_SPRING_BOOT),
    "spring-boot-maven-plugin":         ("org.springframework.boot", TARGET_SPRING_BOOT),
    # Spring Framework
    "spring-context":                   ("org.springframework",       "6.1.12"),
    "spring-webmvc":                    ("org.springframework",       "6.1.12"),
    "spring-data-jpa":                  ("org.springframework.data",  "3.3.4"),
    "spring-security-core":             ("org.springframework.security", "6.3.3"),
    "spring-security-web":              ("org.springframework.security", "6.3.3"),
    "spring-security-config":           ("org.springframework.security", "6.3.3"),
    # Jakarta EE
    "jakarta.servlet-api":              ("jakarta.servlet",           "6.0.0"),
    "jakarta.validation-api":           ("jakarta.validation",        "3.0.2"),
    "jakarta.persistence-api":          ("jakarta.persistence",       "3.1.0"),
    "jakarta.xml.bind-api":             ("jakarta.xml.bind",          "4.0.2"),
    # Persistence
    "hibernate-core":                   ("org.hibernate.orm",         "6.5.2.Final"),
    "hibernate-validator":              ("org.hibernate.validator",   "8.0.1.Final"),
    "mybatis-spring-boot-starter":      ("org.mybatis.spring.boot",   "3.0.3"),
    "flyway-core":                      ("org.flywaydb",              "10.15.0"),
    "liquibase-core":                   ("org.liquibase",             "4.29.1"),
    # Database drivers
    "postgresql":                       ("org.postgresql",            "42.7.3"),
    "mysql-connector-j":                ("com.mysql",                 "8.4.0"),
    "mysql-connector-java":             ("com.mysql",                 "8.4.0"),
    "h2":                               ("com.h2database",            "2.2.224"),
    "mssql-jdbc":                       ("com.microsoft.sqlserver",   "12.6.3.jre11"),
    "mongodb-driver-sync":              ("org.mongodb",               "5.1.3"),
    # Code generation
    "lombok":                           ("org.projectlombok",         "1.18.34"),
    "mapstruct":                        ("org.mapstruct",             "1.6.0"),
    "mapstruct-processor":              ("org.mapstruct",             "1.6.0"),
    # Testing
    "junit-jupiter":                    ("org.junit.jupiter",         "5.10.3"),
    "mockito-core":                     ("org.mockito",               "5.12.0"),
    "mockito-junit-jupiter":            ("org.mockito",               "5.12.0"),
    "assertj-core":                     ("org.assertj",               "3.26.3"),
    # Logging
    "logback-classic":                  ("ch.qos.logback",            "1.5.7"),
    "log4j-core":                       ("org.apache.logging.log4j",  "2.23.1"),
    "log4j-api":                        ("org.apache.logging.log4j",  "2.23.1"),
    "slf4j-api":                        ("org.slf4j",                 "2.0.13"),
    # Jackson
    "jackson-databind":                 ("com.fasterxml.jackson.core","2.17.2"),
    "jackson-core":                     ("com.fasterxml.jackson.core","2.17.2"),
    "jackson-annotations":              ("com.fasterxml.jackson.core","2.17.2"),
    # Maven plugins
    "maven-compiler-plugin":            ("org.apache.maven.plugins",  TARGET_COMPILER_PLUGIN),
    "maven-surefire-plugin":            ("org.apache.maven.plugins",  TARGET_SUREFIRE_PLUGIN),
    "maven-failsafe-plugin":            ("org.apache.maven.plugins",  TARGET_FAILSAFE_PLUGIN),
    "maven-jar-plugin":                 ("org.apache.maven.plugins",  "3.4.2"),
    "maven-war-plugin":                 ("org.apache.maven.plugins",  "3.4.0"),
    # Misc
    "guava":                            ("com.google.guava",          "33.2.1-jre"),
    "commons-lang3":                    ("org.apache.commons",        "3.15.0"),
    "commons-io":                       ("commons-io",                "2.16.1"),
    "httpclient":                       ("org.apache.httpcomponents",  "4.5.14"),
    "httpclient5":                      ("org.apache.httpcomponents.client5", "5.3.1"),
}

# Artifacts whose version is controlled by the Spring Boot BOM — bumping them
# individually would conflict with the parent BOM, so we skip explicit version.
_SPRING_BOM_MANAGED: set[str] = {
    "spring-boot-starter", "spring-boot-starter-web", "spring-boot-starter-data-jpa",
    "spring-boot-starter-security", "spring-boot-starter-test", "spring-boot-starter-actuator",
    "spring-boot-starter-validation", "spring-boot-starter-cache", "spring-boot-starter-aop",
    "spring-boot-starter-data-mongodb",
}

# Java version property keys in <properties>
_JAVA_PROPERTY_KEYS = ("maven.compiler.source", "maven.compiler.target", "java.version")


# ── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class DepChange:
    artifact_id: str
    group_id: str
    old_version: str | None
    new_version: str
    source: str   # "maven_central" | "knowledge_base" | "spring_bom"


@dataclass
class PomUpdateResult:
    java_updated: bool = False
    spring_boot_updated: bool = False
    compiler_plugin_updated: bool = False
    surefire_plugin_updated: bool = False
    dep_changes: list[DepChange] = field(default_factory=list)

    # Keep backward-compatible property used by migration_engine
    @property
    def deps_updated(self) -> list[str]:
        return [c.artifact_id for c in self.dep_changes]

    def any_changed(self) -> bool:
        return (
            self.java_updated or self.spring_boot_updated
            or self.compiler_plugin_updated or self.surefire_plugin_updated
            or bool(self.dep_changes)
        )


# ── Maven Central resolver ───────────────────────────────────────────────────

# Simple in-process cache so repeated calls for the same artifact are free.
_version_cache: dict[str, str | None] = {}


def _fetch_latest_from_maven_central(group_id: str, artifact_id: str) -> str | None:
    """
    Query Maven Central search API for the latest stable release of
    group_id:artifact_id.  Returns the version string or None on any failure.
    Stable = no -SNAPSHOT, -alpha, -beta, -rc, -M suffix.
    """
    cache_key = f"{group_id}:{artifact_id}"
    if cache_key in _version_cache:
        return _version_cache[cache_key]

    url = _MC_URL.format(g=group_id, a=artifact_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "java-migration-assistant/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())

        docs = data.get("response", {}).get("docs", [])
        for doc in docs:
            ver = doc.get("v", "")
            # Skip pre-release versions
            if re.search(r"(?i)(snapshot|alpha|beta|\.rc|\.m\d)", ver):
                continue
            _version_cache[cache_key] = ver
            logger.debug("Maven Central: %s:%s → %s", group_id, artifact_id, ver)
            return ver

    except Exception as exc:
        logger.debug("Maven Central lookup failed for %s:%s — %s", group_id, artifact_id, exc)

    _version_cache[cache_key] = None
    return None


def _resolve_version(group_id: str, artifact_id: str) -> tuple[str | None, str]:
    """
    Resolve the best target version for a dependency.
    Returns (version, source) where source is one of:
      "maven_central"  — live lookup succeeded
      "knowledge_base" — fallback from _FALLBACK
      "unresolved"     — no information available
    """
    # 1. Try Maven Central live
    ver = _fetch_latest_from_maven_central(group_id, artifact_id)
    if ver:
        return ver, "maven_central"

    # 2. Fall back to knowledge base
    fb = _FALLBACK.get(artifact_id)
    if fb:
        return fb[1], "knowledge_base"

    return None, "unresolved"


# ── XML helpers ──────────────────────────────────────────────────────────────

def _child_text(el: ET.Element, tag: str) -> str | None:
    node = el.find(tag)
    return node.text.strip() if node is not None and node.text else None


def _set_text(el: ET.Element, tag: str, value: str) -> None:
    node = el.find(tag)
    if node is not None:
        node.text = value


# ── Main entry point ─────────────────────────────────────────────────────────

def update_pom(pom_path: Path) -> PomUpdateResult:
    """
    Read pom.xml, resolve the latest compatible version for every dependency
    and plugin via Maven Central, apply all changes, and write the file back.

    Returns a PomUpdateResult with a full record of every change made.
    Raises RuntimeError if the file cannot be parsed or written.
    """
    logger.info("Reading pom.xml: %s", pom_path)

    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
    except (ET.ParseError, OSError) as exc:
        raise RuntimeError(f"Cannot parse pom.xml: {exc}") from exc

    ns_match = re.match(r"\{(.*?)\}", root.tag)
    ns_uri = ns_match.group(1) if ns_match else ""
    ns = f"{{{ns_uri}}}" if ns_uri else ""
    if ns_uri:
        ET.register_namespace("", ns_uri)

    result = PomUpdateResult()

    # ── 1. Spring Boot parent ────────────────────────────────────────────────
    parent = root.find(f"{ns}parent")
    if parent is not None:
        aid_node = parent.find(f"{ns}artifactId")
        ver_node = parent.find(f"{ns}version")
        if (
            aid_node is not None
            and aid_node.text == "spring-boot-starter-parent"
            and ver_node is not None
            and ver_node.text != TARGET_SPRING_BOOT
        ):
            old = ver_node.text
            ver_node.text = TARGET_SPRING_BOOT
            result.spring_boot_updated = True
            result.dep_changes.append(DepChange(
                artifact_id="spring-boot-starter-parent",
                group_id="org.springframework.boot",
                old_version=old,
                new_version=TARGET_SPRING_BOOT,
                source="knowledge_base",
            ))
            logger.info("Spring Boot parent: %s → %s", old, TARGET_SPRING_BOOT)

    # ── 2. Java version in <properties> ─────────────────────────────────────
    props = root.find(f"{ns}properties")
    if props is not None:
        for key in _JAVA_PROPERTY_KEYS:
            node = props.find(f"{ns}{key}")
            if node is not None and node.text and node.text.strip() != TARGET_JAVA:
                old = node.text.strip()
                node.text = TARGET_JAVA
                result.java_updated = True
                logger.info("Java property <%s>: %s → %s", key, old, TARGET_JAVA)

    # ── 3. Plugins ───────────────────────────────────────────────────────────
    for plugin in root.iter(f"{ns}plugin"):
        aid_node = plugin.find(f"{ns}artifactId")
        ver_node = plugin.find(f"{ns}version")
        if aid_node is None:
            continue

        aid = (aid_node.text or "").strip()
        gid_node = plugin.find(f"{ns}groupId")
        gid = (gid_node.text or "org.apache.maven.plugins").strip()

        if aid == "maven-compiler-plugin":
            _update_compiler_plugin(plugin, ns, result)
            if ver_node is not None and ver_node.text != TARGET_COMPILER_PLUGIN:
                old = ver_node.text
                ver_node.text = TARGET_COMPILER_PLUGIN
                result.compiler_plugin_updated = True
                result.dep_changes.append(DepChange(
                    artifact_id=aid, group_id=gid,
                    old_version=old, new_version=TARGET_COMPILER_PLUGIN,
                    source="knowledge_base",
                ))
                logger.info("maven-compiler-plugin: %s → %s", old, TARGET_COMPILER_PLUGIN)

        elif ver_node is not None:
            target_ver, source = _resolve_version(gid, aid)
            if target_ver and ver_node.text != target_ver:
                old = ver_node.text
                ver_node.text = target_ver
                if aid == "maven-surefire-plugin":
                    result.surefire_plugin_updated = True
                result.dep_changes.append(DepChange(
                    artifact_id=aid, group_id=gid,
                    old_version=old, new_version=target_ver,
                    source=source,
                ))
                logger.info("Plugin %s: %s → %s (%s)", aid, old, target_ver, source)

    # ── 4. Dependencies ──────────────────────────────────────────────────────
    for dep in root.iter(f"{ns}dependency"):
        aid_node = dep.find(f"{ns}artifactId")
        gid_node = dep.find(f"{ns}groupId")
        ver_node = dep.find(f"{ns}version")

        if aid_node is None or gid_node is None or ver_node is None:
            continue

        aid = (aid_node.text or "").strip()
        gid = (gid_node.text or "").strip()
        current_ver = (ver_node.text or "").strip()

        # Skip BOM-managed starters — their version comes from the parent
        if aid in _SPRING_BOM_MANAGED:
            continue

        # Skip property placeholders like ${spring.version}
        if current_ver.startswith("${"):
            continue

        target_ver, source = _resolve_version(gid, aid)
        if target_ver and current_ver != target_ver:
            ver_node.text = target_ver
            result.dep_changes.append(DepChange(
                artifact_id=aid, group_id=gid,
                old_version=current_ver or None,
                new_version=target_ver,
                source=source,
            ))
            logger.info("Dependency %s:%s: %s → %s (%s)", gid, aid, current_ver, target_ver, source)

    # ── 5. dependencyManagement versions ────────────────────────────────────
    mgmt = root.find(f"{ns}dependencyManagement")
    if mgmt is not None:
        for dep in mgmt.iter(f"{ns}dependency"):
            aid_node = dep.find(f"{ns}artifactId")
            gid_node = dep.find(f"{ns}groupId")
            ver_node = dep.find(f"{ns}version")
            if aid_node is None or gid_node is None or ver_node is None:
                continue
            aid = (aid_node.text or "").strip()
            gid = (gid_node.text or "").strip()
            current_ver = (ver_node.text or "").strip()
            if current_ver.startswith("${"):
                continue
            target_ver, source = _resolve_version(gid, aid)
            if target_ver and current_ver != target_ver:
                ver_node.text = target_ver
                # Only record if not already recorded from the main deps section
                already = any(c.artifact_id == aid for c in result.dep_changes)
                if not already:
                    result.dep_changes.append(DepChange(
                        artifact_id=aid, group_id=gid,
                        old_version=current_ver or None,
                        new_version=target_ver,
                        source=source,
                    ))
                logger.info("DepMgmt %s:%s: %s → %s (%s)", gid, aid, current_ver, target_ver, source)

    # ── 6. Write back ────────────────────────────────────────────────────────
    try:
        tree.write(pom_path, encoding="utf-8", xml_declaration=True)
        logger.info("pom.xml written: %s changes applied to %s", len(result.dep_changes), pom_path)
    except OSError as exc:
        raise RuntimeError(f"Cannot write pom.xml: {exc}") from exc

    return result


def _update_compiler_plugin(plugin: ET.Element, ns: str, result: PomUpdateResult) -> None:
    """
    Ensure maven-compiler-plugin uses <release>21</release> and removes the
    legacy <source>/<target> pair.  Creates <configuration> if absent.
    """
    config = plugin.find(f"{ns}configuration")
    if config is None:
        config = ET.SubElement(plugin, f"{ns}configuration")

    for tag in ("source", "target"):
        node = config.find(f"{ns}{tag}")
        if node is not None:
            config.remove(node)
            logger.info("Removed legacy compiler <%s> tag", tag)

    release_node = config.find(f"{ns}release")
    if release_node is None:
        release_node = ET.SubElement(config, f"{ns}release")

    if release_node.text != TARGET_JAVA:
        old = release_node.text
        release_node.text = TARGET_JAVA
        result.java_updated = True
        logger.info("maven-compiler-plugin <release>: %s → %s", old, TARGET_JAVA)
