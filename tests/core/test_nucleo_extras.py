"""Tests adicionales: ciclo_vital, crear_conceptos_lucas, detectar_emergencias, informe."""
import pytest
import numpy as np


class TestCrearConceptosLucas:
    """Tests para crear_conceptos_lucas y crear_relaciones_lucas."""

    def test_crear_conceptos_lucas_retorna_lista(self, sistema_vacio):
        conceptos = sistema_vacio.crear_conceptos_lucas()
        assert isinstance(conceptos, list)
        assert len(conceptos) > 20

    def test_crear_conceptos_lucas_todos_registrados(self, sistema_vacio):
        conceptos = sistema_vacio.crear_conceptos_lucas()
        for c in conceptos:
            assert c in sistema_vacio.conceptos

    def test_crear_conceptos_lucas_categorias(self, sistema_vacio):
        sistema_vacio.crear_conceptos_lucas()
        assert len(sistema_vacio.categorias['tecnologias']) > 0
        assert len(sistema_vacio.categorias['proyectos']) > 0
        assert len(sistema_vacio.categorias['lucas_personal']) > 0

    def test_crear_relaciones_lucas(self, sistema_vacio):
        sistema_vacio.crear_conceptos_lucas()
        num_relaciones = sistema_vacio.crear_relaciones_lucas()
        assert num_relaciones > 20
        assert sistema_vacio.grafo.number_of_edges() > 0

    def test_crear_relaciones_cross_proyecto(self, sistema_poblado):
        assert sistema_poblado.metricas['proyectos_referenciados'] > 0


class TestCicloVital:
    """Tests para ciclo_vital."""

    def test_ciclo_vital_basico(self, sistema_poblado):
        resultados = sistema_poblado.ciclo_vital(num_ciclos=3, auto_mod=False)
        assert isinstance(resultados, list)
        assert len(resultados) == 3

    def test_ciclo_vital_incrementa_edad(self, sistema_poblado):
        edad_antes = sistema_poblado.metricas['edad']
        sistema_poblado.ciclo_vital(num_ciclos=5)
        assert sistema_poblado.metricas['edad'] == edad_antes + 5

    def test_ciclo_vital_con_auto_mod(self, sistema_poblado):
        resultados = sistema_poblado.ciclo_vital(num_ciclos=3, auto_mod=True)
        assert len(resultados) == 3
        for r in resultados:
            assert 'ciclo' in r
            assert 'concepto_inicial' in r

    def test_ciclo_vital_sin_conceptos(self, sistema_vacio):
        resultados = sistema_vacio.ciclo_vital(num_ciclos=3)
        assert len(resultados) == 0


class TestDetectarEmergencias:
    """Tests para detectar_emergencias."""

    def test_detectar_emergencias_sin_historial(self, sistema_poblado):
        resultado = sistema_poblado.detectar_emergencias()
        assert isinstance(resultado, str)
        assert 'historial' in resultado.lower() or 'Necesario' in resultado

    def test_detectar_emergencias_con_historial(self, sistema_poblado):
        for _ in range(5):
            sistema_poblado.activar('Python', pasos=3)
        resultado = sistema_poblado.detectar_emergencias()
        assert isinstance(resultado, str)

    def test_detectar_emergencias_umbral(self, sistema_poblado):
        for _ in range(5):
            sistema_poblado.activar('Python', pasos=3)
        resultado = sistema_poblado.detectar_emergencias(umbral_emergencia=0.9)
        assert isinstance(resultado, str)


class TestExplorarProyecto:
    """Tests para explorar_proyecto."""

    def test_explorar_proyecto_existente(self, sistema_poblado):
        resultado = sistema_poblado.explorar_proyecto('Tacografos', profundidad=2)
        assert isinstance(resultado, str)
        assert 'TACOGRAFOS' in resultado.upper() or len(resultado) > 0

    def test_explorar_proyecto_inexistente(self, sistema_poblado):
        resultado = sistema_poblado.explorar_proyecto('NoExiste')
        assert 'no encontrado' in resultado.lower()


class TestInformeLucas:
    """Tests para informe_lucas."""

    def test_informe_retorna_true(self, sistema_poblado):
        assert sistema_poblado.informe_lucas() is True


class TestRebuildNumpy:
    """Tests para _rebuild_numpy (reconstrucción desde dicts)."""

    def test_rebuild_sincroniza_indices(self, sistema_poblado, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_poblado.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        # Verificar que _rebuild_numpy sincronizó todo
        for nombre in cargado.conceptos:
            assert nombre in cargado._idx
            idx = cargado._idx[nombre]
            assert cargado._names[idx] == nombre

    def test_rebuild_sincroniza_adyacencia(self, sistema_poblado, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_poblado.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        # Verificar que la matriz de adyacencia tiene pesos
        n = cargado._n
        assert np.sum(cargado._adj[:n, :n]) > 0
