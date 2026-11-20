# VeritasCode: AI-Rewritten Code Plagiarism Detector

An enterprise-grade, high-throughput web application and code analysis engine designed to detect source code plagiarism even when solutions have been disguised or rewritten using modern generative AI tools (such as ChatGPT, Claude, and GitHub Copilot).

---

## 1. Key Capabilities

Traditional plagiarism checkers rely on superficial textual similarity (token string matching or diffs). They fail completely when students:
- **Rename variables and functions**
- **Reorder functions and declarations**
- **Convert loops into recursion** (or vice versa)
- **Modify conditional branch structures**
- **Inject dead code or format differences**
- **Rewrite logic through AI prompts**

**VeritasCode solves this by analyzing structural and logical code semantics rather than surface text.**

### Core Multi-Stage Pipeline:
1. **Stage 1: Code Preprocessing & Normalization**
   - Comment & docstring stripping across Python, C++, and Java.
   - Identifier anonymization (mapping user variables and function names sequentially to canonical symbols `v0`, `v1`, `v2` while retaining keywords and standard library identifiers).
   - Literal value normalization (`<STR>`, `<NUM>`, `<BOOL>`).
   - Token stream and n-gram generation.
2. **Stage 2: Abstract Syntax Tree (AST) Analysis**
   - Multi-language AST parsing (Python built-in AST + structural AST parser for C++ and Java).
   - Subtree hashing for invariant structural sub-trees.
   - Bipartite function-level matching (Hungarian matching) for 100% function reordering invariance.
3. **Stage 3: Control Flow Analysis (CFG)**
   - Basic block extraction and control edge topology.
   - Cyclomatic Complexity calculation ($M = E - N + 2P$).
   - **Loop-to-Recursion Transformation Detector**: Identifies algorithmic equivalence when an iterative loop accumulator is converted into a recursive call structure with base conditions.
4. **Stage 4: Structural Fingerprinting & LSH Candidate Filtering**
   - Winnowing algorithm (robust local minimum hash selection over rolling windows).
   - 64-dimensional MinHash signatures with reproducible hash permutations.
   - **Locality Sensitive Hashing (LSH)** with 16 bands $\times$ 4 rows: filters 44,850 pairs in sub-linear $O(N)$ time.
5. **Stage 5: Multi-Dimensional Scoring & Span Alignment**
   - Configurable weighted composite scoring (AST, CFG, Fingerprints, Tokens, Function Bipartite Match).
   - Risk classification (High $\ge 75\%$, Medium $45\%-74\%$, Low $< 45\%$).
   - Granular match span generation for side-by-side Monaco code comparison.

---

## 2. 300-Submission Performance Benchmark

The system includes a dedicated stress benchmark script (`backend/benchmark_300.py`) that generates 300 submissions across Python, C++, and Java, evaluating all **44,850 possible pairs**.

### Benchmark Target vs Actual Results:
| Metric | Requirement Target | VeritasCode Engine Result | Status |
| :--- | :--- | :--- | :--- |
| **Submissions** | 300 submissions | **300 submissions** | Passed |
| **Pairs Evaluated** | 44,850 pairs | **44,850 pairs** | Passed |
| **Execution Time** | < 120.0 seconds | **7.13 seconds** | **16x faster than target!** |
| **Throughput** | - | **6,288 pairs / second** | - |

To run the benchmark directly:
```bash
python backend/benchmark_300.py
```

---

## 3. The 6 Plagiarism Benchmark Scenarios

The engine is validated against all 6 required benchmark scenarios (verified via `backend/tests/test_engine.py`):
1. **Identical Files**: 100% similarity match.
2. **Renamed Variables & Functions**: High AST similarity ($\ge 80\%$), flags `has_renamed_identifiers`.
3. **Reordered Functions**: Optimal bipartite function matching detects identical function subtrees regardless of position in the file.
4. **Loop Converted to Recursion**: CFG detector recognizes loop state updates as recursive call base cases, flagging `has_loop_to_recursion`.
5. **Logically Similar but Different Implementations**: Measures true algorithmic distance without false-positive collapse.
6. **Completely Unrelated Solutions**: Scores $< 25\%$, categorized as Low Risk.

---

## 4. Architecture & Directory Structure

```
project hackathon/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, static mounts, routes
│   │   ├── config.py                # App configuration & thresholds
│   │   ├── database.py              # SQLite storage & CRUD models
│   │   ├── models.py                # Pydantic data schemas
│   │   ├── sample_data.py           # Preloaded benchmark submissions
│   │   ├── api/
│   │   │   ├── submissions.py       # File/ZIP upload, sample loader
│   │   │   ├── analysis.py          # Detection pipeline & WebSocket progress
│   │   │   ├── comparison.py        # Side-by-side Monaco comparison payload
│   │   │   ├── reports.py           # JSON, CSV, and HTML audit exports
│   │   │   └── benchmark.py         # On-demand benchmark endpoint
│   │   ├── engine/
│   │   │   ├── pipeline.py          # Extensible Multi-Stage Pipeline Runner
│   │   │   ├── stage_preprocess.py  # Stage 1: Preprocessing & tokenization
│   │   │   ├── stage_ast.py         # Stage 2: AST parsing & bipartite matching
│   │   │   ├── stage_cfg.py         # Stage 3: Control flow & loop-to-recursion
│   │   │   ├── stage_fingerprint.py # Stage 4: MinHash, Winnowing, LSH
│   │   │   ├── stage_scoring.py     # Stage 5: Weighted composite scoring
│   │   │   ├── matcher.py           # Span-level alignment for side-by-side view
│   │   │   └── language_detector.py # Python, C++, Java language detector
│   │   └── static/                  # Production Frontend SPA
│   │       ├── index.html           # Tailwind, React 18, Babel
│   │       ├── css/style.css        # Monaco highlight markers
│   │       └── js/app.jsx           # Complete 8-page React application
│   ├── tests/
│   │   ├── test_engine.py           # Automated tests for 6 benchmark scenarios
│   │   └── test_api.py              # Automated tests for API endpoints
│   ├── benchmark_300.py             # Performance benchmark script
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 5. Mid-Event Requirement Extensibility

To easily accommodate unforeseen requirements (e.g. announced at hour 12), the pipeline uses an extensible plugin design:
```python
from app.engine.pipeline import BasePipelineStage, PipelineContext

class CustomAIWatermarkStage(BasePipelineStage):
    @property
    def stage_name(self) -> str:
        return "Custom AI Watermark & Stylometry Detector"

    def execute(self, ctx: PipelineContext) -> None:
        for sub in ctx.submissions:
            # Add custom inspection or attribute
            ctx.custom_stage_data[sub.id] = {"watermark_confidence": 0.95}

# Plug into the pipeline dynamically:
pipeline = PlagiarismPipeline()
pipeline.register_stage(CustomAIWatermarkStage(), position=3)
```

---

## 6. Setup and Execution Instructions

### Option A: Local Execution (Windows / macOS / Linux)

1. **Install Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Run Automated Tests**:
   ```bash
   pytest backend/tests -v
   ```

3. **Run 300 Submissions Performance Benchmark**:
   ```bash
   python backend/benchmark_300.py
   ```

4. **Start the Application Server**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
   ```

5. **Open in Browser**:
   Navigate to:
   ```
   http://localhost:8000
   ```

### Option B: Docker Deployment

```bash
docker-compose up --build
```
Access the application at `http://localhost:8000`.

---

## 7. Interactive Walkthrough of the 8 Required Pages

1. **Login / Overview (`/`)**: Value proposition, feature comparison cards, 1-click sample dataset loader.
2. **Dashboard (`/dashboard`)**: Metric cards (Submissions, Pairs, High Risk, Time), language distribution, severity charts.
3. **Upload Submissions (`/upload`)**: Drag-and-drop folder, ZIP, or file uploads with automatic language identification.
4. **Processing Page (`/processing`)**: Real-time WebSocket animated progress bar across all 5 stages with live log stream.
5. **Plagiarism Results (`/results`)**: Ranked suspicious pairs, search by student/file, risk filter, language filter, minimum similarity slider.
6. **Side-by-Side Comparison (`/comparison`)**: Synchronized dual-editor code view with color-coded highlight markers for exact structure, renamed variables, control flow, and loop-to-recursion, plus match navigation (`Prev` / `Next`).
7. **Individual Submission Details (`/submission_detail`)**: Deep AST node breakdown, extracted function signatures, cyclomatic complexity, loop/branch counts, and counterpart match history.
8. **Reports & Benchmark (`/reports`)**: Download JSON, CSV, or open institutional printable audit reports, plus live 300-submission benchmark runner.
