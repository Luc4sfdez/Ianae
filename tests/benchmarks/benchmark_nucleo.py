"""Benchmarks de rendimiento para nucleo.py."""
import pytest
import time
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'core'))


def _crear_sistema(n_conceptos):
    """Crea sistema con n conceptos conectados aleatoriamente."""
    from nucleo import ConceptosLucas
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.1)
    for i in range(n_conceptos):
        s.añadir_concepto(f'c_{i}', atributos=np.random.rand(15))
    # Crear relaciones aleatorias (~3 por concepto)
    nombres = list(s.conceptos.keys())
    for nombre in nombres:
        vecinos = np.random.choice(nombres, size=min(3, len(nombres)), replace=False)
        for vecino in vecinos:
            if vecino != nombre:
                s.relacionar(nombre, vecino, fuerza=np.random.uniform(0.3, 0.9))
    return s


@pytest.mark.benchmark
@pytest.mark.slow
class TestBenchmarkPropagacion:
    """Benchmarks de propagación con distintos tamaños."""

    def test_propagacion_100_conceptos(self):
        s = _crear_sistema(100)
        start = time.perf_counter()
        s.activar('c_0', pasos=5, temperatura=0.1)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"Propagación 100 conceptos tardó {elapsed:.3f}s (max 5s)"

    def test_propagacion_500_conceptos(self):
        s = _crear_sistema(500)
        start = time.perf_counter()
        s.activar('c_0', pasos=5, temperatura=0.1)
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"Propagación 500 conceptos tardó {elapsed:.3f}s (max 10s)"

    def test_propagacion_1000_conceptos(self):
        s = _crear_sistema(1000)
        start = time.perf_counter()
        s.activar('c_0', pasos=3, temperatura=0.1)
        elapsed = time.perf_counter() - start
        assert elapsed < 30.0, f"Propagación 1000 conceptos tardó {elapsed:.3f}s (max 30s)"


@pytest.mark.benchmark
@pytest.mark.slow
class TestBenchmarkModificacion:
    """Benchmarks de auto-modificación."""

    def test_auto_modificar_100_conceptos(self):
        s = _crear_sistema(100)
        s.activar('c_0', pasos=3, temperatura=0.3)
        start = time.perf_counter()
        s.auto_modificar(fuerza=0.5)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"Auto-mod 100 conceptos tardó {elapsed:.3f}s"

    def test_auto_modificar_500_conceptos(self):
        s = _crear_sistema(500)
        s.activar('c_0', pasos=3, temperatura=0.3)
        start = time.perf_counter()
        s.auto_modificar(fuerza=0.5)
        elapsed = time.perf_counter() - start
        assert elapsed < 15.0, f"Auto-mod 500 conceptos tardó {elapsed:.3f}s"


@pytest.mark.benchmark
@pytest.mark.slow
class TestBenchmarkSerializacion:
    """Benchmarks de guardar/cargar."""

    def test_guardar_500_conceptos(self, tmp_path):
        s = _crear_sistema(500)
        ruta = str(tmp_path / "bench.json")
        start = time.perf_counter()
        s.guardar(ruta)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"Guardar 500 conceptos tardó {elapsed:.3f}s"

    def test_cargar_500_conceptos(self, tmp_path):
        from nucleo import ConceptosLucas
        s = _crear_sistema(500)
        ruta = str(tmp_path / "bench.json")
        s.guardar(ruta)
        start = time.perf_counter()
        ConceptosLucas.cargar(ruta)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"Cargar 500 conceptos tardó {elapsed:.3f}s"


@pytest.mark.benchmark
class TestBenchmarkBuscarSimilares:
    """Benchmark de búsqueda por similitud."""

    def test_buscar_similares_poblado(self):
        s = _crear_sistema(200)
        start = time.perf_counter()
        for _ in range(100):
            s.buscar_similares('c_0', top_k=5)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"100 búsquedas en 200 conceptos tardaron {elapsed:.3f}s"
