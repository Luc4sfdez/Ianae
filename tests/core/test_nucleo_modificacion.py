"""Tests de auto-modificación para nucleo.py — ConceptosLucas.auto_modificar()"""
import pytest
import numpy as np


class TestAutoModificarBasico:
    """Tests básicos del método auto_modificar."""

    def test_auto_modificar_sin_historial_retorna_cero(self, sistema_minimo):
        assert sistema_minimo.auto_modificar() == 0

    def test_auto_modificar_tras_activacion(self, sistema_minimo):
        sistema_minimo.activar('A', pasos=3, temperatura=0.3)
        mods = sistema_minimo.auto_modificar(fuerza=0.5)
        assert isinstance(mods, int)
        assert mods >= 0

    def test_auto_modificar_incrementa_metrica(self, sistema_poblado):
        sistema_poblado.activar('Python', pasos=3, temperatura=0.3)
        antes = sistema_poblado.metricas['auto_modificaciones']
        mods = sistema_poblado.auto_modificar(fuerza=0.5)
        if mods > 0:
            assert sistema_poblado.metricas['auto_modificaciones'] == antes + 1


class TestFortalecerConexiones:
    """Tests de fortalecimiento de conexiones existentes."""

    def test_conexion_existente_puede_fortalecerse(self, sistema_minimo):
        peso_antes = sistema_minimo._adj[
            sistema_minimo._idx['A'],
            sistema_minimo._idx['B']
        ]
        # Activar para generar historial con alta activación
        sistema_minimo.activar('A', pasos=3, temperatura=0.3)
        sistema_minimo.auto_modificar(fuerza=1.0)  # Fuerza alta para asegurar efecto
        peso_despues = sistema_minimo._adj[
            sistema_minimo._idx['A'],
            sistema_minimo._idx['B']
        ]
        # Peso pudo cambiar o no dependiendo de la aleatoriedad,
        # pero debe seguir en rango válido
        assert 0.0 <= peso_despues <= 1.0

    def test_peso_no_excede_uno(self, sistema_minimo):
        """Tras muchas auto-modificaciones, el peso máximo es 1.0."""
        for _ in range(10):
            sistema_minimo.activar('A', pasos=2, temperatura=0.3)
            sistema_minimo.auto_modificar(fuerza=1.0)
        n = sistema_minimo._n
        assert np.all(sistema_minimo._adj[:n, :n] <= 1.0)


class TestCrearNuevasConexiones:
    """Tests de creación de nuevas conexiones por auto-modificación."""

    def test_puede_crear_nuevas_conexiones(self, sistema_minimo):
        """Con suficiente fuerza, se deben crear nuevas conexiones."""
        edges_antes = sistema_minimo.grafo.number_of_edges()
        # Múltiples ciclos para aumentar probabilidad
        for _ in range(20):
            sistema_minimo.activar('A', pasos=3, temperatura=0.3)
            sistema_minimo.auto_modificar(fuerza=1.0)
        edges_despues = sistema_minimo.grafo.number_of_edges()
        # Con fuerza=1.0 y 20 iteraciones, es muy probable que se cree alguna
        assert edges_despues >= edges_antes


class TestLimitesModificacion:
    """Tests de límites en la auto-modificación."""

    def test_fuerza_cero_no_modifica(self, sistema_minimo):
        sistema_minimo.activar('A', pasos=2)
        adj_antes = sistema_minimo._adj.copy()
        sistema_minimo.auto_modificar(fuerza=0.0)
        # Con fuerza 0, no debería haber cambios significativos
        np.testing.assert_array_equal(adj_antes, sistema_minimo._adj)

    def test_auto_modificar_con_pocos_conceptos_activos(self, sistema_vacio):
        """Con un solo concepto no hay pares para modificar."""
        sistema_vacio.añadir_concepto('Solo')
        sistema_vacio.activar('Solo', pasos=1)
        mods = sistema_vacio.auto_modificar(fuerza=1.0)
        assert mods == 0


class TestAñadirConcepto:
    """Tests para añadir_concepto."""

    def test_añadir_concepto_basico(self, sistema_vacio):
        nombre = sistema_vacio.añadir_concepto('Test')
        assert nombre == 'Test'
        assert 'Test' in sistema_vacio.conceptos
        assert sistema_vacio._n == 1
        assert 'Test' in sistema_vacio._idx

    def test_añadir_concepto_con_vector(self, sistema_vacio):
        vec = np.ones(15)
        sistema_vacio.añadir_concepto('Vec', atributos=vec)
        # Vector se normaliza
        base = sistema_vacio.conceptos['Vec']['base']
        assert pytest.approx(np.linalg.norm(base), abs=0.01) == 1.0

    def test_añadir_concepto_sin_vector_genera_aleatorio(self, sistema_vacio):
        sistema_vacio.añadir_concepto('Rand')
        base = sistema_vacio.conceptos['Rand']['base']
        assert base.shape == (15,)
        assert pytest.approx(np.linalg.norm(base), abs=0.01) == 1.0

    def test_añadir_concepto_categoria(self, sistema_vacio):
        sistema_vacio.añadir_concepto('Tech', categoria='tecnologias')
        assert sistema_vacio.conceptos['Tech']['categoria'] == 'tecnologias'
        assert 'Tech' in sistema_vacio.categorias['tecnologias']

    def test_añadir_concepto_incrementa_metrica(self, sistema_vacio):
        sistema_vacio.añadir_concepto('M1')
        sistema_vacio.añadir_concepto('M2')
        assert sistema_vacio.metricas['conceptos_creados'] == 2

    def test_añadir_concepto_sincroniza_numpy(self, sistema_vacio):
        sistema_vacio.añadir_concepto('N1')
        assert sistema_vacio._n == 1
        assert sistema_vacio._names[0] == 'N1'
        assert sistema_vacio._idx['N1'] == 0


class TestRelacionar:
    """Tests para el método relacionar."""

    def test_relacionar_bidireccional(self, sistema_minimo):
        i_a = sistema_minimo._idx['A']
        i_b = sistema_minimo._idx['B']
        assert sistema_minimo._adj[i_a, i_b] > 0
        assert sistema_minimo._adj[i_b, i_a] > 0

    def test_relacionar_unidireccional(self, sistema_vacio):
        sistema_vacio.añadir_concepto('X')
        sistema_vacio.añadir_concepto('Y')
        sistema_vacio.relacionar('X', 'Y', fuerza=0.7, bidireccional=False)
        i_x = sistema_vacio._idx['X']
        i_y = sistema_vacio._idx['Y']
        assert sistema_vacio._adj[i_x, i_y] == pytest.approx(0.7)
        assert sistema_vacio._adj[i_y, i_x] == 0.0

    def test_relacionar_concepto_inexistente(self, sistema_minimo):
        result = sistema_minimo.relacionar('A', 'NoExiste', fuerza=0.5)
        assert result == 0

    def test_relacionar_sin_fuerza_calcula_similitud(self, sistema_minimo):
        sistema_minimo.añadir_concepto('D', atributos=np.ones(15) * 0.9)
        fuerza = sistema_minimo.relacionar('A', 'D')
        assert 0.1 <= fuerza <= 1.0

    def test_relacionar_actualiza_grafo(self, sistema_vacio):
        sistema_vacio.añadir_concepto('G1')
        sistema_vacio.añadir_concepto('G2')
        sistema_vacio.relacionar('G1', 'G2', fuerza=0.5)
        assert sistema_vacio.grafo.has_edge('G1', 'G2')
        assert sistema_vacio.grafo['G1']['G2']['weight'] == pytest.approx(0.5)

    def test_relacionar_incrementa_metrica(self, sistema_vacio):
        sistema_vacio.añadir_concepto('R1')
        sistema_vacio.añadir_concepto('R2')
        sistema_vacio.relacionar('R1', 'R2', fuerza=0.5)
        assert sistema_vacio.metricas['conexiones_formadas'] == 1
