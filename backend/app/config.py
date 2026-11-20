"""
Application settings and defaults.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)

DB_PATH = DATA_DIR / "detector.db"

# Risk Thresholds
HIGH_RISK_THRESHOLD = 75.0
MEDIUM_RISK_THRESHOLD = 45.0

# Candidate Filtering Thresholds
# Fingerprint Jaccard similarity threshold to promote a pair to deep AST/CFG evaluation
MINHASH_CANDIDATE_THRESHOLD = 0.20
# Maximum candidates to deep-evaluate per submission to avoid combinatorial explosion
MAX_CANDIDATES_PER_SUBMISSION = 60

# Max upload limit (bytes)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_ZIP_SIZE_BYTES = 50 * 1024 * 1024   # 50MB
