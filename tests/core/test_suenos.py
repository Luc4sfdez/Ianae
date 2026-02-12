"""Tests para MotorSuenos — imaginacion de IANAE."""
import pytest

from src.core.nucleo import ConceptosLucas
from src.core.emergente import PensamientoLucas
from src.core.suenos import MotorSuenos


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

    for _ in range(3):
        s.activar("Python", pasos=2, temperatura=0.1)
    return s


@pytest.fixture
def motor(sistema):
    pensamiento = PensamientoLucas(sistema)
    return MotorSuenos(sistema, pensamiento)


# ==================== TestSandbox ====================


class TestSandbox:
    def test_sandbox_copia_conceptos(self, motor):
        sandbox = motor._crear_sandbox()
        assert set(sandbox.conceptos.keys()) == set(motor.sistema.conceptos.keys())

    def test_sandbox_copia_relaciones(self, motor):
        sandbox = motor._crear_sandbox()
        # Al menos algunos conceptos deben tener relaciones
        total_relaciones = sum(len(v) for v in sandbox.relaciones.values())
        assert total_relaciones > 0

    def test_sandbox_no_afecta_original(self, motor):
        conceptos_antes = set(motor.sistema.conceptos.keys())
        sandbox = motor._crear_sandbox()
        sandbox.añadir_concepto("NuevoConcepto", categoria="emergentes")
        conceptos_despues = set(motor.sistema.conceptos.keys())
        assert conceptos_antes == conceptos_despues
        assert "NuevoConcepto" not in motor.sistema.conceptos


# ==================== TestImaginarConexion ====================


class TestImaginarConexion:
    def test_retorna_estructura_completa(self, motor):
        r = motor.imaginar_conexion("Docker", "Tacografos")
        assert "tipo" in r
        assert r["tipo"] == "conexion"
        assert "hipotesis" in r
        assert "baseline" in r
        assert "simulacion" in r
        assert "evaluacion" in r

    def test_evaluacion_tiene_veredicto(self, motor):
        r = motor.imaginar_conexion("Docker", "Tacografos")
        ev = r["evaluacion"]
        assert "impacto" in ev
        assert "veredicto" in ev
        assert ev["veredicto"] in {"perseguir", "considerar", "descartar"}

    def test_impacto_entre_0_y_1(self, motor):
        r = motor.imaginar_conexion("Docker", "Tacografos")
        assert 0.0 <= r["evaluacion"]["impacto"] <= 1.0

    def test_concepto_inexistente_falla_graceful(self, motor):
        r = motor.imaginar_conexion("NoExiste", "Python")
        assert r.get("tipo") == "fallido"

    def test_ambos_inexistentes_falla_graceful(self, motor):
        r = motor.imaginar_conexion("NoA", "NoB")
        assert r.get("tipo") == "fallido"


# ==================== TestImaginarConcepto ====================


class TestImaginarConcepto:
    def test_retorna_estructura(self, motor):
        r = motor.imaginar_concepto("NuevaTech", "tecnologias", ["Python", "Docker"])
        assert "tipo" in r
        assert r["tipo"] == "concepto"
        assert "hipotesis" in r
        assert "impacto" in r
        assert "veredicto" in r

    def test_veredicto_valido(self, motor):
        r = motor.imaginar_concepto("NuevaTech", "tecnologias", ["Python"])
        assert r["veredicto"] in {"prometedor", "posible", "descartable"}

    def test_impacto_entre_0_y_1(self, motor):
        r = motor.imaginar_concepto("NuevaTech", "tecnologias", ["Python", "OpenCV"])
        assert 0.0 <= r["impacto"] <= 1.0

    def test_sin_destinos_validos_falla(self, motor):
        r = motor.imaginar_concepto("X", "emergentes", ["NoExiste"])
        assert r.get("tipo") == "fallido"

    def test_no_modifica_sistema_real(self, motor):
        conceptos_antes = set(motor.sistema.conceptos.keys())
        motor.imaginar_concepto("NuevaTech", "tecnologias", ["Python"])
        assert "NuevaTech" not in motor.sistema.conceptos
        assert set(motor.sistema.conceptos.keys()) == conceptos_antes


# ==================== TestSonar ====================


class TestSonar:
    def test_sonar_conexion(self, motor):
        r = motor.sonar({"tipo": "conexion", "a": "Docker", "b": "Tacografos"})
        assert r["tipo"] == "conexion"

    def test_sonar_concepto(self, motor):
        r = motor.sonar({
            "tipo": "concepto", "nombre": "ML",
            "categoria": "tecnologias", "conectar_a": ["Python"],
        })
        assert r["tipo"] == "concepto"

    def test_sonar_tipo_desconocido(self, motor):
        r = motor.sonar({"tipo": "viaje_temporal"})
        assert "error" in r


# ==================== TestHistorial ====================


class TestHistorial:
    def test_historial_vacio_inicial(self, motor):
        assert motor.historial() == []

    def test_historial_registra_suenos(self, motor):
        motor.imaginar_conexion("Docker", "Tacografos")
        motor.imaginar_concepto("ML", "tecnologias", ["Python"])
        assert len(motor.historial()) == 2

    def test_suenos_prometedores_filtra(self, motor):
        motor.imaginar_conexion("Docker", "Tacografos")
        motor.imaginar_conexion("Python", "OpenCV")
        # Algunos pueden ser prometedores, otros no
        prometedores = motor.suenos_prometedores(umbral=0.0)
        assert len(prometedores) >= 0  # Al menos no falla
        # Con umbral imposible, ninguno
        assert len(motor.suenos_prometedores(umbral=2.0)) == 0
