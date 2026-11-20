"""
Analysis API Router:
- Start detection pipeline for specific upload batch sessions or all submissions
- Real-time WebSocket progress broadcasts
- Analysis run history for revisiting previous reports
- Latest results & query filtering (by risk level, language, student, min similarity, session)
- Configurable scoring weights
"""

import asyncio
import json
import uuid
from typing import List, Optional, Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.models import (
    AnalysisProgress,
    AnalysisRunResult,
    PairComparisonResult,
    RiskLevel,
    ScoringWeights,
    Language,
    UploadSessionStatus,
)
from app.database import (
    list_submissions,
    get_submission,
    save_analysis_run,
    get_latest_analysis_run,
    save_setting,
    get_setting,
    list_analysis_history,
    update_session,
    get_session,
    get_or_create_active_session,
)
from app.engine.pipeline import PlagiarismPipeline

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

# Active WebSocket connections per job_id
active_websockets: Dict[str, Set[WebSocket]] = {}
current_progress: Dict[str, AnalysisProgress] = {}


async def broadcast_progress(job_id: str, progress: AnalysisProgress):
    current_progress[job_id] = progress
    if job_id in active_websockets:
        dead_sockets = set()
        msg_str = progress.model_dump_json()
        for ws in active_websockets[job_id]:
            try:
                await ws.send_text(msg_str)
            except Exception:
                dead_sockets.add(ws)
        active_websockets[job_id].difference_update(dead_sockets)


@router.websocket("/ws/{job_id}")
async def websocket_progress_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    if job_id not in active_websockets:
        active_websockets[job_id] = set()
    active_websockets[job_id].add(websocket)

    # Send current progress if available
    if job_id in current_progress:
        await websocket.send_text(current_progress[job_id].model_dump_json())

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if job_id in active_websockets:
            active_websockets[job_id].discard(websocket)


@router.get("/progress/{job_id}", response_model=Optional[AnalysisProgress])
def get_job_progress(job_id: str):
    return current_progress.get(job_id)


@router.get("/history")
def get_history():
    """Returns analysis history of all completed batches."""
    return list_analysis_history()


@router.get("/weights", response_model=ScoringWeights)
def get_weights():
    w_data = get_setting("scoring_weights")
    if w_data:
        return ScoringWeights(**w_data)
    return ScoringWeights()


@router.post("/weights", response_model=ScoringWeights)
def update_weights(weights: ScoringWeights):
    save_setting("scoring_weights", weights.model_dump())
    return weights


@router.get("/latest")
def get_latest_results(
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """
    Returns analysis results. If job_id or session_id is provided, returns that specific run.
    """
    run = get_latest_analysis_run(job_id=job_id, session_id=session_id)
    if not run:
        raise HTTPException(status_code=404, detail="No analysis run found")
    return run


@router.get("/pairs")
def query_pairs(
    risk: Optional[str] = None,
    language: Optional[str] = None,
    student: Optional[str] = None,
    search: Optional[str] = None,
    min_similarity: float = 0.0,
    sort_by: str = "similarity_desc",
    page: int = 1,
    page_size: int = 25,
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    run = get_latest_analysis_run(job_id=job_id, session_id=session_id)
    if not run:
        return {"total": 0, "page": page, "page_size": page_size, "pairs": []}

    pairs: List[PairComparisonResult] = run["top_suspicious_pairs"]

    # Filter
    if risk and risk != "all":
        pairs = [p for p in pairs if p.risk_level.value == risk]
    if language and language != "all":
        pairs = [p for p in pairs if p.language.value == language]
    if student:
        s_lower = student.lower()
        pairs = [
            p for p in pairs
            if s_lower in p.submission_a_student.lower() or s_lower in p.submission_b_student.lower()
        ]
    if search:
        s_term = search.lower()
        pairs = [
            p for p in pairs
            if s_term in p.submission_a_name.lower()
            or s_term in p.submission_b_name.lower()
            or s_term in p.submission_a_student.lower()
            or s_term in p.submission_b_student.lower()
            or s_term in p.summary.lower()
        ]
    if min_similarity > 0:
        pairs = [p for p in pairs if p.overall_similarity >= min_similarity]

    # Sort
    if sort_by == "similarity_desc":
        pairs.sort(key=lambda p: p.overall_similarity, reverse=True)
    elif sort_by == "similarity_asc":
        pairs.sort(key=lambda p: p.overall_similarity)
    elif sort_by == "ast_desc":
        pairs.sort(key=lambda p: p.ast_score, reverse=True)
    elif sort_by == "cfg_desc":
        pairs.sort(key=lambda p: p.cfg_score, reverse=True)

    total_matched = len(pairs)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated = pairs[start_idx:end_idx]

    return {
        "total": total_matched,
        "page": page,
        "page_size": page_size,
        "pairs": [p.model_dump() for p in paginated],
    }


def _run_analysis_sync(job_id: str, session_id: Optional[str], loop: Optional[asyncio.AbstractEventLoop]):
    # Fetch submissions specifically for this session (or all if not specified)
    submissions = list_submissions(session_id=session_id)
    full_subs = []
    for s in submissions:
        sub_full = get_submission(s.id)
        if sub_full:
            full_subs.append(sub_full)

    w_data = get_setting("scoring_weights")
    weights = ScoringWeights(**w_data) if w_data else ScoringWeights()

    if session_id:
        update_session(session_id=session_id, status=UploadSessionStatus.PROCESSING, job_id=job_id)

    def sync_progress_callback(prog: AnalysisProgress):
        prog.session_id = session_id
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_progress(job_id, prog), loop)
        else:
            current_progress[job_id] = prog

    try:
        pipeline = PlagiarismPipeline()
        result = pipeline.run(
            job_id=job_id,
            submissions=full_subs,
            weights=weights,
            progress_callback=sync_progress_callback,
        )

        # Save to database independently with session_id
        save_analysis_run(
            job_id=job_id,
            status="completed",
            total_submissions=result.total_submissions,
            total_pairs=result.total_pairs_evaluated,
            suspicious_pairs=result.suspicious_pairs_count,
            high_risk=result.high_risk_count,
            medium_risk=result.medium_risk_count,
            low_risk=result.low_risk_count,
            processing_time_seconds=result.processing_time_seconds,
            language_distribution=result.language_distribution,
            weights=result.scoring_weights_used,
            results=result.top_suspicious_pairs,
            session_id=session_id,
        )

        if session_id:
            update_session(session_id=session_id, status=UploadSessionStatus.COMPLETED, job_id=job_id)
    except Exception as exc:
        if session_id:
            update_session(session_id=session_id, status=UploadSessionStatus.FAILED, job_id=job_id)
        raise exc


class StartAnalysisPayload(BaseModel):
    session_id: Optional[str] = None


@router.post("/start")
async def start_analysis(
    background_tasks: BackgroundTasks,
    payload: Optional[StartAnalysisPayload] = None,
    session_id: Optional[str] = None,
):
    target_session_id = (payload.session_id if payload else None) or session_id
    if not target_session_id:
        active = get_or_create_active_session()
        target_session_id = active.session_id

    subs = list_submissions(session_id=target_session_id)

    # If active session has 0 submissions, check if there are submissions overall
    if len(subs) < 2:
        all_subs = list_submissions()
        if len(all_subs) >= 2 and len(subs) == 0:
            subs = all_subs
            target_session_id = None
        else:
            raise HTTPException(
                status_code=400,
                detail=f"At least 2 submissions are required to run plagiarism detection (found {len(subs)} in active batch)",
            )

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    loop = asyncio.get_running_loop()

    # Initial progress
    current_progress[job_id] = AnalysisProgress(
        job_id=job_id,
        current_stage="Initializing",
        stage_index=0,
        total_stages=5,
        percent_complete=0.0,
        processed_count=0,
        total_count=len(subs),
        pairs_evaluated=0,
        candidate_pairs_found=0,
        message="Starting plagiarism analysis pipeline...",
        elapsed_seconds=0.0,
        session_id=target_session_id,
    )

    background_tasks.add_task(_run_analysis_sync, job_id, target_session_id, loop)

    return {
        "job_id": job_id,
        "session_id": target_session_id,
        "status": "started",
        "submission_count": len(subs),
    }
