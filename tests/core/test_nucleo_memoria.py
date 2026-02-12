"""Tests para integracion de MemoriaAsociativaV2 con ConceptosLucas."""
import pytest
import numpy as np
from src.core.nucleo import ConceptosLucas


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=5, incertidumbre_base=0.0)
    s.añadir_concepto("Python", atributos=np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    s.añadir_concepto("OpenCV", atributos=np.array([0.5, 0.5, 0.0, 0.0, 0.0]))
    s.añadir_concepto("Numpy", atributos=np.array([0.8, 0.2, 0.0, 0.0, 0.0]))
    s.relacionar("Python", "OpenCV", fuerza=0.8)
    s.relacionar("Python", "Numpy", fuerza=0.9)
    return s


def test_nucleo_tiene_memoria(sistema):
    """El nucleo debe tener atributo memoria de tipo MemoriaAsociativaV2."""
    assert hasattr(sistema, "memoria")
    from src.core.memoria_v2 import MemoriaAsociativaV2
    assert isinstance(sistema.memoria, MemoriaAsociativaV2)


def test_activar_almacena_en_memoria(sistema):
    """Activar un concepto debe almacenar resultados en memoria."""
    assert sistema.memoria.estadisticas()["total"] == 0
    sistema.activar("Python", pasos=2)
    stats = sistema.memoria.estadisticas()
    assert stats["total"] > 0


def test_consultar_memoria(sistema):
    """consultar_memoria debe retornar resultados tras activacion."""
    sistema.activar("Python", pasos=2)
    resultados = sistema.consultar_memoria("Python")
    assert isinstance(resultados, list)
    # Debe haber al menos una entrada con "Python" en la clave
    assert len(resultados) > 0


def test_memoria_capacidad():
    """La memoria del nucleo debe respetar la capacidad configurada."""
    s = ConceptosLucas(dim_vector=5, incertidumbre_base=0.0)
    assert s.memoria.capacidad == 1000


def test_consultar_memoria_vacia(sistema):
    """Consultar memoria sin activaciones previas retorna lista vacia."""
    resultados = sistema.consultar_memoria("inexistente")
    assert resultados == []
