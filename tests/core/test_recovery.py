"""Tests para RecoveryManager — shutdown seguro y recovery de snapshots."""
import json
import os
import tempfile
import time
import pytest
import numpy as np

from src.core.nucleo import ConceptosLucas, crear_universo_lucas
from src.core.recovery import RecoveryManager


@pytest.fixture
def sistema():
    s = crear_universo_lucas()
    s.crear_relaciones_lucas()
    return s


@pytest.fixture
def snap_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def recovery(sistema, snap_dir):
    return RecoveryManager(sistema, snapshot_dir=snap_dir, auto_save_interval=0)


# --- Snapshot guardado ---

class TestGuardarSnapshot:
    def test_guardar_crea_archivo(self, recovery, snap_dir):
        ruta = recovery.guardar_snapshot("test")
        assert ruta is not None
        assert os.path.exists(ruta)
        assert ruta.startswith(snap_dir)

    def test_guardar_json_valido(self, recovery):
        ruta = recovery.guardar_snapshot("test")
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "_meta" in data
        assert data["_meta"]["motivo"] == "test"
        assert "conceptos" in data

    def test_guardar_contiene_conceptos(self, recovery, sistema):
        ruta = recovery.guardar_snapshot("test")
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["_meta"]["num_conceptos"] == len(sistema.conceptos)
        # Al menos algunos conceptos serializados
        assert len(data["conceptos"]) > 0

    def test_guardar_incrementa_contador(self, recovery):
        assert recovery._save_count == 0
        recovery.guardar_snapshot("a")
        assert recovery._save_count == 1
        recovery.guardar_snapshot("b")
        assert recovery._save_count == 2

    def test_guardar_registra_en_log(self, recovery):
        recovery.guardar_snapshot("manual")
        assert len(recovery.recovery_log) == 1
        assert recovery.recovery_log[0]["accion"] == "snapshot_guardado"
        assert recovery.recovery_log[0]["motivo"] == "manual"

    def test_guardar_vectores_serializados(self, recovery, sistema):
        ruta = recovery.guardar_snapshot("test")
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Verificar que al menos un concepto tiene vector como lista
        for nombre, cdata in data["conceptos"].items():
            if "actual" in cdata:
                assert isinstance(cdata["actual"], list)
                break


# --- Snapshot restaurado ---

class TestRestaurarSnapshot:
    def test_restaurar_desde_archivo(self, recovery, sistema):
        # Modificar fuerza de un concepto
        concepto = list(sistema.conceptos.keys())[0]
        sistema.conceptos[concepto]["fuerza"] = 0.5
        ruta = recovery.guardar_snapshot("pre_test")

        # Modificar despues del snapshot
        sistema.conceptos[concepto]["fuerza"] = 0.1

        # Restaurar
        ok = recovery.restaurar_snapshot(ruta)
        assert ok is True
        assert sistema.conceptos[concepto]["fuerza"] == 0.5

    def test_restaurar_ultimo_automatico(self, recovery, sistema):
        recovery.guardar_snapshot("a")
        time.sleep(0.05)
        concepto = list(sistema.conceptos.keys())[0]
        sistema.conceptos[concepto]["fuerza"] = 0.77
        recovery.guardar_snapshot("b")

        sistema.conceptos[concepto]["fuerza"] = 0.01
        ok = recovery.restaurar_snapshot()  # sin ruta = ultimo
        assert ok is True
        assert sistema.conceptos[concepto]["fuerza"] == 0.77

    def test_restaurar_sin_snapshots(self, recovery):
        ok = recovery.restaurar_snapshot()
        assert ok is False

    def test_restaurar_archivo_inexistente(self, recovery):
        ok = recovery.restaurar_snapshot("/no/existe.json")
        assert ok is False

    def test_restaurar_registra_en_log(self, recovery, sistema):
        ruta = recovery.guardar_snapshot("test")
        recovery.restaurar_snapshot(ruta)
        logs_restaurar = [l for l in recovery.recovery_log if l["accion"] == "snapshot_restaurado"]
        assert len(logs_restaurar) == 1
        assert logs_restaurar[0]["conceptos_restaurados"] > 0


# --- Listar snapshots ---

class TestListarSnapshots:
    def test_listar_vacio(self, recovery):
        assert recovery.listar_snapshots() == []

    def test_listar_multiples(self, recovery):
        recovery.guardar_snapshot("a")
        time.sleep(0.05)
        recovery.guardar_snapshot("b")
        snaps = recovery.listar_snapshots()
        assert len(snaps) == 2
        # Ordenados por timestamp desc
        assert snaps[0]["timestamp"] >= snaps[1]["timestamp"]

    def test_listar_contiene_metadata(self, recovery):
        recovery.guardar_snapshot("test")
        snaps = recovery.listar_snapshots()
        assert snaps[0]["motivo"] == "test"
        assert snaps[0]["num_conceptos"] > 0


# --- Limpiar snapshots ---

class TestLimpiarSnapshots:
    def test_limpiar_mantiene_recientes(self, recovery):
        for i in range(5):
            recovery.guardar_snapshot(f"s{i}")
            time.sleep(0.05)
        eliminados = recovery.limpiar_snapshots(mantener=3)
        assert eliminados == 2
        assert len(recovery.listar_snapshots()) == 3

    def test_limpiar_nada_que_eliminar(self, recovery):
        recovery.guardar_snapshot("a")
        eliminados = recovery.limpiar_snapshots(mantener=5)
        assert eliminados == 0


# --- Auto-save ---

class TestAutoSave:
    def test_auto_save_desactivado(self, recovery):
        recovery.auto_save_interval = 0
        assert recovery.check_auto_save() is None

    def test_auto_save_intervalo(self, snap_dir, sistema):
        rm = RecoveryManager(sistema, snapshot_dir=snap_dir, auto_save_interval=1)
        rm._last_save_time = time.time() - 2  # Forzar que paso el intervalo
        ruta = rm.check_auto_save()
        assert ruta is not None

    def test_auto_save_no_prematuro(self, snap_dir, sistema):
        rm = RecoveryManager(sistema, snapshot_dir=snap_dir, auto_save_interval=300)
        rm._last_save_time = time.time()
        assert rm.check_auto_save() is None


# --- Diagnostico ---

class TestDiagnostico:
    def test_diagnostico_basico(self, recovery):
        diag = recovery.diagnostico()
        assert diag["estado"] == "ok"
        assert diag["conceptos_total"] > 0
        assert isinstance(diag["problemas"], list)

    def test_diagnostico_sistema_vacio(self, snap_dir):
        sistema_vacio = ConceptosLucas()
        rm = RecoveryManager(sistema_vacio, snapshot_dir=snap_dir)
        diag = rm.diagnostico()
        assert diag["estado"] == "warning"
        assert any("Sin conceptos" in p for p in diag["problemas"])

    def test_diagnostico_detecta_nan(self, recovery, sistema):
        concepto = list(sistema.conceptos.keys())[0]
        sistema.conceptos[concepto]["actual"] = np.array([float("nan")] * 15)
        diag = recovery.diagnostico()
        assert diag["estado"] == "error"
        assert diag["vectores_nan"] >= 1

    def test_diagnostico_conceptos_debiles(self, recovery, sistema):
        # Poner todos los conceptos con fuerza baja
        for data in sistema.conceptos.values():
            data["fuerza"] = 0.01
        diag = recovery.diagnostico()
        assert diag["estado"] == "warning"
        assert diag["conceptos_debiles"] == len(sistema.conceptos)


# --- Signal handlers ---

class TestSignalHandlers:
    def test_instalar_handlers(self, recovery):
        recovery.instalar_signal_handlers()
        assert recovery._signal_handlers_installed is True

    def test_instalar_doble_no_error(self, recovery):
        recovery.instalar_signal_handlers()
        recovery.instalar_signal_handlers()  # No debe fallar

    def test_shutdown_flag(self, recovery):
        assert recovery.shutdown_requested is False
