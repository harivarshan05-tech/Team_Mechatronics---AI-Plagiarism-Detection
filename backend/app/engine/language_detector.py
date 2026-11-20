"""
Language Detection Engine for Python, C++, and Java.
Uses file extension first, with content-based heuristic fallback.
"""

import re
from pathlib import Path
from app.models import Language

EXT_MAP = {
    ".py": Language.PYTHON,
    ".cpp": Language.CPP,
    ".hpp": Language.CPP,
    ".h": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    ".c": Language.CPP,
    ".java": Language.JAVA,
}


def detect_language(filename: str, content: str = "") -> Language:
    # 1. Try file extension
    ext = Path(filename).suffix.lower()
    if ext in EXT_MAP:
        return EXT_MAP[ext]

    if not content:
        return Language.UNKNOWN

    # 2. Content heuristics
    clean_content = content[:3000]

    # Java patterns
    if re.search(r"\bpublic\s+(class|interface|enum)\b", clean_content) or \
       re.search(r"\bSystem\.(out|err)\.print", clean_content) or \
       re.search(r"^\s*package\s+[a-zA-Z0-9_.]+;", clean_content, re.M) or \
       re.search(r"^\s*import\s+java\.", clean_content, re.M):
        return Language.JAVA

    # C++ patterns
    if re.search(r"#\s*include\s*[<\"].*?[>\"]", clean_content) or \
       re.search(r"\bstd::\w+", clean_content) or \
       re.search(r"\bcout\s*<<", clean_content) or \
       re.search(r"\bcin\s*>>", clean_content) or \
       re.search(r"\bnamespace\s+\w+", clean_content) or \
       re.search(r"\btemplate\s*<", clean_content):
        return Language.CPP

    # Python patterns
    if re.search(r"^\s*def\s+\w+\s*\(", clean_content, re.M) or \
       re.search(r"^\s*class\s+\w+.*?:", clean_content, re.M) or \
       re.search(r"^\s*import\s+\w+", clean_content, re.M) or \
       re.search(r"^\s*from\s+\w+\s+import", clean_content, re.M) or \
       re.search(r"\bprint\s*\(", clean_content):
        return Language.PYTHON

    return Language.UNKNOWN
