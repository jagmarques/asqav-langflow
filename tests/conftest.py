"""Keep real framework state local and disable telemetry during tests."""
import os
from pathlib import Path

os.environ.setdefault(
    "LANGFLOW_CONFIG_DIR", str(Path(__file__).resolve().parents[1] / ".pytest_cache/langflow")
)
os.environ["LANGFLOW_DO_NOT_TRACK"] = "true"
os.environ["LANGFLOW_LOG_LEVEL"] = "ERROR"
