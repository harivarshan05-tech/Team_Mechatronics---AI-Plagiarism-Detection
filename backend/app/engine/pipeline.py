"""
Extensible Multi-Stage Similarity Detection Pipeline.
Designed for modular extension to support hour-12 mid-event requirements.
Emits real-time progress callbacks for WebSocket / SSE streaming.
"""

import time
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Set, Optional, Callable, Any

from app.models import (
    AnalysisProgress,
    AnalysisRunResult,
    PairComparisonResult,
    RiskLevel,
    ScoringWeights,
    SubmissionMeta,
    MatchType,
)
from app.engine.stage_preprocess import preprocess_code, PreprocessResult
from app.engine.stage_ast import parse_ast, compute_ast_similarity, ASTAnalysisResult
from app.engine.stage_cfg import analyze_control_flow, compute_cfg_similarity, CFGAnalysisResult
from app.engine.stage_fingerprint import (
    generate_fingerprints,
    compute_minhash_similarity,
    compute_winnowing_similarity,
    LSHIndex,
    StructuralFingerprint,
)
from app.engine.stage_scoring import (
    calculate_composite_score,
    classify_risk,
    generate_plagiarism_summary,
)
from app.engine.matcher import find_matching_spans


class PipelineContext:
    """Shared execution context passing data between pipeline stages."""

    def __init__(
        self,
        job_id: str,
        submissions: List[SubmissionMeta],
        weights: ScoringWeights,
        progress_callback: Optional[Callable[[AnalysisProgress], None]] = None,
    ):
        self.job_id = job_id
        self.submissions = submissions
        self.weights = weights
        self.progress_callback = progress_callback
        self.start_time = time.time()

        # Intermediate artifacts keyed by submission ID
        self.preprocessed: Dict[str, PreprocessResult] = {}
        self.ast_results: Dict[str, ASTAnalysisResult] = {}
        self.cfg_results: Dict[str, CFGAnalysisResult] = {}
        self.fingerprints: Dict[str, StructuralFingerprint] = {}
        self.candidate_pairs: Set[Tuple[str, str]] = set()

        # Output results
        self.pair_results: List[PairComparisonResult] = []
        self.custom_stage_data: Dict[str, Any] = {}


class BasePipelineStage(ABC):
    """Abstract base class for all pipeline stages. Allows plug-and-play extensions."""

    @property
    @abstractmethod
    def stage_name(self) -> str:
        pass

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> None:
        pass


class PreprocessingStage(BasePipelineStage):
    @property
    def stage_name(self) -> str:
        return "Code Preprocessing & Token Normalization"

    def execute(self, ctx: PipelineContext) -> None:
        total = len(ctx.submissions)
        for idx, sub in enumerate(ctx.submissions, start=1):
            content = sub.content or ""
            res = preprocess_code(content, sub.language)
            ctx.preprocessed[sub.id] = res

            if ctx.progress_callback and (idx % 20 == 0 or idx == total):
                ctx.progress_callback(
                    AnalysisProgress(
                        job_id=ctx.job_id,
                        current_stage=self.stage_name,
                        stage_index=1,
                        total_stages=5,
                        percent_complete=round((idx / total) * 20.0, 1),
                        processed_count=idx,
                        total_count=total,
                        pairs_evaluated=0,
                        candidate_pairs_found=0,
                        message=f"Preprocessed {idx}/{total} submissions",
                        elapsed_seconds=round(time.time() - ctx.start_time, 2),
                    )
                )


class ASTAnalysisStage(BasePipelineStage):
    @property
    def stage_name(self) -> str:
        return "Abstract Syntax Tree (AST) Parsing"

    def execute(self, ctx: PipelineContext) -> None:
        total = len(ctx.submissions)
        for idx, sub in enumerate(ctx.submissions, start=1):
            content = sub.content or ""
            res = parse_ast(content, sub.language)
            ctx.ast_results[sub.id] = res

            if ctx.progress_callback and (idx % 20 == 0 or idx == total):
                ctx.progress_callback(
                    AnalysisProgress(
                        job_id=ctx.job_id,
                        current_stage=self.stage_name,
                        stage_index=2,
                        total_stages=5,
                        percent_complete=20.0 + round((idx / total) * 20.0, 1),
                        processed_count=idx,
                        total_count=total,
                        pairs_evaluated=0,
                        candidate_pairs_found=0,
                        message=f"Parsed ASTs for {idx}/{total} submissions",
                        elapsed_seconds=round(time.time() - ctx.start_time, 2),
                    )
                )


class ControlFlowStage(BasePipelineStage):
    @property
    def stage_name(self) -> str:
        return "Control Flow & Recursion Analysis"

    def execute(self, ctx: PipelineContext) -> None:
        total = len(ctx.submissions)
        for idx, sub in enumerate(ctx.submissions, start=1):
            content = sub.content or ""
            res = analyze_control_flow(content, sub.language)
            ctx.cfg_results[sub.id] = res

            if ctx.progress_callback and (idx % 20 == 0 or idx == total):
                ctx.progress_callback(
                    AnalysisProgress(
                        job_id=ctx.job_id,
                        current_stage=self.stage_name,
                        stage_index=3,
                        total_stages=5,
                        percent_complete=40.0 + round((idx / total) * 20.0, 1),
                        processed_count=idx,
                        total_count=total,
                        pairs_evaluated=0,
                        candidate_pairs_found=0,
                        message=f"Constructed CFGs for {idx}/{total} submissions",
                        elapsed_seconds=round(time.time() - ctx.start_time, 2),
                    )
                )


class StructuralFingerprintStage(BasePipelineStage):
    @property
    def stage_name(self) -> str:
        return "Structural Fingerprinting & LSH Candidate Filtering"

    def execute(self, ctx: PipelineContext) -> None:
        total = len(ctx.submissions)
        lsh = LSHIndex(num_bands=16, rows_per_band=4)

        for idx, sub in enumerate(ctx.submissions, start=1):
            prep = ctx.preprocessed.get(sub.id)
            ast_res = ctx.ast_results.get(sub.id)
            norm_tokens = prep.normalized_tokens if prep else []
            node_types = ast_res.node_type_sequence if ast_res else []

            fp = generate_fingerprints(sub.id, norm_tokens, node_types)
            ctx.fingerprints[sub.id] = fp
            lsh.insert(fp)

        # Retrieve candidates via LSH collision
        candidates = lsh.get_candidate_pairs()
        ctx.candidate_pairs = candidates

        if ctx.progress_callback:
            ctx.progress_callback(
                AnalysisProgress(
                    job_id=ctx.job_id,
                    current_stage=self.stage_name,
                    stage_index=4,
                    total_stages=5,
                    percent_complete=80.0,
                    processed_count=total,
                    total_count=total,
                    pairs_evaluated=0,
                    candidate_pairs_found=len(candidates),
                    message=f"Generated fingerprints; filtered {len(candidates)} candidate pairs",
                    elapsed_seconds=round(time.time() - ctx.start_time, 2),
                )
            )


class SimilarityScoringStage(BasePipelineStage):
    @property
    def stage_name(self) -> str:
        return "Multi-Dimensional Similarity Scoring"

    def execute(self, ctx: PipelineContext) -> None:
        subs = ctx.submissions
        n = len(subs)
        sub_map = {s.id: s for s in subs}
        total_possible_pairs = n * (n - 1) // 2

        # Invert candidate lookup
        candidates = ctx.candidate_pairs

        # For smaller runs (<= 40 submissions), evaluate all pairs deeply to ensure zero false negatives.
        # For large runs (> 40 submissions), use LSH candidate filtering + fast MinHash screening.
        evaluate_all_deep = (n <= 40)

        pairs_evaluated = 0
        pair_results: List[PairComparisonResult] = []

        for i in range(n):
            sub_a = subs[i]
            for j in range(i + 1, n):
                sub_b = subs[j]
                pairs_evaluated += 1

                pair_key = (sub_a.id, sub_b.id) if sub_a.id < sub_b.id else (sub_b.id, sub_a.id)
                is_candidate = evaluate_all_deep or (pair_key in candidates)

                fp_a = ctx.fingerprints[sub_a.id]
                fp_b = ctx.fingerprints[sub_b.id]
                minhash_sim = compute_minhash_similarity(fp_a.minhash_signature, fp_b.minhash_signature)
                winnow_sim = compute_winnowing_similarity(fp_a.winnowed_fingerprints, fp_b.winnowed_fingerprints)
                fingerprint_sim = max(minhash_sim, winnow_sim)

                # Skip deep comparison if completely different language or not a candidate and minhash is very low
                if not is_candidate and fingerprint_sim < 0.20:
                    # Low similarity pair, score directly from MinHash to save CPU
                    if fingerprint_sim > 0.05:
                        score = round(fingerprint_sim * 100.0, 1)
                        if score >= 15.0:
                            pair_results.append(
                                PairComparisonResult(
                                    pair_id=f"{sub_a.id}_{sub_b.id}",
                                    submission_a_id=sub_a.id,
                                    submission_a_name=sub_a.filename,
                                    submission_a_student=sub_a.student_id,
                                    submission_b_id=sub_b.id,
                                    submission_b_name=sub_b.filename,
                                    submission_b_student=sub_b.student_id,
                                    language=sub_a.language,
                                    overall_similarity=score,
                                    risk_level=classify_risk(score),
                                    ast_score=round(fingerprint_sim * 100.0, 1),
                                    cfg_score=round(fingerprint_sim * 100.0, 1),
                                    fingerprint_score=round(fingerprint_sim * 100.0, 1),
                                    token_score=round(fingerprint_sim * 100.0, 1),
                                    function_score=round(fingerprint_sim * 100.0, 1),
                                    summary="Low structural similarity.",
                                )
                            )
                    continue

                # Deep evaluation for candidate pairs or identical language pairs
                prep_a = ctx.preprocessed[sub_a.id]
                prep_b = ctx.preprocessed[sub_b.id]
                ast_a = ctx.ast_results[sub_a.id]
                ast_b = ctx.ast_results[sub_b.id]
                cfg_a = ctx.cfg_results[sub_a.id]
                cfg_b = ctx.cfg_results[sub_b.id]

                # 1. AST Similarity
                ast_sim, func_sim, has_reordered = compute_ast_similarity(ast_a, ast_b)

                # 2. CFG Similarity
                cfg_sim, has_l2r = compute_cfg_similarity(
                    cfg_a, cfg_b, prep_a.clean_code, prep_b.clean_code
                )

                # 3. Token Jaccard Similarity
                token_inter = len(prep_a.token_ngrams.intersection(prep_b.token_ngrams))
                token_union = len(prep_a.token_ngrams.union(prep_b.token_ngrams))
                token_sim = token_inter / token_union if token_union > 0 else 0.0

                # 4. Qualitative checks
                has_renamed = (
                    ast_sim >= 0.70 and token_sim < (ast_sim - 0.15)
                ) or len(prep_a.identifier_map) > 2

                # 5. Composite score
                overall_score = calculate_composite_score(
                    ast_sim=ast_sim,
                    cfg_sim=cfg_sim,
                    fingerprint_sim=fingerprint_sim,
                    token_sim=token_sim,
                    function_sim=func_sim,
                    weights=ctx.weights,
                )

                risk = classify_risk(overall_score)

                # Generate matching spans for side-by-side comparison
                spans = find_matching_spans(
                    source_a=sub_a.content or "",
                    source_b=sub_b.content or "",
                    language=sub_a.language,
                    ast_a=ast_a,
                    ast_b=ast_b,
                    cfg_a=cfg_a,
                    cfg_b=cfg_b,
                    has_l2r=has_l2r,
                    has_reordered=has_reordered,
                )

                summary = generate_plagiarism_summary(
                    overall_sim=overall_score,
                    has_renamed_ids=has_renamed,
                    has_reordered_funcs=has_reordered,
                    has_loop_to_rec=has_l2r,
                    ast_score=round(ast_sim * 100.0, 1),
                    cfg_score=round(cfg_sim * 100.0, 1),
                    token_score=round(token_sim * 100.0, 1),
                )

                pair_results.append(
                    PairComparisonResult(
                        pair_id=f"{sub_a.id}_{sub_b.id}",
                        submission_a_id=sub_a.id,
                        submission_a_name=sub_a.filename,
                        submission_a_student=sub_a.student_id,
                        submission_b_id=sub_b.id,
                        submission_b_name=sub_b.filename,
                        submission_b_student=sub_b.student_id,
                        language=sub_a.language,
                        overall_similarity=overall_score,
                        risk_level=risk,
                        ast_score=round(ast_sim * 100.0, 1),
                        cfg_score=round(cfg_sim * 100.0, 1),
                        fingerprint_score=round(fingerprint_sim * 100.0, 1),
                        token_score=round(token_sim * 100.0, 1),
                        function_score=round(func_sim * 100.0, 1),
                        has_renamed_identifiers=has_renamed,
                        has_reordered_functions=has_reordered,
                        has_loop_to_recursion=has_l2r,
                        has_modified_conditionals=abs(cfg_a.total_branches - cfg_b.total_branches) > 0,
                        matching_spans=spans,
                        summary=summary,
                    )
                )

            if ctx.progress_callback and (pairs_evaluated % 500 == 0 or pairs_evaluated == total_possible_pairs):
                pct = 80.0 + min(20.0, (pairs_evaluated / max(1, total_possible_pairs)) * 20.0)
                ctx.progress_callback(
                    AnalysisProgress(
                        job_id=ctx.job_id,
                        current_stage=self.stage_name,
                        stage_index=5,
                        total_stages=5,
                        percent_complete=round(pct, 1),
                        processed_count=len(subs),
                        total_count=len(subs),
                        pairs_evaluated=pairs_evaluated,
                        candidate_pairs_found=len(candidates),
                        message=f"Scored {pairs_evaluated}/{total_possible_pairs} pairs",
                        elapsed_seconds=round(time.time() - ctx.start_time, 2),
                    )
                )

        # Sort pairs from highest to lowest similarity
        pair_results.sort(key=lambda p: p.overall_similarity, reverse=True)
        ctx.pair_results = pair_results


class PlagiarismPipeline:
    """
    Main Pipeline Runner. Manages execution of registered stages.
    """

    def __init__(self):
        self.stages: List[BasePipelineStage] = [
            PreprocessingStage(),
            ASTAnalysisStage(),
            ControlFlowStage(),
            StructuralFingerprintStage(),
            SimilarityScoringStage(),
        ]

    def register_stage(self, stage: BasePipelineStage, position: Optional[int] = None):
        """Allows dynamic injection of new stages for mid-event requirements."""
        if position is not None:
            self.stages.insert(position, stage)
        else:
            self.stages.append(stage)

    def run(
        self,
        job_id: str,
        submissions: List[SubmissionMeta],
        weights: Optional[ScoringWeights] = None,
        progress_callback: Optional[Callable[[AnalysisProgress], None]] = None,
    ) -> AnalysisRunResult:
        if weights is None:
            weights = ScoringWeights()

        ctx = PipelineContext(
            job_id=job_id,
            submissions=submissions,
            weights=weights,
            progress_callback=progress_callback,
        )

        for stage in self.stages:
            stage.execute(ctx)

        total_time = round(time.time() - ctx.start_time, 2)

        # Calculate high/med/low counts
        high_c = sum(1 for p in ctx.pair_results if p.risk_level == RiskLevel.HIGH)
        med_c = sum(1 for p in ctx.pair_results if p.risk_level == RiskLevel.MEDIUM)
        low_c = sum(1 for p in ctx.pair_results if p.risk_level == RiskLevel.LOW)
        suspicious_c = high_c + med_c

        # Language distribution
        lang_dist: Dict[str, int] = {}
        for s in submissions:
            lang_dist[s.language.value] = lang_dist.get(s.language.value, 0) + 1

        total_pairs = len(submissions) * (len(submissions) - 1) // 2

        if progress_callback:
            progress_callback(
                AnalysisProgress(
                    job_id=job_id,
                    current_stage="Complete",
                    stage_index=5,
                    total_stages=5,
                    percent_complete=100.0,
                    processed_count=len(submissions),
                    total_count=len(submissions),
                    pairs_evaluated=total_pairs,
                    candidate_pairs_found=len(ctx.candidate_pairs),
                    message=f"Analysis completed in {total_time}s",
                    elapsed_seconds=total_time,
                )
            )

        return AnalysisRunResult(
            job_id=job_id,
            status="completed",
            total_submissions=len(submissions),
            total_pairs_evaluated=total_pairs,
            suspicious_pairs_count=suspicious_c,
            high_risk_count=high_c,
            medium_risk_count=med_c,
            low_risk_count=low_c,
            processing_time_seconds=total_time,
            language_distribution=lang_dist,
            top_suspicious_pairs=ctx.pair_results,
            scoring_weights_used=weights,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        )
