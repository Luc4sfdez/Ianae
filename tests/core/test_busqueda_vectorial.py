import pytest
import numpy as np
from src.core.nucleo import ConceptosLucas


@pytest.fixture
def sistema():
    """Sistema con conceptos básicos para testing."""
    s = ConceptosLucas(dim_vector=5)
    
    # Vectores conocidos para pruebas predecibles
    s.añadir_concepto("A", atributos=np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    s.añadir_concepto("B", atributos=np.array([0.8, 0.2, 0.0, 0.0, 0.0]))
    s.añadir_concepto("C", atributos=np.array([0.0, 1.0, 0.0, 0.0, 0.0]))
    s.añadir_concepto("D", atributos=np.array([0.0, 0.0, 1.0, 0.0, 0.0]))
    s.añadir_concepto("E", atributos=np.array([0.0, 0.0, 0.0, 1.0, 0.0]))
    
    return s


def test_buscar_concepto_existente(sistema):
    """Buscar un concepto existente retorna resultados."""
    resultados = sistema.buscar_por_similitud_coseno("A")
    assert isinstance(resultados, list)
    assert len(resultados) > 0


def test_buscar_concepto_inexistente(sistema):
    """Buscar concepto inexistente retorna lista vacía."""
    resultados = sistema.buscar_por_similitud_coseno("INEXISTENTE")
    assert resultados == []


def test_formato_resultados(sistema):
    """Cada resultado es una tupla (nombre, similitud)."""
    resultados = sistema.buscar_por_similitud_coseno("A")
    for resultado in resultados:
        assert isinstance(resultado, tuple)
        assert len(resultado) == 2
        nombre, sim = resultado
        assert isinstance(nombre, str)
        assert isinstance(sim, (float, np.floating))


def test_orden_descendente(sistema):
    """Resultados ordenados por similitud descendente."""
    resultados = sistema.buscar_por_similitud_coseno("A", top_k=10)
    similitudes = [sim for _, sim in resultados]
    assert similitudes == sorted(similitudes, reverse=True)


def test_busqueda_top_k(sistema):
    """top_k=2 retorna exactamente 2 resultados."""
    resultados = sistema.buscar_por_similitud_coseno("A", top_k=2)
    assert len(resultados) == 2


def test_similitud_rango(sistema):
    """Similitudes deben estar entre -1 y 1."""
    resultados = sistema.buscar_por_similitud_coseno("A", top_k=10)
    for nombre, sim in resultados:
        assert -1.0 <= sim <= 1.0 + 1e-9, f"{nombre}: sim={sim} fuera de rango"


def test_no_incluye_referencia(sistema):
    """El concepto buscado no aparece en sus propios resultados."""
    resultados = sistema.buscar_por_similitud_coseno("A", top_k=10)
    nombres = [r[0] for r in resultados]
    assert "A" not in nombres