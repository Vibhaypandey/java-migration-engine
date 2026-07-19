from __future__ import annotations
from app.models.build import BuildResult, AttemptRecord


def render_build_report(result: BuildResult) -> str:
    is_success = result.status == "SUCCESS"
    banner_color = "#198754" if is_success else "#dc3545"
    banner_icon  = "🎉" if is_success else "🔴"
    title = "Build Successful" if is_success else "Build Failed — Manual Intervention Required"

    attempt_rows = "".join(_attempt_row(a) for a in result.attempts)
    files_html = _files_list(result.files_modified)

    jar_section = ""
    if is_success and result.jar_generated:
        jar_section = f"""
  <div class="card">
    <div class="card-header">📦 Generated Artifact</div>
    <div class="card-body">
      <div class="kv">{_kv("JAR Location", result.jar_location)}</div>
      <div class="kv">{_kv("Status", '<span class="badge badge-success">READY</span>')}</div>
    </div>
  </div>"""

    manual_section = ""
    if result.manual_intervention_required:
        manual_section = """
  <div class="alert-box">
    <div class="alert-title">⚠️ Manual Intervention Required</div>
    <p>The automated build loop reached the maximum retry limit without a successful build.
    Review the attempt history below, inspect the remaining errors in the build logs,
    and apply fixes manually before re-running the build.</p>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Build Report — {result.project_id[:8]}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --primary:#1a56db;--primary-dark:#1e429f;
  --bg:#f3f4f6;--surface:#fff;--border:#e5e7eb;
  --text:#111827;--muted:#6b7280;
  --radius:10px;--shadow:0 1px 3px rgba(0,0,0,.1);
}}
body{{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.5}}
.header{{position:sticky;top:0;z-index:100;background:var(--primary-dark);color:#fff;
  padding:.75rem 2rem;display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 2px 8px rgba(0,0,0,.25)}}
.header h1{{font-size:1.1rem;font-weight:700}}
.page{{max-width:960px;margin:2rem auto;padding:0 1rem 3rem}}
.banner{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.5rem 2rem;margin-bottom:1.5rem;box-shadow:var(--shadow);
  display:flex;align-items:center;gap:1.25rem;border-left:5px solid {banner_color}}}
.banner-icon{{font-size:2.5rem;line-height:1}}
.banner-title{{font-size:1.3rem;font-weight:700}}
.banner-sub{{font-size:.875rem;color:var(--muted);margin-top:.2rem}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;margin-bottom:1.5rem}}
.stat-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:1rem 1.25rem;box-shadow:var(--shadow)}}
.stat-label{{font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:.3rem}}
.stat-value{{font-size:1.6rem;font-weight:700}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  box-shadow:var(--shadow);margin-bottom:1.25rem;overflow:hidden}}
.card-header{{padding:.85rem 1.25rem;font-weight:700;font-size:.9rem;
  background:#f9fafb;border-bottom:1px solid var(--border)}}
.card-body{{padding:1rem 1.25rem}}
.attempt{{border-bottom:1px solid #f3f4f6;padding:1rem 1.25rem}}
.attempt:last-child{{border-bottom:none}}
.attempt-header{{display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem}}
.attempt-num{{background:var(--primary);color:#fff;border-radius:50%;
  width:1.6rem;height:1.6rem;display:flex;align-items:center;justify-content:center;
  font-size:.75rem;font-weight:700;flex-shrink:0}}
.attempt-title{{font-weight:600;font-size:.9rem;flex:1}}
.attempt-meta{{font-size:.78rem;color:var(--muted)}}
.error-box{{background:#fff5f5;border:1px solid #fecaca;border-radius:8px;
  padding:.75rem 1rem;margin-top:.5rem;font-size:.82rem}}
.error-file{{font-weight:600;color:#dc3545;margin-bottom:.25rem}}
.error-msg{{color:#7f1d1d}}
.fix-box{{background:#f0fff4;border:1px solid #bbf7d0;border-radius:8px;
  padding:.75rem 1rem;margin-top:.5rem;font-size:.82rem}}
.fix-title{{font-weight:600;color:#166534;margin-bottom:.25rem}}
.files-list{{list-style:none;padding:0}}
.files-list li{{padding:.3rem 0;font-size:.82rem;font-family:monospace;
  border-bottom:1px solid #f3f4f6;color:var(--muted)}}
.files-list li:last-child{{border-bottom:none}}
.kv{{display:flex;justify-content:space-between;align-items:center;
  padding:.4rem 0;border-bottom:1px solid #f3f4f6;font-size:.875rem}}
.kv:last-child{{border-bottom:none}}
.badge{{display:inline-flex;align-items:center;padding:.15rem .55rem;
  border-radius:20px;font-size:.7rem;font-weight:700;text-transform:uppercase}}
.badge-success{{background:#f0fff4;color:#198754;border:1px solid #bbf7d0}}
.badge-failed{{background:#fff5f5;color:#dc3545;border:1px solid #fecaca}}
.alert-box{{background:#fffbeb;border:1px solid #fcd34d;border-radius:var(--radius);
  padding:1.25rem;margin-bottom:1.25rem}}
.alert-title{{font-weight:700;font-size:.95rem;margin-bottom:.5rem;color:#92400e}}
.actions{{display:flex;gap:.75rem;margin-top:1.5rem;flex-wrap:wrap}}
.btn{{display:inline-flex;align-items:center;gap:.4rem;padding:.6rem 1.25rem;
  border-radius:8px;font-size:.875rem;font-weight:600;text-decoration:none}}
.btn-primary{{background:var(--primary);color:#fff}}
.btn-outline{{background:var(--surface);color:var(--primary);border:1px solid var(--primary)}}
</style>
</head>
<body>
<header class="header">
  <h1>☕ Java Migration Assistant</h1>
  <span style="font-size:.8rem;opacity:.8">Build Verification Report</span>
</header>
<div class="page">

  <div class="banner">
    <div class="banner-icon">{banner_icon}</div>
    <div>
      <div class="banner-title">{title}</div>
      <div class="banner-sub">Project: {result.project_id}</div>
    </div>
  </div>

  {manual_section}

  <div class="cards">
    {_stat("Attempts", str(result.total_attempts))}
    {_stat("Errors Fixed", str(result.errors_fixed))}
    {_stat("Files Modified", str(len(result.files_modified)))}
    {_stat("Final Status", result.status)}
    {_stat("JAR Generated", "Yes" if result.jar_generated else "No")}
  </div>

  {jar_section}

  <div class="card">
    <div class="card-header">Build Attempt History</div>
    {attempt_rows}
  </div>

  {files_html}

  <div class="actions">
    <a class="btn btn-primary" href="/assessment/{result.project_id}/report">📋 Assessment Report</a>
    <a class="btn btn-outline"  href="/migration/{result.project_id}/summary">🔧 Migration Summary</a>
  </div>

</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Component helpers
# ---------------------------------------------------------------------------

def _stat(label: str, value: str) -> str:
    return (
        f'<div class="stat-card">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'</div>'
    )


def _kv(label: str, value: str) -> str:
    return f'<span style="color:var(--muted)">{label}</span><span>{value}</span>'


def _attempt_row(a: AttemptRecord) -> str:
    badge = f'<span class="badge badge-{a.status.lower()}">{a.status}</span>'
    error_html = ""
    if a.error:
        error_html = (
            f'<div class="error-box">'
            f'<div class="error-file">📄 {a.error.file_path} — line {a.error.line_number or "?"}</div>'
            f'<div class="error-msg">{a.error.error_message}</div>'
            f'</div>'
        )
    fix_html = ""
    if a.ai_fix_reason:
        fix_html = (
            f'<div class="fix-box">'
            f'<div class="fix-title">🤖 AI Fix Applied</div>'
            f'<div>{a.ai_fix_reason}</div>'
            f'{"<div style=margin-top:.3rem>Files: " + ", ".join(a.files_modified) + "</div>" if a.files_modified else ""}'
            f'</div>'
        )
    return (
        f'<div class="attempt">'
        f'<div class="attempt-header">'
        f'<div class="attempt-num">{a.attempt_number}</div>'
        f'<div class="attempt-title">Attempt {a.attempt_number}</div>'
        f'{badge}'
        f'</div>'
        f'<div class="attempt-meta">Exit code: {a.exit_code} &nbsp;·&nbsp; Duration: {a.duration_seconds:.1f}s &nbsp;·&nbsp; Log: {a.log_file}</div>'
        f'{error_html}{fix_html}'
        f'</div>'
    )


def _files_list(files: list[str]) -> str:
    if not files:
        return ""
    items = "".join(f"<li>{f}</li>" for f in files)
    return (
        f'<div class="card">'
        f'<div class="card-header">Modified Files</div>'
        f'<div class="card-body"><ul class="files-list">{items}</ul></div>'
        f'</div>'
    )
