"""Tests para PensamientoLucas incluyendo pensamiento recursivo."""
import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'core'))
from nucleo import ConceptosLucas
from emergente import PensamientoLucas


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=15)
    # Crear conceptos de diferentes categorias
    s.añadir_concepto('Python', categoria='tecnologias')
    s.añadir_concepto('OpenCV', categoria='tecnologias')
    s.añadir_concepto('Tacografos', categoria='proyectos')
    s.añadir_concepto('IANAE', categoria='proyectos')
    s.añadir_concepto('Lucas', categoria='lucas_personal')
    s.añadir_concepto('Creatividad', categoria='conceptos_ianae')
    # Relaciones
    s.relacionar('Python', 'OpenCV', fuerza=0.8)
    s.relacionar('Python', 'Tacografos', fuerza=0.7)
    s.relacionar('Python', 'IANAE', fuerza=0.9)
    s.relacionar('Lucas', 'Python', fuerza=0.8)
    s.relacionar('Creatividad', 'IANAE', fuerza=0.6)
    return s


@pytest.fixture
def pensamiento(sistema):
    return PensamientoLucas(sistema)


class TestPensamientoRecursivo:
    def test_retorna_estructura(self, pensamiento):
        result = pensamiento.pensar_recursivo('Python', max_ciclos=3)
        assert isinstance(result, dict)
        assert 'ciclos' in result
        assert 'convergencia' in result
        assert 'activaciones_finales' in result
        assert 'coherencia_final' in result
        assert 'traza' in result

    def test_traza_formato(self, pensamiento):
        result = pensamiento.pensar_recursivo('Python', max_ciclos=2)
        traza = result['traza']
        assert len(traza) > 0
        for entry in traza:
            assert len(entry) == 3
            ciclo, coherencia, top3 = entry
            assert isinstance(ciclo, int)
            assert isinstance(coherencia, float)
            assert isinstance(top3, list)

    def test_max_ciclos_respetado(self, pensamiento):
        result = pensamiento.pensar_recursivo('Python', max_ciclos=2)
        assert result['ciclos'] <= 2

    def test_convergencia_posible(self, pensamiento):
        # Con umbral alto deberia converger rapido
        result = pensamiento.pensar_recursivo('Python', max_ciclos=10, umbral_convergencia=1.0)
        assert result['convergencia'] is True
        assert result['ciclos'] <= 10


class TestCoherencia:
    def test_coherencia_entre_0_y_1(self, pensamiento):
        activaciones = {'Python': 0.8, 'OpenCV': 0.6, 'Tacografos': 0.4}
        c = pensamiento._evaluar_coherencia_activacion(activaciones)
        assert 0.0 <= c <= 1.0

    def test_coherencia_vacia(self, pensamiento):
        c = pensamiento._evaluar_coherencia_activacion({})
        assert c == 1.0

    def test_coherencia_un_concepto(self, pensamiento):
        c = pensamiento._evaluar_coherencia_activacion({'Python': 0.8})
        assert c == 1.0

    def test_penaliza_echo_chamber(self, sistema):
        """Conceptos de misma categoria -> penalizacion."""
        # Agregar mas conceptos de la misma categoria
        sistema.añadir_concepto('Java', categoria='tecnologias')
        sistema.añadir_concepto('Go', categoria='tecnologias')
        sistema.añadir_concepto('Rust', categoria='tecnologias')
        p = PensamientoLucas(sistema)
        # Todos tecnologias -> echo chamber
        activaciones = {'Python': 0.8, 'OpenCV': 0.7, 'Java': 0.6, 'Go': 0.5}
        c = p._evaluar_coherencia_activacion(activaciones)
        # Deberia tener penalizacion echo chamber
        assert c < 1.0


class TestRefinamiento:
    def test_sube_temperatura_coherencia_baja(self, pensamiento):
        t = pensamiento._refinar_activacion({'a': 1}, 0.3, 0.5)
        assert t > 0.5

    def test_baja_temperatura_coherencia_alta_pocos(self, pensamiento):
        t = pensamiento._refinar_activacion({'a': 1, 'b': 1}, 0.8, 0.5)
        assert t < 0.5

    def test_mantiene_temperatura_coherencia_media(self, pensamiento):
        t = pensamiento._refinar_activacion({'a': 1, 'b': 1, 'c': 1, 'd': 1}, 0.5, 0.5)
        assert t == 0.5
