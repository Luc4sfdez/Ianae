"""Tests para IntegradorSimbolico — puente difuso/simbolico."""
import pytest
import numpy as np
from src.core.nucleo import ConceptosLucas
from src.core.integracion_simbolica import IntegradorSimbolico
from src.core.pensamiento_simbolico import ThoughtNode


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    s.añadir_concepto("Python", atributos=np.random.rand(15))
    s.añadir_concepto("OpenCV", atributos=np.random.rand(15))
    s.añadir_concepto("Numpy", atributos=np.random.rand(15))
    s.relacionar("Python", "OpenCV", fuerza=0.8)
    s.relacionar("Python", "Numpy", fuerza=0.9)
    s.relacionar("OpenCV", "Numpy", fuerza=0.5)
    return s


@pytest.fixture
def integrador(sistema):
    return IntegradorSimbolico(sistema)


# --- Tests conversion ---

def test_difuso_a_simbolico(integrador):
    node = integrador.difuso_a_simbolico("Python")
    assert node is not None
    assert isinstance(node, ThoughtNode)
    assert node.concept_id == "Python"
    assert node.vector.shape == (15,)
    assert 0 <= node.activation <= 1
    assert 0 <= node.coherence <= 1


def test_difuso_a_simbolico_inexistente(integrador):
    assert integrador.difuso_a_simbolico("NoExiste") is None


def test_simbolico_a_difuso(integrador):
    node = ThoughtNode(
        concept_id="Test",
        activation=0.7,
        vector=np.random.rand(15),
        coherence=0.8,
        origin="propagation",
    )
    data = integrador.simbolico_a_difuso(node)
    assert "actual" in data
    assert "base" in data
    assert data["categoria"] == "simbolico"
    assert data["fuerza"] == 0.8
    np.testing.assert_array_equal(data["actual"], node.vector)


def test_roundtrip_difuso_simbolico_difuso(integrador, sistema):
    """Convertir difuso->simbolico->difuso conserva el vector."""
    node = integrador.difuso_a_simbolico("Python")
    data = integrador.simbolico_a_difuso(node)
    vec_original = sistema.conceptos["Python"]["actual"]
    np.testing.assert_array_almost_equal(data["actual"], vec_original)


# --- Tests pensamiento hibrido ---

def test_pensamiento_hibrido_basico(integrador):
    resultado = integrador.ejecutar_pensamiento_hibrido("Python", profundidad=2)
    assert resultado["modo"] == "hibrido"
    assert resultado["tema"] == "Python"
    assert resultado["nodos_simbolicos"] > 0
    assert len(resultado["conceptos_activados"]) > 0


def test_pensamiento_hibrido_concepto_inexistente(integrador):
    resultado = integrador.ejecutar_pensamiento_hibrido("NoExiste")
    assert "error" in resultado


def test_pensamiento_hibrido_coherencia(integrador):
    resultado = integrador.ejecutar_pensamiento_hibrido("Python", profundidad=3)
    assert 0.0 <= resultado["coherencia_media"] <= 1.0
    assert 0.0 <= resultado["activacion_media"] <= 1.0


def test_representacion_simbolica(integrador):
    resultado = integrador.ejecutar_pensamiento_hibrido("Python", profundidad=2)
    rep = resultado["representacion_simbolica"]
    assert isinstance(rep, str)
    assert "Python" in rep or len(rep) > 0
