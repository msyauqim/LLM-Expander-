"""Simple file-based cache."""
import hashlib
import json
import os
from typing import Optional
from pipeline.config import CACHE_DIR


def _hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def get(key_data: str) -> Optional[str]:
    path = os.path.join(CACHE_DIR, f"{_hash(key_data)}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("value")
    return None


def put(key_data: str, value: str):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{_hash(key_data)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"key": key_data[:200], "value": value}, f, ensure_ascii=False)
