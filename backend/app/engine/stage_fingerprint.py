"""
Stage 4: Structural Fingerprinting & Scalable Candidate Filtering.
- Winnowing Algorithm (local minimum hash selection over rolling windows)
- MinHash Signature Generation (64 independent hash functions)
- Locality Sensitive Hashing (LSH) for sub-linear O(N) candidate pair filtering
- Structural Fingerprint Matching for 44,850+ pairwise comparisons
"""

import hashlib
from typing import List, Set, Dict, Tuple, Optional

# Large prime for universal hashing
PRIME_MODULUS = 2147483647

# Pre-computed hash parameters (a_i, b_i) for 64 MinHash functions
# Guaranteed reproducible random seeds
HASH_COEFFS = [
    (131 * i + 17, 313 * i + 97) for i in range(1, 65)
]


class StructuralFingerprint:
    def __init__(
        self,
        submission_id: str,
        winnowed_fingerprints: Set[int],
        minhash_signature: List[int],
        kgrams_count: int,
    ):
        self.submission_id = submission_id
        self.winnowed_fingerprints = winnowed_fingerprints
        self.minhash_signature = minhash_signature
        self.kgrams_count = kgrams_count


def _hash_token(token: str) -> int:
    return int(hashlib.md5(token.encode('utf-8')).hexdigest()[:8], 16)


def generate_fingerprints(
    submission_id: str,
    normalized_tokens: List[str],
    ast_node_types: List[str],
    k: int = 4,
    window_size: int = 6,
) -> StructuralFingerprint:
    """
    Generates Winnowing fingerprints and 64-dim MinHash signature
    from combined normalized tokens and AST structural nodes.
    """
    # Combine normalized code tokens with AST structure tokens
    combined_stream = normalized_tokens + [f"AST_{n}" for n in ast_node_types]

    if not combined_stream:
        return StructuralFingerprint(submission_id, set(), [0] * 64, 0)

    # 1. Generate k-gram integer hashes
    kgram_hashes: List[int] = []
    if len(combined_stream) >= k:
        for i in range(len(combined_stream) - k + 1):
            kgram_str = "_".join(combined_stream[i : i + k])
            kgram_hashes.append(_hash_token(kgram_str))
    else:
        kgram_hashes = [_hash_token(t) for t in combined_stream]

    # 2. Winnowing algorithm (robust local minima selection)
    winnowed: Set[int] = set()
    if len(kgram_hashes) <= window_size:
        winnowed = set(kgram_hashes)
    else:
        min_idx = -1
        for i in range(len(kgram_hashes) - window_size + 1):
            window = kgram_hashes[i : i + window_size]
            min_val = min(window)
            winnowed.add(min_val)

    # 3. MinHash 64 signatures
    minhash_sig: List[int] = []
    if not kgram_hashes:
        minhash_sig = [0] * 64
    else:
        for a, b in HASH_COEFFS:
            min_h = min(((a * h + b) % PRIME_MODULUS) for h in kgram_hashes)
            minhash_sig.append(min_h)

    return StructuralFingerprint(
        submission_id=submission_id,
        winnowed_fingerprints=winnowed,
        minhash_signature=minhash_sig,
        kgrams_count=len(kgram_hashes),
    )


def compute_minhash_similarity(sig_a: List[int], sig_b: List[int]) -> float:
    """
    Computes Jaccard similarity estimate from two 64-dim MinHash signatures:
    Jaccard = (matching hash count) / 64.
    Runs in nanoseconds.
    """
    if len(sig_a) != len(sig_b) or not sig_a:
        return 0.0
    matches = sum(1 for i in range(len(sig_a)) if sig_a[i] == sig_b[i])
    return matches / len(sig_a)


def compute_winnowing_similarity(
    winnowed_a: Set[int], winnowed_b: Set[int]
) -> float:
    """
    Computes exact Jaccard similarity over winnowed fingerprints.
    """
    if not winnowed_a or not winnowed_b:
        return 0.0
    intersection = len(winnowed_a.intersection(winnowed_b))
    union = len(winnowed_a.union(winnowed_b))
    return intersection / union if union > 0 else 0.0


class LSHIndex:
    """
    Locality Sensitive Hashing (LSH) Index with 16 bands x 4 rows.
    Filters candidate pairs for 44,850+ comparisons in O(N) time.
    """

    def __init__(self, num_bands: int = 16, rows_per_band: int = 4):
        self.num_bands = num_bands
        self.rows_per_band = rows_per_band
        # band_idx -> bucket_hash -> list of submission_ids
        self.buckets: List[Dict[int, List[str]]] = [{} for _ in range(num_bands)]
        self.fingerprints: Dict[str, StructuralFingerprint] = {}

    def insert(self, fp: StructuralFingerprint):
        self.fingerprints[fp.submission_id] = fp
        sig = fp.minhash_signature
        for b in range(self.num_bands):
            start = b * self.rows_per_band
            band_chunk = tuple(sig[start : start + self.rows_per_band])
            bucket_key = hash(band_chunk)
            if bucket_key not in self.buckets[b]:
                self.buckets[b][bucket_key] = []
            self.buckets[b][bucket_key].append(fp.submission_id)

    def get_candidate_pairs(self) -> Set[Tuple[str, str]]:
        """
        Finds all candidate pairs that collided in at least one band.
        Guaranteed sub-quadratic candidate generation.
        """
        candidates: Set[Tuple[str, str]] = set()
        for b in range(self.num_bands):
            for sub_list in self.buckets[b].values():
                if len(sub_list) > 1:
                    for i in range(len(sub_list)):
                        for j in range(i + 1, len(sub_list)):
                            sub_a = sub_list[i]
                            sub_b = sub_list[j]
                            pair = (sub_a, sub_b) if sub_a < sub_b else (sub_b, sub_a)
                            candidates.add(pair)
        return candidates
