import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)


def _ns(root: ET.Element) -> str:
    """Extract the XML namespace prefix from the root element tag."""
    m = re.match(r"\{(.*?)\}", root.tag)
    return f"{{{m.group(1)}}}" if m else ""


def parse_pom(pom_path: Path) -> dict:
    """
    Parse pom.xml and return a flat dict with all fields the report needs.
    Returns an empty dict if the file cannot be parsed.

    Keys returned:
      project_name, group_id, artifact_id, version, packaging,
      java_version, source_compatibility, target_compatibility, encoding,
      spring_boot_version, spring_framework_version,
      dependencies: list[dict(group_id, artifact_id, version)],
      plugins: list[dict(group_id, artifact_id, version)]
    """
    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        logger.error("Failed to parse pom.xml: %s", exc)
        return {}

    p = _ns(root)

    def text(tag: str) -> str | None:
        node = root.find(f"{p}{tag}")
        return node.text.strip() if node is not None and node.text else None

    def prop(key: str) -> str | None:
        props = root.find(f"{p}properties")
        if props is None:
            return None
        node = props.find(f"{p}{key}")
        return node.text.strip() if node is not None and node.text else None

    # Resolve a value that may be a ${property} reference
    def resolve(raw: str | None) -> str | None:
        if raw is None:
            return None
        m = re.match(r"\$\{(.+?)\}", raw)
        if m:
            return prop(m.group(1)) or raw
        return raw

    # --- Basic project coordinates ---
    artifact_id = text("artifactId") or pom_path.parent.name
    raw_java = (
        prop("maven.compiler.source")
        or prop("maven.compiler.target")
        or prop("java.version")
    )
    java_version = _parse_java_version(resolve(raw_java))

    # --- Spring versions ---
    spring_boot_version = resolve(prop("spring-boot.version") or _spring_boot_parent_version(root, p))
    spring_fw_version = resolve(prop("spring-framework.version") or prop("spring.version"))

    # --- Build / compiler settings ---
    source_compat = resolve(prop("maven.compiler.source"))
    target_compat = resolve(prop("maven.compiler.target"))
    encoding = resolve(prop("project.build.sourceEncoding") or prop("project.reporting.outputEncoding"))

    # --- Dependencies ---
    dependencies = []
    dep_mgmt_versions: dict[str, str] = _collect_dep_mgmt_versions(root, p)

    for dep in root.iter(f"{p}dependency"):
        gid = _child_text(dep, f"{p}groupId")
        aid = _child_text(dep, f"{p}artifactId")
        ver = resolve(_child_text(dep, f"{p}version"))
        if ver is None:
            ver = dep_mgmt_versions.get(f"{gid}:{aid}")
        if gid and aid:
            dependencies.append({"group_id": gid, "artifact_id": aid, "version": ver})

    # --- Plugins ---
    plugins = []
    for plugin in root.iter(f"{p}plugin"):
        gid = _child_text(plugin, f"{p}groupId") or "org.apache.maven.plugins"
        aid = _child_text(plugin, f"{p}artifactId")
        ver = resolve(_child_text(plugin, f"{p}version"))

        # Also check source/target inside compiler plugin config
        if aid == "maven-compiler-plugin":
            config = plugin.find(f"{p}configuration")
            if config is not None:
                for key in ("source", "target", "release"):
                    node = config.find(f"{p}{key}")
                    if node is not None and node.text and java_version is None:
                        java_version = _parse_java_version(node.text.strip())

        if aid:
            plugins.append({"group_id": gid, "artifact_id": aid, "version": ver})

    logger.info(
        "pom.xml parsed: artifact=%s, java=%s, spring_boot=%s, deps=%d, plugins=%d",
        artifact_id, java_version, spring_boot_version, len(dependencies), len(plugins),
    )

    return {
        "project_name": artifact_id,
        "group_id": text("groupId"),
        "artifact_id": artifact_id,
        "version": text("version"),
        "packaging": text("packaging") or "jar",
        "java_version": java_version,
        "source_compatibility": source_compat,
        "target_compatibility": target_compat,
        "encoding": encoding,
        "spring_boot_version": spring_boot_version,
        "spring_framework_version": spring_fw_version,
        "dependencies": dependencies,
        "plugins": plugins,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _child_text(element: ET.Element, tag: str) -> str | None:
    node = element.find(tag)
    return node.text.strip() if node is not None and node.text else None


def _parse_java_version(raw: str | None) -> int | None:
    if not raw:
        return None
    legacy = {f"1.{v}": v for v in range(1, 10)}
    raw = raw.strip()
    if raw in legacy:
        return legacy[raw]
    m = re.match(r"^(\d+)", raw)
    return int(m.group(1)) if m else None


def _spring_boot_parent_version(root: ET.Element, p: str) -> str | None:
    """Check if the project inherits from spring-boot-starter-parent."""
    parent = root.find(f"{p}parent")
    if parent is None:
        return None
    aid = _child_text(parent, f"{p}artifactId")
    if aid == "spring-boot-starter-parent":
        return _child_text(parent, f"{p}version")
    return None


def _collect_dep_mgmt_versions(root: ET.Element, p: str) -> dict[str, str]:
    """Build a {groupId:artifactId → version} map from <dependencyManagement>."""
    result: dict[str, str] = {}
    mgmt = root.find(f"{p}dependencyManagement")
    if mgmt is None:
        return result
    for dep in mgmt.iter(f"{p}dependency"):
        gid = _child_text(dep, f"{p}groupId")
        aid = _child_text(dep, f"{p}artifactId")
        ver = _child_text(dep, f"{p}version")
        if gid and aid and ver:
            result[f"{gid}:{aid}"] = ver
    return result
