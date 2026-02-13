"""Tests para MemoriaViva — Fase 10."""
import pytest
from src.core.memoria_viva import MemoriaViva


@pytest.fixture
def memoria():
    return MemoriaViva(capacidad_episodica=50, capacidad_semantica=50)


class TestMemoriaViva:
    def test_recordar_y_detectar_deja_vu(self, memoria):
        memoria.recordar_ciclo("Python", "gap", 0.8, "revelador", 1)
        dv = memoria.detectar_deja_vu("Python")
        assert dv["deja_vu"] is True
        assert len(dv["recuerdos"]) > 0

    def test_concepto_nuevo_no_deja_vu(self, memoria):
        dv = memoria.detectar_deja_vu("concepto_nunca_visto")
        assert dv["deja_vu"] is False
        assert dv["factor_ajuste"] > 1.0

    def test_multiples_ciclos_acumulan(self, memoria):
        for i in range(5):
            memoria.recordar_ciclo("Python", "gap", 0.5, "interesante", i + 1)
        dv = memoria.detectar_deja_vu("Python")
        assert dv["deja_vu"] is True

    def test_relacion_almacenada(self, memoria):
        memoria.recordar_relacion("Python", "OpenCV", 0.9, "ciclo:1")
        stats = memoria.estadisticas()
        assert stats["semantica"]["total"] > 0

    def test_orden_canonico(self, memoria):
        memoria.recordar_relacion("Z_concepto", "A_concepto", 0.7)
        memoria.recordar_relacion("A_concepto", "Z_concepto", 0.8)
        stats = memoria.estadisticas()
        # Solo debe haber 1 relacion (misma clave canonica)
        assert stats["semantica"]["total"] == 1

    def test_conceptos_novedosos_ordena(self, memoria):
        memoria.recordar_ciclo("Python", "gap", 0.9, "revelador", 1)
        memoria.recordar_ciclo("Python", "puente", 0.8, "interesante", 2)
        resultado = memoria.conceptos_novedosos(["Python", "Rust", "Go"])
        # Rust y Go nunca vistos → deberian estar primero
        assert resultado[0] in ("Rust", "Go")
        assert resultado[-1] == "Python"

    def test_almacenar_descubrimiento_sin_simbolico(self, memoria):
        memoria.almacenar_descubrimiento(
            concepto="Python", tipo="gap", score=0.6,
            veredicto="interesante", ciclo=1,
        )
        stats = memoria.estadisticas()
        assert stats["episodica"]["total"] > 0

    def test_almacenar_descubrimiento_con_simbolico(self, memoria):
        simbolico = {
            "coherencia_simbolica": 0.8,
            "hibrido": {"conceptos_activados": ["OpenCV", "Pandas"]},
        }
        memoria.almacenar_descubrimiento(
            concepto="Python", tipo="gap", score=0.8,
            veredicto="revelador", ciclo=1, simbolico=simbolico,
        )
        stats = memoria.estadisticas()
        assert stats["semantica"]["total"] > 0

    def test_consolidar_retorna_dict(self, memoria):
        memoria.recordar_ciclo("Python", "gap", 0.5, "rutinario", 1)
        r = memoria.consolidar()
        assert "episodicas_eliminadas" in r
        assert "semanticas_eliminadas" in r

    def test_estadisticas_estructura(self, memoria):
        stats = memoria.estadisticas()
        assert "episodica" in stats
        assert "semantica" in stats
        assert "total_memorias" in stats
        assert "total_activas" in stats

    def test_factor_ajuste_penaliza_deja_vu_fuerte(self, memoria):
        # Almacenar con fuerza alta
        memoria.recordar_ciclo("Python", "gap", 0.99, "revelador", 1)
        memoria.recordar_ciclo("Python", "puente", 0.99, "revelador", 2)
        dv = memoria.detectar_deja_vu("Python")
        # factor_ajuste debe ser bajo (penalizar)
        assert dv["factor_ajuste"] <= 1.0

    def test_estadisticas_vacias(self, memoria):
        stats = memoria.estadisticas()
        assert stats["total_memorias"] == 0
        assert stats["total_activas"] == 0
