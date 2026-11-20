"""
Reports & Export API Router:
Exports plagiarism investigation reports in JSON, CSV, and printable HTML formats,
supporting batch session filtering and historical report retrieval.
"""

import io
import csv
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, HTMLResponse

from app.database import get_latest_analysis_run

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/json")
def export_json_report(
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    run = get_latest_analysis_run(job_id=job_id, session_id=session_id)
    if not run:
        raise HTTPException(status_code=404, detail="No analysis run available to export")

    content = json.dumps(run, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o), indent=2)
    filename = f"plagiarism_report_{run['job_id']}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/csv")
def export_csv_report(
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    run = get_latest_analysis_run(job_id=job_id, session_id=session_id)
    if not run:
        raise HTTPException(status_code=404, detail="No analysis run available to export")

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Pair ID",
        "Submission A Student",
        "Submission A File",
        "Submission B Student",
        "Submission B File",
        "Language",
        "Overall Similarity (%)",
        "Risk Level",
        "AST Score (%)",
        "CFG Score (%)",
        "Fingerprint Score (%)",
        "Token Score (%)",
        "Function Score (%)",
        "Renamed Identifiers",
        "Reordered Functions",
        "Loop to Recursion",
        "Summary",
    ])

    for p in run["top_suspicious_pairs"]:
        writer.writerow([
            p.pair_id,
            p.submission_a_student,
            p.submission_a_name,
            p.submission_b_student,
            p.submission_b_name,
            p.language.value,
            p.overall_similarity,
            p.risk_level.value.upper(),
            p.ast_score,
            p.cfg_score,
            p.fingerprint_score,
            p.token_score,
            p.function_score,
            "YES" if p.has_renamed_identifiers else "NO",
            "YES" if p.has_reordered_functions else "NO",
            "YES" if p.has_loop_to_recursion else "NO",
            p.summary,
        ])

    filename = f"plagiarism_report_{run['job_id']}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/html", response_class=HTMLResponse)
def export_html_report(
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    run = get_latest_analysis_run(job_id=job_id, session_id=session_id)
    if not run:
        raise HTTPException(status_code=404, detail="No analysis run available to export")

    pairs = run["top_suspicious_pairs"]
    batch_title = run.get("batch_name", f"Scan {run['job_id']}")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Plagiarism Investigation Audit Report - {batch_title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.5; color: #1e293b; background: #f8fafc; padding: 2rem; margin: 0; }}
    .container {{ max-width: 1000px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 2.5rem; }}
    .header {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 1.5rem; margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; }}
    .title {{ font-size: 1.75rem; font-weight: 700; color: #0f172a; margin: 0; }}
    .meta {{ font-size: 0.875rem; color: #64748b; margin-top: 0.25rem; }}
    .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }}
    .stat-card {{ background: #f1f5f9; border-radius: 8px; padding: 1.25rem; text-align: center; }}
    .stat-val {{ font-size: 1.75rem; font-weight: 700; color: #0f172a; }}
    .stat-val.high {{ color: #dc2626; }}
    .stat-val.med {{ color: #d97706; }}
    .stat-val.time {{ color: #2563eb; }}
    .stat-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; font-weight: 600; margin-top: 0.25rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; font-size: 0.875rem; }}
    th {{ background: #f8fafc; text-align: left; padding: 0.75rem 1rem; border-bottom: 2px solid #cbd5e1; color: #475569; font-weight: 600; }}
    td {{ padding: 0.75rem 1rem; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
    tr:hover {{ background: #f8fafc; }}
    .badge {{ display: inline-block; padding: 0.25rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
    .badge-high {{ background: #fee2e2; color: #991b1b; }}
    .badge-med {{ background: #fef3c7; color: #92400e; }}
    .badge-low {{ background: #dcfce7; color: #166534; }}
    .tag {{ display: inline-block; background: #e0e7ff; color: #3730a3; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.7rem; margin-right: 0.25rem; margin-top: 0.25rem; font-weight: 500; }}
    .print-btn {{ background: #2563eb; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer; }}
    @media print {{
      body {{ background: white; padding: 0; }}
      .container {{ box-shadow: none; padding: 0; }}
      .print-btn {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1 class="title">Plagiarism Investigation Audit Report</h1>
        <div class="meta">Batch: <strong>{batch_title}</strong> &bull; Run ID: <strong>{run['job_id']}</strong> | Generated: {run['created_at']} UTC</div>
      </div>
      <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-val">{run['total_submissions']}</div>
        <div class="stat-label">Submissions Analyzed</div>
      </div>
      <div class="stat-card">
        <div class="stat-val high">{run['high_risk_count']}</div>
        <div class="stat-label">High Risk Matches</div>
      </div>
      <div class="stat-card">
        <div class="stat-val med">{run['medium_risk_count']}</div>
        <div class="stat-label">Medium Risk Matches</div>
      </div>
      <div class="stat-card">
        <div class="stat-val time">{run['processing_time_seconds']}s</div>
        <div class="stat-label">Processing Time</div>
      </div>
    </div>

    <h2>Ranked Suspicious Matches</h2>
    <p style="color: #64748b; font-size: 0.9rem;">
      Submissions flagged based on multi-stage structural AST, Control Flow Graph topology, MinHash structural fingerprinting, and token normalization.
    </p>

    <table>
      <thead>
        <tr>
          <th>Risk</th>
          <th>Similarity</th>
          <th>Student A (File)</th>
          <th>Student B (File)</th>
          <th>Dimensional Scores</th>
          <th>Detections & Summary</th>
        </tr>
      </thead>
      <tbody>
"""

    for p in pairs:
        if p.risk_level.value == "low" and p.overall_similarity < 30.0:
            continue
        badge_cls = f"badge-{p.risk_level.value}"
        tags = []
        if p.has_loop_to_recursion:
            tags.append('<span class="tag">Loop-to-Recursion</span>')
        if p.has_renamed_identifiers:
            tags.append('<span class="tag">Renamed IDs</span>')
        if p.has_reordered_functions:
            tags.append('<span class="tag">Reordered Logic</span>')

        tags_html = "".join(tags)

        html += f"""
        <tr>
          <td><span class="badge {badge_cls}">{p.risk_level.value}</span></td>
          <td><strong style="font-size: 1.1rem;">{p.overall_similarity}%</strong></td>
          <td><strong>{p.submission_a_student}</strong><br><small style="color: #64748b;">{p.submission_a_name}</small></td>
          <td><strong>{p.submission_b_student}</strong><br><small style="color: #64748b;">{p.submission_b_name}</small></td>
          <td style="font-size: 0.8rem; line-height: 1.4;">
            AST: {p.ast_score}%<br>
            CFG: {p.cfg_score}%<br>
            F-Print: {p.fingerprint_score}%<br>
            Token: {p.token_score}%
          </td>
          <td>
            <div>{tags_html}</div>
            <div style="margin-top: 0.35rem; color: #334155;">{p.summary}</div>
          </td>
        </tr>
"""

    html += """
      </tbody>
    </table>

    <div style="margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0; font-size: 0.8rem; color: #94a3b8; text-align: center;">
      Generated by VeritasCode Plagiarism Engine &bull; Multi-Batch Session Architecture &bull; Non-destructive Analysis
    </div>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html)
