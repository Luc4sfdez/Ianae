"""Tests para PulsoStreaming — Fase 11."""
import threading
import pytest
from src.core.pulso_streaming import PulsoStreaming, TIPOS_EVENTO


@pytest.fixture
def pulso():
    return PulsoStreaming(max_eventos=100)


class TestPulsoStreaming:
    def test_emitir_tipo_valido(self, pulso):
        eid = pulso.emitir("ciclo_inicio", {"ciclo": 1})
        assert eid is not None
        assert eid > 0

    def test_tipo_invalido_no_guarda(self, pulso):
        eid = pulso.emitir("tipo_inventado", {"x": 1})
        assert eid is None
        assert pulso.ultimo_id() == 0

    def test_id_incrementa(self, pulso):
        pulso.emitir("ciclo_inicio", {})
        pulso.emitir("reflexion", {})
        assert pulso.ultimo_id() == 2

    def test_bounded_queue_descarta_antiguos(self):
        p = PulsoStreaming(max_eventos=5)
        for i in range(10):
            p.emitir("ciclo_inicio", {"i": i})
        stats = p.estadisticas()
        assert stats["eventos_en_buffer"] == 5
        assert stats["ultimo_id"] == 10

    def test_consumir_desde_id(self, pulso):
        pulso.emitir("ciclo_inicio", {"a": 1})
        pulso.emitir("reflexion", {"b": 2})
        pulso.emitir("integracion", {"c": 3})

        eventos = pulso.consumir(desde_id=1)
        assert len(eventos) == 2
        assert eventos[0]["id"] == 2

    def test_consumir_con_filtro_tipos(self, pulso):
        pulso.emitir("ciclo_inicio", {})
        pulso.emitir("reflexion", {})
        pulso.emitir("ciclo_inicio", {})

        eventos = pulso.consumir(tipos={"reflexion"})
        assert len(eventos) == 1
        assert eventos[0]["tipo"] == "reflexion"

    def test_consumir_max_eventos(self, pulso):
        for _ in range(10):
            pulso.emitir("ciclo_inicio", {})
        eventos = pulso.consumir(max_eventos=3)
        assert len(eventos) == 3

    def test_suscribir_recibe_eventos(self, pulso):
        recibidos = []
        pulso.suscribir(lambda ev: recibidos.append(ev))
        pulso.emitir("ciclo_inicio", {"x": 1})
        assert len(recibidos) == 1
        assert recibidos[0]["tipo"] == "ciclo_inicio"

    def test_desuscribir(self, pulso):
        recibidos = []
        cb = lambda ev: recibidos.append(ev)
        pulso.suscribir(cb)
        pulso.emitir("ciclo_inicio", {})
        pulso.desuscribir(cb)
        pulso.emitir("reflexion", {})
        assert len(recibidos) == 1

    def test_thread_safety(self, pulso):
        errores = []

        def emitir_muchos(tipo):
            for i in range(50):
                try:
                    pulso.emitir(tipo, {"i": i})
                except Exception as e:
                    errores.append(e)

        tipos = ["ciclo_inicio", "reflexion", "integracion", "exploracion_completa"]
        hilos = [threading.Thread(target=emitir_muchos, args=(t,)) for t in tipos]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        assert len(errores) == 0
        assert pulso.ultimo_id() == 200  # 4 hilos * 50

    def test_estadisticas(self, pulso):
        pulso.emitir("ciclo_inicio", {})
        stats = pulso.estadisticas()
        assert stats["activo"] is True
        assert stats["eventos_en_buffer"] == 1
        assert stats["ultimo_id"] == 1
        assert "ciclo_inicio" in stats["tipos"]
