"""Tests for tools/file_ops.py — sandbox path enforcement and basic I/O."""
import sys
import pytest
from pathlib import Path

import tools.file_ops as _file_ops_mod
from tools.file_ops import read_file, write_file


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_workspace(tmp_path, monkeypatch):
    """Redirect WORKSPACE to a per-test temp directory so tests never touch workspace/."""
    monkeypatch.setattr(_file_ops_mod, "WORKSPACE", tmp_path.resolve())
    return tmp_path


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

class TestReadFile:
    def test_reads_existing_file(self, isolated_workspace):
        (isolated_workspace / "hello.txt").write_text("hello world", encoding="utf-8")
        result = read_file.invoke({"filename": "hello.txt"})
        assert result == "hello world"

    def test_file_not_found(self):
        result = read_file.invoke({"filename": "missing.txt"})
        assert "not found" in result.lower()

    def test_path_traversal_dotdot(self):
        result = read_file.invoke({"filename": "../agent.py"})
        assert "escapes" in result.lower() or "error" in result.lower()

    def test_path_traversal_absolute_unix(self):
        result = read_file.invoke({"filename": "/etc/passwd"})
        assert "escapes" in result.lower() or "error" in result.lower()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows drive-letter paths are relative strings on Linux/macOS")
    def test_path_traversal_absolute_windows(self):
        result = read_file.invoke({"filename": "C:\\Windows\\system32\\drivers\\etc\\hosts"})
        assert "escapes" in result.lower() or "error" in result.lower()

    def test_path_traversal_encoded(self):
        result = read_file.invoke({"filename": "..%2Fagent.py"})
        # URL-encoded traversal — the raw string won't resolve outside workspace
        assert "not found" in result.lower() or "escapes" in result.lower()

    def test_not_a_file(self, isolated_workspace):
        (isolated_workspace / "subdir").mkdir()
        result = read_file.invoke({"filename": "subdir"})
        assert "not a regular file" in result.lower() or "error" in result.lower()


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

class TestWriteFile:
    def test_writes_new_file(self, isolated_workspace):
        result = write_file.invoke({"filename": "out.txt", "content": "data"})
        assert "wrote" in result.lower()
        assert (isolated_workspace / "out.txt").read_text(encoding="utf-8") == "data"

    def test_overwrites_existing_file(self, isolated_workspace):
        (isolated_workspace / "out.txt").write_text("old", encoding="utf-8")
        write_file.invoke({"filename": "out.txt", "content": "new"})
        assert (isolated_workspace / "out.txt").read_text(encoding="utf-8") == "new"

    def test_creates_subdirectory(self, isolated_workspace):
        result = write_file.invoke({"filename": "sub/file.txt", "content": "nested"})
        assert "wrote" in result.lower()
        assert (isolated_workspace / "sub" / "file.txt").exists()

    def test_path_traversal_dotdot(self):
        result = write_file.invoke({"filename": "../evil.txt", "content": "x"})
        assert "escapes" in result.lower() or "error" in result.lower()

    def test_path_traversal_absolute(self):
        result = write_file.invoke({"filename": "/tmp/evil.txt", "content": "x"})
        assert "escapes" in result.lower() or "error" in result.lower()

    def test_reports_byte_count(self, isolated_workspace):
        result = write_file.invoke({"filename": "count.txt", "content": "12345"})
        assert "5" in result
