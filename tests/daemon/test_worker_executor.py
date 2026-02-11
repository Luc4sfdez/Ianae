"""
Tests para worker_executor.py — Motor de ejecucion autonomo.

Verifica:
- Parsing de bloques ### FILE y ### REPORT del LLM
- Scope enforcement (no escribe fuera del scope)
- Limite de archivos por orden
- Backup y rollback de archivos
- Flujo completo execute_order (mock LLM + mock tests)
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Agregar path del daemon
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "orchestra", "daemon"))

from worker_executor import WorkerExecutor, parse_llm_file_blocks
from llm_provider import LLMResponse


# ============================================
# Tests de parse_llm_file_blocks
# ============================================

class TestParseLLMFileBlocks:
    def test_single_file_block(self):
        text = (
            "### FILE: src/core/nucleo.py\n"
            "```python\n"
            "print('hello')\n"
            "```\n\n"
            "### REPORT\n"
            "Se agrego un print."
        )
        files, report = parse_llm_file_blocks(text)
        assert len(files) == 1
        assert files[0]["path"] == "src/core/nucleo.py"
        assert files[0]["content"] == "print('hello')"
        assert "Se agrego un print" in report

    def test_multiple_file_blocks(self):
        text = (
            "### FILE: src/core/nucleo.py\n"
            "```python\n"
            "class Nucleo: pass\n"
            "```\n\n"
            "### FILE: tests/core/test_nucleo.py\n"
            "```python\n"
            "def test_nucleo(): assert True\n"
            "```\n\n"
            "### REPORT\n"
            "Dos archivos modificados."
        )
        files, report = parse_llm_file_blocks(text)
        assert len(files) == 2
        assert files[0]["path"] == "src/core/nucleo.py"
        assert files[1]["path"] == "tests/core/test_nucleo.py"
        assert "Dos archivos" in report

    def test_no_file_blocks(self):
        text = "Solo texto sin bloques de archivo."
        files, report = parse_llm_file_blocks(text)
        assert len(files) == 0
        assert report == ""

    def test_file_block_without_report(self):
        text = (
            "### FILE: src/core/emergente.py\n"
            "```python\n"
            "x = 1\n"
            "```\n"
        )
        files, report = parse_llm_file_blocks(text)
        assert len(files) == 1
        assert report == ""

    def test_report_without_file_blocks(self):
        text = (
            "### REPORT\n"
            "No hubo cambios necesarios."
        )
        files, report = parse_llm_file_blocks(text)
        assert len(files) == 0
        assert "No hubo cambios" in report

    def test_multiline_file_content(self):
        text = (
            "### FILE: src/core/nucleo.py\n"
            "```python\n"
            "import numpy as np\n"
            "\n"
            "class Nucleo:\n"
            "    def __init__(self):\n"
            "        self.data = np.array([])\n"
            "```\n\n"
            "### REPORT\n"
            "Refactored."
        )
        files, report = parse_llm_file_blocks(text)
        assert len(files) == 1
        assert "import numpy" in files[0]["content"]
        assert "class Nucleo" in files[0]["content"]
        assert "self.data" in files[0]["content"]

    def test_generic_code_fence(self):
        """Soporta bloques ``` sin especificar lenguaje."""
        text = (
            "### FILE: config/settings.toml\n"
            "```\n"
            "[project]\n"
            "name = \"ianae\"\n"
            "```\n\n"
            "### REPORT\n"
            "Config updated."
        )
        files, report = parse_llm_file_blocks(text)
        assert len(files) == 1
        assert files[0]["path"] == "config/settings.toml"


# ============================================
# Tests de WorkerExecutor — inicializacion
# ============================================

class TestWorkerExecutorInit:
    @patch("worker_executor.ProviderChain")
    def test_invalid_worker_raises(self, mock_chain):
        with pytest.raises(ValueError, match="Worker no valido"):
            WorkerExecutor("worker-fantasma", "/tmp/project")

    @patch("worker_executor.ProviderChain")
    def test_valid_worker_initializes(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")
        assert executor.worker_name == "worker-core"
        assert executor.scope_paths == ["src/core/", "tests/core/"]
        assert executor.test_cmd == "python -m pytest tests/core/ -q"

    @patch("worker_executor.ProviderChain")
    def test_custom_scope_overrides_config(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor(
            "worker-core", "/tmp/project",
            scope_paths=["custom/path/"],
        )
        assert executor.scope_paths == ["custom/path/"]


# ============================================
# Tests de scope enforcement
# ============================================

class TestScopeEnforcement:
    @patch("worker_executor.ProviderChain")
    def test_path_in_scope(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        assert executor._is_path_in_scope("src/core/nucleo.py") is True
        assert executor._is_path_in_scope("src/core/emergente.py") is True
        assert executor._is_path_in_scope("tests/core/test_nucleo.py") is True

    @patch("worker_executor.ProviderChain")
    def test_path_out_of_scope(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        assert executor._is_path_in_scope("src/nlp/parser.py") is False
        assert executor._is_path_in_scope("docker/Dockerfile") is False
        assert executor._is_path_in_scope("../../etc/passwd") is False

    @patch("worker_executor.ProviderChain")
    def test_scope_with_backslashes(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        # Windows-style paths should be normalized
        assert executor._is_path_in_scope("src\\core\\nucleo.py") is True

    @patch("worker_executor.ProviderChain")
    def test_apply_files_scope_violation_raises(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        files = [{"path": "src/nlp/forbidden.py", "content": "hack"}]
        with pytest.raises(ValueError, match="fuera de scope"):
            executor._apply_files(files)

    @patch("worker_executor.ProviderChain")
    def test_apply_files_max_limit_raises(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        files = [
            {"path": f"src/core/file{i}.py", "content": f"# file {i}"}
            for i in range(6)  # Mas que WORKER_MAX_FILES (5)
        ]
        with pytest.raises(ValueError, match="Demasiados archivos"):
            executor._apply_files(files)


# ============================================
# Tests de backup y rollback
# ============================================

class TestBackupRollback:
    @patch("worker_executor.ProviderChain")
    def test_backup_and_rollback_existing_file(self, mock_chain, tmp_path):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor(
            "worker-core", str(tmp_path),
            scope_paths=["src/core/"],
        )

        # Crear archivo original
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)
        original = src_dir / "nucleo.py"
        original.write_text("original content", encoding="utf-8")

        # Aplicar cambio
        files = [{"path": "src/core/nucleo.py", "content": "new content"}]
        executor._apply_files(files)
        assert original.read_text(encoding="utf-8") == "new content"

        # Rollback
        executor._rollback()
        assert original.read_text(encoding="utf-8") == "original content"

    @patch("worker_executor.ProviderChain")
    def test_rollback_removes_new_file(self, mock_chain, tmp_path):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor(
            "worker-core", str(tmp_path),
            scope_paths=["src/core/"],
        )

        # No crear archivo — es nuevo
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)
        new_file = src_dir / "nuevo.py"

        files = [{"path": "src/core/nuevo.py", "content": "nuevo"}]
        executor._apply_files(files)
        assert new_file.exists()

        # Rollback debe eliminarlo
        executor._rollback()
        assert not new_file.exists()


# ============================================
# Tests de execute_order (flujo completo)
# ============================================

class TestExecuteOrder:
    def _make_executor(self, mock_chain, tmp_path):
        """Helper para crear executor con mocks."""
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor(
            "worker-core", str(tmp_path),
            scope_paths=["src/core/", "tests/core/"],
        )
        return executor

    @patch("worker_executor.mark_as_blocked")
    @patch("worker_executor.mark_as_in_progress")
    @patch("worker_executor.mark_as_completed")
    @patch("worker_executor.ProviderChain")
    def test_successful_order(
        self, mock_chain, mock_completed, mock_progress, mock_blocked, tmp_path
    ):
        executor = self._make_executor(mock_chain, tmp_path)

        # Setup archivos del scope
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)
        (src_dir / "nucleo.py").write_text("# original", encoding="utf-8")

        # Mock LLM response
        llm_text = (
            "### FILE: src/core/nucleo.py\n"
            "```python\n"
            "# modified\n"
            "```\n\n"
            "### REPORT\n"
            "Se modifico nucleo."
        )
        executor.llm_chain.chat.return_value = LLMResponse(
            text=llm_text,
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=500,
            output_tokens=200,
        )

        # Mock tests passing
        with patch.object(executor, "_run_tests", return_value=(True, "2 passed")):
            executor.docs_client = MagicMock()
            result = executor.execute_order({"id": 7, "title": "Test orden", "content": "Haz algo"})

        assert result is True
        mock_progress.assert_called_once()
        mock_completed.assert_called_once()
        mock_blocked.assert_not_called()

    @patch("worker_executor.mark_as_blocked")
    @patch("worker_executor.mark_as_in_progress")
    @patch("worker_executor.mark_as_completed")
    @patch("worker_executor.ProviderChain")
    def test_failed_tests_triggers_rollback(
        self, mock_chain, mock_completed, mock_progress, mock_blocked, tmp_path
    ):
        executor = self._make_executor(mock_chain, tmp_path)

        # Setup
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)
        (src_dir / "nucleo.py").write_text("# original", encoding="utf-8")

        llm_text = (
            "### FILE: src/core/nucleo.py\n"
            "```python\n"
            "# broken code\n"
            "```\n\n"
            "### REPORT\n"
            "Cambio roto."
        )
        executor.llm_chain.chat.return_value = LLMResponse(
            text=llm_text,
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=500,
            output_tokens=200,
        )

        # Mock tests failing
        with patch.object(executor, "_run_tests", return_value=(False, "FAILED test_x")):
            executor.docs_client = MagicMock()
            result = executor.execute_order({"id": 8, "title": "Orden rota", "content": "Rompe algo"})

        assert result is False
        mock_blocked.assert_called_once()
        mock_completed.assert_not_called()
        # Archivo debe estar restaurado (rollback)
        assert (src_dir / "nucleo.py").read_text(encoding="utf-8") == "# original"

    @patch("worker_executor.mark_as_blocked")
    @patch("worker_executor.mark_as_in_progress")
    @patch("worker_executor.ProviderChain")
    def test_llm_error_marks_blocked(self, mock_chain, mock_progress, mock_blocked, tmp_path):
        executor = self._make_executor(mock_chain, tmp_path)
        executor.docs_client = MagicMock()

        # LLM falla
        executor.llm_chain.chat.side_effect = RuntimeError("All providers failed")

        result = executor.execute_order({"id": 9, "title": "Fallo LLM", "content": "..."})

        assert result is False
        mock_blocked.assert_called_once()

    @patch("worker_executor.mark_as_blocked")
    @patch("worker_executor.mark_as_in_progress")
    @patch("worker_executor.ProviderChain")
    def test_no_files_in_response_marks_blocked(
        self, mock_chain, mock_progress, mock_blocked, tmp_path
    ):
        executor = self._make_executor(mock_chain, tmp_path)
        executor.docs_client = MagicMock()

        # LLM responde sin bloques de archivo
        executor.llm_chain.chat.return_value = LLMResponse(
            text="No entendi la orden, podrias clarificar?",
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=100,
            output_tokens=50,
        )

        result = executor.execute_order({"id": 10, "title": "Orden vaga", "content": "Haz algo"})

        assert result is False
        mock_blocked.assert_called_once()
