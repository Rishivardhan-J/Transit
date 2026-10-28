"""Filesystem anchors so code works regardless of the current working directory."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
BENCHMARK_DIR = DATA_DIR / "benchmark"
RESULTS_DIR = PROJECT_ROOT / "results"
MODELS_DIR = RESULTS_DIR / "models"
FIGURES_DIR = RESULTS_DIR / "figures"
MLFLOW_URI = "sqlite:///" + str(RESULTS_DIR / "mlruns.db")
