"""
Stage 2: Abstract Syntax Tree (AST) Analysis.
- Multi-language AST parsing (Python ast module + structural AST parser for C++/Java)
- Function-level AST decomposition
- Subtree hashing for invariant structural sub-trees
- Bipartite function matching (Hungarian / greedy matching) for function reordering invariance
- Structural statement and expression similarity
"""

import ast
import hashlib
import re
from typing import List, Dict, Set, Tuple, Optional, Any
from app.models import Language


class ASTFunctionNode:
    def __init__(self, name: str, params: List[str], body_types: List[str], line_start: int, line_end: int, tree_hash: str):
        self.name = name
        self.params = params
        self.body_types = body_types
        self.line_start = line_start
        self.line_end = line_end
        self.tree_hash = tree_hash


class ASTAnalysisResult:
    def __init__(
        self,
        node_type_sequence: List[str],
        subtree_hashes: Set[str],
        functions: List[ASTFunctionNode],
        structural_signature: str,
        total_nodes: int,
    ):
        self.node_type_sequence = node_type_sequence
        self.subtree_hashes = subtree_hashes
        self.functions = functions
        self.structural_signature = structural_signature
        self.total_nodes = total_nodes


class PythonASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.node_types: List[str] = []
        self.subtree_hashes: Set[str] = set()
        self.functions: List[ASTFunctionNode] = []
        self.current_func_nodes: List[str] = []
        self.in_function = False

    def visit(self, node):
        node_name = type(node).__name__
        self.node_types.append(node_name)

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            old_in_func = self.in_function
            old_func_nodes = self.current_func_nodes
            self.in_function = True
            self.current_func_nodes = []

            # Process parameters
            params = [a.arg for a in node.args.args]

            # Visit children
            for child in ast.iter_child_nodes(node):
                self.visit(child)

            # Compute subtree hash for function body
            func_sig = f"Func:{':'.join(self.current_func_nodes)}"
            f_hash = hashlib.md5(func_sig.encode()).hexdigest()[:16]

            line_start = getattr(node, "lineno", 1)
            line_end = getattr(node, "end_lineno", line_start)

            self.functions.append(
                ASTFunctionNode(
                    name=node.name,
                    params=params,
                    body_types=self.current_func_nodes,
                    line_start=line_start,
                    line_end=line_end,
                    tree_hash=f_hash,
                )
            )

            self.in_function = old_in_func
            self.current_func_nodes = old_func_nodes
            return

        if self.in_function:
            self.current_func_nodes.append(node_name)

        # Hash compound statements (For, While, If, Try, With)
        if isinstance(node, (ast.For, ast.While, ast.If, ast.Try, ast.With, ast.Assign, ast.Return)):
            child_types = [type(c).__name__ for c in ast.iter_child_nodes(node)]
            sub_sig = f"{node_name}({','.join(child_types)})"
            self.subtree_hashes.add(hashlib.md5(sub_sig.encode()).hexdigest()[:16])

        self.generic_visit(node)


def parse_python_ast(source: str) -> ASTAnalysisResult:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Fallback to structural regex parsing if code has syntax issues
        return parse_generic_ast(source, Language.PYTHON)

    visitor = PythonASTVisitor()
    visitor.visit(tree)

    full_sig = ":".join(visitor.node_types[:200])
    struct_hash = hashlib.md5(full_sig.encode()).hexdigest()[:16]

    return ASTAnalysisResult(
        node_type_sequence=visitor.node_types,
        subtree_hashes=visitor.subtree_hashes,
        functions=visitor.functions,
        structural_signature=struct_hash,
        total_nodes=len(visitor.node_types),
    )


def parse_generic_ast(source: str, language: Language) -> ASTAnalysisResult:
    """
    Structural AST parser for C++, Java, and fallback Python.
    Deconstructs blocks, functions, control flows, and statements.
    """
    lines = source.splitlines()
    node_types: List[str] = []
    subtree_hashes: Set[str] = set()
    functions: List[ASTFunctionNode] = []

    # Regex patterns for function definitions in C++/Java
    func_pattern = re.compile(
        r'^\s*(?:(?:public|private|protected|static|final|inline|virtual|constexpr)\s+)*'
        r'([\w<>\[\]]+)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*(?:const)?\s*(?:throws\s+[\w\s,]+)?\s*\{?'
    )

    current_func: Optional[Dict[str, Any]] = None
    brace_depth = 0

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        # Check for function start
        m = func_pattern.match(line)
        if m and "{" in line or (m and idx < len(lines) and "{" in lines[idx]):
            ret_type, func_name, params = m.groups()
            if func_name not in ("if", "for", "while", "switch", "catch"):
                param_list = [p.strip().split()[-1] for p in params.split(",") if p.strip()]
                current_func = {
                    "name": func_name,
                    "params": param_list,
                    "line_start": idx,
                    "body_nodes": [],
                }
                node_types.append("FunctionDef")

        # Statement type detection
        stmt_type = None
        if re.search(r'\bfor\s*\(', stripped):
            stmt_type = "ForStmt"
        elif re.search(r'\bwhile\s*\(', stripped):
            stmt_type = "WhileStmt"
        elif re.search(r'\bif\s*\(', stripped):
            stmt_type = "IfStmt"
        elif re.search(r'\belse\s+if\s*\(', stripped):
            stmt_type = "ElifStmt"
        elif re.search(r'\belse\b', stripped):
            stmt_type = "ElseStmt"
        elif re.search(r'\bswitch\s*\(', stripped):
            stmt_type = "SwitchStmt"
        elif re.search(r'\breturn\b', stripped):
            stmt_type = "ReturnStmt"
        elif re.search(r'\b(try|catch|finally|throw)\b', stripped):
            stmt_type = "ExceptionStmt"
        elif "=" in stripped and not re.search(r'==|!=|<=|>=', stripped):
            stmt_type = "AssignStmt"
        elif re.search(r'\w+\s*\([^)]*\)\s*;', stripped):
            stmt_type = "CallStmt"

        if stmt_type:
            node_types.append(stmt_type)
            if current_func:
                current_func["body_nodes"].append(stmt_type)
            subtree_hashes.add(hashlib.md5(f"{stmt_type}:{len(stripped)}".encode()).hexdigest()[:16])

        # Track braces for function boundary
        brace_depth += line.count("{") - line.count("}")
        if current_func and brace_depth <= 0 and "}" in line:
            func_sig = f"Func:{':'.join(current_func['body_nodes'])}"
            f_hash = hashlib.md5(func_sig.encode()).hexdigest()[:16]
            functions.append(
                ASTFunctionNode(
                    name=current_func["name"],
                    params=current_func["params"],
                    body_types=current_func["body_nodes"],
                    line_start=current_func["line_start"],
                    line_end=idx,
                    tree_hash=f_hash,
                )
            )
            current_func = None

    if current_func:
        func_sig = f"Func:{':'.join(current_func['body_nodes'])}"
        f_hash = hashlib.md5(func_sig.encode()).hexdigest()[:16]
        functions.append(
            ASTFunctionNode(
                name=current_func["name"],
                params=current_func["params"],
                body_types=current_func["body_nodes"],
                line_start=current_func["line_start"],
                line_end=len(lines),
                tree_hash=f_hash,
            )
        )

    full_sig = ":".join(node_types[:200])
    struct_hash = hashlib.md5(full_sig.encode()).hexdigest()[:16]

    return ASTAnalysisResult(
        node_type_sequence=node_types,
        subtree_hashes=subtree_hashes,
        functions=functions,
        structural_signature=struct_hash,
        total_nodes=len(node_types),
    )


def parse_ast(source: str, language: Language) -> ASTAnalysisResult:
    if language == Language.PYTHON:
        return parse_python_ast(source)
    return parse_generic_ast(source, language)


def compare_functions_bipartite(
    funcs_a: List[ASTFunctionNode], funcs_b: List[ASTFunctionNode]
) -> Tuple[float, bool]:
    """
    Computes optimal function similarity regardless of function ordering.
    Returns (similarity_score_0_to_1, has_reordering).
    """
    if not funcs_a or not funcs_b:
        return 0.0, False

    # Build similarity matrix
    scores: List[List[float]] = []
    for fa in funcs_a:
        row = []
        for fb in funcs_b:
            if fa.tree_hash == fb.tree_hash:
                sim = 1.0
            else:
                # Jaccard over body node types
                set_a = set(fa.body_types)
                set_b = set(fb.body_types)
                if not set_a and not set_b:
                    sim = 0.5
                else:
                    intersection = len(set_a.intersection(set_b))
                    union = len(set_a.union(set_b))
                    sim = intersection / union if union > 0 else 0.0
            row.append(sim)
        scores.append(row)

    # Greedy bipartite matching
    matched_b = set()
    total_matched_sim = 0.0
    matched_pairs = []

    for i, row in enumerate(scores):
        best_sim = -1.0
        best_j = -1
        for j, s in enumerate(row):
            if j not in matched_b and s > best_sim:
                best_sim = s
                best_j = j
        if best_j != -1 and best_sim > 0.3:
            matched_b.add(best_j)
            total_matched_sim += best_sim
            matched_pairs.append((i, best_j))

    max_funcs = max(len(funcs_a), len(funcs_b))
    overall_func_sim = total_matched_sim / max_funcs if max_funcs > 0 else 0.0

    # Detect reordering: if matched indices are not monotonic
    has_reordered = False
    if len(matched_pairs) >= 2:
        for k in range(len(matched_pairs) - 1):
            if matched_pairs[k][1] > matched_pairs[k + 1][1]:
                has_reordered = True
                break

    return overall_func_sim, has_reordered


def compute_ast_similarity(ast_a: ASTAnalysisResult, ast_b: ASTAnalysisResult) -> Tuple[float, float, bool]:
    """
    Computes overall AST similarity.
    Returns: (ast_similarity_0_to_1, function_similarity_0_to_1, has_reordered_functions).
    """
    # 1. Subtree Jaccard
    sub_union = len(ast_a.subtree_hashes.union(ast_b.subtree_hashes))
    sub_inter = len(ast_a.subtree_hashes.intersection(ast_b.subtree_hashes))
    subtree_sim = sub_inter / sub_union if sub_union > 0 else 0.0

    # 2. Sequential node type similarity (Levenshtein / n-gram)
    def to_ngrams(seq: List[str], n: int = 3) -> Set[Tuple[str, ...]]:
        return {tuple(seq[i : i + n]) for i in range(len(seq) - n + 1)} if len(seq) >= n else set()

    ng_a = to_ngrams(ast_a.node_type_sequence, 3)
    ng_b = to_ngrams(ast_b.node_type_sequence, 3)
    ng_union = len(ng_a.union(ng_b))
    ng_inter = len(ng_a.intersection(ng_b))
    seq_sim = ng_inter / ng_union if ng_union > 0 else 0.0

    # 3. Function-level bipartite matching
    func_sim, has_reorder = compare_functions_bipartite(ast_a.functions, ast_b.functions)

    # Combined AST similarity score
    ast_composite = 0.5 * seq_sim + 0.3 * subtree_sim + 0.2 * func_sim
    return min(1.0, ast_composite), min(1.0, func_sim), has_reorder
