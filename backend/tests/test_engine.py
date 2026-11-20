"""
Automated tests for all 6 required plagiarism benchmark scenarios:
1. Two identical code files
2. Two files with renamed variables
3. Two files with reordered functions
4. A loop converted into recursion
5. Two logically similar but differently implemented solutions
6. Two completely unrelated solutions
"""

import pytest
from app.models import Language, ScoringWeights, RiskLevel
from app.engine.language_detector import detect_language
from app.engine.stage_preprocess import preprocess_code
from app.engine.stage_ast import parse_ast, compute_ast_similarity
from app.engine.stage_cfg import analyze_control_flow, compute_cfg_similarity
from app.engine.stage_fingerprint import generate_fingerprints, compute_minhash_similarity
from app.sample_data import get_sample_submissions
from app.engine.pipeline import PlagiarismPipeline
from app.models import SubmissionMeta


@pytest.fixture
def sample_dict():
    samples = get_sample_submissions()
    return {s["id"]: s for s in samples}


def test_language_detection():
    assert detect_language("sort.py", "def my_func(): pass") == Language.PYTHON
    assert detect_language("main.cpp", "#include <iostream>\nint main() {}") == Language.CPP
    assert detect_language("Tree.java", "public class Tree { public static void main() {} }") == Language.JAVA
    assert detect_language("unknown_script", "def run():\n    print('hello')") == Language.PYTHON


def test_scenario_1_identical_files(sample_dict):
    """Scenario 1: Two identical code files should have ~100% similarity."""
    sub1 = sample_dict["sub_py_01"]
    sub2 = sample_dict["sub_py_02"]

    subs = [
        SubmissionMeta(
            id=sub1["id"], filename=sub1["filename"], student_id=sub1["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub1["content"]),
            line_count=len(sub1["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub1["content"]
        ),
        SubmissionMeta(
            id=sub2["id"], filename=sub2["filename"], student_id=sub2["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub2["content"]),
            line_count=len(sub2["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub2["content"]
        )
    ]

    pipeline = PlagiarismPipeline()
    result = pipeline.run("test_job_1", subs)

    assert len(result.top_suspicious_pairs) >= 1
    pair = result.top_suspicious_pairs[0]
    assert pair.overall_similarity >= 95.0
    assert pair.risk_level == RiskLevel.HIGH


def test_scenario_2_renamed_variables(sample_dict):
    """Scenario 2: Renamed variables and functions should still yield high AST structural similarity."""
    sub1 = sample_dict["sub_py_01"]
    sub3 = sample_dict["sub_py_03"]  # AI renamed quicksort

    subs = [
        SubmissionMeta(
            id=sub1["id"], filename=sub1["filename"], student_id=sub1["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub1["content"]),
            line_count=len(sub1["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub1["content"]
        ),
        SubmissionMeta(
            id=sub3["id"], filename=sub3["filename"], student_id=sub3["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub3["content"]),
            line_count=len(sub3["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub3["content"]
        )
    ]

    pipeline = PlagiarismPipeline()
    result = pipeline.run("test_job_2", subs)

    pair = result.top_suspicious_pairs[0]
    assert pair.ast_score >= 80.0
    assert pair.has_renamed_identifiers is True
    assert pair.risk_level in (RiskLevel.HIGH, RiskLevel.MEDIUM)


def test_scenario_3_reordered_functions(sample_dict):
    """Scenario 3: Two files with reordered functions should be recognized as matching."""
    sub4 = sample_dict["sub_py_04"]
    sub5 = sample_dict["sub_py_05"]

    subs = [
        SubmissionMeta(
            id=sub4["id"], filename=sub4["filename"], student_id=sub4["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub4["content"]),
            line_count=len(sub4["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub4["content"]
        ),
        SubmissionMeta(
            id=sub5["id"], filename=sub5["filename"], student_id=sub5["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub5["content"]),
            line_count=len(sub5["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub5["content"]
        )
    ]

    pipeline = PlagiarismPipeline()
    result = pipeline.run("test_job_3", subs)

    pair = result.top_suspicious_pairs[0]
    assert pair.has_reordered_functions is True
    assert pair.function_score >= 80.0
    assert pair.overall_similarity >= 70.0


def test_scenario_4_loop_to_recursion(sample_dict):
    """Scenario 4: Loop converted to recursion should be specifically identified."""
    sub6 = sample_dict["sub_py_06"]  # Factorial loop
    sub7 = sample_dict["sub_py_07"]  # Factorial recursion

    subs = [
        SubmissionMeta(
            id=sub6["id"], filename=sub6["filename"], student_id=sub6["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub6["content"]),
            line_count=len(sub6["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub6["content"]
        ),
        SubmissionMeta(
            id=sub7["id"], filename=sub7["filename"], student_id=sub7["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub7["content"]),
            line_count=len(sub7["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub7["content"]
        )
    ]

    pipeline = PlagiarismPipeline()
    result = pipeline.run("test_job_4", subs)

    pair = result.top_suspicious_pairs[0]
    assert pair.has_loop_to_recursion is True
    assert pair.cfg_score >= 80.0
    # Confirms loop-to-recursion match span is generated
    l2r_spans = [s for s in pair.matching_spans if s.match_type.value == "loop_to_recursion"]
    assert len(l2r_spans) >= 1


def test_scenario_5_logically_similar_different_impl(sample_dict):
    """Scenario 5: Two logically similar solutions (binary search variants) should have moderate similarity."""
    sub8 = sample_dict["sub_py_08"]
    sub9 = sample_dict["sub_py_09"]

    subs = [
        SubmissionMeta(
            id=sub8["id"], filename=sub8["filename"], student_id=sub8["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub8["content"]),
            line_count=len(sub8["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub8["content"]
        ),
        SubmissionMeta(
            id=sub9["id"], filename=sub9["filename"], student_id=sub9["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub9["content"]),
            line_count=len(sub9["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub9["content"]
        )
    ]

    pipeline = PlagiarismPipeline()
    result = pipeline.run("test_job_5", subs)

    pair = result.top_suspicious_pairs[0]
    # Algorithmic overlap without exact duplicate
    assert pair.overall_similarity >= 40.0


def test_scenario_6_unrelated_solutions(sample_dict):
    """Scenario 6: Matrix multiply and web text parser should have very low similarity."""
    sub10 = sample_dict["sub_py_10"]
    sub11 = sample_dict["sub_py_11"]

    subs = [
        SubmissionMeta(
            id=sub10["id"], filename=sub10["filename"], student_id=sub10["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub10["content"]),
            line_count=len(sub10["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub10["content"]
        ),
        SubmissionMeta(
            id=sub11["id"], filename=sub11["filename"], student_id=sub11["student_id"],
            language=Language.PYTHON, file_size_bytes=len(sub11["content"]),
            line_count=len(sub11["content"].splitlines()), created_at="2026-11-20T00:00:00",
            content=sub11["content"]
        )
    ]

    pipeline = PlagiarismPipeline()
    result = pipeline.run("test_job_6", subs)

    if result.top_suspicious_pairs:
        pair = result.top_suspicious_pairs[0]
        assert pair.overall_similarity < 30.0
        assert pair.risk_level == RiskLevel.LOW
