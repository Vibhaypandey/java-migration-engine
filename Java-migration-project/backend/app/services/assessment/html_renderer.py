from __future__ import annotations
from app.models.report import AssessmentReport

_RISK_COLOR = {"High": "#dc3545", "Medium": "#fd7e14", "Low": "#198754"}
_RISK_BG    = {"High": "#fff5f5", "Medium": "#fff8f0", "Low": "#f0fff4"}


def render_html(report: AssessmentReport) -> str:
    pi  = report.project_info
    jm  = report.java_migration
    sb  = report.spring_boot_migration
    cr  = report.code_refactoring
    bc  = report.build_configuration
    da  = report.database_analysis
    dr  = report.docker_readiness
    ms  = report.migration_summary
    dep = report.dependency_analysis

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Migration Report — {pi.project_name}</title>
<style>
/* ── Reset & base ── */
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --primary:#1a56db;--primary-dark:#1e429f;--surface:#fff;
  --bg:#f3f4f6;--border:#e5e7eb;--text:#111827;--muted:#6b7280;
  --high:#dc3545;--medium:#fd7e14;--low:#198754;
  --high-bg:#fff5f5;--medium-bg:#fff8f0;--low-bg:#f0fff4;
  --radius:10px;--shadow:0 1px 3px rgba(0,0,0,.1),0 1px 2px rgba(0,0,0,.06);
}}
body{{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.5}}

/* ── Sticky header ── */
.site-header{{
  position:sticky;top:0;z-index:100;
  background:var(--primary-dark);color:#fff;
  padding:.75rem 2rem;display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 2px 8px rgba(0,0,0,.25);
}}
.site-header h1{{font-size:1.1rem;font-weight:700;letter-spacing:.01em}}
.site-header .meta{{font-size:.8rem;opacity:.8}}
.header-badge{{
  background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);
  border-radius:20px;padding:.25rem .75rem;font-size:.78rem;font-weight:600;
}}

/* ── Layout ── */
.page{{max-width:1200px;margin:0 auto;padding:1.5rem 1rem 3rem}}

/* ── Summary cards ── */
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin-bottom:2rem}}
.card{{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.1rem 1.25rem;box-shadow:var(--shadow);
}}
.card-label{{font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:.35rem}}
.card-value{{font-size:1.6rem;font-weight:700;line-height:1}}
.card-sub{{font-size:.78rem;color:var(--muted);margin-top:.3rem}}
.card.risk-high{{border-left:4px solid var(--high)}}
.card.risk-medium{{border-left:4px solid var(--medium)}}
.card.risk-low{{border-left:4px solid var(--low)}}

/* ── Section ── */
.section{{margin-bottom:1.25rem}}
.section-header{{
  display:flex;align-items:center;justify-content:space-between;
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:.85rem 1.25rem;cursor:pointer;user-select:none;
  box-shadow:var(--shadow);transition:background .15s;
}}
.section-header:hover{{background:#f9fafb}}
.section-header h2{{font-size:.95rem;font-weight:700;display:flex;align-items:center;gap:.6rem}}
.section-num{{
  background:var(--primary);color:#fff;border-radius:50%;
  width:1.5rem;height:1.5rem;display:inline-flex;align-items:center;justify-content:center;
  font-size:.72rem;font-weight:700;flex-shrink:0;
}}
.chevron{{transition:transform .25s;font-size:.85rem;color:var(--muted)}}
.section-body{{
  background:var(--surface);border:1px solid var(--border);border-top:none;
  border-radius:0 0 var(--radius) var(--radius);
  padding:1.25rem;overflow:hidden;
  max-height:5000px;transition:max-height .35s ease,padding .35s ease;
}}
.section-body.collapsed{{max-height:0;padding-top:0;padding-bottom:0}}
.section-header.collapsed .chevron{{transform:rotate(-90deg)}}

/* ── KV rows ── */
.kv-grid{{display:grid;grid-template-columns:1fr 1fr;gap:.1rem 2rem}}
.kv{{display:flex;justify-content:space-between;align-items:center;padding:.4rem 0;border-bottom:1px solid #f3f4f6;font-size:.875rem}}
.kv:last-child{{border-bottom:none}}
.kv-label{{color:var(--muted);flex-shrink:0;margin-right:1rem}}
.kv-value{{font-weight:500;text-align:right}}

/* ── Badges ── */
.badge{{
  display:inline-flex;align-items:center;gap:.3rem;
  padding:.2rem .6rem;border-radius:20px;font-size:.72rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.04em;
}}
.badge-high{{background:var(--high-bg);color:var(--high);border:1px solid #fecaca}}
.badge-medium{{background:var(--medium-bg);color:var(--medium);border:1px solid #fed7aa}}
.badge-low{{background:var(--low-bg);color:var(--low);border:1px solid #bbf7d0}}
.badge-info{{background:#eff6ff;color:var(--primary);border:1px solid #bfdbfe}}

/* ── Tables ── */
.table-wrap{{overflow-x:auto;border-radius:var(--radius);border:1px solid var(--border)}}
table{{width:100%;border-collapse:collapse;font-size:.83rem}}
thead tr{{background:#f9fafb}}
th{{padding:.6rem .9rem;text-align:left;font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);border-bottom:1px solid var(--border)}}
td{{padding:.55rem .9rem;border-bottom:1px solid #f3f4f6;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#fafafa}}

/* ── Timeline ── */
.timeline{{position:relative;padding-left:2rem;margin-top:.5rem}}
.timeline::before{{content:'';position:absolute;left:.55rem;top:.5rem;bottom:.5rem;width:2px;background:var(--border)}}
.tl-item{{position:relative;margin-bottom:1.25rem}}
.tl-item:last-child{{margin-bottom:0}}
.tl-dot{{
  position:absolute;left:-1.55rem;top:.2rem;
  width:.9rem;height:.9rem;border-radius:50%;border:2px solid var(--surface);
  background:var(--primary);
}}
.tl-dot.done{{background:var(--low)}}
.tl-dot.warn{{background:var(--medium)}}
.tl-dot.danger{{background:var(--high)}}
.tl-title{{font-weight:600;font-size:.875rem}}
.tl-desc{{font-size:.8rem;color:var(--muted);margin-top:.15rem}}

/* ── Misc ── */
ul.check-list{{list-style:none;padding:0}}
ul.check-list li{{padding:.3rem 0;font-size:.875rem;display:flex;align-items:flex-start;gap:.5rem}}
ul.check-list li::before{{content:'›';color:var(--primary);font-weight:700;flex-shrink:0}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}}
.info-box{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:1rem}}
.warn-box{{background:var(--medium-bg);border:1px solid #fed7aa;border-radius:8px;padding:1rem}}
.danger-box{{background:var(--high-bg);border:1px solid #fecaca;border-radius:8px;padding:1rem}}
.success-box{{background:var(--low-bg);border:1px solid #bbf7d0;border-radius:8px;padding:1rem}}
.box-title{{font-weight:700;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem}}
.docker-icon{{font-size:1.5rem}}
@media(max-width:640px){{
  .two-col{{grid-template-columns:1fr}}
  .kv-grid{{grid-template-columns:1fr}}
  .cards{{grid-template-columns:1fr 1fr}}
  .site-header .meta{{display:none}}
}}
</style>
</head>
<body>

<!-- ── Sticky Header ── -->
<header class="site-header">
  <h1>☕ Java Migration Assistant</h1>
  <span class="meta">Migration Assessment Report</span>
  <div style="display:flex;align-items:center;gap:.75rem">
    <span class="header-badge">{pi.project_name}</span>
    <a href="#" onclick="startMigration(event, '{report.project_id}')" style="
      background:#16a34a;color:#fff;border:none;border-radius:8px;
      padding:.4rem 1rem;font-size:.8rem;font-weight:700;cursor:pointer;
      text-decoration:none;display:inline-flex;align-items:center;gap:.4rem;
    ">🚀 Start Migration</a>
  </div>
</header>

<div class="page">

<!-- ── Summary Cards ── -->
<div class="cards">
  {_summary_card("Java Version", str(ms.current_java) if ms.current_java else "?", f"Target: Java {ms.target_java}", jm.risk_level)}
  {_summary_card("Spring Boot", ms.current_spring_boot or "N/A", f"Target: {ms.target_spring_boot}", "High" if sb.upgrade_required else "Low")}
  {_summary_card("Dependencies", str(dep.total_dependencies), f"{dep.dependencies_requiring_upgrade} need upgrade", "High" if dep.dependencies_requiring_upgrade > 5 else "Medium" if dep.dependencies_requiring_upgrade > 0 else "Low")}
  {_summary_card("Files to Change", str(cr.files_likely_to_change), f"of {cr.total_java_files} Java files", cr.overall_risk)}
  {_summary_card("Complexity", ms.migration_complexity, f"Confidence: {ms.migration_confidence}", ms.migration_complexity)}
  {_summary_card("Build Tool", pi.build_tool.capitalize(), pi.packaging or "jar", "Low")}
</div>

<!-- ── Section 1: Project Info ── -->
{_section(1, "Project Information", f"""
<div class="two-col">
  <div>
    <div class="kv-grid">
      {_kv("Project Name", pi.project_name)}
      {_kv("Build Tool", pi.build_tool.capitalize())}
      {_kv("Packaging", pi.packaging or "N/A")}
      {_kv("Java Version", str(pi.java_version) if pi.java_version else _badge("Unknown","info"))}
    </div>
  </div>
  <div>
    <div class="kv-grid">
      {_kv("Spring Boot", pi.spring_boot_version or "Not detected")}
      {_kv("Spring Framework", pi.spring_framework_version or "Not detected")}
    </div>
  </div>
</div>
""")}

<!-- ── Section 2: Dependency Analysis ── -->
{_section(2, f"Dependency Analysis <span style='font-weight:400;color:var(--muted);font-size:.85rem;margin-left:.5rem'>{dep.total_dependencies} total &nbsp;·&nbsp; {dep.dependencies_requiring_upgrade} require upgrade</span>", f"""
<div class="table-wrap">
<table>
  <thead><tr>
    <th>Group ID</th><th>Artifact ID</th><th>Current</th>
    <th>Recommended</th><th>Priority</th><th>Notes</th>
  </tr></thead>
  <tbody>{"".join(_dep_row(d) for d in dep.dependencies)}</tbody>
</table>
</div>
""")}

<!-- ── Section 3: Java Migration ── -->
{_section(3, "Java Migration Analysis", f"""
<div class="two-col">
  <div>
    <div class="kv-grid">
      {_kv("Current Version", str(jm.current_version) if jm.current_version else "Unknown")}
      {_kv("Target Version", f"Java {jm.target_version}")}
      {_kv("Migration Supported", "✅ Yes" if jm.migration_supported else "❌ No")}
      {_kv("Risk Level", _risk_badge(jm.risk_level))}
    </div>
    <div style="margin-top:1.25rem">
      <div class="timeline">
        {_timeline_item(f"Java {jm.current_version or '?'}", "Current version", "warn" if (jm.current_version or 0) < 17 else "done")}
        {_timeline_item("Java 17", "LTS — Strong encapsulation, records, sealed classes", "done" if (jm.current_version or 0) >= 17 else "")}
        {_timeline_item("Java 21", "LTS Target — Virtual threads, pattern matching, sequenced collections", "done" if (jm.current_version or 0) >= 21 else "")}
      </div>
    </div>
  </div>
  <div>
    <div class="{'danger' if jm.risk_level == 'High' else 'warn' if jm.risk_level == 'Medium' else 'success'}-box">
      <div class="box-title">Migration Notes</div>
      <ul class="check-list">{"".join(f"<li>{n}</li>" for n in jm.migration_notes)}</ul>
    </div>
  </div>
</div>
""")}

<!-- ── Section 4: Spring Boot Migration ── -->
{_section(4, "Spring Boot Migration", f"""
<div class="two-col">
  <div>
    <div class="kv-grid">
      {_kv("Current Version", sb.current_version or "Not detected")}
      {_kv("Recommended", sb.recommended_version)}
      {_kv("Upgrade Required", _badge("Yes","high") if sb.upgrade_required else _badge("No","low"))}
    </div>
    <div style="margin-top:1.25rem">
      <div class="timeline">
        {_timeline_item(sb.current_version or "Unknown", "Current Spring Boot", "warn" if sb.upgrade_required else "done")}
        {_timeline_item("Spring Boot 3.x", "Jakarta EE 10, Spring Security 6, Hibernate 6", "done" if not sb.upgrade_required else "")}
        {_timeline_item(sb.recommended_version, "Recommended stable target", "done" if not sb.upgrade_required else "")}
      </div>
    </div>
  </div>
  <div>
    <div class="warn-box">
      <div class="box-title">⚠ Breaking Changes</div>
      <ul class="check-list">{"".join(f"<li>{c}</li>" for c in sb.breaking_changes)}</ul>
    </div>
  </div>
</div>
""")}

<!-- ── Section 5: Code Refactoring ── -->
{_section(5, "Code Refactoring Analysis", f"""
<div class="cards" style="margin-bottom:1.25rem">
  {_mini_card("Java Files", str(cr.total_java_files))}
  {_mini_card("Files to Change", str(cr.files_likely_to_change))}
  {_mini_card("Imports Affected", str(cr.estimated_imports_affected))}
  {_mini_card("Effort", cr.estimated_effort)}
  {_mini_card("Overall Risk", cr.overall_risk)}
</div>
{"<p style='color:var(--muted);font-size:.875rem'>No refactoring signals detected in source files.</p>" if not cr.refactoring_items else f'''
<div class="table-wrap">
<table>
  <thead><tr><th>Category</th><th>Files Affected</th><th>Risk</th><th>Description</th></tr></thead>
  <tbody>{"".join(_refactor_row(r) for r in cr.refactoring_items)}</tbody>
</table>
</div>'''}
""")}

<!-- ── Section 6: Build Configuration ── -->
{_section(6, "Build Configuration", f"""
<div class="two-col">
  <div>
    <div class="kv-grid">
      {_kv("Build Tool", bc.build_tool.capitalize())}
      {_kv("Source Compatibility", bc.source_compatibility or "N/A")}
      {_kv("Target Compatibility", bc.target_compatibility or "N/A")}
      {_kv("Encoding", bc.encoding or "N/A")}
    </div>
  </div>
  <div>
    <div class="kv-grid">
      {_plugin_kv("Compiler Plugin", bc.compiler_plugin)}
      {_plugin_kv("Surefire Plugin", bc.surefire_plugin)}
      {"".join(_plugin_kv(p.artifact_id, p) for p in bc.other_plugins_requiring_update)}
    </div>
  </div>
</div>
""")}

<!-- ── Section 7: Database Analysis ── -->
{_section(7, "Database Analysis", f"""
{"<p style='color:var(--muted);font-size:.875rem'>No database dependencies detected in the build file.</p>" if da.no_database_detected else f'''
<div class="table-wrap">
<table>
  <thead><tr><th>Database</th><th>Driver Artifact</th><th>Current</th><th>Recommended</th><th>Notes</th></tr></thead>
  <tbody>{"".join(_db_row(d) for d in da.databases_detected)}</tbody>
</table>
</div>'''}
""")}

<!-- ── Section 8: Docker Readiness ── -->
{_section(8, "Docker Readiness", f"""
<div class="two-col">
  <div>
    <div class="kv-grid">
      {_kv("Dockerfile", "✅ Found" if dr.dockerfile_exists else "❌ Not found")}
      {_kv("Docker Compose", "✅ Found" if dr.docker_compose_exists else "❌ Not found")}
    </div>
  </div>
  <div>
    <div class="info-box">
      <div class="box-title">Recommendations</div>
      <ul class="check-list">{"".join(f"<li>{r}</li>" for r in dr.recommendations)}</ul>
    </div>
  </div>
</div>
""")}

<!-- ── Section 9: Migration Summary ── -->
{_section(9, "Migration Summary", f"""
<div class="two-col" style="margin-bottom:1.25rem">
  <div>
    <div class="kv-grid">
      {_kv("Java", f"{ms.current_java or '?'} &rarr; {ms.target_java}")}
      {_kv("Spring Boot", f"{ms.current_spring_boot or 'N/A'} &rarr; {ms.target_spring_boot}")}
      {_kv("Dependencies to Upgrade", str(ms.dependencies_to_upgrade))}
      {_kv("Files Requiring Changes", str(ms.estimated_files_to_change))}
      {_kv("Migration Complexity", _risk_badge(ms.migration_complexity))}
      {_kv("Migration Confidence", _risk_badge(ms.migration_confidence))}
    </div>
  </div>
  <div>
    <div class="{'danger' if ms.migration_complexity == 'High' else 'warn' if ms.migration_complexity == 'Medium' else 'success'}-box">
      <div class="box-title">Top Risks</div>
      <ul class="check-list">{"".join(f"<li>{r}</li>" for r in ms.top_risks)}</ul>
    </div>
  </div>
</div>
""", open_by_default=True)}

</div><!-- /page -->

<script>
// Collapsible sections
document.querySelectorAll('.section-header').forEach(function(header) {{
  header.addEventListener('click', function() {{
    var body = this.nextElementSibling;
    var isCollapsed = body.classList.toggle('collapsed');
    this.classList.toggle('collapsed', isCollapsed);
  }});
}});

// Start Migration: POST /migration/PROJECT_ID/start then redirect to summary
function startMigration(event, projectId) {{
  event.preventDefault();
  var btn = event.currentTarget;
  btn.textContent = '⏳ Running...';
  btn.style.pointerEvents = 'none';
  btn.style.opacity = '0.7';

  fetch('/migration/' + projectId + '/start', {{ method: 'POST' }})
    .then(function(res) {{ return res.json(); }})
    .then(function(data) {{
      window.location.href = '/migration/' + projectId + '/summary';
    }})
    .catch(function(err) {{
      btn.textContent = '❌ Failed';
      btn.style.background = '#dc3545';
      btn.style.pointerEvents = 'auto';
      btn.style.opacity = '1';
      alert('Migration failed: ' + err);
    }});
}}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Component helpers
# ---------------------------------------------------------------------------

def _badge(text: str, kind: str = "info") -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'


def _risk_badge(level: str) -> str:
    kind = level.lower()
    dot = "🔴" if level == "High" else "🟡" if level == "Medium" else "🟢"
    return f'<span class="badge badge-{kind}">{dot} {level}</span>'


def _kv(label: str, value: str) -> str:
    return (
        f'<div class="kv">'
        f'<span class="kv-label">{label}</span>'
        f'<span class="kv-value">{value}</span>'
        f'</div>'
    )


def _summary_card(label: str, value: str, sub: str, risk: str) -> str:
    cls = f"card risk-{risk.lower()}"
    return (
        f'<div class="{cls}">'
        f'<div class="card-label">{label}</div>'
        f'<div class="card-value">{value}</div>'
        f'<div class="card-sub">{sub}</div>'
        f'</div>'
    )


def _mini_card(label: str, value: str) -> str:
    return (
        f'<div class="card" style="padding:.75rem 1rem">'
        f'<div class="card-label">{label}</div>'
        f'<div class="card-value" style="font-size:1.2rem">{value}</div>'
        f'</div>'
    )


def _section(num: int, title: str, body_html: str, open_by_default: bool = False) -> str:
    collapsed_cls = "" if open_by_default else ""  # all open by default; JS toggles
    return (
        f'<div class="section">'
        f'<div class="section-header">'
        f'<h2><span class="section-num">{num}</span>{title}</h2>'
        f'<span class="chevron">▾</span>'
        f'</div>'
        f'<div class="section-body {collapsed_cls}">{body_html}</div>'
        f'</div>'
    )


def _timeline_item(title: str, desc: str, dot_class: str = "") -> str:
    return (
        f'<div class="tl-item">'
        f'<div class="tl-dot {dot_class}"></div>'
        f'<div class="tl-title">{title}</div>'
        f'<div class="tl-desc">{desc}</div>'
        f'</div>'
    )


def _dep_row(d) -> str:
    priority_cell = _risk_badge(d.upgrade_priority) if d.upgrade_required else '<span style="color:var(--muted)">—</span>'
    current = d.current_version or '<span style="color:var(--muted)">—</span>'
    recommended = d.recommended_version or '<span style="color:var(--muted)">—</span>'
    return (
        f"<tr>"
        f"<td style='color:var(--muted);font-size:.78rem'>{d.group_id}</td>"
        f"<td><strong>{d.artifact_id}</strong></td>"
        f"<td>{current}</td>"
        f"<td>{recommended}</td>"
        f"<td>{priority_cell}</td>"
        f"<td style='font-size:.8rem'>{d.compatibility_notes}</td>"
        f"</tr>"
    )


def _refactor_row(r) -> str:
    return (
        f"<tr>"
        f"<td><strong>{r.category}</strong></td>"
        f"<td style='text-align:center'>{r.files_affected}</td>"
        f"<td>{_risk_badge(r.risk_level)}</td>"
        f"<td style='font-size:.8rem'>{r.description}</td>"
        f"</tr>"
    )


def _plugin_kv(label: str, plugin) -> str:
    if plugin is None:
        return ""
    val = plugin.current_version or "N/A"
    if plugin.update_required and plugin.recommended_version:
        val = f'{val} <span style="color:var(--medium)">→</span> <strong>{plugin.recommended_version}</strong>'
    return _kv(label, val)


def _db_row(d) -> str:
    return (
        f"<tr>"
        f"<td><strong>{d.database}</strong></td>"
        f"<td style='font-size:.8rem;color:var(--muted)'>{d.driver_artifact}</td>"
        f"<td>{d.current_version or '—'}</td>"
        f"<td>{d.recommended_version or '—'}</td>"
        f"<td style='font-size:.8rem'>{d.compatibility_notes}</td>"
        f"</tr>"
    )
