"""Tests para AprendizajeRefuerzo y su integracion con ConceptosLucas."""
import pytest
import numpy as np
from src.core.aprendizaje_refuerzo import AprendizajeRefuerzo
from src.core.nucleo import ConceptosLucas


# --- Tests unitarios AprendizajeRefuerzo ---

@pytest.fixture
def rl():
    return AprendizajeRefuerzo(alpha=0.1, gamma=0.9, epsilon=0.3)


def test_q_table_inicialmente_vacia(rl):
    assert len(rl.q_table) == 0
    assert rl.get_q("A", "B") == 0.0


def test_actualizar_q_value(rl):
    rl.actualizar("A", "B", recompensa=1.0, siguientes_vecinos=["C"])
    assert rl.get_q("A", "B") > 0.0


def test_seleccionar_accion_sin_vecinos(rl):
    assert rl.seleccionar_accion("A", []) == "A"


def test_seleccionar_accion_explotacion(rl):
    """Con epsilon=0 siempre explota el mejor Q-value."""
    rl.epsilon = 0.0
    rl.q_table[("A", "B")] = 0.5
    rl.q_table[("A", "C")] = 0.1
    # Con epsilon 0, siempre elige B
    selecciones = [rl.seleccionar_accion("A", ["B", "C"]) for _ in range(20)]
    assert all(s == "B" for s in selecciones)


def test_epsilon_decay(rl):
    epsilon_inicial = rl.epsilon
    rl.fin_episodio()
    assert rl.epsilon < epsilon_inicial
    assert rl.episodios == 1


def test_calcular_recompensa(rl):
    activaciones = {"A": 0.5, "B": 0.3, "C": 0.2, "D": 0.15, "E": 0.1}
    r = rl.calcular_recompensa(activaciones, conceptos_utiles=4, diversidad=0.5)
    assert -1.0 <= r <= 1.0
    assert len(rl.historial_recompensas) == 1


def test_calcular_recompensa_vacia(rl):
    r = rl.calcular_recompensa({}, conceptos_utiles=0, diversidad=0.0)
    assert r < 0  # Penaliza sin activaciones


def test_aprender_de_propagacion(rl):
    resultados = [
        {"A": 1.0},
        {"A": 0.5, "B": 0.3},
        {"A": 0.3, "B": 0.4, "C": 0.2},
    ]
    relaciones = {
        "A": [("B", 0.5)],
        "B": [("A", 0.5), ("C", 0.3)],
    }
    rl.aprender_de_propagacion("A", resultados, relaciones)
    assert rl.episodios == 1
    assert len(rl.q_table) > 0


def test_sugerir_ajustes(rl):
    rl.q_table[("A", "B")] = 0.5
    rl.q_table[("C", "D")] = -0.4
    rl.q_table[("E", "F")] = 0.1  # Bajo umbral
    ajustes = rl.sugerir_ajustes_pesos({}, umbral_q=0.3)
    assert len(ajustes) == 2
    # A->B positivo, C->D negativo
    for orig, dest, delta in ajustes:
        if orig == "A":
            assert delta > 0
        elif orig == "C":
            assert delta < 0


def test_estadisticas(rl):
    stats = rl.estadisticas()
    assert stats["episodios"] == 0
    assert stats["q_entries"] == 0
    assert stats["recompensa_media"] == 0.0


# --- Tests integracion con nucleo ---

@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=5, incertidumbre_base=0.0)
    s.añadir_concepto("A", atributos=np.array([1.0, 0.0, 0.0, 0.0, 0.0]))
    s.añadir_concepto("B", atributos=np.array([0.5, 0.5, 0.0, 0.0, 0.0]))
    s.añadir_concepto("C", atributos=np.array([0.0, 1.0, 0.0, 0.0, 0.0]))
    s.relacionar("A", "B", fuerza=0.7)
    s.relacionar("B", "C", fuerza=0.5)
    return s


def test_nucleo_tiene_aprendizaje(sistema):
    assert hasattr(sistema, "aprendizaje")
    assert isinstance(sistema.aprendizaje, AprendizajeRefuerzo)


def test_activar_entrena_q_learning(sistema):
    assert sistema.aprendizaje.episodios == 0
    sistema.activar("A", pasos=3)
    assert sistema.aprendizaje.episodios >= 1
    assert len(sistema.aprendizaje.q_table) > 0


def test_multiples_activaciones_mejoran_q(sistema):
    for _ in range(10):
        sistema.activar("A", pasos=3)
    stats = sistema.aprendizaje.estadisticas()
    assert stats["episodios"] == 10
    assert stats["q_entries"] > 0


def test_aprender_de_experiencia(sistema):
    # Forzar Q-values altos para que sugiera ajustes
    sistema.aprendizaje.q_table[("A", "B")] = 0.8
    peso_original = float(sistema._adj[sistema._idx["A"], sistema._idx["B"]])
    ajustados = sistema.aprender_de_experiencia()
    if ajustados > 0:
        peso_nuevo = float(sistema._adj[sistema._idx["A"], sistema._idx["B"]])
        assert peso_nuevo != peso_original
