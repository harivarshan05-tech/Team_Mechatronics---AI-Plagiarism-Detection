"""
Stage 3: Control Flow Analysis (CFG) Engine.
- Extracts Basic Blocks and Control Flow Edges
- Calculates Cyclomatic Complexity (M = E - N + 2P)
- Detects loops, branches, nested conditionals, and recursive patterns
- Identifies Loop-to-Recursion Transformations
"""

import ast
import re
from typing import List, Dict, Set, Tuple, Optional, Any
from app.models import Language


class BasicBlock:
    def __init__(self, block_id: int, block_type: str, statements: List[str], line_range: Tuple[int, int]):
        self.block_id = block_id
        self.block_type = block_type  # ENTRY, LOOP, CONDITIONAL, BODY, EXIT
        self.statements = statements
        self.line_range = line_range
        self.successors: List[int] = []


class CFGGraph:
    def __init__(self, function_name: str):
        self.function_name = function_name
        self.blocks: Dict[int, BasicBlock] = {}
        self.num_edges: int = 0
        self.loop_count: int = 0
        self.branch_count: int = 0
        self.has_recursion: bool = False
        self.recursive_call_count: int = 0
        self.cyclomatic_complexity: int = 1


class CFGAnalysisResult:
    def __init__(
        self,
        cfgs: List[CFGGraph],
        total_loops: int,
        total_branches: int,
        total_recursions: int,
        avg_cyclomatic_complexity: float,
        cfg_topological_hash: str,
    ):
        self.cfgs = cfgs
        self.total_loops = total_loops
        self.total_branches = total_branches
        self.total_recursions = total_recursions
        self.avg_cyclomatic_complexity = avg_cyclomatic_complexity
        self.cfg_topological_hash = cfg_topological_hash


def build_python_cfgs(source: str) -> List[CFGGraph]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return build_generic_cfgs(source, Language.PYTHON)

    cfgs: List[CFGGraph] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cfg = CFGGraph(node.name)
            block_id = 0

            # Entry block
            entry = BasicBlock(block_id, "ENTRY", [f"def {node.name}"], (node.lineno, node.lineno))
            cfg.blocks[block_id] = entry
            prev_id = block_id

            edges = 0
            loops = 0
            branches = 0
            rec_calls = 0

            for stmt in node.body:
                block_id += 1
                s_name = type(stmt).__name__
                s_lineno = getattr(stmt, "lineno", node.lineno)
                e_lineno = getattr(stmt, "end_lineno", s_lineno)

                if isinstance(stmt, (ast.For, ast.While)):
                    loops += 1
                    b = BasicBlock(block_id, "LOOP", [s_name], (s_lineno, e_lineno))
                    cfg.blocks[block_id] = b
                    cfg.blocks[prev_id].successors.append(block_id)
                    # Loop body edge and back-edge
                    edges += 2
                    prev_id = block_id
                elif isinstance(stmt, ast.If):
                    branches += 1
                    b = BasicBlock(block_id, "CONDITIONAL", [s_name], (s_lineno, e_lineno))
                    cfg.blocks[block_id] = b
                    cfg.blocks[prev_id].successors.append(block_id)
                    # True and False branches
                    edges += 2
                    prev_id = block_id
                else:
                    b = BasicBlock(block_id, "BODY", [s_name], (s_lineno, e_lineno))
                    cfg.blocks[block_id] = b
                    cfg.blocks[prev_id].successors.append(block_id)
                    edges += 1
                    prev_id = block_id

                # Check for recursive calls
                for inner in ast.walk(stmt):
                    if isinstance(inner, ast.Call):
                        if isinstance(inner.func, ast.Name) and inner.func.id == node.name:
                            rec_calls += 1

            # Exit block
            block_id += 1
            exit_block = BasicBlock(block_id, "EXIT", ["return"], (e_lineno, e_lineno))
            cfg.blocks[block_id] = exit_block
            cfg.blocks[prev_id].successors.append(block_id)
            edges += 1

            cfg.num_edges = edges
            cfg.loop_count = loops
            cfg.branch_count = branches
            cfg.has_recursion = rec_calls > 0
            cfg.recursive_call_count = rec_calls

            # Cyclomatic complexity: M = E - N + 2P where P = 1
            num_nodes = len(cfg.blocks)
            cfg.cyclomatic_complexity = max(1, edges - num_nodes + 2)
            cfgs.append(cfg)

    # If no functions found (e.g. script level code)
    if not cfgs:
        cfg = CFGGraph("main_script")
        loops = len(re.findall(r'\b(for|while)\b', source))
        branches = len(re.findall(r'\b(if|elif)\b', source))
        cfg.loop_count = loops
        cfg.branch_count = branches
        cfg.cyclomatic_complexity = 1 + branches + loops
        cfgs.append(cfg)

    return cfgs


def build_generic_cfgs(source: str, language: Language) -> List[CFGGraph]:
    """
    CFG extractor for C++, Java, or syntax-broken Python.
    """
    cfgs: List[CFGGraph] = []
    lines = source.splitlines()

    func_re = re.compile(
        r'^\s*(?:(?:public|private|protected|static|final|inline|virtual)\s+)*'
        r'[\w<>\[\]]+\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{?'
    )

    current_func: Optional[str] = None
    func_lines: List[str] = []
    brace_count = 0

    for line in lines:
        m = func_re.match(line)
        if m and "{" in line and m.group(1) not in ("if", "for", "while", "switch"):
            if current_func and func_lines:
                cfgs.append(_analyze_function_lines(current_func, func_lines))
            current_func = m.group(1)
            func_lines = [line]
            brace_count = line.count("{") - line.count("}")
        elif current_func:
            func_lines.append(line)
            brace_count += line.count("{") - line.count("}")
            if brace_count <= 0 and "}" in line:
                cfgs.append(_analyze_function_lines(current_func, func_lines))
                current_func = None
                func_lines = []

    if current_func and func_lines:
        cfgs.append(_analyze_function_lines(current_func, func_lines))

    if not cfgs:
        cfgs.append(_analyze_function_lines("global", lines))

    return cfgs


def _analyze_function_lines(func_name: str, lines: List[str]) -> CFGGraph:
    cfg = CFGGraph(func_name)
    body = "\n".join(lines)

    loops = len(re.findall(r'\b(for|while|do)\b', body))
    branches = len(re.findall(r'\b(if|else if|switch|case)\b', body))

    # Detect recursive calls to func_name
    rec_pattern = rf'\b{re.escape(func_name)}\s*\('
    rec_matches = len(re.findall(rec_pattern, body)) - 1  # minus definition itself
    rec_calls = max(0, rec_matches)

    cfg.loop_count = loops
    cfg.branch_count = branches
    cfg.has_recursion = rec_calls > 0
    cfg.recursive_call_count = rec_calls
    cfg.cyclomatic_complexity = 1 + branches + loops
    return cfg


def analyze_control_flow(source: str, language: Language) -> CFGAnalysisResult:
    if language == Language.PYTHON:
        cfgs = build_python_cfgs(source)
    else:
        cfgs = build_generic_cfgs(source, language)

    total_loops = sum(c.loop_count for c in cfgs)
    total_branches = sum(c.branch_count for c in cfgs)
    total_recursions = sum(c.recursive_call_count for c in cfgs)
    avg_complexity = (
        sum(c.cyclomatic_complexity for c in cfgs) / len(cfgs) if cfgs else 1.0
    )

    topological_tokens = [
        f"{c.loop_count}L_{c.branch_count}B_{int(c.has_recursion)}R_{c.cyclomatic_complexity}C"
        for c in cfgs
    ]
    topological_hash = ":".join(sorted(topological_tokens))

    return CFGAnalysisResult(
        cfgs=cfgs,
        total_loops=total_loops,
        total_branches=total_branches,
        total_recursions=total_recursions,
        avg_cyclomatic_complexity=avg_complexity,
        cfg_topological_hash=topological_hash,
    )


def detect_loop_to_recursion_equivalence(
    cfg_a: CFGAnalysisResult,
    cfg_b: CFGAnalysisResult,
    clean_code_a: str,
    clean_code_b: str,
) -> Tuple[bool, float]:
    """
    Identifies loop-to-recursion transformations at both function-level and module-level.
    Returns: (is_loop_to_recursion, confidence_0_to_1)
    """
    # 1. Check function-by-function
    for fa in cfg_a.cfgs:
        for fb in cfg_b.cfgs:
            fa_is_loop = fa.loop_count > 0 and not fa.has_recursion
            fb_is_rec = fb.has_recursion and fb.loop_count == 0

            fb_is_loop = fb.loop_count > 0 and not fb.has_recursion
            fa_is_rec = fa.has_recursion and fa.loop_count == 0

            if (fa_is_loop and fb_is_rec) or (fb_is_loop and fa_is_rec):
                # Verify complexity delta and operator overlap
                delta = abs(fa.cyclomatic_complexity - fb.cyclomatic_complexity)
                if delta <= 3:
                    return True, 0.90

    # 2. Check aggregate program metrics fallback
    has_loop_a = cfg_a.total_loops > 0 and cfg_a.total_recursions == 0
    has_rec_b = cfg_b.total_recursions > 0 and cfg_b.total_loops == 0

    has_loop_b = cfg_b.total_loops > 0 and cfg_b.total_recursions == 0
    has_rec_a = cfg_a.total_recursions > 0 and cfg_a.total_loops == 0

    if (has_loop_a and has_rec_b) or (has_loop_b and has_rec_a):
        tokens_a = set(re.findall(r'[+\-*/%=<>!&|^]+', clean_code_a))
        tokens_b = set(re.findall(r'[+\-*/%=<>!&|^]+', clean_code_b))
        inter = len(tokens_a.intersection(tokens_b))
        union = len(tokens_a.union(tokens_b))
        op_similarity = inter / union if union > 0 else 0.0
        if op_similarity >= 0.4:
            return True, max(0.85, round(0.6 + 0.35 * op_similarity, 2))

    return False, 0.0


def compute_cfg_similarity(
    cfg_a: CFGAnalysisResult,
    cfg_b: CFGAnalysisResult,
    clean_code_a: str,
    clean_code_b: str,
) -> Tuple[float, bool]:
    """
    Computes CFG structural similarity.
    Returns: (cfg_score_0_to_1, has_loop_to_recursion)
    """
    is_l2r, l2r_conf = detect_loop_to_recursion_equivalence(
        cfg_a, cfg_b, clean_code_a, clean_code_b
    )

    if is_l2r:
        # Loop-to-recursion detected! Reward equivalent execution semantics
        return max(0.85, l2r_conf), True

    # Standard CFG metric distance
    max_loops = max(cfg_a.total_loops, cfg_b.total_loops, 1)
    loop_diff = abs(cfg_a.total_loops - cfg_b.total_loops)
    loop_sim = max(0.0, 1.0 - (loop_diff / max_loops))

    max_branches = max(cfg_a.total_branches, cfg_b.total_branches, 1)
    branch_diff = abs(cfg_a.total_branches - cfg_b.total_branches)
    branch_sim = max(0.0, 1.0 - (branch_diff / max_branches))

    max_cc = max(cfg_a.avg_cyclomatic_complexity, cfg_b.avg_cyclomatic_complexity, 1.0)
    cc_diff = abs(cfg_a.avg_cyclomatic_complexity - cfg_b.avg_cyclomatic_complexity)
    cc_sim = max(0.0, 1.0 - (cc_diff / max_cc))

    # Topological signature equality
    sig_sim = 1.0 if cfg_a.cfg_topological_hash == cfg_b.cfg_topological_hash else 0.0

    composite = 0.35 * loop_sim + 0.35 * branch_sim + 0.20 * cc_sim + 0.10 * sig_sim
    return min(1.0, max(0.0, composite)), False
