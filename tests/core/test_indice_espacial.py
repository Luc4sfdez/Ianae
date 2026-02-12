"""Tests para IndiceEspacial."""
import pytest
import numpy as np
from src.core.indice_espacial import IndiceEspacial


@pytest.fixture
def indice():
    return IndiceEspacial(dimension=5)


def test_agregar_y_buscar(indice):
    """Agregar vectores y buscar similares."""
    indice.agregar("A", np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    indice.agregar("B", np.array([0.9, 0.1, 0.0, 0.0, 0.0]))
    indice.agregar("C", np.array([0.0, 1.0, 0.0, 0.0, 0.0]))

    resultados = indice.buscar_similares(np.array([1.0, 0.0, 0.0, 0.0, 0.0]), top_k=2)
    assert len(resultados) == 2
    # A deberia ser el mas similar (es identico)
    assert resultados[0][0] == "A"
    assert resultados[0][1] > 0.99


def test_actualizar(indice):
    """Actualizar vector de concepto existente."""
    indice.agregar("A", np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    indice.actualizar("A", np.array([0.0, 1.0, 0.0, 0.0, 0.0]))

    resultados = indice.buscar_similares(np.array([0.0, 1.0, 0.0, 0.0, 0.0]), top_k=1)
    assert resultados[0][0] == "A"
    assert resultados[0][1] > 0.99


def test_eliminar(indice):
    """Eliminar concepto del indice."""
    indice.agregar("A", np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    indice.agregar("B", np.array([0.0, 1.0, 0.0, 0.0, 0.0]))
    assert indice.size == 2

    indice.eliminar("A")
    assert indice.size == 1
    assert not indice.contiene("A")
    assert indice.contiene("B")


def test_excluir_consulta(indice):
    """Excluir un id de los resultados."""
    indice.agregar("A", np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    indice.agregar("B", np.array([0.9, 0.1, 0.0, 0.0, 0.0]))

    resultados = indice.buscar_similares(
        np.array([1.0, 0.0, 0.0, 0.0, 0.0]), top_k=5, excluir_id="A"
    )
    nombres = [r[0] for r in resultados]
    assert "A" not in nombres


def test_muchos_vectores(indice):
    """Funciona con muchos vectores (prueba redimensionamiento)."""
    for i in range(200):
        vec = np.random.randn(5)
        indice.agregar(f"v{i}", vec)

    assert indice.size == 200
    resultados = indice.buscar_similares(np.random.randn(5), top_k=10)
    assert len(resultados) == 10


def test_buscar_vacio(indice):
    """Buscar en indice vacio retorna lista vacia."""
    resultados = indice.buscar_similares(np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    assert resultados == []


def test_similitudes_en_rango(indice):
    """Similitudes deben estar entre -1 y 1."""
    for i in range(20):
        indice.agregar(f"v{i}", np.random.randn(5))

    resultados = indice.buscar_similares(np.random.randn(5), top_k=20)
    for _, sim in resultados:
        assert -1.0 - 1e-9 <= sim <= 1.0 + 1e-9
