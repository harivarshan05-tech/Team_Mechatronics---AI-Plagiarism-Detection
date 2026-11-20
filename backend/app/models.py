"""
Pydantic schemas and data transfer objects for the Plagiarism Detector.
Includes multi-batch session tracking and analysis history management.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class Language(str, Enum):
    PYTHON = "python"
    CPP = "cpp"
    JAVA = "java"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    HIGH = "high"       # >= 75%
    MEDIUM = "medium"   # 45% - 74%
    LOW = "low"         # < 45%


class MatchType(str, Enum):
    EXACT_STRUCTURE = "exact_structure"
    RENAMED_IDENTIFIERS = "renamed_identifiers"
    CONTROL_FLOW = "control_flow"
    LOOP_TO_RECURSION = "loop_to_recursion"
    REORDERED_LOGIC = "reordered_logic"
    TOKEN_SIMILARITY = "token_similarity"


class UploadSessionStatus(str, Enum):
    DRAFT = "Draft"
    UPLOADING = "Uploading"
    UPLOADED = "Uploaded"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


class UploadSession(BaseModel):
    session_id: str
    batch_name: str
    status: UploadSessionStatus
    submission_count: int = 0
    file_names: List[str] = []
    languages: List[str] = []
    job_id: Optional[str] = None
    created_at: str
    updated_at: str


class CreateSessionRequest(BaseModel):
    batch_name: Optional[str] = None


class MatchSpan(BaseModel):
    span_id: str
    match_type: MatchType
    sub_a_start_line: int
    sub_a_end_line: int
    sub_b_start_line: int
    sub_b_end_line: int
    description: str
    confidence: float = Field(ge=0.0, le=1.0)


class ScoringWeights(BaseModel):
    ast_structural: float = Field(default=0.30, ge=0.0, le=1.0)
    control_flow: float = Field(default=0.25, ge=0.0, le=1.0)
    structural_fingerprint: float = Field(default=0.20, ge=0.0, le=1.0)
    token_similarity: float = Field(default=0.15, ge=0.0, le=1.0)
    function_similarity: float = Field(default=0.10, ge=0.0, le=1.0)

    def normalized(self) -> "ScoringWeights":
        total = (
            self.ast_structural
            + self.control_flow
            + self.structural_fingerprint
            + self.token_similarity
            + self.function_similarity
        )
        if total == 0:
            return ScoringWeights()
        return ScoringWeights(
            ast_structural=self.ast_structural / total,
            control_flow=self.control_flow / total,
            structural_fingerprint=self.structural_fingerprint / total,
            token_similarity=self.token_similarity / total,
            function_similarity=self.function_similarity / total,
        )


class SubmissionMeta(BaseModel):
    id: str
    filename: str
    student_id: str
    language: Language
    file_size_bytes: int
    line_count: int
    created_at: str
    content: Optional[str] = None
    session_id: str = "default_session"


class SubmissionCreate(BaseModel):
    filename: str
    student_id: str
    content: str
    language: Optional[Language] = None
    session_id: Optional[str] = None


class PairComparisonResult(BaseModel):
    pair_id: str
    submission_a_id: str
    submission_a_name: str
    submission_a_student: str
    submission_b_id: str
    submission_b_name: str
    submission_b_student: str
    language: Language
    overall_similarity: float  # 0.0 to 100.0
    risk_level: RiskLevel

    # Dimensional scores (0.0 to 100.0)
    ast_score: float
    cfg_score: float
    fingerprint_score: float
    token_score: float
    function_score: float

    # Qualitative detections
    has_renamed_identifiers: bool = False
    has_reordered_functions: bool = False
    has_loop_to_recursion: bool = False
    has_modified_conditionals: bool = False

    matching_spans: List[MatchSpan] = []
    summary: str = ""
    session_id: Optional[str] = None


class AnalysisProgress(BaseModel):
    job_id: str
    current_stage: str
    stage_index: int
    total_stages: int = 5
    percent_complete: float
    processed_count: int
    total_count: int
    pairs_evaluated: int
    candidate_pairs_found: int
    message: str
    elapsed_seconds: float
    session_id: Optional[str] = None


class AnalysisRunResult(BaseModel):
    job_id: str
    session_id: Optional[str] = None
    batch_name: Optional[str] = None
    status: str
    total_submissions: int
    total_pairs_evaluated: int
    suspicious_pairs_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    processing_time_seconds: float
    language_distribution: Dict[str, int]
    top_suspicious_pairs: List[PairComparisonResult]
    scoring_weights_used: ScoringWeights
    created_at: str


class BenchmarkResult(BaseModel):
    num_submissions: int
    num_pairs_evaluated: int
    total_time_seconds: float
    pairs_per_second: float
    target_time_seconds: float = 120.0
    target_met: bool
    stage_timings: Dict[str, float]
    memory_mb: float
