import logging
import re
from pathlib import Path

from app.models.report import CodeRefactoringAnalysis, RefactoringItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Refactoring signal definitions
# Each entry: (category, description, regex_pattern, risk_level)
# The regex is searched across each .java file's full text.
# ---------------------------------------------------------------------------
_SIGNALS: list[tuple[str, str, str, str]] = [
    (
        "javax → jakarta namespace",
        "Imports using javax.* must be updated to jakarta.* for Jakarta EE 9+ / Spring Boot 3.x",
        r"\bimport\s+javax\.(servlet|persistence|validation|transaction|annotation|xml|ws|mail|ejb|jms)\b",
        "High",
    ),
    (
        "Deprecated Spring Security config",
        "WebSecurityConfigurerAdapter is removed in Spring Security 6; migrate to SecurityFilterChain beans",
        r"WebSecurityConfigurerAdapter",
        "High",
    ),
    (
        "Spring @Configuration bean methods",
        "Some @Bean factory method patterns changed in Spring 6; verify proxy behaviour",
        r"@Configuration\b",
        "Low",
    ),
    (
        "JUnit 4 annotations",
        "JUnit 4 (@Test from org.junit, @RunWith) should be migrated to JUnit 5 equivalents",
        r"import\s+org\.junit\.Test|@RunWith\s*\(",
        "Medium",
    ),
    (
        "Removed Java APIs (sun.* / com.sun.*)",
        "Internal JDK APIs removed or encapsulated in Java 17+; use standard replacements",
        r"\bimport\s+(sun\.|com\.sun\.)",
        "High",
    ),
    (
        "javax.xml.bind (JAXB)",
        "JAXB was removed from the JDK in Java 11; add jakarta.xml.bind-api dependency",
        r"import\s+javax\.xml\.bind\b",
        "High",
    ),
    (
        "Finalize method override",
        "finalize() is deprecated for removal in Java 18+; replace with Cleaner or try-with-resources",
        r"protected\s+void\s+finalize\s*\(\s*\)",
        "Medium",
    ),
    (
        "Raw type usage",
        "Raw generic types produce unchecked warnings and may cause runtime issues",
        r"\bList\s+\w+\s*=|Map\s+\w+\s*=|Set\s+\w+\s*=",
        "Low",
    ),
    (
        "Spring MVC XML config",
        "XML-based Spring MVC configuration should be migrated to Java config",
        r"@ImportResource|ClassPathXmlApplicationContext|FileSystemXmlApplicationContext",
        "Medium",
    ),
    (
        "Validation API (javax.validation)",
        "@Valid / @NotNull from javax.validation must move to jakarta.validation",
        r"import\s+javax\.validation\b",
        "High",
    ),
    (
        "Persistence API (javax.persistence)",
        "@Entity / @Table / @Column from javax.persistence must move to jakarta.persistence",
        r"import\s+javax\.persistence\b",
        "High",
    ),
    (
        "Thread.stop / Thread.suspend",
        "Deprecated thread control methods removed in Java 20+",
        r"\bThread\.(stop|suspend|resume)\s*\(",
        "Medium",
    ),
]


def analyze_code(extract_dir: Path) -> CodeRefactoringAnalysis:
    """
    Walk all .java files under extract_dir, apply each signal pattern,
    and return a CodeRefactoringAnalysis.  Read-only — no files are modified.
    """
    java_files = list(extract_dir.rglob("*.java"))
    total_files = len(java_files)
    logger.info("Code analysis: scanning %d .java files", total_files)

    # Per-signal hit counts: signal_index → set of file paths
    hits: list[set[Path]] = [set() for _ in _SIGNALS]
    import_count = 0

    for java_file in java_files:
        try:
            source = java_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        import_count += len(re.findall(r"^import\s+", source, re.MULTILINE))

        for idx, (_, _, pattern, _) in enumerate(_SIGNALS):
            if re.search(pattern, source):
                hits[idx].add(java_file)

    # Build RefactoringItem list — only include signals with at least one hit
    items: list[RefactoringItem] = []
    all_affected: set[Path] = set()

    for idx, (category, description, _, risk) in enumerate(_SIGNALS):
        affected = hits[idx]
        if affected:
            items.append(RefactoringItem(
                category=category,
                description=description,
                files_affected=len(affected),
                risk_level=risk,
            ))
            all_affected |= affected

    files_to_change = len(all_affected)
    effort = _estimate_effort(files_to_change, total_files)
    overall_risk = _overall_risk(items)

    logger.info(
        "Code analysis complete: %d/%d files need changes, effort=%s, risk=%s",
        files_to_change, total_files, effort, overall_risk,
    )

    return CodeRefactoringAnalysis(
        total_java_files=total_files,
        files_likely_to_change=files_to_change,
        estimated_imports_affected=import_count,
        estimated_effort=effort,
        overall_risk=overall_risk,
        refactoring_items=items,
    )


def _estimate_effort(files_to_change: int, total: int) -> str:
    if total == 0:
        return "Low"
    ratio = files_to_change / total
    if ratio > 0.5 or files_to_change > 50:
        return "High"
    if ratio > 0.2 or files_to_change > 15:
        return "Medium"
    return "Low"


def _overall_risk(items: list[RefactoringItem]) -> str:
    if any(i.risk_level == "High" for i in items):
        return "High"
    if any(i.risk_level == "Medium" for i in items):
        return "Medium"
    return "Low"
