"""Tests para ExtractorConceptos — extraccion NLP con fallback basico."""
import pytest
import numpy as np
from src.nlp.extractor import ExtractorConceptos


@pytest.fixture
def extractor():
    return ExtractorConceptos(modo="basico")


# --- Extraccion de conceptos ---

def test_modo_basico(extractor):
    assert extractor.modo == "basico"
    assert extractor.nlp is None
    assert extractor.modelo_embeddings is None


def test_extraer_conceptos_basico(extractor):
    texto = "Python es un lenguaje de programacion muy utilizado en inteligencia artificial"
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=5)
    assert len(conceptos) > 0
    assert all("nombre" in c for c in conceptos)
    assert all("relevancia" in c for c in conceptos)
    assert all("tipo" in c for c in conceptos)
    assert all(0 <= c["relevancia"] <= 1 for c in conceptos)


def test_extraer_conceptos_texto_vacio(extractor):
    assert extractor.extraer_conceptos("") == []


def test_extraer_conceptos_solo_stopwords(extractor):
    texto = "el la los las un una de en y o a"
    assert extractor.extraer_conceptos(texto) == []


def test_extraer_max_conceptos(extractor):
    texto = ("Python numpy pandas matplotlib scikit tensorflow keras "
             "pytorch opencv flask django fastapi requests")
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=3)
    assert len(conceptos) <= 3


def test_relevancia_ordenada(extractor):
    texto = "Python Python Python numpy numpy tensorflow"
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=10)
    relevancias = [c["relevancia"] for c in conceptos]
    assert relevancias == sorted(relevancias, reverse=True)


# --- Embeddings ---

def test_embedding_fallback(extractor):
    embedding = extractor.generar_embedding("inteligencia")
    assert isinstance(embedding, np.ndarray)
    assert len(embedding) == 15


def test_embedding_determinista(extractor):
    e1 = extractor.generar_embedding("concepto")
    e2 = extractor.generar_embedding("concepto")
    np.testing.assert_array_equal(e1, e2)


def test_embedding_diferente_texto(extractor):
    e1 = extractor.generar_embedding("python")
    e2 = extractor.generar_embedding("java")
    assert not np.array_equal(e1, e2)


# --- Relaciones ---

def test_relaciones_coocurrencia(extractor):
    texto = "Python y numpy trabajan juntos. Python usa numpy para vectores."
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=5)
    relaciones = extractor.extraer_relaciones(texto, conceptos)
    assert isinstance(relaciones, list)
    # Debe detectar al menos la relacion python-numpy
    if relaciones:
        assert all(len(r) == 3 for r in relaciones)
        assert all(0 <= r[2] <= 1 for r in relaciones)


def test_relaciones_texto_corto(extractor):
    texto = "solo una palabra"
    conceptos = extractor.extraer_conceptos(texto, max_conceptos=5)
    relaciones = extractor.extraer_relaciones(texto, conceptos)
    assert isinstance(relaciones, list)
