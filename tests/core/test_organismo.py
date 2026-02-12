"""Tests para IANAE — el organismo completo."""
import json
import os

import pytest

from src.core.nucleo import ConceptosLucas
from src.core.organismo import IANAE


# ==================== Fixtures ====================


@pytest.fixture
def sistema():
    s = ConceptosLucas(dim_vector=15, incertidumbre_base=0.0)
    s.añadir_concepto("Python", categoria="tecnologias")
    s.añadir_concepto("OpenCV", categoria="tecnologias")
    s.añadir_concepto("Docker", categoria="tecnologias")
    s.añadir_concepto("Tacografos", categoria="proyectos")
    s.añadir_concepto("RAG_System", categoria="proyectos")
    s.añadir_concepto("Lucas", categoria="lucas_personal")
    s.añadir_concepto("IANAE", categoria="conceptos_ianae")
    s.añadir_concepto("Automatizacion", categoria="herramientas")

    s.relacionar("Python", "OpenCV", fuerza=0.9)
    s.relacionar("Python", "Tacografos", fuerza=0.85)
    s.relacionar("OpenCV", "Tacografos", fuerza=0.95)
    s.relacionar("Python", "RAG_System", fuerza=0.8)
    s.relacionar("RAG_System", "IANAE", fuerza=0.9)
    s.relacionar("Lucas", "Python", fuerza=0.95)
    s.relacionar("Lucas", "IANAE", fuerza=0.9)
    s.relacionar("Docker", "RAG_System", fuerza=0.7)
    s.relacionar("Automatizacion", "Python", fuerza=0.85)

    for _ in range(5):
        s.activar("Python", pasos=2, temperatura=0.1)
        s.activar("Tacografos", pasos=2, temperatura=0.1)
    return s


@pytest.fixture
def ianae(sistema, tmp_path):
    return IANAE.desde_componentes(
        sistema,
        diario_path=str(tmp_path / "diario.jsonl"),
        objetivos_path=str(tmp_path / "objetivos.json"),
        conversaciones_path=str(tmp_path / "conversaciones.jsonl"),
        snapshot_dir=str(tmp_path / "snapshots"),
        intervalo_base=0.01,
    )


# ==================== TestEnsamblaje ====================


class TestEnsamblaje:
    def test_todos_componentes_presentes(self, ianae):
        assert ianae.sistema is not None
        assert ianae.pensamiento is not None
        assert ianae.insights is not None
        assert ianae.vida is not None
        assert ianae.consciencia is not None
        assert ianae.suenos is not None
        assert ianae.dialogo is not None

    def test_componentes_comparten_sistema(self, ianae):
        assert ianae.pensamiento.sistema is ianae.sistema
        assert ianae.insights.sistema is ianae.sistema
        assert ianae.vida.sistema is ianae.sistema

    def test_estado_inicial(self, ianae):
        e = ianae.estado()
        assert e["conceptos"] == 8
        assert e["ciclo_actual"] == 0
        assert e["conversaciones"] == 0


# ==================== TestCicloCompleto ====================


class TestCicloCompleto:
    def test_ciclo_retorna_todas_capas(self, ianae):
        r = ianae.ciclo_completo()
        assert "timestamp" in r
        assert "vida" in r
        assert "narrativa" in r
        assert "fuerzas" in r
        assert "ajustes_curiosidad" in r
        assert "sueno" in r

    def test_multiples_ciclos(self, ianae):
        for _ in range(5):
            r = ianae.ciclo_completo()
            assert isinstance(r, dict)
        assert ianae.vida._ciclo_actual == 5

    def test_sueno_puede_ser_none_o_dict(self, ianae):
        r = ianae.ciclo_completo()
        assert r["sueno"] is None or isinstance(r["sueno"], dict)


# ==================== TestHablar ====================


class TestHablar:
    def test_hablar_retorna_string(self, ianae):
        resp = ianae.hablar("Hablame de Python")
        assert isinstance(resp, str)
        assert len(resp) > 0

    def test_hablar_sobre_concepto(self, ianae):
        resp = ianae.hablar("Que sabes de Docker?")
        assert "Docker" in resp

    def test_preguntar_retorna_dict(self, ianae):
        r = ianae.preguntar("Python y OpenCV?")
        assert "respuesta" in r
        assert "conceptos_detectados" in r
        assert "Python" in r["conceptos_detectados"]

    def test_hablar_sin_concepto_no_falla(self, ianae):
        resp = ianae.hablar("Hola, como estas?")
        assert isinstance(resp, str)


# ==================== TestPersistenciaConversacion ====================


class TestPersistenciaConversacion:
    def test_conversacion_se_persiste(self, ianae):
        ianae.hablar("Python es genial")
        assert os.path.exists(ianae._conversaciones_path)

    def test_leer_conversaciones(self, ianae):
        ianae.hablar("Hablame de Python")
        ianae.hablar("Y de Docker?")
        convs = ianae.leer_conversaciones(ultimas=5)
        assert len(convs) == 2
        assert convs[0]["mensaje"] == "Hablame de Python"

    def test_conversacion_tiene_campos(self, ianae):
        ianae.hablar("IANAE")
        convs = ianae.leer_conversaciones(ultimas=1)
        assert len(convs) == 1
        assert "timestamp" in convs[0]
        assert "mensaje" in convs[0]
        assert "respuesta" in convs[0]
        assert "conceptos" in convs[0]


# ==================== TestRetroalimentacion ====================


class TestRetroalimentacion:
    def test_suenos_retroalimentan(self, ianae):
        # Imaginar algo prometedor
        ianae.imaginar({"tipo": "conexion", "a": "Docker", "b": "Tacografos"})
        # No debe fallar al retroalimentar
        ianae._retroalimentar_suenos()

    def test_conversacion_boost_conceptos(self, ianae):
        activaciones_antes = ianae.sistema.conceptos["Python"]["activaciones"]
        ianae.hablar("Cuentame sobre Python")
        activaciones_despues = ianae.sistema.conceptos["Python"]["activaciones"]
        assert activaciones_despues > activaciones_antes

    def test_sonar_desde_descubrimiento(self, ianae):
        # Ejecutar ciclo para tener descubrimiento
        resultado = ianae.consciencia.ciclo_consciente()
        sueno = ianae._sonar_desde_descubrimiento(resultado)
        # Puede ser None (si fue rutinario) o dict
        assert sueno is None or isinstance(sueno, dict)


# ==================== TestImaginar ====================


class TestImaginar:
    def test_imaginar_conexion(self, ianae):
        r = ianae.imaginar({"tipo": "conexion", "a": "Docker", "b": "Tacografos"})
        assert r["tipo"] == "conexion"
        assert "evaluacion" in r

    def test_imaginar_concepto(self, ianae):
        r = ianae.imaginar({
            "tipo": "concepto", "nombre": "ML",
            "categoria": "tecnologias", "conectar_a": ["Python"],
        })
        assert r["tipo"] == "concepto"


# ==================== TestEstado ====================


class TestEstado:
    def test_estado_completo(self, ianae):
        e = ianae.estado()
        assert "nacido" in e
        assert "edad_s" in e
        assert "conceptos" in e
        assert "relaciones" in e
        assert "pulso" in e
        assert "superficie" in e
        assert "corrientes" in e
        assert "suenos_prometedores" in e
        assert "conversaciones" in e

    def test_detener(self, ianae):
        ianae.vida._corriendo = True
        ianae.detener()
        assert ianae.vida._corriendo is False
