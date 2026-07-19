"""
source_refactorer.py — Java source code refactoring for Java 21 / Spring Boot 3.x

Design
------
Each refactoring rule is a self-contained object with:
  - A detection regex  (used to decide whether the file needs this rule at all)
  - A list of (pattern, replacement) pairs applied via re.sub

Rules are applied in a fixed order so that earlier rules do not interfere with
later ones (e.g. javax→jakarta runs before any annotation-specific rules).

Every change is recorded as a SourceChange so the HTML report can show exactly
what was done to each file.

Only files that actually change are written back to disk.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Change record ────────────────────────────────────────────────────────────

@dataclass
class FileChange:
    """All changes applied to one .java file."""
    file_path: Path
    changes: list[tuple[str, str, int]] = field(default_factory=list)
    # Each entry: (category, description, occurrences)

    @property
    def total_occurrences(self) -> int:
        return sum(c[2] for c in self.changes)


# ── Rule definition ──────────────────────────────────────────────────────────

@dataclass
class RefactorRule:
    category: str
    description: str
    # Quick check — if this pattern is NOT found in the file, skip all subs
    trigger: str
    # List of (regex_pattern, replacement) — applied in order
    substitutions: list[tuple[str, str]]


# ── Rule catalogue ───────────────────────────────────────────────────────────

_RULES: list[RefactorRule] = [

    # ── 1. javax.servlet → jakarta.servlet ──────────────────────────────────
    RefactorRule(
        category="javax.servlet → jakarta.servlet",
        description="Servlet API namespace migrated from javax.servlet to jakarta.servlet (Jakarta EE 9+)",
        trigger=r"javax\.servlet",
        substitutions=[
            (r"\bjavax\.servlet\b", "jakarta.servlet"),
        ],
    ),

    # ── 2. javax.persistence → jakarta.persistence ──────────────────────────
    RefactorRule(
        category="javax.persistence → jakarta.persistence",
        description="JPA namespace migrated from javax.persistence to jakarta.persistence (Jakarta EE 9+)",
        trigger=r"javax\.persistence",
        substitutions=[
            (r"\bjavax\.persistence\b", "jakarta.persistence"),
        ],
    ),

    # ── 3. javax.validation → jakarta.validation ────────────────────────────
    RefactorRule(
        category="javax.validation → jakarta.validation",
        description="Bean Validation namespace migrated from javax.validation to jakarta.validation",
        trigger=r"javax\.validation",
        substitutions=[
            (r"\bjavax\.validation\b", "jakarta.validation"),
        ],
    ),

    # ── 4. javax.transaction → jakarta.transaction ──────────────────────────
    RefactorRule(
        category="javax.transaction → jakarta.transaction",
        description="Transaction API namespace migrated from javax.transaction to jakarta.transaction",
        trigger=r"javax\.transaction",
        substitutions=[
            (r"\bjavax\.transaction\b", "jakarta.transaction"),
        ],
    ),

    # ── 5. javax.annotation → jakarta.annotation ────────────────────────────
    RefactorRule(
        category="javax.annotation → jakarta.annotation",
        description="Common annotations namespace migrated from javax.annotation to jakarta.annotation",
        trigger=r"javax\.annotation",
        substitutions=[
            (r"\bjavax\.annotation\b", "jakarta.annotation"),
        ],
    ),

    # ── 6. javax.xml.bind (JAXB) → jakarta.xml.bind ─────────────────────────
    RefactorRule(
        category="javax.xml.bind → jakarta.xml.bind",
        description="JAXB namespace migrated from javax.xml.bind to jakarta.xml.bind (removed from JDK 11+)",
        trigger=r"javax\.xml\.bind",
        substitutions=[
            (r"\bjavax\.xml\.bind\b", "jakarta.xml.bind"),
        ],
    ),

    # ── 7. javax.ws.rs → jakarta.ws.rs (JAX-RS) ─────────────────────────────
    RefactorRule(
        category="javax.ws.rs → jakarta.ws.rs",
        description="JAX-RS namespace migrated from javax.ws.rs to jakarta.ws.rs",
        trigger=r"javax\.ws\.rs",
        substitutions=[
            (r"\bjavax\.ws\.rs\b", "jakarta.ws.rs"),
        ],
    ),

    # ── 8. javax.mail → jakarta.mail ────────────────────────────────────────
    RefactorRule(
        category="javax.mail → jakarta.mail",
        description="JavaMail namespace migrated from javax.mail to jakarta.mail",
        trigger=r"javax\.mail",
        substitutions=[
            (r"\bjavax\.mail\b", "jakarta.mail"),
        ],
    ),

    # ── 9. javax.ejb → jakarta.ejb ──────────────────────────────────────────
    RefactorRule(
        category="javax.ejb → jakarta.ejb",
        description="EJB namespace migrated from javax.ejb to jakarta.ejb",
        trigger=r"javax\.ejb",
        substitutions=[
            (r"\bjavax\.ejb\b", "jakarta.ejb"),
        ],
    ),

    # ── 10. javax.jms → jakarta.jms ─────────────────────────────────────────
    RefactorRule(
        category="javax.jms → jakarta.jms",
        description="JMS namespace migrated from javax.jms to jakarta.jms",
        trigger=r"javax\.jms",
        substitutions=[
            (r"\bjavax\.jms\b", "jakarta.jms"),
        ],
    ),

    # ── 11. Spring Security — WebSecurityConfigurerAdapter removal ───────────
    RefactorRule(
        category="Spring Security — WebSecurityConfigurerAdapter removed",
        description=(
            "WebSecurityConfigurerAdapter was removed in Spring Security 6. "
            "Class declaration updated to remove the extends clause. "
            "Manual review required to convert configure() methods to SecurityFilterChain @Bean."
        ),
        trigger=r"WebSecurityConfigurerAdapter",
        substitutions=[
            # Remove 'extends WebSecurityConfigurerAdapter' from class declarations
            (
                r"\bextends\s+WebSecurityConfigurerAdapter\s*",
                "",
            ),
            # Remove the import
            (
                r"import\s+org\.springframework\.security\.config\.annotation\.web\.configuration\.WebSecurityConfigurerAdapter;\n?",
                "",
            ),
        ],
    ),

    # ── 12. Spring Security — @EnableWebSecurity no longer extends adapter ───
    RefactorRule(
        category="Spring Security — add @Configuration to security classes",
        description=(
            "Security configuration classes that previously extended WebSecurityConfigurerAdapter "
            "need @Configuration to be picked up as Spring beans."
        ),
        trigger=r"@EnableWebSecurity",
        substitutions=[
            # Add @Configuration before @EnableWebSecurity if not already present
            (
                r"(?<!@Configuration\n)(@EnableWebSecurity)",
                "@Configuration\n\\1",
            ),
        ],
    ),

    # ── 13. Spring Security — HttpMethod.valueOf → HttpMethod.resolve ────────
    RefactorRule(
        category="Spring Security — HttpMethod is now an enum",
        description=(
            "HttpMethod changed from a class with string constants to an enum in Spring 6. "
            "HttpMethod.valueOf() replaced with HttpMethod.valueOf() is still valid for enums, "
            "but string comparisons like .name().equals() are updated."
        ),
        trigger=r"HttpMethod\.GET|HttpMethod\.POST|HttpMethod\.PUT|HttpMethod\.DELETE|HttpMethod\.PATCH",
        substitutions=[
            # HttpMethod.GET.name() → "GET"  style comparisons — leave as-is, enum .name() works
            # HttpMethod.resolve(str) is the new factory — update old string-based construction
            (
                r'new\s+HttpMethod\s*\(\s*"([A-Z]+)"\s*\)',
                r"HttpMethod.\1",
            ),
        ],
    ),

    # ── 14. JUnit 4 → JUnit 5 imports ───────────────────────────────────────
    RefactorRule(
        category="JUnit 4 → JUnit 5 migration",
        description=(
            "JUnit 4 annotations and imports replaced with JUnit 5 (Jupiter) equivalents. "
            "@RunWith → @ExtendWith, org.junit.Test → org.junit.jupiter.api.Test, "
            "Assert.* → Assertions.*"
        ),
        trigger=r"import\s+org\.junit\.(Test|Before|After|Assert|runner\.RunWith|Ignore|Rule)",
        substitutions=[
            # @RunWith(SpringRunner.class) → @ExtendWith(SpringExtension.class)
            (
                r"@RunWith\s*\(\s*SpringRunner\.class\s*\)",
                "@ExtendWith(SpringExtension.class)",
            ),
            # @RunWith(MockitoJUnitRunner.class) → @ExtendWith(MockitoExtension.class)
            (
                r"@RunWith\s*\(\s*MockitoJUnitRunner(?:\.Silent)?\.class\s*\)",
                "@ExtendWith(MockitoExtension.class)",
            ),
            # Generic @RunWith → @ExtendWith
            (
                r"@RunWith\s*\(",
                "@ExtendWith(",
            ),
            # Import replacements
            (r"import\s+org\.junit\.Test;", "import org.junit.jupiter.api.Test;"),
            (r"import\s+org\.junit\.Before;", "import org.junit.jupiter.api.BeforeEach;"),
            (r"import\s+org\.junit\.After;", "import org.junit.jupiter.api.AfterEach;"),
            (r"import\s+org\.junit\.BeforeClass;", "import org.junit.jupiter.api.BeforeAll;"),
            (r"import\s+org\.junit\.AfterClass;", "import org.junit.jupiter.api.AfterAll;"),
            (r"import\s+org\.junit\.Ignore;", "import org.junit.jupiter.api.Disabled;"),
            (r"import\s+org\.junit\.Assert;", "import org.junit.jupiter.api.Assertions;"),
            (r"import\s+org\.junit\.runner\.RunWith;", "import org.junit.jupiter.api.extension.ExtendWith;"),
            (r"import\s+org\.junit\.runners\.Parameterized;", "import org.junit.jupiter.params.ParameterizedTest;"),
            # Annotation replacements
            (r"@Before\b", "@BeforeEach"),
            (r"@After\b", "@AfterEach"),
            (r"@BeforeClass\b", "@BeforeAll"),
            (r"@AfterClass\b", "@AfterAll"),
            (r"@Ignore\b", "@Disabled"),
            # Assert.* → Assertions.*
            (r"\bAssert\.assertEquals\b", "Assertions.assertEquals"),
            (r"\bAssert\.assertTrue\b", "Assertions.assertTrue"),
            (r"\bAssert\.assertFalse\b", "Assertions.assertFalse"),
            (r"\bAssert\.assertNull\b", "Assertions.assertNull"),
            (r"\bAssert\.assertNotNull\b", "Assertions.assertNotNull"),
            (r"\bAssert\.assertSame\b", "Assertions.assertSame"),
            (r"\bAssert\.assertNotSame\b", "Assertions.assertNotSame"),
            (r"\bAssert\.assertArrayEquals\b", "Assertions.assertArrayEquals"),
            (r"\bAssert\.fail\b", "Assertions.fail"),
        ],
    ),

    # ── 15. Spring Boot test annotation ─────────────────────────────────────
    RefactorRule(
        category="Spring Boot test — @SpringBootTest replaces @SpringApplicationConfiguration",
        description="@SpringApplicationConfiguration and @WebAppConfiguration replaced by @SpringBootTest",
        trigger=r"@SpringApplicationConfiguration|@WebAppConfiguration",
        substitutions=[
            (
                r"import\s+org\.springframework\.boot\.test\.context\.SpringApplicationConfiguration;\n?",
                "",
            ),
            (
                r"import\s+org\.springframework\.test\.context\.web\.WebAppConfiguration;\n?",
                "",
            ),
            (r"@SpringApplicationConfiguration\s*\([^)]*\)", "@SpringBootTest"),
            (r"@WebAppConfiguration\b", ""),
        ],
    ),

    # ── 16. Deprecated @Autowired on constructors ────────────────────────────
    RefactorRule(
        category="Constructor injection — remove redundant @Autowired",
        description=(
            "Spring 4.3+ injects single-constructor beans automatically. "
            "@Autowired on the sole constructor is redundant and removed."
        ),
        trigger=r"@Autowired\s*\n\s*public\s+\w+\s*\(",
        substitutions=[
            # Only remove @Autowired immediately before a public constructor
            (
                r"@Autowired\s*\n(\s*public\s+\w+\s*\()",
                r"\1",
            ),
        ],
    ),

    # ── 17. Deprecated Spring Data repository methods ────────────────────────
    RefactorRule(
        category="Spring Data — deprecated repository method names",
        description=(
            "Spring Data 3.x removed findOne() — replaced with findById(). "
            "delete(id) replaced with deleteById(id)."
        ),
        trigger=r"\.findOne\(|repository\.delete\(",
        substitutions=[
            (r"\.findOne\(", ".findById("),
            # Only replace repository.delete(id) patterns, not delete(entity)
            (r"(\w+Repository)\.delete\(([^,)]+)\)", r"\1.deleteById(\2)"),
        ],
    ),

    # ── 18. Hibernate — deprecated Criteria API ──────────────────────────────
    RefactorRule(
        category="Hibernate — deprecated Criteria API",
        description=(
            "Hibernate 5 deprecated session.createCriteria(). "
            "Import updated to use JPA CriteriaBuilder API."
        ),
        trigger=r"import\s+org\.hibernate\.Criteria|session\.createCriteria",
        substitutions=[
            (
                r"import\s+org\.hibernate\.Criteria;\n?",
                "import jakarta.persistence.criteria.CriteriaQuery;\n",
            ),
            (
                r"import\s+org\.hibernate\.criterion\.Restrictions;\n?",
                "",
            ),
        ],
    ),

    # ── 19. Deprecated Date/Time API ─────────────────────────────────────────
    RefactorRule(
        category="Java Date/Time — deprecated java.util.Date usage",
        description=(
            "java.util.Date and java.util.Calendar are deprecated. "
            "Import for java.time.* added as a reminder; manual conversion required."
        ),
        trigger=r"import\s+java\.util\.Date;|new\s+Date\(\)",
        substitutions=[
            # Add java.time import after java.util.Date import as a hint
            (
                r"(import\s+java\.util\.Date;)",
                r"\1\nimport java.time.LocalDateTime; // TODO: migrate from java.util.Date to java.time",
            ),
        ],
    ),

    # ── 20. Removed sun.* / com.sun.* internal APIs ──────────────────────────
    RefactorRule(
        category="Removed internal JDK APIs (sun.* / com.sun.*)",
        description=(
            "Internal JDK APIs under sun.* and com.sun.* are encapsulated in Java 17+ "
            "and may be removed. Imports flagged with TODO comment for manual review."
        ),
        trigger=r"import\s+(?:sun\.|com\.sun\.)",
        substitutions=[
            (
                r"(import\s+(?:sun\.|com\.sun\.)\S+;)",
                r"// TODO: Replace internal JDK API — not available in Java 17+\n\1",
            ),
        ],
    ),

    # ── 21. finalize() deprecation ───────────────────────────────────────────
    RefactorRule(
        category="Deprecated finalize() method",
        description=(
            "Object.finalize() is deprecated for removal since Java 18. "
            "Method annotated with @Deprecated and TODO comment added."
        ),
        trigger=r"protected\s+void\s+finalize\s*\(\s*\)",
        substitutions=[
            (
                r"(protected\s+void\s+finalize\s*\(\s*\))",
                r"@Deprecated(since = \"18\", forRemoval = true) // TODO: Replace with Cleaner or try-with-resources\n    \1",
            ),
        ],
    ),

    # ── 22. Thread.stop / Thread.suspend / Thread.resume ────────────────────
    RefactorRule(
        category="Removed Thread methods (stop/suspend/resume)",
        description=(
            "Thread.stop(), Thread.suspend(), and Thread.resume() were removed in Java 20. "
            "Calls flagged with TODO comment for manual replacement."
        ),
        trigger=r"\bThread\.(stop|suspend|resume)\s*\(",
        substitutions=[
            (
                r"(\w+\.(?:stop|suspend|resume)\s*\()",
                r"/* TODO: Thread.stop/suspend/resume removed in Java 20 — use interruption */ \1",
            ),
        ],
    ),

    # ── 23. Spring @RequestMapping method shortcuts ──────────────────────────
    RefactorRule(
        category="Spring MVC — @RequestMapping to shortcut annotations",
        description=(
            "Verbose @RequestMapping(method=RequestMethod.GET) replaced with "
            "@GetMapping, @PostMapping, @PutMapping, @DeleteMapping, @PatchMapping."
        ),
        trigger=r"@RequestMapping\s*\([^)]*method\s*=\s*RequestMethod\.",
        substitutions=[
            (
                r'@RequestMapping\s*\(\s*value\s*=\s*("(?:[^"\\]|\\.)*")\s*,\s*method\s*=\s*RequestMethod\.GET\s*\)',
                r"@GetMapping(\1)",
            ),
            (
                r'@RequestMapping\s*\(\s*value\s*=\s*("(?:[^"\\]|\\.)*")\s*,\s*method\s*=\s*RequestMethod\.POST\s*\)',
                r"@PostMapping(\1)",
            ),
            (
                r'@RequestMapping\s*\(\s*value\s*=\s*("(?:[^"\\]|\\.)*")\s*,\s*method\s*=\s*RequestMethod\.PUT\s*\)',
                r"@PutMapping(\1)",
            ),
            (
                r'@RequestMapping\s*\(\s*value\s*=\s*("(?:[^"\\]|\\.)*")\s*,\s*method\s*=\s*RequestMethod\.DELETE\s*\)',
                r"@DeleteMapping(\1)",
            ),
            (
                r'@RequestMapping\s*\(\s*value\s*=\s*("(?:[^"\\]|\\.)*")\s*,\s*method\s*=\s*RequestMethod\.PATCH\s*\)',
                r"@PatchMapping(\1)",
            ),
            # Without value= prefix
            (
                r'@RequestMapping\s*\(\s*("(?:[^"\\]|\\.)*")\s*,\s*method\s*=\s*RequestMethod\.GET\s*\)',
                r"@GetMapping(\1)",
            ),
            (
                r'@RequestMapping\s*\(\s*("(?:[^"\\]|\\.)*")\s*,\s*method\s*=\s*RequestMethod\.POST\s*\)',
                r"@PostMapping(\1)",
            ),
        ],
    ),

    # ── 24. Spring — ResponseEntity.ok() shorthand ───────────────────────────
    RefactorRule(
        category="Spring MVC — ResponseEntity builder shorthand",
        description=(
            "new ResponseEntity<>(body, HttpStatus.OK) replaced with ResponseEntity.ok(body) "
            "for cleaner code."
        ),
        trigger=r"new\s+ResponseEntity\s*<[^>]*>\s*\([^,]+,\s*HttpStatus\.OK\s*\)",
        substitutions=[
            (
                r"new\s+ResponseEntity\s*<[^>]*>\s*\(([^,]+),\s*HttpStatus\.OK\s*\)",
                r"ResponseEntity.ok(\1)",
            ),
        ],
    ),

    # ── 25. Mockito — MockitoAnnotations.initMocks → openMocks ───────────────
    RefactorRule(
        category="Mockito — initMocks() deprecated",
        description="MockitoAnnotations.initMocks() deprecated; replaced with openMocks().",
        trigger=r"MockitoAnnotations\.initMocks",
        substitutions=[
            (r"MockitoAnnotations\.initMocks\(", "MockitoAnnotations.openMocks("),
        ],
    ),

    # ── 26. Spring Boot — SpringApplication.run shorthand ────────────────────
    RefactorRule(
        category="Spring Boot — SpringApplication.run with varargs",
        description=(
            "SpringApplication.run(App.class, args) is the preferred form. "
            "new SpringApplication(App.class).run(args) updated to static form."
        ),
        trigger=r"new\s+SpringApplication\s*\(",
        substitutions=[
            (
                r"new\s+SpringApplication\s*\(\s*(\w+\.class)\s*\)\.run\s*\(\s*args\s*\)",
                r"SpringApplication.run(\1, args)",
            ),
        ],
    ),
]


# ── Engine ───────────────────────────────────────────────────────────────────

def refactor_sources(project_dir: Path) -> list[FileChange]:
    """
    Walk all .java files under project_dir, apply every applicable rule,
    and write back only files that actually changed.

    Returns a list of FileChange objects — one per modified file.
    """
    java_files = list(project_dir.rglob("*.java"))
    logger.info("Source refactoring: scanning %d .java files", len(java_files))

    modified: list[FileChange] = []

    for java_file in java_files:
        try:
            original = java_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning("Cannot read %s: %s", java_file, exc)
            continue

        current = original
        file_change = FileChange(file_path=java_file)

        for rule in _RULES:
            # Quick trigger check — skip the rule entirely if the pattern is absent
            if not re.search(rule.trigger, current):
                continue

            before = current
            total_hits = 0

            for pattern, replacement in rule.substitutions:
                new_text, count = re.subn(pattern, replacement, current)
                total_hits += count
                current = new_text

            if current != before and total_hits > 0:
                file_change.changes.append((rule.category, rule.description, total_hits))
                logger.debug("  %s: rule '%s' made %d change(s)", java_file.name, rule.category, total_hits)

        if current != original:
            try:
                java_file.write_text(current, encoding="utf-8")
                modified.append(file_change)
                logger.info(
                    "Refactored: %s (%d rule(s), %d change(s))",
                    java_file.name,
                    len(file_change.changes),
                    file_change.total_occurrences,
                )
            except OSError as exc:
                logger.error("Cannot write %s: %s", java_file, exc)

    logger.info(
        "Source refactoring complete: %d/%d files modified",
        len(modified), len(java_files),
    )
    return modified
