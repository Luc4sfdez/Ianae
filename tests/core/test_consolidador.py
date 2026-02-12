"""Tests para Consolidador — consolidacion periodica del sistema IANAE."""
import time
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.nucleo import ConceptosLucas, crear_universo_lucas
from src.core.memoria_v2 import MemoriaAsociativaV2
from src.core.aprendizaje_refuerzo import AprendizajeRefuerzo
from src.core.consolidador import Consolidador


@pytest.fixture
def sistema():
    s = crear_universo_lucas()
    s.crear_relaciones_lucas()
    return s


@pytest.fixture
def memoria():
    return MemoriaAsociativaV2(capacidad=50, decaimiento=0.95)


@pytest.fixture
def aprendizaje():
    return AprendizajeRefuerzo()


@pytest.fixture
def consolidador(sistema, memoria, aprendizaje):
    return Consolidador(
        sistema=sistema,
        memoria=memoria,
        aprendizaje=aprendizaje,
        intervalo_min=1.0,
        ciclos_por_consolidacion=2,
    )


# ==================== Consolidacion basica ====================

class TestConsolidacion:
    def test_consolidar_retorna_metricas(self, consolidador):
        result = consolidador.consolidar()
        assert "conceptos_antes" in result
        assert "conceptos_despues" in result
        assert "conceptos_delta" in result
        assert "ciclos_ejecutados" in result
        assert "memorias_eliminadas" in result
        assert "conceptos_decaidos" in result
        assert "genesis_creados" in result
        assert "tiempo_s" in result

    def test_consolidar_ejecuta_ciclo_vital(self, consolidador):
        result = consolidador.consolidar()
        assert result["ciclos_ejecutados"] > 0

    def test_consolidar_guarda_historial(self, consolidador):
        assert len(consolidador.historial) == 0
        consolidador.consolidar()
        assert len(consolidador.historial) == 1
        consolidador.consolidar()
        assert len(consolidador.historial) == 2

    def test_consolidar_multiples(self, consolidador):
        for _ in range(3):
            consolidador.consolidar()
        assert len(consolidador.historial) == 3

    def test_consolidar_sin_memoria(self, sistema):
        c = Consolidador(sistema=sistema, memoria=None)
        result = c.consolidar()
        assert result["memorias_eliminadas"] == 0

    def test_consolidar_sin_aprendizaje(self, sistema, memoria):
        c = Consolidador(sistema=sistema, memoria=memoria, aprendizaje=None)
        result = c.consolidar()
        assert "ciclos_ejecutados" in result


# ==================== Decay de inactivos ====================

class TestDecay:
    def test_decaer_no_afecta_activos(self, consolidador):
        # Activar conceptos recientemente
        sistema = consolidador.sistema
        for nombre in list(sistema.conceptos.keys())[:3]:
            sistema.activar(nombre, pasos=1)

        decaidos = consolidador._decaer_inactivos(umbral_ciclos=1000)
        # Con umbral alto, ninguno deberia decaer
        assert decaidos == 0

    def test_decaer_afecta_inactivos(self, consolidador):
        sistema = consolidador.sistema
        # Simular que el sistema tiene mucha edad
        sistema.metricas["edad"] = 200
        # Ningun concepto se ha activado recientemente (ultima_activacion=0)
        decaidos = consolidador._decaer_inactivos(umbral_ciclos=50)
        assert decaidos > 0

    def test_decaer_reduce_fuerza(self, consolidador):
        sistema = consolidador.sistema
        sistema.metricas["edad"] = 200

        nombre = list(sistema.conceptos.keys())[0]
        fuerza_antes = sistema.conceptos[nombre]["fuerza"]

        consolidador._decaer_inactivos(umbral_ciclos=50)

        fuerza_despues = sistema.conceptos[nombre]["fuerza"]
        assert fuerza_despues < fuerza_antes

    def test_decaer_no_baja_de_minimo(self, consolidador):
        sistema = consolidador.sistema
        sistema.metricas["edad"] = 10000

        # Forzar fuerza muy baja
        nombre = list(sistema.conceptos.keys())[0]
        sistema.conceptos[nombre]["fuerza"] = 0.06

        consolidador._decaer_inactivos(umbral_ciclos=1)

        # No debe bajar de 0.05
        assert sistema.conceptos[nombre]["fuerza"] >= 0.05


# ==================== Snapshot ====================

class TestSnapshot:
    def test_consolidar_con_snapshot(self, sistema, memoria):
        with tempfile.TemporaryDirectory() as tmpdir:
            c = Consolidador(sistema=sistema, memoria=memoria, snapshot_dir=tmpdir)
            result = c.consolidar()
            assert "snapshot" in result
            assert Path(result["snapshot"]).exists()

    def test_consolidar_sin_snapshot(self, consolidador):
        result = consolidador.consolidar()
        assert "snapshot" not in result


# ==================== Callback ====================

class TestCallback:
    def test_callback_llamado(self, sistema, memoria):
        cb = MagicMock()
        c = Consolidador(sistema=sistema, memoria=memoria, on_consolidacion=cb)
        c.consolidar()
        cb.assert_called_once()
        metricas = cb.call_args[0][0]
        assert "conceptos_antes" in metricas


# ==================== Estadisticas ====================

class TestEstadisticas:
    def test_estadisticas_vacio(self, consolidador):
        stats = consolidador.estadisticas()
        assert stats["consolidaciones"] == 0

    def test_estadisticas_con_datos(self, consolidador):
        consolidador.consolidar()
        consolidador.consolidar()
        stats = consolidador.estadisticas()
        assert stats["consolidaciones"] == 2
        assert "genesis_total" in stats
        assert "decay_total" in stats
        assert "tiempo_total_s" in stats

    def test_metricas_crecimiento_insuficientes(self, consolidador):
        mc = consolidador.metricas_crecimiento()
        assert mc["crecimiento"] == "insuficientes_datos"

    def test_metricas_crecimiento_con_datos(self, consolidador):
        consolidador.consolidar()
        # Simular paso de tiempo
        consolidador._historial[0]["timestamp"] = time.time() - 7200  # 2h atras
        consolidador.consolidar()
        mc = consolidador.metricas_crecimiento()
        assert "conceptos_por_hora" in mc
        assert "horas_monitoreadas" in mc


# ==================== Timer periodico ====================

class TestPeriodico:
    def test_iniciar_y_detener(self, consolidador):
        consolidador.intervalo_min = 0.001  # rapido para test
        consolidador.iniciar()
        assert consolidador._running is True
        assert consolidador._timer is not None
        consolidador.detener()
        assert consolidador._running is False

    def test_detener_sin_iniciar(self, consolidador):
        consolidador.detener()
        assert consolidador._running is False
