"""S1-1: API_KEY must never default to a secret; missing config must fail startup.

Runs config.py import in a fresh subprocess so env vars take effect before
any module-level code executes (settings is instantiated at import time).
The subprocess cwd is a tmpdir with no .env file, so python-dotenv can't
backfill API_KEY from backend/.env and mask the "unset" case.
"""
import os
import subprocess
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_IMPORT_CMD = [sys.executable, "-c", "import src.core.config"]


def _run_with_env(env_overrides, tmp_path):
    env = os.environ.copy()
    env.pop("API_KEY", None)
    env["PYTHONPATH"] = BACKEND_DIR
    env.update(env_overrides)
    return subprocess.run(
        _IMPORT_CMD, cwd=str(tmp_path), env=env, capture_output=True, text=True
    )


def test_missing_api_key_refuses_to_start(tmp_path):
    result = _run_with_env({}, tmp_path)
    assert result.returncode != 0
    assert "API_KEY" in result.stderr


def test_empty_api_key_refuses_to_start(tmp_path):
    result = _run_with_env({"API_KEY": ""}, tmp_path)
    assert result.returncode != 0
    assert "API_KEY" in result.stderr


def test_set_api_key_starts_cleanly(tmp_path):
    result = _run_with_env({"API_KEY": "some-real-secret"}, tmp_path)
    assert result.returncode == 0, result.stderr
