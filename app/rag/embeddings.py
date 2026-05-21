import hashlib
import math
import re
from typing import List


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")


def deterministic_embedding(text: str, dim: int = 128) -> List[float]:
    vector = [0.0] * dim
    tokens = TOKEN_RE.findall(text.lower())
    if not tokens:
        tokens = [text[:64] or "empty"]

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]
