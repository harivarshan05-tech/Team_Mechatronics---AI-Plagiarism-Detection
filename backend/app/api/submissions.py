"""
Submissions & Upload Sessions API Router:
- Multi-batch upload session management
- Sequential and concurrent file uploads
- ZIP Archive Upload (extracts & organizes by student/filename)
- Language identification & validation
- Pre-loaded sample datasets for immediate testing
"""

import os
import io
import zipfile
import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel

from app.models import (
    SubmissionMeta,
    Language,
    SubmissionCreate,
    UploadSession,
    UploadSessionStatus,
    CreateSessionRequest,
)
from app.database import (
    save_submission,
    list_submissions,
    get_submission,
    delete_submission,
    delete_all_submissions,
    create_session,
    get_session,
    list_sessions,
    update_session,
    delete_session,
    get_or_create_active_session,
)
from app.engine.language_detector import detect_language
from app.engine.stage_ast import parse_ast
from app.engine.stage_cfg import analyze_control_flow

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])

ALLOWED_EXTS = {".py", ".cpp", ".hpp", ".h", ".cc", ".cxx", ".java"}


# -------------------------------------------------------------
# Sessions Endpoints
# -------------------------------------------------------------
@router.get("/sessions", response_model=List[UploadSession])
def get_all_sessions():
    """Lists all upload batch sessions."""
    return list_sessions()


@router.post("/sessions", response_model=UploadSession)
def create_new_session(req: Optional[CreateSessionRequest] = None):
    """Creates a new independent upload batch session."""
    batch_name = req.batch_name if req else None
    return create_session(batch_name=batch_name)


@router.get("/sessions/{session_id}", response_model=UploadSession)
def get_single_session(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Upload session not found")
    return sess


@router.delete("/sessions/{session_id}")
def remove_session(session_id: str):
    delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


# -------------------------------------------------------------
# Submissions Endpoints
# -------------------------------------------------------------
@router.get("", response_model=List[SubmissionMeta])
def get_all_submissions(session_id: Optional[str] = None):
    """
    Returns submissions. If session_id is provided, returns only submissions in that batch.
    """
    return list_submissions(session_id=session_id)


@router.get("/{sub_id}")
def get_single_submission(sub_id: str):
    sub = get_submission(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Include AST and CFG summary for individual details page
    ast_res = parse_ast(sub.content or "", sub.language)
    cfg_res = analyze_control_flow(sub.content or "", sub.language)

    return {
        "submission": sub,
        "ast_summary": {
            "total_nodes": ast_res.total_nodes,
            "structural_signature": ast_res.structural_signature,
            "functions": [
                {
                    "name": f.name,
                    "params": f.params,
                    "body_nodes": f.body_types,
                    "line_start": f.line_start,
                    "line_end": f.line_end,
                }
                for f in ast_res.functions
            ],
            "node_type_sample": ast_res.node_type_sequence[:30],
        },
        "cfg_summary": {
            "total_loops": cfg_res.total_loops,
            "total_branches": cfg_res.total_branches,
            "total_recursions": cfg_res.total_recursions,
            "avg_cyclomatic_complexity": round(cfg_res.avg_cyclomatic_complexity, 2),
            "topological_hash": cfg_res.cfg_topological_hash,
        },
    }


@router.delete("/{sub_id}")
def remove_submission(sub_id: str):
    delete_submission(sub_id)
    return {"status": "deleted", "id": sub_id}


@router.delete("")
def clear_all_submissions():
    delete_all_submissions()
    return {"status": "all submissions cleared"}


@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    student_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    batch_name: Optional[str] = Form(None),
):
    """
    Uploads submissions to a specific session. If session_id is not provided,
    creates or uses an active batch session.
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided for upload")

    # Resolve or create session
    target_session_id = session_id
    if not target_session_id or target_session_id == "new":
        sess = create_session(batch_name=batch_name)
        target_session_id = sess.session_id
    else:
        # Check if exists
        existing = get_session(target_session_id)
        if not existing:
            sess = create_session(batch_name=batch_name, session_id=target_session_id)
            target_session_id = sess.session_id

    saved: List[SubmissionMeta] = []

    for file in files:
        fname = file.filename or "unknown"
        ext = os.path.splitext(fname)[1].lower()

        # Handle ZIP files
        if ext == ".zip":
            zip_bytes = await file.read()
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                    for member in z.infolist():
                        if member.is_dir():
                            continue
                        # Prevent path traversal
                        if ".." in member.filename or member.filename.startswith("/"):
                            continue

                        mem_ext = os.path.splitext(member.filename)[1].lower()
                        if mem_ext not in ALLOWED_EXTS:
                            continue

                        parts = member.filename.replace("\\", "/").strip("/").split("/")
                        inferred_student = parts[0] if len(parts) > 1 else (student_id or "student_zip")
                        leaf_name = parts[-1]

                        raw_content = z.read(member)
                        try:
                            text_content = raw_content.decode("utf-8")
                        except UnicodeDecodeError:
                            text_content = raw_content.decode("latin-1", errors="replace")

                        lang = detect_language(leaf_name, text_content)
                        sub_id = str(uuid.uuid4())[:8]
                        sub_meta = save_submission(
                            sub_id=sub_id,
                            filename=leaf_name,
                            student_id=inferred_student,
                            language=lang,
                            content=text_content,
                            session_id=target_session_id,
                        )
                        saved.append(sub_meta)
            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail=f"Invalid or corrupted zip file: {fname}")
            continue

        # Regular single or multi-file upload
        if ext not in ALLOWED_EXTS and ext != "":
            continue

        raw = await file.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("latin-1", errors="replace")

        clean_base = os.path.splitext(os.path.basename(fname))[0]
        inferred_id = student_id or (clean_base.split("_")[0] if "_" in clean_base else clean_base)

        lang = detect_language(fname, content)
        sub_id = str(uuid.uuid4())[:8]
        sub_meta = save_submission(
            sub_id=sub_id,
            filename=os.path.basename(fname),
            student_id=inferred_id,
            language=lang,
            content=content,
            session_id=target_session_id,
        )
        saved.append(sub_meta)

    return {
        "session_id": target_session_id,
        "uploaded_count": len(saved),
        "submissions": saved,
    }


@router.post("/load-samples")
def load_sample_datasets(
    session_id: Optional[str] = None,
    batch_name: Optional[str] = "Benchmark Sample Pack",
):
    """
    Loads rich sample submissions into a dedicated batch session.
    """
    from app.sample_data import get_sample_submissions

    target_session_id = session_id
    if not target_session_id or target_session_id == "new":
        sess = create_session(batch_name=batch_name)
        target_session_id = sess.session_id

    samples = get_sample_submissions()
    loaded = []
    for s in samples:
        sub_id = f"{s['id']}_{str(uuid.uuid4())[:4]}"
        lang = detect_language(s["filename"], s["content"])
        meta = save_submission(
            sub_id=sub_id,
            filename=s["filename"],
            student_id=s["student_id"],
            language=lang,
            content=s["content"],
            session_id=target_session_id,
        )
        loaded.append(meta)

    return {
        "session_id": target_session_id,
        "loaded_count": len(loaded),
        "submissions": loaded,
    }
