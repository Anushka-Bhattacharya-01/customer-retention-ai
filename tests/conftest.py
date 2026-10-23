import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Tests use a throwaway SQLite database and the mock LLM (no AWS, no cost)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/test_assistant.db")
os.environ["LLM_PROVIDER"] = "mock"
