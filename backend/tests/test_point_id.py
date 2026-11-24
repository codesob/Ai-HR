"""_point_id must be identical across separate Python processes (regression test)."""
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

SNIPPET = """
import sys, types
for name in ("numpy", "qdrant_client", "qdrant_client.models", "sentence_transformers"):
    m = types.ModuleType(name)
    for attr in ("QdrantClient", "Distance", "PointStruct", "VectorParams", "SentenceTransformer"):
        setattr(m, attr, object)
    sys.modules[name] = m
cfg = types.ModuleType("shared.core.config"); cfg.get_settings = lambda: None
sys.modules["shared.core.config"] = cfg
from shared.services.embeddings import _point_id
print(_point_id("leave-001"), _point_id(42), _point_id("42"))
"""


def _run(seed: str) -> str:
    env = {"PYTHONHASHSEED": seed, "PATH": ""}
    out = subprocess.run(
        [sys.executable, "-c", SNIPPET], cwd=BACKEND, env=env, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def test_point_id_is_stable_across_processes():
    results = {_run(seed) for seed in ("1", "2", "random")}
    assert len(results) == 1


def test_point_id_is_valid_uuid_and_int_str_agree():
    import uuid

    a, b, c = _run("1").split()
    uuid.UUID(a)
    assert b == c
