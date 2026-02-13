"""Tests para el motor emocional — Fase 16."""
import pytest

from src.core.emociones import MotorEmocional, EMOCIONES, EFECTOS


@pytest.fixture
def motor():
    return MotorEmocional()


def _pulso(estado="curiosa", energia=0.5, racha=1):
    return {"estado": estado, "energia": energia, "racha": racha, "coherencia": 0.3, "curiosidad": 0.5}


def _crec(tendencia="estable", novedad=0.0):
    return {"tendencia": tendencia, "novedad_promedio": novedad, "score_promedio_reciente": 0.3, "score_promedio_anterior": 0.3}


class TestEstructura:
    def test_emociones_tienen_descripcion_y_valencia(self):
        for nombre, info in EMOCIONES.items():
            assert "descripcion" in info
            assert "valencia" in info
            assert isinstance(info["valencia"], (int, float))

    def test_efectos_cubren_todas_emociones(self):
        for nombre in EMOCIONES:
            assert nombre in EFECTOS

    def test_efectos_son_dicts(self):
        for nombre, efecto in EFECTOS.items():
            assert isinstance(efecto, dict)


class TestEvaluar:
    def test_default_curiosa(self, motor):
        r = motor.evaluar(_pulso(), _crec(), [], 0.5, 0.3, 0.0)
        assert r["emocion"] == "curiosa"
        assert 0.0 <= r["intensidad"] <= 1.0
        assert "valencia" in r
        assert "descripcion" in r
        assert "efectos" in r

    def test_inspirada(self, motor):
        r = motor.evaluar(_pulso("inspirada", 0.8), _crec(), [], 0.5, 0.3, 0.0)
        assert r["emocion"] == "inspirada"

    def test_aburrida(self, motor):
        r = motor.evaluar(_pulso("aburrida", 0.2), _crec(), [], 0.3, 0.1, 0.0)
        assert r["emocion"] == "aburrida"

    def test_enfocada(self, motor):
        r = motor.evaluar(_pulso("enfocada", 0.7, racha=4), _crec(), [], 0.5, 0.3, 0.0)
        assert r["emocion"] == "enfocada"

    def test_melancolica(self, motor):
        r = motor.evaluar(_pulso("curiosa", 0.2), _crec("decayendo"), [], 0.3, 0.1, 0.0)
        assert r["emocion"] == "melancolica"

    def test_asombrada(self, motor):
        r = motor.evaluar(_pulso(), _crec(), [], 0.8, 0.3, 0.8)
        assert r["emocion"] == "asombrada"

    def test_reflexiva(self, motor):
        r = motor.evaluar(_pulso(), _crec("estable"), [], 0.5, 0.7, 0.0)
        assert r["emocion"] == "reflexiva"

    def test_inquieta(self, motor):
        sesgos = [
            {"tipo": "tipo_dominante", "severidad": 0.5, "fuente": "gap", "descripcion": "x"},
            {"tipo": "concepto_dominante", "severidad": 0.3, "fuente": "y", "descripcion": "y"},
        ]
        r = motor.evaluar(_pulso(), _crec(), sesgos, 0.5, 0.3, 0.0)
        assert r["emocion"] == "inquieta"

    def test_intensidad_entre_0_y_1(self, motor):
        for _ in range(10):
            r = motor.evaluar(_pulso(), _crec(), [], 0.5, 0.3, 0.0)
            assert 0.0 <= r["intensidad"] <= 1.0


class TestHistorial:
    def test_historial_se_acumula(self, motor):
        motor.evaluar(_pulso(), _crec(), [], 0.5, 0.3, 0.0)
        motor.evaluar(_pulso("inspirada"), _crec(), [], 0.5, 0.3, 0.0)
        h = motor.historial()
        assert len(h) == 2

    def test_emocion_dominante(self, motor):
        for _ in range(5):
            motor.evaluar(_pulso(), _crec(), [], 0.5, 0.3, 0.0)
        motor.evaluar(_pulso("inspirada"), _crec(), [], 0.5, 0.3, 0.0)
        dom = motor.emocion_dominante()
        assert dom == "curiosa"

    def test_emocion_dominante_vacia(self, motor):
        assert motor.emocion_dominante() is None
