"""Tests de integracion para Fases 9+10+11."""
import os
import tempfile
import pytest

from src.core.nucleo import crear_universo_lucas
from src.core.emergente import PensamientoLucas
from src.core.insights import InsightsEngine
from src.core.vida_autonoma import VidaAutonoma
from src.core.consciencia import Consciencia
from src.core.pensamiento_profundo import PensamientoProfundo
from src.core.memoria_viva import MemoriaViva
from src.core.pulso_streaming import PulsoStreaming


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def componentes(tmpdir):
    sistema = crear_universo_lucas()
    sistema.crear_relaciones_lucas()
    pensamiento = PensamientoLucas(sistema)
    insights = InsightsEngine(sistema, pensamiento)
    pp = PensamientoProfundo(sistema)
    mv = MemoriaViva()
    ps = PulsoStreaming()
    vida = VidaAutonoma(
        sistema, pensamiento, insights,
        diario_path=os.path.join(tmpdir, "diario.jsonl"),
        snapshot_dir=os.path.join(tmpdir, "snapshots"),
        pensamiento_profundo=pp,
        memoria_viva=mv,
        pulso_streaming=ps,
    )
    consciencia = Consciencia(
        vida,
        objetivos_path=os.path.join(tmpdir, "obj.json"),
    )
    return {
        "sistema": sistema, "vida": vida, "consciencia": consciencia,
        "pp": pp, "mv": mv, "ps": ps,
    }


class TestIntegracionFases:
    def test_ciclo_produce_simbolico_en_diario(self, componentes):
        vida = componentes["vida"]
        resultado = vida.ejecutar_ciclo()
        assert "simbolico" in resultado

    def test_ciclo_emite_eventos(self, componentes):
        ps = componentes["ps"]
        componentes["vida"].ejecutar_ciclo()
        eventos = ps.consumir()
        tipos = {e["tipo"] for e in eventos}
        assert "ciclo_inicio" in tipos
        assert "curiosidad_elegida" in tipos
        assert "reflexion" in tipos

    def test_memoria_almacena_tras_ciclo(self, componentes):
        mv = componentes["mv"]
        componentes["vida"].ejecutar_ciclo()
        stats = mv.estadisticas()
        assert stats["total_memorias"] > 0

    def test_multiples_ciclos_integrados(self, componentes):
        vida = componentes["vida"]
        ps = componentes["ps"]
        mv = componentes["mv"]
        for _ in range(5):
            vida.ejecutar_ciclo()
        assert ps.ultimo_id() >= 5  # al menos 1 evento por ciclo
        assert mv.estadisticas()["total_memorias"] >= 5

    def test_deja_vu_afecta_prioridad(self, componentes):
        """Tras varios ciclos, deja vu deberia detectarse."""
        vida = componentes["vida"]
        mv = componentes["mv"]
        # Forzar un concepto especifico en memoria
        concepto = list(componentes["sistema"].conceptos.keys())[0]
        for i in range(5):
            mv.recordar_ciclo(concepto, "gap", 0.9, "revelador", i + 1)
        dv = mv.detectar_deja_vu(concepto)
        assert dv["deja_vu"] is True
        assert dv["factor_ajuste"] <= 1.0

    def test_nuevas_fuerzas_en_ciclo_consciente(self, componentes):
        consciencia = componentes["consciencia"]
        resultado = consciencia.ciclo_consciente()
        fuerzas = resultado["fuerzas"]
        assert "profundidad_simbolica" in fuerzas
        assert "profundidad_memoria" in fuerzas

    def test_ajustar_curiosidad_incluye_nuevas_fuerzas(self, componentes):
        consciencia = componentes["consciencia"]
        ajustes = consciencia.ajustar_curiosidad()
        # Debe retornar dict con tipos de curiosidad
        assert "gap" in ajustes
        assert "serendipia" in ajustes

    def test_profundidad_simbolica_estructura(self, componentes):
        consciencia = componentes["consciencia"]
        prof = consciencia.profundidad_simbolica()
        assert "coherencia_media" in prof
        assert "profundidad_media" in prof
        assert "arboles_construidos" in prof

    def test_profundidad_memoria_activa(self, componentes):
        consciencia = componentes["consciencia"]
        mem = consciencia.profundidad_memoria()
        assert mem["activa"] is True

    def test_vida_sin_nuevos_sistemas_backward_compat(self, tmpdir):
        """VidaAutonoma sin pensamiento_profundo/memoria_viva/pulso funciona."""
        sistema = crear_universo_lucas()
        sistema.crear_relaciones_lucas()
        pensamiento = PensamientoLucas(sistema)
        insights = InsightsEngine(sistema, pensamiento)

        vida = VidaAutonoma(
            sistema, pensamiento, insights,
            diario_path=os.path.join(tmpdir, "diario2.jsonl"),
            snapshot_dir=os.path.join(tmpdir, "snap2"),
        )
        resultado = vida.ejecutar_ciclo()
        assert "ciclo" in resultado
        assert "reflexion" in resultado
        # simbolico debe ser dict vacio (no hay pensamiento_profundo)
        assert resultado.get("simbolico") == {}
