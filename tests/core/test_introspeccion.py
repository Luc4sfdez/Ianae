"""Tests para Introspeccion — Fase 14: IANAE se Mira a Si Misma."""
import os
import textwrap

import pytest

from src.core.introspeccion import ExtractorCodigo, MapaInterno
from src.core.nucleo import ConceptosLucas


# ==================== Fixtures ====================


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    s.añadir_concepto("Python", categoria="tecnologias")
    s.añadir_concepto("IANAE", categoria="conceptos_ianae")
    s.relacionar("Python", "IANAE", fuerza=0.9)
    return s


@pytest.fixture
def src_dir():
    """Directorio src/ real del proyecto."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def archivo_py(tmp_path):
    """Crea un archivo .py temporal para testear."""
    code = textwrap.dedent('''\
        """Modulo de ejemplo para tests."""
        import os
        import json
        from typing import List

        def funcion_top():
            """Una funcion top-level."""
            pass

        class MiClase:
            """Una clase de ejemplo."""

            def metodo_a(self):
                pass

            def metodo_b(self):
                pass

            def _privado(self):
                pass

        class OtraClase:
            def hacer_algo(self):
                pass
    ''')
    archivo = tmp_path / "ejemplo.py"
    archivo.write_text(code, encoding="utf-8")
    return str(archivo)


@pytest.fixture
def directorio_py(tmp_path):
    """Crea un directorio con varios .py."""
    core_dir = tmp_path / "core"
    core_dir.mkdir()

    (core_dir / "modulo_a.py").write_text(
        '"""Modulo A."""\nimport os\nclass ClaseA:\n    def metodo1(self): pass\n',
        encoding="utf-8",
    )
    (core_dir / "modulo_b.py").write_text(
        '"""Modulo B."""\nfrom src.core.modulo_a import ClaseA\nclass ClaseB:\n    def metodo2(self): pass\n',
        encoding="utf-8",
    )
    (core_dir / "__init__.py").write_text("", encoding="utf-8")
    return str(tmp_path)


# ==================== TestExtractorCodigo ====================


class TestExtractorCodigo:
    def test_extraer_modulo_basico(self, archivo_py):
        resultado = ExtractorCodigo.extraer_modulo(archivo_py)
        assert resultado is not None
        assert resultado["nombre"] == "ejemplo"
        assert len(resultado["clases"]) == 2
        assert resultado["lineas"] > 0

    def test_extraer_clases_con_metodos(self, archivo_py):
        resultado = ExtractorCodigo.extraer_modulo(archivo_py)
        mi_clase = [c for c in resultado["clases"] if c["nombre"] == "MiClase"][0]
        assert "metodo_a" in mi_clase["metodos"]
        assert "metodo_b" in mi_clase["metodos"]
        assert "_privado" in mi_clase["metodos"]

    def test_extraer_docstring_clase(self, archivo_py):
        resultado = ExtractorCodigo.extraer_modulo(archivo_py)
        mi_clase = [c for c in resultado["clases"] if c["nombre"] == "MiClase"][0]
        assert "ejemplo" in mi_clase["docstring"].lower()

    def test_extraer_imports(self, archivo_py):
        resultado = ExtractorCodigo.extraer_modulo(archivo_py)
        assert "os" in resultado["imports"]
        assert "json" in resultado["imports"]

    def test_extraer_funciones_top_level(self, archivo_py):
        resultado = ExtractorCodigo.extraer_modulo(archivo_py)
        assert "funcion_top" in resultado["funciones"]

    def test_extraer_docstring_modulo(self, archivo_py):
        resultado = ExtractorCodigo.extraer_modulo(archivo_py)
        assert "ejemplo" in resultado["docstring"].lower()

    def test_archivo_inexistente_retorna_none(self):
        resultado = ExtractorCodigo.extraer_modulo("/ruta/inexistente.py")
        assert resultado is None

    def test_syntax_error_retorna_none(self, tmp_path):
        malo = tmp_path / "malo.py"
        malo.write_text("def broken(\n", encoding="utf-8")
        resultado = ExtractorCodigo.extraer_modulo(str(malo))
        assert resultado is None

    def test_extraer_directorio(self, directorio_py):
        modulos = ExtractorCodigo.extraer_directorio(directorio_py)
        nombres = {m["nombre"] for m in modulos}
        assert "modulo_a" in nombres
        assert "modulo_b" in nombres

    def test_extraer_directorio_inexistente(self):
        modulos = ExtractorCodigo.extraer_directorio("/ruta/inexistente")
        assert modulos == []

    def test_extraer_archivo_real(self, src_dir):
        """Testea con un archivo real del proyecto."""
        ruta = os.path.join(src_dir, "src", "core", "introspeccion.py")
        if os.path.exists(ruta):
            resultado = ExtractorCodigo.extraer_modulo(ruta)
            assert resultado is not None
            clases = [c["nombre"] for c in resultado["clases"]]
            assert "ExtractorCodigo" in clases
            assert "MapaInterno" in clases


# ==================== TestMapaInterno ====================


class TestMapaInterno:
    def test_construir_retorna_lista(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        modulos = mapa.construir()
        assert isinstance(modulos, list)
        assert len(modulos) > 0

    def test_cache_no_reconstruye(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        m1 = mapa.construir()
        m2 = mapa.construir()
        assert m1 is m2  # misma referencia = cache hit

    def test_invalidar_cache(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        m1 = mapa.construir()
        mapa.invalidar_cache()
        m2 = mapa.construir()
        assert m1 is not m2  # referencia distinta = reconstruido

    def test_quien_soy_narrativa(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        texto = mapa.quien_soy()
        assert "IANAE" in texto
        assert "modulos" in texto.lower() or "modulo" in texto.lower()
        assert "clases" in texto.lower() or "clase" in texto.lower()

    def test_que_puedo_hacer_lista(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        caps = mapa.que_puedo_hacer()
        assert isinstance(caps, list)
        assert len(caps) > 0
        # Cada capacidad es un string
        for c in caps:
            assert isinstance(c, str)

    def test_modulos_retorna_estructura(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        mods = mapa.modulos()
        assert isinstance(mods, list)
        for m in mods:
            assert "nombre" in m
            assert "clases" in m

    def test_buscar_en_codigo(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        resultados = mapa.buscar_en_codigo("Consciencia")
        assert len(resultados) > 0
        tipos = {r["tipo"] for r in resultados}
        assert "clase" in tipos or "modulo" in tipos

    def test_buscar_sin_resultados(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        resultados = mapa.buscar_en_codigo("xyzzy_no_existe_99")
        assert resultados == []

    def test_complejidad_metricas(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        comp = mapa.complejidad()
        assert comp["modulos"] > 0
        assert comp["clases"] > 0
        assert comp["metodos"] > 0
        assert comp["lineas"] > 0
        assert isinstance(comp["dependencias"], dict)

    def test_quien_soy_sin_directorio(self, sistema):
        mapa = MapaInterno(sistema, "/ruta/inexistente")
        texto = mapa.quien_soy()
        assert "IANAE" in texto
        assert "no puedo" in texto.lower()


# ==================== TestInyeccion ====================


class TestInyeccion:
    def test_inyectar_crea_conceptos(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        mapa.construir()
        # construir() llama inyectar_autoconocimiento internamente
        conceptos_auto = [
            c for c in sistema.conceptos
            if c.startswith("mod_")
        ]
        assert len(conceptos_auto) > 0

    def test_conceptos_categoria_autoconocimiento(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        mapa.construir()
        for nombre, datos in sistema.conceptos.items():
            if nombre.startswith("mod_"):
                assert datos.get("categoria") == "autoconocimiento"

    def test_inyeccion_idempotente(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        mapa.construir()
        count1 = len([c for c in sistema.conceptos if c.startswith("mod_")])
        # Forzar re-inyeccion
        mapa._inyectado = False
        mapa.invalidar_cache()
        mapa.construir()
        count2 = len([c for c in sistema.conceptos if c.startswith("mod_")])
        assert count2 == count1  # no duplicados

    def test_relaciones_entre_modulos(self, sistema, src_dir):
        mapa = MapaInterno(sistema, os.path.join(src_dir, "src"))
        mapa.construir()
        # Debe haber al menos alguna relacion entre modulos
        relaciones_auto = 0
        for c1, c2, _ in sistema.grafo.edges(data=True):
            if c1.startswith("mod_") and c2.startswith("mod_"):
                relaciones_auto += 1
        assert relaciones_auto > 0

    def test_inyeccion_sin_sistema(self):
        mapa = MapaInterno(sistema=None, directorio_src="/tmp")
        creados = mapa.inyectar_autoconocimiento()
        assert creados == 0
