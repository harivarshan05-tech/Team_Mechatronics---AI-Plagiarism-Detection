"""
SQLite database management for submissions, analysis runs, comparison results,
and multi-batch upload session tracking.
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

from app.config import DB_PATH
from app.models import (
    Language,
    PairComparisonResult,
    RiskLevel,
    ScoringWeights,
    SubmissionMeta,
    MatchSpan,
    MatchType,
    UploadSession,
    UploadSessionStatus,
)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS upload_sessions (
        session_id TEXT PRIMARY KEY,
        batch_name TEXT NOT NULL,
        status TEXT NOT NULL,
        submission_count INTEGER NOT NULL DEFAULT 0,
        file_names_json TEXT NOT NULL DEFAULT '[]',
        languages_json TEXT NOT NULL DEFAULT '[]',
        job_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        student_id TEXT NOT NULL,
        language TEXT NOT NULL,
        content TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL,
        line_count INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        session_id TEXT NOT NULL DEFAULT 'default_session'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_runs (
        job_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        total_submissions INTEGER NOT NULL,
        total_pairs INTEGER NOT NULL,
        suspicious_pairs INTEGER NOT NULL,
        high_risk INTEGER NOT NULL,
        medium_risk INTEGER NOT NULL,
        low_risk INTEGER NOT NULL,
        processing_time_seconds REAL NOT NULL,
        language_dist_json TEXT NOT NULL,
        weights_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        session_id TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pair_results (
        pair_id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        sub_a_id TEXT NOT NULL,
        sub_a_name TEXT NOT NULL,
        sub_a_student TEXT NOT NULL,
        sub_b_id TEXT NOT NULL,
        sub_b_name TEXT NOT NULL,
        sub_b_student TEXT NOT NULL,
        language TEXT NOT NULL,
        overall_similarity REAL NOT NULL,
        risk_level TEXT NOT NULL,
        ast_score REAL NOT NULL,
        cfg_score REAL NOT NULL,
        fingerprint_score REAL NOT NULL,
        token_score REAL NOT NULL,
        function_score REAL NOT NULL,
        has_renamed_identifiers INTEGER NOT NULL,
        has_reordered_functions INTEGER NOT NULL,
        has_loop_to_recursion INTEGER NOT NULL,
        has_modified_conditionals INTEGER NOT NULL,
        matching_spans_json TEXT NOT NULL,
        summary TEXT NOT NULL,
        session_id TEXT,
        FOREIGN KEY(job_id) REFERENCES analysis_runs(job_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL
    );
    """)

    # Safe migrations for existing databases
    cursor.execute("PRAGMA table_info(submissions)")
    sub_cols = [row["name"] for row in cursor.fetchall()]
    if "session_id" not in sub_cols:
        cursor.execute("ALTER TABLE submissions ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default_session'")

    cursor.execute("PRAGMA table_info(analysis_runs)")
    run_cols = [row["name"] for row in cursor.fetchall()]
    if "session_id" not in run_cols:
        cursor.execute("ALTER TABLE analysis_runs ADD COLUMN session_id TEXT")

    cursor.execute("PRAGMA table_info(pair_results)")
    pair_cols = [row["name"] for row in cursor.fetchall()]
    if "session_id" not in pair_cols:
        cursor.execute("ALTER TABLE pair_results ADD COLUMN session_id TEXT")

    conn.commit()
    conn.close()


# -------------------------------------------------------------
# Upload Session Management
# -------------------------------------------------------------
def create_session(batch_name: Optional[str] = None, session_id: Optional[str] = None) -> UploadSession:
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now(timezone.utc).isoformat()
    if not session_id:
        import uuid
        session_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    if not batch_name:
        cursor.execute("SELECT COUNT(*) as count FROM upload_sessions")
        count = cursor.fetchone()["count"] + 1
        batch_name = f"Batch {count} - Submission Set"

    cursor.execute(
        """
        INSERT INTO upload_sessions (
            session_id, batch_name, status, submission_count,
            file_names_json, languages_json, job_id, created_at, updated_at
        ) VALUES (?, ?, ?, 0, '[]', '[]', NULL, ?, ?)
        """,
        (session_id, batch_name, UploadSessionStatus.DRAFT.value, now, now),
    )
    conn.commit()
    conn.close()

    return UploadSession(
        session_id=session_id,
        batch_name=batch_name,
        status=UploadSessionStatus.DRAFT,
        submission_count=0,
        file_names=[],
        languages=[],
        job_id=None,
        created_at=now,
        updated_at=now,
    )


def get_session(session_id: str) -> Optional[UploadSession]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upload_sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None

    return UploadSession(
        session_id=row["session_id"],
        batch_name=row["batch_name"],
        status=UploadSessionStatus(row["status"]),
        submission_count=row["submission_count"],
        file_names=json.loads(row["file_names_json"]),
        languages=json.loads(row["languages_json"]),
        job_id=row["job_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def get_or_create_active_session() -> UploadSession:
    """Returns the latest non-completed or latest session, or creates a new one."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upload_sessions ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return create_session("Batch 1 - Initial Submission Set")

    # If the latest session is already Completed, create a new draft session for the next batch!
    if row["status"] == UploadSessionStatus.COMPLETED.value:
        return create_session()

    return UploadSession(
        session_id=row["session_id"],
        batch_name=row["batch_name"],
        status=UploadSessionStatus(row["status"]),
        submission_count=row["submission_count"],
        file_names=json.loads(row["file_names_json"]),
        languages=json.loads(row["languages_json"]),
        job_id=row["job_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_sessions() -> List[UploadSession]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upload_sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    return [
        UploadSession(
            session_id=r["session_id"],
            batch_name=r["batch_name"],
            status=UploadSessionStatus(r["status"]),
            submission_count=r["submission_count"],
            file_names=json.loads(r["file_names_json"]),
            languages=json.loads(r["languages_json"]),
            job_id=r["job_id"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


def update_session(
    session_id: str,
    status: Optional[UploadSessionStatus] = None,
    job_id: Optional[str] = None,
    new_filename: Optional[str] = None,
    new_language: Optional[str] = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upload_sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return

    files = json.loads(row["file_names_json"])
    langs = json.loads(row["languages_json"])
    count = row["submission_count"]

    if new_filename and new_filename not in files:
        files.append(new_filename)
        count = len(files)
    if new_language and new_language not in langs:
        langs.append(new_language)

    new_status = status.value if status else row["status"]
    new_job_id = job_id if job_id is not None else row["job_id"]
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        UPDATE upload_sessions SET
            status = ?,
            submission_count = ?,
            file_names_json = ?,
            languages_json = ?,
            job_id = ?,
            updated_at = ?
        WHERE session_id = ?
        """,
        (new_status, count, json.dumps(files), json.dumps(langs), new_job_id, now, session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pair_results WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM analysis_runs WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM submissions WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM upload_sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


# -------------------------------------------------------------
# Submission CRUD
# -------------------------------------------------------------
def save_submission(
    sub_id: str,
    filename: str,
    student_id: str,
    language: Language,
    content: str,
    session_id: str = "default_session",
) -> SubmissionMeta:
    lines = content.splitlines()
    line_count = len(lines)
    file_size = len(content.encode("utf-8"))
    created_at = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO submissions (
            id, filename, student_id, language, content, file_size_bytes, line_count, created_at, session_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sub_id,
            filename,
            student_id,
            language.value,
            content,
            file_size,
            line_count,
            created_at,
            session_id,
        ),
    )
    conn.commit()
    conn.close()

    # Update session statistics
    update_session(
        session_id=session_id,
        status=UploadSessionStatus.UPLOADED,
        new_filename=filename,
        new_language=language.value,
    )

    return SubmissionMeta(
        id=sub_id,
        filename=filename,
        student_id=student_id,
        language=language,
        file_size_bytes=file_size,
        line_count=line_count,
        created_at=created_at,
        content=content,
        session_id=session_id,
    )


def get_submission(sub_id: str) -> Optional[SubmissionMeta]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM submissions WHERE id = ?", (sub_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return SubmissionMeta(
        id=row["id"],
        filename=row["filename"],
        student_id=row["student_id"],
        language=Language(row["language"]),
        file_size_bytes=row["file_size_bytes"],
        line_count=row["line_count"],
        created_at=row["created_at"],
        content=row["content"],
        session_id=row["session_id"] if "session_id" in row.keys() else "default_session",
    )


def list_submissions(session_id: Optional[str] = None) -> List[SubmissionMeta]:
    conn = get_connection()
    cursor = conn.cursor()
    if session_id and session_id != "all":
        cursor.execute(
            """
            SELECT id, filename, student_id, language, file_size_bytes, line_count, created_at, session_id
            FROM submissions WHERE session_id = ? ORDER BY created_at DESC
            """,
            (session_id,),
        )
    else:
        cursor.execute(
            """
            SELECT id, filename, student_id, language, file_size_bytes, line_count, created_at, session_id
            FROM submissions ORDER BY created_at DESC
            """
        )
    rows = cursor.fetchall()
    conn.close()
    return [
        SubmissionMeta(
            id=r["id"],
            filename=r["filename"],
            student_id=r["student_id"],
            language=Language(r["language"]),
            file_size_bytes=r["file_size_bytes"],
            line_count=r["line_count"],
            created_at=r["created_at"],
            content=None,
            session_id=r["session_id"] if "session_id" in r.keys() else "default_session",
        )
        for r in rows
    ]


def delete_all_submissions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pair_results")
    cursor.execute("DELETE FROM analysis_runs")
    cursor.execute("DELETE FROM submissions")
    cursor.execute("DELETE FROM upload_sessions")
    cursor.execute("DELETE FROM settings")
    conn.commit()
    conn.close()


def delete_submission(sub_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM submissions WHERE id = ?", (sub_id,))
    cursor.execute("DELETE FROM pair_results WHERE sub_a_id = ? OR sub_b_id = ?", (sub_id, sub_id))
    conn.commit()
    conn.close()


# -------------------------------------------------------------
# Analysis Runs CRUD
# -------------------------------------------------------------
def save_analysis_run(
    job_id: str,
    status: str,
    total_submissions: int,
    total_pairs: int,
    suspicious_pairs: int,
    high_risk: int,
    medium_risk: int,
    low_risk: int,
    processing_time_seconds: float,
    language_distribution: Dict[str, int],
    weights: ScoringWeights,
    results: List[PairComparisonResult],
    session_id: Optional[str] = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        INSERT OR REPLACE INTO analysis_runs (
            job_id, status, total_submissions, total_pairs, suspicious_pairs,
            high_risk, medium_risk, low_risk, processing_time_seconds,
            language_dist_json, weights_json, created_at, session_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            status,
            total_submissions,
            total_pairs,
            suspicious_pairs,
            high_risk,
            medium_risk,
            low_risk,
            processing_time_seconds,
            json.dumps(language_distribution),
            json.dumps(weights.model_dump()),
            created_at,
            session_id,
        ),
    )

    for r in results:
        spans_json = json.dumps([s.model_dump() for s in r.matching_spans])
        cursor.execute(
            """
            INSERT OR REPLACE INTO pair_results (
                pair_id, job_id, sub_a_id, sub_a_name, sub_a_student,
                sub_b_id, sub_b_name, sub_b_student, language,
                overall_similarity, risk_level,
                ast_score, cfg_score, fingerprint_score, token_score, function_score,
                has_renamed_identifiers, has_reordered_functions,
                has_loop_to_recursion, has_modified_conditionals,
                matching_spans_json, summary, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r.pair_id,
                job_id,
                r.submission_a_id,
                r.submission_a_name,
                r.submission_a_student,
                r.submission_b_id,
                r.submission_b_name,
                r.submission_b_student,
                r.language.value,
                r.overall_similarity,
                r.risk_level.value,
                r.ast_score,
                r.cfg_score,
                r.fingerprint_score,
                r.token_score,
                r.function_score,
                1 if r.has_renamed_identifiers else 0,
                1 if r.has_reordered_functions else 0,
                1 if r.has_loop_to_recursion else 0,
                1 if r.has_modified_conditionals else 0,
                spans_json,
                r.summary,
                session_id,
            ),
        )

    conn.commit()
    conn.close()

    if session_id:
        update_session(session_id=session_id, status=UploadSessionStatus.COMPLETED, job_id=job_id)


def get_latest_analysis_run(
    job_id: Optional[str] = None, session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    if job_id:
        cursor.execute("SELECT * FROM analysis_runs WHERE job_id = ?", (job_id,))
    elif session_id:
        cursor.execute("SELECT * FROM analysis_runs WHERE session_id = ? ORDER BY created_at DESC LIMIT 1", (session_id,))
    else:
        cursor.execute("SELECT * FROM analysis_runs ORDER BY created_at DESC LIMIT 1")

    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    actual_job_id = row["job_id"]
    sess_id = row["session_id"] if "session_id" in row.keys() else None

    # Fetch batch name if session exists
    batch_name = None
    if sess_id:
        cursor.execute("SELECT batch_name FROM upload_sessions WHERE session_id = ?", (sess_id,))
        s_row = cursor.fetchone()
        if s_row:
            batch_name = s_row["batch_name"]

    cursor.execute(
        "SELECT * FROM pair_results WHERE job_id = ? ORDER BY overall_similarity DESC",
        (actual_job_id,),
    )
    pair_rows = cursor.fetchall()
    conn.close()

    pairs: List[PairComparisonResult] = []
    for pr in pair_rows:
        spans_data = json.loads(pr["matching_spans_json"])
        spans = [
            MatchSpan(
                span_id=s["span_id"],
                match_type=MatchType(s["match_type"]),
                sub_a_start_line=s["sub_a_start_line"],
                sub_a_end_line=s["sub_a_end_line"],
                sub_b_start_line=s["sub_b_start_line"],
                sub_b_end_line=s["sub_b_end_line"],
                description=s["description"],
                confidence=s.get("confidence", 1.0),
            )
            for s in spans_data
        ]
        pairs.append(
            PairComparisonResult(
                pair_id=pr["pair_id"],
                submission_a_id=pr["sub_a_id"],
                submission_a_name=pr["sub_a_name"],
                submission_a_student=pr["sub_a_student"],
                submission_b_id=pr["sub_b_id"],
                submission_b_name=pr["sub_b_name"],
                submission_b_student=pr["sub_b_student"],
                language=Language(pr["language"]),
                overall_similarity=pr["overall_similarity"],
                risk_level=RiskLevel(pr["risk_level"]),
                ast_score=pr["ast_score"],
                cfg_score=pr["cfg_score"],
                fingerprint_score=pr["fingerprint_score"],
                token_score=pr["token_score"],
                function_score=pr["function_score"],
                has_renamed_identifiers=bool(pr["has_renamed_identifiers"]),
                has_reordered_functions=bool(pr["has_reordered_functions"]),
                has_loop_to_recursion=bool(pr["has_loop_to_recursion"]),
                has_modified_conditionals=bool(pr["has_modified_conditionals"]),
                matching_spans=spans,
                summary=pr["summary"],
                session_id=sess_id,
            )
        )

    return {
        "job_id": row["job_id"],
        "session_id": sess_id,
        "batch_name": batch_name or (f"Session {sess_id}" if sess_id else "All Submissions"),
        "status": row["status"],
        "total_submissions": row["total_submissions"],
        "total_pairs_evaluated": row["total_pairs"],
        "suspicious_pairs_count": row["suspicious_pairs"],
        "high_risk_count": row["high_risk"],
        "medium_risk_count": row["medium_risk"],
        "low_risk_count": row["low_risk"],
        "processing_time_seconds": row["processing_time_seconds"],
        "language_distribution": json.loads(row["language_dist_json"]),
        "scoring_weights_used": ScoringWeights(**json.loads(row["weights_json"])),
        "created_at": row["created_at"],
        "top_suspicious_pairs": pairs,
    }


def list_analysis_history() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ar.*, us.batch_name
        FROM analysis_runs ar
        LEFT JOIN upload_sessions us ON ar.session_id = us.session_id
        ORDER BY ar.created_at DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        history.append({
            "job_id": r["job_id"],
            "session_id": r["session_id"],
            "batch_name": r["batch_name"] or f"Scan {r['job_id'][:8]}",
            "status": r["status"],
            "total_submissions": r["total_submissions"],
            "total_pairs": r["total_pairs"],
            "suspicious_pairs": r["suspicious_pairs"],
            "high_risk": r["high_risk"],
            "medium_risk": r["medium_risk"],
            "low_risk": r["low_risk"],
            "processing_time_seconds": r["processing_time_seconds"],
            "languages": list(json.loads(r["language_dist_json"]).keys()),
            "created_at": r["created_at"],
        })
    return history


def get_pair_result(pair_id: str) -> Optional[PairComparisonResult]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pair_results WHERE pair_id = ?", (pair_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None

    spans_data = json.loads(row["matching_spans_json"])
    spans = [
        MatchSpan(
            span_id=s["span_id"],
            match_type=MatchType(s["match_type"]),
            sub_a_start_line=s["sub_a_start_line"],
            sub_a_end_line=s["sub_a_end_line"],
            sub_b_start_line=s["sub_b_start_line"],
            sub_b_end_line=s["sub_b_end_line"],
            description=s["description"],
            confidence=s.get("confidence", 1.0),
        )
        for s in spans_data
    ]

    return PairComparisonResult(
        pair_id=row["pair_id"],
        submission_a_id=row["sub_a_id"],
        submission_a_name=row["sub_a_name"],
        submission_a_student=row["sub_a_student"],
        submission_b_id=row["sub_b_id"],
        submission_b_name=row["sub_b_name"],
        submission_b_student=row["sub_b_student"],
        language=Language(row["language"]),
        overall_similarity=row["overall_similarity"],
        risk_level=RiskLevel(row["risk_level"]),
        ast_score=row["ast_score"],
        cfg_score=row["cfg_score"],
        fingerprint_score=row["fingerprint_score"],
        token_score=row["token_score"],
        function_score=row["function_score"],
        has_renamed_identifiers=bool(row["has_renamed_identifiers"]),
        has_reordered_functions=bool(row["has_reordered_functions"]),
        has_loop_to_recursion=bool(row["has_loop_to_recursion"]),
        has_modified_conditionals=bool(row["has_modified_conditionals"]),
        matching_spans=spans,
        summary=row["summary"],
        session_id=row["session_id"] if "session_id" in row.keys() else None,
    )


def save_setting(key: str, value: Any):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value_json) VALUES (?, ?)",
        (key, json.dumps(value)),
    )
    conn.commit()
    conn.close()


def get_setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value_json FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return default
    return json.loads(row["value_json"])
