"""Versioned model bundles: one directory per training run containing everything needed to serve it.

results/models/<kind>_<YYYYmmdd_HHMMSS>_<gitsha>/
    pipeline.pkl   fitted feature pipeline (same object used for training and serving)
    p10.pkl p50.pkl p90.pkl   quantile models
    metadata.json  metrics, CQR offset, feature list, data hash, seed, unit
    importance.json  impurity / permutation / SHAP importances
A text file `latest_<kind>` in the models dir points at the active bundle.
"""
import json
import os
import pickle
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.paths import MODELS_DIR, PROJECT_ROOT


def git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "nogit"
    except Exception:
        return "nogit"


@dataclass
class Bundle:
    path: Path
    version: str
    pipeline: Any
    models: Dict[str, Any]
    metadata: Dict[str, Any]
    importance: Dict[str, Any] = field(default_factory=dict)


def save_bundle(kind: str, pipeline, models: Dict[str, Any], metadata: Dict[str, Any],
                importance: Optional[Dict[str, Any]] = None, root: Path = MODELS_DIR) -> Path:
    version = f"{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{git_sha()}"
    d = Path(root) / version
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "pipeline.pkl", "wb") as f:
        pickle.dump(pipeline, f)
    for q, m in models.items():
        with open(d / f"{q}.pkl", "wb") as f:
            pickle.dump(m, f)
    metadata = {**metadata, "version": version, "kind": kind, "created_at": datetime.now().isoformat(timespec="seconds")}
    (d / "metadata.json").write_text(json.dumps(metadata, indent=2, default=float))
    (d / "importance.json").write_text(json.dumps(importance or {}, indent=2, default=float))
    return d


def set_latest(kind: str, bundle_dir: Path, root: Path = MODELS_DIR) -> None:
    (Path(root) / f"latest_{kind}").write_text(Path(bundle_dir).name)


def list_bundles(root: Path = MODELS_DIR) -> List[Dict[str, Any]]:
    root = Path(root)
    out = []
    if not root.exists():
        return out
    active = {p.read_text().strip() for p in root.glob("latest_*")}
    for d in sorted(root.iterdir()):
        meta = d / "metadata.json"
        if d.is_dir() and meta.exists():
            m = json.loads(meta.read_text())
            m["active"] = d.name in active
            out.append(m)
    return out


def load_bundle(kind: str, version: str = "latest", root: Path = MODELS_DIR) -> Bundle:
    root = Path(root)
    if version == "latest":
        ptr = root / f"latest_{kind}"
        if not ptr.exists():
            raise FileNotFoundError(f"No trained '{kind}' model found in {root}. Run `python -m src.models.train`.")
        version = ptr.read_text().strip()
    d = root / version
    with open(d / "pipeline.pkl", "rb") as f:
        pipeline = pickle.load(f)
    models = {}
    for q in ("p10", "p50", "p90"):
        if (d / f"{q}.pkl").exists():
            with open(d / f"{q}.pkl", "rb") as f:
                models[q] = pickle.load(f)
    imp = json.loads((d / "importance.json").read_text()) if (d / "importance.json").exists() else {}
    return Bundle(d, version, pipeline, models, json.loads((d / "metadata.json").read_text()), imp)
