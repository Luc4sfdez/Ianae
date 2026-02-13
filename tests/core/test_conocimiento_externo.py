"""
Tests para Fase 13: Conocimiento Externo.

Todas las llamadas de red mockeadas via unittest.mock.patch.
"""
import json
import os
import time
from unittest.mock import MagicMock, patch, PropertyMock
from xml.etree import ElementTree

import pytest

from src.core.conocimiento_externo import (
    ConocimientoExterno,
    FiltroDigestion,
    FuenteArchivos,
    FuenteExterna,
    FuenteRSS,
    FuenteWeb,
    FuenteWikipedia,
)


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def sistema():
    from src.core.nucleo import ConceptosLucas
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    s.añadir_concepto("Python", categoria="tecnologias")
    s.añadir_concepto("Machine_Learning", categoria="tecnologias")
    s.añadir_concepto("Redes_Neuronales", categoria="tecnologias")
    s.añadir_concepto("Algoritmos", categoria="fundamentos")
    s.relacionar("Python", "Machine_Learning", fuerza=0.8)
    s.relacionar("Machine_Learning", "Redes_Neuronales", fuerza=0.9)
    s.relacionar("Python", "Algoritmos", fuerza=0.7)
    for _ in range(3):
        s.activar("Python", pasos=2, temperatura=0.1)
    return s


@pytest.fixture
def wiki_response_opensearch():
    """Mock de respuesta opensearch de Wikipedia."""
    return json.dumps(["Python", ["Python (lenguaje)", "Python (serpiente)"], [], []]).encode("utf-8")


@pytest.fixture
def wiki_response_extract():
    """Mock de respuesta extract de Wikipedia."""
    return json.dumps({
        "query": {
            "pages": {
                "123": {
                    "title": "Python (lenguaje)",
                    "extract": "Python es un lenguaje de programacion interpretado de alto nivel.",
                }
            }
        }
    }).encode("utf-8")


@pytest.fixture
def rss_xml():
    """XML RSS valido."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test Feed</title>
            <item>
                <title>Python 4.0 Released</title>
                <description>Major update with new features for machine learning and data science</description>
                <link>https://example.com/python4</link>
            </item>
            <item>
                <title>Rust vs Go Performance</title>
                <description>A benchmark comparison of Rust and Go in production</description>
                <link>https://example.com/rust-go</link>
            </item>
            <item>
                <title>New Database Technology</title>
                <description>Revolutionary approach to data storage</description>
                <link>https://example.com/db</link>
            </item>
        </channel>
    </rss>"""


@pytest.fixture
def atom_xml():
    """XML Atom valido."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Atom Test</title>
        <entry>
            <title>Python Tips</title>
            <summary>Advanced python programming tips</summary>
        </entry>
    </feed>"""


@pytest.fixture
def ddg_response():
    """Mock de respuesta DDG Instant Answer."""
    return json.dumps({
        "Heading": "Python (programming language)",
        "AbstractText": "Python is a high-level general-purpose programming language.",
        "RelatedTopics": [
            {"Text": "Python Software Foundation", "FirstURL": "https://python.org"},
            {"Text": "PyPI - Python Package Index", "FirstURL": "https://pypi.org"},
        ],
    }).encode("utf-8")


def _mock_urlopen(response_bytes, status=200):
    """Helper para mockear urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_bytes
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ======================================================================
# TestFuenteWikipedia
# ======================================================================


class TestFuenteWikipedia:

    def test_disponible_inicialmente(self):
        wiki = FuenteWikipedia(cooldown=0.0)
        assert wiki.disponible() is True

    def test_no_disponible_en_cooldown(self):
        wiki = FuenteWikipedia(cooldown=10.0)
        wiki._ultimo_request = time.time()
        assert wiki.disponible() is False

    @patch("src.core.conocimiento_externo.urlopen")
    def test_buscar_retorna_resultados(self, mock_url, wiki_response_opensearch, wiki_response_extract):
        mock_url.side_effect = [
            _mock_urlopen(wiki_response_opensearch),
            _mock_urlopen(wiki_response_extract),
            _mock_urlopen(wiki_response_extract),
        ]
        wiki = FuenteWikipedia(cooldown=0.0)
        resultados = wiki.buscar("Python")
        assert len(resultados) > 0
        assert resultados[0]["fuente"] == "wikipedia_es"
        assert len(resultados[0]["texto"]) > 0

    @patch("src.core.conocimiento_externo.urlopen")
    def test_buscar_trunca_texto(self, mock_url, wiki_response_opensearch):
        extract_largo = json.dumps({
            "query": {"pages": {"1": {"extract": "x" * 10000}}}
        }).encode("utf-8")
        mock_url.side_effect = [
            _mock_urlopen(wiki_response_opensearch),
            _mock_urlopen(extract_largo),
            _mock_urlopen(extract_largo),
        ]
        wiki = FuenteWikipedia(cooldown=0.0)
        resultados = wiki.buscar("Python")
        for r in resultados:
            assert len(r["texto"]) <= 5000

    @patch("src.core.conocimiento_externo.urlopen")
    def test_buscar_maneja_error_red(self, mock_url):
        from urllib.error import URLError
        mock_url.side_effect = URLError("timeout")
        wiki = FuenteWikipedia(cooldown=0.0)
        resultados = wiki.buscar("Python")
        assert resultados == []
        assert wiki._errores > 0

    def test_estado_incluye_campos(self):
        wiki = FuenteWikipedia()
        estado = wiki.estado()
        assert "tipo" in estado
        assert estado["tipo"] == "FuenteWikipedia"
        assert "lang" in estado
        assert "busquedas" in estado

    @patch("src.core.conocimiento_externo.urlopen")
    def test_buscar_sin_resultados_opensearch(self, mock_url):
        mock_url.return_value = _mock_urlopen(json.dumps(["q", []]).encode("utf-8"))
        wiki = FuenteWikipedia(cooldown=0.0)
        resultados = wiki.buscar("xyznoexiste")
        assert resultados == []

    def test_lang_configurable(self):
        wiki = FuenteWikipedia(lang="en")
        assert wiki._lang == "en"


# ======================================================================
# TestFuenteRSS
# ======================================================================


class TestFuenteRSS:

    def test_disponible_con_feeds(self):
        rss = FuenteRSS(feeds=["https://example.com/feed"])
        assert rss.disponible() is True

    def test_no_disponible_sin_feeds(self):
        rss = FuenteRSS(feeds=[])
        assert rss.disponible() is False

    @patch("src.core.conocimiento_externo.urlopen")
    def test_buscar_con_keywords(self, mock_url, rss_xml):
        mock_url.return_value = _mock_urlopen(rss_xml)
        rss = FuenteRSS(feeds=["https://example.com/feed"])
        resultados = rss.buscar("python machine learning")
        assert len(resultados) > 0
        # primer resultado debe ser el de Python con mayor relevancia
        assert "python" in resultados[0]["titulo"].lower()

    @patch("src.core.conocimiento_externo.urlopen")
    def test_buscar_sin_match(self, mock_url, rss_xml):
        mock_url.return_value = _mock_urlopen(rss_xml)
        rss = FuenteRSS(feeds=["https://example.com/feed"])
        resultados = rss.buscar("xyznoexiste123")
        assert resultados == []

    @patch("src.core.conocimiento_externo.urlopen")
    def test_cache_funciona(self, mock_url, rss_xml):
        mock_url.return_value = _mock_urlopen(rss_xml)
        rss = FuenteRSS(feeds=["https://example.com/feed"], cache_ttl=3600)
        rss.buscar("python")
        # Segunda busqueda no deberia hacer request (cache hit)
        mock_url.reset_mock()
        rss.buscar("rust")
        mock_url.assert_not_called()

    @patch("src.core.conocimiento_externo.urlopen")
    def test_parsear_atom(self, mock_url, atom_xml):
        mock_url.return_value = _mock_urlopen(atom_xml)
        rss = FuenteRSS(feeds=["https://example.com/atom"])
        resultados = rss.buscar("python")
        assert len(resultados) > 0
        assert "Python" in resultados[0]["titulo"]

    def test_agregar_feed(self):
        rss = FuenteRSS(feeds=[])
        rss.agregar_feed("https://new.com/feed")
        assert "https://new.com/feed" in rss.listar_feeds()

    def test_quitar_feed(self):
        rss = FuenteRSS(feeds=["https://a.com/feed", "https://b.com/feed"])
        assert rss.quitar_feed("https://a.com/feed") is True
        assert "https://a.com/feed" not in rss.listar_feeds()

    def test_quitar_feed_inexistente(self):
        rss = FuenteRSS(feeds=["https://a.com/feed"])
        assert rss.quitar_feed("https://noexiste.com") is False

    def test_no_agrega_feed_duplicado(self):
        rss = FuenteRSS(feeds=["https://a.com/feed"])
        rss.agregar_feed("https://a.com/feed")
        assert len(rss.listar_feeds()) == 1

    def test_estado_incluye_campos(self):
        rss = FuenteRSS()
        estado = rss.estado()
        assert "feeds" in estado
        assert "busquedas" in estado
        assert estado["tipo"] == "FuenteRSS"

    @patch("src.core.conocimiento_externo.urlopen")
    def test_maneja_xml_invalido(self, mock_url):
        mock_url.return_value = _mock_urlopen(b"not xml at all")
        rss = FuenteRSS(feeds=["https://bad.com/feed"])
        resultados = rss.buscar("anything")
        assert resultados == []


# ======================================================================
# TestFuenteWeb
# ======================================================================


class TestFuenteWeb:

    def test_disponible_inicialmente(self):
        web = FuenteWeb(cooldown=0.0)
        assert web.disponible() is True

    def test_no_disponible_en_cooldown(self):
        web = FuenteWeb(cooldown=10.0)
        web._ultimo_request = time.time()
        assert web.disponible() is False

    @patch("src.core.conocimiento_externo.urlopen")
    def test_buscar_ddg(self, mock_url, ddg_response):
        mock_url.return_value = _mock_urlopen(ddg_response)
        web = FuenteWeb(cooldown=0.0)
        resultados = web.buscar("Python")
        assert len(resultados) > 0
        assert resultados[0]["fuente"] == "duckduckgo"
        assert "Python" in resultados[0]["titulo"]

    @patch("src.core.conocimiento_externo.urlopen")
    def test_buscar_searxng(self, mock_url):
        searx_data = json.dumps({
            "results": [
                {"title": "Test", "content": "Some content about Python"},
            ]
        }).encode("utf-8")
        mock_url.return_value = _mock_urlopen(searx_data)
        web = FuenteWeb(cooldown=0.0, searxng_url="https://searx.local/search")
        resultados = web.buscar("Python")
        assert len(resultados) > 0
        assert resultados[0]["fuente"] == "searxng"

    @patch("src.core.conocimiento_externo.urlopen")
    def test_maneja_error_red(self, mock_url):
        from urllib.error import URLError
        mock_url.side_effect = URLError("timeout")
        web = FuenteWeb(cooldown=0.0)
        resultados = web.buscar("Python")
        assert resultados == []
        assert web._errores > 0

    def test_estado_ddg_por_defecto(self):
        web = FuenteWeb()
        assert web.estado()["backend"] == "duckduckgo"

    def test_estado_searxng(self):
        web = FuenteWeb(searxng_url="https://searx.local/search")
        assert web.estado()["backend"] == "searxng"


# ======================================================================
# TestFuenteArchivos
# ======================================================================


class TestFuenteArchivos:

    def test_disponible_con_directorio(self, tmp_path):
        arch = FuenteArchivos(directorios=[str(tmp_path)])
        assert arch.disponible() is True

    def test_no_disponible_sin_directorios(self):
        arch = FuenteArchivos(directorios=[])
        assert arch.disponible() is False

    def test_no_disponible_directorio_inexistente(self):
        arch = FuenteArchivos(directorios=["/no/existe/xyz123"])
        assert arch.disponible() is False

    def test_buscar_por_contenido(self, tmp_path):
        (tmp_path / "test.txt").write_text("Python es un lenguaje de programacion", encoding="utf-8")
        arch = FuenteArchivos(directorios=[str(tmp_path)])
        resultados = arch.buscar("python programacion")
        assert len(resultados) > 0
        assert resultados[0]["relevancia"] > 0

    def test_buscar_recursivo(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.md").write_text("machine learning algorithms", encoding="utf-8")
        arch = FuenteArchivos(directorios=[str(tmp_path)])
        resultados = arch.buscar("machine learning")
        assert len(resultados) > 0

    def test_ignora_extensiones_no_soportadas(self, tmp_path):
        (tmp_path / "binary.exe").write_bytes(b"\x00\x01\x02")
        (tmp_path / "text.txt").write_text("python code", encoding="utf-8")
        arch = FuenteArchivos(directorios=[str(tmp_path)])
        resultados = arch.buscar("python")
        assert len(resultados) == 1
        assert "text.txt" in resultados[0]["titulo"]

    def test_buscar_sin_match(self, tmp_path):
        (tmp_path / "test.txt").write_text("hello world", encoding="utf-8")
        arch = FuenteArchivos(directorios=[str(tmp_path)])
        resultados = arch.buscar("xyznoexiste123")
        assert resultados == []

    def test_estado_campos(self, tmp_path):
        arch = FuenteArchivos(directorios=[str(tmp_path)])
        estado = arch.estado()
        assert estado["tipo"] == "FuenteArchivos"
        assert "directorios" in estado


# ======================================================================
# TestFiltroDigestion
# ======================================================================


class TestFiltroDigestion:

    def test_digerir_extrae_conceptos(self, sistema):
        filtro = FiltroDigestion(sistema=sistema)
        resultados = [
            {"titulo": "Test", "texto": "Python es un lenguaje de programacion popular", "fuente": "test", "relevancia": 0.8}
        ]
        digestion = filtro.digerir(resultados)
        assert "conceptos" in digestion
        assert "total_extraidos" in digestion
        assert "absorbidos" in digestion

    def test_digerir_respeta_umbral(self, sistema):
        filtro = FiltroDigestion(sistema=sistema, umbral_relevancia=0.99)
        resultados = [
            {"titulo": "Test", "texto": "concepto raro xyz", "fuente": "test", "relevancia": 0.1}
        ]
        digestion = filtro.digerir(resultados)
        assert digestion["absorbidos"] == 0

    def test_digerir_respeta_rate_limit(self, sistema):
        filtro = FiltroDigestion(sistema=sistema, max_conceptos_por_ciclo=2, umbral_relevancia=0.0)
        resultados = [
            {"titulo": "T", "texto": "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima", "fuente": "t", "relevancia": 0.9}
        ]
        digestion = filtro.digerir(resultados)
        assert digestion["absorbidos"] <= 2

    def test_absorber_agrega_al_sistema(self, sistema):
        filtro = FiltroDigestion(sistema=sistema)
        n_antes = len(sistema.conceptos)
        conceptos = [{"nombre": "NuevoConcepto", "score": 0.8, "relevancia": 0.7}]
        absorbidos = filtro.absorber(conceptos)
        assert "NuevoConcepto" in absorbidos
        assert len(sistema.conceptos) == n_antes + 1
        assert sistema.conceptos["NuevoConcepto"]["categoria"] == "conocimiento_externo"

    def test_absorber_concepto_existente_solo_activa(self, sistema):
        filtro = FiltroDigestion(sistema=sistema)
        n_antes = len(sistema.conceptos)
        conceptos = [{"nombre": "Python", "score": 0.8}]
        absorbidos = filtro.absorber(conceptos)
        assert absorbidos == []  # no es "nuevo"
        assert len(sistema.conceptos) == n_antes

    def test_absorber_crea_relaciones_debiles(self, sistema):
        filtro = FiltroDigestion(sistema=sistema, factor_relacion=0.6)
        conceptos = [{"nombre": "NuevoExterno", "score": 0.8}]
        filtro.absorber(conceptos)
        assert "NuevoExterno" in sistema.conceptos
        # Debe tener al menos una relacion
        vecinos = list(sistema.grafo.neighbors("NuevoExterno"))
        assert len(vecinos) > 0

    def test_absorber_sin_sistema(self):
        filtro = FiltroDigestion(sistema=None)
        result = filtro.absorber([{"nombre": "Test"}])
        assert result == []

    def test_puntuar_boost_overlap(self, sistema):
        filtro = FiltroDigestion(sistema=sistema)
        conceptos = [
            {"nombre": "Python", "relevancia": 0.5, "relevancia_fuente": 0.5},
            {"nombre": "xyzdesconocido", "relevancia": 0.5, "relevancia_fuente": 0.5},
        ]
        scored = filtro._puntuar(conceptos)
        python_score = next(c["score"] for c in scored if c["nombre"] == "Python")
        desconocido_score = next(c["score"] for c in scored if c["nombre"] == "xyzdesconocido")
        assert python_score > desconocido_score

    def test_puntuar_penaliza_palabras_cortas(self, sistema):
        filtro = FiltroDigestion(sistema=sistema)
        conceptos = [
            {"nombre": "ab", "relevancia": 0.8, "relevancia_fuente": 0.8},
            {"nombre": "algoritmo", "relevancia": 0.8, "relevancia_fuente": 0.8},
        ]
        scored = filtro._puntuar(conceptos)
        corto = next(c["score"] for c in scored if c["nombre"] == "ab")
        largo = next(c["score"] for c in scored if c["nombre"] == "algoritmo")
        assert corto < largo

    def test_extraccion_basica_sin_nlp(self, sistema):
        filtro = FiltroDigestion(sistema=sistema)
        filtro._extractor = None  # forzar basico
        conceptos = filtro._extraccion_basica(
            "Python es un lenguaje de programacion interpretado de alto nivel usado para machine learning"
        )
        assert len(conceptos) > 0
        nombres = [c["nombre"] for c in conceptos]
        assert any("python" in n for n in nombres)

    def test_estado_campos(self, sistema):
        filtro = FiltroDigestion(sistema=sistema)
        estado = filtro.estado()
        assert "absorbidos_total" in estado
        assert "rechazados_total" in estado
        assert "umbral_relevancia" in estado

    def test_digerir_texto_vacio(self, sistema):
        filtro = FiltroDigestion(sistema=sistema)
        digestion = filtro.digerir([{"titulo": "Vacio", "texto": "", "fuente": "test", "relevancia": 0.5}])
        assert digestion["total_extraidos"] == 0


# ======================================================================
# TestConocimientoExterno
# ======================================================================


class TestConocimientoExterno:

    def test_deshabilitado_por_defecto(self, sistema):
        ce = ConocimientoExterno(sistema=sistema)
        assert ce._habilitado is False

    def test_habilitado_por_parametro(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=True)
        assert ce._habilitado is True

    def test_habilitado_por_env(self, sistema, monkeypatch):
        monkeypatch.setenv("IANAE_CONOCIMIENTO_EXTERNO", "true")
        ce = ConocimientoExterno(sistema=sistema)
        assert ce._habilitado is True

    def test_explorar_deshabilitado(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=False)
        resultado = ce.explorar_externo("Python")
        assert resultado["status"] == "deshabilitado"

    @patch("src.core.conocimiento_externo.urlopen")
    def test_explorar_wikipedia(self, mock_url, sistema, wiki_response_opensearch, wiki_response_extract):
        mock_url.side_effect = [
            _mock_urlopen(wiki_response_opensearch),
            _mock_urlopen(wiki_response_extract),
            _mock_urlopen(wiki_response_extract),
        ]
        ce = ConocimientoExterno(sistema=sistema, habilitado=True)
        resultado = ce.explorar_externo("Python", fuente="wikipedia")
        assert resultado["status"] == "ok"
        assert resultado["fuente"] == "FuenteWikipedia"
        assert resultado["resultados_encontrados"] > 0

    @patch("src.core.conocimiento_externo.urlopen")
    def test_explorar_error_red(self, mock_url, sistema):
        from urllib.error import URLError
        mock_url.side_effect = URLError("timeout")
        ce = ConocimientoExterno(sistema=sistema, habilitado=True)
        resultado = ce.explorar_externo("Python", fuente="wikipedia")
        assert resultado["status"] == "sin_resultados" or resultado["absorbidos"] == []

    def test_deberia_explorar_deshabilitado(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=False)
        assert ce.deberia_explorar_externo() is False

    def test_deberia_explorar_probabilidad(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=True, probabilidad_externa=1.0)
        assert ce.deberia_explorar_externo() is True

    def test_deberia_explorar_nunca(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=True, probabilidad_externa=0.0)
        assert ce.deberia_explorar_externo() is False

    def test_configurar_actualiza(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=False)
        estado = ce.configurar(habilitado=True, probabilidad_externa=0.5)
        assert ce._habilitado is True
        assert ce._probabilidad_externa == 0.5
        assert estado["habilitado"] is True

    def test_estado_completo(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=True)
        estado = ce.estado()
        assert "habilitado" in estado
        assert "probabilidad_externa" in estado
        assert "exploraciones" in estado
        assert "filtro" in estado
        assert "fuentes" in estado
        assert "wikipedia" in estado["fuentes"]
        assert "rss" in estado["fuentes"]
        assert "web" in estado["fuentes"]
        assert "archivos" in estado["fuentes"]

    def test_seleccion_fuente_auto_archivos(self, sistema, tmp_path):
        ce = ConocimientoExterno(sistema=sistema, habilitado=True)
        ce.archivos = FuenteArchivos(directorios=[str(tmp_path)])
        fuente = ce._seleccionar_fuente("algo")
        assert isinstance(fuente, FuenteArchivos)

    def test_seleccion_fuente_tech_rss(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=True)
        ce.archivos = FuenteArchivos(directorios=[])  # sin archivos
        fuente = ce._seleccionar_fuente("python framework")
        assert isinstance(fuente, FuenteRSS)

    def test_seleccion_fuente_wikipedia_default(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=True)
        ce.archivos = FuenteArchivos(directorios=[])
        fuente = ce._seleccionar_fuente("filosofia existencialismo")
        assert isinstance(fuente, FuenteWikipedia)

    def test_seleccion_fuente_hint(self, sistema):
        ce = ConocimientoExterno(sistema=sistema, habilitado=True)
        fuente = ce._seleccionar_fuente("algo", fuente_hint="web")
        assert isinstance(fuente, FuenteWeb)


# ======================================================================
# TestIntegracionVidaAutonoma
# ======================================================================


class TestIntegracionVidaAutonoma:

    @pytest.fixture
    def organismo(self, sistema, tmp_path):
        from src.core.organismo import IANAE
        org = IANAE.desde_componentes(
            sistema,
            diario_path=str(tmp_path / "diario.jsonl"),
            objetivos_path=str(tmp_path / "objetivos.json"),
            conversaciones_path=str(tmp_path / "conv.jsonl"),
            snapshot_dir=str(tmp_path / "snapshots"),
            estado_path=str(tmp_path / "estado.json"),
        )
        return org

    def test_organismo_tiene_conocimiento_externo(self, organismo):
        assert hasattr(organismo, "conocimiento_externo")
        assert organismo.conocimiento_externo is not None

    def test_vida_tiene_conocimiento_externo(self, organismo):
        assert hasattr(organismo.vida, "conocimiento_externo")
        assert organismo.vida.conocimiento_externo is not None

    def test_estado_organismo_incluye_conocimiento(self, organismo):
        estado = organismo.estado()
        assert "conocimiento_externo" in estado

    def test_exploracion_externa_tipo_curiosidad(self):
        from src.core.vida_autonoma import TIPOS_CURIOSIDAD
        assert "exploracion_externa" in TIPOS_CURIOSIDAD

    def test_ciclo_completo_sin_exploracion_externa(self, organismo):
        """Un ciclo normal funciona aunque conocimiento_externo este deshabilitado."""
        resultado = organismo.ciclo_completo()
        assert "vida" in resultado or "timestamp" in resultado

    @patch("src.core.conocimiento_externo.urlopen")
    def test_ciclo_con_exploracion_externa(self, mock_url, organismo,
                                           wiki_response_opensearch, wiki_response_extract):
        """Si se activa y toca exploracion_externa, funciona."""
        mock_url.side_effect = [
            _mock_urlopen(wiki_response_opensearch),
            _mock_urlopen(wiki_response_extract),
            _mock_urlopen(wiki_response_extract),
        ] * 5  # Dar suficientes responses
        organismo.conocimiento_externo.configurar(habilitado=True, probabilidad_externa=1.0)
        # Ejecutar ciclo - puede o no tocar exploracion externa dependiendo de la curiosidad
        resultado = organismo.ciclo_completo()
        assert resultado is not None

    def test_streaming_acepta_evento_exploracion_externa(self, organismo):
        """El bus de streaming acepta el nuevo tipo de evento."""
        ps = organismo.pulso_streaming
        eid = ps.emitir("exploracion_externa", {"concepto": "test", "absorbidos": 2})
        assert eid is not None
        eventos = ps.consumir(desde_id=0)
        assert any(e["tipo"] == "exploracion_externa" for e in eventos)
