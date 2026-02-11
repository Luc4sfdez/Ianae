"""
Fixtures compartidas para tests de IANAE.
"""
import sys
import os
import pytest
import tempfile
import numpy as np

# Asegurar que src/ esté en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def sistema_vacio():
    """Sistema ConceptosLucas sin conceptos."""
    from nucleo import ConceptosLucas
    return ConceptosLucas(dim_vector=15, incertidumbre_base=0.1)


@pytest.fixture
def sistema_minimo():
    """Sistema con 3 conceptos y 2 relaciones para tests unitarios."""
    from nucleo import ConceptosLucas
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.05)
    s.añadir_concepto('A', atributos=np.ones(15), categoria='tecnologias')
    s.añadir_concepto('B', atributos=np.ones(15) * 0.5, categoria='proyectos')
    s.añadir_concepto('C', atributos=np.random.rand(15), categoria='herramientas')
    s.relacionar('A', 'B', fuerza=0.8)
    s.relacionar('B', 'C', fuerza=0.6)
    return s


@pytest.fixture
def sistema_poblado():
    """Sistema completo con conceptos y relaciones de Lucas."""
    from nucleo import ConceptosLucas
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.15)
    s.crear_conceptos_lucas()
    s.crear_relaciones_lucas()
    return s


@pytest.fixture
def archivo_temporal():
    """Proporciona ruta temporal que se limpia automáticamente."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        ruta = f.name
    yield ruta
    if os.path.exists(ruta):
        os.unlink(ruta)


@pytest.fixture
def directorio_temporal():
    """Proporciona directorio temporal que se limpia automáticamente."""
    d = tempfile.mkdtemp()
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)
