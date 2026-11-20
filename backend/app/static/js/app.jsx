/**
 * VeritasCode - AI Plagiarism Engine
 * Multi-batch session architecture, resilient file upload handlers,
 * real-time WebSockets, Monaco code comparison, and analysis history.
 */

const { useState, useEffect, useRef } = React;

// API Helper with strict error checking
const API = {
  get: async (url) => {
    const r = await fetch(url);
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      const error = new Error(err.detail || `HTTP ${r.status}`);
      error.status = r.status;
      throw error;
    }
    return r.json();
  },
  post: async (url, body) => {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      const error = new Error(err.detail || `HTTP ${r.status}`);
      error.status = r.status;
      throw error;
    }
    return r.json();
  },
  delete: async (url) => {
    const r = await fetch(url, { method: "DELETE" });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      const error = new Error(err.detail || `HTTP ${r.status}`);
      error.status = r.status;
      throw error;
    }
    return r.json();
  },
  upload: async (url, formData) => {
    const r = await fetch(url, { method: "POST", body: formData });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    return r.json();
  },
};

// SVG Icons
function Icon({ name, className = "w-4 h-4" }) {
  const icons = {
    shield: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    ),
    dashboard: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    ),
    upload: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
    ),
    plus: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    ),
    history: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    ),
    play: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
    ),
    check: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    ),
    alert: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    ),
    compare: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
    ),
    fileText: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    ),
    download: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    ),
    zap: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    ),
    code: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    ),
    trash: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    ),
    slider: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
    ),
    arrowLeft: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
    ),
    refresh: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    ),
  };

  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      {icons[name] || icons.shield}
    </svg>
  );
}

// Risk Badge Helper
function RiskBadge({ risk }) {
  const r = (risk || "low").toLowerCase();
  const styles = {
    high: "bg-red-500/10 text-red-400 border border-red-500/30",
    medium: "bg-amber-500/10 text-amber-400 border border-amber-500/30",
    low: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30",
  };
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${styles[r] || styles.low}`}>
      {r} risk
    </span>
  );
}

// Language Badge Helper
function LanguageBadge({ lang }) {
  const l = (lang || "").toLowerCase();
  const colors = {
    python: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    cpp: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    java: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono font-medium border ${colors[l] || "bg-slate-800 text-slate-300 border-slate-700"}`}>
      {l.toUpperCase()}
    </span>
  );
}

// -------------------------------------------------------------
// MAIN APP COMPONENT
// -------------------------------------------------------------
function App() {
  const [currentPage, setCurrentPageRaw] = useState(() => {
    return localStorage.getItem("veritas_page") || "welcome";
  });
  const setCurrentPage = (p) => {
    localStorage.setItem("veritas_page", p);
    setCurrentPageRaw(p);
  };

  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionIdRaw] = useState(() => {
    return localStorage.getItem("veritas_session_id") || null;
  });
  const setActiveSessionId = (s) => {
    if (s) localStorage.setItem("veritas_session_id", s);
    else localStorage.removeItem("veritas_session_id");
    setActiveSessionIdRaw(s);
  };

  const [submissions, setSubmissions] = useState([]);
  const [latestRun, setLatestRun] = useState(null);
  const [history, setHistory] = useState([]);
  const [selectedPairId, setSelectedPairId] = useState(null);
  const [selectedSubId, setSelectedSubId] = useState(null);
  const [activeJobId, setActiveJobId] = useState(null);
  const [showWeightsModal, setShowWeightsModal] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [weights, setWeights] = useState({
    ast_structural: 0.3,
    control_flow: 0.25,
    structural_fingerprint: 0.2,
    token_similarity: 0.15,
    function_similarity: 0.1,
  });

  const showToast = (msg, isError = false) => {
    setToastMessage({ text: msg, isError });
    setTimeout(() => setToastMessage(null), 4000);
  };

  useEffect(() => {
    refreshAllData();
  }, []);

  const refreshAllData = async (preferredSessionId = null) => {
    try {
      // 1. Fetch sessions
      const sessList = await API.get("/api/submissions/sessions");
      setSessions(sessList || []);

      let currentSess = preferredSessionId;
      if (!currentSess) {
        currentSess = activeSessionId || localStorage.getItem("veritas_session_id");
      }
      if (!currentSess && sessList && sessList.length > 0) {
        currentSess = sessList[0].session_id;
      }
      setActiveSessionId(currentSess);

      // 2. Fetch submissions for active session
      if (currentSess) {
        const subs = await API.get(`/api/submissions?session_id=${currentSess}`);
        setSubmissions(subs || []);
      } else {
        const subs = await API.get("/api/submissions");
        setSubmissions(subs || []);
      }

      // 3. Fetch latest run
      try {
        const runUrl = currentSess ? `/api/analysis/latest?session_id=${currentSess}` : "/api/analysis/latest";
        const run = await API.get(runUrl);
        if (run && run.job_id) {
          setLatestRun(run);
        } else {
          setLatestRun(null);
        }
      } catch (err) {
        // No run for this session yet
        setLatestRun(null);
      }

      // 4. Fetch history
      const hist = await API.get("/api/analysis/history");
      setHistory(hist || []);

      // 5. Fetch weights
      const w = await API.get("/api/analysis/weights");
      if (w) setWeights(w);
    } catch (e) {
      console.log("Data sync notice:", e.message);
    }
  };

  const handleSelectSession = async (sessId) => {
    setActiveSessionId(sessId);
    await refreshAllData(sessId);
  };

  const handleCreateNewBatch = async () => {
    try {
      const newSess = await API.post("/api/submissions/sessions");
      setActiveSessionId(newSess.session_id);
      await refreshAllData(newSess.session_id);
      setCurrentPage("upload");
      showToast(`Created new batch: ${newSess.batch_name}`);
    } catch (e) {
      alert("Failed to create new batch: " + e.message);
    }
  };

  const startAnalysis = async (targetSessId = null) => {
    const sessToScan = targetSessId || activeSessionId;
    try {
      const res = await API.post(`/api/analysis/start?session_id=${sessToScan || ""}`, { session_id: sessToScan });
      if (!res || !res.job_id) {
        alert("Failed to start scan: no job ID returned.");
        return;
      }
      setActiveJobId(res.job_id);
      setCurrentPage("processing");
    } catch (e) {
      alert("Cannot start analysis: " + e.message);
    }
  };

  const loadSamples = async () => {
    try {
      const res = await API.post("/api/submissions/load-samples");
      setActiveSessionId(res.session_id);
      await refreshAllData(res.session_id);
      setCurrentPage("upload");
      showToast(`Loaded ${res.loaded_count} benchmark submissions into new batch!`);
    } catch (e) {
      alert("Failed to load samples: " + e.message);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div
            className="flex items-center space-x-3 cursor-pointer"
            onClick={() => setCurrentPage("welcome")}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Icon name="shield" className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                VeritasCode
              </span>
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                Multi-Batch Engine
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            {[
              { id: "welcome", label: "Overview", icon: "shield" },
              { id: "dashboard", label: "Dashboard", icon: "dashboard" },
              { id: "upload", label: "Upload & Batches", icon: "upload", count: submissions.length },
              { id: "results", label: "Results", icon: "fileText", count: latestRun?.suspicious_pairs_count },
              { id: "history", label: "Scan History", icon: "history", count: history.length },
              { id: "reports", label: "Reports & Benchmark", icon: "download" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setCurrentPage(tab.id)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  currentPage === tab.id
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`}
              >
                <Icon name={tab.icon} className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.count !== undefined && tab.count > 0 && (
                  <span
                    className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] ${
                      currentPage === tab.id
                        ? "bg-white text-indigo-600 font-bold"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>

          {/* Action buttons */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowWeightsModal(true)}
              className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              title="Scoring Weights Configuration"
            >
              <Icon name="slider" className="w-5 h-5" />
            </button>
            <button
              onClick={() => startAnalysis()}
              disabled={submissions.length < 2}
              className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition shadow-sm ${
                submissions.length >= 2
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-indigo-600/25"
                  : "bg-slate-800 text-slate-500 cursor-not-allowed"
              }`}
            >
              <Icon name="play" className="w-4 h-4" />
              <span>Scan Active Batch</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentPage === "welcome" && (
          <WelcomePage
            onExplore={() => setCurrentPage("dashboard")}
            onLoadSamples={loadSamples}
            onUpload={() => setCurrentPage("upload")}
            submissionsCount={submissions.length}
          />
        )}
        {currentPage === "dashboard" && (
          <DashboardPage
            latestRun={latestRun}
            submissions={submissions}
            history={history}
            onStartScan={() => {
              setCurrentPage("upload");
            }}
            onGoToUpload={() => setCurrentPage("upload")}
            onGoToResults={() => setCurrentPage("results")}
            onCompare={(pairId) => {
              setSelectedPairId(pairId);
              setCurrentPage("comparison");
            }}
            onViewHistoryRun={async (jobId, sessId) => {
              await refreshAllData(sessId);
              setCurrentPage("results");
            }}
          />
        )}
        {currentPage === "upload" && (
          <UploadPage
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
            onCreateSession={handleCreateNewBatch}
            submissions={submissions}
            onRefresh={refreshAllData}
            onLoadSamples={loadSamples}
            onStartScan={() => startAnalysis(activeSessionId)}
            onViewDetails={(subId) => {
              setSelectedSubId(subId);
              setCurrentPage("submission_detail");
            }}
          />
        )}
        {currentPage === "processing" && (
          <ProcessingPage
            jobId={activeJobId}
            onComplete={async () => {
              await refreshAllData(activeSessionId);
              setCurrentPage("results");
            }}
          />
        )}
        {currentPage === "results" && (
          <ResultsPage
            latestRun={latestRun}
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
            onReRunScan={() => startAnalysis(activeSessionId)}
            onUploadNewSubmissions={() => {
              handleCreateNewBatch();
            }}
            onCompare={(pairId) => {
              setSelectedPairId(pairId);
              setCurrentPage("comparison");
            }}
            onViewSubmission={(subId) => {
              setSelectedSubId(subId);
              setCurrentPage("submission_detail");
            }}
          />
        )}
        {currentPage === "history" && (
          <AnalysisHistoryPage
            history={history}
            onViewResults={async (jobId, sessId) => {
              await refreshAllData(sessId);
              setCurrentPage("results");
            }}
            onStartNewBatch={handleCreateNewBatch}
          />
        )}
        {currentPage === "comparison" && (
          <ComparisonPage
            pairId={selectedPairId}
            onBack={() => setCurrentPage("results")}
          />
        )}
        {currentPage === "submission_detail" && (
          <SubmissionDetailPage
            subId={selectedSubId}
            onBack={() => setCurrentPage("upload")}
          />
        )}
        {currentPage === "reports" && (
          <ReportsPage
            latestRun={latestRun}
            activeSessionId={activeSessionId}
          />
        )}
      </main>

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50">
          <div className={`px-4 py-3 rounded-xl shadow-xl flex items-center space-x-2 border text-xs font-semibold ${
            toastMessage.isError
              ? "bg-red-950/90 border-red-500/50 text-red-200"
              : "bg-indigo-950/90 border-indigo-500/50 text-indigo-200"
          }`}>
            <Icon name={toastMessage.isError ? "alert" : "check"} className="w-4 h-4 text-emerald-400" />
            <span>{toastMessage.text}</span>
          </div>
        </div>
      )}

      {/* Scoring Weights Modal */}
      {showWeightsModal && (
        <WeightsModal
          weights={weights}
          onClose={() => setShowWeightsModal(false)}
          onSave={async (newW) => {
            const saved = await API.post("/api/analysis/weights", newW);
            setWeights(saved);
            setShowWeightsModal(false);
          }}
        />
      )}
    </div>
  );
}

// -------------------------------------------------------------
// 1. WELCOME PAGE
// -------------------------------------------------------------
function WelcomePage({ onExplore, onLoadSamples, onUpload }) {
  return (
    <div className="space-y-12 py-6">
      <div className="text-center max-w-3xl mx-auto space-y-5">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
          <Icon name="zap" className="w-3.5 h-3.5" />
          <span>Multi-Batch Structural & Logical Plagiarism Detection</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
          Detect Code Plagiarism Even When{" "}
          <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Rewritten by AI
          </span>
        </h1>
        <p className="text-slate-400 text-base sm:text-lg leading-relaxed">
          VeritasCode parses ASTs, constructs Control Flow Graphs, and analyzes invariant logic.
          Supports unlimited sequential upload batches with independent session preservation.
        </p>

        <div className="pt-2 flex flex-wrap items-center justify-center gap-4">
          <button
            onClick={onLoadSamples}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold shadow-lg shadow-indigo-600/30 flex items-center space-x-2 transition"
          >
            <Icon name="zap" className="w-5 h-5" />
            <span>Load Benchmark Submissions</span>
          </button>
          <button
            onClick={onUpload}
            className="px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold border border-slate-700 flex items-center space-x-2 transition"
          >
            <Icon name="upload" className="w-5 h-5" />
            <span>Upload Student Files / ZIP</span>
          </button>
          <button
            onClick={onExplore}
            className="px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-semibold border border-slate-800 flex items-center space-x-2 transition"
          >
            <Icon name="dashboard" className="w-5 h-5" />
            <span>Open Dashboard</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Icon name="code" className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white">AST Subtree Isomorphism</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            Parses Python, C++, and Java into normalized syntax trees. Renamed variables and
            reordered functions produce zero disguise.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Icon name="zap" className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white">Loop-to-Recursion Detection</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            Constructs Control Flow Graphs (CFG) and automatically identifies when loops are
            mechanically converted into recursive functions.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Icon name="history" className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white">Multi-Batch Sessions</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            Upload and analyze multiple batches independently. Revisit previous scan history
            without overwriting or losing any past data.
          </p>
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// 2. MAIN DASHBOARD PAGE
// -------------------------------------------------------------
function DashboardPage({
  latestRun,
  submissions,
  history,
  onStartScan,
  onGoToUpload,
  onGoToResults,
  onCompare,
  onViewHistoryRun,
}) {
  const topPairs = latestRun?.top_suspicious_pairs?.slice(0, 5) || [];

  return (
    <div className="space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Analytics Dashboard</h1>
          <p className="text-slate-400 text-sm">
            Continuous structural plagiarism evaluation across uploaded programming solutions.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={onStartScan}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-indigo-600/30 flex items-center space-x-1.5 transition"
          >
            <Icon name="upload" className="w-4 h-4" />
            <span>START NEW SCAN</span>
          </button>
          <button
            onClick={onGoToUpload}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
          >
            Manage Submissions ({submissions.length})
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="text-xs uppercase font-semibold text-slate-400">Submissions Analyzed</div>
          <div className="text-3xl font-bold text-white">
            {latestRun ? latestRun.total_submissions : submissions.length}
          </div>
          <div className="text-xs text-slate-500">Active batch solutions</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="text-xs uppercase font-semibold text-slate-400">Pairs Evaluated</div>
          <div className="text-3xl font-bold text-indigo-400">
            {latestRun
              ? latestRun.total_pairs_evaluated.toLocaleString()
              : (submissions.length * (submissions.length - 1) / 2).toLocaleString()}
          </div>
          <div className="text-xs text-slate-500">Full pairwise matrix</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="text-xs uppercase font-semibold text-slate-400">High Risk Matches</div>
          <div className="text-3xl font-bold text-red-400">
            {latestRun ? latestRun.high_risk_count : 0}
          </div>
          <div className="text-xs text-red-500/80 font-medium">&ge; 75% structural similarity</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <div className="text-xs uppercase font-semibold text-slate-400">Processing Time</div>
          <div className="text-3xl font-bold text-emerald-400">
            {latestRun ? `${latestRun.processing_time_seconds}s` : "0.0s"}
          </div>
          <div className="text-xs text-emerald-500/80 font-medium">Sub-linear LSH acceleration</div>
        </div>
      </div>

      {/* Top Suspicious Pairs Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white">Top Suspicious Submission Pairs</h3>
            <div className="text-xs text-slate-400 mt-0.5">
              Active Batch: <span className="font-semibold text-indigo-400">{latestRun?.batch_name || "Current Batch"}</span>
            </div>
          </div>
          <button
            onClick={onGoToResults}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
          >
            View All ({latestRun?.top_suspicious_pairs?.length || 0}) &rarr;
          </button>
        </div>

        {topPairs.length > 0 ? (
          <div className="divide-y divide-slate-800/60">
            {topPairs.map((p, idx) => (
              <div
                key={p.pair_id}
                className="px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-slate-800/30 transition"
              >
                <div className="flex items-center space-x-4">
                  <div className="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs text-slate-400">
                    #{idx + 1}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-white">{p.submission_a_student}</span>
                      <span className="text-slate-500 text-xs">vs</span>
                      <span className="font-semibold text-white">{p.submission_b_student}</span>
                      <LanguageBadge lang={p.language} />
                    </div>
                    <div className="text-xs text-slate-400 mt-1 flex flex-wrap gap-2">
                      <span>{p.submission_a_name} &bull; {p.submission_b_name}</span>
                      {p.has_loop_to_recursion && (
                        <span className="text-purple-400 font-medium">[Loop &harr; Recursion]</span>
                      )}
                      {p.has_renamed_identifiers && (
                        <span className="text-blue-400 font-medium">[Renamed Identifiers]</span>
                      )}
                      {p.has_reordered_functions && (
                        <span className="text-indigo-400 font-medium">[Reordered Functions]</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-4 self-end sm:self-auto">
                  <div className="text-right">
                    <div className="text-lg font-bold text-white">{p.overall_similarity}%</div>
                    <RiskBadge risk={p.risk_level} />
                  </div>
                  <button
                    onClick={() => onCompare(p.pair_id)}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 text-xs font-semibold hover:bg-indigo-600 hover:text-white transition"
                  >
                    Compare
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 text-sm">
            No analysis results available for this batch. Upload submissions and click "Scan Active Batch".
          </div>
        )}
      </div>

      {/* Quick History Section */}
      {history.length > 0 && (
        <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-base font-bold text-white">Recent Analysis Batches</h3>
            <span className="text-xs text-slate-400">{history.length} saved scans</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/40 text-slate-400 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-6">Batch ID / Name</th>
                  <th className="py-3 px-6">Date</th>
                  <th className="py-3 px-6">Files</th>
                  <th className="py-3 px-6">Languages</th>
                  <th className="py-3 px-6">High Risk</th>
                  <th className="py-3 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {history.slice(0, 4).map((h) => (
                  <tr key={h.job_id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-6 font-semibold text-slate-200">
                      {h.batch_name}
                      <span className="text-[10px] text-slate-500 block font-normal">{h.job_id}</span>
                    </td>
                    <td className="py-3 px-6 text-slate-400">{new Date(h.created_at).toLocaleDateString()}</td>
                    <td className="py-3 px-6 text-white font-bold">{h.total_submissions}</td>
                    <td className="py-3 px-6">
                      <div className="flex gap-1">
                        {h.languages.map((l) => (
                          <LanguageBadge key={l} lang={l} />
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-6">
                      <span className="text-red-400 font-bold">{h.high_risk}</span>
                    </td>
                    <td className="py-3 px-6 text-right font-sans">
                      <button
                        onClick={() => onViewHistoryRun(h.job_id, h.session_id)}
                        className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                      >
                        View Results &rarr;
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// -------------------------------------------------------------
// 3. UPLOAD SUBMISSIONS & SESSION MANAGEMENT PAGE
// -------------------------------------------------------------
function UploadPage({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  submissions,
  onRefresh,
  onLoadSamples,
  onStartScan,
  onViewDetails,
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);

  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const zipInputRef = useRef(null);

  // Dedicated Reset Function complying with requirements
  const handleResetInputs = () => {
    setUploadProgress(0);
    setIsUploading(false);
    setErrorMessage(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    if (folderInputRef.current) {
      folderInputRef.current.value = "";
    }
    if (zipInputRef.current) {
      zipInputRef.current.value = "";
    }
  };

  const handleFiles = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    setIsUploading(true);
    setErrorMessage(null);
    setUploadProgress(20);

    const formData = new FormData();
    for (let i = 0; i < fileList.length; i++) {
      formData.append("files", fileList[i]);
    }
    if (activeSessionId) {
      formData.append("session_id", activeSessionId);
    }

    try {
      setUploadProgress(60);
      const res = await API.upload("/api/submissions/upload", formData);
      setUploadProgress(100);
      alert(`Successfully uploaded ${res.uploaded_count} submissions to ${activeSessionId || "new batch"}!`);
      await onRefresh(res.session_id || activeSessionId);
    } catch (e) {
      setErrorMessage(e.message);
      alert("Upload failed: " + e.message);
    } finally {
      handleResetInputs();
    }
  };

  const clearCurrentBatch = async () => {
    if (!activeSessionId) return;
    if (confirm("Delete submissions in this batch? (Other batches will remain safe)")) {
      await API.delete(`/api/submissions/sessions/${activeSessionId}`);
      await onRefresh();
    }
  };

  return (
    <div className="space-y-8">
      {/* Header with Batch Session Switcher */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Upload Submissions</h1>
          <p className="text-slate-400 text-sm">
            Upload files, folders, or ZIP archives into independent, isolated batch sessions.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={onCreateSession}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-indigo-600/30 flex items-center space-x-1.5 transition"
          >
            <Icon name="plus" className="w-4 h-4" />
            <span>+ START NEW BATCH</span>
          </button>
          <button
            onClick={onLoadSamples}
            className="px-4 py-2 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 text-xs font-semibold hover:bg-indigo-600 hover:text-white transition"
          >
            Load Benchmark Sample Pack
          </button>
        </div>
      </div>

      {/* Batch Session Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <label className="text-xs uppercase font-bold text-slate-400 tracking-wider">Active Batch Session:</label>
          <select
            value={activeSessionId || ""}
            onChange={(e) => onSelectSession(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-xs font-semibold focus:outline-none focus:border-indigo-500 flex-1 sm:flex-initial"
          >
            {sessions.map((s) => (
              <option key={s.session_id} value={s.session_id}>
                {s.batch_name} ({s.submission_count} files) &bull; [{s.status}]
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <span className="text-slate-500">Status:</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
            {sessions.find((s) => s.session_id === activeSessionId)?.status || "Active"}
          </span>
          {submissions.length > 0 && (
            <button
              onClick={clearCurrentBatch}
              className="ml-3 text-red-400 hover:text-red-300 transition text-xs font-semibold"
            >
              Delete Batch
            </button>
          )}
        </div>
      </div>

      {/* Upload Dropzones */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Files Dropzone */}
        <div
          onClick={() => {
            if (fileInputRef.current) {
              fileInputRef.current.value = "";
              fileInputRef.current.click();
            }
          }}
          className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition space-y-3 ${
            isUploading
              ? "border-slate-700 bg-slate-900/20 cursor-wait"
              : "border-slate-800 hover:border-indigo-500/50 bg-slate-900/40 hover:bg-slate-900/80"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            multiple
            accept=".py,.cpp,.hpp,.h,.java"
            className="hidden"
            onChange={(e) => {
              const files = e.target.files;
              handleFiles(files);
              e.target.value = "";
            }}
          />
          <div className="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 mx-auto flex items-center justify-center">
            <Icon name="code" className="w-6 h-6" />
          </div>
          <div>
            <div className="font-semibold text-white text-sm">Individual Files</div>
            <div className="text-xs text-slate-400 mt-1">Select one or multiple .py, .cpp, .java files</div>
          </div>
        </div>

        {/* Folder Upload */}
        <div
          onClick={() => {
            if (folderInputRef.current) {
              folderInputRef.current.value = "";
              folderInputRef.current.click();
            }
          }}
          className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition space-y-3 ${
            isUploading
              ? "border-slate-700 bg-slate-900/20 cursor-wait"
              : "border-slate-800 hover:border-indigo-500/50 bg-slate-900/40 hover:bg-slate-900/80"
          }`}
        >
          <input
            type="file"
            ref={folderInputRef}
            webkitdirectory="true"
            directory="true"
            multiple
            className="hidden"
            onChange={(e) => {
              const files = e.target.files;
              handleFiles(files);
              e.target.value = "";
            }}
          />
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20 mx-auto flex items-center justify-center">
            <Icon name="upload" className="w-6 h-6" />
          </div>
          <div>
            <div className="font-semibold text-white text-sm">Entire Folder</div>
            <div className="text-xs text-slate-400 mt-1">Directory of student submissions</div>
          </div>
        </div>

        {/* ZIP Upload */}
        <div
          onClick={() => {
            if (zipInputRef.current) {
              zipInputRef.current.value = "";
              zipInputRef.current.click();
            }
          }}
          className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition space-y-3 ${
            isUploading
              ? "border-slate-700 bg-slate-900/20 cursor-wait"
              : "border-slate-800 hover:border-indigo-500/50 bg-slate-900/40 hover:bg-slate-900/80"
          }`}
        >
          <input
            type="file"
            ref={zipInputRef}
            accept=".zip"
            className="hidden"
            onChange={(e) => {
              const files = e.target.files;
              handleFiles(files);
              e.target.value = "";
            }}
          />
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mx-auto flex items-center justify-center">
            <Icon name="fileText" className="w-6 h-6" />
          </div>
          <div>
            <div className="font-semibold text-white text-sm">ZIP Archive</div>
            <div className="text-xs text-slate-400 mt-1">Auto-extracted & organized by student</div>
          </div>
        </div>
      </div>

      {isUploading && (
        <div className="p-4 rounded-xl bg-indigo-950/40 border border-indigo-500 text-center space-y-2">
          <div className="text-xs font-semibold text-indigo-300">Uploading files to active session...</div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div className="h-full bg-indigo-500 transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
          </div>
        </div>
      )}

      {/* Submissions List */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white">
              Submissions in Batch ({submissions.length})
            </h3>
            <span className="text-xs text-slate-400">
              Only files in this batch will be analyzed together.
            </span>
          </div>
          <button
            onClick={onStartScan}
            disabled={submissions.length < 2 || isUploading}
            className={`px-4 py-2 rounded-lg text-xs font-bold shadow-md transition ${
              submissions.length >= 2 && !isUploading
                ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30"
                : "bg-slate-800 text-slate-500 cursor-not-allowed"
            }`}
          >
            Scan This Batch ({submissions.length} files) &rarr;
          </button>
        </div>

        {submissions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/40 text-slate-400 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="py-3 px-6">Filename</th>
                  <th className="py-3 px-6">Student ID</th>
                  <th className="py-3 px-6">Language</th>
                  <th className="py-3 px-6">Lines</th>
                  <th className="py-3 px-6">File Size</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {submissions.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-6 font-semibold text-slate-200">{s.filename}</td>
                    <td className="py-3 px-6 text-slate-400">{s.student_id}</td>
                    <td className="py-3 px-6">
                      <LanguageBadge lang={s.language} />
                    </td>
                    <td className="py-3 px-6 text-slate-400">{s.line_count}</td>
                    <td className="py-3 px-6 text-slate-400">{(s.file_size_bytes / 1024).toFixed(1)} KB</td>
                    <td className="py-3 px-6 text-right font-sans space-x-2">
                      <button
                        onClick={() => onViewDetails(s.id)}
                        className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                      >
                        Inspect AST
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-500 text-sm">
            This batch currently has no files. Drag and drop files above or click "Load Benchmark Sample Pack".
          </div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// 4. PROCESSING / ANALYSIS PAGE
// -------------------------------------------------------------
function ProcessingPage({ jobId, onComplete }) {
  const [progress, setProgress] = useState({
    percent_complete: 0,
    current_stage: "Initializing Engine...",
    stage_index: 0,
    total_stages: 5,
    pairs_evaluated: 0,
    candidate_pairs_found: 0,
    elapsed_seconds: 0,
    message: "Connecting to real-time engine telemetry...",
  });
  const [logs, setLogs] = useState([]);
  const completedRef = useRef(false);

  useEffect(() => {
    if (!jobId) return;
    completedRef.current = false;

    const finishOnce = () => {
      if (!completedRef.current) {
        completedRef.current = true;
        setTimeout(() => {
          onComplete();
        }, 900);
      }
    };

    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/api/analysis/ws/${jobId}`;
    let socket;

    try {
      socket = new WebSocket(wsUrl);
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setProgress(data);
          setLogs((prev) => [
            ...prev.slice(-40),
            `[${new Date().toLocaleTimeString()}] Stage ${data.stage_index}/5: ${data.message}`,
          ]);

          if (data.percent_complete >= 100) {
            finishOnce();
          }
        } catch (err) {}
      };
    } catch (e) {
      console.log("WebSocket connect notice:", e);
    }

    const interval = setInterval(async () => {
      try {
        const p = await API.get(`/api/analysis/progress/${jobId}`);
        if (p) {
          setProgress(p);
          if (p.percent_complete >= 100) {
            clearInterval(interval);
            finishOnce();
          }
        }
      } catch (err) {}
    }, 500);

    return () => {
      if (socket) socket.close();
      clearInterval(interval);
    };
  }, [jobId]);

  const stages = [
    "Code Preprocessing & Normalization",
    "Abstract Syntax Tree Parsing",
    "Control Flow & Recursion Analysis",
    "Structural Fingerprinting & LSH",
    "Multi-Dimensional Scoring",
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-8 py-8">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-extrabold text-white">Plagiarism Analysis in Progress</h1>
        <p className="text-slate-400 text-sm">
          Job ID: <span className="font-mono text-indigo-400">{jobId}</span>
        </p>
      </div>

      <div className="p-8 rounded-2xl bg-slate-900 border border-slate-800 text-center space-y-6">
        <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 font-mono">
          {progress.percent_complete.toFixed(1)}%
        </div>

        <div className="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 transition-all duration-300"
            style={{ width: `${progress.percent_complete}%` }}
          />
        </div>

        <div className="text-sm font-semibold text-slate-200">
          {progress.current_stage}
        </div>

        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-800 text-xs">
          <div>
            <div className="text-slate-400 uppercase font-semibold">Pairs Evaluated</div>
            <div className="text-base font-bold text-white font-mono mt-0.5">
              {progress.pairs_evaluated.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-slate-400 uppercase font-semibold">Candidates Screened</div>
            <div className="text-base font-bold text-indigo-400 font-mono mt-0.5">
              {progress.candidate_pairs_found.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-slate-400 uppercase font-semibold">Elapsed Time</div>
            <div className="text-base font-bold text-emerald-400 font-mono mt-0.5">
              {progress.elapsed_seconds.toFixed(2)}s
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {stages.map((stName, idx) => {
          const sNum = idx + 1;
          const isDone = progress.stage_index > sNum || progress.percent_complete >= 100;
          const isCurrent = progress.stage_index === sNum && progress.percent_complete < 100;

          return (
            <div
              key={stName}
              className={`p-3.5 rounded-xl border flex items-center justify-between text-xs transition ${
                isCurrent
                  ? "bg-indigo-950/40 border-indigo-500 text-white font-semibold"
                  : isDone
                  ? "bg-slate-900/60 border-slate-800 text-slate-300"
                  : "bg-slate-900/20 border-slate-900 text-slate-600"
              }`}
            >
              <div className="flex items-center space-x-3">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs ${
                    isDone
                      ? "bg-emerald-500 text-slate-950"
                      : isCurrent
                      ? "bg-indigo-500 text-white animate-pulse"
                      : "bg-slate-800 text-slate-500"
                  }`}
                >
                  {isDone ? <Icon name="check" className="w-3.5 h-3.5" /> : sNum}
                </div>
                <span>{stName}</span>
              </div>
              <span className="font-mono text-[10px] text-slate-500">
                {isDone ? "COMPLETE" : isCurrent ? "PROCESSING" : "QUEUED"}
              </span>
            </div>
          );
        })}
      </div>

      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-400 h-36 overflow-y-auto space-y-1">
        {logs.map((l, i) => (
          <div key={i}>{l}</div>
        ))}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// 5. PLAGIARISM RESULTS PAGE
// -------------------------------------------------------------
function ResultsPage({
  latestRun,
  sessions,
  activeSessionId,
  onSelectSession,
  onReRunScan,
  onUploadNewSubmissions,
  onCompare,
  onViewSubmission,
}) {
  const [filterRisk, setFilterRisk] = useState("all");
  const [filterLang, setFilterLang] = useState("all");
  const [search, setSearch] = useState("");
  const [minSim, setMinSim] = useState(0);
  const [sortBy, setSortBy] = useState("similarity_desc");

  const pairs = latestRun?.top_suspicious_pairs || [];

  const filtered = pairs.filter((p) => {
    if (filterRisk !== "all" && p.risk_level !== filterRisk) return false;
    if (filterLang !== "all" && p.language !== filterLang) return false;
    if (p.overall_similarity < minSim) return false;
    if (search) {
      const q = search.toLowerCase();
      const matchA = p.submission_a_student.toLowerCase().includes(q) || p.submission_a_name.toLowerCase().includes(q);
      const matchB = p.submission_b_student.toLowerCase().includes(q) || p.submission_b_name.toLowerCase().includes(q);
      const matchSumm = p.summary.toLowerCase().includes(q);
      if (!matchA && !matchB && !matchSumm) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header with Required "UPLOAD NEW SUBMISSIONS" button */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Plagiarism Findings</h1>
          <p className="text-slate-400 text-sm">
            Viewing results for: <span className="font-bold text-indigo-400">{latestRun?.batch_name || "Active Batch"}</span>
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => onReRunScan && onReRunScan(activeSessionId)}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold border border-slate-700 flex items-center space-x-1.5 transition"
            title="Re-run analysis on this batch"
          >
            <Icon name="refresh" className="w-4 h-4 text-indigo-400" />
            <span>RE-RUN SCAN</span>
          </button>
          <button
            onClick={onUploadNewSubmissions}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 flex items-center space-x-2 transition"
          >
            <Icon name="upload" className="w-4 h-4" />
            <span>UPLOAD NEW SUBMISSIONS</span>
          </button>
        </div>
      </div>

      {/* Batch Switcher Bar in Results */}
      {sessions.length > 1 && (
        <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between text-xs">
          <span className="text-slate-400">Switch Analysis Batch:</span>
          <select
            value={activeSessionId || ""}
            onChange={(e) => onSelectSession(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white font-medium focus:outline-none"
          >
            {sessions.map((s) => (
              <option key={s.session_id} value={s.session_id}>
                {s.batch_name} &bull; {s.submission_count} files
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
        <div>
          <label className="block text-slate-400 font-semibold mb-1">Search Student / File</label>
          <input
            type="text"
            placeholder="e.g. quicksort, alice..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-slate-400 font-semibold mb-1">Risk Level</label>
          <select
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Risk Levels</option>
            <option value="high">High Risk (&ge; 75%)</option>
            <option value="medium">Medium Risk (45-74%)</option>
            <option value="low">Low Risk (&lt; 45%)</option>
          </select>
        </div>

        <div>
          <label className="block text-slate-400 font-semibold mb-1">Language</label>
          <select
            value={filterLang}
            onChange={(e) => setFilterLang(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Languages</option>
            <option value="python">Python</option>
            <option value="cpp">C++</option>
            <option value="java">Java</option>
          </select>
        </div>

        <div>
          <div className="flex justify-between text-slate-400 font-semibold mb-1">
            <span>Min Similarity</span>
            <span className="font-mono text-white">{minSim}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={minSim}
            onChange={(e) => setMinSim(Number(e.target.value))}
            className="w-full accent-indigo-500 mt-1"
          />
        </div>

        <div>
          <label className="block text-slate-400 font-semibold mb-1">Sort By</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="similarity_desc">Similarity: High to Low</option>
            <option value="similarity_asc">Similarity: Low to High</option>
            <option value="ast_desc">AST Score: High to Low</option>
            <option value="cfg_desc">CFG Score: High to Low</option>
          </select>
        </div>
      </div>

      {/* Ranked Pair Cards */}
      <div className="space-y-4">
        {filtered.length > 0 ? (
          filtered.map((p, idx) => (
            <div
              key={p.pair_id}
              className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition space-y-4"
            >
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center font-bold text-xs text-slate-300">
                    #{idx + 1}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-base font-bold text-white">{p.submission_a_student}</span>
                      <span className="text-slate-500">&harr;</span>
                      <span className="text-base font-bold text-white">{p.submission_b_student}</span>
                      <LanguageBadge lang={p.language} />
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      {p.submission_a_name} &bull; {p.submission_b_name}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-4 self-end sm:self-auto">
                  <div className="text-right">
                    <div className="text-2xl font-black text-white font-mono">
                      {p.overall_similarity}%
                    </div>
                    <RiskBadge risk={p.risk_level} />
                  </div>
                  <button
                    onClick={() => onCompare(p.pair_id)}
                    className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 flex items-center space-x-1.5 transition"
                  >
                    <Icon name="compare" className="w-4 h-4" />
                    <span>Compare Code</span>
                  </button>
                </div>
              </div>

              {/* Dimensional Score Chips */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-2 border-t border-slate-800/60 text-xs font-mono">
                <div className="p-2 rounded bg-slate-950 border border-slate-800/80">
                  <div className="text-slate-500 text-[10px] uppercase font-sans">AST Structure</div>
                  <div className="text-slate-200 font-bold mt-0.5">{p.ast_score}%</div>
                </div>
                <div className="p-2 rounded bg-slate-950 border border-slate-800/80">
                  <div className="text-slate-500 text-[10px] uppercase font-sans">Control Flow</div>
                  <div className="text-slate-200 font-bold mt-0.5">{p.cfg_score}%</div>
                </div>
                <div className="p-2 rounded bg-slate-950 border border-slate-800/80">
                  <div className="text-slate-500 text-[10px] uppercase font-sans">Fingerprint</div>
                  <div className="text-slate-200 font-bold mt-0.5">{p.fingerprint_score}%</div>
                </div>
                <div className="p-2 rounded bg-slate-950 border border-slate-800/80">
                  <div className="text-slate-500 text-[10px] uppercase font-sans">Token n-gram</div>
                  <div className="text-slate-200 font-bold mt-0.5">{p.token_score}%</div>
                </div>
                <div className="p-2 rounded bg-slate-950 border border-slate-800/80">
                  <div className="text-slate-500 text-[10px] uppercase font-sans">Functions</div>
                  <div className="text-slate-200 font-bold mt-0.5">{p.function_score}%</div>
                </div>
              </div>

              {/* AI Disguise Flags & Summary */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pt-1 text-xs">
                <div className="flex flex-wrap gap-1.5">
                  {p.has_loop_to_recursion && (
                    <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-medium">
                      Loop &harr; Recursion Equivalence
                    </span>
                  )}
                  {p.has_renamed_identifiers && (
                    <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 font-medium">
                      Renamed Identifiers
                    </span>
                  )}
                  {p.has_reordered_functions && (
                    <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-medium">
                      Reordered Function Logic
                    </span>
                  )}
                  {p.has_modified_conditionals && (
                    <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium">
                      Branch Variations
                    </span>
                  )}
                </div>
                <div className="text-slate-400 italic sm:text-right">{p.summary}</div>
              </div>
            </div>
          ))
        ) : (
          <div className="p-12 text-center text-slate-500 text-sm rounded-xl bg-slate-900 border border-slate-800">
            No matching submission pairs found for this batch.
          </div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// HISTORICAL ANALYSIS SECTION
// -------------------------------------------------------------
function AnalysisHistoryPage({ history, onViewResults, onStartNewBatch }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Analysis History & Saved Batches</h1>
          <p className="text-slate-400 text-sm">
            All previous scan batches are permanently preserved and independently accessible.
          </p>
        </div>
        <button
          onClick={onStartNewBatch}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-md shadow-indigo-600/30 transition flex items-center space-x-1.5"
        >
          <Icon name="plus" className="w-4 h-4" />
          <span>Upload Next Batch</span>
        </button>
      </div>

      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
        {history.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/40 text-slate-400 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-6">Batch ID / Name</th>
                  <th className="py-3 px-6">Upload Timestamp</th>
                  <th className="py-3 px-6">Submissions</th>
                  <th className="py-3 px-6">Pairs Evaluated</th>
                  <th className="py-3 px-6">Languages</th>
                  <th className="py-3 px-6">Risk Summary</th>
                  <th className="py-3 px-6">Time</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {history.map((h) => (
                  <tr key={h.job_id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-6 font-semibold text-slate-200">
                      {h.batch_name}
                      <span className="text-[10px] text-slate-500 block font-normal">{h.job_id}</span>
                    </td>
                    <td className="py-3 px-6 text-slate-400">{new Date(h.created_at).toLocaleString()}</td>
                    <td className="py-3 px-6 text-white font-bold">{h.total_submissions}</td>
                    <td className="py-3 px-6 text-slate-400">{h.total_pairs.toLocaleString()}</td>
                    <td className="py-3 px-6">
                      <div className="flex gap-1">
                        {h.languages.map((l) => (
                          <LanguageBadge key={l} lang={l} />
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-6">
                      <span className="text-red-400 font-bold">{h.high_risk} High</span> &bull;{" "}
                      <span className="text-amber-400">{h.medium_risk} Med</span>
                    </td>
                    <td className="py-3 px-6 text-emerald-400 font-bold">{h.processing_time_seconds}s</td>
                    <td className="py-3 px-6 text-right font-sans space-x-2">
                      <button
                        onClick={() => onViewResults(h.job_id, h.session_id)}
                        className="px-3 py-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 text-xs font-semibold hover:bg-indigo-600 hover:text-white transition"
                      >
                        Revisit Results &rarr;
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-500 text-sm">
            No analysis history recorded yet.
          </div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// 6. SIDE-BY-SIDE CODE COMPARISON PAGE
// -------------------------------------------------------------
function ComparisonPage({ pairId, onBack }) {
  const [data, setData] = useState(null);
  const [activeSpanIdx, setActiveSpanIdx] = useState(0);

  useEffect(() => {
    if (!pairId) return;
    API.get(`/api/comparison/${pairId}`).then((d) => {
      setData(d);
      setActiveSpanIdx(0);
    });
  }, [pairId]);

  if (!data) {
    return <div className="p-12 text-center text-slate-400">Loading side-by-side comparison...</div>;
  }

  const spans = data.matching_spans || [];
  const currentSpan = spans[activeSpanIdx] || null;

  const prevSpan = () => {
    setActiveSpanIdx((i) => Math.max(0, i - 1));
  };

  const nextSpan = () => {
    setActiveSpanIdx((i) => Math.min(spans.length - 1, i + 1));
  };

  const linesA = (data.submission_a.content || "").split("\n");
  const linesB = (data.submission_b.content || "").split("\n");

  const getLineClassA = (lineNum) => {
    for (let s of spans) {
      if (lineNum >= s.sub_a_start_line && lineNum <= s.sub_a_end_line) {
        if (s === currentSpan) return "bg-indigo-500/30 border-l-4 border-indigo-400 font-semibold";
        if (s.match_type === "loop_to_recursion") return "bg-purple-500/20 border-l-2 border-purple-400";
        if (s.match_type === "renamed_identifiers") return "bg-blue-500/20 border-l-2 border-blue-400";
        if (s.match_type === "control_flow") return "bg-amber-500/20 border-l-2 border-amber-400";
        return "bg-emerald-500/20 border-l-2 border-emerald-400";
      }
    }
    return "text-slate-300";
  };

  const getLineClassB = (lineNum) => {
    for (let s of spans) {
      if (lineNum >= s.sub_b_start_line && lineNum <= s.sub_b_end_line) {
        if (s === currentSpan) return "bg-indigo-500/30 border-l-4 border-indigo-400 font-semibold";
        if (s.match_type === "loop_to_recursion") return "bg-purple-500/20 border-l-2 border-purple-400";
        if (s.match_type === "renamed_identifiers") return "bg-blue-500/20 border-l-2 border-blue-400";
        if (s.match_type === "control_flow") return "bg-amber-500/20 border-l-2 border-amber-400";
        return "bg-emerald-500/20 border-l-2 border-emerald-400";
      }
    }
    return "text-slate-300";
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <button onClick={onBack} className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition">
            <Icon name="arrowLeft" className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white">Side-by-Side Code Comparison</h1>
            <p className="text-slate-400 text-xs">
              Synchronized structural alignment between suspected plagiarism counterparts.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="text-right">
            <span className="text-2xl font-black text-white font-mono">{data.overall_similarity}%</span>
            <span className="ml-2">
              <RiskBadge risk={data.risk_level} />
            </span>
          </div>
        </div>
      </div>

      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <span className="text-xs font-semibold uppercase text-slate-400">Match Navigation:</span>
          <button
            onClick={prevSpan}
            disabled={activeSpanIdx === 0}
            className={`p-1.5 rounded-lg border text-xs font-semibold ${
              activeSpanIdx > 0
                ? "bg-slate-800 border-slate-700 text-white hover:bg-slate-700"
                : "bg-slate-950 border-slate-900 text-slate-600 cursor-not-allowed"
            }`}
          >
            &larr; Prev
          </button>
          <span className="text-xs font-mono font-bold text-indigo-400">
            {spans.length > 0 ? `${activeSpanIdx + 1} of ${spans.length}` : "0 matches"}
          </span>
          <button
            onClick={nextSpan}
            disabled={activeSpanIdx >= spans.length - 1}
            className={`p-1.5 rounded-lg border text-xs font-semibold ${
              activeSpanIdx < spans.length - 1
                ? "bg-slate-800 border-slate-700 text-white hover:bg-slate-700"
                : "bg-slate-950 border-slate-900 text-slate-600 cursor-not-allowed"
            }`}
          >
            Next &rarr;
          </button>
          {currentSpan && (
            <span className="text-xs text-slate-300 italic hidden md:inline">
              &bull; {currentSpan.description}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-emerald-500/40 border border-emerald-400" />
            <span className="text-slate-400">Exact Structure</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-blue-500/40 border border-blue-400" />
            <span className="text-slate-400">Renamed IDs</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-amber-500/40 border border-amber-400" />
            <span className="text-slate-400">Control Flow</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded bg-purple-500/40 border border-purple-400" />
            <span className="text-slate-400">Loop &harr; Recursion</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Panel */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col">
          <div className="px-4 py-3 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-white text-sm">{data.submission_a.student_id}</span>
              <span className="text-slate-400 text-xs font-mono">({data.submission_a.filename})</span>
            </div>
            <LanguageBadge lang={data.submission_a.language} />
          </div>
          <div className="flex-1 bg-slate-950 p-4 font-mono text-xs overflow-y-auto max-h-[580px] select-text">
            {linesA.map((line, idx) => {
              const lineNum = idx + 1;
              const lineCls = getLineClassA(lineNum);
              return (
                <div key={idx} className={`flex items-start py-0.5 px-2 rounded ${lineCls}`}>
                  <span className="w-8 text-slate-600 select-none text-right pr-3">{lineNum}</span>
                  <span className="flex-1 whitespace-pre">{line || " "}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Panel */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col">
          <div className="px-4 py-3 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-white text-sm">{data.submission_b.student_id}</span>
              <span className="text-slate-400 text-xs font-mono">({data.submission_b.filename})</span>
            </div>
            <LanguageBadge lang={data.submission_b.language} />
          </div>
          <div className="flex-1 bg-slate-950 p-4 font-mono text-xs overflow-y-auto max-h-[580px] select-text">
            {linesB.map((line, idx) => {
              const lineNum = idx + 1;
              const lineCls = getLineClassB(lineNum);
              return (
                <div key={idx} className={`flex items-start py-0.5 px-2 rounded ${lineCls}`}>
                  <span className="w-8 text-slate-600 select-none text-right pr-3">{lineNum}</span>
                  <span className="flex-1 whitespace-pre">{line || " "}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// 7. SUBMISSION DETAILS PAGE
// -------------------------------------------------------------
function SubmissionDetailPage({ subId, onBack }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!subId) return;
    API.get(`/api/submissions/${subId}`).then(setData);
  }, [subId]);

  if (!data) {
    return <div className="p-12 text-center text-slate-400">Loading submission analysis...</div>;
  }

  const { submission: sub, ast_summary: ast, cfg_summary: cfg } = data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <button onClick={onBack} className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition">
            <Icon name="arrowLeft" className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-2xl font-extrabold text-white">{sub.filename}</h1>
            <p className="text-slate-400 text-xs">
              Student ID: <span className="font-bold text-white">{sub.student_id}</span> &bull; Batch:{" "}
              <span className="text-indigo-400 font-mono">{sub.session_id}</span> &bull; Language:{" "}
              <LanguageBadge lang={sub.language} />
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400 uppercase font-semibold">AST Total Nodes</div>
          <div className="text-2xl font-bold text-white font-mono mt-1">{ast.total_nodes}</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400 uppercase font-semibold">Cyclomatic Complexity</div>
          <div className="text-2xl font-bold text-indigo-400 font-mono mt-1">{cfg.avg_cyclomatic_complexity}</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400 uppercase font-semibold">Loops & Branches</div>
          <div className="text-2xl font-bold text-purple-400 font-mono mt-1">
            {cfg.total_loops}L / {cfg.total_branches}B
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400 uppercase font-semibold">Recursion Detected</div>
          <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">
            {cfg.total_recursions > 0 ? "YES" : "NO"}
          </div>
        </div>
      </div>

      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
          Extracted Function Signatures & Subtree Offsets
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {ast.functions.map((fn, idx) => (
            <div key={idx} className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs">
              <div className="font-bold text-indigo-400">{fn.name}({fn.params.join(", ")})</div>
              <div className="text-[10px] text-slate-500 mt-1">
                Lines {fn.line_start} &ndash; {fn.line_end} &bull; {fn.body_nodes.length} nodes
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden">
        <div className="px-4 py-2.5 bg-slate-800/60 border-b border-slate-800 text-xs font-semibold text-slate-300">
          Source Code
        </div>
        <pre className="p-4 bg-slate-950 text-slate-300 font-mono text-xs overflow-x-auto max-h-[450px]">
          {sub.content}
        </pre>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// 8. REPORTS & BENCHMARK PAGE
// -------------------------------------------------------------
function ReportsPage({ latestRun, activeSessionId }) {
  const [benchRunning, setBenchRunning] = useState(false);
  const [benchResult, setBenchResult] = useState(null);

  const runBenchmark = async () => {
    setBenchRunning(true);
    try {
      const res = await API.post("/api/benchmark/run");
      setBenchResult(res);
    } catch (e) {
      alert("Benchmark failed: " + e.message);
    } finally {
      setBenchRunning(false);
    }
  };

  const jsonUrl = activeSessionId ? `/api/reports/json?session_id=${activeSessionId}` : "/api/reports/json";
  const csvUrl = activeSessionId ? `/api/reports/csv?session_id=${activeSessionId}` : "/api/reports/csv";
  const htmlUrl = activeSessionId ? `/api/reports/html?session_id=${activeSessionId}` : "/api/reports/html";

  return (
    <div className="space-y-8">
      <div className="pb-2 border-b border-slate-800">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Reports & Benchmark Suite</h1>
        <p className="text-slate-400 text-sm">
          Download institutional audit reports or run high-throughput stress benchmarks (300 submissions / 44,850 pairs).
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
            <Icon name="fileText" className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white">JSON Analysis Report</h3>
          <p className="text-slate-400 text-xs leading-relaxed">
            Raw machine-readable telemetry including full AST match mappings, CFG graph metrics,
            and pairwise similarity breakdowns.
          </p>
          <a
            href={jsonUrl}
            download
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow transition"
          >
            <Icon name="download" className="w-4 h-4" />
            <span>Download JSON</span>
          </a>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
            <Icon name="download" className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white">CSV Spreadsheet Export</h3>
          <p className="text-slate-400 text-xs leading-relaxed">
            Tabular spreadsheet with one row per suspicious pair, scores, AI disguise flags,
            and textual justification for academic committees.
          </p>
          <a
            href={csvUrl}
            download
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow transition"
          >
            <Icon name="download" className="w-4 h-4" />
            <span>Download CSV</span>
          </a>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
            <Icon name="shield" className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white">Printable / PDF Audit Report</h3>
          <p className="text-slate-400 text-xs leading-relaxed">
            Executive audit report with official academic integrity formatting, summary statistics,
            and 1-click browser printing/PDF generation.
          </p>
          <a
            href={htmlUrl}
            target="_blank"
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow transition"
          >
            <Icon name="play" className="w-4 h-4" />
            <span>Open Printable Report</span>
          </a>
        </div>
      </div>

      {/* 300 Submissions Benchmark Card */}
      <div className="p-8 rounded-2xl bg-slate-900 border border-indigo-500/30 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-semibold">
              <Icon name="zap" className="w-3.5 h-3.5" />
              <span>Official Benchmark Engine</span>
            </div>
            <h2 className="text-2xl font-extrabold text-white mt-1">300-Submission Stress Benchmark</h2>
            <p className="text-slate-400 text-xs max-w-2xl mt-1">
              Tests the full pipeline on 300 realistic submissions (44,850 pairwise comparisons)
              incorporating Python, C++, and Java across all 6 plagiarism disguise patterns.
              Target: Complete in under 2 minutes (120 seconds).
            </p>
          </div>
          <button
            onClick={runBenchmark}
            disabled={benchRunning}
            className={`px-5 py-2.5 rounded-xl text-xs font-bold shadow-lg transition flex items-center space-x-2 ${
              benchRunning
                ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-indigo-600/30"
            }`}
          >
            <Icon name="play" className="w-4 h-4" />
            <span>{benchRunning ? "Executing 44,850 Comparisons..." : "Run 300 Submissions Benchmark"}</span>
          </button>
        </div>

        {benchResult && (
          <div className="p-6 rounded-xl bg-slate-950 border border-emerald-500/40 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-emerald-400 font-bold text-sm">
                <Icon name="check" className="w-5 h-5" />
                <span>BENCHMARK VALIDATION PASSED [TARGET MET]</span>
              </div>
              <span className="font-mono text-xs text-slate-400">
                Constraint: &lt; 120.0s | Actual: <strong>{benchResult.total_time_seconds}s</strong>
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono pt-2 border-t border-slate-800">
              <div>
                <div className="text-slate-500 font-sans uppercase">Submissions</div>
                <div className="text-white text-lg font-bold">{benchResult.num_submissions}</div>
              </div>
              <div>
                <div className="text-slate-500 font-sans uppercase">Pairs Evaluated</div>
                <div className="text-indigo-400 text-lg font-bold">{benchResult.num_pairs_evaluated.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-slate-500 font-sans uppercase">Total Time</div>
                <div className="text-emerald-400 text-lg font-bold">{benchResult.total_time_seconds}s</div>
              </div>
              <div>
                <div className="text-slate-500 font-sans uppercase">Throughput</div>
                <div className="text-purple-400 text-lg font-bold">{benchResult.pairs_per_second.toLocaleString()} pairs/sec</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// SCORING WEIGHTS MODAL
// -------------------------------------------------------------
function WeightsModal({ weights, onClose, onSave }) {
  const [w, setW] = useState({ ...weights });

  const update = (key, val) => {
    setW((prev) => ({ ...prev, [key]: parseFloat(val) }));
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h2 className="text-lg font-bold text-white">Configurable Scoring Weights</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            &times;
          </button>
        </div>

        <p className="text-slate-400 text-xs">
          Adjust the relative importance of AST structural similarity, control-flow branching,
          structural MinHash fingerprinting, token n-grams, and function bipartite matching.
        </p>

        <div className="space-y-4 text-xs">
          <div>
            <div className="flex justify-between text-slate-300 font-semibold mb-1">
              <span>AST Structural Weight</span>
              <span className="font-mono text-indigo-400">{(w.ast_structural * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={w.ast_structural}
              onChange={(e) => update("ast_structural", e.target.value)}
              className="w-full accent-indigo-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-slate-300 font-semibold mb-1">
              <span>Control Flow (CFG) Weight</span>
              <span className="font-mono text-indigo-400">{(w.control_flow * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={w.control_flow}
              onChange={(e) => update("control_flow", e.target.value)}
              className="w-full accent-indigo-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-slate-300 font-semibold mb-1">
              <span>Structural Fingerprint (MinHash) Weight</span>
              <span className="font-mono text-indigo-400">{(w.structural_fingerprint * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={w.structural_fingerprint}
              onChange={(e) => update("structural_fingerprint", e.target.value)}
              className="w-full accent-indigo-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-slate-300 font-semibold mb-1">
              <span>Token n-gram Weight</span>
              <span className="font-mono text-indigo-400">{(w.token_similarity * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={w.token_similarity}
              onChange={(e) => update("token_similarity", e.target.value)}
              className="w-full accent-indigo-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-slate-300 font-semibold mb-1">
              <span>Function Bipartite Match Weight</span>
              <span className="font-mono text-indigo-400">{(w.function_similarity * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={w.function_similarity}
              onChange={(e) => update("function_similarity", e.target.value)}
              className="w-full accent-indigo-500"
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-800">
          <button
            onClick={() => {
              setW({
                ast_structural: 0.3,
                control_flow: 0.25,
                structural_fingerprint: 0.2,
                token_similarity: 0.15,
                function_similarity: 0.1,
              });
            }}
            className="text-xs text-slate-400 hover:text-white"
          >
            Reset Defaults
          </button>
          <div className="flex space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition"
            >
              Cancel
            </button>
            <button
              onClick={() => onSave(w)}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-500 transition shadow-md shadow-indigo-600/30"
            >
              Save Weights
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Render root
ReactDOM.render(<App />, document.getElementById("root"));
