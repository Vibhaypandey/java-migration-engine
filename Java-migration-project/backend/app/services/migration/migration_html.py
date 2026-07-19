"""
migration_html.py — Migration Change Report renderer

Sections
--------
1. Status banner
2. Migration Steps (pass/skip/fail per step)
3. Summary cards (files modified, source changes, deps updated, source)
4. Dependency Changes table (artifact, old → new, resolution source)
5. Source Code Changes — grouped by file, showing every rule applied
6. Source Changes by Category — aggregated view
7. Details (paths, project ID)
8. Action buttons
"""

from __future__ import annotations
from collections import defaultdict
from app.models.migration import MigrationResult, SourceChange, DependencyChange


def render_migration_summary(result: MigrationResult) -> str:
    overall_color = "#198754" if result.status == "COMPLETED" else "#dc3545"
    overall_icon  = "✅" if result.status == "COMPLETED" else "❌"

    step_rows_html   = "".join(_step_row(s) for s in result.steps)
    dep_section_html = _dep_section(result.dependency_changes)
    src_section_html = _source_section(result.source_changes)
    cat_section_html = _category_section(result.source_changes)
    cards_html       = _summary_cards(result)

    mc_count  = sum(1 for d in result.dependency_changes if d.source == "maven_central")
    kb_count  = sum(1 for d in result.dependency_changes if d.source == "knowledge_base")
    src_label = f"{mc_count} from Maven Central, {kb_count} from knowledge base" if result.dependency_changes else "None"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Migration Change Report</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --primary:#1a56db;--primary-dark:#1e429f;
  --bg:#f3f4f6;--surface:#fff;--border:#e5e7eb;
  --text:#111827;--muted:#6b7280;
  --high:#dc3545;--medium:#fd7e14;--low:#198754;
  --radius:10px;--shadow:0 1px 3px rgba(0,0,0,.1);
}}
body{{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.5}}
.header{{
  position:sticky;top:0;z-index:100;
  background:var(--primary-dark);color:#fff;
  padding:.75rem 2rem;display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 2px 8px rgba(0,0,0,.25);
}}
.header h1{{font-size:1.1rem;font-weight:700}}
.page{{max-width:1100px;margin:2rem auto;padding:0 1rem 3rem}}

/* Banner */
.banner{{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.5rem 2rem;margin-bottom:1.5rem;box-shadow:var(--shadow);
  display:flex;align-items:center;gap:1.25rem;
  border-left:5px solid {overall_color};
}}
.banner-icon{{font-size:2.5rem;line-height:1}}
.banner-title{{font-size:1.3rem;font-weight:700}}
.banner-sub{{font-size:.875rem;color:var(--muted);margin-top:.2rem}}

/* Summary cards */
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:1.5rem}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1rem 1.25rem;box-shadow:var(--shadow)}}
.card-label{{font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:.3rem}}
.card-value{{font-size:1.5rem;font-weight:700;line-height:1}}
.card-sub{{font-size:.75rem;color:var(--muted);margin-top:.25rem}}
.card.green{{border-left:4px solid var(--low)}}
.card.blue{{border-left:4px solid var(--primary)}}
.card.orange{{border-left:4px solid var(--medium)}}

/* Section */
.section{{margin-bottom:1.25rem}}
.section-header{{
  display:flex;align-items:center;justify-content:space-between;
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:.85rem 1.25rem;cursor:pointer;user-select:none;box-shadow:var(--shadow);
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
  max-height:9000px;transition:max-height .35s ease,padding .35s ease;
}}
.section-body.collapsed{{max-height:0;padding-top:0;padding-bottom:0}}
.section-header.collapsed .chevron{{transform:rotate(-90deg)}}

/* Steps */
.step-row{{display:flex;align-items:flex-start;gap:1rem;padding:.75rem 0;border-bottom:1px solid #f3f4f6}}
.step-row:last-child{{border-bottom:none}}
.step-icon{{font-size:1.2rem;flex-shrink:0;margin-top:.05rem}}
.step-name{{font-weight:600;font-size:.875rem}}
.step-detail{{font-size:.8rem;color:var(--muted);margin-top:.15rem}}
.badge{{display:inline-flex;align-items:center;padding:.15rem .55rem;border-radius:20px;font-size:.7rem;font-weight:700;text-transform:uppercase;margin-left:auto;flex-shrink:0}}
.badge-success{{background:#f0fff4;color:#198754;border:1px solid #bbf7d0}}
.badge-skipped{{background:#f9fafb;color:#6b7280;border:1px solid #e5e7eb}}
.badge-failed{{background:#fff5f5;color:#dc3545;border:1px solid #fecaca}}
.badge-mc{{background:#eff6ff;color:var(--primary);border:1px solid #bfdbfe;font-size:.65rem}}
.badge-kb{{background:#fefce8;color:#854d0e;border:1px solid #fef08a;font-size:.65rem}}

/* Tables */
.table-wrap{{overflow-x:auto;border-radius:var(--radius);border:1px solid var(--border)}}
table{{width:100%;border-collapse:collapse;font-size:.83rem}}
thead tr{{background:#f9fafb}}
th{{padding:.6rem .9rem;text-align:left;font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);border-bottom:1px solid var(--border)}}
td{{padding:.55rem .9rem;border-bottom:1px solid #f3f4f6;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#fafafa}}

/* File change blocks */
.file-block{{margin-bottom:1rem;border:1px solid var(--border);border-radius:8px;overflow:hidden}}
.file-header{{
  background:#f9fafb;padding:.6rem 1rem;
  font-family:monospace;font-size:.8rem;font-weight:600;
  display:flex;align-items:center;justify-content:space-between;
  border-bottom:1px solid var(--border);
}}
.file-changes{{padding:.5rem 0}}
.change-row{{display:flex;align-items:flex-start;gap:.75rem;padding:.4rem 1rem}}
.change-cat{{font-weight:600;font-size:.8rem;min-width:220px;flex-shrink:0;color:var(--primary)}}
.change-desc{{font-size:.78rem;color:var(--muted);flex:1}}
.change-count{{font-size:.75rem;font-weight:700;color:var(--low);flex-shrink:0}}

/* KV */
.kv-grid{{display:grid;grid-template-columns:1fr 1fr;gap:.1rem 2rem}}
.kv{{display:flex;justify-content:space-between;align-items:center;padding:.4rem 0;border-bottom:1px solid #f3f4f6;font-size:.875rem}}
.kv:last-child{{border-bottom:none}}
.kv-label{{color:var(--muted)}}
.kv-value{{font-weight:500;font-size:.82rem;word-break:break-all;text-align:right;max-width:65%}}

/* Actions */
.actions{{display:flex;gap:.75rem;margin-top:1.5rem;flex-wrap:wrap}}
.btn{{display:inline-flex;align-items:center;gap:.4rem;padding:.6rem 1.25rem;border-radius:8px;font-size:.875rem;font-weight:600;text-decoration:none;cursor:pointer;border:none}}
.btn-primary{{background:var(--primary);color:#fff}}
.btn-primary:hover{{background:var(--primary-dark)}}
.btn-outline{{background:var(--surface);color:var(--primary);border:1px solid var(--primary)}}
.btn-outline:hover{{background:#eff6ff}}
.btn-green{{background:#16a34a;color:#fff}}

.empty-msg{{color:var(--muted);font-size:.875rem;padding:.5rem 0}}
.arrow{{color:var(--medium);font-weight:700;margin:0 .3rem}}

@media(max-width:640px){{
  .kv-grid{{grid-template-columns:1fr}}
  .cards{{grid-template-columns:1fr 1fr}}
  .banner{{flex-direction:column;gap:.75rem}}
  .change-cat{{min-width:140px}}
}}
</style>
</head>
<body>

<header class="header">
  <h1>☕ Java Migration Assistant</h1>
  <span style="font-size:.8rem;opacity:.8">Migration Change Report</span>
</header>

<div class="page">

  <!-- Banner -->
  <div class="banner">
    <div class="banner-icon">{overall_icon}</div>
    <div>
      <div class="banner-title">Migration {result.status.capitalize()}</div>
      <div class="banner-sub">
        Project: {result.project_id}
        &nbsp;·&nbsp; Dependency resolution: {src_label}
      </div>
    </div>
  </div>

  <!-- Summary cards -->
  {cards_html}

  <!-- Section 1: Steps -->
  {_section(1, "Migration Steps", f'<div style="padding:.25rem 0">{step_rows_html}</div>', open_default=True)}

  <!-- Section 2: Dependency Changes -->
  {_section(2, f"Dependency Changes <span style='font-weight:400;color:var(--muted);font-size:.85rem;margin-left:.5rem'>{len(result.dependency_changes)} updated</span>", dep_section_html)}

  <!-- Section 3: Source Code Changes by File -->
  {_section(3, f"Source Code Changes — by File <span style='font-weight:400;color:var(--muted);font-size:.85rem;margin-left:.5rem'>{result.total_files_modified} file(s) · {result.total_source_changes} change(s)</span>", src_section_html)}

  <!-- Section 4: Source Changes by Category -->
  {_section(4, "Source Code Changes — by Category", cat_section_html)}

  <!-- Section 5: Details -->
  {_section(5, "Details", f"""
<div class="kv-grid">
  <div>
    {_kv("Project ID", result.project_id)}
    {_kv("Overall Status", result.status)}
    {_kv("Build Status", result.build_status)}
    {_kv("Files Modified", str(result.total_files_modified))}
  </div>
  <div>
    {_kv("Backup Location", result.backup_path)}
    {_kv("Updated pom.xml", result.updated_pom_path)}
    {_kv("Total Source Changes", str(result.total_source_changes))}
    {_kv("Dependencies Updated", str(len(result.dependency_changes)))}
  </div>
</div>
""")}

  <!-- Actions -->
  <div class="actions">
    <a class="btn btn-primary" href="/assessment/{result.project_id}/report">📋 Assessment Report</a>
    <a class="btn btn-outline" href="/assessment/{result.project_id}">{"{}"} JSON Report</a>
    <a href="#" onclick="startBuild(event,'{result.project_id}')" class="btn btn-green">⚡ Run Build Verification</a>
  </div>

</div>

<script>
document.querySelectorAll('.section-header').forEach(function(h){{
  h.addEventListener('click',function(){{
    var b=this.nextElementSibling;
    var c=b.classList.toggle('collapsed');
    this.classList.toggle('collapsed',c);
  }});
}});

function startBuild(event,projectId){{
  event.preventDefault();
  var btn=event.currentTarget;
  btn.textContent='\u23f3 Building...';
  btn.style.pointerEvents='none';btn.style.opacity='0.7';
  fetch('/build/'+projectId+'/start',{{method:'POST'}})
    .then(function(r){{return r.json();}})
    .then(function(){{window.location.href='/build/'+projectId+'/report';}})
    .catch(function(e){{
      btn.textContent='\u274c Failed';
      btn.style.background='#dc3545';
      btn.style.pointerEvents='auto';btn.style.opacity='1';
      alert('Build failed to start: '+e);
    }});
}}
</script>
</body>
</html>"""


# ── Section builders ─────────────────────────────────────────────────────────

def _summary_cards(result: MigrationResult) -> str:
    mc = sum(1 for d in result.dependency_changes if d.source == "maven_central")
    kb = sum(1 for d in result.dependency_changes if d.source == "knowledge_base")
    return f"""<div class="cards">
  {_card("Files Modified", str(result.total_files_modified), "Java source files", "green")}
  {_card("Source Changes", str(result.total_source_changes), "Total replacements", "blue")}
  {_card("Deps Updated", str(len(result.dependency_changes)), "pom.xml changes", "orange")}
  {_card("Maven Central", str(mc), "Live resolved", "blue")}
  {_card("Knowledge Base", str(kb), "Fallback resolved", "orange")}
  {_card("Status", result.status, result.build_status, "green" if result.status == "COMPLETED" else "orange")}
</div>"""


def _dep_section(changes: list[DependencyChange]) -> str:
    if not changes:
        return '<p class="empty-msg">No dependency version changes were applied.</p>'

    rows = "".join(_dep_row(c) for c in changes)
    return f"""<div class="table-wrap">
<table>
  <thead><tr>
    <th>Group ID</th><th>Artifact ID</th>
    <th>Old Version</th><th>New Version</th><th>Resolution</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
</div>"""


def _dep_row(c: DependencyChange) -> str:
    old = c.old_version or '<span style="color:var(--muted)">—</span>'
    src_badge = (
        '<span class="badge badge-mc">Maven Central</span>'
        if c.source == "maven_central"
        else '<span class="badge badge-kb">Knowledge Base</span>'
    )
    return (
        f"<tr>"
        f"<td style='color:var(--muted);font-size:.78rem'>{c.group_id}</td>"
        f"<td><strong>{c.artifact_id}</strong></td>"
        f"<td>{old}</td>"
        f"<td><strong style='color:var(--low)'>{c.new_version}</strong></td>"
        f"<td>{src_badge}</td>"
        f"</tr>"
    )


def _source_section(changes: list[SourceChange]) -> str:
    if not changes:
        return '<p class="empty-msg">No Java source files required changes.</p>'

    # Group by file
    by_file: dict[str, list[SourceChange]] = defaultdict(list)
    for sc in changes:
        by_file[sc.file_path].append(sc)

    blocks = []
    for file_path, file_changes in sorted(by_file.items()):
        total = sum(c.occurrences for c in file_changes)
        change_rows = "".join(
            f'<div class="change-row">'
            f'<span class="change-cat">{c.category}</span>'
            f'<span class="change-desc">{c.description}</span>'
            f'<span class="change-count">{c.occurrences}×</span>'
            f'</div>'
            for c in file_changes
        )
        blocks.append(
            f'<div class="file-block">'
            f'<div class="file-header">'
            f'<span>📄 {file_path}</span>'
            f'<span style="color:var(--muted);font-size:.75rem">{total} change(s)</span>'
            f'</div>'
            f'<div class="file-changes">{change_rows}</div>'
            f'</div>'
        )

    return "".join(blocks)


def _category_section(changes: list[SourceChange]) -> str:
    if not changes:
        return '<p class="empty-msg">No source code changes were applied.</p>'

    # Aggregate by category
    cat_files: dict[str, set[str]] = defaultdict(set)
    cat_occ: dict[str, int] = defaultdict(int)
    cat_desc: dict[str, str] = {}

    for sc in changes:
        cat_files[sc.category].add(sc.file_path)
        cat_occ[sc.category] += sc.occurrences
        cat_desc[sc.category] = sc.description

    rows = "".join(
        f"<tr>"
        f"<td><strong>{cat}</strong></td>"
        f"<td style='text-align:center'>{len(cat_files[cat])}</td>"
        f"<td style='text-align:center'>{cat_occ[cat]}</td>"
        f"<td style='font-size:.8rem;color:var(--muted)'>{cat_desc[cat]}</td>"
        f"</tr>"
        for cat in sorted(cat_files)
    )

    return f"""<div class="table-wrap">
<table>
  <thead><tr>
    <th>Category</th><th>Files Affected</th><th>Occurrences</th><th>Description</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
</div>"""


# ── Component helpers ────────────────────────────────────────────────────────

def _card(label: str, value: str, sub: str, color: str) -> str:
    return (
        f'<div class="card {color}">'
        f'<div class="card-label">{label}</div>'
        f'<div class="card-value">{value}</div>'
        f'<div class="card-sub">{sub}</div>'
        f'</div>'
    )


def _section(num: int, title: str, body: str, open_default: bool = False) -> str:
    return (
        f'<div class="section">'
        f'<div class="section-header">'
        f'<h2><span class="section-num">{num}</span>{title}</h2>'
        f'<span class="chevron">▾</span>'
        f'</div>'
        f'<div class="section-body{"" if open_default else ""}">{body}</div>'
        f'</div>'
    )


def _step_row(step) -> str:
    icon  = "✅" if step.status == "SUCCESS" else ("⏭️" if step.status == "SKIPPED" else "❌")
    badge = f'<span class="badge badge-{step.status.lower()}">{step.status}</span>'
    return (
        f'<div class="step-row">'
        f'<span class="step-icon">{icon}</span>'
        f'<div style="flex:1">'
        f'<div class="step-name">{step.step}</div>'
        f'<div class="step-detail">{step.detail}</div>'
        f'</div>'
        f'{badge}'
        f'</div>'
    )


def _kv(label: str, value: str) -> str:
    return (
        f'<div class="kv">'
        f'<span class="kv-label">{label}</span>'
        f'<span class="kv-value">{value}</span>'
        f'</div>'
    )
