"""Tests para integracion de persistencia SQLite con ConceptosLucas."""
import pytest
import numpy as np
from src.core.nucleo import ConceptosLucas


@pytest.fixture
def sistema(tmp_path):
    """Sistema con persistencia apuntando a DB temporal."""
    s = ConceptosLucas(dim_vector=5, incertidumbre_base=0.0)
    s.persistencia.ruta_db = str(tmp_path / "test.db")
    s.persistencia._inicializar_tabla()
    s.añadir_concepto("Alpha", atributos=np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    s.añadir_concepto("Beta", atributos=np.array([0.0, 1.0, 0.0, 0.0, 0.0]))
    s.añadir_concepto("Gamma", atributos=np.array([0.0, 0.0, 1.0, 0.0, 0.0]))
    return s


def test_guardar_estado(sistema):
    """guardar_estado retorna True y escribe en DB."""
    assert sistema.guardar_estado("snap1")
    assert sistema.persistencia.contar_vectores() == 3


def test_guardar_y_cargar_mantiene_vectores(sistema):
    """Vectores se mantienen iguales despues de guardar/cargar."""
    vec_original = sistema.conceptos["Alpha"]["actual"].copy()

    sistema.guardar_estado("snap1")

    # Perturbar el vector en memoria
    sistema.conceptos["Alpha"]["actual"] = np.array([9.9, 9.9, 9.9, 9.9, 9.9])

    # Cargar restaura
    assert sistema.cargar_estado("snap1")
    np.testing.assert_array_almost_equal(
        sistema.conceptos["Alpha"]["actual"], vec_original
    )


def test_cargar_estado_inexistente(sistema):
    """Cargar snapshot que no existe retorna False."""
    assert not sistema.cargar_estado("no_existe")
