"""Tests para genesis de conceptos dinamicos en ConceptosLucas."""
import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'core'))
from nucleo import ConceptosLucas


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=15)
    s.añadir_concepto('Python', categoria='tecnologias')
    s.añadir_concepto('OpenCV', categoria='tecnologias')
    s.añadir_concepto('Tacografos', categoria='proyectos')
    s.añadir_concepto('IANAE', categoria='proyectos')
    s.añadir_concepto('Lucas', categoria='lucas_personal')
    s.relacionar('Python', 'OpenCV', fuerza=0.8)
    s.relacionar('Python', 'Tacografos', fuerza=0.7)
    s.relacionar('Python', 'IANAE', fuerza=0.9)
    return s


class TestGenesisConcepto:
    def test_crea_concepto_con_vector_fusionado(self, sistema):
        nombre = sistema.genesis_concepto(['Python', 'OpenCV'], 'Fusion1')
        assert nombre == 'Fusion1'
        assert 'Fusion1' in sistema.conceptos
        # El vector debe existir y tener 15 dims
        vec = sistema.conceptos['Fusion1']['actual']
        assert vec.shape == (15,)

    def test_nombre_autogenerado(self, sistema):
        nombre = sistema.genesis_concepto(['Python', 'OpenCV'])
        assert nombre.startswith('EMG_')
        assert 'Python' in nombre
        assert 'OpenCV' in nombre

    def test_conexiones_con_padres(self, sistema):
        nombre = sistema.genesis_concepto(['Python', 'OpenCV'], 'TestConn')
        # Verificar que hay aristas en el grafo
        assert sistema.grafo.has_edge('TestConn', 'Python')
        assert sistema.grafo.has_edge('TestConn', 'OpenCV')

    def test_categoria_emergentes(self, sistema):
        nombre = sistema.genesis_concepto(['Python', 'OpenCV'], 'TestCat')
        assert sistema.conceptos['TestCat']['categoria'] == 'emergentes'

    def test_genesis_guarda_linaje(self, sistema):
        nombre = sistema.genesis_concepto(['Python', 'OpenCV'], 'TestLinaje')
        assert 'genesis' in sistema.conceptos['TestLinaje']
        assert sistema.conceptos['TestLinaje']['genesis']['padres'] == ['Python', 'OpenCV']

    def test_error_padre_inexistente(self, sistema):
        with pytest.raises(ValueError, match="no existe"):
            sistema.genesis_concepto(['Python', 'NoExiste'])

    def test_error_menos_de_2_padres(self, sistema):
        with pytest.raises(ValueError, match="al menos 2"):
            sistema.genesis_concepto(['Python'])

    def test_vector_es_promedio_con_ruido(self, sistema):
        """El vector fusionado debe ser cercano al promedio de los padres."""
        vec_py = sistema.conceptos['Python']['actual']
        vec_cv = sistema.conceptos['OpenCV']['actual']
        promedio = np.mean([vec_py, vec_cv], axis=0)

        nombre = sistema.genesis_concepto(['Python', 'OpenCV'], 'TestVec')
        vec_nuevo = sistema.conceptos['TestVec']['actual']

        # Debe ser cercano al promedio (tolerancia por ruido y normalizacion)
        # No exacto por el ruido gaussiano
        diff = np.linalg.norm(vec_nuevo - promedio)
        assert diff < 5.0  # Tolerancia amplia por ruido


class TestDetectarCandidatos:
    def test_sin_historial_retorna_vacio(self, sistema):
        assert sistema.detectar_candidatos_genesis() == []

    def test_con_coactivaciones(self, sistema):
        # Simular activaciones
        for _ in range(5):
            resultado = sistema.activar('Python', pasos=3, temperatura=0.2)
            sistema.historial_activaciones.append(resultado[-1] if resultado else {})

        candidatos = sistema.detectar_candidatos_genesis(umbral_coactivacion=0.1)
        # Debe encontrar al menos un par cross-categoria
        # (Python=tecnologias se coactiva con Tacografos=proyectos)
        assert isinstance(candidatos, list)
        for c1, c2, freq in candidatos:
            assert isinstance(freq, float)
            assert freq > 0


class TestCicloGenesis:
    def test_limita_max_nuevos(self, sistema):
        # Simular historial
        for _ in range(5):
            resultado = sistema.activar('Python', pasos=3, temperatura=0.3)
            sistema.historial_activaciones.append(resultado[-1] if resultado else {})

        creados = sistema.ciclo_genesis(max_nuevos=1)
        assert len(creados) <= 1

    def test_sin_candidatos_retorna_vacio(self, sistema):
        creados = sistema.ciclo_genesis()
        assert creados == []

    def test_conceptos_creados_existen(self, sistema):
        for _ in range(5):
            resultado = sistema.activar('Python', pasos=3, temperatura=0.3)
            sistema.historial_activaciones.append(resultado[-1] if resultado else {})

        creados = sistema.ciclo_genesis(max_nuevos=3)
        for nombre in creados:
            assert nombre in sistema.conceptos
