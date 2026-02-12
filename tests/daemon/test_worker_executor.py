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
from config import WORKER_MAX_FILES


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

        # Mock planning call (chat) -> devuelve plan con archivos
        plan_text = (
            "### PLAN\n"
            "- FILE: src/core/nucleo.py — Modificar nucleo\n"
            "### REPORT\n"
            "Se modifico nucleo."
        )
        executor.llm_chain.chat.return_value = LLMResponse(
            text=plan_text,
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=500,
            output_tokens=200,
        )
        # Mock per-file call (chat_with_preferred) -> devuelve archivo
        file_text = (
            "### FILE: src/core/nucleo.py\n"
            "```python\n"
            "# modified\n"
            "```\n"
        )
        executor.llm_chain.chat_with_preferred = MagicMock(return_value=LLMResponse(
            text=file_text,
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=300,
            output_tokens=150,
        ))

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

        # Mock planning call -> plan con archivo
        plan_text = (
            "### PLAN\n"
            "- FILE: src/core/nucleo.py — Romper nucleo\n"
            "### REPORT\n"
            "Cambio roto."
        )
        executor.llm_chain.chat.return_value = LLMResponse(
            text=plan_text,
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=500,
            output_tokens=200,
        )
        # Mock per-file call -> archivo roto
        file_text = (
            "### FILE: src/core/nucleo.py\n"
            "```python\n"
            "# broken code\n"
            "```\n"
        )
        executor.llm_chain.chat_with_preferred = MagicMock(return_value=LLMResponse(
            text=file_text,
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=300,
            output_tokens=150,
        ))

        # Mock tests failing — simulate last attempt so mark_as_blocked fires
        with patch.object(executor, "_run_tests", return_value=(False, "FAILED test_x")):
            executor.docs_client = MagicMock()
            result = executor.execute_order({"id": 8, "title": "Orden rota", "content": "Rompe algo"}, attempt=3)

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

        # Planning call responde sin plan de archivos
        executor.llm_chain.chat.return_value = LLMResponse(
            text="No entendi la orden, podrias clarificar?",
            provider="deepseek",
            model="deepseek-chat",
            input_tokens=100,
            output_tokens=50,
        )

        # Simulate last attempt so mark_as_blocked fires
        result = executor.execute_order({"id": 10, "title": "Orden vaga", "content": "Haz algo"}, attempt=3)

        assert result is False
        mock_blocked.assert_called_once()


# ============================================
# Tests de _fix_scope_path
# ============================================

class TestFixScopePath:
    @patch("worker_executor.ProviderChain")
    def test_already_in_scope(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        assert executor._fix_scope_path("src/core/nucleo.py") == "src/core/nucleo.py"

    @patch("worker_executor.ProviderChain")
    def test_fix_bare_filename_src(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        fixed = executor._fix_scope_path("emergente.py")
        assert fixed is not None
        assert fixed.startswith("src/core/")
        assert fixed.endswith("emergente.py")

    @patch("worker_executor.ProviderChain")
    def test_fix_test_file_to_test_scope(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        fixed = executor._fix_scope_path("test_nucleo.py")
        assert fixed is not None
        assert "tests/core/" in fixed

    @patch("worker_executor.ProviderChain")
    def test_fix_wrong_prefix(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        fixed = executor._fix_scope_path("src/memoria.py")
        assert fixed is not None
        # Should land in some scope path
        assert any(scope in fixed for scope in ["src/core/", "tests/core/"])


# ============================================
# Tests de _normalize_title y _is_duplicate
# ============================================

class TestDuplicateDetection:
    @patch("worker_executor.ProviderChain")
    def test_normalize_title_strips_order_prefix(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        assert "agregar" in executor._normalize_title("Orden CORE-#04: Agregar metodo X")
        assert "agregar" in executor._normalize_title("ORDEN CORE-04: Agregar metodo X")

    @patch("worker_executor.ProviderChain")
    def test_normalize_collapses_spaces(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        t1 = executor._normalize_title("Agregar   metodo   X")
        t2 = executor._normalize_title("Agregar metodo X")
        assert t1 == t2

    @patch("worker_executor.ProviderChain")
    def test_is_duplicate_first_unseen(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        assert executor._is_duplicate({"title": "Agregar genesis"}) is False

    @patch("worker_executor.ProviderChain")
    def test_is_duplicate_after_seen(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        title = "Agregar genesis de conceptos"
        norm = executor._normalize_title(title)
        executor._seen_titles.add(norm)
        assert executor._is_duplicate({"title": title}) is True


# ============================================
# Tests de _cost_block_multi
# ============================================

class TestCostBlockMulti:
    @patch("worker_executor.ProviderChain")
    def test_empty_responses(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        result = executor._cost_block_multi([])
        assert result == ""

    @patch("worker_executor.ProviderChain")
    def test_single_response(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        responses = [
            LLMResponse(text="ok", provider="deepseek", model="deepseek-chat",
                        input_tokens=1000, output_tokens=500),
        ]
        result = executor._cost_block_multi(responses)
        assert "COST_DATA" in result
        import json
        data = json.loads(result.split("COST_DATA: ")[1].split(" -->")[0])
        assert data["input_tokens"] == 1000
        assert data["output_tokens"] == 500
        assert data["chunked_calls"] == 1
        assert data["cost_usd"] > 0

    @patch("worker_executor.ProviderChain")
    def test_multiple_responses_accumulate(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        responses = [
            LLMResponse(text="plan", provider="deepseek", model="deepseek-chat",
                        input_tokens=1000, output_tokens=200),
            LLMResponse(text="file1", provider="deepseek", model="deepseek-chat",
                        input_tokens=800, output_tokens=300),
            LLMResponse(text="file2", provider="anthropic", model="claude-sonnet",
                        input_tokens=900, output_tokens=400),
        ]
        result = executor._cost_block_multi(responses)
        import json
        data = json.loads(result.split("COST_DATA: ")[1].split(" -->")[0])
        assert data["input_tokens"] == 2700
        assert data["output_tokens"] == 900
        assert data["chunked_calls"] == 3
        assert "deepseek" in data["providers"]
        assert "anthropic" in data["providers"]
        assert data["by_provider"]["deepseek"]["calls"] == 2
        assert data["by_provider"]["anthropic"]["calls"] == 1


# ============================================
# Tests de _assess_complexity
# ============================================

class TestAssessComplexity:
    @patch("worker_executor.ProviderChain")
    def test_simple_task_uses_deepseek(self, mock_chain, tmp_path):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", str(tmp_path),
                                  scope_paths=["src/core/", "tests/core/"])

        planned = [("src/core/nuevo.py", "Archivo nuevo")]
        provider, tokens = executor._assess_complexity(planned)
        assert provider == "deepseek"
        assert tokens == 6000

    @patch("worker_executor.ProviderChain")
    def test_many_files_uses_anthropic(self, mock_chain, tmp_path):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", str(tmp_path),
                                  scope_paths=["src/core/", "tests/core/"])

        planned = [
            ("src/core/a.py", "A"), ("src/core/b.py", "B"), ("src/core/c.py", "C"),
        ]
        provider, tokens = executor._assess_complexity(planned)
        assert provider == "anthropic"
        assert tokens == 16000

    @patch("worker_executor.ProviderChain")
    def test_large_existing_file_uses_anthropic(self, mock_chain, tmp_path):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", str(tmp_path),
                                  scope_paths=["src/core/", "tests/core/"])

        # Crear archivo grande
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)
        big_file = src_dir / "big.py"
        big_file.write_text("\n".join([f"# line {i}" for i in range(300)]))

        planned = [("src/core/big.py", "Modificar archivo grande")]
        provider, tokens = executor._assess_complexity(planned)
        assert provider == "anthropic"
        assert tokens == 16000

    @patch("worker_executor.ProviderChain")
    def test_two_small_files_uses_deepseek(self, mock_chain, tmp_path):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", str(tmp_path),
                                  scope_paths=["src/core/", "tests/core/"])

        # Crear archivos pequenos
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)
        (src_dir / "small.py").write_text("x = 1\n" * 50)

        planned = [("src/core/small.py", "Editar"), ("src/core/new.py", "Crear")]
        provider, tokens = executor._assess_complexity(planned)
        assert provider == "deepseek"
        assert tokens == 6000


# ============================================
# Tests de prompts para chunked generation
# ============================================

class TestChunkedPrompts:
    @patch("worker_executor.ProviderChain")
    def test_planning_prompt_has_format(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        prompt = executor._load_planning_prompt()
        assert "### PLAN" in prompt
        assert "FILE:" in prompt
        assert "worker-core" in prompt
        assert str(WORKER_MAX_FILES) in prompt

    @patch("worker_executor.ProviderChain")
    def test_file_gen_prompt_has_target(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        prompt = executor._load_file_gen_prompt(
            "src/core/nucleo.py",
            "Agregar metodo X",
            "### PLAN\n- FILE: src/core/nucleo.py\n",
            [],
        )
        assert "src/core/nucleo.py" in prompt
        assert "Agregar metodo X" in prompt
        assert "### FILE: src/core/nucleo.py" in prompt

    @patch("worker_executor.ProviderChain")
    def test_file_gen_prompt_includes_previous(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        previously = [
            {"path": "src/core/a.py", "content": "class A: pass"},
        ]
        prompt = executor._load_file_gen_prompt(
            "tests/core/test_a.py",
            "Test para A",
            "plan text",
            previously,
        )
        assert "ARCHIVOS YA GENERADOS" in prompt
        assert "src/core/a.py" in prompt
        assert "class A: pass" in prompt


# ============================================
# Tests de _chunked_generate
# ============================================

class TestChunkedGenerate:
    def _make_executor(self, mock_chain, tmp_path):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor(
            "worker-core", str(tmp_path),
            scope_paths=["src/core/", "tests/core/"],
        )
        return executor

    @patch("worker_executor.ProviderChain")
    def test_chunked_basic_flow(self, mock_chain, tmp_path):
        executor = self._make_executor(mock_chain, tmp_path)

        # Setup files
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)

        # Mock planning call
        plan_text = (
            "### PLAN\n"
            "- FILE: src/core/nuevo.py — Crear clase nueva\n"
            "- FILE: tests/core/test_nuevo.py — Tests\n"
            "### REPORT\n"
            "Se crean dos archivos."
        )
        executor.llm_chain.chat.return_value = LLMResponse(
            text=plan_text, provider="deepseek", model="deepseek-chat",
            input_tokens=500, output_tokens=200,
        )

        # Mock per-file calls
        file_responses = [
            LLMResponse(
                text="### FILE: src/core/nuevo.py\n```python\nclass Nuevo: pass\n```\n",
                provider="deepseek", model="deepseek-chat",
                input_tokens=400, output_tokens=100,
            ),
            LLMResponse(
                text="### FILE: tests/core/test_nuevo.py\n```python\ndef test_nuevo(): assert True\n```\n",
                provider="deepseek", model="deepseek-chat",
                input_tokens=400, output_tokens=100,
            ),
        ]
        executor.llm_chain.chat_with_preferred = MagicMock(side_effect=file_responses)

        files, report, responses = executor._chunked_generate(
            {"title": "Test", "content": "Crear algo"},
            "# context",
        )

        assert len(files) == 2
        assert files[0]["path"] == "src/core/nuevo.py"
        assert files[1]["path"] == "tests/core/test_nuevo.py"
        assert "Se crean dos archivos" in report
        assert len(responses) == 3  # 1 plan + 2 files

    @patch("worker_executor.ProviderChain")
    def test_chunked_with_retry_context(self, mock_chain, tmp_path):
        executor = self._make_executor(mock_chain, tmp_path)
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)

        plan_text = "### PLAN\n- FILE: src/core/fix.py — Fix\n### REPORT\nFix."
        executor.llm_chain.chat.return_value = LLMResponse(
            text=plan_text, provider="deepseek", model="deepseek-chat",
            input_tokens=500, output_tokens=200,
        )
        executor.llm_chain.chat_with_preferred = MagicMock(return_value=LLMResponse(
            text="### FILE: src/core/fix.py\n```python\n# fixed\n```\n",
            provider="deepseek", model="deepseek-chat",
            input_tokens=300, output_tokens=100,
        ))

        files, report, responses = executor._chunked_generate(
            {"title": "Fix", "content": "Fix bug"},
            "# context",
            previous_test_output="FAILED test_x - AssertionError",
        )

        # Verificar que retry context se paso al planning call
        call_args = executor.llm_chain.chat.call_args
        user_msg = call_args[1]["messages"][0]["content"] if "messages" in call_args[1] else call_args[0][1][0]["content"]
        assert "ERRORES DEL INTENTO ANTERIOR" in user_msg

    @patch("worker_executor.ProviderChain")
    def test_chunked_raw_fallback(self, mock_chain, tmp_path):
        """Si el LLM no usa ### FILE: wrapper, se extrae el codigo raw."""
        executor = self._make_executor(mock_chain, tmp_path)
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)

        plan_text = "### PLAN\n- FILE: src/core/raw.py — Raw\n### REPORT\nRaw."
        executor.llm_chain.chat.return_value = LLMResponse(
            text=plan_text, provider="deepseek", model="deepseek-chat",
            input_tokens=500, output_tokens=200,
        )
        # Response sin ### FILE: wrapper, solo un bloque de codigo
        executor.llm_chain.chat_with_preferred = MagicMock(return_value=LLMResponse(
            text="Aqui esta el codigo:\n```python\nclass Raw: pass\n```\n",
            provider="deepseek", model="deepseek-chat",
            input_tokens=300, output_tokens=100,
        ))

        files, report, responses = executor._chunked_generate(
            {"title": "Raw", "content": "Crear raw"},
            "# context",
        )

        assert len(files) == 1
        assert files[0]["path"] == "src/core/raw.py"
        assert "class Raw" in files[0]["content"]

    @patch("worker_executor.ProviderChain")
    def test_chunked_scope_autocorrect(self, mock_chain, tmp_path):
        """Paths fuera de scope en el plan se autocorrigen."""
        executor = self._make_executor(mock_chain, tmp_path)
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)

        # Plan con path fuera de scope
        plan_text = "### PLAN\n- FILE: emergente.py — Fix emergente\n### REPORT\nFix."
        executor.llm_chain.chat.return_value = LLMResponse(
            text=plan_text, provider="deepseek", model="deepseek-chat",
            input_tokens=500, output_tokens=200,
        )
        executor.llm_chain.chat_with_preferred = MagicMock(return_value=LLMResponse(
            text="### FILE: src/core/emergente.py\n```python\n# fixed\n```\n",
            provider="deepseek", model="deepseek-chat",
            input_tokens=300, output_tokens=100,
        ))

        files, report, responses = executor._chunked_generate(
            {"title": "Fix", "content": "Fix"},
            "# context",
        )

        # El plan deberia corregir el path
        assert len(files) == 1

    @patch("worker_executor.ProviderChain")
    def test_chunked_empty_plan(self, mock_chain, tmp_path):
        executor = self._make_executor(mock_chain, tmp_path)

        executor.llm_chain.chat.return_value = LLMResponse(
            text="No entiendo la orden.",
            provider="deepseek", model="deepseek-chat",
            input_tokens=100, output_tokens=50,
        )

        files, report, responses = executor._chunked_generate(
            {"title": "Vaga", "content": "..."},
            "# context",
        )

        assert files == []
        assert len(responses) == 1  # Solo planning call

    @patch("worker_executor.ProviderChain")
    def test_chunked_deduplicates_plan_files(self, mock_chain, tmp_path):
        executor = self._make_executor(mock_chain, tmp_path)
        src_dir = tmp_path / "src" / "core"
        src_dir.mkdir(parents=True)

        # Plan con archivo duplicado
        plan_text = (
            "### PLAN\n"
            "- FILE: src/core/x.py — Crear\n"
            "- FILE: src/core/x.py — Duplicado\n"
            "### REPORT\nOk."
        )
        executor.llm_chain.chat.return_value = LLMResponse(
            text=plan_text, provider="deepseek", model="deepseek-chat",
            input_tokens=500, output_tokens=200,
        )
        executor.llm_chain.chat_with_preferred = MagicMock(return_value=LLMResponse(
            text="### FILE: src/core/x.py\n```python\n# x\n```\n",
            provider="deepseek", model="deepseek-chat",
            input_tokens=300, output_tokens=100,
        ))

        files, report, responses = executor._chunked_generate(
            {"title": "Dedup", "content": "Crear"},
            "# context",
        )

        # Solo 1 archivo (el duplicado se descarta)
        assert len(files) == 1


# ============================================
# Tests de _estimate_cost
# ============================================

class TestEstimateCost:
    @patch("worker_executor.ProviderChain")
    def test_deepseek_cost(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        cost = executor._estimate_cost("deepseek", 1_000_000, 1_000_000)
        # $0.27 input + $1.10 output = $1.37
        assert abs(cost - 1.37) < 0.01

    @patch("worker_executor.ProviderChain")
    def test_anthropic_cost(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        cost = executor._estimate_cost("anthropic", 1_000_000, 1_000_000)
        # $3.00 input + $15.00 output = $18.00
        assert abs(cost - 18.0) < 0.01

    @patch("worker_executor.ProviderChain")
    def test_unknown_provider_uses_default(self, mock_chain):
        mock_chain.return_value = MagicMock(available_providers=["deepseek"])
        executor = WorkerExecutor("worker-core", "/tmp/project")

        cost = executor._estimate_cost("unknown", 1_000_000, 1_000_000)
        # Uses default rates ($3 + $15 = $18)
        assert abs(cost - 18.0) < 0.01


# ============================================
# Tests de _summarize_python
# ============================================

class TestSummarizePython:
    def test_summarize_keeps_imports(self):
        content = (
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "class MyClass:\n"
            "    def method_a(self):\n"
            '        """Do A."""\n'
            "        return 1\n"
            "\n"
            "    def method_b(self):\n"
            '        """Do B."""\n'
            "        return 2\n"
        )
        lines = content.split("\n")
        summary = WorkerExecutor._summarize_python(content, lines)
        assert "import os" in summary
        assert "from pathlib" in summary
        assert "class MyClass" in summary
        assert "def method_a" in summary
        assert "def method_b" in summary

    def test_summarize_truncates_method_bodies(self):
        content = (
            "import os\n"
            "\n"
            "class Big:\n"
            "    def long_method(self):\n"
            '        """Long."""\n'
            + "".join(f"        x = {i}\n" for i in range(100))
        )
        lines = content.split("\n")
        summary = WorkerExecutor._summarize_python(content, lines)
        # Should NOT contain all 100 lines of the method body
        assert summary.count("x = ") < 30
