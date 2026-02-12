"""Tests para metodos principales de PensamientoLucas (emergente.py)."""
import pytest
import numpy as np
import os
import tempfile

from src.core.nucleo import ConceptosLucas, crear_universo_lucas
from src.core.emergente import PensamientoLucas


@pytest.fixture
def sistema_lucas():
    """Sistema completo con conceptos y relaciones de Lucas."""
    s = crear_universo_lucas()
    s.crear_relaciones_lucas()
    return s


@pytest.fixture
def pensamiento(sistema_lucas):
    return PensamientoLucas(sistema_lucas)


# --- Inicializacion ---

class TestInit:
    def test_init_con_sistema(self, sistema_lucas):
        p = PensamientoLucas(sistema_lucas)
        assert p.sistema is sistema_lucas
        assert p.historial_pensamientos == []

    def test_init_sin_sistema(self):
        p = PensamientoLucas()
        assert p.sistema is not None
        assert isinstance(p.sistema, ConceptosLucas)

    def test_contextos_proyecto(self, pensamiento):
        assert 'desarrollo' in pensamiento.contextos_proyecto
        assert 'vision_artificial' in pensamiento.contextos_proyecto
        assert 'ia_local' in pensamiento.contextos_proyecto

    def test_patrones_lucas(self, pensamiento):
        assert 'tecnico_optimizado' in pensamiento.patrones_lucas
        assert all(0 <= v <= 1 for v in pensamiento.patrones_lucas.values())


# --- Detectar contexto ---

class TestDetectarContexto:
    def test_detecta_contexto(self, pensamiento):
        ctx = pensamiento._detectar_contexto_proyecto('Tacografos')
        assert isinstance(ctx, str)

    def test_concepto_inexistente_retorna_general(self, pensamiento):
        ctx = pensamiento._detectar_contexto_proyecto('NoExiste')
        # activar retorna None/[] para conceptos que no existen, pero
        # _detectar_contexto_proyecto llama activar que maneja conceptos inexistentes
        assert isinstance(ctx, str)


# --- Explorar desde proyecto ---

class TestExplorarDesdeProyecto:
    def test_explorar_proyecto_existente(self, pensamiento):
        resultado = pensamiento.explorar_desde_proyecto('Tacografos')
        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_explorar_proyecto_inexistente(self, pensamiento):
        resultado = pensamiento.explorar_desde_proyecto('NoExiste')
        assert 'no encontrado' in resultado.lower()

    def test_explorar_guarda_historial(self, pensamiento):
        assert len(pensamiento.historial_pensamientos) == 0
        pensamiento.explorar_desde_proyecto('Python')
        assert len(pensamiento.historial_pensamientos) == 1
        h = pensamiento.historial_pensamientos[0]
        assert h['proyecto_inicial'] == 'Python'
        assert 'cadena_emergente' in h
        assert 'timestamp' in h

    def test_explorar_con_contexto_explicito(self, pensamiento):
        resultado = pensamiento.explorar_desde_proyecto('Python', contexto='desarrollo')
        assert isinstance(resultado, str)


# --- Construir cadena emergente ---

class TestConstruirCadena:
    def test_cadena_tiene_elementos(self, pensamiento):
        resultado = pensamiento.sistema.activar('Python', pasos=3, temperatura=0.2)
        cadena = pensamiento._construir_cadena_emergente('Python', resultado, 'desarrollo')
        assert len(cadena) > 0
        assert any('Python' in elem for elem in cadena)

    def test_cadena_contextos_diferentes(self, pensamiento):
        resultado = pensamiento.sistema.activar('Python', pasos=2, temperatura=0.2)
        for ctx in ['desarrollo', 'vision_artificial', 'ia_local', 'creatividad', 'general']:
            cadena = pensamiento._construir_cadena_emergente('Python', resultado, ctx)
            assert len(cadena) > 0


# --- Detectar conexiones inesperadas ---

class TestConexionesInesperadas:
    def test_retorna_lista(self, pensamiento):
        resultado = pensamiento.sistema.activar('Python', pasos=3, temperatura=0.2)
        activaciones = resultado[-1]
        conexiones = pensamiento._detectar_conexiones_inesperadas(activaciones)
        assert isinstance(conexiones, list)

    def test_max_3_conexiones(self, pensamiento):
        resultado = pensamiento.sistema.activar('Python', pasos=4, temperatura=0.3)
        activaciones = resultado[-1]
        conexiones = pensamiento._detectar_conexiones_inesperadas(activaciones)
        assert len(conexiones) <= 3

    def test_conexion_tiene_estructura(self, pensamiento):
        resultado = pensamiento.sistema.activar('Python', pasos=4, temperatura=0.3)
        activaciones = resultado[-1]
        conexiones = pensamiento._detectar_conexiones_inesperadas(activaciones)
        for conn in conexiones:
            assert 'conceptos' in conn
            assert 'categorias' in conn
            assert 'fuerza_emergente' in conn
            assert 'novedad' in conn


# --- Sugerir optimizaciones ---

class TestSugerirOptimizaciones:
    def test_retorna_lista(self, pensamiento):
        resultado = pensamiento.sistema.activar('Tacografos', pasos=3, temperatura=0.2)
        activaciones = resultado[-1]
        opts = pensamiento._sugerir_optimizaciones('Tacografos', activaciones)
        assert isinstance(opts, list)

    def test_max_3_optimizaciones(self, pensamiento):
        resultado = pensamiento.sistema.activar('Tacografos', pasos=4, temperatura=0.3)
        activaciones = resultado[-1]
        opts = pensamiento._sugerir_optimizaciones('Tacografos', activaciones)
        assert len(opts) <= 3


# --- Generar reporte ---

class TestGenerarReporte:
    def test_reporte_es_string(self, pensamiento):
        cadena = ['paso1', 'paso2']
        conexiones = []
        optimizaciones = []
        r = pensamiento._generar_reporte_exploracion('Python', cadena, conexiones, optimizaciones, 'desarrollo')
        assert isinstance(r, str)
        assert 'PYTHON' in r.upper()

    def test_reporte_con_conexiones(self, pensamiento):
        cadena = ['paso1']
        conexiones = [{
            'conceptos': ('A', 'B'),
            'categorias': ('tecnologias', 'proyectos'),
            'novedad': 0.5,
        }]
        r = pensamiento._generar_reporte_exploracion('Python', cadena, conexiones, [], 'desarrollo')
        assert 'CONEXIONES' in r.upper()

    def test_reporte_con_optimizaciones(self, pensamiento):
        cadena = ['paso1']
        optimizaciones = [{
            'tipo': 'automatizacion',
            'descripcion': 'Test opt',
            'potencial': 0.5,
            'herramienta': 'Python'
        }]
        r = pensamiento._generar_reporte_exploracion('Python', cadena, [], optimizaciones, 'desarrollo')
        assert 'OPTIMIZACIONES' in r.upper()


# --- Emoji categoria ---

class TestEmojiCategoria:
    def test_categorias_conocidas(self, pensamiento):
        assert pensamiento._get_emoji_categoria('tecnologias') != ''
        assert pensamiento._get_emoji_categoria('proyectos') != ''

    def test_categoria_desconocida(self, pensamiento):
        emoji = pensamiento._get_emoji_categoria('categoria_rara')
        assert isinstance(emoji, str)


# --- Pensamiento contextual ---

class TestPensamientoContextual:
    def test_genera_pensamiento(self, pensamiento):
        texto = pensamiento.generar_pensamiento_contextual('desarrollo', longitud=3)
        assert isinstance(texto, str)
        assert len(texto) > 0

    def test_contexto_aleatorio(self, pensamiento):
        texto = pensamiento.generar_pensamiento_contextual(longitud=3)
        assert isinstance(texto, str)

    def test_guarda_historial(self, pensamiento):
        pensamiento.generar_pensamiento_contextual('desarrollo', longitud=3)
        assert len(pensamiento.historial_pensamientos) == 1
        h = pensamiento.historial_pensamientos[0]
        assert h['patron_aplicado'] == 'contextual_lucas'


# --- Crear narrativa ---

class TestCrearNarrativa:
    def test_narrativa_desarrollo(self, pensamiento):
        t = pensamiento._crear_narrativa_pensamiento(['Python', 'OpenCV'], 'desarrollo')
        assert 'Python' in t
        assert 'OpenCV' in t

    def test_narrativa_single(self, pensamiento):
        t = pensamiento._crear_narrativa_pensamiento(['Python'], 'general')
        assert 'Python' in t


# --- Convergencia proyectos ---

class TestConvergenciaProyectos:
    def test_convergencia_basica(self, pensamiento):
        resultado = pensamiento.experimento_convergencia_proyectos(['Tacografos', 'VBA2Python'])
        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_convergencia_guarda_historial(self, pensamiento):
        pensamiento.experimento_convergencia_proyectos(['Tacografos', 'VBA2Python'])
        assert len(pensamiento.historial_pensamientos) == 1
        h = pensamiento.historial_pensamientos[0]
        assert h['tipo'] == 'convergencia_proyectos'

    def test_convergencia_sin_proyectos(self, pensamiento):
        resultado = pensamiento.experimento_convergencia_proyectos()
        assert isinstance(resultado, str)

    def test_convergencia_tres_proyectos(self, pensamiento):
        resultado = pensamiento.experimento_convergencia_proyectos(
            ['Tacografos', 'VBA2Python', 'RAG_System']
        )
        assert isinstance(resultado, str)


# --- Detectar oportunidades automatizacion ---

class TestDetectarAutomatizacion:
    def test_detectar_retorna_string(self, pensamiento):
        resultado = pensamiento.detectar_oportunidades_automatizacion()
        assert isinstance(resultado, str)
        assert 'AUTOMATIZACI' in resultado.upper()


# --- Analizar patrones personales ---

class TestAnalizarPatrones:
    def test_analizar_retorna_string(self, pensamiento):
        resultado = pensamiento.analizar_patrones_personales()
        assert isinstance(resultado, str)
        assert 'LUCAS' in resultado.upper()


# --- Exportar insights ---

class TestExportarInsights:
    def test_exportar_sin_historial(self, pensamiento):
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            path = f.name
        try:
            result = pensamiento.exportar_insights_lucas(path)
            assert result is True
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_exportar_con_historial(self, pensamiento):
        pensamiento.explorar_desde_proyecto('Python')
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            path = f.name
        try:
            result = pensamiento.exportar_insights_lucas(path)
            assert result is True
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert 'INSIGHTS' in content.upper()
            assert '1' in content
        finally:
            os.unlink(path)

    def test_exportar_ruta_invalida(self, pensamiento):
        result = pensamiento.exportar_insights_lucas('/ruta/invalida/no_existe/archivo.txt')
        assert result is False


# --- Visualizar (no crashea) ---

class TestVisualizar:
    def test_sin_historial(self, pensamiento, capsys):
        pensamiento.visualizar_pensamiento_lucas()
        captured = capsys.readouterr()
        assert 'no hay' in captured.out.lower() or captured.out == ''

    def test_indice_fuera_rango(self, pensamiento, capsys):
        pensamiento.visualizar_pensamiento_lucas(indice=99)
        captured = capsys.readouterr()
        assert 'no hay' in captured.out.lower() or 'rango' in captured.out.lower() or captured.out == ''
