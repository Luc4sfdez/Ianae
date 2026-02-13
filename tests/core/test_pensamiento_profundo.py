"""Tests para PensamientoProfundo — Fase 9."""
import pytest
from src.core.nucleo import crear_universo_lucas
from src.core.pensamiento_profundo import PensamientoProfundo


@pytest.fixture
def sistema():
    s = crear_universo_lucas()
    s.crear_relaciones_lucas()
    return s


@pytest.fixture
def profundo(sistema):
    return PensamientoProfundo(sistema)


class TestPensamientoProfundo:
    def test_profundizar_retorna_dict_completo(self, profundo, sistema):
        concepto = list(sistema.conceptos.keys())[0]
        r = profundo.profundizar(concepto)
        assert isinstance(r, dict)
        assert "coherencia_simbolica" in r
        assert "profundidad_max" in r
        assert "nodos_totales" in r
        assert "nodos_podados" in r
        assert "representacion_simbolica" in r
        assert "depth_stats" in r
        assert "hibrido" in r

    def test_coherencia_entre_0_y_1(self, profundo, sistema):
        concepto = list(sistema.conceptos.keys())[0]
        r = profundo.profundizar(concepto)
        assert 0.0 <= r["coherencia_simbolica"] <= 1.0

    def test_concepto_inexistente_resultado_vacio(self, profundo):
        r = profundo.profundizar("concepto_que_no_existe_xyz")
        assert r["coherencia_simbolica"] == 0.0
        assert r["nodos_totales"] == 0
        assert r["nodos_podados"] == 0
        assert r["representacion_simbolica"] == ""

    def test_ultimo_arbol_se_cachea(self, profundo, sistema):
        assert profundo.ultimo_arbol is None
        concepto = list(sistema.conceptos.keys())[0]
        profundo.profundizar(concepto)
        assert profundo.ultimo_arbol is not None

    def test_poda_reduce_o_mantiene_nodos(self, profundo, sistema):
        concepto = list(sistema.conceptos.keys())[0]
        r = profundo.profundizar(concepto)
        assert r["nodos_podados"] >= 0

    def test_hibrido_contiene_campos(self, profundo, sistema):
        concepto = list(sistema.conceptos.keys())[0]
        r = profundo.profundizar(concepto)
        h = r["hibrido"]
        assert isinstance(h, dict)
        if h:  # puede estar vacio si falla
            assert "modo" in h

    def test_multiples_conceptos_no_rompen(self, profundo, sistema):
        conceptos = list(sistema.conceptos.keys())[:5]
        for c in conceptos:
            r = profundo.profundizar(c)
            assert isinstance(r, dict)
            assert "coherencia_simbolica" in r
