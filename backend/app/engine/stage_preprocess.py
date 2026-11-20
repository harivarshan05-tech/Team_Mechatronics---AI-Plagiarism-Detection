"""
Stage 1: Code Preprocessing Engine.
- Comment stripping (Python docstrings/#, C++/Java // and /* */)
- Whitespace and formatting normalization
- Literal value canonicalization (<STR>, <NUM>, <BOOL>)
- Identifier anonymization (mapping custom variables/functions to VAR_x / FUNC_x)
- Source code tokenization
"""

import re
import tokenize
import io
from typing import List, Tuple, Dict, Set
from app.models import Language

COMMON_KEYWORDS = {
    # Control flow & keywords
    "if", "else", "elif", "for", "while", "do", "switch", "case", "default",
    "break", "continue", "return", "yield", "try", "catch", "finally", "except",
    "throw", "raise", "assert", "with", "as", "class", "def", "struct", "enum",
    "public", "private", "protected", "static", "final", "const", "virtual",
    "void", "int", "float", "double", "char", "bool", "boolean", "long", "short",
    "byte", "unsigned", "signed", "new", "delete", "import", "package", "from",
    "lambda", "pass", "global", "nonlocal", "in", "is", "not", "and", "or",
    "True", "False", "None", "true", "false", "null", "nullptr", "this", "super",
    # Standard library / built-in functions
    "print", "println", "printf", "range", "len", "enumerate", "zip", "map",
    "filter", "list", "dict", "set", "tuple", "str", "input", "open", "abs",
    "min", "max", "sum", "sorted", "reversed", "isinstance", "type",
    "cout", "cin", "endl", "vector", "string", "map", "set", "pair",
    "System", "out", "String", "Integer", "Double", "Boolean", "List", "ArrayList",
    "Map", "HashMap", "Set", "HashSet", "Arrays", "Collections", "Scanner",
}


def remove_comments_and_docstrings(source: str, language: Language) -> str:
    if language == Language.PYTHON:
        try:
            # Tokenize python and strip comments and standalone docstrings
            io_obj = io.StringIO(source)
            out = []
            prev_toktype = tokenize.INDENT
            last_lineno = -1
            last_col = 0
            tokgen = tokenize.generate_tokens(io_obj.readline)
            for toktype, ttext, (s_line, s_col), (e_line, e_col), line in tokgen:
                if toktype == tokenize.COMMENT:
                    continue
                elif toktype == tokenize.STRING:
                    if prev_toktype in (tokenize.INDENT, tokenize.NL, tokenize.NEWLINE):
                        # Docstring
                        continue
                out.append(ttext)
                prev_toktype = toktype
            return " ".join(out)
        except Exception:
            # Fallback regex for Python
            no_comment = re.sub(r'#.*$', '', source, flags=re.M)
            no_docstring = re.sub(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')', '', no_comment)
            return no_docstring

    # C++ and Java
    # Remove block comments /* ... */
    no_block = re.sub(r'/\*[\s\S]*?\*/', '', source)
    # Remove line comments // ...
    no_line = re.sub(r'//.*$', '', no_block, flags=re.M)
    return no_line


def normalize_literals(source: str) -> str:
    # Strings
    s1 = re.sub(r'"([^"\\]|\\.)*"', '"<STR>"', source)
    s2 = re.sub(r"'([^'\\]|\\.)*'", "'<STR>'", s1)
    # Numbers (floats, ints, hex)
    s3 = re.sub(r'\b0x[0-9a-fA-F]+\b', '<NUM>', s2)
    s4 = re.sub(r'\b\d+(\.\d+)?([eE][+-]?\d+)?\b', '<NUM>', s3)
    # Booleans
    s5 = re.sub(r'\b(true|false|True|False)\b', '<BOOL>', s4)
    return s5


def tokenize_code(source: str) -> List[str]:
    """
    Splits code into a sequence of alphanumeric identifiers, operators, and delimiters.
    """
    pattern = r'[a-zA-Z_]\w*|<STR>|<NUM>|<BOOL>|==|!=|<=|>=|\+\+|--|&&|\|\||<<|>>|->|\+=|-=|\*=|/=|%=|[+\-*/%=<>&|^!~?:;,.\(\)\[\]\{\}]'
    return re.findall(pattern, source)


def anonymize_identifiers(tokens: List[str]) -> Tuple[List[str], Dict[str, str]]:
    """
    Maps variable and user function names to normalized symbols (v0, v1, v2...)
    while preserving language keywords, standard types, and literals.
    """
    id_map: Dict[str, str] = {}
    normalized_tokens: List[str] = []
    var_counter = 0

    for token in tokens:
        if token.startswith("<") and token.endswith(">"):
            normalized_tokens.append(token)
        elif token in COMMON_KEYWORDS:
            normalized_tokens.append(token)
        elif re.match(r'^[a-zA-Z_]\w*$', token):
            if token not in id_map:
                id_map[token] = f"v{var_counter}"
                var_counter += 1
            normalized_tokens.append(id_map[token])
        else:
            normalized_tokens.append(token)

    return normalized_tokens, id_map


class PreprocessResult:
    def __init__(
        self,
        original_code: str,
        clean_code: str,
        normalized_tokens: List[str],
        token_ngrams: Set[Tuple[str, ...]],
        identifier_map: Dict[str, str],
    ):
        self.original_code = original_code
        self.clean_code = clean_code
        self.normalized_tokens = normalized_tokens
        self.token_ngrams = token_ngrams
        self.identifier_map = identifier_map


def preprocess_code(source: str, language: Language, ngram_size: int = 4) -> PreprocessResult:
    stripped = remove_comments_and_docstrings(source, language)
    normalized_lit = normalize_literals(stripped)
    tokens = tokenize_code(normalized_lit)
    norm_tokens, id_map = anonymize_identifiers(tokens)

    # Generate token n-grams for Jaccard token similarity
    ngrams = set()
    if len(norm_tokens) >= ngram_size:
        for i in range(len(norm_tokens) - ngram_size + 1):
            ngrams.add(tuple(norm_tokens[i : i + ngram_size]))
    elif norm_tokens:
        ngrams.add(tuple(norm_tokens))

    clean_code = " ".join(norm_tokens)
    return PreprocessResult(
        original_code=source,
        clean_code=clean_code,
        normalized_tokens=norm_tokens,
        token_ngrams=ngrams,
        identifier_map=id_map,
    )
