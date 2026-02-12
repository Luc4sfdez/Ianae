"""Tests para InsightsEngine — patrones, recomendaciones, predicciones."""
import pytest
import numpy as np

from src.core.nucleo import ConceptosLucas
from src.core.emergente import PensamientoLucas
from src.core.insights import InsightsEngine


@pytest.fixture
def sistema():
    """Sistema con 6+ conceptos multi-categoria, relaciones y activaciones."""
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    # Tecnologias
    s.añadir_concepto("Python", categoria="tecnologias")
    s.añadir_concepto("OpenCV", categoria="tecnologias")
    s.añadir_concepto("Docker", categoria="tecnologias")
    # Proyectos
    s.añadir_concepto("Tacografos", categoria="proyectos")
    s.añadir_concepto("RAG_System", categoria="proyectos")
    # Personal
    s.añadir_concepto("Lucas", categoria="lucas_personal")
    # IANAE
    s.añadir_concepto("IANAE", categoria="conceptos_ianae")
    # Herramientas
    s.añadir_concepto("Automatizacion", categoria="herramientas")

    # Relaciones que forman un grafo interesante
    s.relacionar("Python", "OpenCV", fuerza=0.9)
    s.relacionar("Python", "Tacografos", fuerza=0.85)
    s.relacionar("OpenCV", "Tacografos", fuerza=0.95)
    s.relacionar("Python", "RAG_System", fuerza=0.8)
    s.relacionar("RAG_System", "IANAE", fuerza=0.9)
    s.relacionar("Lucas", "Python", fuerza=0.95)
    s.relacionar("Lucas", "IANAE", fuerza=0.9)
    s.relacionar("Docker", "RAG_System", fuerza=0.7)
    s.relacionar("Automatizacion", "Python", fuerza=0.85)

    # Generar historial de activaciones
    for _ in range(5):
        s.activar("Python", pasos=2, temperatura=0.1)
        s.activar("Tacografos", pasos=2, temperatura=0.1)
    return s


@pytest.fixture
def engine(sistema):
    return InsightsEngine(sistema)


@pytest.fixture
def engine_con_pensamiento(sistema):
    pensamiento = PensamientoLucas(sistema)
    return InsightsEngine(sistema, pensamiento=pensamiento)


# ==================== TestDetectarPatrones ====================

class TestDetectarPatrones:
    def test_estructura_resultado(self, engine):
        r = engine.detectar_patrones()
        assert "comunidades" in r
        assert "puentes" in r
        assert "clusters_densos" in r
        assert "conceptos_aislados" in r
        assert "patrones_emergentes" in r
        assert "candidatos_genesis" in r
        assert "narrativa" in r

    def test_comunidades_no_vacias(self, engine):
        r = engine.detectar_patrones()
        assert len(r["comunidades"]) > 0

    def test_union_comunidades_todos_nodos(self, engine):
        r = engine.detectar_patrones()
        todos = set()
        for com in r["comunidades"]:
            todos.update(com)
        nodos_grafo = set(engine._grafo.nodes)
        assert todos == nodos_grafo

    def test_puentes_formato(self, engine):
        r = engine.detectar_patrones()
        for puente in r["puentes"]:
            assert "concepto" in puente
            assert "centralidad" in puente
            assert isinstance(puente["centralidad"], float)
            assert puente["centralidad"] >= 0

    def test_clustering_valido(self, engine):
        r = engine.detectar_patrones()
        for cluster in r["clusters_densos"]:
            assert "concepto" in cluster
            assert "coeficiente" in cluster
            assert 0 <= cluster["coeficiente"] <= 1

    def test_narrativa_no_vacia(self, engine):
        r = engine.detectar_patrones()
        assert len(r["narrativa"]) > 0
        assert "comunidades" in r["narrativa"].lower() or "comunidad" in r["narrativa"].lower()

    def test_emergentes_es_string(self, engine):
        r = engine.detectar_patrones()
        assert isinstance(r["patrones_emergentes"], str)

    def test_genesis_es_lista(self, engine):
        r = engine.detectar_patrones()
        assert isinstance(r["candidatos_genesis"], list)


# ==================== TestRecomendaciones ====================

class TestRecomendaciones:
    def test_recomendaciones_globales(self, engine):
        r = engine.generar_recomendaciones()
        assert "explorar" in r
        assert "conectar" in r
        assert "narrativa" in r
        assert isinstance(r["explorar"], list)

    def test_recomendaciones_por_concepto(self, engine):
        r = engine.generar_recomendaciones(concepto="Python")
        assert "explorar" in r
        assert "conectar" in r
        assert len(r["narrativa"]) > 0

    def test_concepto_inexistente(self, engine):
        r = engine.generar_recomendaciones(concepto="NoExiste")
        assert "no encontrado" in r["narrativa"].lower() or len(r["explorar"]) == 0

    def test_explorar_formato(self, engine):
        r = engine.generar_recomendaciones()
        for item in r["explorar"]:
            assert "concepto" in item

    def test_conectar_formato(self, engine):
        r = engine.generar_recomendaciones(concepto="Tacografos")
        for item in r["conectar"]:
            assert "concepto" in item
            assert "distancia" in item

    def test_max_resultados_respetado(self, engine):
        r = engine.generar_recomendaciones(max_resultados=2)
        assert len(r["explorar"]) <= 2

    def test_narrativa_no_vacia(self, engine):
        r = engine.generar_recomendaciones()
        assert len(r["narrativa"]) > 0


# ==================== TestPredicciones ====================

class TestPredicciones:
    def test_estructura_resultado(self, engine):
        r = engine.analisis_predictivo()
        assert "tendencias" in r
        assert "gaps_conocimiento" in r
        assert "proximas_tecnologias" in r
        assert "patrones_personales" in r
        assert "narrativa" in r

    def test_tendencias_formato(self, engine):
        r = engine.analisis_predictivo()
        for t in r["tendencias"]:
            assert "concepto" in t
            assert "frecuencia" in t
            assert "recencia" in t
            assert "direccion" in t

    def test_tendencias_valores_validos(self, engine):
        r = engine.analisis_predictivo()
        for t in r["tendencias"]:
            assert 0 <= t["frecuencia"] <= 1
            assert 0 <= t["recencia"] <= 1
            assert t["direccion"] in ("ascendente", "descendente", "estable")

    def test_gaps_formato(self, engine):
        r = engine.analisis_predictivo()
        for g in r["gaps_conocimiento"]:
            assert "categoria" in g
            assert "centralidad_media" in g
            assert "deficit" in g

    def test_proximas_formato(self, engine):
        r = engine.analisis_predictivo()
        for p in r["proximas_tecnologias"]:
            assert "concepto" in p
            assert "centralidad" in p
            assert "score_prediccion" in p

    def test_narrativa_no_vacia(self, engine):
        r = engine.analisis_predictivo()
        assert len(r["narrativa"]) > 0


# ==================== TestNarrativas ====================

class TestNarrativas:
    def test_narrativa_patrones_contiene_comunidades(self, engine):
        r = engine.detectar_patrones()
        assert "comunidad" in r["narrativa"].lower()

    def test_narrativa_recomendaciones_con_concepto(self, engine):
        r = engine.generar_recomendaciones(concepto="Python")
        assert "Python" in r["narrativa"]

    def test_narrativa_predicciones_contiene_tendencias(self, engine):
        r = engine.analisis_predictivo()
        narrativa = r["narrativa"].lower()
        assert "tendencia" in narrativa or "historial" in narrativa


# ==================== TestGrafoInsuficiente ====================

class TestGrafoInsuficiente:
    def test_patrones_grafo_vacio(self):
        s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        e = InsightsEngine(s)
        r = e.detectar_patrones()
        assert r["comunidades"] == []
        assert "insuficiente" in r["narrativa"].lower()

    def test_recomendaciones_grafo_vacio(self):
        s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        e = InsightsEngine(s)
        r = e.generar_recomendaciones()
        assert r["explorar"] == []

    def test_predictivo_grafo_vacio(self):
        s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
        e = InsightsEngine(s)
        r = e.analisis_predictivo()
        assert r["tendencias"] == []
