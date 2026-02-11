"""Tests de propagación para nucleo.py — ConceptosLucas.activar()"""
import pytest
import numpy as np


class TestActivarBasico:
    """Tests básicos del método activar (propagación matricial)."""

    def test_activar_concepto_existente(self, sistema_minimo):
        resultado = sistema_minimo.activar('A', pasos=2)
        assert isinstance(resultado, list)
        assert len(resultado) == 3  # estado_inicial + 2 pasos

    def test_activar_concepto_inexistente(self, sistema_minimo):
        resultado = sistema_minimo.activar('NoExiste', pasos=2)
        assert resultado == []

    def test_activar_primer_paso_tiene_concepto_inicial(self, sistema_minimo):
        resultado = sistema_minimo.activar('A', pasos=1)
        assert resultado[0]['A'] == 1.0  # El concepto semilla arranca en 1.0

    def test_activar_propaga_a_vecinos(self, sistema_poblado):
        resultado = sistema_poblado.activar('Python', pasos=3, temperatura=0.1)
        activacion_final = resultado[-1]
        # Al menos algún vecino directo de Python debe tener activación > 0
        vecinos_python = [c for c, a in activacion_final.items()
                         if c != 'Python' and a > 0.001]
        assert len(vecinos_python) > 0

    def test_activar_incrementa_contadores(self, sistema_minimo):
        activaciones_antes = sistema_minimo.conceptos['A']['activaciones']
        ciclos_antes = sistema_minimo.metricas['ciclos_pensamiento']
        sistema_minimo.activar('A', pasos=2)
        assert sistema_minimo.conceptos['A']['activaciones'] > activaciones_antes
        assert sistema_minimo.metricas['ciclos_pensamiento'] == ciclos_antes + 1

    def test_activar_registra_historial(self, sistema_minimo):
        assert len(sistema_minimo.historial_activaciones) == 0
        sistema_minimo.activar('A', pasos=2)
        assert len(sistema_minimo.historial_activaciones) == 1
        entry = sistema_minimo.historial_activaciones[0]
        assert entry['inicio'] == 'A'
        assert entry['pasos'] == 2
        assert isinstance(entry['resultado'], dict)


class TestActivarTemperatura:
    """Tests de propagación con distintas temperaturas."""

    def test_temperatura_cero_es_determinista_estructura(self, sistema_poblado):
        """Con temperatura 0, la estructura del resultado es válida."""
        resultado = sistema_poblado.activar('Python', pasos=2, temperatura=0.0)
        assert len(resultado) == 3
        # Cada paso es un dict con todos los conceptos
        for paso in resultado:
            assert isinstance(paso, dict)
            assert len(paso) == len(sistema_poblado.conceptos)

    def test_temperatura_alta_produce_resultado_valido(self, sistema_poblado):
        resultado = sistema_poblado.activar('Python', pasos=2, temperatura=0.9)
        assert len(resultado) == 3
        for paso in resultado:
            for val in paso.values():
                assert 0.0 <= val <= 1.0


class TestActivarConDecay:
    """Tests de propagación con decaimiento por pasos."""

    def test_mas_pasos_extiende_resultado(self, sistema_poblado):
        r2 = sistema_poblado.activar('Python', pasos=2)
        r5 = sistema_poblado.activar('Python', pasos=5)
        assert len(r5) > len(r2)

    def test_activaciones_normalizadas(self, sistema_minimo):
        """Todas las activaciones deben estar en [0, 1] tras clip."""
        resultado = sistema_minimo.activar('A', pasos=3, temperatura=0.2)
        for paso in resultado:
            for val in paso.values():
                assert 0.0 <= val <= 1.0


class TestActivarCiclos:
    """Tests de propagación con ciclos en la red."""

    def test_propagacion_con_ciclo(self, sistema_minimo):
        """Añadir ciclo A-B-C-A y verificar que no explota."""
        sistema_minimo.relacionar('C', 'A', fuerza=0.5)
        resultado = sistema_minimo.activar('A', pasos=5, temperatura=0.1)
        assert len(resultado) == 6
        # No debe haber valores NaN o Inf
        for paso in resultado:
            for val in paso.values():
                assert np.isfinite(val)

    def test_propagacion_red_densa(self, sistema_minimo):
        """Todos conectados con todos — no debe fallar."""
        sistema_minimo.relacionar('A', 'C', fuerza=0.7)
        sistema_minimo.relacionar('C', 'A', fuerza=0.3)
        resultado = sistema_minimo.activar('B', pasos=4)
        assert len(resultado) == 5


class TestPropagacionMatricial:
    """Tests específicos de la implementación numpy."""

    def test_adj_matrix_sincronizada(self, sistema_minimo):
        """La matriz de adyacencia refleja las relaciones."""
        i_a = sistema_minimo._idx['A']
        i_b = sistema_minimo._idx['B']
        assert sistema_minimo._adj[i_a, i_b] == pytest.approx(0.8)
        assert sistema_minimo._adj[i_b, i_a] == pytest.approx(0.8)  # bidireccional

    def test_vec_actual_tiene_dimension_correcta(self, sistema_minimo):
        for nombre in sistema_minimo.conceptos:
            idx = sistema_minimo._idx[nombre]
            vec = sistema_minimo._vec_actual[idx]
            assert vec.shape == (15,)

    def test_act_to_dict_convierte_correctamente(self, sistema_minimo):
        arr = np.array([0.5, 0.3, 0.2])
        d = sistema_minimo._act_to_dict(arr)
        assert len(d) == 3
        assert all(isinstance(v, float) for v in d.values())
