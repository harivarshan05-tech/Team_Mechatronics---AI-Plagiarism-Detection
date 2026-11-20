"""
Fine-Grained Matcher for Side-by-Side Code Comparison.
Maps matching spans between Submission A and Submission B, classifying:
- EXACT_STRUCTURE
- RENAMED_IDENTIFIERS
- CONTROL_FLOW
- LOOP_TO_RECURSION
- REORDERED_LOGIC
"""

import uuid
import re
from typing import List, Dict, Set, Tuple
from app.models import MatchSpan, MatchType, Language
from app.engine.stage_preprocess import preprocess_code
from app.engine.stage_ast import ASTAnalysisResult
from app.engine.stage_cfg import CFGAnalysisResult


def find_matching_spans(
    source_a: str,
    source_b: str,
    language: Language,
    ast_a: ASTAnalysisResult,
    ast_b: ASTAnalysisResult,
    cfg_a: CFGAnalysisResult,
    cfg_b: CFGAnalysisResult,
    has_l2r: bool,
    has_reordered: bool,
) -> List[MatchSpan]:
    spans: List[MatchSpan] = []
    lines_a = source_a.splitlines()
    lines_b = source_b.splitlines()

    # Preprocess both sources
    prep_a = preprocess_code(source_a, language)
    prep_b = preprocess_code(source_b, language)

    # 1. Check for Loop-to-Recursion Span
    if has_l2r:
        loop_line_a = -1
        for i, l in enumerate(lines_a, start=1):
            if re.search(r'\b(for|while)\b', l):
                loop_line_a = i
                break

        rec_line_b = -1
        for i, l in enumerate(lines_b, start=1):
            if re.search(r'\b(return\s+\w+\s*\(|def\s+\w+|public\s+.*\w+\s*\()', l):
                rec_line_b = i
                break

        if loop_line_a != -1 and rec_line_b != -1:
            spans.append(
                MatchSpan(
                    span_id=str(uuid.uuid4())[:8],
                    match_type=MatchType.LOOP_TO_RECURSION,
                    sub_a_start_line=loop_line_a,
                    sub_a_end_line=min(loop_line_a + 6, len(lines_a)),
                    sub_b_start_line=rec_line_b,
                    sub_b_end_line=min(rec_line_b + 6, len(lines_b)),
                    description="Loop construct in Submission A mapped to equivalent recursive structure in Submission B",
                    confidence=0.92,
                )
            )

    # 2. Check for Function Level / Reordered Matches
    for fa in ast_a.functions:
        for fb in ast_b.functions:
            # Check body similarity
            set_a = set(fa.body_types)
            set_b = set(fb.body_types)
            inter = len(set_a.intersection(set_b))
            union = len(set_a.union(set_b))
            sim = inter / union if union > 0 else 0.0

            if sim >= 0.75 or fa.tree_hash == fb.tree_hash:
                m_type = MatchType.REORDERED_LOGIC if (has_reordered and fa.name != fb.name) else (
                    MatchType.EXACT_STRUCTURE if sim >= 0.95 else MatchType.RENAMED_IDENTIFIERS
                )
                desc = (
                    f"Reordered function logic '{fa.name}' corresponds to '{fb.name}'"
                    if m_type == MatchType.REORDERED_LOGIC
                    else (
                        f"Matching function implementation ({fa.name} ~ {fb.name})"
                        if fa.name != fb.name
                        else f"Identical function structure '{fa.name}'"
                    )
                )
                spans.append(
                    MatchSpan(
                        span_id=str(uuid.uuid4())[:8],
                        match_type=m_type,
                        sub_a_start_line=fa.line_start,
                        sub_a_end_line=fa.line_end,
                        sub_b_start_line=fb.line_start,
                        sub_b_end_line=fb.line_end,
                        description=desc,
                        confidence=round(sim, 2),
                    )
                )

    # 3. Line-by-line normalized statement matching
    # Map normalized lines
    norm_lines_a = [preprocess_code(l, language).clean_code for l in lines_a]
    norm_lines_b = [preprocess_code(l, language).clean_code for l in lines_b]

    matched_b_lines = set()
    for idx_a, nl_a in enumerate(norm_lines_a, start=1):
        if not nl_a or len(nl_a) < 5:
            continue
        for idx_b, nl_b in enumerate(norm_lines_b, start=1):
            if idx_b in matched_b_lines or not nl_b or len(nl_b) < 5:
                continue

            # Exact normalized line match
            if nl_a == nl_b:
                matched_b_lines.add(idx_b)
                raw_a = lines_a[idx_a - 1].strip()
                raw_b = lines_b[idx_b - 1].strip()

                is_control = any(k in raw_a for k in ("if", "for", "while", "else", "switch"))
                is_renamed = raw_a != raw_b

                mtype = MatchType.CONTROL_FLOW if is_control else (
                    MatchType.RENAMED_IDENTIFIERS if is_renamed else MatchType.EXACT_STRUCTURE
                )

                # Avoid duplicate spans if already covered in function spans
                already_covered = any(
                    s.sub_a_start_line <= idx_a <= s.sub_a_end_line and
                    s.sub_b_start_line <= idx_b <= s.sub_b_end_line
                    for s in spans
                )
                if not already_covered:
                    spans.append(
                        MatchSpan(
                            span_id=str(uuid.uuid4())[:8],
                            match_type=mtype,
                            sub_a_start_line=idx_a,
                            sub_a_end_line=idx_a,
                            sub_b_start_line=idx_b,
                            sub_b_end_line=idx_b,
                            description=f"Matching statement (line {idx_a} to {idx_b})",
                            confidence=0.88,
                        )
                    )
                break

    # Sort spans by line number in Submission A
    spans.sort(key=lambda s: s.sub_a_start_line)
    return spans
