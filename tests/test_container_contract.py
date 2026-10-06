"""Tests for Dockerfile and container configuration contract (Task T15)."""

from pathlib import Path


def test_dockerfile_structure_and_solver():
    """Verify Dockerfile contains required CBC solver and endpoint definitions."""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists()

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "coinor-cbc" in content
    assert "EXPOSE 8000" in content
    assert "demandguard.api:app" in content
    assert "HEALTHCHECK" in content
