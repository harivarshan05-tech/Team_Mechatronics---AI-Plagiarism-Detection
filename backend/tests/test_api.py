"""
Comprehensive integration tests for FastAPI API route handlers:
- Submissions (load samples, list, detail, upload handling, delete)
- Multi-batch upload session management & preservation
- Analysis (start, latest results, pair query filtering, scoring weights, history)
- Comparison (side-by-side payload with match spans)
- Reports (JSON, CSV, and HTML export generation)
"""

import pytest
from app.database import (
    init_db,
    delete_all_submissions,
    create_session,
    list_sessions,
    list_submissions,
    save_submission,
    list_analysis_history,
)
from app.api.submissions import (
    load_sample_datasets,
    get_all_submissions,
    get_single_submission,
    clear_all_submissions,
)
from app.api.analysis import (
    _run_analysis_sync,
    get_latest_results,
    query_pairs,
    get_weights,
    update_weights,
    get_history,
)
from app.api.comparison import get_comparison_detail
from app.api.reports import export_json_report, export_csv_report, export_html_report
from app.models import ScoringWeights, RiskLevel, Language


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    delete_all_submissions()
    yield
    delete_all_submissions()


def test_submissions_sample_loading_and_list():
    res = load_sample_datasets()
    assert res["loaded_count"] >= 10

    subs = get_all_submissions()
    assert len(subs) >= 10
    assert any(s.student_id == "alice_smith" for s in subs)


def test_submission_detail():
    load_sample_datasets()
    subs = get_all_submissions()
    target_id = subs[0].id

    detail = get_single_submission(target_id)
    assert detail["submission"].id == target_id
    assert "ast_summary" in detail
    assert "cfg_summary" in detail
    assert detail["ast_summary"]["total_nodes"] > 0


def test_full_analysis_workflow_and_filtering():
    # 1. Load samples
    res = load_sample_datasets()
    session_id = res["session_id"]

    # 2. Run analysis synchronously
    job_id = "test_run_job_123"
    _run_analysis_sync(job_id, session_id, None)

    # 3. Retrieve latest analysis run
    latest = get_latest_results(session_id=session_id)
    assert latest["job_id"] == job_id
    assert latest["total_submissions"] >= 10
    assert latest["suspicious_pairs_count"] >= 1
    assert latest["high_risk_count"] >= 1

    # 4. Query pairs with filtering
    all_pairs = query_pairs(risk="all", session_id=session_id)
    assert all_pairs["total"] >= 1

    high_pairs = query_pairs(risk="high", session_id=session_id)
    assert high_pairs["total"] >= 1
    for p in high_pairs["pairs"]:
        assert p["risk_level"] == "high"
        assert p["overall_similarity"] >= 75.0

    # 5. Query pairs with text search
    searched = query_pairs(search="quicksort", session_id=session_id)
    assert searched["total"] >= 1


def test_multiple_upload_sessions_and_preservation():
    """
    Validates Requirement 2, 5, 6, 8:
    Uploading Batch 1, scanning Batch 1, uploading Batch 2, scanning Batch 2.
    Ensures Batch 1 is NOT deleted, overwritten, or mixed with Batch 2!
    """
    # 1. Upload Batch 1
    sess1 = create_session("Batch 1 - Sorting Algorithms")
    save_submission(
        "b1_1", "bubble.py", "student1", Language.PYTHON,
        "def sort(a):\n    for i in range(len(a)):\n        for j in range(len(a)-1):\n            if a[j] > a[j+1]:\n                a[j], a[j+1] = a[j+1], a[j]\n    return a\n",
        sess1.session_id,
    )
    save_submission(
        "b1_2", "bubble_copy.py", "student2", Language.PYTHON,
        "def sort(arr):\n    for i in range(len(arr)):\n        for j in range(len(arr)-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr\n",
        sess1.session_id,
    )

    # 2. Scan Batch 1
    _run_analysis_sync("job_batch_1", sess1.session_id, None)
    res_b1 = get_latest_results(session_id=sess1.session_id)
    assert res_b1["job_id"] == "job_batch_1"
    assert res_b1["total_submissions"] == 2
    assert res_b1["high_risk_count"] == 1

    # 3. Create and Upload Batch 2 WITHOUT clearing Batch 1
    sess2 = create_session("Batch 2 - Math Utilities")
    save_submission(
        "b2_1", "fib.py", "student3", Language.PYTHON,
        "def fib(n):\n    return n if n <= 1 else fib(n-1)+fib(n-2)\n",
        sess2.session_id,
    )
    save_submission(
        "b2_2", "fib_unrelated.py", "student4", Language.PYTHON,
        "import math\ndef calc(x):\n    return math.sin(x)\n",
        sess2.session_id,
    )

    # 4. Verify Batch 2 has only its 2 submissions and Batch 1 has its 2 submissions
    subs_b1 = list_submissions(session_id=sess1.session_id)
    subs_b2 = list_submissions(session_id=sess2.session_id)
    assert len(subs_b1) == 2
    assert len(subs_b2) == 2
    assert all(s.session_id == sess1.session_id for s in subs_b1)
    assert all(s.session_id == sess2.session_id for s in subs_b2)

    # 5. Scan Batch 2 independently
    _run_analysis_sync("job_batch_2", sess2.session_id, None)
    res_b2 = get_latest_results(session_id=sess2.session_id)
    assert res_b2["job_id"] == "job_batch_2"
    assert res_b2["total_submissions"] == 2

    # 6. Verify Batch 1 results are completely PRESERVED and untouched
    preserved_b1 = get_latest_results(session_id=sess1.session_id)
    assert preserved_b1["job_id"] == "job_batch_1"
    assert preserved_b1["total_submissions"] == 2
    assert preserved_b1["high_risk_count"] == 1

    # 7. Verify history endpoint contains both batches
    hist = list_analysis_history()
    assert len(hist) >= 2
    job_ids = [h["job_id"] for h in hist]
    assert "job_batch_1" in job_ids
    assert "job_batch_2" in job_ids


def test_side_by_side_comparison():
    res = load_sample_datasets()
    session_id = res["session_id"]
    job_id = "test_run_job_comp"
    _run_analysis_sync(job_id, session_id, None)

    latest = get_latest_results(session_id=session_id)
    top_pair = latest["top_suspicious_pairs"][0]
    pair_id = top_pair.pair_id

    comp = get_comparison_detail(pair_id)
    assert comp["pair_id"] == pair_id
    assert "submission_a" in comp
    assert "submission_b" in comp
    assert comp["submission_a"]["content"] is not None
    assert comp["submission_b"]["content"] is not None
    assert "scores" in comp
    assert "transformations" in comp
    assert "matching_spans" in comp
    assert len(comp["matching_spans"]) >= 1


def test_reports_generation():
    res = load_sample_datasets()
    session_id = res["session_id"]
    job_id = "test_run_job_rep"
    _run_analysis_sync(job_id, session_id, None)

    # JSON report
    json_resp = export_json_report(session_id=session_id)
    assert json_resp.status_code == 200
    assert "quicksort" in json_resp.body.decode()

    # CSV report
    csv_resp = export_csv_report(session_id=session_id)
    assert csv_resp.status_code == 200
    csv_text = csv_resp.body.decode()
    assert "Pair ID,Submission A Student" in csv_text
    assert "alice_smith" in csv_text

    # HTML report
    html_resp = export_html_report(session_id=session_id)
    assert html_resp.status_code == 200
    html_text = html_resp.body.decode()
    assert "<!DOCTYPE html>" in html_text
    assert "Plagiarism Investigation Audit Report" in html_text


def test_weights_configuration():
    initial = get_weights()
    assert initial.ast_structural == 0.30

    new_weights = ScoringWeights(
        ast_structural=0.40,
        control_flow=0.30,
        structural_fingerprint=0.15,
        token_similarity=0.10,
        function_similarity=0.05,
    )
    saved = update_weights(new_weights)
    assert saved.ast_structural == 0.40

    retrieved = get_weights()
    assert retrieved.ast_structural == 0.40
