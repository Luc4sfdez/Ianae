"""Tests de serialización para nucleo.py — guardar/cargar estado."""
import pytest
import numpy as np
import json
import os


class TestGuardar:
    """Tests del método guardar()."""

    def test_guardar_crea_archivo(self, sistema_minimo, archivo_temporal):
        assert sistema_minimo.guardar(archivo_temporal)
        assert os.path.exists(archivo_temporal)

    def test_guardar_formato_json_valido(self, sistema_minimo, archivo_temporal):
        sistema_minimo.guardar(archivo_temporal)
        with open(archivo_temporal, 'r', encoding='utf-8') as f:
            estado = json.load(f)
        assert isinstance(estado, dict)

    def test_guardar_contiene_claves_requeridas(self, sistema_minimo, archivo_temporal):
        sistema_minimo.guardar(archivo_temporal)
        with open(archivo_temporal, 'r', encoding='utf-8') as f:
            estado = json.load(f)
        claves = {'metricas', 'dim_vector', 'incertidumbre_base',
                   'conceptos', 'relaciones', 'categorias', 'timestamp'}
        assert claves.issubset(estado.keys())

    def test_guardar_conceptos_como_listas(self, sistema_minimo, archivo_temporal):
        """Los vectores numpy se guardan como listas JSON."""
        sistema_minimo.guardar(archivo_temporal)
        with open(archivo_temporal, 'r', encoding='utf-8') as f:
            estado = json.load(f)
        for nombre, datos in estado['conceptos'].items():
            assert isinstance(datos['base'], list)
            assert isinstance(datos['actual'], list)
            assert len(datos['base']) == 15

    def test_guardar_relaciones_formato(self, sistema_minimo, archivo_temporal):
        sistema_minimo.guardar(archivo_temporal)
        with open(archivo_temporal, 'r', encoding='utf-8') as f:
            estado = json.load(f)
        for rel in estado['relaciones']:
            assert 'origen' in rel
            assert 'destino' in rel
            assert 'peso' in rel
            assert isinstance(rel['peso'], float)

    def test_guardar_sistema_vacio(self, sistema_vacio, archivo_temporal):
        assert sistema_vacio.guardar(archivo_temporal)
        with open(archivo_temporal, 'r', encoding='utf-8') as f:
            estado = json.load(f)
        assert len(estado['conceptos']) == 0
        assert len(estado['relaciones']) == 0

    def test_guardar_ruta_invalida(self, sistema_minimo):
        result = sistema_minimo.guardar('/ruta/que/no/existe/archivo.json')
        assert result is False


class TestCargar:
    """Tests del classmethod cargar()."""

    def test_cargar_restaura_conceptos(self, sistema_minimo, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_minimo.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        assert cargado is not None
        assert set(cargado.conceptos.keys()) == set(sistema_minimo.conceptos.keys())

    def test_cargar_restaura_relaciones(self, sistema_minimo, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_minimo.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        # El grafo debe tener las mismas aristas
        assert cargado.grafo.number_of_edges() == sistema_minimo.grafo.number_of_edges()

    def test_cargar_restaura_metricas(self, sistema_minimo, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_minimo.metricas['edad'] = 42
        sistema_minimo.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        assert cargado.metricas['edad'] == 42

    def test_cargar_vectores_son_numpy(self, sistema_minimo, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_minimo.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        for nombre, datos in cargado.conceptos.items():
            assert isinstance(datos['base'], np.ndarray)
            assert isinstance(datos['actual'], np.ndarray)

    def test_cargar_archivo_inexistente(self):
        from nucleo import ConceptosLucas
        result = ConceptosLucas.cargar('no_existe.json')
        assert result is None

    def test_cargar_reconstruye_numpy(self, sistema_minimo, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_minimo.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        assert cargado._n == len(cargado.conceptos)
        assert len(cargado._idx) == cargado._n
        assert len(cargado._names) == cargado._n


class TestPersistenciaCompleta:
    """Tests de round-trip guardar -> cargar -> usar."""

    def test_guardar_cargar_activar(self, sistema_poblado, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_poblado.activar('Python', pasos=2)
        sistema_poblado.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        # El sistema cargado debe poder activar sin errores
        resultado = cargado.activar('Python', pasos=2)
        assert len(resultado) == 3

    def test_guardar_cargar_auto_modificar(self, sistema_poblado, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_poblado.activar('Python', pasos=2)
        sistema_poblado.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        cargado.activar('Python', pasos=2)
        mods = cargado.auto_modificar(fuerza=0.5)
        assert isinstance(mods, int)

    def test_guardar_cargar_preserva_categorias(self, sistema_poblado, archivo_temporal):
        from nucleo import ConceptosLucas
        sistema_poblado.guardar(archivo_temporal)
        cargado = ConceptosLucas.cargar(archivo_temporal)
        assert len(cargado.categorias) > 0

    def test_doble_round_trip(self, sistema_minimo, archivo_temporal):
        """Guardar -> cargar -> guardar -> cargar debe ser consistente."""
        from nucleo import ConceptosLucas
        sistema_minimo.guardar(archivo_temporal)
        cargado1 = ConceptosLucas.cargar(archivo_temporal)
        cargado1.guardar(archivo_temporal)
        cargado2 = ConceptosLucas.cargar(archivo_temporal)
        assert set(cargado1.conceptos.keys()) == set(cargado2.conceptos.keys())
        assert cargado1.grafo.number_of_edges() == cargado2.grafo.number_of_edges()


class TestBuscarSimilares:
    """Tests para el método buscar_similares (índice espacial)."""

    def test_buscar_similares_concepto_existente(self, sistema_poblado):
        similares = sistema_poblado.buscar_similares('Python', top_k=3)
        assert isinstance(similares, list)
        assert len(similares) <= 3
        # Cada entrada es (nombre, similitud)
        for nombre, sim in similares:
            assert isinstance(nombre, str)
            assert isinstance(sim, float)

    def test_buscar_similares_concepto_inexistente(self, sistema_poblado):
        similares = sistema_poblado.buscar_similares('NoExiste')
        assert similares == []

    def test_buscar_similares_no_incluye_a_si_mismo(self, sistema_poblado):
        similares = sistema_poblado.buscar_similares('Python', top_k=10)
        nombres = [n for n, _ in similares]
        assert 'Python' not in nombres

    def test_buscar_similares_top_k(self, sistema_poblado):
        s3 = sistema_poblado.buscar_similares('Python', top_k=3)
        s5 = sistema_poblado.buscar_similares('Python', top_k=5)
        assert len(s3) <= 3
        assert len(s5) <= 5


class TestEnsureCapacity:
    """Tests para la expansión dinámica de arrays numpy."""

    def test_capacidad_inicial(self, sistema_vacio):
        assert sistema_vacio._cap == 64

    def test_expansion_al_superar_capacidad(self, sistema_vacio):
        """Añadir más de 64 conceptos debe expandir arrays."""
        for i in range(70):
            sistema_vacio.añadir_concepto(f'concepto_{i}')
        assert sistema_vacio._cap >= 70
        assert sistema_vacio._n == 70
        assert sistema_vacio._adj.shape[0] >= 70

    def test_expansion_preserva_datos(self, sistema_vacio):
        """Los datos existentes se preservan tras expansión."""
        vec = np.ones(15) * 0.5
        sistema_vacio.añadir_concepto('Primero', atributos=vec)
        for i in range(70):
            sistema_vacio.añadir_concepto(f'c_{i}')
        # El primer concepto debe mantener sus datos
        idx_primero = sistema_vacio._idx['Primero']
        base = sistema_vacio._vec_base[idx_primero]
        assert np.linalg.norm(base) > 0
