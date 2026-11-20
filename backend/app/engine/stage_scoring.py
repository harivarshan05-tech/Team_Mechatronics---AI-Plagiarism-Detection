"""
Stage 5: Similarity Scoring Engine.
- Multi-dimensional weighted composite score (AST, CFG, Fingerprints, Tokens, Functions)
- Dynamic and configurable weights
- Risk categorization (High >= 75%, Medium 45-74%, Low < 45%)
- Qualitative plagiarism transformation flags
- Explanatory textual summaries
"""

from typing import Dict, Any, Tuple
from app.models import RiskLevel, ScoringWeights
from app.config import HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD


def classify_risk(similarity: float) -> RiskLevel:
    if similarity >= HIGH_RISK_THRESHOLD:
        return RiskLevel.HIGH
    elif similarity >= MEDIUM_RISK_THRESHOLD:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def calculate_composite_score(
    ast_sim: float,           # 0.0 to 1.0
    cfg_sim: float,           # 0.0 to 1.0
    fingerprint_sim: float,   # 0.0 to 1.0
    token_sim: float,         # 0.0 to 1.0
    function_sim: float,      # 0.0 to 1.0
    weights: ScoringWeights,
) -> float:
    """
    Computes normalized similarity score (0.0 to 100.0).
    """
    w = weights.normalized()
    raw = (
        w.ast_structural * ast_sim
        + w.control_flow * cfg_sim
        + w.structural_fingerprint * fingerprint_sim
        + w.token_similarity * token_sim
        + w.function_similarity * function_sim
    )
    score = max(0.0, min(1.0, raw)) * 100.0
    return round(score, 1)


def generate_plagiarism_summary(
    overall_sim: float,
    has_renamed_ids: bool,
    has_reordered_funcs: bool,
    has_loop_to_rec: bool,
    ast_score: float,
    cfg_score: float,
    token_score: float,
) -> str:
    points = []
    if has_loop_to_rec:
        points.append("Equivalent algorithm detected via loop-to-recursion transformation")
    if has_renamed_ids and ast_score > 70.0 and token_score < ast_score - 10.0:
        points.append("Identical structural logic disguised with renamed variables and functions")
    if has_reordered_funcs:
        points.append("Functions have been reordered to alter syntactic appearance")
    if ast_score >= 85.0:
        points.append("High degree of Abstract Syntax Tree subtree isomorphism")
    if cfg_score >= 85.0 and not has_loop_to_rec:
        points.append("Near-identical control flow branching and cyclomatic complexity")

    if not points:
        if overall_sim >= 75.0:
            return "Strong structural and logical similarity detected across submissions."
        elif overall_sim >= 45.0:
            return "Moderate structural overlap detected; possible code sharing or common boilerplate."
        return "Low structural similarity; submissions appear independently authored."

    return "; ".join(points) + "."
