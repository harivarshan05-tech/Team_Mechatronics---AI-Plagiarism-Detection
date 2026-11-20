"""
Comparison API Router:
Detailed side-by-side comparison payload for Monaco Editor diffing and match highlights.
"""

from fastapi import APIRouter, HTTPException
from app.database import get_pair_result, get_submission
from app.models import PairComparisonResult

router = APIRouter(prefix="/api/comparison", tags=["Comparison"])


@router.get("/{pair_id}")
def get_comparison_detail(pair_id: str):
    pair = get_pair_result(pair_id)
    if not pair:
        raise HTTPException(status_code=404, detail="Comparison pair not found")

    sub_a = get_submission(pair.submission_a_id)
    sub_b = get_submission(pair.submission_b_id)

    if not sub_a or not sub_b:
        raise HTTPException(status_code=404, detail="One or both submissions no longer exist")

    return {
        "pair_id": pair.pair_id,
        "submission_a": {
            "id": sub_a.id,
            "filename": sub_a.filename,
            "student_id": sub_a.student_id,
            "language": sub_a.language,
            "content": sub_a.content,
            "line_count": sub_a.line_count,
        },
        "submission_b": {
            "id": sub_b.id,
            "filename": sub_b.filename,
            "student_id": sub_b.student_id,
            "language": sub_b.language,
            "content": sub_b.content,
            "line_count": sub_b.line_count,
        },
        "overall_similarity": pair.overall_similarity,
        "risk_level": pair.risk_level,
        "scores": {
            "ast_structural": pair.ast_score,
            "control_flow": pair.cfg_score,
            "structural_fingerprint": pair.fingerprint_score,
            "token_similarity": pair.token_score,
            "function_similarity": pair.function_score,
        },
        "transformations": {
            "renamed_identifiers": pair.has_renamed_identifiers,
            "reordered_functions": pair.has_reordered_functions,
            "loop_to_recursion": pair.has_loop_to_recursion,
            "modified_conditionals": pair.has_modified_conditionals,
        },
        "matching_spans": [s.model_dump() for s in pair.matching_spans],
        "summary": pair.summary,
    }
