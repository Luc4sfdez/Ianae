"""
Tests para emergente.py — PensamientoLucas.

Cubre:
- Inicializacion y contextos
- Exploracion desde proyecto
- Pensamiento contextual
- Convergencia de proyectos
- Deteccion de oportunidades
- Analisis de patrones personales
- Historial de pensamientos
- Exportar insights
"""

import os
import sys
import pytest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'core'))

from nucleo import ConceptosLucas, crear_universo_lucas
from emergente import PensamientoLucas


@pytest.fixture
def sistema_lucas():
    """Sistema completo con conceptos de Lucas."""
    return crear_universo_lucas()


@pytest.fixture
def pensamiento(sistema_lucas):
    """PensamientoLucas con sistema poblado."""
    return PensamientoLucas(sistema=sistema_lucas)


@pytest.fixture
def pensamiento_vacio():
    """PensamientoLucas con sistema vacio."""
    sistema = ConceptosLucas(dim_vector=15)
    sistema.añadir_concepto('TestA', categoria='tecnologias')
    sistema.añadir_concepto('TestB', categoria='proyectos')
    sistema.relacionar('TestA', 'TestB', fuerza=0.5)
    return PensamientoLucas(sistema=sistema)


# ============================================
# Inicializacion
# ============================================

class TestInitPensamientoLucas:
    def test_crea_con_sistema_existente(self, sistema_lucas):
        p = PensamientoLucas(sistema=sistema_lucas)
        assert p.sistema is sistema_lucas
        assert p.historial_pensamientos == []

    def test_crea_sistema_propio_si_no_se_pasa(self):
        p = PensamientoLucas()
        assert p.sistema is not None
        assert isinstance(p.sistema, ConceptosLucas)

    def test_tiene_contextos_proyecto(self, pensamiento):
        assert 'desarrollo' in pensamiento.contextos_proyecto
        assert 'ia_local' in pensamiento.contextos_proyecto
        assert 'creatividad' in pensamiento.contextos_proyecto

    def test_tiene_patrones_lucas(self, pensamiento):
        assert pensamiento.patrones_lucas['tecnico_optimizado'] > 0
        assert pensamiento.patrones_lucas['creativo_divergente'] > 0
        assert pensamiento.patrones_lucas['detalle_exhaustivo'] > 0


# ============================================
# Exploracion desde proyecto
# ============================================

class TestExplorarDesdeProyecto:
    def test_explorar_proyecto_existente(self, pensamiento):
        resultado = pensamiento.explorar_desde_proyecto('Tacografos')
        assert isinstance(resultado, str)
        assert len(resultado) > 0
        assert 'TACOGRAFOS' in resultado.upper() or 'Tacografos' in resultado

    def test_explorar_proyecto_inexistente(self, pensamiento):
        resultado = pensamiento.explorar_desde_proyecto('ProyectoFalso')
        assert 'no encontrado' in resultado.lower()

    def test_explorar_guarda_en_historial(self, pensamiento):
        assert len(pensamiento.historial_pensamientos) == 0
        pensamiento.explorar_desde_proyecto('Tacografos')
        assert len(pensamiento.historial_pensamientos) == 1

    def test_explorar_historial_tiene_datos(self, pensamiento):
        pensamiento.explorar_desde_proyecto('IANAE')
        entry = pensamiento.historial_pensamientos[-1]
        assert entry['proyecto_inicial'] == 'IANAE'
        assert 'contexto' in entry
        assert 'cadena_emergente' in entry
        assert 'timestamp' in entry

    def test_explorar_con_contexto_explicito(self, pensamiento):
        resultado = pensamiento.explorar_desde_proyecto('Python', contexto='desarrollo')
        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_explorar_con_profundidad_custom(self, pensamiento):
        resultado = pensamiento.explorar_desde_proyecto('Tacografos', profundidad=2)
        assert isinstance(resultado, str)


# ============================================
# Pensamiento contextual
# ============================================

class TestPensamientoContextual:
    def test_genera_pensamiento_con_contexto(self, pensamiento):
        resultado = pensamiento.generar_pensamiento_contextual('desarrollo')
        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_genera_pensamiento_sin_contexto(self, pensamiento):
        resultado = pensamiento.generar_pensamiento_contextual()
        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_pensamiento_contextual_guarda_historial(self, pensamiento):
        pensamiento.generar_pensamiento_contextual('ia_local')
        entry = pensamiento.historial_pensamientos[-1]
        assert entry['contexto'] == 'ia_local'
        assert 'conceptos' in entry
        assert 'texto' in entry
        assert entry['patron_aplicado'] == 'contextual_lucas'

    def test_pensamiento_tiene_cadena_conceptos(self, pensamiento):
        pensamiento.generar_pensamiento_contextual('desarrollo')
        entry = pensamiento.historial_pensamientos[-1]
        assert len(entry['conceptos']) >= 1


# ============================================
# Convergencia de proyectos
# ============================================

class TestConvergenciaProyectos:
    def test_convergencia_auto(self, pensamiento):
        resultado = pensamiento.experimento_convergencia_proyectos()
        assert isinstance(resultado, str)
        assert 'CONVERGENCIA' in resultado.upper()

    def test_convergencia_proyectos_especificos(self, pensamiento):
        resultado = pensamiento.experimento_convergencia_proyectos(
            ['Tacografos', 'IANAE']
        )
        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_convergencia_guarda_historial(self, pensamiento):
        pensamiento.experimento_convergencia_proyectos(['Tacografos', 'IANAE'])
        entry = pensamiento.historial_pensamientos[-1]
        assert entry['tipo'] == 'convergencia_proyectos'
        assert 'proyectos' in entry

    def test_convergencia_con_pocos_proyectos(self, pensamiento_vacio):
        resultado = pensamiento_vacio.experimento_convergencia_proyectos()
        assert isinstance(resultado, str)


# ============================================
# Deteccion de oportunidades
# ============================================

class TestDetectarOportunidades:
    def test_detectar_automatizacion(self, pensamiento):
        resultado = pensamiento.detectar_oportunidades_automatizacion()
        assert isinstance(resultado, str)
        assert 'AUTOMATIZACI' in resultado.upper()

    def test_detectar_sin_concepto_automatizacion(self, pensamiento_vacio):
        resultado = pensamiento_vacio.detectar_oportunidades_automatizacion()
        assert isinstance(resultado, str)


# ============================================
# Patrones personales
# ============================================

class TestPatronesPersonales:
    def test_analizar_patrones(self, pensamiento):
        resultado = pensamiento.analizar_patrones_personales()
        assert isinstance(resultado, str)
        assert 'PATRONES' in resultado.upper()

    def test_patrones_incluye_secciones(self, pensamiento):
        resultado = pensamiento.analizar_patrones_personales()
        # Debe incluir al menos alguna seccion de analisis
        assert any(keyword in resultado.upper() for keyword in [
            'FORTALEZAS', 'SUPERPODERES', 'PROYECTOS', 'HERRAMIENTAS', 'RECOMENDACIONES'
        ])


# ============================================
# Historial
# ============================================

class TestHistorial:
    def test_historial_acumula(self, pensamiento):
        pensamiento.explorar_desde_proyecto('Tacografos')
        pensamiento.generar_pensamiento_contextual('desarrollo')
        assert len(pensamiento.historial_pensamientos) == 2

    def test_historial_vacio_al_inicio(self, pensamiento):
        assert pensamiento.historial_pensamientos == []


# ============================================
# Exportar insights
# ============================================

class TestExportarInsights:
    def test_exportar_crea_archivo(self, pensamiento):
        pensamiento.explorar_desde_proyecto('Tacografos')
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            ruta = f.name
        try:
            resultado = pensamiento.exportar_insights_lucas(ruta)
            assert resultado is True
            assert os.path.exists(ruta)
            contenido = open(ruta, encoding='utf-8').read()
            assert 'INSIGHTS' in contenido.upper()
            assert 'Tacografos' in contenido
        finally:
            os.unlink(ruta)

    def test_exportar_sin_historial(self, pensamiento):
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            ruta = f.name
        try:
            resultado = pensamiento.exportar_insights_lucas(ruta)
            assert resultado is True
        finally:
            os.unlink(ruta)


# ============================================
# Deteccion de contexto
# ============================================

class TestDeteccionContexto:
    def test_detecta_contexto_desarrollo(self, pensamiento):
        ctx = pensamiento._detectar_contexto_proyecto('Python')
        assert isinstance(ctx, str)
        assert ctx in list(pensamiento.contextos_proyecto.keys()) + ['general']

    def test_detecta_contexto_ia(self, pensamiento):
        ctx = pensamiento._detectar_contexto_proyecto('IANAE')
        assert isinstance(ctx, str)

    def test_detecta_contexto_general_si_no_match(self, pensamiento_vacio):
        ctx = pensamiento_vacio._detectar_contexto_proyecto('TestA')
        assert ctx == 'general'
