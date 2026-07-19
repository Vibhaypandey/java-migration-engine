import logging
from pathlib import Path

from app.config import settings
from app.models.report import (
    AssessmentReport, ProjectInfo, JavaMigrationAnalysis,
    SpringBootMigration, BuildConfiguration, PluginInfo,
    DatabaseAnalysis, DatabaseInfo, DockerReadiness, MigrationSummary,
)
from app.services.assessment.maven_parser import parse_pom
from app.services.assessment.gradle_parser import parse_gradle
from app.services.assessment.dependency_analyzer import analyze_dependencies
from app.services.assessment.code_analyzer import analyze_code
from app.services.assessment.html_renderer import render_html

logger = logging.getLogger(__name__)

TARGET_JAVA = 21
TARGET_SPRING_BOOT = "3.3.4"

# Known database driver artifact IDs → (display name, recommended version, notes)
_DB_DRIVERS: dict[str, tuple[str, str, str]] = {
    "postgresql":                    ("PostgreSQL",  "42.7.3",  "Compatible with Java 21; supports JDBC 4.2"),
    "mysql-connector-java":          ("MySQL",       "8.4.0",   "Artifact renamed to mysql-connector-j in 8.1+"),
    "mysql-connector-j":             ("MySQL",       "8.4.0",   "Latest connector; compatible with Java 21"),
    "ojdbc8":                        ("Oracle",      "23.4.0.24.05", "Oracle 23c driver; compatible with Java 21"),
    "ojdbc11":                       ("Oracle",      "23.4.0.24.05", "Oracle 23c driver for Java 11+"),
    "mssql-jdbc":                    ("SQL Server",  "12.6.3.jre11", "Latest SQL Server JDBC driver"),
    "h2":                            ("H2",          "2.2.224", "H2 2.x has breaking schema changes from 1.x"),
    "mongodb-driver-sync":           ("MongoDB",     "5.1.3",   "Compatible with Java 21"),
    "spring-boot-starter-data-mongodb": ("MongoDB",  "3.3.4",   "Compatible with Spring Boot 3.x and Java 21"),
}

# Plugin recommendations: artifact_id → recommended version
_PLUGIN_RECOMMENDATIONS: dict[str, str] = {
    "maven-compiler-plugin": "3.13.0",
    "maven-surefire-plugin":  "3.3.1",
    "maven-failsafe-plugin":  "3.3.1",
    "maven-jar-plugin":       "3.4.2",
    "maven-war-plugin":       "3.4.0",
    "spring-boot-maven-plugin": TARGET_SPRING_BOOT,
}


def build_report(workspace_id: str, extract_dir: Path) -> AssessmentReport:
    """
    Entry point called by the router.
    Parses the project, runs all analyzers, saves the HTML report to disk,
    and returns a structured AssessmentReport with a report_url.
    """
    logger.info("Starting assessment for workspace: %s", workspace_id)

    # ── 1. Parse build file ──────────────────────────────────────────────────
    parsed = _parse_build_file(extract_dir)
    build_tool = parsed.get("build_tool", "maven")

    # ── 2. Project Info ──────────────────────────────────────────────────────
    project_info = ProjectInfo(
        project_name=parsed.get("project_name", extract_dir.name),
        build_tool=build_tool,
        packaging=parsed.get("packaging"),
        java_version=parsed.get("java_version"),
        spring_boot_version=parsed.get("spring_boot_version"),
        spring_framework_version=parsed.get("spring_framework_version"),
    )

    # ── 3. Dependency Analysis ───────────────────────────────────────────────
    dep_analysis = analyze_dependencies(parsed.get("dependencies", []))

    # ── 4. Java Migration ────────────────────────────────────────────────────
    java_migration = _build_java_migration(parsed.get("java_version"))

    # ── 5. Spring Boot Migration ─────────────────────────────────────────────
    spring_migration = _build_spring_migration(parsed.get("spring_boot_version"))

    # ── 6. Code Refactoring ──────────────────────────────────────────────────
    code_refactoring = analyze_code(extract_dir)

    # ── 7. Build Configuration ───────────────────────────────────────────────
    build_config = _build_configuration(parsed, build_tool)

    # ── 8. Database Analysis ─────────────────────────────────────────────────
    db_analysis = _build_database_analysis(parsed.get("dependencies", []))

    # ── 9. Docker Readiness ──────────────────────────────────────────────────
    docker = _build_docker_readiness(extract_dir)

    # ── 10. Migration Summary ────────────────────────────────────────────────
    summary = _build_summary(project_info, dep_analysis, code_refactoring, java_migration)

    # ── Assemble report (without HTML first) ─────────────────────────────────
    report_url = f"/assessment/{workspace_id}/report"

    report = AssessmentReport(
        project_id=workspace_id,
        status="SUCCESS",
        report_url=report_url,
        project_info=project_info,
        dependency_analysis=dep_analysis,
        java_migration=java_migration,
        spring_boot_migration=spring_migration,
        code_refactoring=code_refactoring,
        build_configuration=build_config,
        database_analysis=db_analysis,
        docker_readiness=docker,
        migration_summary=summary,
    )

    # ── Save HTML report to workspace/reports/{project_id}.html ──────────────
    html_content = render_html(report)
    report_path = settings.reports_dir / f"{workspace_id}.html"
    report_path.write_text(html_content, encoding="utf-8")
    logger.info("HTML report saved: %s", report_path)

    logger.info("Assessment complete for workspace: %s", workspace_id)
    return report


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _parse_build_file(extract_dir: Path) -> dict:
    """Find and parse the first pom.xml or build.gradle in the workspace."""
    pom = next(extract_dir.rglob("pom.xml"), None)
    if pom:
        data = parse_pom(pom)
        data["build_tool"] = "maven"
        return data

    gradle = next(extract_dir.rglob("build.gradle.kts"), None) or \
             next(extract_dir.rglob("build.gradle"), None)
    if gradle:
        data = parse_gradle(gradle)
        data["build_tool"] = "gradle"
        return data

    logger.warning("No build file found in %s", extract_dir)
    return {"build_tool": "maven"}


def _build_java_migration(current: int | None) -> JavaMigrationAnalysis:
    notes = []
    risk = "Low"

    if current is None:
        notes.append("Java version not declared in build file — manual verification required.")
        risk = "Medium"
    elif current < 17:
        risk = "High"
        notes += [
            f"Migrating from Java {current} to {TARGET_JAVA} is a multi-version jump.",
            "Strong encapsulation of JDK internals enforced from Java 17+.",
            "Sealed classes, records, and pattern matching are available from Java 17+.",
            "javax.* packages replaced by jakarta.* in Jakarta EE 9+.",
        ]
    elif current < 21:
        risk = "Medium"
        notes += [
            f"Migrating from Java {current} to {TARGET_JAVA}.",
            "Virtual threads (Project Loom) available in Java 21 — consider adoption.",
            "Sequenced Collections API added in Java 21.",
        ]
    else:
        notes.append("Project is already on Java 21. No Java migration required.")

    return JavaMigrationAnalysis(
        current_version=current,
        target_version=TARGET_JAVA,
        migration_supported=True,
        risk_level=risk,
        migration_notes=notes,
    )


def _build_spring_migration(current_sb: str | None) -> SpringBootMigration:
    breaking = [
        "javax.* → jakarta.* namespace migration required across all source files.",
        "WebSecurityConfigurerAdapter removed; use SecurityFilterChain @Bean instead.",
        "Spring MVC and WebFlux: HttpMethod is now an enum — update comparisons.",
        "spring.factories auto-configuration replaced by AutoConfiguration.imports.",
        "Actuator endpoints restructured; review custom endpoint security.",
        "Hibernate 6 included: SessionFactory and Criteria API have breaking changes.",
        "spring-boot-starter-validation uses jakarta.validation — update all @Valid imports.",
    ]

    upgrade_required = current_sb is None or not current_sb.startswith("3.")

    return SpringBootMigration(
        current_version=current_sb,
        recommended_version=TARGET_SPRING_BOOT,
        upgrade_required=upgrade_required,
        breaking_changes=breaking,
    )


def _build_configuration(parsed: dict, build_tool: str) -> BuildConfiguration:
    plugins_raw = parsed.get("plugins", [])
    compiler_plugin = None
    surefire_plugin = None
    others: list[PluginInfo] = []

    for p in plugins_raw:
        aid = p.get("artifact_id", "")
        ver = p.get("version")
        rec = _PLUGIN_RECOMMENDATIONS.get(aid)
        needs_update = rec is not None and ver != rec

        info = PluginInfo(
            artifact_id=aid,
            current_version=ver,
            recommended_version=rec,
            update_required=needs_update,
        )

        if aid == "maven-compiler-plugin":
            compiler_plugin = info
        elif aid == "maven-surefire-plugin":
            surefire_plugin = info
        elif needs_update:
            others.append(info)

    return BuildConfiguration(
        build_tool=build_tool,
        source_compatibility=parsed.get("source_compatibility"),
        target_compatibility=parsed.get("target_compatibility"),
        encoding=parsed.get("encoding"),
        compiler_plugin=compiler_plugin,
        surefire_plugin=surefire_plugin,
        other_plugins_requiring_update=others,
    )


def _build_database_analysis(deps: list[dict]) -> DatabaseAnalysis:
    found: list[DatabaseInfo] = []
    dep_aids = {d.get("artifact_id", ""): d.get("version") for d in deps}

    for aid, current_ver in dep_aids.items():
        if aid in _DB_DRIVERS:
            db_name, rec_ver, notes = _DB_DRIVERS[aid]
            found.append(DatabaseInfo(
                database=db_name,
                driver_artifact=aid,
                current_version=current_ver,
                recommended_version=rec_ver,
                compatibility_notes=notes,
            ))

    return DatabaseAnalysis(
        databases_detected=found,
        no_database_detected=len(found) == 0,
    )


def _build_docker_readiness(extract_dir: Path) -> DockerReadiness:
    has_dockerfile = any(extract_dir.rglob("Dockerfile"))
    has_compose = any(extract_dir.rglob("docker-compose.yml")) or \
                  any(extract_dir.rglob("docker-compose.yaml"))

    recs = []
    if not has_dockerfile:
        recs.append("Create a Dockerfile using eclipse-temurin:21-jre-alpine as the base image.")
        recs.append("Use multi-stage build: builder stage compiles, runtime stage runs the JAR.")
    if not has_compose:
        recs.append("Add docker-compose.yml to orchestrate the app with its database locally.")
    if has_dockerfile and has_compose:
        recs.append("Docker setup detected. Verify base image uses Java 21.")

    return DockerReadiness(
        dockerfile_exists=has_dockerfile,
        docker_compose_exists=has_compose,
        recommendations=recs,
    )


def _build_summary(project_info, dep_analysis, code_refactoring, java_migration) -> MigrationSummary:
    complexity = _derive_complexity(dep_analysis, code_refactoring, java_migration)
    confidence = "High" if complexity == "Low" else ("Medium" if complexity == "Medium" else "Low")

    risks = []
    if java_migration.risk_level == "High":
        risks.append(f"Large Java version gap: {java_migration.current_version} → {TARGET_JAVA}")
    if dep_analysis.dependencies_requiring_upgrade > 10:
        risks.append(f"{dep_analysis.dependencies_requiring_upgrade} dependencies need upgrading")
    if code_refactoring.overall_risk == "High":
        risks.append("javax.* → jakarta.* migration affects multiple source files")
    if not risks:
        risks.append("No critical risks identified — migration is straightforward")

    return MigrationSummary(
        current_java=project_info.java_version,
        target_java=TARGET_JAVA,
        current_spring_boot=project_info.spring_boot_version,
        target_spring_boot=TARGET_SPRING_BOOT,
        total_dependencies=dep_analysis.total_dependencies,
        dependencies_to_upgrade=dep_analysis.dependencies_requiring_upgrade,
        estimated_files_to_change=code_refactoring.files_likely_to_change,
        migration_complexity=complexity,
        migration_confidence=confidence,
        top_risks=risks,
    )


def _derive_complexity(dep_analysis, code_refactoring, java_migration) -> str:
    score = 0
    if java_migration.risk_level == "High":
        score += 2
    elif java_migration.risk_level == "Medium":
        score += 1
    if dep_analysis.dependencies_requiring_upgrade > 10:
        score += 2
    elif dep_analysis.dependencies_requiring_upgrade > 4:
        score += 1
    if code_refactoring.overall_risk == "High":
        score += 2
    elif code_refactoring.overall_risk == "Medium":
        score += 1
    if score >= 4:
        return "High"
    if score >= 2:
        return "Medium"
    return "Low"
