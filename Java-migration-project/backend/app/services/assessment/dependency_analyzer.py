import logging
from app.models.report import DependencyInfo, DependencyAnalysis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Curated knowledge base
# Each entry: artifact_id → (recommended_version, upgrade_priority, notes)
# This is the single place to update when new stable versions are released.
# ---------------------------------------------------------------------------
_KNOWN_DEPS: dict[str, tuple[str, str, str]] = {
    # Spring ecosystem
    "spring-boot-starter-parent":   ("3.3.4", "High",   "Upgrade to Spring Boot 3.x for Java 21 support and Jakarta EE 10"),
    "spring-boot-starter":          ("3.3.4", "High",   "Spring Boot 3.x requires Java 17+ and migrates to jakarta.* namespace"),
    "spring-boot-starter-web":      ("3.3.4", "High",   "Embedded Tomcat 10+ uses jakarta.servlet — update all servlet imports"),
    "spring-boot-starter-data-jpa": ("3.3.4", "High",   "Hibernate 6.x included; javax.persistence.* → jakarta.persistence.*"),
    "spring-boot-starter-security": ("3.3.4", "High",   "Security config DSL changed; WebSecurityConfigurerAdapter removed"),
    "spring-boot-starter-test":     ("3.3.4", "Medium", "JUnit 5 is default; remove JUnit 4 vintage engine if not needed"),
    "spring-boot-starter-actuator": ("3.3.4", "Medium", "Endpoint paths and security config changed in 3.x"),
    "spring-boot-starter-cache":    ("3.3.4", "Medium", "Compatible with Spring Boot 3.x"),
    "spring-boot-starter-aop":      ("3.3.4", "Medium", "Compatible with Spring Boot 3.x"),
    "spring-boot-starter-validation":("3.3.4","High",   "javax.validation.* → jakarta.validation.*"),
    "spring-context":               ("6.1.12","High",   "Spring Framework 6.x requires Java 17+ and Jakarta EE 9+"),
    "spring-webmvc":                ("6.1.12","High",   "javax.servlet.* → jakarta.servlet.*"),
    "spring-data-jpa":              ("3.3.4", "High",   "Hibernate 6 and Jakarta Persistence 3.0"),
    "spring-security-core":         ("6.3.3", "High",   "Major API changes; SecurityFilterChain replaces WebSecurityConfigurerAdapter"),
    "spring-security-web":          ("6.3.3", "High",   "HttpSecurity lambda DSL is now mandatory"),
    "spring-security-config":       ("6.3.3", "High",   "WebSecurityConfigurerAdapter fully removed"),

    # Jakarta / Java EE
    "javax.servlet-api":            ("jakarta.servlet-api:6.0.0", "High", "Renamed to jakarta.servlet-api in Jakarta EE 9+"),
    "javax.validation-api":         ("jakarta.validation-api:3.0.2","High","Renamed to jakarta.validation-api"),
    "javax.persistence-api":        ("jakarta.persistence-api:3.1.0","High","Renamed to jakarta.persistence-api"),
    "jaxb-api":                     ("4.0.2", "High",   "JAXB removed from JDK 11+; must be added as explicit dependency"),
    "javax.xml.bind-api":           ("jakarta.xml.bind-api:4.0.2","High","Renamed to jakarta.xml.bind-api"),

    # Persistence / ORM
    "hibernate-core":               ("6.5.2.Final","High","Hibernate 6 has breaking API changes; SessionFactory and Criteria API updated"),
    "hibernate-validator":          ("8.0.1.Final","High","javax.validation → jakarta.validation"),
    "mybatis-spring-boot-starter":  ("3.0.3", "Medium","Compatible with Spring Boot 3.x"),
    "flyway-core":                  ("10.15.0","Medium","Flyway 10 requires Java 17+"),
    "liquibase-core":               ("4.29.1","Medium","Compatible with Java 21"),

    # Database drivers
    "postgresql":                   ("42.7.3", "Medium","Latest driver; compatible with Java 21"),
    "mysql-connector-java":         ("8.4.0",  "High",  "Artifact renamed to mysql-connector-j in 8.1+"),
    "mysql-connector-j":            ("8.4.0",  "Medium","Latest connector; compatible with Java 21"),
    "ojdbc8":                       ("23.4.0.24.05","Medium","Oracle 23c driver; compatible with Java 21"),
    "mssql-jdbc":                   ("12.6.3.jre11","Medium","Latest SQL Server driver"),
    "h2":                           ("2.2.224","Medium","H2 2.x has breaking changes from 1.x"),
    "mongodb-driver-sync":          ("5.1.3",  "Medium","Compatible with Java 21"),
    "spring-boot-starter-data-mongodb":("3.3.4","Medium","Compatible with Spring Boot 3.x"),

    # Lombok / code generation
    "lombok":                       ("1.18.34","Medium","Ensure annotation processor is configured for Java 21"),
    "mapstruct":                    ("1.6.0",  "Medium","Compatible with Java 21"),
    "mapstruct-processor":          ("1.6.0",  "Medium","Compatible with Java 21"),

    # Testing
    "junit":                        ("4.13.2", "Medium","Consider migrating to JUnit 5 (junit-jupiter)"),
    "junit-jupiter":                ("5.10.3", "Low",   "Latest JUnit 5; compatible with Java 21"),
    "mockito-core":                 ("5.12.0", "Medium","Mockito 5 requires Java 11+; compatible with Java 21"),
    "mockito-junit-jupiter":        ("5.12.0", "Medium","Compatible with Java 21"),
    "assertj-core":                 ("3.26.3", "Low",   "Compatible with Java 21"),

    # Logging
    "logback-classic":              ("1.5.7",  "Low",   "Compatible with Java 21"),
    "log4j-core":                   ("2.23.1", "High",  "Upgrade immediately — older versions have critical CVEs"),
    "log4j-api":                    ("2.23.1", "High",  "Upgrade immediately — older versions have critical CVEs"),
    "slf4j-api":                    ("2.0.13", "Low",   "SLF4J 2.x uses fluent API; backward compatible"),

    # Build plugins
    "maven-compiler-plugin":        ("3.13.0", "Medium","Set <release>21</release> instead of source/target"),
    "maven-surefire-plugin":        ("3.3.1",  "Medium","3.x required for JUnit 5 support"),
    "maven-failsafe-plugin":        ("3.3.1",  "Medium","Align with surefire version"),
    "maven-jar-plugin":             ("3.4.2",  "Low",   "Compatible with Java 21"),
    "maven-war-plugin":             ("3.4.0",  "Low",   "Compatible with Java 21"),
    "spring-boot-maven-plugin":     ("3.3.4",  "High",  "Must match Spring Boot version"),

    # Jackson
    "jackson-databind":             ("2.17.2", "Medium","Compatible with Java 21; check custom serializers"),
    "jackson-core":                 ("2.17.2", "Low",   "Compatible with Java 21"),
    "jackson-annotations":          ("2.17.2", "Low",   "Compatible with Java 21"),

    # Misc
    "guava":                        ("33.2.1-jre","Low","Compatible with Java 21"),
    "commons-lang3":                ("3.15.0", "Low",   "Compatible with Java 21"),
    "commons-io":                   ("2.16.1", "Low",   "Compatible with Java 21"),
    "httpclient":                   ("4.5.14", "Medium","Consider migrating to httpclient5"),
    "httpclient5":                  ("5.3.1",  "Low",   "Compatible with Java 21"),
}


def analyze_dependencies(raw_deps: list[dict]) -> DependencyAnalysis:
    """
    Enrich raw dependency dicts from the parser with upgrade recommendations.
    raw_deps items: {group_id, artifact_id, version}
    """
    enriched: list[DependencyInfo] = []

    for dep in raw_deps:
        aid = dep.get("artifact_id", "")
        current_ver = dep.get("version")
        known = _KNOWN_DEPS.get(aid)

        if known:
            rec_ver, priority, notes = known
            upgrade_required = current_ver is None or current_ver != rec_ver
        else:
            rec_ver = None
            priority = "Low"
            notes = "No specific migration guidance available."
            upgrade_required = False

        enriched.append(DependencyInfo(
            group_id=dep.get("group_id", ""),
            artifact_id=aid,
            current_version=current_ver,
            recommended_version=rec_ver,
            upgrade_required=upgrade_required,
            upgrade_priority=priority,
            compatibility_notes=notes,
        ))

    requiring_upgrade = sum(1 for d in enriched if d.upgrade_required)
    logger.info("Dependency analysis: %d total, %d require upgrade", len(enriched), requiring_upgrade)

    return DependencyAnalysis(
        total_dependencies=len(enriched),
        dependencies_requiring_upgrade=requiring_upgrade,
        dependencies=enriched,
    )
