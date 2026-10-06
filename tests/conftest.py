"""Pytest configuration and global fixtures for DemandGuard."""

import os

import matplotlib
import mlflow
import pytest

# Set non-interactive backend for headless test runs
matplotlib.use("Agg")
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"


@pytest.fixture(autouse=True)
def isolate_test_mlflow(tmp_path, monkeypatch):
    """Ensure test runs log MLflow artifacts to an isolated temporary SQLite database."""
    test_db = tmp_path / "test_mlflow.db"
    test_uri = f"sqlite:///{test_db.as_posix()}"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", test_uri)
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    mlflow.set_tracking_uri(test_uri)
